#!/usr/bin/env python3
"""Smoke test for Step-1 E2E validation."""
import sys
from client.sdk.client import AIRuntimeClient


def main() -> None:
    base_url = "http://127.0.0.1:8000"
    client = AIRuntimeClient(base_url=base_url, timeout=10)

    if not client.health_check():
        print("FAIL: Health check failed", file=sys.stderr)
        sys.exit(1)

    response = client.infer(prompt="hello world")

    if not response.text:
        print("FAIL: Empty response text", file=sys.stderr)
        sys.exit(1)

    if not response.request_id:
        print("FAIL: Missing request_id", file=sys.stderr)
        sys.exit(1)

    print("PASS: Step-1 E2E validation successful")


if __name__ == "__main__":
    main()

