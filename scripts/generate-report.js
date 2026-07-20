const DISCORD_TOKEN = process.env.DISCORD_BOT_TOKEN;
const FEISHU_WEBHOOK = process.env.FEISHU_WEBHOOK_URL;
const GUILD_ID = "1458340952358785193";
const SKIP_CHANNEL_PATTERNS = ["log","welcome","rules","faq","reward","test"];
async function fetchAllChannels() {
  var res = await fetch("https://discord.com/api/v10/guilds/" + GUILD_ID + "/channels", { headers: { Authorization: "Bot " + DISCORD_TOKEN } });
  var channels = await res.json();
  return channels.filter(function(c) { return c.type === 0 && !SKIP_CHANNEL_PATTERNS.some(function(p) { return c.name.includes(p); }); });
}
const REPORT_URL = "https://jiashi65.github.io/yoyo-community-report/";

const KOC_DM_STATIC = {
  total_dm: 500, total_creators: 60,
  topic_breakdown: {
    "📦 周边发货":    { count: 121, pct: 43, color: "#ff6b9d" },
    "📊 积分结算":    { count: 38,  pct: 14, color: "#ffab00" },
    "💝 感谢回馈":    { count: 21,  pct: 7,  color: "#00e676" },
    "❓ 答疑指导":    { count: 18,  pct: 6,  color: "#00d4ff" },
    "🧑‍💼 招募欢迎":  { count: 9,   pct: 3,  color: "#b388ff" },
    "💬 其他沟通":    { count: 94,  pct: 29, color: "#8892b0" }
  },
  dm_descs: {
    "📦 周边发货":    "协助KOC完成收货信息、报关资料",
    "📊 积分结算":    "发送月度积分明细",
    "💝 感谢回馈":    "KOC收到帮助后的致谢",
    "❓ 答疑指导":    "解答Discord使用、活动规则",
    "🧑‍💼 招募欢迎":  "邀请加入创作者计划",
    "💬 其他沟通":    "各类日常协调"
  }
};

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchDiscordMessages(channelId, daysBack = 14) {
  const since = Date.now() - daysBack * 86400000;
  const all = []; let before = null;
  console.log(`Fetching ${channelId} since ${new Date(since).toISOString()}`);
  for (let p = 0; p < 200; p++) {
    let url = `https://discord.com/api/v10/channels/${channelId}/messages?limit=100`;
    if (before) url += `&before=${before}`;
    let res = null;
    for (let r = 0; r < 5; r++) {
      await sleep(600 + r * 300);
      res = await fetch(url, { headers: { Authorization: `Bot ${DISCORD_TOKEN}` } });
      if (res.status === 429) {
        const ra = parseInt(res.headers.get("Retry-After") || "5") * 1000;
        console.log(`Rate limited, waiting ${ra/1000}s...`);
        await sleep(ra + 2000); continue;
      }
      break;
    }
    if (!res || !res.ok) { console.error(`API error: ${res?.status}`); break; }
    const msgs = await res.json();
    if (!Array.isArray(msgs) || msgs.length === 0) break;
    const cut = msgs.filter(m => Date.parse(m.timestamp) >= since);
    all.push(...cut);
    if (cut.length < msgs.length) break;
    before = msgs[msgs.length - 1].id;
  }
  console.log(`Got ${all.length} messages`);
  return all;
}

const EMOJI_PATTERNS = [
  { name: "🎨 作品分享",  color: "#ff6b9d",  keywords: ["upload","post","creation","share","submit","link","attachment","作品","发布","分享","创作","投稿","my art","my work","check out"] },
  { name: "💝 正向反馈",  color: "#00e676",  keywords: ["thank","thanks","appreciate","感谢","谢谢","great","awesome","helpful","love it","amazing","wonderful","perfect"] },
  { name: "❓ 规则答疑",  color: "#ffab00",  keywords: ["question","rule","point","how to","what is","help","clarif","不明白","规则","积分","请问","能不能","可以吗","怎么回事","什么意思","怎么算"] },
  { name: "🎮 游戏设计",  color: "#b388ff",  keywords: ["game","design","gameplay","角色","场景","关卡","玩法","机制","平衡","美术","策划"] },
  { name: "💬 其他讨论",  color: "#00bcd4",  keywords: [] }
];

