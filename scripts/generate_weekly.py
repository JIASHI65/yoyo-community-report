#!/usr/bin/env python3
"""Generate weekly community growth report."""
import subprocess, json, os, datetime, urllib.request

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
FEISHU = os.environ.get("FEISHU_WEBHOOK", "https://open.feishu.cn/open-apis/bot/v2/hook/a770eb64-5613-4078-904d-ac649b47b145")
SUPABASE_URL = "https://rryzofimrehmkijkckrm.supabase.co"
SUPABASE_KEY = "sb_publishable_oyewqnQ8AnitAOD94Qg0nA_v6Zqkr7r"

CHANNELS = {
    "creators-exchange": "1458349180748828757",
    "show-pet": "1529062536404795443",
    "show-merch": "1529063019349545021",
    "bulletin-board": "1458347958389965035",
}

def discord_fetch(channel_id, before=None):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"
    if before: url += f"&before={before}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bot {TOKEN}"})
    return json.loads(urllib.request.urlopen(req).read())

def supabase_fetch(endpoint):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{endpoint}",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(req).read())

def count_week(channel_id):
    count, speakers = 0, set()
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    before = None
    for _ in range(60):
        try: msgs = discord_fetch(channel_id, before)
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
    monday = now - datetime.timedelta(days=now.weekday())
    last_monday = monday - datetime.timedelta(days=7)
    week_label = f"{monday.strftime('%m/%d')}-{now.strftime('%m/%d')}"

    print(f"📊 周报: {week_label}")

    # Discord data
    main_count, main_speakers = count_week(CHANNELS["creators-exchange"])
    pet_count, _ = count_week(CHANNELS["show-pet"])
    merch_count, _ = count_week(CHANNELS["show-merch"])
    total_discord = main_count + pet_count + merch_count

    # Supabase KOC data
    try:
        kocs = supabase_fetch("kocs?select=uid,tier,created_at&status=eq.active")
        total_koc = len(kocs) if isinstance(kocs, list) else 0
        new_this_week = 0
        week_ago = (now - datetime.timedelta(days=7)).isoformat()
        for k in (kocs if isinstance(kocs, list) else []):
            if k.get("created_at", "") >= week_ago:
                new_this_week += 1
    except:
        total_koc = "?"
        new_this_week = "?"

    # Build the Feishu card
    g = lambda v: f"+{v}" if isinstance(v, (int, float)) and v > 0 else str(v)

    payload = json.dumps({
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"content": f"📊 Yoyo 创作者社群 · 周报 {week_label}", "tag": "plain_text"},
                "template": "blue"
            },
            "elements": [
                {"tag": "div", "text": {"content": f"**📈 本周增长数据**\n\n🆕 新增创作者：**{new_this_week}** 人\n👥 创作者总数：**{total_koc}** 人\n💬 本周消息总量：**{total_discord}** 条\n🎨 含作品/宠物/周边分享", "tag": "lark_md"}},
                {"tag": "hr"},
                {"tag": "div", "text": {"content": f"**📊 核心指标看板**\n\n· 主频道活跃：{main_count} 条消息 | {main_speakers} 人参与\n· 宠物频道：{pet_count} 条 | 周边频道：{merch_count} 条\n· 创作者池规模：{total_koc} 人（本周净增 {new_this_week}）", "tag": "lark_md"}},
                {"tag": "hr"},
                {"tag": "action", "actions": [
                    {"tag": "button", "text": {"content": "📊 完整月报", "tag": "plain_text"}, "url": "https://jiashi65.github.io/yoyo-community-report/", "type": "primary"},
                    {"tag": "button", "text": {"content": "👥 KOC 管理系统", "tag": "plain_text"}, "url": "https://jiashi65.github.io/yoyo-koc-exchange/admin.html", "type": "default"}
                ]},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "🤖 自动生成 · yoyo-community-report · 每周一推送"}]}
            ]
        }
    }).encode()

    try:
        req = urllib.request.Request(FEISHU, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req)
        print(f"✅ 飞书已推送: {total_discord}条, {total_koc}创作者")
    except Exception as e:
        print(f"⚠️ 飞书推送失败: {e}")

    # Write minimal HTML
    with open("index.html", "w") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Yoyo Creative Studio · 社群周报</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0e17;color:#e0e6f0;font-family:-apple-system,sans-serif;min-height:100vh}}
.container{{max-width:800px;margin:0 auto;padding:20px}}
h1{{font-size:28px;text-align:center;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;padding:30px 0 10px}}
.sub{{text-align:center;color:#5a6480;font-size:13px;margin-bottom:30px}}
.metrics{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.m{{background:linear-gradient(135deg,rgba(20,30,60,.8),rgba(15,20,40,.8));border:1px solid rgba(0,212,255,.12);border-radius:12px;padding:16px}}
.m .label{{color:#5a6480;font-size:11px;text-transform:uppercase;margin-bottom:4px}}
.m .val{{font-size:28px;font-weight:700;color:#00d4ff}}
.m .detail{{font-size:11px;color:#8892b0;margin-top:4px}}
.footer{{text-align:center;color:#5a6480;font-size:11px;margin-top:40px}}
</style></head><body><div class="container">
<h1>Yoyo Creative Studio</h1>
<div class="sub">{week_label} · {now.year}年{now.month}月{now.day}日 · 自动生成</div>
<div class="metrics">
<div class="m"><div class="label">🆕 本周新增创作者</div><div class="val">{new_this_week}</div><div class="detail">总创作者池: {total_koc} 人</div></div>
<div class="m"><div class="label">💬 本周消息总量</div><div class="val">{total_discord}</div><div class="detail">{main_speakers} 人参与讨论</div></div>
<div class="m"><div class="label">🐈 宠物频道</div><div class="val">{pet_count}</div><div class="detail">show-us-your-pet</div></div>
<div class="m"><div class="label">🎁 周边频道</div><div class="val">{merch_count}</div><div class="detail">show-us-official-merch</div></div>
</div>
<div class="footer">🤖 GitHub Actions 自动生成 · {now.strftime('%Y-%m-%d %H:%M')} UTC</div>
</div></body></html>""")
    print("✅ HTML updated")

if __name__ == "__main__":
    main()
