from main import run_once


def handler(event, context):
    run_once()
    return {"status": "ok"}
