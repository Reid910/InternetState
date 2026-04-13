"""
cluster.py — Story grouping, angle sub-clustering, media tier comparison,
             and coverage gap analysis.

Runs after ingest.py has populated the database with articles and embeddings.
All AI calls that operate on groups of articles live here.
"""

import requests
from config import (
    OLLAMA_URL, MIN_WORD_COUNT, MIN_ARTICLES_FOR_ANGLES,
    ANGLE_DISTANCE_THRESHOLD, MEDIA_TIERS,
)


# ---------------------------------------------------------------------------
# AI — story/group level
# ---------------------------------------------------------------------------

def generate_headline(summaries: list[str]) -> str:
    joined = "\n".join(f"- {s}" for s in summaries)
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "llama3", "prompt": (
            "The following are summaries of news articles all covering the same story.\n"
            "Write a single concise headline (under 15 words) that captures what the story is about.\n"
            "Respond with only the headline, no punctuation at the end:\n\n"
            f"{joined}"
        ), "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip().strip(".")


def generate_story_summary(summaries: list[str]) -> str:
    n = len(summaries)
    joined = "\n".join(f"- {s}" for s in summaries)
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "llama3", "prompt": (
            f"The following are summaries from {n} news sources all covering the same story.\n"
            "Write a 2-3 sentence overview. If sources report different numbers or statistics "
            "(casualties, vote tallies, dollar amounts), note the discrepancy explicitly "
            "(e.g. \"Sources differ, with reports ranging from X to Y\"). "
            "Include specific numbers where they appear. Respond with only the summary, no preamble:\n\n"
            f"{joined}"
        ), "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def generate_angle_title(summaries: list[str]) -> str:
    """Generate a short label (2-5 words) naming a story facet/angle."""
    joined = "\n".join(f"- {s}" for s in summaries[:5])
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "llama3", "prompt": (
            "The following are summaries of news articles focusing on one specific aspect of a larger story.\n"
            "Write a short label (2-5 words) naming this angle or facet.\n"
            "Examples: 'Oil market reaction', 'Military escalation', 'Diplomatic response'\n"
            "Respond with only the label, no punctuation at the end:\n\n"
            f"{joined}"
        ), "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip().strip(".")


def generate_framing_comparison(
    legacy_items: list[tuple[str, str]],
    independent_items: list[tuple[str, str]],
) -> str:
    """Compare how legacy vs independent outlets framed the same story."""
    legacy_block = "\n".join(f"- [{d}] {s}" for d, s in legacy_items[:5])
    indie_block = "\n".join(f"- [{d}] {s}" for d, s in independent_items[:5])
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "llama3", "prompt": (
            "Below are summaries of the same news story from two groups of outlets.\n\n"
            f"LEGACY / MAINSTREAM MEDIA:\n{legacy_block}\n\n"
            f"INDEPENDENT / INVESTIGATIVE MEDIA:\n{indie_block}\n\n"
            "In 3-4 sentences, compare how the two groups framed this story. "
            "Note differences in emphasis, language, what was included or omitted, "
            "and any differences in figures or claims. "
            "Be specific. Respond with only the comparison, no preamble."
        ), "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def generate_coverage_gap_analysis(
    legacy_only: list[str],
    independent_only: list[str],
) -> str:
    """Narrative analysis of what each tier chose to cover vs ignore."""
    legacy_block = "\n".join(f"- {h}" for h in legacy_only[:20])
    indie_block = "\n".join(f"- {h}" for h in independent_only[:20])
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "llama3", "prompt": (
            "Below are news stories covered ONLY by legacy/mainstream media "
            "and stories covered ONLY by independent/investigative media in the past 24 hours.\n\n"
            f"ONLY IN LEGACY MEDIA:\n{legacy_block}\n\n"
            f"ONLY IN INDEPENDENT MEDIA:\n{indie_block}\n\n"
            "In 4-6 sentences, analyze the pattern. What topics or angles is each tier "
            "systematically covering or ignoring? What does this reveal about editorial priorities? "
            "Be specific and analytical. Respond with only the analysis, no preamble."
        ), "stream": False},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


# ---------------------------------------------------------------------------
# Media tier helpers
# ---------------------------------------------------------------------------

