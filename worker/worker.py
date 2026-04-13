"""
worker.py — SQS-based entry point for AWS deployment.

Polls an SQS queue for job messages. When a 'fetch_feeds' message arrives,
calls run_once() from main.py, then deletes the message.

For local dev, use main.py (sleep loop) instead.

EventBridge Scheduler → SQS queue → this worker → run_once()
"""

import json
import time
import boto3

from config import AWS_REGION, SQS_URL
from main import run_once


def handle_message(sqs, message):
    try:
        body = json.loads(message.get("Body", "{}"))
        if body.get("type") == "fetch_feeds":
            print(f"[sqs] received fetch_feeds — starting run")
            run_once()
        else:
            print(f"[sqs] unknown message type: {body.get('type')} — skipping")
    finally:
        sqs.delete_message(
            QueueUrl=SQS_URL,
            ReceiptHandle=message["ReceiptHandle"],
        )


def poll_queue_forever():
    if not SQS_URL:
        raise RuntimeError("SQS_URL is not set — cannot start SQS worker")

    sqs = boto3.client("sqs", region_name=AWS_REGION)
    print(f"[sqs] polling {SQS_URL}")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,  # long polling
            )
            for message in response.get("Messages", []):
                handle_message(sqs, message)
        except Exception as e:
            print(f"[sqs-error] {e}")
            time.sleep(5)


if __name__ == "__main__":
    poll_queue_forever()
