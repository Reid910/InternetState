import time
import os
import psycopg2

from config import DB_URL, RSS_SOURCES
from ingest import process_rss_feed, reset_feed_failures, get_feed_failures


def connect_db(retries=10, delay_seconds=2):
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(DB_URL)
            print("Connected to Postgres")
            return conn
        except psycopg2.OperationalError as e:
            print(f"DB connection failed attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                time.sleep(delay_seconds)
            else:
                raise



def run_once():
    reset_feed_failures()

    conn = connect_db()
    cur = conn.cursor()

    for feed_url in RSS_SOURCES:
        try:
            process_rss_feed(feed_url, cur, conn)
        except Exception as e:
            print(f"[feed-error] {feed_url}: {e}")
            conn.rollback()

    failures = get_feed_failures()
    if failures:
        print(f"\nFeed failures this run: {failures}")

    cur.close()
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
