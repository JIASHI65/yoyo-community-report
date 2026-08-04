#!/usr/bin/env python3
"""Yoyo Creative Studio Weekly Report: Discord data + ARK deep analysis + Mochi tracking."""
import json, os, datetime, urllib.request, collections, sys

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
ARK_KEY = os.environ.get("ARK_API_KEY", "")
FEISHU = os.environ.get("FEISHU_WEEKLY_WEBHOOK", os.environ.get("FEISHU_WEBHOOK", ""))
SUPABASE_URL = "https://rryzofimrehmkijkckrm.supabase.co"
SUPABASE_KEY = "sb_publishable_oyewqnQ8AnitAOD94Qg0nA_v6Zqkr7r"
CACHE_FILE = "weekly_cache.json"

CHANNELS = {
    "creators-exchange": "1458349180748828757",
    "bulletin-board": "1458347958389965035",
    "refer-a-friend": "1518810024015695984",
    "creator-tier-system": "1518810441961177241",
    "official-inspirations": "1458348802397442149",
    "rules-faq": "1519180265396637776",
    "show-pet": "1529062536404795443",
    "show-merch": "1529063019349545021",
}

def fetch(channel_id, before=None):
    data = json.dumps({"action":"list_messages","data":{"channel_id":channel_id,"limit":100,"before":before} if before else {"channel_id":channel_id,"limit":100},"token":TOKEN}).encode()
    req = urllib.request.Request(f"{SUPABASE_URL}/functions/v1/discord-proxy",data=data,headers={"Content-Type":"application/json","Authorization":f"Bearer {SUPABASE_KEY}"})
    return json.loads(urllib.request.urlopen(req,timeout=15).read())

def count_week_full(channel_id):
    """Count + daily breakdown + user ranking + samples."""
    count, speakers, daily, user_counts, samples = 0, set(), collections.Counter(), collections.Counter(), []
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    before = None
    for _ in range(60):
        try: msgs = fetch(channel_id, before)
        except: break
        if not msgs or not isinstance(msgs, list): break
        for m in msgs:
            ts = m.get("timestamp","")
            if not ts: continue
            dt = datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
            if dt >= cutoff:
                author = m.get("author",{})
                if not author.get("bot"):
                    count += 1
                    uid = author.get("id","")
                    uname = author.get("username","?")
                    speakers.add(uid)
                    daily[dt.strftime("%m-%d")] += 1
                    user_counts[uname] += 1
                    ct = m.get("content","")[:250].strip()
                    if ct and len(ct) > 3:
                        samples.append(f"[{uname}]: {ct}")
            else: return count, speakers, daily, user_counts, smart_sample(samples)
        before = msgs[-1]["id"]
    return count, speakers, daily, user_counts, smart_sample(samples)

def quick_count(channel_id):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    count, before = 0, None
    for _ in range(30):
        try: msgs = fetch(channel_id, before)
        except: break
        if not msgs or not isinstance(msgs, list): break
        for m in msgs:
            ts = m.get("timestamp","")
            if not ts: continue
            dt = datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
            if dt >= cutoff:
                if not m.get("author",{}).get("bot"): count += 1
            else: return count
        before = msgs[-1]["id"]
    return count

def fetch_samples(channel_id, max_n=10):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    samples, before = [], None
    for _ in range(20):
        try: msgs = fetch(channel_id, before)
        except: break
        if not msgs or not isinstance(msgs, list): break
        for m in msgs:
            ts = m.get("timestamp","")
            if not ts: continue
            dt = datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
            if dt >= cutoff:
                if not m.get("author",{}).get("bot"):
                    ct = m.get("content","")[:250].strip()
                    uname = m.get("author",{}).get("username","?")
                    if ct and len(ct) > 3:
                        samples.append(f"[{uname}]: {ct}")
            else: return smart_sample(samples, max_n)
        before = msgs[-1]["id"]
    return smart_sample(samples, max_n)

