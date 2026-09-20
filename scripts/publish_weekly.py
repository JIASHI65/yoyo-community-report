#!/usr/bin/env python3
"""Publish the exact weekly draft that was previously generated and reviewed."""
import os
import urllib.request

PAYLOAD_FILE = "weekly-feishu-payload.json"
FEISHU = os.environ.get("FEISHU_WEBHOOK", "")


def main():
    if not FEISHU:
        raise RuntimeError("FEISHU_WEBHOOK is not configured")
    with open(PAYLOAD_FILE, "rb") as payload_file:
        payload = payload_file.read()
    request = urllib.request.Request(
        FEISHU,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        print(response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
