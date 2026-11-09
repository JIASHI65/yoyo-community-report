#!/usr/bin/env python3
"""List Discord members assigned to a named role."""
import json
import os
import time
import urllib.error
import urllib.request


GUILD_ID = "1458340952358785193"
ROLE_NAME = os.environ.get("ROLE_NAME", "Gold Creator")
TOKEN = os.environ["DISCORD_BOT_TOKEN"]


def get(path):
    request = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {TOKEN}", "User-Agent": "DiscordBot (role-audit, 1.0)"},
    )
    for attempt in range(8):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 7:
                raise
            delay = float(json.load(error).get("retry_after", 1))
            time.sleep(delay + 0.25)


def main():
    roles = get(f"/guilds/{GUILD_ID}/roles")
    matches = [role for role in roles if role["name"].casefold() == ROLE_NAME.casefold()]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one role named {ROLE_NAME!r}; found {len(matches)}")
    role_id = matches[0]["id"]
    members = []
    after = "0"
    while True:
        page = get(f"/guilds/{GUILD_ID}/members?limit=1000&after={after}")
        if not isinstance(page, list):
            raise RuntimeError("Discord did not return a member list")
        for member in page:
            if role_id in member.get("roles", []):
                user = member["user"]
                members.append({
                    "id": user["id"],
                    "username": user.get("username", ""),
                    "display_name": member.get("nick") or user.get("global_name") or user.get("username", ""),
                })
        if len(page) < 1000:
            break
        after = page[-1]["user"]["id"]
    with open("role-members.json", "w", encoding="utf-8") as output:
        json.dump({"role": ROLE_NAME, "role_id": role_id, "members": members}, output, ensure_ascii=False)
    print(f"Matched {len(members)} members to requested role")


if __name__ == "__main__":
    main()