function classify(msg) {
  const c = (msg.content || "").toLowerCase();
  const hasAttach = msg.attachments && msg.attachments.length > 0;
  for (const p of EMOJI_PATTERNS) {
    if (p.keywords.length === 0) continue;
    if (hasAttach && p.name === "🎨 作品分享") return p;
    for (const kw of p.keywords) {
      if (c.includes(kw)) return p;
    }
  }
  return EMOJI_PATTERNS[EMOJI_PATTERNS.length - 1];
}

function analyze(msgs) {
  const classified = msgs.map(m => ({ ...m, ...classify(m), date: new Date(m.timestamp) }));
  const counts = {}, samples = {}, authors = new Set();
  for (const m of classified) {
    const n = m.name;
    counts[n] = (counts[n] || 0) + 1;
    if (!samples[n]) samples[n] = [];
    if (samples[n].length < 3) samples[n].push(m);
    authors.add(m.author?.id);
  }
  // Daily breakdown
  const daily = {};
  for (const m of classified) {
    const d = m.date.toISOString().slice(0,10);
    if (!daily[d]) daily[d] = 0;
    daily[d]++;
  }
  return { total: classified.length, authors: authors.size, counts, samples, daily };
}

function escape(s) {
  return (s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\n/g,"<br>");
}

function fmtDate(d) { return `${d.getMonth()+1}/${d.getDate()}`; }

