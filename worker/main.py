import time
import os
import psycopg2
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import DB_URL, RSS_SOURCES
from ingest import process_rss_feed, reset_feed_failures, get_feed_failures
from cluster import cluster_articles


def connect_db(retries=10, delay_seconds=2):
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(DB_URL)
            return conn
        except psycopg2.OperationalError as e:
            print(f"DB connection failed attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                time.sleep(delay_seconds)
            else:
                raise


def _process_feed(feed_url: str) -> list[dict]:
    conn = connect_db()
    cur = conn.cursor()
    try:
        return process_rss_feed(feed_url, cur, conn)
    except Exception as e:
        print(f"[feed-error] {feed_url}: {e}")
        conn.rollback()
        return []
    finally:
        cur.close()
        conn.close()


def run_once():
    reset_feed_failures()

    all_new_articles: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(RSS_SOURCES)) as executor:
        futures = {executor.submit(_process_feed, url): url for url in RSS_SOURCES}
        for future in as_completed(futures):
            exc = future.exception()
            if exc:
                print(f"[feed-error] {futures[future]}: {exc}")
            else:
                all_new_articles.extend(future.result())

    failures = get_feed_failures()
    if failures:
        print(f"\nFeed failures this run: {failures}")

    print(f"\n[ingest] {len(all_new_articles)} new articles to cluster")

    conn = connect_db()
    cluster_articles(conn, all_new_articles)
    conn.close()
    print("\nDone")


def main():
    interval = int(os.getenv("RUN_INTERVAL_MINUTES", "15")) * 60
    while True:
        start = time.time()
        try:
            run_once()
        except Exception as e:
            print(f"[run-error] {e}")
        elapsed = time.time() - start
        sleep_for = max(0, interval - elapsed)
        print(f"\nSleeping {sleep_for / 60:.1f}min until next run...")
        if sleep_for > 0:
            time.sleep(sleep_for)

if __name__ == "__main__":
    main()
