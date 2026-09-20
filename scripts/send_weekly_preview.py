#!/usr/bin/env python3
"""Send the generated weekly draft to the private Feishu review group."""
import json
import os
import urllib.request

PREVIEW_WEBHOOK = os.environ.get("FEISHU_PREVIEW_WEBHOOK", "")
PAYLOAD_FILE = "weekly-feishu-payload.json"


def main():
    if not PREVIEW_WEBHOOK:
        print("ℹ️ 未配置私人飞书审稿群，跳过草稿提醒")
        return

    with open(PAYLOAD_FILE) as payload_file:
        payload = json.load(payload_file)

    payload["card"]["header"]["title"]["content"] = (
        "📝 待确认 · " + payload["card"]["header"]["title"]["content"]
    )
    payload["card"]["header"]["template"] = "orange"
    payload["card"]["elements"].append({
        "tag": "note",
        "elements": [{
            "tag": "plain_text",
            "content": "此消息仅供审稿，尚未发送到正式群。请回复修改意见或“确认发送”。",
        }],
    })

    request = urllib.request.Request(
        PREVIEW_WEBHOOK,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        print("私人飞书审稿群响应：" + response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
