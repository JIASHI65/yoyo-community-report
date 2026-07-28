#!/usr/bin/env python3
"""Generate weekly community report from Discord data."""
import subprocess, json, os, datetime, urllib.request

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
FEISHU = os.environ.get("FEISHU_WEBHOOK", "")

CHANNELS = {
    "creators-exchange": "1458349180748828757",
    "bulletin-board": "1458347958389965035",
    "show-pet": "1529062536404795443",
    "show-merch": "1529063019349545021",
}

def discord_fetch(channel_id, before=None):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"
    if before: url += f"&before={before}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bot {TOKEN}"})
    return json.loads(urllib.request.urlopen(req).read())

def count_recent_week(channel_id):
    """Count messages in the past 7 days."""
    count = 0
    speakers = set()
    week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    before = None
    for _ in range(50):
        try:
            msgs = discord_fetch(channel_id, before)
        except:
            break
        if not msgs or not isinstance(msgs, list): break
        for m in msgs:
            ts = m.get("timestamp", "")
            if not ts: continue
            dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt >= week_ago:
                a = m.get("author", {})
                if not a.get("bot"):
                    count += 1
                    speakers.add(a.get("id"))
            else:
                return count, len(speakers)
        before = msgs[-1]["id"]
    return count, len(speakers)

def main():
    now = datetime.datetime.now()
    week_start = (now - datetime.timedelta(days=now.weekday())).strftime("%m/%d")
    week_end = now.strftime("%m/%d")
    
    # Pull data
    main_count, main_speakers = count_recent_week(CHANNELS["creators-exchange"])
    
    # Build report
    report = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Yoyo Creative Studio · 社群周报</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0e17;color:#e0e6f0;font-family:-apple-system,sans-serif;min-height:100vh}}
.container{{max-width:1200px;margin:0 auto;padding:20px}}
.header{{text-align:center;padding:40px 0 30px;border-bottom:1px solid rgba(0,255,255,.1);margin-bottom:30px}}
.header h1{{font-size:34px;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.header .subtitle{{color:#8892b0;font-size:14px;margin-top:6px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:28px}}
.kpi-card{{background:linear-gradient(135deg,rgba(20,30,60,.8),rgba(15,20,40,.8));border:1px solid rgba(0,212,255,.12);border-radius:14px;padding:18px 20px}}
.kpi-card .label{{color:#8892b0;font-size:11px;text-transform:uppercase;letter-spacing:1px}}
.kpi-card .value{{font-size:30px;font-weight:700;margin:6px 0 3px;color:#00d4ff}}
.kpi-card .change{{font-size:12px;color:#00e676}}
.footer{{text-align:center;padding:20px;color:#5a6480;font-size:11px}}
</style></head>
<body><div class="container">
<div class="header">
  <h1>Yoyo Creative Studio</h1>
  <div class="subtitle">{week_start}-{week_end} · {now.year}年{now.month}月{now.day}日 · 自动生成</div>
</div>
<div class="kpi-grid">
  <div class="kpi-card"><div class="label">📢 公开频道消息</div><div class="value">{main_count}</div><div class="change">本周消息总量</div></div>
  <div class="kpi-card"><div class="label">👥 发言人数</div><div class="value">{main_speakers}</div><div class="change">本周活跃创作者</div></div>
</div>
<div class="footer"><p>🤖 由 GitHub Actions 自动生成 · {now.strftime('%Y年%m月%d日')}</p></div>
</div></body></html>"""
    
    with open("index.html", "w") as f:
        f.write(report)
    
    # Feishu push
    if FEISHU:
        payload = json.dumps({
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"content": f"📊 Yoyo Creative Studio 周报 · {week_start}-{week_end}", "tag": "plain_text"}},
                "elements": [
                    {"tag": "div", "text": {"content": f"📢 本周消息: {main_count} 条 | 👥 发言: {main_speakers} 人", "tag": "lark_md"}},
                    {"tag": "action", "actions": [{"tag": "button", "text": {"content": "📊 查看完整报告", "tag": "plain_text"}, "url": "https://jiashi65.github.io/yoyo-community-report/", "type": "default"}]}
                ]
            }
        }).encode()
        try:
            req = urllib.request.Request(FEISHU, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req)
            print("✅ 已推送飞书")
        except Exception as e:
            print(f"⚠️ 飞书推送失败: {e}")

if __name__ == "__main__":
    main()
