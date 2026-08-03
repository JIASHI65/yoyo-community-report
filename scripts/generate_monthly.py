#!/usr/bin/env python3
"""Generate monthly community report. Feishu push needs FEISHU_MONTHLY_WEBHOOK secret."""
import json, os, datetime, urllib.request, sys

SUPABASE_URL = "https://rryzofimrehmkijkckrm.supabase.co"
SUPABASE_KEY = "sb_publishable_oyewqnQ8AnitAOD94Qg0nA_v6Zqkr7r"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
FEISHU = os.environ.get("FEISHU_MONTHLY_WEBHOOK", "")  # Different from weekly!

CHANNELS = {
    "creators-exchange": "1458349180748828757",
    "show-pet": "1529062536404795443",
    "show-merch": "1529063019349545021",
}

def fetch(channel_id, before=None):
    data = json.dumps({
        "action": "list_messages",
        "data": {"channel_id": channel_id, "limit": 100, "before": before} if before else {"channel_id": channel_id, "limit": 100},
        "token": TOKEN
    }).encode()
    req = urllib.request.Request(f"{SUPABASE_URL}/functions/v1/discord-proxy", data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {SUPABASE_KEY}"})
    return json.loads(urllib.request.urlopen(req).read())

def count_month(channel_id):
    count, speakers = 0, set()
    cutoff = datetime.datetime.now(datetime.timezone.utc).replace(day=1)
    before = None
    for i in range(100):
        try: msgs = fetch(channel_id, before)
        except: break
        if not msgs or not isinstance(msgs, list): break
        for m in msgs:
            ts = m.get("timestamp", "")
            if not ts: continue
            dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt >= cutoff:
                if not m.get("author", {}).get("bot"):
                    count += 1; speakers.add(m.get("author", {}).get("id"))
            else: return count, len(speakers)
        before = msgs[-1]["id"]
    return count, len(speakers)

def main():
    if not TOKEN:
        print("❌ DISCORD_BOT_TOKEN not set"); return

    now = datetime.datetime.now()
    month_cn = f"{now.year}年{now.month}月"
    print(f"📊 月报: {month_cn}")

    main_count, main_speakers = count_month(CHANNELS["creators-exchange"])
    pet_count, _ = count_month(CHANNELS["show-pet"])
    merch_count, _ = count_month(CHANNELS["show-merch"])
    total = main_count + pet_count + merch_count
    print(f"  Total: {total} | main: {main_count} ({main_speakers}人) | pet: {pet_count} | merch: {merch_count}")

    if total == 0:
        print("❌ 数据为 0，不发飞书"); return

    # Generate minimal HTML placeholder
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>Yoyo · 月报 {month_cn}</title></head>
<body style="background:#0a0e17;color:#e0e6f0;font-family:-apple-system,sans-serif;text-align:center;padding:60px">
<h1 style="background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent">Yoyo Creative Studio</h1>
<p>📊 {month_cn} 月报</p>
<p>全频道消息: {total} | 主频道: {main_count} ({main_speakers}人) | 🐈宠物: {pet_count} | 🎁周边: {merch_count}</p>
<p style="color:#5a6480;font-size:11px;margin-top:40px">🤖 自动生成 · {now.strftime('%Y-%m-%d')}</p>
</body></html>"""
    with open("index.html", "w") as f:
        f.write(html)
    print("✅ HTML 已生成")

    if FEISHU:
        payload = json.dumps({
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"content": f"📊 Yoyo 月报 · {month_cn}", "tag": "plain_text"}, "template": "blue"},
                "elements": [
                    {"tag": "div", "text": {"content": f"📢 全频道消息: **{total}** 条\n💬 主频道: **{main_count}** 条 ({main_speakers}人)\n🐈 宠物: {pet_count} | 🎁 周边: {merch_count}", "tag": "lark_md"}},
                    {"tag": "action", "actions": [{"tag": "button", "text": {"content": "📊 查看完整月报", "tag": "plain_text"}, "url": "https://jiashi65.github.io/yoyo-community-report/", "type": "primary"}]}
                ]
            }
        }).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(FEISHU, data=payload, headers={"Content-Type": "application/json"}))
            print("✅ 已推送飞书")
        except Exception as e:
            print(f"⚠️ 飞书推送失败: {e}")
    else:
        print("⚠️ FEISHU_MONTHLY_WEBHOOK 未设置，跳过飞书推送")

if __name__ == "__main__":
    main()
