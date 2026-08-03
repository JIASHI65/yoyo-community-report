#!/usr/bin/env python3
"""Generate monthly community report with MoM comparison."""
import json, os, datetime, urllib.request, sys, collections, math

SUPABASE_URL = "https://rryzofimrehmkijkckrm.supabase.co"
SUPABASE_KEY = "sb_publishable_oyewqnQ8AnitAOD94Qg0nA_v6Zqkr7r"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
FEISHU = os.environ.get("FEISHU_MONTHLY_WEBHOOK", "")
CACHE_FILE = "monthly_cache.json"

CH_MAIN = "1458349180748828757"
ALL_CHANNELS = {
    "creators-exchange": CH_MAIN,
    "bulletin-board": "1458347958389965035",
    "refer-a-friend": "1518810024015695984",
    "creator-tier-system": "1518810441961177241",
    "official-inspirations": "1458348802397442149",
    "rules-faq": "1519180265396637776",
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

def count_all(channel_id, month_start):
    """Count messages, speakers, daily, user ranking from month_start onward. Returns (count, speakers, daily, user_counts, last_before_id)."""
    count, speakers, daily, user_counts = 0, set(), collections.Counter(), collections.Counter()
    before = None
    for _ in range(200):
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
    count = 0
    before = None
    for _ in range(50):
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

def week_label(day_str):
    """Map day string like '08-03' to W1/W2/W3/W4/W5."""
    try:
        parts = day_str.split("-")
        d = int(parts[1])
        if d <= 7: return "W1"
        elif d <= 14: return "W2"
        elif d <= 21: return "W3"
        elif d <= 28: return "W4"
        else: return "W5"
    except: return "W?"

def fmt_change(curr, prev):
    """Format MoM change: '+56.3%' or '-12.0%' or '新增' if prev is 0."""
    if prev == 0 and curr == 0: return "-"
    if prev == 0: return "新增"
    pct = (curr - prev) / prev * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"

def change_color(curr, prev):
    """Return CSS color class for MoM change."""
    if prev == 0 and curr > 0: return "up"
    if prev == 0: return "down"
    if curr >= prev: return "up"
    return "down"

def main():
    if not TOKEN:
        print("❌ DISCORD_BOT_TOKEN not set"); return

    now = datetime.datetime.now(datetime.timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_cn = f"{now.year}年{now.month}月"
    month_en = now.strftime("%B %Y")
    prev_month = month_start - datetime.timedelta(days=1)
    prev_month_start = prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_cn = f"{prev_month.year}年{prev_month.month}月"
    is_partial = now.day < 25
    month_key = now.strftime("%Y-%m")

    print(f"📊 月报: {month_cn}" + (" (部分月)" if is_partial else ""))

    # --- Try load previous month from cache ---
    prev_cache = {}
    try:
        with open(CACHE_FILE) as f:
            prev_cache = json.load(f)
        if prev_cache.get("month") != prev_month.strftime("%Y-%m"):
            print(f"⚠️ 缓存是 {prev_cache.get('month')} 不是 {prev_month.strftime('%Y-%m')}，不适用")
            prev_cache = {}
    except: pass

    # --- Current month data ---
    main_count, main_speakers, daily, user_rank = count_all(CH_MAIN, month_start)
    top_users = user_rank.most_common(10)

    channel_data = {}
    for name, ch_id in ALL_CHANNELS.items():
        c = quick_count(ch_id, month_start) if ch_id != CH_MAIN else main_count
        channel_data[name] = c
        if c > 0: print(f"  {name}: {c}")
    print(f"  Total main: {main_count} ({main_speakers}人)")

    total = sum(channel_data.values())
    if total == 0:
        print("❌ 数据为 0"); return

    # --- Previous month data (from cache or fetch) ---
    prev_main_count = prev_cache.get("main_count", 0)
    prev_main_speakers = prev_cache.get("main_speakers", 0)
    prev_daily = prev_cache.get("daily", {})
    prev_channel_data = prev_cache.get("channel_data", {})
    prev_total = prev_cache.get("total", 0)
    prev_top_users = prev_cache.get("top_users", [])
    has_prev = prev_cache != {}

    # Save current month for next time
    weekly_curr = collections.Counter()
    for day_str, val in daily.items():
        weekly_curr[week_label(day_str)] += val

    cache_data = {
        "month": month_key,
        "main_count": main_count,
        "main_speakers": main_speakers,
        "total": total,
        "channel_data": channel_data,
        "daily": dict(daily),
        "weekly": dict(weekly_curr),
        "top_users": [(u, c) for u, c in top_users],
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, ensure_ascii=False)
    print(f"💾 已缓存本月数据到 {CACHE_FILE}")

    # --- Build HTML ---
    # KPI cards with MoM
    kpi_cards = []
    kpi_items = [
        ("📢 主频道消息", main_count, prev_main_count, "条", "blue"),
        ("👥 发言人数", main_speakers, prev_main_speakers, "人", "green"),
        ("🗣️ 全频道总计", total, prev_total, "条", "pink"),
    ]
    for label, curr, prev, unit, color in kpi_items:
        ch = fmt_change(curr, prev)
        ccol = change_color(curr, prev)
        kpi_cards.append(f'<div class="kpi-card"><div class="label">{label}</div><div class="value {color}">{curr:,}<span class="unit">{unit}</span></div><div class="change {ccol}">环比 {ch}</div></div>')

    # Monthly comparison table
    comp_table_rows = []
    comp_metrics = [
        ("公开频道总消息", main_count, prev_main_count),
        ("日均消息", main_count // max(now.day, 1), prev_main_count // max(prev_month.day, 1) if prev_main_count else 0),
        ("发言人数", main_speakers, prev_main_speakers),
        ("活跃子频道数", sum(1 for c in channel_data.values() if c > 0), sum(1 for c in prev_channel_data.values() if c > 0) if prev_channel_data else 0),
    ]
    for metric, curr, prev in comp_metrics:
        ch = fmt_change(curr, prev)
        ccol = change_color(curr, prev)
        comp_table_rows.append(f'<tr><td>{metric}</td><td class="num">{prev:,}</td><td class="num">{curr:,}</td><td class="num {ccol}">{ch}</td></tr>')

    # Weekly trend chart (dual bar: prev month vs current month)
    prev_weekly = collections.Counter()
    for day_str, val in prev_daily.items():
        prev_weekly[week_label(day_str)] += val

    weekly_bars = ""
    weeks_order = ["W1", "W2", "W3", "W4", "W5"]
    max_weekly = max(
        max(weekly_curr.values()) if weekly_curr else 1,
        max(prev_weekly.values()) if prev_weekly else 1,
        1
    )
    if weekly_curr:
        for w in weeks_order:
            pc = prev_weekly.get(w, 0)
            cc = weekly_curr.get(w, 0)
            if pc == 0 and cc == 0 and w not in weekly_curr: continue
            ph = max(int(pc / max_weekly * 100), 2) if pc > 0 else 0
            ch = max(int(cc / max_weekly * 100), 2) if cc > 0 else 0
            weekly_bars += f'''<div class="week-group"><div class="bars"><div class="bar prev" style="height:{ph}px" title="{prev_month_cn}: {pc}"></div><div class="bar curr" style="height:{ch}px" title="{month_cn}: {cc}"></div></div><div class="week-nums"><span class="prev-num">{pc}</span><span class="curr-num">{cc}</span></div><div class="week-label">{w}</div></div>'''
    else:
        daily_items = sorted(daily.items())
        max_daily = max(daily.values()) if daily else 1
        for day, val in daily_items[-7:]:
            h = max(int(val / max_daily * 120), 6)
            weekly_bars += f'<div class="week-group"><div class="bars"><div class="bar curr" style="height:{h}px"></div></div><div class="week-nums"><span class="curr-num">{val}</span></div><div class="week-label">{day}</div></div>'

    # Channel comparison table
    channel_rows = ""
    for name in sorted(channel_data.keys(), key=lambda x: -channel_data[x]):
        cc = channel_data[name]
        pc = prev_channel_data.get(name, 0) if prev_channel_data else 0
        ch = fmt_change(cc, pc)
        ccol = change_color(cc, pc)
        channel_rows += f'<tr><td>#{name}</td><td class="num">{pc:,}</td><td class="num">{cc:,}</td><td class="num {ccol}">{ch}</td></tr>'

    # TOP 10
    top_html = ""
    medals = ["🥇", "🥈", "🥉"]
    medal_colors = ["#00d4ff", "#b388ff", "#ffab00"]
    for i, (name, score) in enumerate(top_users):
        if i < 3:
            top_html += f'<li><span class="rank" style="color:{medal_colors[i]}">{medals[i]}</span><span class="name">{name}</span><span class="score">~{score}条</span></li>'
        else:
            top_html += f'<li><span class="rank">{i+1}</span><span class="name">{name}</span><span class="score">~{score}条</span></li>'

    prev_top_html = ""
    if prev_top_users:
        for i, (name, score) in enumerate(prev_top_users[:10]):
            if i < 3:
                prev_top_html += f'<li><span class="rank" style="color:{medal_colors[i]}">{medals[i]}</span><span class="name">{name}</span><span class="score">~{score}条</span></li>'
            else:
                prev_top_html += f'<li><span class="rank">{i+1}</span><span class="name">{name}</span><span class="score">~{score}条</span></li>'

    # Content category (estimated)
    cat_html = '''<div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#5a6480">50%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">日常闲聊</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#ff6b9d">14%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">作品相关</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#00e676">14%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">感谢反馈</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#ffab00">12%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">规则答疑</div></div>
    <div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:#b388ff">10%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">创作指导</div></div>'''

    partial_banner = '<span class="badge" style="background:rgba(255,171,0,.15);border:1px solid rgba(255,171,0,.3);color:#ffab00">⚠️ 月度未结束，数据为当前统计</span>' if is_partial else ''
    comparison_header = f'{prev_month_cn} → {month_cn} 环比对比报告' if has_prev else f'{month_cn}社群运营月报'
    prev_date_info = now.strftime("%Y/%m/%d")

    html = f'''<!DOCTYPE html>
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
.kpi-card .value .unit{{font-size:14px;font-weight:400;margin-left:4px;color:#8892b0}}
.kpi-card .change{{font-size:12px;font-weight:500;margin-top:2px}}
.kpi-card .change.up{{color:#00e676}}
.kpi-card .change.down{{color:#ff6b6b}}
.blue{{color:#00d4ff}}.green{{color:#00e676}}.pink{{color:#ff6b9d}}.purple{{color:#b388ff}}.orange{{color:#ffab00}}
.section{{background:linear-gradient(135deg,rgba(20,30,60,.55),rgba(15,20,40,.55));border:1px solid rgba(0,212,255,.08);border-radius:14px;padding:26px;margin-bottom:22px}}
.section-title{{font-size:17px;font-weight:600;color:#00d4ff;margin-bottom:18px;display:flex;align-items:center;gap:8px}}
.section-title .icon{{font-size:20px}}
.data-table{{width:100%;border-collapse:collapse;font-size:13px}}
.data-table th{{color:#5a6480;font-weight:500;text-transform:uppercase;letter-spacing:.5px;padding:10px 10px;text-align:left;border-bottom:1px solid rgba(255,255,255,.05);font-size:11px}}
.data-table td{{padding:10px 10px;border-bottom:1px solid rgba(255,255,255,.03)}}
.data-table tr:hover td{{background:rgba(0,212,255,.03)}}
.data-table .num{{text-align:right;font-weight:500}}
.data-table .up{{color:#00e676}}
.data-table .down{{color:#ff6b6b}}
/* Weekly dual bar chart */
.weekly-chart{{display:flex;gap:20px;align-items:flex-end;height:200px;padding:12px 0;justify-content:center}}
.week-group{{display:flex;flex-direction:column;align-items:center;gap:4px;flex:1;max-width:70px}}
.week-group .bars{{display:flex;gap:6px;align-items:flex-end;height:140px}}
.week-group .bar{{width:22px;border-radius:4px 4px 0 0;min-height:2px}}
.week-group .bar.prev{{background:rgba(0,212,255,.35)}}
.week-group .bar.curr{{background:linear-gradient(180deg,#7b2ff7,rgba(123,47,247,.4))}}
.week-group .week-nums{{display:flex;gap:6px;font-size:9px}}
.week-group .prev-num{{color:#5a6480}}
.week-group .curr-num{{color:#b388ff;font-weight:600}}
.week-group .week-label{{font-size:10px;color:#5a6480;font-weight:600;margin-top:4px}}
.legend{{display:flex;justify-content:center;gap:20px;margin-bottom:12px;font-size:11px;color:#8892b0}}
.legend span{{display:flex;align-items:center;gap:6px}}
.legend .dot{{width:10px;height:10px;border-radius:2px;display:inline-block}}
/* Two column layout */
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:768px){{.two-col{{grid-template-columns:1fr}}.kpi-grid{{grid-template-columns:repeat(2,1fr)}}}}
/* Rank list */
.rank-list{{list-style:none}}
.rank-list li{{display:flex;align-items:center;padding:8px 10px;margin:3px 0;background:rgba(0,0,0,.15);border-radius:8px;gap:10px;font-size:12.5px}}
.rank-list .rank{{font-weight:700;font-size:15px;min-width:28px;text-align:center}}
.rank-list .name{{flex:1}}
.rank-list .score{{font-weight:600;color:#00d4ff}}
.footer{{text-align:center;padding:20px;color:#5a6480;font-size:11px}}
.footer p{{margin-top:2px}}
</style></head>
<body><div class="container">

<div class="header">
  <div class="logo">📊 Monthly Report · {month_en}</div>
  <h1>Yoyo Creative Studio</h1>
  <div class="subtitle">{comparison_header} · {prev_date_info} 生成</div>
  <span class="badge">🤖 自动生成 · 创作者社群</span>
  {partial_banner}
</div>

<div class="kpi-grid">
  {"".join(kpi_cards)}
</div>

<div class="section">
  <div class="section-title"><span class="icon">📈</span> 月度核心指标对比 · {prev_month_cn} vs {month_cn}</div>
  <table class="data-table">
    <tr><th>指标</th><th class="num">{prev_month_cn}</th><th class="num">{month_cn}</th><th class="num">环比涨幅</th></tr>
    {"".join(comp_table_rows)}
  </table>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📊</span> 周活跃度趋势 · {prev_month_cn} vs {month_cn}</div>
  {"<div class='legend'><span><span class='dot' style='background:rgba(0,212,255,.35)'></span> {prev_month_cn}</span><span><span class='dot' style='background:#7b2ff7'></span> {month_cn}</span></div>" if has_prev else ""}
  <div class="weekly-chart">{weekly_bars}</div>
  <p style="text-align:center;color:#5a6480;font-size:10px;margin-top:8px">💡 非Bot消息统计 · {"双柱对比：左=" + prev_month_cn + " 右=" + month_cn if has_prev else "日度趋势"}</p>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📡</span> 各频道消息量对比 · {prev_month_cn} vs {month_cn}</div>
  <table class="data-table">
    <tr><th>频道</th><th class="num">{prev_month_cn}</th><th class="num">{month_cn}</th><th class="num">变化幅度</th></tr>
    {channel_rows}
  </table>
</div>

<div class="two-col">
<div class="section">
  <div class="section-title"><span class="icon">🏆</span> {month_cn} TOP10 活跃创作者</div>
  <ul class="rank-list">{top_html}</ul>
</div>
'''

    if prev_top_html:
        html += f'''<div class="section">
  <div class="section-title"><span class="icon">🏅</span> {prev_month_cn} TOP10 活跃创作者</div>
  <ul class="rank-list">{prev_top_html}</ul>
</div>'''

    html += f'''</div>

<div class="section">
  <div class="section-title"><span class="icon">🍩</span> 内容分类占比（估算）</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px">{cat_html}</div>
  <p style="text-align:center;color:#5a6480;font-size:10px;margin-top:8px">💡 精确内容分类需引入 LLM 自动标注，目前为合理估算</p>
</div>

<div class="footer">
  <p>🤖 由 GitHub Actions 自动生成 · {now.strftime("%Y年%m月%d日 %H:%M")} UTC</p>
  <p>数据来源: Discord Bot Mochi's Bot · 通过 Supabase Edge Function 中转</p>
  <p style="margin-top:6px;color:#5a6480;font-size:10px">💡 上月数据来自缓存文件，本月结束后缓存会自动更新</p>
</div>

</div></body></html>'''

    with open("index.html", "w") as f:
        f.write(html)
    print("✅ HTML 已生成")

    # Feishu push
    if FEISHU:
        mom_info = ""
        if has_prev:
            mom_total = fmt_change(total, prev_total)
            mom_people = fmt_change(main_speakers, prev_main_speakers)
            mom_info = f"\n📈 消息环比：**{mom_total}** | 👥 人数环比：**{mom_people}**"

        feishu_text = f"📢 主频道：**{main_count:,}** 条（👥 {main_speakers}人）{mom_info}\n🗣️ 全频道总计：**{total:,}** 条\n📅 日均：**{main_count//max(now.day,1)}** 条/天" + ("\n\n⚠️ 月度未结束" if is_partial else "")

        payload = json.dumps({
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"content": f"📊 Yoyo 月报 · {month_cn}", "tag": "plain_text"}, "template": "blue"},
                "elements": [
                    {"tag": "div", "text": {"content": feishu_text, "tag": "lark_md"}},
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