function genHTML(cur, prev, label, prevLabel) {
  const now = new Date();
  const dateStr = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日`;
  const mT = cur.total, pT = prev.total || 1;
  const mA = cur.authors, pA = prev.authors || 1;
  const mC = ((mT-pT)/pT*100).toFixed(1);
  const aC = ((mA-pA)/pA*100).toFixed(1);

  // Topic keys
  const keys = EMOJI_PATTERNS.map(p => p.name);
  const maxC = Math.max(...keys.map(k => cur.counts[k] || 0), 1);
  const bars = keys.map(k => {
    const c = cur.counts[k] || 0;
    const p = prev.counts[k] || 0;
    const ch = p > 0 ? ((c-p)/p*100).toFixed(1) : null;
    const e = EMOJI_PATTERNS.find(e => e.name === k);
    return { name: k, cur: c, prev: p, pct: c/maxC*100, ch, color: e.color };
  });

  const pctMap = {};
  for (const k of keys) pctMap[k] = mT > 0 ? ((cur.counts[k]||0)/mT*100).toFixed(0) : 0;

  // Sample chat messages
  const samples = keys.map(k => (cur.samples[k]||[]).slice(0,1)).flat().filter(Boolean).slice(0,4);

  // Daily chart data
  const days = Object.keys(cur.daily).sort();
  const maxDay = Math.max(...Object.values(cur.daily), 1);

  // DM items
  const dm = Object.entries(KOC_DM_STATIC.topic_breakdown);
  const dmMid = Math.ceil(dm.length / 2);

  // KPI card helpers
  const kpiUp = (v) => v >= 0 ? "up" : "down";
  const kpiArrow = (v) => v >= 0 ? "↗" : "↘";

  // Comparison table rows
  const tableRows = bars.map(b => {
    const ch = b.ch !== null ? `${b.ch >= 0 ? "📈" : "📉"} ${b.ch >= 0 ? "+" : ""}${b.ch}%` : "NEW";
    const cls = b.ch !== null && b.ch >= 0 ? "up" : "down";
    return `<tr><td>${b.name}</td><td class="num">${b.prev}</td><td class="num">${b.cur}</td><td class="num ${cls}">${ch}</td></tr>`;
  }).join("\n    ");

  // Category colors for chat bubbles
  const catStyle = {
    "🎨 作品分享": { bg: "#ff6b9d", fg: "#fff", border: "#ff6b9d" },
    "💝 正向反馈": { bg: "#00e676", fg: "#000", border: "#00e676" },
    "❓ 规则答疑": { bg: "#ffab00", fg: "#000", border: "#ffab00" },
    "🎮 游戏设计": { bg: "#b388ff", fg: "#fff", border: "#b388ff" },
    "💬 其他讨论": { bg: "#00bcd4", fg: "#000", border: "#00bcd4" }
  };

  function chatBubble(m) {
    const cs = catStyle[m.name] || { bg: "#8892b0", fg: "#fff", border: "#8892b0" };
    const d = new Date(m.timestamp);
    const dateLabel = `${d.getMonth()+1}/${d.getDate()}`;
    const content = escape((m.content || "(empty)").substring(0, 180));
    const author = m.author?.username || "Unknown";
    const pct = pctMap[m.name] || 0;
    return `<div class="chat-bubble" style="background:rgba(0,0,0,.25);border-radius:12px;padding:14px 16px;margin-bottom:10px;border-left:3px solid ${cs.border}">
      <span class="tag" style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;background:${cs.bg};color:${cs.fg};margin-bottom:6px">${m.name} · ${pct}%</span>
      <p style="font-size:12px;line-height:1.6;color:#c0c8e0">${content}</p>
      <div class="meta" style="font-size:10px;color:#8892b0;margin-top:6px">${author} · ${dateLabel}</div>
    </div>`;
  }

  function dmBubble(key, data) {
    const c = {
      "📦 周边发货": { bg: "#ff6b9d", fg: "#fff" },
      "📊 积分结算": { bg: "#ffab00", fg: "#000" },
      "💝 感谢回馈": { bg: "#00e676", fg: "#000" },
      "❓ 答疑指导": { bg: "#00d4ff", fg: "#000" },
      "🧑‍💼 招募欢迎": { bg: "#b388ff", fg: "#fff" },
      "💬 其他沟通": { bg: "#8892b0", fg: "#fff" }
    }[key] || { bg: "#8892b0", fg: "#fff" };
    const desc = KOC_DM_STATIC.dm_descs[key] || "创作者运营";
    return `<div class="chat-bubble" style="background:rgba(0,0,0,.25);border-radius:12px;padding:14px 16px;margin-bottom:10px;border-left:3px solid ${c.bg}">
      <span class="tag" style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;background:${c.bg};color:${c.fg};margin-bottom:6px">${key} · ${data.pct}%</span>
      <p style="font-size:12px;line-height:1.6;color:#c0c8e0">→ ${desc}</p>
      <div class="meta" style="font-size:10px;color:#8892b0;margin-top:6px">${data.count}条</div>
    </div>`;
  }

  // Daily chart bars
  const dayBars = days.slice(-7).map(d => {
    const h = cur.daily[d] / maxDay * 160;
    const label = d.slice(5); // MM-DD
    return `<div class="daily-bar"><div class="bar" style="height:${Math.max(h,4)}px"></div><div class="val-label">${cur.daily[d]}</div><div class="day-label">${label}</div></div>`;
  }).join("\n      ");

  // Insight cards
  const works = cur.counts["🎨 作品分享"] || 0;
  const pWorks = prev.counts["🎨 作品分享"] || 1;
  const worksCh = ((works - pWorks)/pWorks*100).toFixed(1);
  const feedback = cur.counts["💝 正向反馈"] || 0;
  const pFeed = prev.counts["💝 正向反馈"] || 1;
  const feedCh = ((feedback - pFeed)/pFeed*100).toFixed(1);
  const questions = cur.counts["❓ 规则答疑"] || 0;
  const pQ = prev.counts["❓ 规则答疑"] || 1;
  const qCh = ((questions - pQ)/pQ*100).toFixed(1);

  const insightClass = (v) => v >= 5 ? "up" : v < -5 ? "down" : "flat";

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Yoyo Creative Studio · 社群周报</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e6f0;font-family:-apple-system,'Inter','Segoe UI',sans-serif;min-height:100vh}
.container{max-width:1200px;margin:0 auto;padding:20px}
.header{text-align:center;padding:40px 0 30px;border-bottom:1px solid rgba(0,255,255,.1);margin-bottom:30px}
.header .logo{font-size:13px;color:#00d4ff;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px}
.header h1{font-size:34px;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.header .subtitle{color:#8892b0;font-size:14px;margin-top:6px}
.header .badge{display:inline-block;background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.3);color:#00d4ff;padding:4px 14px;border-radius:12px;font-size:11px;margin-top:8px}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:28px}
.kpi-card{background:linear-gradient(135deg,rgba(20,30,60,.8),rgba(15,20,40,.8));border:1px solid rgba(0,212,255,.12);border-radius:14px;padding:18px 20px;position:relative;overflow:hidden}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#00d4ff,#7b2ff7);opacity:.5}
.kpi-card .label{color:#8892b0;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:1px}
.kpi-card .value{font-size:32px;font-weight:700;margin:6px 0 3px;letter-spacing:-1px;line-height:1.1}
.kpi-card .change{font-size:12px;font-weight:500;margin-top:2px}
.kpi-card .change.up{color:#00d4ff}.kpi-card .change.down{color:#ff6b6b}
.kpi-card .mini{font-size:10px;color:#5a6480;margin-top:3px}
.blue{color:#00d4ff}.green{color:#00e676}.orange{color:#ffab00}.purple{color:#b388ff}.pink{color:#ff6b9d}.red{color:#ff6b6b}
.section{background:linear-gradient(135deg,rgba(20,30,60,.55),rgba(15,20,40,.55));border:1px solid rgba(0,212,255,.08);border-radius:14px;padding:26px;margin-bottom:22px}
.section-title{font-size:17px;font-weight:600;color:#00d4ff;margin-bottom:18px;display:flex;align-items:center;gap:8px}
.section-title .icon{font-size:20px}
.data-table{width:100%;border-collapse:collapse;font-size:12.5px}
.data-table th{color:#5a6480;font-weight:500;text-transform:uppercase;letter-spacing:.5px;padding:9px 8px;text-align:left;border-bottom:1px solid rgba(255,255,255,.05);font-size:11px}
.data-table td{padding:9px 8px;border-bottom:1px solid rgba(255,255,255,.03)}
.data-table tr:hover td{background:rgba(0,212,255,.03)}
.data-table .num{text-align:right;font-weight:500}
.data-table .up{color:#00d4ff}.data-table .down{color:#ff6b6b}
.bar-chart{margin:10px 0}
.bar-row{display:flex;align-items:center;margin:6px 0;gap:8px}
.bar-label{min-width:110px;font-size:12px;color:#8892b0;white-space:nowrap}
.bar-fill{flex:1;height:20px;background:rgba(255,255,255,.03);border-radius:4px;overflow:hidden}
.bar-fill .bar{height:100%;border-radius:4px;transition:width .4s ease}
.bar-val{min-width:40px;text-align:right;font-size:12px;font-weight:600}
.bar-chg{min-width:50px;text-align:right;font-size:11px}
.daily-chart{display:flex;gap:6px;align-items:flex-end;height:180px;padding:16px 0;justify-content:center}
.daily-bar{flex:1;max-width:60px;display:flex;flex-direction:column;align-items:center;gap:3px}
.daily-bar .bar{width:100%;border-radius:4px 4px 0 0;min-height:4px;background:linear-gradient(180deg,#00d4ff,rgba(0,212,255,.2));transition:height .4s ease}
.daily-bar .val-label{font-size:9px;font-weight:600;color:#e0e6f0}
.daily-bar .day-label{font-size:9px;color:#5a6480;margin-top:1px}
.insight-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px;margin-top:4px}
.insight-card{background:rgba(0,0,0,.15);border:1px solid rgba(0,212,255,.06);border-radius:10px;padding:14px 16px}
.insight-card .icon{font-size:22px;margin-bottom:4px}
.insight-card h4{font-size:13px;font-weight:600;margin-bottom:3px}
.insight-card h4.up{color:#00d4ff}.insight-card h4.down{color:#ff6b6b}.insight-card h4.flat{color:#8892b0}
.insight-card p{font-size:11.5px;color:#8892b0;line-height:1.5}
.chat-bubble{background:rgba(0,0,0,.25);border-radius:12px;padding:12px 14px;margin-bottom:8px}
.chat-bubble p{font-size:11.5px;line-height:1.6;color:#c0c8e0;word-break:break-word}
.chat-bubble .meta{font-size:10px;color:#5a6480;margin-top:5px}
.chat-bubble .tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;margin-bottom:6px}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <div class="logo">📊 Weekly Report</div>
  <h1>Yoyo Creative Studio</h1>
  <div class="subtitle">${label} · ${dateStr} · 自动生成</div>
  <span class="badge">🤖 GitHub Actions · 创作者社群</span>
</div>

<div class="kpi-grid">
  <div class="kpi-card"><div class="label">📢 公开频道消息</div><div class="value blue">${mT}</div><div class="change ${kpiUp(mC)}">${kpiArrow(mC)} ${prevLabel} ${pT}条 · ${mC >= 0 ? "+" : ""}${mC}%</div><div class="mini">日均 ${(mT/7).toFixed(0)}条/天</div></div>
  <div class="kpi-card"><div class="label">👥 发言人数</div><div class="value green">${mA}</div><div class="change ${kpiUp(aC)}">${kpiArrow(aC)} ${prevLabel} ${pA}人 · ${aC >= 0 ? "+" : ""}${aC}%</div><div class="mini">本周活跃创作者</div></div>
  <div class="kpi-card"><div class="label">💬 KOC私信对接</div><div class="value purple">${KOC_DM_STATIC.total_creators}+</div><div class="change up">↗ 持续运营中</div><div class="mini">创作者私信运营</div></div>
  <div class="kpi-card"><div class="label">📝 私信消息量</div><div class="value orange">${KOC_DM_STATIC.total_dm}+</div><div class="change up">↗ 日均 ${Math.round(KOC_DM_STATIC.total_dm/30)}条</div><div class="mini">覆盖全链路运营</div></div>
  <div class="kpi-card"><div class="label">🎨 作品分享</div><div class="value pink">${works}</div><div class="change ${kpiUp(worksCh)}">${kpiArrow(worksCh)} ${prevLabel} ${pWorks}条 · ${worksCh >= 0 ? "+" : ""}${worksCh}%</div><div class="mini">UGC产出</div></div>
  <div class="kpi-card"><div class="label">💝 正向反馈</div><div class="value green">${feedback}</div><div class="change ${kpiUp(feedCh)}">${kpiArrow(feedCh)} ${prevLabel} ${pFeed}条 · ${feedCh >= 0 ? "+" : ""}${feedCh}%</div><div class="mini">社群氛围</div></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📈</span> 日度活跃趋势</div>
  <div class="daily-chart">
    ${dayBars}
  </div>
  <p style="text-align:center;color:#5a6480;font-size:11px;margin-top:6px">💡 过去7天每日消息量</p>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📊</span> 核心指标对比 · ${prevLabel} → ${label}</div>
  <table class="data-table">
    <tr><th>指标</th><th class="num">${prevLabel}</th><th class="num">${label}</th><th class="num">环比</th></tr>
    <tr><td>公开频道消息总量</td><td class="num">${pT}</td><td class="num">${mT}</td><td class="num ${kpiUp(mC)}">${mC >= 0 ? "📈" : "📉"} ${mC >= 0 ? "+" : ""}${mC}%</td></tr>
    <tr><td>日均消息</td><td class="num">${(pT/7).toFixed(0)}</td><td class="num">${(mT/7).toFixed(0)}</td><td class="num ${kpiUp(mC)}">${mC >= 0 ? "📈" : "📉"} ${mC >= 0 ? "+" : ""}${mC}%</td></tr>
    <tr><td>发言人数</td><td class="num">${pA}</td><td class="num">${mA}</td><td class="num ${kpiUp(aC)}">${aC >= 0 ? "📈" : "📉"} ${aC >= 0 ? "+" : ""}${aC}%</td></tr>
    ${tableRows}
  </table>
</div>

<div class="section">
  <div class="section-title"><span class="icon">🎯</span> 内容画像 · 话题分布</div>
  <div class="bar-chart">
    ${bars.map(b => `<div class="bar-row">
      <div class="bar-label">${b.name}</div>
      <div class="bar-fill"><div class="bar" style="width:${b.pct}%;background:${b.color};opacity:.8"></div></div>
      <div class="bar-val" style="color:${b.color}">${b.cur}</div>
      <div class="bar-chg" style="color:${b.ch !== null && b.ch >= 0 ? "#00d4ff" : "#ff6b6b"}">${b.ch !== null ? (b.ch >= 0 ? "+" : "") + b.ch + "%" : "NEW"}</div>
    </div>`).join("\n    ")}
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">💬</span> 大家都在聊什么？</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div>${samples.slice(0, Math.ceil(samples.length/2)).map(chatBubble).join("\n      ")}</div>
    <div>${samples.slice(Math.ceil(samples.length/2)).map(chatBubble).join("\n      ")}</div>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">💌</span> KOC私信 · 工作内容</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div>${dm.slice(0, dmMid).map(([k,d]) => dmBubble(k,d)).join("\n      ")}</div>
    <div>${dm.slice(dmMid).map(([k,d]) => dmBubble(k,d)).join("\n      ")}</div>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">💡</span> 关键洞察</div>
  <div class="insight-grid">
    <div class="insight-card">
      <div class="icon">📈</div>
      <h4 class="${insightClass(mC)}">${mC >= 5 ? "社群活跃度显著提升" : mC < -5 ? "社群活跃度下降" : "社群活跃度平稳"}</h4>
      <p>本周消息量 ${mT} 条，较上周${mC >= 0 ? "增长" : "下降"} ${Math.abs(mC)}%。${mC >= 10 ? "社群增长势头良好！" : mC >= 0 ? "保持稳定增长。" : "建议关注内容互动情况。"}</p>
    </div>
    <div class="insight-card">
      <div class="icon">👥</div>
      <h4 class="${insightClass(aC)}">${aC >= 5 ? "创作者基数扩大" : aC < -5 ? "创作者参与度下降" : "创作者结构稳定"}</h4>
      <p>本周 ${mA} 人参与讨论（上周 ${pA} 人），${aC >= 0 ? "社群正在健康扩张。" : "部分创作者活跃度降低。"}</p>
    </div>
    <div class="insight-card">
      <div class="icon">🎨</div>
      <h4 class="${insightClass(worksCh)}">${worksCh >= 5 ? "UGC 产出活跃" : worksCh < -5 ? "创作分享减少" : "创作量平稳"}</h4>
      <p>作品分享 ${works} 条（上周 ${pWorks} 条），${worksCh >= 0 ? "创作者积极性高。" : "建议激励更多创作。"}</p>
    </div>
    <div class="insight-card">
      <div class="icon">❓</div>
      <h4 class="${insightClass(qCh)}">${qCh >= 5 ? "咨询量增加" : qCh < -5 ? "咨询减少" : "咨询量平稳"}</h4>
      <p>规则答疑 ${questions} 条（上周 ${pQ} 条），${qCh >= 0 ? "新创作者活跃度上升。" : "社群规则认知度提高。"}</p>
    </div>
  </div>
</div>

<div class="section" style="text-align:center;padding:16px">
  <p style="color:#5a6480;font-size:11px">🤖 由 GitHub Actions 自动生成 · ${dateStr}</p>
  <p style="color:#5a6480;font-size:11px;margin-top:2px">Discord Bot: Mochi's bot · 数据来自 #creators-exchange 公开频道</p>
</div>

</div>
</body>
</html>`;
}

