import numpy as np
from openai import OpenAI
from config import OPENAI_API_KEY

_openai = OpenAI(api_key=OPENAI_API_KEY)

SIMILARITY_THRESHOLD = 0.25
MIN_ARTICLES_FOR_STORY = 2


def _parse_embedding(raw) -> np.ndarray:
    if isinstance(raw, (list, np.ndarray)):
        return np.array(raw, dtype=np.float32)
    return np.array(raw.strip("[]").split(","), dtype=np.float32)


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 1.0
    return float(1.0 - np.dot(a, b) / denom)


def _generate_story(articles: list[dict]) -> tuple[str, str]:
    lines = []
    for a in articles[:8]:
        title = a.get("title") or ""
        summary = a.get("summary") or ""
        lines.append(f"- {title}: {summary[:200]}")
    prompt = (
        "The following news articles all cover the same story. "
        "Write a single neutral headline (max 12 words) and a 2-sentence summary of what happened. "
        "Respond in this exact format:\n"
        "HEADLINE: <headline>\n"
        "SUMMARY: <summary>\n\n"
        + "\n".join(lines)
    )
    resp = _openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
    )
    text = resp.choices[0].message.content.strip()
    headline, summary = "", ""
    for line in text.splitlines():
        if line.startswith("HEADLINE:"):
            headline = line.removeprefix("HEADLINE:").strip()
        elif line.startswith("SUMMARY:"):
            summary = line.removeprefix("SUMMARY:").strip()
    return headline or "Untitled Story", summary


def cluster_articles(conn, new_articles: list[dict]):
    """
    new_articles: list of {id, title, summary, embedding} from the current ingest run.
    Embeddings are already in memory — no Neon transfer needed for article embeddings.

    Flow:
      1. Load story centroids from Neon (LIMIT 200, most recent)
      2. Load 50 newest orphans from Neon
      3. Cluster all candidates (new + orphans) against story centroids
      4. Group remaining unmatched candidates against each other
      5. Delete matched orphans, insert newly unmatched new articles as orphans
    """
    cur = conn.cursor()

    # --- Load story centroids (most recent 200, no time filter) ---
    cur.execute("""
        SELECT id, embedding, article_count FROM stories
        WHERE embedding IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT 200
    """)
    stories = [
        {"id": r[0], "centroid": _parse_embedding(r[1]), "count": r[2] or 1}
        for r in cur.fetchall()
    ]
    print(f"[cluster] {len(stories)} story centroids (~{len(stories) * 1536 * 4 // 1024}KB)")

    # --- Load 50 newest orphans ---
    cur.execute("""
        SELECT oa.page_id, p.title, pv.summary, oa.embedding
        FROM orphan_articles oa
        JOIN pages p ON p.id = oa.page_id
        JOIN (
            SELECT DISTINCT ON (page_id) page_id, summary
            FROM page_versions
            WHERE ingest_status = 'full'
            ORDER BY page_id, fetched_at DESC
        ) pv ON pv.page_id = oa.page_id
        ORDER BY oa.created_at DESC
        LIMIT 50
    """)
    orphans = [
        {"id": r[0], "title": r[1], "summary": r[2], "embedding": _parse_embedding(r[3])}
        for r in cur.fetchall()
    ]
    orphan_ids = {a["id"] for a in orphans}
    print(f"[cluster] {len(orphans)} orphans (~{len(orphans) * 1536 * 4 // 1024}KB)")

    # Normalize new article embeddings to numpy arrays
    for a in new_articles:
        if not isinstance(a["embedding"], np.ndarray):
            a["embedding"] = _parse_embedding(a["embedding"])

    candidates = new_articles + orphans

    if not candidates:
        print("[cluster] no candidates")
        cur.close()
        return

    print(f"[cluster] {len(candidates)} total candidates ({len(new_articles)} new + {len(orphans)} orphans)")

    # --- Match all candidates against existing story centroids ---
    still_unassigned = []
    matched_orphan_ids = set()

    for article in candidates:
        emb = article["embedding"]
        best_story_id = None
        best_dist = SIMILARITY_THRESHOLD

        for story in stories:
            dist = _cosine_distance(emb, story["centroid"])
            if dist < best_dist:
                best_dist = dist
                best_story_id = story["id"]

        if best_story_id is not None:
            cur.execute(
                "INSERT INTO story_articles (story_id, page_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (best_story_id, article["id"]),
            )
            for s in stories:
                if s["id"] == best_story_id:
                    old_count = s["count"]
                    new_count = old_count + 1
                    new_centroid = ((s["centroid"] * old_count) + emb) / new_count
                    cur.execute(
                        "UPDATE stories SET embedding = %s, article_count = %s, updated_at = NOW() WHERE id = %s",
                        (new_centroid.tolist(), new_count, best_story_id),
                    )
                    s["centroid"] = new_centroid
                    s["count"] = new_count
                    break
            if article["id"] in orphan_ids:
                matched_orphan_ids.add(article["id"])
            conn.commit()
        else:
            still_unassigned.append(article)

    print(f"[cluster] {len(candidates) - len(still_unassigned)} matched to existing stories, {len(still_unassigned)} remaining")

    # --- Group remaining candidates against each other ---
    used = set()
    new_clusters = []

    for i, a in enumerate(still_unassigned):
        if i in used:
            continue
        cluster = [a]
        used.add(i)
        for j, b in enumerate(still_unassigned):
            if j <= i or j in used:
                continue
            if _cosine_distance(a["embedding"], b["embedding"]) < SIMILARITY_THRESHOLD:
                cluster.append(b)
                used.add(j)
        if len(cluster) >= MIN_ARTICLES_FOR_STORY:
            new_clusters.append(cluster)

    print(f"[cluster] {len(new_clusters)} new stories to create")

    assigned_ids = set()
    for cluster in new_clusters:
        headline, summary = _generate_story(cluster)
        centroid = np.mean([a["embedding"] for a in cluster], axis=0)

        cur.execute("""
            INSERT INTO stories (headline, summary, embedding, article_count, last_seen, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW(), NOW())
            RETURNING id
        """, (headline, summary, centroid.tolist(), len(cluster)))
        story_id = cur.fetchone()[0]

        for a in cluster:
            cur.execute(
                "INSERT INTO story_articles (story_id, page_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (story_id, a["id"]),
            )
            assigned_ids.add(a["id"])
            if a["id"] in orphan_ids:
                matched_orphan_ids.add(a["id"])

        stories.append({"id": story_id, "centroid": centroid, "count": len(cluster)})
        conn.commit()
        print(f"  [new story] {headline} ({len(cluster)} articles)")

    # --- Update orphan table ---
    if matched_orphan_ids:
        cur.execute(
            "DELETE FROM orphan_articles WHERE page_id = ANY(%s)",
            (list(matched_orphan_ids),)
        )
        print(f"[cluster] {len(matched_orphan_ids)} orphans graduated to stories")

    new_orphans = [
        a for a in still_unassigned
        if a["id"] not in orphan_ids and a["id"] not in assigned_ids
    ]
    if new_orphans:
        cur.executemany(
            "INSERT INTO orphan_articles (page_id, embedding) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            [(a["id"], a["embedding"].tolist()) for a in new_orphans]
        )
        print(f"[cluster] {len(new_orphans)} new orphans added to pool")

    conn.commit()
    cur.close()
