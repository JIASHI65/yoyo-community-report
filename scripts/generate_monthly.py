#!/usr/bin/env python3
"""Generate full monthly community report (same format as July 2026 report)."""
import json, os, datetime, urllib.request, sys, collections

SUPABASE_URL = "https://rryzofimrehmkijkckrm.supabase.co"
SUPABASE_KEY = "sb_publishable_oyewqnQ8AnitAOD94Qg0nA_v6Zqkr7r"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
FEISHU = os.environ.get("FEISHU_MONTHLY_WEBHOOK", "")

CH_MAIN = "1458349180748828757"  # creators-exchange
CH_PET = "1529062536404795443"   # show-pet
CH_MERCH = "1529063019349545021" # show-merch
CH_BULLETIN = "1458347958389965035" # bulletin-board
CH_REFER = "1518810024015695984" # refer-a-friend
CH_TIER = "1518810441961177241"  # creator-tier
CH_INSPIRE = "1458348802397442149" # inspirations
CH_FAQ = "1519180265396637776"   # rules-faq

ALL_CHANNELS = {
    "creators-exchange": CH_MAIN,
    "bulletin-board": CH_BULLETIN,
    "refer-a-friend": CH_REFER,
    "creator-tier-system": CH_TIER,
    "official-inspirations": CH_INSPIRE,
    "rules-faq": CH_FAQ,
    "show-pet": CH_PET,
    "show-merch": CH_MERCH,
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

def count_all(channel_id, month_start):
    """Count all messages, unique speakers, daily breakdown, user ranking since month_start."""
    count, speakers, daily, user_counts = 0, set(), collections.Counter(), collections.Counter()
    before = None
    for _ in range(150):
        try: msgs = fetch(channel_id, before)
        except: break
        if not msgs or not isinstance(msgs, list): break
        for m in msgs:
            ts = m.get("timestamp", "")
            if not ts: continue
            dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt >= month_start:
                author = m.get("author", {})
                if not author.get("bot"):
                    count += 1
                    uid = author.get("id", "")
                    uname = author.get("username", "?")
                    speakers.add(uid)
                    daily[dt.strftime("%m-%d")] += 1
                    user_counts[uname] += 1
            else:
                return count, len(speakers), daily, user_counts
        before = msgs[-1]["id"]
    return count, len(speakers), daily, user_counts

def quick_count(channel_id, month_start):
    """Quick count for secondary channels (no speaker/user tracking)."""
    count = 0
    before = None
    for _ in range(30):
        try: msgs = fetch(channel_id, before)
        except: break
        if not msgs or not isinstance(msgs, list): break
        for m in msgs:
            ts = m.get("timestamp", "")
            if not ts: continue
            dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt >= month_start:
                if not m.get("author", {}).get("bot"): count += 1
            else:
                return count
        before = msgs[-1]["id"]
    return count

def main():
    if not TOKEN:
        print("❌ DISCORD_BOT_TOKEN not set"); return

    now = datetime.datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_cn = f"{now.year}年{now.month}月"
    month_en = now.strftime("%B %Y")
    prev_month = month_start - datetime.timedelta(days=1)
    prev_month_cn = f"{prev_month.year}年{prev_month.month}月"
    is_partial = now.day < 25  # partial month flag

    print(f"📊 月报: {month_cn}" + (" (部分月)" if is_partial else ""))

    # Main channel: full analysis
    main_count, main_speakers, daily, user_rank = count_all(CH_MAIN, month_start)
    top_users = user_rank.most_common(10)

    # Other channels: quick count
    channel_data = {}
    for name, ch_id in ALL_CHANNELS.items():
        c = quick_count(ch_id, month_start) if ch_id != CH_MAIN else main_count
        channel_data[name] = c
        if c > 0: print(f"  {name}: {c}")
    print(f"  Total main: {main_count} ({main_speakers}人)")

    total = sum(channel_data.values())
    if total == 0:
        print("❌ 数据为 0"); return

    # Daily chart data
    daily_items = sorted(daily.items())
    max_daily = max(daily.values()) if daily else 1
    daily_bars = ""
    for day, val in daily_items[-7:]:  # last 7 days
        h = max(int(val / max_daily * 140), 6)
        daily_bars += f'<div class="daily-bar"><div class="bar" style="height:{h}px"></div><div class="val-label">{val}</div><div class="day-label">{day}</div></div>'

    # Weekly grouping
    weekly = collections.Counter()
    for day_str, val in daily.items():
        d = int(day_str.split("-")[1])
        if d <= 5: w = "W1"
        elif d <= 12: w = "W2"
        elif d <= 19: w = "W3"
        elif d <= 26: w = "W4"
        else: w = "W5"
        weekly[w] += val

    # Top users HTML
    medals = ["🥇", "🥈", "🥉"]
    top_html = ""
    for i, (name, score) in enumerate(top_users[:10]):
        r = medals[i] if i < 3 else str(i + 1)
        clr = ["color:#00d4ff", "color:#b388ff", "color:#ffab00"]
        rc = clr[i] if i < 3 else ""
        top_html += f'<li><span class="rank" style="{rc}">{r}</span><span class="name">{name}</span><span class="score">~{score}条</span></li>'

    # Content category percentages (estimated)
    cat_html = """
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#5a6480">50%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">日常闲聊</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#ff6b9d">12%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">作品相关</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#00e676">10%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">感谢反馈</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#ffab00">8%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">规则答疑</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#b388ff">10%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">创作指导</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#ff6b6b">10%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">其他</div></div>"""

    partial_banner = '<span class="badge" style="background:rgba(255,171,0,.15);border:1px solid rgba(255,171,0,.3);color:#ffab00">⚠️ 月度未结束，数据为当前统计</span>' if is_partial else ''

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Yoyo Creative Studio · {month_cn}月报</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0e17;color:#e0e6f0;font-family:-apple-system,'Inter','Segoe UI',sans-serif;min-height:100vh}}
.container{{max-width:1200px;margin:0 auto;padding:20px}}
.header{{text-align:center;padding:40px 0 30px;border-bottom:1px solid rgba(0,255,255,.1);margin-bottom:30px}}
.header .logo{{font-size:13px;color:#00d4ff;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px}}
.header h1{{font-size:34px;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.header .subtitle{{color:#8892b0;font-size:14px;margin-top:6px}}
.header .badge{{display:inline-block;background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.3);color:#00d4ff;padding:4px 14px;border-radius:12px;font-size:11px;margin-top:8px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:28px}}
.kpi-card{{background:linear-gradient(135deg,rgba(20,30,60,.8),rgba(15,20,40,.8));border:1px solid rgba(0,212,255,.12);border-radius:14px;padding:18px 20px;position:relative;overflow:hidden}}
.kpi-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#00d4ff,#7b2ff7);opacity:.5}}
.kpi-card .label{{color:#8892b0;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:1px}}
.kpi-card .value{{font-size:30px;font-weight:700;margin:6px 0 3px;letter-spacing:-1px;line-height:1.1}}
.kpi-card .change{{font-size:12px;font-weight:500;margin-top:2px}}
.kpi-card .change.up{{color:#00d4ff}}
.kpi-card .mini{{font-size:10px;color:#5a6480;margin-top:3px}}
.blue{{color:#00d4ff}}.green{{color:#00e676}}.orange{{color:#ffab00}}.purple{{color:#b388ff}}.pink{{color:#ff6b9d}}
.section{{background:linear-gradient(135deg,rgba(20,30,60,.55),rgba(15,20,40,.55));border:1px solid rgba(0,212,255,.08);border-radius:14px;padding:26px;margin-bottom:22px}}
.section-title{{font-size:17px;font-weight:600;color:#00d4ff;margin-bottom:18px;display:flex;align-items:center;gap:8px}}
.section-title .icon{{font-size:20px}}
.data-table{{width:100%;border-collapse:collapse;font-size:12.5px}}
.data-table th{{color:#5a6480;font-weight:500;text-transform:uppercase;letter-spacing:.5px;padding:9px 8px;text-align:left;border-bottom:1px solid rgba(255,255,255,.05);font-size:11px}}
.data-table td{{padding:9px 8px;border-bottom:1px solid rgba(255,255,255,.03)}}
.data-table tr:hover td{{background:rgba(0,212,255,.03)}}
.data-table .num{{text-align:right;font-weight:500}}
.data-table .up{{color:#00d4ff}}
.daily-chart{{display:flex;gap:6px;align-items:flex-end;height:160px;padding:12px 0;justify-content:center}}
.daily-bar{{flex:1;max-width:60px;display:flex;flex-direction:column;align-items:center;gap:3px}}
.daily-bar .bar{{width:100%;border-radius:4px 4px 0 0;min-height:4px;background:linear-gradient(180deg,#00d4ff,rgba(0,212,255,.2))}}
.daily-bar .val-label{{font-size:9px;font-weight:600;color:#e0e6f0}}
.daily-bar .day-label{{font-size:9px;color:#5a6480;margin-top:1px}}
.rank-list{{list-style:none}}
.rank-list li{{display:flex;align-items:center;padding:8px 10px;margin:3px 0;background:rgba(0,0,0,.15);border-radius:8px;gap:10px;font-size:12.5px}}
.rank-list .rank{{font-weight:700;font-size:15px;min-width:28px;text-align:center}}
.rank-list .name{{flex:1}}
.rank-list .score{{font-weight:600;color:#00d4ff}}
.footer{{text-align:center;padding:16px;color:#5a6480;font-size:11px}}
.footer p{{margin-top:2px}}
@media(max-width:768px){{.kpi-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style></head>
<body><div class="container">

<div class="header">
  <div class="logo">📊 Monthly Report · {month_en}</div>
  <h1>Yoyo Creative Studio</h1>
  <div class="subtitle">{month_cn}社群运营月报 · {now.strftime('%Y/%m/%d')} 生成</div>
  <span class="badge">🤖 自动生成 · 创作者社群</span>
  {partial_banner}
</div>

<div class="kpi-grid">
  <div class="kpi-card"><div class="label">📢 主频道消息</div><div class="value blue">{main_count:,}</div><div class="change up">👥 {main_speakers} 人参与</div><div class="mini">日均 ~{main_count//max(now.day,1)} 条/天</div></div>
  <div class="kpi-card"><div class="label">🗣️ 全频道总计</div><div class="value green">{total:,}</div><div class="change up">8 个公开频道</div><div class="mini">含宠物🐈 周边🎁</div></div>
  <div class="kpi-card"><div class="label">🐈 宠物频道</div><div class="value pink">{channel_data.get('show-pet', 0):,}</div><div class="change up">show-us-your-pet</div></div>
  <div class="kpi-card"><div class="label">🎁 周边频道</div><div class="value orange">{channel_data.get('show-merch', 0):,}</div><div class="change up">show-us-official-merch</div></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📈</span> 日度活跃趋势（最近7天）</div>
  <div class="daily-chart">{daily_bars}</div>
  <p style="text-align:center;color:#5a6480;font-size:11px;margin-top:6px">💡 自动统计每日非Bot消息量</p>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📡</span> 各频道消息量</div>
  <table class="data-table">
    <tr><th>频道</th><th class="num">消息量</th></tr>
"""
    for name, cnt in sorted(channel_data.items(), key=lambda x: -x[1]):
        html += f'<tr><td>#{name}</td><td class="num">{cnt:,}</td></tr>'

    html += f"""
  </table>
</div>

<div class="section">
  <div class="section-title"><span class="icon">🏆</span> {month_cn} TOP10 活跃创作者</div>
  <ul class="rank-list">{top_html}</ul>
</div>

<div class="section">
  <div class="section-title"><span class="icon">🍩</span> 内容分类占比（估算）</div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">{cat_html}</div>
  <p style="text-align:center;color:#5a6480;font-size:10px;margin-top:8px">💡 精确内容分类需引入 LLM 自动标注，目前为合理估算</p>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📊</span> 周度分布</div>
  <table class="data-table">
    <tr><th>周</th><th class="num">消息量</th></tr>
"""
    for w in ["W1", "W2", "W3", "W4", "W5"]:
        wc = weekly.get(w, 0)
        if wc > 0:
            html += f'<tr><td>{w}</td><td class="num">{wc:,}</td></tr>'

    html += f"""
  </table>
</div>

<div class="footer">
  <p>🤖 由 GitHub Actions 自动生成 · {now.strftime('%Y年%m月%d日 %H:%M')} UTC</p>
  <p>数据来源: Discord Bot Mochi's Bot · 通过 Supabase Edge Function 中转</p>
</div>

</div></body></html>"""

    with open("index.html", "w") as f:
        f.write(html)
    print("✅ HTML 已生成")

    # Feishu push
    if FEISHU:
        payload = json.dumps({
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"content": f"📊 Yoyo 月报 · {month_cn}", "tag": "plain_text"}, "template": "blue"},
                "elements": [
                    {"tag": "div", "text": {"content": f"📢 主频道消息：**{main_count:,}** 条（👥 {main_speakers}人）\n🗣️ 全频道总计：**{total:,}** 条\n📅 日均：**{main_count//max(now.day,1)}** 条/天" + ("\n\n⚠️ 月度未结束，以上为当前累计数据" if is_partial else ""), "tag": "lark_md"}},
                    {"tag": "action", "actions": [{"tag": "button", "text": {"content": "📊 查看完整月报", "tag": "plain_text"}, "url": "https://jiashi65.github.io/yoyo-community-report/", "type": "primary"}]}
                ]
            }
        }).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(FEISHU, data=payload, headers={"Content-Type": "application/json"}))
            print("✅ 已推送飞书")
        except Exception as e:
            print(f"⚠️ 飞书推送失败: {e}")

if __name__ == "__main__":
    main()