def arkanalyze(messages):
    meaningful = [m for m in messages if len(m.strip()) > 5]
    if not meaningful: return {"hot_discussions":[],"user_sentiment":"","pain_points":[],"highlights":[],"notable_quotes":[],"emerging_topics":"","content_categories":[{{"category":"分类名(如作品分享/问题咨询/正向反馈/闲聊/游戏设计讨论)","pct":整数百分比}}],
    "content_categories":[],"keyword_cloud":[],"weekly_summary":"","mochi_mentions":"无","mochi_feedback":"无"}
    text = "\n".join(f"{i+1}. {m}" for i,m in enumerate(meaningful[:80]))
    prompt = f"""你是 Yoyo Creative Studio 游戏创作者社群的运营分析师。仔细阅读本周 Discord 聊天记录。

社群背景：这是一个游戏 UGC 创作者社群。Mochi（摸鱼小助手）是运营助理 bot，负责积分统计、投稿管理、新人欢迎。运营对接人是 Mochi。

请深度分析（周报数据少，每条消息都要深挖）：

1. **热议话题深层解读**：具体聊什么内容？有什么分歧或共识？这个话题为什么重要？谁在主导讨论？对社群有什么潜在影响？
2. **创作者痛点**：具体抱怨什么游戏机制、流程、体验？不只是说积分规则不清楚，要说清楚哪里不清楚、影响了谁、有多严重。
3. **积分/投稿/奖励讨论**：有人问积分怎么算吗？有人吐槽投稿流程吗？有人反映兑换体验吗？
4. **新人体验**：新来的创作者遇到什么困难？有没有被帮助？有没有沉默或流失的迹象？
5. **社群氛围**：互助行为有哪些？有没有矛盾？氛围向上还是向下？
6. **Mochi 专项**：有没有人提到 Mochi 助手、摸鱼、bot？评价是什么？有没有功能吐槽或建议？
7. **运营洞察**：你觉得这批数据里，Mochi 运营最该关注什么？

不要泛泛而谈。每条分析都要有具体细节、具体人名（如果有）、具体场景。不只是统计，要有判断和洞察。

返回纯JSON（不要markdown代码块）：
{{"hot_discussions":[{{"theme":"12字主题","detail":"120字以上深度分析：聊什么、谁在说、不同观点、潜在影响","buzz":"🔥高/📊中/💬一般","participants":"几个人参与"}}],"user_sentiment":"80字：正/负面各占%、具体情绪关键词、与上周相比的变化","pain_points":["每条80字：具体抱怨什么游戏机制/流程、影响多大、有没有解决方案被提出"],"highlights":["每条40字：有趣事件、谁参与、社区反响"],"notable_quotes":["至少6条英文原文、选最有代表性的"],"emerging_topics":"40字：新趋势","keyword_cloud":["12个高频关键词"],"weekly_summary":"100字：本周一句话总结+值得关注的信号+建议运营动作","mochi_mentions":"如果有人讨论Mochi/Bot/摸鱼：具体评价和吐槽。如果没人讨论直接返回空字符串\"\"","mochi_feedback":"如有具体吐槽/建议摘录原话，否则返回空字符串\"\""}}

要求：具体、有数据感、运营视角。中文分析，quotes保留英文。

聊天记录：
{text}"""
    data = json.dumps({"model":"deepseek-v4-flash-260425","input":[{"role":"user","content":[{"type":"input_text","text":prompt}]}]}).encode()
    req = urllib.request.Request("https://ark.cn-beijing.volces.com/api/v3/responses",data=data,headers={"Content-Type":"application/json","Authorization":f"Bearer {ARK_KEY}"})
    resp = json.loads(urllib.request.urlopen(req,timeout=120).read())
    for item in resp.get("output",[]):
        if item.get("type") == "message":
            for c in item.get("content",[]):
                if c.get("type") == "output_text":
                    try:
                        raw = c.get("text","").strip()
                        for fence in ["```json","```"]: raw = raw.replace(fence,"")
                        return json.loads(raw)
                    except: return {"hot_discussions":[],"user_sentiment":c.get("text","")[:200],"pain_points":[],"highlights":[],"notable_quotes":[],"emerging_topics":"","content_categories":[],"keyword_cloud":[],"weekly_summary":"","mochi_mentions":"无","mochi_feedback":"无"}
    return {"hot_discussions":[],"user_sentiment":"分析失败","pain_points":[],"highlights":[],"notable_quotes":[],"emerging_topics":"","content_categories":[],"keyword_cloud":[],"weekly_summary":"","mochi_mentions":"无","mochi_feedback":"无"}