def get_media_tier(domain: str) -> str:
    domain = domain.lower().replace("www.", "")
    if domain in MEDIA_TIERS:
        return MEDIA_TIERS[domain]
    for key, tier in MEDIA_TIERS.items():
        if domain.endswith(key):
            return tier
    return "unknown"


def _tiers_from_page_ids(page_ids: list[int], cur) -> tuple[str | None, dict]:
    """Return (coverage_tiers_label, page_meta_dict) for a set of page ids."""
    cur.execute(
        "SELECT id, source_domain, media_tier FROM pages WHERE id = ANY(%s)",
        (page_ids,),
    )
    page_meta = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
    tiers = {t for _, t in page_meta.values() if t not in (None, "aggregator", "unknown")}
    if "legacy" in tiers and "independent" in tiers:
        label = "both"
    elif "legacy" in tiers:
        label = "legacy_only"
    elif "independent" in tiers:
        label = "independent_only"
    else:
        label = None
    return label, page_meta


# ---------------------------------------------------------------------------
# Angle clustering (sub-topics within a story)
# ---------------------------------------------------------------------------

def cluster_angles(story_id: int, page_ids: list[int], conn):
    """
    Sub-cluster articles within a story into named angles.
    Uses a tighter distance threshold than story clustering.
    Only creates angles when the story splits into 2+ distinct groups.
    """
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, pv.summary
        FROM page_versions pv
        JOIN pages p ON p.id = pv.page_id
        WHERE p.id = ANY(%s)
          AND pv.embedding IS NOT NULL
          AND pv.ingest_status = 'full'
        ORDER BY pv.article_date DESC NULLS LAST, pv.fetched_at DESC
    """, (page_ids,))
    articles = {row[0]: row[1] for row in cur.fetchall()}

    if len(articles) < 2:
        cur.close()
        return

    unclustered = dict(articles)
    angle_clusters: list[dict] = []

    while unclustered:
        seed_id = next(iter(unclustered))
        seed_summary = unclustered.pop(seed_id)
        remaining = list(unclustered.keys())
        members = {seed_id: seed_summary}

        if remaining:
            cur.execute("""
                SELECT p.id
                FROM page_versions pv
                JOIN pages p ON p.id = pv.page_id
                WHERE p.id = ANY(%s)
                  AND pv.embedding IS NOT NULL
                  AND pv.embedding <=> (
                      SELECT embedding FROM page_versions
                      WHERE page_id = %s
                      ORDER BY fetched_at DESC LIMIT 1
                  ) < %s
            """, (remaining, seed_id, ANGLE_DISTANCE_THRESHOLD))

            for row in cur.fetchall():
                mid = row[0]
                if mid in unclustered:
                    members[mid] = unclustered.pop(mid)

        angle_clusters.append(members)

    if len(angle_clusters) < 2:
        cur.close()
        return

    print(f"    {len(angle_clusters)} angles for story {story_id}")

    for angle_members in angle_clusters:
        a_page_ids = list(angle_members.keys())
        summaries = [s for s in angle_members.values() if s]
        if not summaries:
            continue

        cur.execute("""
            SELECT sa.angle_id, COUNT(*) AS overlap
            FROM story_articles sa
            WHERE sa.story_id = %s AND sa.page_id = ANY(%s) AND sa.angle_id IS NOT NULL
            GROUP BY sa.angle_id
            ORDER BY overlap DESC
            LIMIT 1
        """, (story_id, a_page_ids))
        existing = cur.fetchone()

        if existing and existing[1] >= max(1, len(a_page_ids) // 2):
            angle_id = existing[0]
            cur.execute("SELECT page_id FROM story_articles WHERE angle_id = %s", (angle_id,))
            already_in = {row[0] for row in cur.fetchall()}
            if not [pid for pid in a_page_ids if pid not in already_in]:
                continue
            title = generate_angle_title(summaries)
            cur.execute(
                "UPDATE story_angles SET title = %s, last_seen = NOW() WHERE id = %s",
                (title, angle_id),
            )
        else:
            title = generate_angle_title(summaries)
            cur.execute(
                "INSERT INTO story_angles (story_id, title) VALUES (%s, %s) RETURNING id",
                (story_id, title),
            )
            angle_id = cur.fetchone()[0]

        for pid in a_page_ids:
            cur.execute("""
                UPDATE story_articles SET angle_id = %s
                WHERE story_id = %s AND page_id = %s AND angle_id IS NULL
            """, (angle_id, story_id, pid))

        conn.commit()
        print(f"      [{angle_id}] {title}")

    cur.close()


# ---------------------------------------------------------------------------
# Story clustering
# ---------------------------------------------------------------------------

def cluster_stories(conn):
    print("\nClustering stories...")
    cur = conn.cursor()

    # --- Pass 1: embedding-based BFS clustering ---
    cur.execute("""
        SELECT p.id, pv.summary
        FROM page_versions pv
        JOIN pages p ON p.id = pv.page_id
        WHERE pv.embedding IS NOT NULL
          AND pv.fetched_at >= NOW() - INTERVAL '7 days'
        ORDER BY pv.article_date DESC NULLS LAST, pv.fetched_at DESC
    """)
    unclustered = {row[0]: row[1] for row in cur.fetchall()}

    clusters: list[dict] = []
    while unclustered:
        seed_id = next(iter(unclustered))
        seed_summary = unclustered.pop(seed_id)

        cur.execute("""
            SELECT p.id
            FROM page_versions pv
            JOIN pages p ON p.id = pv.page_id
            WHERE pv.embedding IS NOT NULL
              AND p.id != %s
              AND pv.embedding <=> (
                  SELECT embedding FROM page_versions
                  WHERE page_id = %s
                  ORDER BY fetched_at DESC LIMIT 1
              ) < 0.25
              AND pv.fetched_at >= NOW() - INTERVAL '7 days'
        """, (seed_id, seed_id))

        members = {seed_id: seed_summary}
        for row in cur.fetchall():
            mid = row[0]
            if mid in unclustered:
                members[mid] = unclustered.pop(mid)

        clusters.append(members)

    multi = sum(1 for c in clusters if len(c) >= 2)
    print(f"  {len(clusters)} stories from embeddings ({multi} with 2+ sources)")

    for members in clusters:
        page_ids = list(members.keys())
        summaries = [s for s in members.values() if s]
        is_solo = len(page_ids) == 1

        coverage_tiers, page_meta = _tiers_from_page_ids(page_ids, cur)

        cur.execute("""
            SELECT story_id, COUNT(*) AS overlap
            FROM story_articles
            WHERE page_id = ANY(%s)
            GROUP BY story_id ORDER BY overlap DESC LIMIT 1
        """, (page_ids,))
        existing = cur.fetchone()

        if existing and existing[1] >= max(1, len(page_ids) // 2):
            story_id = existing[0]
            cur.execute("SELECT page_id FROM story_articles WHERE story_id = %s", (story_id,))
            already_in = {row[0] for row in cur.fetchall()}
            new_ids = [pid for pid in page_ids if pid not in already_in]

            if not new_ids:
                cur.execute(
                    "UPDATE stories SET coverage_tiers = %s WHERE id = %s",
                    (coverage_tiers, story_id),
                )
            else:
                for pid in new_ids:
                    cur.execute("""
                        INSERT INTO story_articles (story_id, page_id) VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (story_id, pid))

                if not is_solo:
                    headline = generate_headline(summaries)
                    story_summary = generate_story_summary(summaries)
                    cur.execute("""
                        UPDATE stories SET headline = %s, summary = %s,
                            coverage_tiers = %s, last_seen = NOW()
                        WHERE id = %s
                    """, (headline, story_summary, coverage_tiers, story_id))
                    print(f"  Updated story {story_id}: {headline}")
                else:
                    cur.execute(
                        "UPDATE stories SET coverage_tiers = %s, last_seen = NOW() WHERE id = %s",
                        (coverage_tiers, story_id),
                    )
            conn.commit()

        else:
            if is_solo:
                cur.execute("SELECT title FROM pages WHERE id = %s", (page_ids[0],))
                row = cur.fetchone()
                headline = row[0] if row and row[0] else (summaries[0][:100] if summaries else "Untitled")
                story_summary = summaries[0] if summaries else None
            else:
                headline = generate_headline(summaries)
                story_summary = generate_story_summary(summaries)

            cur.execute(
                "INSERT INTO stories (headline, summary, coverage_tiers) VALUES (%s, %s, %s) RETURNING id",
                (headline, story_summary, coverage_tiers),
            )
            story_id = cur.fetchone()[0]
            for pid in page_ids:
                cur.execute("""
                    INSERT INTO story_articles (story_id, page_id) VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (story_id, pid))
            conn.commit()
            print(f"  {'Solo' if is_solo else 'New'} story {story_id} [{coverage_tiers}]: {headline[:60]}")

        # Framing comparison when both tiers are present
        if coverage_tiers == "both" and not is_solo:
            cur.execute("SELECT media_comparison FROM stories WHERE id = %s", (story_id,))
            if not cur.fetchone()[0]:
                try:
                    legacy_items = [
                        (page_meta[pid][0], members[pid])
                        for pid in page_ids
                        if page_meta.get(pid, (None, None))[1] == "legacy" and members.get(pid)
                    ]
                    indie_items = [
                        (page_meta[pid][0], members[pid])
                        for pid in page_ids
                        if page_meta.get(pid, (None, None))[1] == "independent" and members.get(pid)
                    ]
                    if legacy_items and indie_items:
                        comparison = generate_framing_comparison(legacy_items, indie_items)
                        cur.execute(
                            "UPDATE stories SET media_comparison = %s WHERE id = %s",
                            (comparison, story_id),
                        )
                        conn.commit()
                        print(f"    [framing] {comparison[:80]}...")
                except Exception as e:
                    print(f"    [framing-error] {e}")

        if len(page_ids) >= MIN_ARTICLES_FOR_ANGLES:
            cluster_angles(story_id, page_ids, conn)

    # --- Pass 2: solo stories for unembedded articles ---
    cur.execute("""
        SELECT p.id, p.title, pv.summary
        FROM page_versions pv
        JOIN pages p ON p.id = pv.page_id
        WHERE pv.fetched_at >= NOW() - INTERVAL '7 days'
          AND pv.embedding IS NULL
          AND p.id NOT IN (SELECT page_id FROM story_articles)
        ORDER BY pv.fetched_at DESC
    """)
    unembedded = cur.fetchall()
    if unembedded:
        print(f"  {len(unembedded)} unembedded articles → solo stories")
    for page_id, title, summary in unembedded:
        headline = title or (summary[:100] if summary else "Untitled")
        cur.execute(
            "INSERT INTO stories (headline, summary) VALUES (%s, %s) RETURNING id",
            (headline, summary),
        )
        story_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO story_articles (story_id, page_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (story_id, page_id),
        )
        conn.commit()

    cur.close()


# ---------------------------------------------------------------------------
# Coverage gap analysis
# ---------------------------------------------------------------------------

def analyze_coverage_gaps(conn):
    """
    Compare what each media tier covered exclusively in the past 24 hours
    and generate an AI narrative about the pattern.
    """
    print("\nAnalyzing coverage gaps...")
    cur = conn.cursor()

    cur.execute("""
        SELECT s.headline, s.coverage_tiers
        FROM stories s
        WHERE s.coverage_tiers IN ('legacy_only', 'independent_only')
          AND s.last_seen >= NOW() - INTERVAL '24 hours'
        ORDER BY s.coverage_tiers, s.last_seen DESC
    """)
    rows = cur.fetchall()

    legacy_only = [r[0] for r in rows if r[1] == "legacy_only"]
    indie_only = [r[0] for r in rows if r[1] == "independent_only"]

    print(f"  {len(legacy_only)} legacy-only, {len(indie_only)} independent-only stories")

    if not legacy_only or not indie_only:
        print("  Skipping — need stories from both tiers")
        cur.close()
        return

    try:
        analysis = generate_coverage_gap_analysis(legacy_only, indie_only)
        cur.execute("""
            INSERT INTO coverage_reports
                (legacy_only_count, independent_only_count, both_count, gap_analysis)
            VALUES (%s, %s,
                (SELECT COUNT(*) FROM stories
                 WHERE coverage_tiers = 'both' AND last_seen >= NOW() - INTERVAL '24 hours'),
                %s)
        """, (len(legacy_only), len(indie_only), analysis))
        conn.commit()
        print(f"  Saved: {analysis[:100]}...")
    except Exception as e:
        print(f"  [gap-analysis-error] {e}")

    cur.close()