async function pushFeishu(cur, prev, label, prevLabel) {
  if (!FEISHU_WEBHOOK) { console.log("Skip Feishu push (no webhook)"); return; }
  const mT = cur.total, pT = prev.total || 1, mC = ((mT-pT)/pT*100).toFixed(1);
  const mA = cur.authors, pA = prev.authors || 1, aC = ((mA-pA)/pA*100).toFixed(1);
  const card = {
    config: { wide_screen_mode: true },
    header: { title: { tag: "plain_text", content: `📊 Yoyo Creative Studio · ${label} 社区周报` }, template: "blue" },
    elements: [
      { tag: "div", text: { tag: "lark_md", content: "**📈 本周核心数据**" } },
      { tag: "column_set", flex_mode: "none", background_style: "default", columns: [
        { tag: "column", width: "weighted", weight: 1, elements: [{ tag: "div", text: { tag: "lark_md", content: `**📢 消息**\n${mT} 条\n↗ ${mC}%` } }] },
        { tag: "column", width: "weighted", weight: 1, elements: [{ tag: "div", text: { tag: "lark_md", content: `**👥 发言人**\n${mA} 人\n↗ ${aC}%` } }] },
        { tag: "column", width: "weighted", weight: 1, elements: [{ tag: "div", text: { tag: "lark_md", content: `**💬 KOC私信**\n${KOC_DM_STATIC.total_creators}+ 人\n${KOC_DM_STATIC.total_dm}+ 条` } }] }
      ]},
      { tag: "hr" },
      { tag: "action", actions: [{ tag: "button", text: { tag: "plain_text", content: "🔗 查看完整报告" }, type: "primary", url: REPORT_URL, multi_url: { url: REPORT_URL } }] },
      { tag: "note", elements: [{ tag: "plain_text", content: `Yoyo Creative Studio · ${label} · 自动生成` }] }
    ]
  };
  const res = await fetch(FEISHU_WEBHOOK, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ msg_type:"interactive", card }) });
  const d = await res.json();
  console.log("Feishu:", d.code === 0 ? "✅ OK" : "❌ FAIL");
}