def fmt_change(c,p):
    if p==0 and c==0: return "-"
    if p==0: return "新增"
    pct = (c-p)/p*100
    return f"{'+'if pct>=0 else''}{pct:.0f}%"

def score_message(content):
    """Score message by discussion value: longer + questions + links = more valuable."""
    score = len(content)  # base: length
    score += content.count("?") * 10  # questions = discussion value
    score += content.count("http") * 15  # links = content sharing
    score += content.count("@") * 5  # mentions = conversation
    # Reward messages between 100-250 chars (substantive but not spam)
    if 80 < len(content) < 300:
        score *= 1.2
    return int(score)

def smart_sample(samples, n=40):
    """Select the n most discussion-worthy messages from samples."""
    if len(samples) <= n:
        return samples
    scored = [(score_message(s), s) for s in samples]
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:n]]

def main():
    if not TOKEN:
        print("❌ DISCORD_BOT_TOKEN not set"); return
    now = datetime.datetime.now(datetime.timezone.utc)
    week_start = now - datetime.timedelta(days=7)
    week_label = f"{week_start.strftime('%m/%d')}-{now.strftime('%m/%d')}"
    week_key = now.strftime("W%U")
    print(f"📊 Yoyo Creative Studio 周报 · {week_label}")

    # Step 1: Main channel full data
    print("📡 采集 creators-exchange...")
    mc, main_speakers, daily, user_rank, samples = count_week_full(CHANNELS["creators-exchange"])
    mc_speakers = len(main_speakers)
    top_users = user_rank.most_common(10)
    print(f"  ✅ {mc}条 ({mc_speakers}人) | 样本{len(samples)}条")

    # Step 2: Other channels
    chan_data = {}
    all_samples = list(samples[:30])
    for name, cid in CHANNELS.items():
        if name == "creators-exchange":
            chan_data[name] = mc
            continue
        c = quick_count(cid)
        chan_data[name] = c
        if c > 5:
            more = fetch_samples(cid, 8)
            all_samples.extend(more)
            print(f"  📡 #{name}: {c}条 (+{len(more)}样本)")
        else:
            print(f"  📡 #{name}: {c}条")

    total = sum(chan_data.values())
    active_chan = sum(1 for c in chan_data.values() if c > 0)
    daily_avg = total // 7
    print(f"\n📊 总计: {total}条 | 日均{daily_avg}条 | {active_chan}/{len(CHANNELS)}频道活跃")

    # Step 3: Load cache for WoW comparison
    cache = {}
    try:
        with open(CACHE_FILE) as f: cache = json.load(f)
    except: pass
    prev_week = cache.get("weeks",[])[-1] if cache.get("weeks") else None
    prev_total = prev_week.get("total",0) if prev_week else 0
    prev_speakers = set(prev_week.get("speakers_chat",[])) if prev_week else set()
    new_speakers = main_speakers - prev_speakers
    returning = main_speakers & prev_speakers

    # Step 4: ARK Analysis
    analysis = {}
    if ARK_KEY and all_samples:
        print(f"\n🤖 ARK 深度分析... (样本{len(all_samples)}条, {sum(len(m) for m in all_samples)}字符)")
        analysis = arkanalyze(all_samples)
        topics_list = [d.get('theme','') for d in analysis.get('hot_discussions',[])]
        print(f"  🔥 话题: {', '.join(topics_list[:5])}")
        print(f"  💬 情绪: {analysis.get('user_sentiment','?')[:100]}")
        print(f"  🤖 Mochi: {analysis.get('mochi_mentions','?')[:80]}")
        print(f"  ⚠️ 痛点: {', '.join(analysis.get('pain_points',[])[:3])}")
    else:
        if not ARK_KEY: print("⚠️ 未设置 ARK_API_KEY，跳过分析")

    # Step 4.5: Second ARK call - problem diagnosis & action plan
    if ARK_KEY and all_samples:
        print("\n🧠 第二轮 ARK: 运营分析...")
        strat_prompt = "你是游戏创作者社群的运营分析师。基于本周聊天数据，用中文写一个200字以上的运营总结，必须包含三段：\n\n【问题诊断】列出1-2个核心问题及影响\n【行动建议】给出2-3条可执行动作+预期效果\n【路线图】本周做什么→两周内做什么→一个月内达成什么\n\n聊天数据：\n" + "\n".join(all_samples[:40])
        strat_data = json.dumps({"model":"deepseek-v4-flash-260425","input":[{"role":"user","content":[{"type":"input_text","text":strat_prompt}]}]}).encode()
        strat_req = urllib.request.Request("https://ark.cn-beijing.volces.com/api/v3/responses",data=strat_data,headers={"Content-Type":"application/json","Authorization":f"Bearer {ARK_KEY}"})
        try:
            strat_resp = json.loads(urllib.request.urlopen(strat_req,timeout=60).read())
            for item in strat_resp.get("output",[]):
                if item.get("type")=="message":
                    for c in item.get("content",[]):
                        if c.get("type")=="output_text":
                            strat_text = c.get("text","").strip()
                            if "【问题诊断】" in strat_text or "【行动建议】" in strat_text:
                                analysis["monthly_summary"] = strat_text
                                print(f"  ✅ 运营分析已生成 ({len(strat_text)}字)")
                            else:
                                analysis["monthly_summary"] = strat_text[:500]
        except Exception as e:
            print(f"  ⚠️ 运营分析失败: {e}")

    # Step 5: Build HTML
    print("\n🌐 生成 HTML...")

    # Daily chart
    daily_items = sorted(daily.items())
    max_d = max(daily.values()) if daily else 1
    daily_bars = ""
    for day, val in daily_items[-7:]:
        h = max(int(val/max_d*120),4)
        daily_bars += f'<div class="daily-bar"><div class="bar" style="height:{h}px"></div><div class="val-label">{val}</div><div class="day-label">{day.split("-")[-1]}日</div></div>'

    # Channel table
    chan_rows = ""
    for name in sorted(chan_data.keys(), key=lambda x: -chan_data[x]):
        c = chan_data[name]
        icon = "🔥" if c > 100 else "📊" if c > 20 else "💤" if c > 0 else "⛔"
        chan_rows += f'<tr class="{"dim" if c==0 else ""}"><td>{icon} #{name}</td><td class="num">{c:,}</td></tr>'

    # TOP 10
    medals = ["🥇","🥈","🥉"]; medal_c = ["#00d4ff","#b388ff","#ffab00"]
    top_html = ""
    for i,(name,score) in enumerate(top_users):
        if i < 3:
            top_html += f'<li><span class="rank" style="color:{medal_c[i]}">{medals[i]}</span><span class="name">{name}</span><span class="score">~{score}条</span></li>'
        else:
            top_html += f'<li><span class="rank">{i+1}</span><span class="name">{name}</span><span class="score">~{score}条</span></li>'

    # Analysis HTML blocks
    analysis_html = ""
    if analysis:
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

        disc_fb = disc_cards if disc_cards else '<p style="color:#5a6480">暂无数据</p>'
        pain_fb = pain_html if pain_html else '<li style="color:#5a6480">本周无特别痛点</li>'
        high_fb = high_html if high_html else '<li style="color:#5a6480">暂无</li>'
        quotes_fb = quotes_html if quotes_html else '<p style="color:#5a6480">暂无</p>'
        emerging = f'<div style="margin-top:12px;padding:10px;background:rgba(0,212,255,.05);border-radius:8px;font-size:12px;color:#8892b0">🔮 新趋势：{analysis.get("emerging_topics","")}</div>' if analysis.get("emerging_topics") else ""

        analysis_html = f'''
<div class="section">
  <div class="section-title"><span class="icon">🤖</span> LLM 深度分析 · 本周</div>
  <div class="section-title" style="font-size:14px;color:#b388ff;margin-bottom:10px"><span class="icon">🔥</span> 热议话题</div>
  {disc_fb}
  <div style="margin-top:16px">
    <div class="two-col" style="margin-top:12px">
      <div>
        <div class="section-title" style="font-size:14px;color:#ff6b6b"><span class="icon">⚠️</span> 关注痛点</div>
        <ul class="pain-list">{pain_fb}</ul>
      </div>
      <div>
        <div class="section-title" style="font-size:14px;color:#00e676"><span class="icon">✨</span> 本周亮点</div>
        <ul class="highlight-list">{high_fb}</ul>
      </div>
    </div>
  </div>
  <div style="margin-top:16px">
    <div class="section-title" style="font-size:14px;color:#00d4ff"><span class="icon">💬</span> 代表发言</div>
    <div class="quotes-area">{quotes_fb}</div>
  </div>
  {emerging}
</div>
'''
        mochi_txt = analysis.get("mochi_mentions","")
        skip_words = ["暂无","未出现","未提及","没有提到","没有发现","未发现","无相关"]
        has_mochi = mochi_txt and not any(w in mochi_txt for w in skip_words)
        if has_mochi:
            fb = analysis.get("mochi_feedback","")
            extra = f'<div style="margin-top:12px;padding:10px;background:rgba(255,171,0,.05);border-radius:8px;font-size:12px;color:#ffab00">💬 具体评价：{fb}</div>' if fb and fb != "无" else ""
            analysis_html += f'<div class="section"><div class="section-title"><span class="icon">🤖</span> Mochi 小助手 · 创作者反馈</div><p style="color:#e0e6f0;font-size:14px;line-height:1.8">{analysis.get("mochi_mentions","")}</p>{extra}</div>'

        analysis_html += kw_html
        if analysis.get("weekly_summary"):
            analysis_html += f'<div class="section"><div class="section-title"><span class="icon">📝</span> 本周运营总结</div><p style="color:#e0e6f0;font-size:14px;line-height:1.8">{analysis.get("weekly_summary","")}</p></div>'
        # Problem diagnosis & action plan section
        if analysis.get("monthly_summary"):
            summary = analysis.get("monthly_summary","")
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
            for k in parts:
                parts[k] = parts[k].replace("**", "").replace("#", "")
            if parts["问题诊断"].strip():
                analysis_html += '<div class="section"><div class="section-title"><span class="icon">🔍</span> 问题诊断 & 行动计划</div><div style="margin-bottom:20px"><div style="font-size:15px;color:#ff6b6b;font-weight:600;margin-bottom:10px">🔍 问题诊断</div><div style="font-size:13px;color:#c0c8d8;line-height:1.9;background:linear-gradient(135deg,rgba(255,107,107,.08),rgba(255,107,107,.02));border:1px solid rgba(255,107,107,.15);border-radius:12px;padding:16px 20px;white-space:pre-line">' + parts["问题诊断"].strip() + '</div></div>'
            if parts["行动建议"].strip():
                analysis_html += '<div style="margin-bottom:20px"><div style="font-size:15px;color:#00e676;font-weight:600;margin-bottom:10px">✅ 行动方案</div><div style="font-size:13px;color:#c0c8d8;line-height:1.9;background:linear-gradient(135deg,rgba(0,230,118,.08),rgba(0,230,118,.02));border:1px solid rgba(0,230,118,.15);border-radius:12px;padding:16px 20px;white-space:pre-line">' + parts["行动建议"].strip() + '</div></div>'
            if parts["路线图"].strip():
                analysis_html += '<div style="margin-bottom:20px"><div style="font-size:15px;color:#ffab00;font-weight:600;margin-bottom:10px">📅 路线图</div><div style="font-size:13px;color:#c0c8d8;line-height:1.9;background:linear-gradient(135deg,rgba(255,171,0,.08),rgba(255,171,0,.02));border:1px solid rgba(255,171,0,.15);border-radius:12px;padding:16px 20px;white-space:pre-line">' + parts["路线图"].strip() + '</div></div>'
            analysis_html += '</div>'

    # Alert for activity drop
    alert_html = ""
    if prev_total > 0:
        drop_pct = (total - prev_total) / prev_total * 100
        if drop_pct < -30:
            alert_html = f'<div class="alert">🚨 活跃度突降：本周较上周下跌 {abs(int(drop_pct))}%</div>'
        elif drop_pct > 50:
            alert_html = f'<div class="alert" style="border-color:rgba(0,230,118,.3);color:#00e676">📈 活跃度大幅上升 {int(drop_pct)}%</div>'

    wow_change = fmt_change(total, prev_total)
    wow_class = "up" if total >= prev_total else "down"

    # LLM content categories
    cat_html = ""
    if analysis.get("content_categories"):
        colors = ["#ff6b9d","#00e676","#ffab00","#b388ff","#00d4ff","#5a6480"]
        for i, c in enumerate(analysis["content_categories"]):
            color = colors[i % len(colors)]
            cat_html += f'<div style="background:rgba(0,0,0,.15);border-radius:10px;padding:14px;text-align:center"><div style="font-size:28px;font-weight:700;color:{color}">{c.get("pct",0)}%</div><div style="font-size:12px;color:#8892b0;margin-top:4px">{c.get("category","?")}</div></div>' + chr(10) + "    "
    if cat_html:
        cat_html = f'<div class="section"><div class="section-title"><span class="icon">🍩</span> 内容分类占比 · LLM 自动分析</div><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px">{cat_html}</div></div>' + chr(10)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Yoyo Creative Studio · 周报 {week_label}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0e17;color:#e0e6f0;font-family:-apple-system,'Inter','Segoe UI',sans-serif;min-height:100vh}}
