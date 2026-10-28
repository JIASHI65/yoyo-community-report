#!/usr/bin/env python3
import datetime
import json
import os
import urllib.parse
import urllib.request


TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "1458349180748828757")
LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "72"))
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "recent-channel-scan.json")


def fetch(before=None):
    params = {"limit": 100}
    if before:
        params["before"] = before
    url = (
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?"
        + urllib.parse.urlencode(params)
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "User-Agent": "DiscordBot (community incident review, 1.0)",
        },
    )
    return json.loads(urllib.request.urlopen(request, timeout=30).read())


def main():
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=LOOKBACK_HOURS
    )
    before = None
    messages = []
    for _ in range(100):
        batch = fetch(before)
        if not batch:
            break
        reached_cutoff = False
        for message in batch:
            timestamp = datetime.datetime.fromisoformat(
                message["timestamp"].replace("Z", "+00:00")
            )
            if timestamp < cutoff:
                reached_cutoff = True
                continue
            author = message.get("author", {})
            if author.get("bot"):
                continue
            referenced = message.get("referenced_message") or {}
            messages.append(
                {
                    "id": message["id"],
                    "timestamp": message["timestamp"],
                    "username": author.get("username", "unknown"),
                    "display_name": author.get("global_name") or "",
                    "content": message.get("content", ""),
                    "referenced_content": referenced.get("content", ""),
                }
            )
        if reached_cutoff:
            break
        before = batch[-1]["id"]

    messages.reverse()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as output:
        json.dump(messages, output, ensure_ascii=False)
    print(f"Captured {len(messages)} messages from the requested time window")


if __name__ == "__main__":
    main()