async function main() {
  if (!DISCORD_TOKEN) { console.error("Missing DISCORD_BOT_TOKEN"); process.exit(1); }
  console.log("Starting weekly report...");
    var allChannels = await fetchAllChannels();
  var curMsgs = [], allMsgs = [];
  for (var ci = 0; ci < allChannels.length; ci++) {
    console.log('Scanning #' + allChannels[ci].name + '...');
    var cur = await fetchDiscordMessages(allChannels[ci].id, 7);
    var all = await fetchDiscordMessages(allChannels[ci].id, 14);
    curMsgs = curMsgs.concat(cur);
    allMsgs = allMsgs.concat(all);
  }
  
  const curIds = new Set(curMsgs.map(m => m.id));
  const prevMsgs = allMsgs.filter(m => !curIds.has(m.id));
  console.log(`This: ${curMsgs.length}, Prev: ${prevMsgs.length}`);
  const cur = analyze(curMsgs), prev = analyze(prevMsgs);

  const now = new Date();
  const ws = new Date(now); ws.setDate(ws.getDate() - ws.getDay() - 6);
  const we = new Date(now); we.setDate(we.getDate() - we.getDay());
  const label = `${fmtDate(ws)}-${fmtDate(we)}`;
  const pp = new Date(ws); pp.setDate(pp.getDate() - 7);
  const pe = new Date(we); pe.setDate(pe.getDate() - 7);
  const prevLabel = `${fmtDate(pp)}-${fmtDate(pe)}`;

  const html = genHTML(cur, prev, label, prevLabel);
  require("fs").writeFileSync("index.html", html, "utf-8");
  console.log(`✅ Saved to index.html · ${label}: ${cur.total} msgs, ${cur.authors} auth`);
  await pushFeishu(cur, prev, label, prevLabel);
}

main().catch(e => { console.error("❌", e.message); process.exit(1); });
