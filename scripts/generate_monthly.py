#!/usr/bin/env python3
"""Generate monthly community report with MoM comparison."""
import json, os, datetime, urllib.request, sys, collections, math
ARK_KEY = os.environ.get("ARK_API_KEY", "")

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

def fetch_samples(channel_id, month_start, max_samples=60):
    """Fetch message samples for ARK analysis. Returns list of strings."""
    samples = []
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
                author = m.get("author", {})
                if not author.get("bot"):
                    ct = m.get("content", "")[:250].strip()
                    if ct and len(ct) > 3:
                        uname = author.get("username", "?")
                        samples.append(f"[{uname}]: {ct}")
                        if len(samples) >= max_samples: return samples
            else: return samples
        before = msgs[-1]["id"]
    return samples

def arkanalyze_yoyo(messages):
    if not messages: return {"hot_discussions":[],"user_sentiment":"","pain_points":[],"highlights":[],"notable_quotes":[],"emerging_topics":"","keyword_cloud":[],"monthly_summary":"","mochi_mentions":"无","mochi_feedback":"无"}
    text="\n".join(f"{i+1}. {m}" for i,m in enumerate(messages[:80]))
    prompt=f"""你是游戏创作者社群（Yoyo Creative Studio）的运营分析师。仔细阅读以下本月 Discord 聊天记录。

社群背景：Yoyo Creative Studio 游戏 UGC 创作者社群。Mochi（摸鱼小助手）是运营助理 bot，负责积分统计、投稿管理、新人欢迎。对接运营人是 Mochi。

请深度分析：

1. **热议话题深层解读**：本月创作者在聊什么具体内容？有什么共识或争议？每个话题对社群意味着什么？
2. **创作者痛点**：具体抱怨什么游戏机制/流程/体验？不只是说"积分规则不清楚"，要说清楚哪里不清楚、谁在困惑、影响面多大。
3. **积分/投稿/奖励讨论**：有人反映积分统计不准吗？投稿流程是否顺畅？兑换奖励体验如何？
4. **新人体验与老创作者动态**：新人遇到什么困难？有没有老创作者沉默或流失的迹象？新人留存怎么样？
5. **社群氛围**：互助行为有哪些？有没有负面情绪扩散？创作者之间关系怎么样？
6. **Mochi 专项**：有没有人提到 Mochi 助手、摸鱼、bot？评价好不好？有没有功能吐槽或具体的改进建议？
7. **运营洞察**：Mochi 运营这个月最该关注什么？有什么风险信号或机会？

要求：每条分析具体、有细节、有判断。不只是总结表面内容，要挖掘背后的含义。

返回纯JSON（不要markdown代码块，不要省略）：
{{"hot_discussions":[{{"theme":"15字主题","detail":"100字以上：聊什么、不同观点、谁主导","buzz":"🔥高/📊中/💬一般"}}],"user_sentiment":"50字：正/负面占比%、趋势","pain_points":["每条50字：具体抱怨、影响"],"highlights":["每条30字：有趣事件"],"notable_quotes":["至少6条英文原文"],"emerging_topics":"新趋势","keyword_cloud":["10个高频词"],"monthly_summary":"200字以上，必须包含三段：【问题诊断】列出1-2个核心问题；【行动建议】给出2-3条可执行动作+预期效果；【路线图】本周→两周内→一个月内","mochi_mentions":"如果有人讨论Mochi/Bot/摸鱼：具体评价。如果没人讨论直接返回空字符串\"\"","mochi_feedback":"如有人提出Mochi功能建议/吐槽，摘录原话，否则写'无'}}

要求：每条具体有信息量，不泛泛而谈。中文分析，quotes 保留英文原文。

聊天记录：
{text}"""
    data=json.dumps({"model":"deepseek-v4-flash-260425","input":[{"role":"user","content":[{"type":"input_text","text":prompt}]}]}).encode()
    req=urllib.request.Request("https://ark.cn-beijing.volces.com/api/v3/responses",data=data,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {ARK_KEY}"})
    resp=json.loads(urllib.request.urlopen(req,timeout=120).read())
    for item in resp.get("output",[]):
        if item.get("type")=="message":
            for c in item.get("content",[]):
                if c.get("type")=="output_text":
                    try:
                        raw=c.get("text","").strip()
                        for fence in ["```json","```"]: raw=raw.replace(fence,"")
                        return json.loads(raw)
                    except: return {"hot_discussions":[],"user_sentiment":c.get("text","")[:200],"pain_points":[],"highlights":[],"notable_quotes":[],"emerging_topics":"","keyword_cloud":[],"monthly_summary":"","mochi_mentions":"无","mochi_feedback":"无"}
    return {"hot_discussions":[],"user_sentiment":"分析失败","pain_points":[],"highlights":[],"notable_quotes":[],"emerging_topics":"","keyword_cloud":[],"monthly_summary":"","mochi_mentions":"无","mochi_feedback":"无"}

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

    # Collect samples for ARK analysis
    print("📝 采集消息样本...")
    all_samples = fetch_samples(CH_MAIN, month_start, 60)
    # Also grab a few from active sub-channels
    for name, ch_id in ALL_CHANNELS.items():
        if ch_id == CH_MAIN: continue
        if channel_data.get(name, 0) > 10:
            more = fetch_samples(ch_id, month_start, 10)
            all_samples.extend(more)
    print(f"  ✅ 共采集 {len(all_samples)} 条样本")

    # ARK Analysis
    if ARK_KEY and all_samples:
        print("🤖 ARK 话题分析...")
        analysis = arkanalyze_yoyo(all_samples)
        topics_list = [d.get('theme','') for d in analysis.get('hot_discussions',[])]
        print(f"  🔥 话题: {', '.join(topics_list[:5])}")
        print(f"  💬 情绪: {analysis.get('user_sentiment','?')[:80]}")
        print(f"  🤖 Mochi讨论: {analysis.get('mochi_mentions','')[:80]}")
        print(f"  ⚠️ 痛点: {', '.join(analysis.get('pain_points',[])[:3])}")
    else:
        analysis = {}
        if not ARK_KEY: print("⚠️ 未设置 ARK_API_KEY，跳过分析")


    # Second ARK call: strategic decision analysis (separate, simpler prompt)
    if ARK_KEY and all_samples:
        print("\n🧠 第二轮 ARK: 运营决策分析...")
        strat_prompt = "你是游戏创作者社群的运营分析师。基于本月聊天数据，用中文写一个200字以上的月度运营总结，必须包含三段：\n\n【问题诊断】列出1-2个核心问题及影响\n【行动建议】给出2-3条可执行动作+预期效果\n【路线图】本周做什么→两周内做什么→一个月内达成什么\n\n聊天数据：\n" + "\n".join(all_samples[:40])
        strat_data = json.dumps({"model":"deepseek-v4-flash-260425","input":[{"role":"user","content":[{"type":"input_text","text":strat_prompt}]}]}).encode()
        strat_req = urllib.request.Request("https://ark.cn-beijing.volces.com/api/v3/responses",data=strat_data,headers={"Content-Type":"application/json","Authorization":f"Bearer {ARK_KEY}"})
        try:
            strat_resp = json.loads(urllib.request.urlopen(strat_req,timeout=60).read())
            for item in strat_resp.get("output",[]):
                if item.get("type")=="message":
                    for c in item.get("content",[]):
                        if c.get("type")=="output_text":
                            strat_text = c.get("text","").strip()
                            # Extract content between ** markers or use as-is
                            if "【问题诊断】" in strat_text or "【行动建议】" in strat_text:
                                analysis["monthly_summary"] = strat_text
                                print(f"  ✅ 运营分析已生成 ({len(strat_text)}字)")
                            else:
                                print(f"  ⚠️ 格式不符，尝试备用解析...")
                                analysis["monthly_summary"] = strat_text[:500]
        except Exception as e:
            print(f"  ⚠️ 运营分析失败: {e}")
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


    # Build ARK analysis HTML blocks
    analysis_html = ""
    if True:  # was: if analysis:
        disc_cards = ""
        buzz_bg = {"🔥高":"rgba(255,107,107,.1)","📊中":"rgba(255,171,0,.1)","💬一般":"rgba(100,100,255,.1)"}
        buzz_bd = {"🔥高":"rgba(255,107,107,.25)","📊中":"rgba(255,171,0,.25)","💬一般":"rgba(100,100,255,.15)"}
        for d in analysis.get("hot_discussions",[]):
            bg = buzz_bg.get(d.get("buzz",""),"rgba(255,255,255,.05)")
            bd = buzz_bd.get(d.get("buzz",""),"rgba(255,255,255,.1)")
            disc_cards += f'<div class="disc-card" style="border-color:{bd};background:{bg}"><div class="disc-header"><span class="buzz-badge">{d.get("buzz","")}</span> {d.get("theme","")}</div><div class="disc-body">{d.get("detail","")}</div></div>'
        pain_html = "".join(f'<li class="pain-item">⚠️ {p}</li>' for p in analysis.get("pain_points",[]))
        high_html = "".join(f'<li class="highlight-item">✨ {h}</li>' for h in analysis.get("highlights",[]))
        quotes_html = "".join(f'<div class="quote-card">「{q}」</div>' for q in analysis.get("notable_quotes",[]))
        kw_html = ""
        if analysis.get("keyword_cloud"):
            tags = " ".join(f'<span class="tag kw">{w}</span>' for w in analysis["keyword_cloud"])
            kw_html = f'<div class="section"><div class="section-title"><span class="icon">🏷️</span> 高频关键词</div><div class="tags-area">{tags}</div></div>'
        analysis_html = ""

        # Hot discussion cards
        disc_cards = ""
        buzz_bg = {"🔥高":"rgba(255,107,107,.1)","📊中":"rgba(255,171,0,.1)","💬一般":"rgba(100,100,255,.1)"}
        buzz_bd = {"🔥高":"rgba(255,107,107,.25)","📊中":"rgba(255,171,0,.25)","💬一般":"rgba(100,100,255,.15)"}
        for d in analysis.get("hot_discussions",[]):
            bg = buzz_bg.get(d.get("buzz",""),"rgba(255,255,255,.05)")
            bd = buzz_bd.get(d.get("buzz",""),"rgba(255,255,255,.1)")
            disc_cards += f'<div class="disc-card" style="border-color:{bd};background:{bg}"><div class="disc-header"><span class="buzz-badge">{d.get("buzz","")}</span> {d.get("theme","")}</div><div class="disc-body">{d.get("detail","")}</div></div>'
        disc_fallback = disc_cards if disc_cards else '<p style="color:#5a6480">暂无数据</p>'

        pain_html = "".join(f'<li class="pain-item">⚠️ {p}</li>' for p in analysis.get("pain_points",[]))
        pain_fallback = pain_html if pain_html else '<li style="color:#5a6480">暂无</li>'

        high_html = "".join(f'<li class="highlight-item">✨ {h}</li>' for h in analysis.get("highlights",[]))
        high_fallback = high_html if high_html else '<li style="color:#5a6480">暂无</li>'

        quotes_html = "".join(f'<div class="quote-card">「{q}」</div>' for q in analysis.get("notable_quotes",[]))
        quotes_fallback = quotes_html if quotes_html else '<p style="color:#5a6480">暂无</p>'

        emerging_html = f'<div style="margin-top:12px;padding:10px;background:rgba(0,212,255,.05);border-radius:8px;font-size:12px;color:#8892b0">🔮 新趋势：{analysis.get("emerging_topics","")}</div>' if analysis.get("emerging_topics") else ""

        kw_html = ""
        if analysis.get("keyword_cloud"):
            tags = " ".join(f'<span class="tag kw">{w}</span>' for w in analysis["keyword_cloud"])
            kw_html = f'<div class="section"><div class="section-title"><span class="icon">🏷️</span> 高频关键词</div><div class="tags-area">{tags}</div></div>'

        analysis_html = f'''
<div class="section">
  <div class="section-title"><span class="icon">🤖</span> LLM 舆情分析 · {month_cn}</div>
  <div class="section-title" style="font-size:14px;color:#b388ff;margin-bottom:10px"><span class="icon">🔥</span> 热议话题</div>
  {disc_fallback}
  <div style="margin-top:16px">
    <div class="two-col" style="margin-top:12px">
      <div>
        <div class="section-title" style="font-size:14px;color:#ff6b6b"><span class="icon">⚠️</span> 关注痛点</div>
        <ul class="pain-list">{pain_fallback}</ul>
      </div>
      <div>
        <div class="section-title" style="font-size:14px;color:#00e676"><span class="icon">✨</span> 本月亮点</div>
        <ul class="highlight-list">{high_fallback}</ul>
      </div>
    </div>
  </div>
  <div style="margin-top:16px">
    <div class="section-title" style="font-size:14px;color:#00d4ff"><span class="icon">💬</span> 代表发言</div>
    <div class="quotes-area">{quotes_fallback}</div>
  </div>
  {emerging_html}
</div>
'''
        if analysis.get("mochi_mentions"):
            mochi_extra = f'<div style="margin-top:12px;padding:10px;background:rgba(255,171,0,.05);border-radius:8px;font-size:12px;color:#ffab00">💬 具体评价：{analysis.get("mochi_feedback","")}</div>' if analysis.get("mochi_feedback") and analysis.get("mochi_feedback") != "无" else ""
            mochi_ment = analysis.get("mochi_mentions","")
            mochi_extra = ""
            fb = analysis.get("mochi_feedback","")
            if fb and fb != "无":
                mochi_extra = f'<div style="margin-top:12px;padding:10px;background:rgba(255,171,0,.05);border-radius:8px;font-size:12px;color:#ffab00">💬 具体评价：{fb}</div>'
            analysis_html += f'<div class="section"><div class="section-title"><span class="icon">🤖</span> Mochi 小助手 · 创作者反馈</div><p style="color:#e0e6f0;font-size:14px;line-height:1.8">{mochi_ment}</p>{mochi_extra}</div>'
        analysis_html += kw_html
        if analysis.get("monthly_summary"):
            summary = analysis.get("monthly_summary","")
            # Render structured summary with sections
            parts = {"问题诊断":"","行动建议":"","路线图":""}
            current_key = None
            for line in summary.split(chr(10)):
                for key in parts:
                    if f"【{key}】" in line:
                        current_key = key
                        line = line.split(f"【{key}】")[-1]
                        break
                if current_key:
                    parts[current_key] += line + chr(10)
            strategic_html = '<div class="section"><div class="section-title"><span class="icon">🧠</span> 问题诊断 & 行动计划</div>'
            # Strip markdown formatting from content
            for k in parts:
                parts[k] = parts[k].replace("**", "").replace("#", "")
            if parts["问题诊断"].strip():
                strategic_html += '<div style="margin-bottom:16px"><div style="font-size:14px;color:#ff6b6b;font-weight:600;margin-bottom:8px">🔍 问题诊断</div><div style="font-size:13px;color:#e0e6f0;line-height:1.8;background:rgba(255,107,107,.06);border-left:3px solid rgba(255,107,107,.5);padding:12px 16px;border-radius:0 8px 8px 0;white-space:pre-line">' + parts["问题诊断"].strip() + '</div></div>'
            if parts["行动建议"].strip():
                strategic_html += '<div style="margin-bottom:16px"><div style="font-size:14px;color:#00e676;font-weight:600;margin-bottom:8px">✅ 行动方案</div><div style="font-size:13px;color:#e0e6f0;line-height:1.8;background:rgba(0,230,118,.06);border-left:3px solid rgba(0,230,118,.5);padding:12px 16px;border-radius:0 8px 8px 0;white-space:pre-line">' + parts["行动建议"].strip() + '</div></div>'
            if parts["路线图"].strip():
                strategic_html += '<div style="margin-bottom:16px"><div style="font-size:14px;color:#ffab00;font-weight:600;margin-bottom:8px">📅 路线图</div><div style="font-size:13px;color:#e0e6f0;line-height:1.8;background:rgba(255,171,0,.06);border-left:3px solid rgba(255,171,0,.5);padding:12px 16px;border-radius:0 8px 8px 0;white-space:pre-line">' + parts["路线图"].strip() + '</div></div>'
            strategic_html += '</div>'
            analysis_html += strategic_html

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
.disc-card{{border:1px solid;border-radius:10px;padding:14px 18px;margin-bottom:10px}}
.disc-header{{font-weight:600;font-size:14px;margin-bottom:6px;color:#e0e6f0}}
.disc-body{{font-size:12.5px;color:#8892b0;line-height:1.6}}
.buzz-badge{{font-size:10px;margin-right:6px}}
.pain-list,.highlight-list{{list-style:none;padding:0}}
.pain-item,.highlight-item{{padding:6px 10px;margin:4px 0;background:rgba(0,0,0,.15);border-radius:6px;font-size:12.5px;color:#e0e6f0}}
.pain-item{{border-left:3px solid rgba(255,107,107,.5)}}
.highlight-item{{border-left:3px solid rgba(0,230,118,.5)}}
.quotes-area{{display:flex;flex-wrap:wrap;gap:8px}}
.quote-card{{background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.12);border-radius:8px;padding:10px 14px;font-size:12px;color:#c0c8d8;font-style:italic;flex:1;min-width:200px}}
.tags-area{{line-height:2.2}}
.tag.kw{{display:inline-block;background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.2);border-radius:6px;padding:2px 10px;font-size:10px;color:#00d4ff;margin:2px 4px}}
</style></head>
<body><div class="container">

<div class="header">
  <div style="display:inline-block;background:#7b2ff7;color:#fff;padding:6px 20px;border-radius:20px;font-size:14px;font-weight:700;letter-spacing:2px;margin-bottom:12px">📊 月 报</div>
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

{analysis_html}
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

    with open("monthly.html", "w") as f:
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

        if analysis:
            sent = analysis.get('user_sentiment','')
            topics = [d.get('theme','') for d in analysis.get('hot_discussions',[])]
            pains = [p[:50] for p in analysis.get('pain_points',[])][:2]
            highlights = [h[:30] for h in analysis.get('highlights',[])][:2]
            mochi = analysis.get('mochi_mentions','')
            feishu_text += f"\n\n🤖 **LLM 舆情分析**\n🔥 热议：{'、'.join(topics[:3])}\n💬 情绪：{sent[:100]}"
            if pains: feishu_text += f"\n⚠️ 痛点：{'；'.join(pains)}"
            if highlights: feishu_text += f"\n🌟 亮点：{'；'.join(highlights)}"
            skip_m = ["暂无","未出现","未提及","没有提到","没有发现","未发现","无相关","未参与","没有相关","无相关讨论","未被提及","不涉及","没有讨论","0条","无讨论"]
            if mochi and not any(w in mochi for w in skip_m):
                feishu_text += f"\n🤖 Mochi反馈：{mochi[:120]}"

        payload = json.dumps({
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"content": f"📊 Yoyo Creative Studio 月报 · {month_cn}", "tag": "plain_text"}, "template": "blue"},
                "elements": [
                    {"tag": "div", "text": {"content": feishu_text, "tag": "lark_md"}},
                    {"tag": "action", "actions": [{"tag": "button", "text": {"content": "📊 查看完整月报", "tag": "plain_text"}, "url": "https://jiashi65.github.io/yoyo-community-report/monthly.html", "type": "primary"}]}
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