.container{{max-width:1100px;margin:0 auto;padding:20px}}
.header{{text-align:center;padding:40px 0 30px;border-bottom:1px solid rgba(0,255,255,.08);margin-bottom:28px}}
.header .logo{{font-size:13px;color:#00d4ff;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px}}
.header h1{{font-size:34px;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.header .subtitle{{color:#8892b0;font-size:14px;margin-top:6px}}
.header .badge{{display:inline-block;background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.3);color:#00d4ff;padding:4px 14px;border-radius:12px;font-size:11px;margin-top:10px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:26px}}
.kpi-card{{background:linear-gradient(135deg,rgba(20,30,60,.8),rgba(15,20,40,.8));border:1px solid rgba(0,212,255,.1);border-radius:14px;padding:18px 20px;position:relative;overflow:hidden}}
.kpi-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#00d4ff,#7b2ff7);opacity:.5}}
.kpi-card .label{{color:#8892b0;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:1px}}
.kpi-card .value{{font-size:30px;font-weight:700;margin:6px 0 3px;letter-spacing:-1px}}
.kpi-card .muted{{font-size:12px;color:#5a6480;margin-top:2px}}
.kpi-card .change{{font-size:12px;font-weight:500;margin-top:2px}}
.kpi-card .change.up{{color:#00e676}}.kpi-card .change.down{{color:#ff6b6b}}
.blue{{color:#00d4ff}}.green{{color:#00e676}}.pink{{color:#ff6b9d}}.orange{{color:#ffab00}}.purple{{color:#b388ff}}
.section{{background:linear-gradient(135deg,rgba(20,30,60,.5),rgba(15,20,40,.5));border:1px solid rgba(0,212,255,.06);border-radius:14px;padding:24px;margin-bottom:20px}}
.section-title{{font-size:16px;font-weight:600;color:#00d4ff;margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.section-title .icon{{font-size:18px}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:768px){{.two-col{{grid-template-columns:1fr}}.kpi-grid{{grid-template-columns:repeat(2,1fr)}}}}
.data-table{{width:100%;border-collapse:collapse;font-size:12.5px}}
.data-table th{{color:#5a6480;font-weight:500;text-transform:uppercase;letter-spacing:.5px;padding:9px;text-align:left;border-bottom:1px solid rgba(255,255,255,.05);font-size:10px}}
.data-table td{{padding:9px;border-bottom:1px solid rgba(255,255,255,.03)}}
.data-table tr:hover td{{background:rgba(0,212,255,.02)}}
.data-table .num{{text-align:right;font-weight:500}}
.data-table .dim td{{opacity:.35}}
.daily-chart{{display:flex;gap:6px;align-items:flex-end;height:140px;padding:12px 0;justify-content:center}}
.daily-bar{{flex:1;max-width:80px;display:flex;flex-direction:column;align-items:center;gap:3px}}
.daily-bar .bar{{width:100%;border-radius:4px 4px 0 0;min-height:4px;background:linear-gradient(180deg,#00d4ff,rgba(0,212,255,.15))}}
.daily-bar .val-label{{font-size:9px;font-weight:600;color:#e0e6f0}}
.daily-bar .day-label{{font-size:9px;color:#5a6480;margin-top:1px}}
.rank-list{{list-style:none}}
.rank-list li{{display:flex;align-items:center;padding:7px 10px;margin:2px 0;background:rgba(0,0,0,.15);border-radius:8px;gap:10px;font-size:12px}}
.rank-list .rank{{font-weight:700;font-size:14px;min-width:28px;text-align:center}}
.rank-list .name{{flex:1}}
.rank-list .score{{font-weight:600;color:#00d4ff}}
.alert{{background:rgba(255,107,107,.08);border:1px solid rgba(255,107,107,.25);border-radius:10px;padding:12px 18px;margin-bottom:16px;font-size:13px;color:#ff6b6b}}
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
.footer{{text-align:center;padding:24px;color:#5a6480;font-size:11px}}
.footer p{{margin-top:3px}}
</style></head>
<body><div class="container">

<div class="header">
  <div style="display:inline-block;background:#00d4ff;color:#0a0e17;padding:6px 20px;border-radius:20px;font-size:14px;font-weight:700;letter-spacing:2px;margin-bottom:12px">📊 周 报</div>
  <div class="logo">📊 Weekly Report</div>
  <h1>Yoyo Creative Studio</h1>
  <div class="subtitle">{week_label} · KOC 创作者社群周报 · {now.strftime('%Y/%m/%d')} 生成</div>
  <span class="badge">🤖 Mochi Bot · 深度分析 by DeepSeek</span>
</div>

{alert_html}

<div class="kpi-grid">
  <div class="kpi-card"><div class="label">🗣️ 全频道消息</div><div class="value blue">{total:,}</div><div class="muted">日均 {daily_avg:,} 条</div><div class="change {wow_class}">环比 {wow_change}</div></div>
  <div class="kpi-card"><div class="label">💬 主频道</div><div class="value green">{mc:,}</div><div class="muted">👥 {mc_speakers} 人发言</div></div>
  <div class="kpi-card"><div class="label">🆕 新发言者</div><div class="value pink">{len(new_speakers):,}</div><div class="muted">本周首次说话</div></div>
  <div class="kpi-card"><div class="label">🔄 回流用户</div><div class="value orange">{len(returning):,}</div><div class="muted">上周也发言了</div></div>
  <div class="kpi-card"><div class="label">📡 活跃频道</div><div class="value purple">{active_chan}<span style="font-size:14px;color:#8892b0">/{len(CHANNELS)}</span></div><div class="muted">本周有消息的频道</div></div>
  <div class="kpi-card"><div class="label">😊 社群氛围</div><div class="value" style="color:#00d4ff;font-size:22px">见分析</div><span style="font-size:11px;color:#8892b0">下方 LLM 深度分析</span></div>
</div>

{analysis_html}

<div class="section">
  <div class="section-title"><span class="icon">📈</span> creators-exchange 日活跃趋势</div>
  <div class="daily-chart">{daily_bars}</div>
  <p style="text-align:center;color:#5a6480;font-size:10px;margin-top:6px">💡 非 Bot 消息量 · 条/天</p>
</div>

{cat_html}

    <div class="two-col">
<div class="section">
  <div class="section-title"><span class="icon">📡</span> 各频道消息分布</div>
  <table class="data-table">
    <tr><th>频道</th><th class="num">消息量</th></tr>
    {chan_rows}
  </table>
  <div style="margin-top:8px;font-size:10px;color:#5a6480">🔥>100 📊>20 💤≤20 ⛔无消息</div>
</div>
<div class="section">
  <div class="section-title"><span class="icon">🏆</span> TOP 10 活跃创作者</div>
  <ul class="rank-list">{top_html}</ul>
</div>
</div>

<div class="footer">
  <p>🤖 由 GitHub Actions 自动生成 · {now.strftime('%Y年%m月%d日 %H:%M')} UTC</p>
  <p>数据来源: Discord · Yoyo Creative Studio · 话题分析: DeepSeek V4 Flash · 通过 ARK API</p>
</div>

</div></body></html>'''

    with open("weekly.html","w") as f:
        f.write(html)
    print("✅ HTML 已生成")

    # Step 6: Save cache
    cache.setdefault("weeks",[])
    cache["weeks"].append({
        "week":week_key,"label":week_label,"total":total,"chat_area":mc,
        "speakers_chat":list(main_speakers),"speakers_count":mc_speakers,
        "chan_data":chan_data,"top_users":[(u,c) for u,c in top_users],
        "date":now.isoformat()
    })
    if len(cache["weeks"]) > 8: cache["weeks"] = cache["weeks"][-8:]
    with open(CACHE_FILE,"w") as f: json.dump(cache, f, ensure_ascii=False)
    print("💾 缓存已保存")

    # Step 7: Feishu
    if FEISHU:
        print("\n📤 推送飞书...")
        top5 = ""
        i = 0
        for name in sorted(chan_data.keys(), key=lambda x: -chan_data[x])[:5]:
            c = chan_data[name]; i += 1
            top5 += f"\n{i}. #{name}: {c:,}条"
        ns = len(new_speakers); rs = len(returning)

        text = f"📢 creators-exchange：**{mc:,}** 条（👥 {mc_speakers}人）\n🗣️ 全频道总计：**{total:,}** 条 · 日均 **{daily_avg:,}** 条\n🆕 新发言：{ns}人 · 🔄 回流：{rs}人"

        if analysis:
            topics_for_feishu = [d.get('theme','') for d in analysis.get('hot_discussions',[])]
            pains = [p[:40] for p in analysis.get('pain_points',[])][:2]
            highlights = [h[:30] for h in analysis.get('highlights',[])][:2]
            text += f"\n\n🤖 **LLM 深度分析**\n🔥 热议：{'、'.join(topics_for_feishu[:3])}\n💬 情绪：{analysis.get('user_sentiment','')[:100]}"
            if pains: text += f"\n⚠️ 痛点：{'；'.join(pains)}"
            if highlights: text += f"\n🌟 亮点：{'；'.join(highlights)}"
            mochi = analysis.get('mochi_mentions','')
            skip_words2 = ["暂无","未出现","未提及","没有提到","没有发现","未发现","无相关","未参与","没有相关","无相关讨论","未被提及","不涉及","没有讨论","0条","无讨论"]
            if mochi and not any(w in mochi for w in skip_words2):
                text += f"\n🤖 Mochi反馈：{mochi[:100]}"

        text += f"\n\n📡 **频道 TOP 5**：{top5}"

        payload = json.dumps({
            "msg_type":"interactive",
            "card":{
                "header":{"title":{"content":f"📊 Yoyo Creative Studio 周报 · {week_label}","tag":"plain_text"},"template":"blue"},
                "elements":[
                    {"tag":"div","text":{"content":text,"tag":"lark_md"}},
                    {"tag":"action","actions":[{"tag":"button","text":{"content":"🌐 查看完整周报","tag":"plain_text"},"url":"https://jiashi65.github.io/yoyo-community-report/weekly.html","type":"primary"}]},
                    {"tag":"note","elements":[{"tag":"plain_text","content":"🤖 Mochi Bot · LLM分析 by ARK DeepSeek · 每周一更新"}]}
                ]
            }
        }).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(FEISHU, data=payload, headers={"Content-Type":"application/json"}))
            print("✅ 已推送到飞书！")
        except Exception as e:
            print(f"⚠️ 推送失败: {e}")
    else:
        print("⚠️ 未设置飞书 Webhook，跳过推送")

    print(f"\n✅ 周报完成！总计 {total:,} 条消息 · {mc_speakers} 人参与 · {active_chan} 个频道活跃")

if __name__ == "__main__":
    main()
