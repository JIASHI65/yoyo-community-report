const DISCORD_TOKEN = process.env.DISCORD_BOT_TOKEN;
const FEISHU_WEBHOOK = process.env.FEISHU_WEBHOOK_URL;
const GUILD_ID = "1458340952358785193";
const CHANNEL_IDS = ["1458349180748828757"];

const REPORT_URL = "https://jiashi65.github.io/yoyo-community-report/";

const KOC_DM_STATIC = {
  total_dm: 500,
  total_creators: 60,
  topic_breakdown: {
    "\U0001f4e6 周边发货": { count: 121, pct: 31, color: "#ff6b9d" },
    "\U0001f4ca 积分结算": { count: 38, pct: 10, color: "#ffab00" },
    "\U0001f49d 感谢回馈": { count: 21, pct: 5, color: "#00e676" },
    "\u2753 答疑指导": { count: 18, pct: 5, color: "#00d4ff" },
    "\U0001f9d1\u200d\U0001f4bc 招募欢迎": { count: 9, pct: 2, color: "#b388ff" },
    "\U0001f4ac 其他沟通": { count: 94, pct: 24, color: "#8892b0" }
  }
};

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function fetchDiscordMessages(channelId, daysBack = 14) {
  const since = Date.now() - daysBack * 86400000;
  const allMessages = [];
  let before = null;
  console.log(`Fetching ${channelId} since ${new Date(since).toISOString()}`);
  for (let page = 0; page < 200; page++) {
    let url = `https://discord.com/api/v10/channels/${channelId}/messages?limit=100`;
    if (before) url += `&before=${before}`;
    let res = null;
    for (let retry = 0; retry < 5; retry++) {
      await sleep(800 + retry * 400);
      res = await fetch(url, { headers: { Authorization: `Bot ${DISCORD_TOKEN}` } });
      if (res.status === 429) {
        const ra = parseInt(res.headers.get("Retry-After") || "5") * 1000;
        console.log(`Rate limited, waiting ${ra/1000}s...`);
        await sleep(ra + 2000);
        continue;
      }
      break;
    }
    if (!res || !res.ok) { console.error(`API error: ${res?.status}`); break; }
    const msgs = await res.json();
    if (!Array.isArray(msgs) || msgs.length === 0) break;
    const cutoff = msgs.filter(m => Date.parse(m.timestamp) >= since);
    allMessages.push(...cutoff);
    if (cutoff.length < msgs.length) break;
    before = msgs[msgs.length - 1].id;
  }
  console.log(`Got ${allMessages.length} messages`);
  return allMessages;
}

function classifyMessage(msg) {
  const c = (msg.content || "").toLowerCase();
  if (msg.attachments?.length > 0 || c.includes("upload") || c.includes("post") || c.includes("creation") || c.includes("share") || c.includes("submit") || c.includes("link") || c.includes("作品") || c.includes("发布"))
    return { category: "\U0001f3a8 作品分享", pctColor: "#ff6b9d" };
  if (c.includes("thank") || c.includes("appreciate") || c.includes("感谢") || c.includes("谢谢") || c.includes("great") || c.includes("awesome") || c.includes("helpful"))
    return { category: "\U0001f49d 正向反馈", pctColor: "#00e676" };
  if (c.includes("question") || c.includes("rule") || c.includes("point") || c.includes("how") || c.includes("what") || c.includes("help") || c.includes("clarif") || c.includes("规则") || c.includes("积分") || c.includes("请问") || c.includes("不明白"))
    return { category: "\u2753 规则答疑", pctColor: "#ffab00" };
  if (c.includes("game") || c.includes("design") || c.includes("gameplay") || c.includes("角色") || c.includes("场景") || c.includes("关卡"))
    return { category: "\U0001f3ae 游戏设计", pctColor: "#b388ff" };
  return { category: "\U0001f4ac 其他讨论", pctColor: "#00bcd4" };
}

function analyzeMessages(messages) {
  const classified = messages.map(m => ({ ...m, ...classifyMessage(m), date: new Date(m.timestamp) }));
  const topicCounts = {}, topicSamples = {}, authorSet = new Set();
  for (const m of classified) {
    const cat = m.category;
    topicCounts[cat] = (topicCounts[cat] || 0) + 1;
    if (!topicSamples[cat]) topicSamples[cat] = [];
    if (topicSamples[cat].length < 3) topicSamples[cat].push(m);
    authorSet.add(m.author?.id);
  }
  return {
    total_messages: classified.length,
    total_authors: authorSet.size,
    topic_counts: topicCounts,
    topic_samples: topicSamples,
  };
}

function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
}

function generateHTML(current, previous, periodLabel, prevPeriodLabel) {
  const now = new Date();
  const dateStr = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日`;
  const mT = current.total_messages, pT = previous.total_messages || 1;
  const mA = current.total_authors, pA = previous.total_authors || 1;
  const mC = ((mT-pT)/pT*100).toFixed(1), aC = ((mA-pA)/pA*100).toFixed(1);
  const wS = current.topic_counts["\U0001f3a8 作品分享"]||0, pW = previous.topic_counts["\U0001f3a8 作品分享"]||1, wC = ((wS-pW)/pW*100).toFixed(1);
  const fB = current.topic_counts["\U0001f49d 正向反馈"]||0, pF = previous.topic_counts["\U0001f49d 正向反馈"]||1, fC = ((fB-pF)/pF*100).toFixed(1);
  const topicKeys = ["\U0001f3a8 作品分享","\U0001f49d 正向反馈","\u2753 规则答疑","\U0001f3ae 游戏设计","\U0001f4ac 其他讨论"];
  const tCol = {"\U0001f3a8 作品分享":"blue","\U0001f49d 正向反馈":"green","\u2753 规则答疑":"orange","\U0001f3ae 游戏设计":"purple","\U0001f4ac 其他讨论":"cyan"};
  const tHex = {"\U0001f3a8 作品分享":"#00d4ff","\U0001f49d 正向反馈":"#00e676","\u2753 规则答疑":"#ffab00","\U0001f3ae 游戏设计":"#b388ff","\U0001f4ac 其他讨论":"#00bcd4"};
  const maxT = Math.max(...topicKeys.map(k=>current.topic_counts[k]||0),1);
  const bars = topicKeys.map(k=>{const c=current.topic_counts[k]||0,p=previous.topic_counts[k]||0;return{key:k,count:c,pct:maxT>0?c/maxT*100:0,change:p>0?((c-p)/p*100).toFixed(1):"+NEW",color:tCol[k],hex:tHex[k]};});
  const pcts = Object.fromEntries(topicKeys.map(k=>[k,mT>0?((current.topic_counts[k]||0)/mT*100).toFixed(0):0]));
  const samples = topicKeys.map(k=>(current.topic_samples[k]||[]).slice(0,2)).flat().filter(Boolean).slice(0,6);
  const mid = Math.ceil(samples.length/2);

  function chatBubble(msg, cat, pct){
    const cc={"\U0001f49d 正向反馈":{bg:"#00e676",fg:"#000"},"\u2753 规则答疑":{bg:"#ffab00",fg:"#000"},"\U0001f3a8 作品分享":{bg:"#ff6b9d",fg:"#fff"},"\U0001f3ae 游戏设计":{bg:"#b388ff",fg:"#fff"},"\U0001f4ac 其他讨论":{bg:"#00bcd4",fg:"#000"}}[cat]||{bg:"#8892b0",fg:"#fff"};
    const d=new Date(msg.timestamp).toLocaleDateString("zh-CN",{month:"numeric",day:"numeric"});
    return `\n      <div class="chat-bubble" style="background:rgba(0,0,0,.25);border-radius:12px;padding:14px 16px;margin-bottom:10px;border-left:3px solid ${cc.bg}"><span class="tag" style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;background:${cc.bg};color:${cc.fg};margin-bottom:6px">${cat} · ${pct}%</span><p style="font-size:12px;line-height:1.6;color:#c0c8e0">${escapeHtml(msg.content||"(empty)").substring(0,200)}</p><div class="meta" style="font-size:10px;color:#8892b0;margin-top:6px">${msg.author?.username||"Unknown"} · ${d}</div></div>`;
  }

  function dmBubble(name, data){
    const cc={"周边发货":{bg:"#ff6b9d",fg:"#fff"},"积分结算":{bg:"#ffab00",fg:"#000"},"感谢回馈":{bg:"#00e676",fg:"#000"},"答疑指导":{bg:"#00d4ff",fg:"#000"},"招募欢迎":{bg:"#b388ff",fg:"#fff"},"其他沟通":{bg:"#8892b0",fg:"#fff"}};
    const c=Object.values(cc).find(()=>true)||{bg:"#8892b0",fg:"#fff"};
    const descs={"周边发货":"协助KOC完成收货信息、报关资料","积分结算":"发送月度积分明细","感谢回馈":"KOC收到帮助后的致谢","答疑指导":"解答Discord使用、活动规则","招募欢迎":"邀请加入创作者计划","其他沟通":"各类日常协调"};
    return `\n      <div class="chat-bubble" style="background:rgba(0,0,0,.25);border-radius:12px;padding:14px 16px;margin-bottom:10px;border-left:3px solid ${cc[name.replace(/^.{1,2}\s/,'')]?.bg||"#8892b0"}"><span class="tag" style="display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;background:${cc[name.replace(/^.{1,2}\s/,'')]?.bg||"#8892b0"};color:${cc[name.replace(/^.{1,2}\s/,'')]?.fg||"#fff"};margin-bottom:6px">${name} · ${data.pct}%</span><p style="font-size:12px;line-height:1.6;color:#c0c8e0">→ ${descs[name.replace(/^.{1,2}\s/,'')]||"创作者运营"}</p><div class="meta" style="font-size:10px;color:#8892b0;margin-top:6px">${data.count}条</div></div>`;
  }

  const dmE = Object.entries(KOC_DM_STATIC.topic_breakdown);
  const dM = Math.ceil(dmE.length/2);

  const rows = topicKeys.map(k=>{
    const c=current.topic_counts[k]||0, p=previous.topic_counts[k]||0;
    const ch=p>0?((c-p)/p*100).toFixed(1):null;
    return `<tr><td>${k}</td><td class="num">${p}</td><td class="num">${c}</td><td class="num ${ch!==null?(ch>=0?"up":"down"):"up"}">${ch!==null?(ch>=0?"📈":"📉")+" "+(ch>=0?"+":"")+ch+"%":"NEW"}</td></tr>`;
  }).join("\\n");

  return `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Yoyo Creative Studio · 社群周报</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e6f0;font-family:'Inter',sans-serif;min-height:100vh}
.container{max-width:1200px;margin:0 auto;padding:20px}
.header{text-align:center;padding:40px 0 30px;border-bottom:1px solid rgba(0,255,255,.1);margin-bottom:30px}
.header .logo{font-size:14px;color:#00d4ff;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px}
.header h1{font-size:34px;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .subtitle{color:#8892b0;font-size:14px;margin-top:6px}
.header .badge{display:inline-block;background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.3);color:#00d4ff;padding:4px 14px;border-radius:12px;font-size:12px;margin-top:8px}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:30px}
.kpi-card{background:linear-gradient(135deg,rgba(20,30,60,.8),rgba(15,20,40,.8));border:1px solid rgba(0,212,255,.15);border-radius:14px;padding:20px;position:relative;overflow:hidden}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#00d4ff,#7b2ff7);opacity:.6}
.kpi-card .label{color:#8892b0;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:1px}
.kpi-card .value{font-size:34px;font-weight:700;margin:8px 0 4px;letter-spacing:-1px}
.kpi-card .change{font-size:13px;font-weight:500}
.kpi-card .change.up{color:#00d4ff}.kpi-card .change.down{color:#ff6b6b}
.kpi-card .mini{font-size:11px;color:#8892b0;margin-top:4px}
.blue{color:#00d4ff}.green{color:#00e676}.orange{color:#ffab00}.purple{color:#b388ff}.pink{color:#ff6b9d}.red{color:#ff6b6b}
.section{background:linear-gradient(135deg,rgba(20,30,60,.6),rgba(15,20,40,.6));border:1px solid rgba(0,212,255,.1);border-radius:14px;padding:28px;margin-bottom:24px}
.section-title{font-size:18px;font-weight:600;color:#00d4ff;margin-bottom:20px;display:flex;align-items:center;gap:10px}
.section-title .icon{font-size:22px}
.data-table{width:100%;border-collapse:collapse;font-size:13px}
.data-table th{color:#8892b0;font-weight:500;text-transform:uppercase;letter-spacing:.5px;padding:10px 8px;text-align:left;border-bottom:1px solid rgba(255,255,255,.06)}
.data-table td{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.04)}
.data-table tr:hover td{background:rgba(0,212,255,.04)}
.data-table .num{text-align:right;font-family:'Inter',monospace;font-weight:500}
.data-table .up{color:#00d4ff}.data-table .down{color:#ff6b6b}
.bar-chart{margin:12px 0}
.bar-row{display:flex;align-items:center;margin:8px 0;gap:8px}
.bar-label{min-width:110px;font-size:12px;color:#8892b0}
.bar-fill{flex:1;height:22px;background:rgba(255,255,255,.04);border-radius:4px;overflow:hidden}
.bar-fill .bar{height:100%;border-radius:4px}
.bar-fill .bar.blue{background:linear-gradient(90deg,#00d4ff,rgba(0,212,255,.3))}
.bar-fill .bar.green{background:linear-gradient(90deg,#00e676,rgba(0,230,118,.3))}
.bar-fill .bar.orange{background:linear-gradient(90deg,#ffab00,rgba(255,171,0,.3))}
.bar-fill .bar.purple{background:linear-gradient(90deg,#b388ff,rgba(179,136,255,.3))}
.bar-fill .bar.pink{background:linear-gradient(90deg,#ff6b9d,rgba(255,107,157,.3))}
.bar-fill .bar.cyan{background:linear-gradient(90deg,#00bcd4,rgba(0,188,212,.3))}
.bar-val{min-width:50px;text-align:right;font-size:12px;font-weight:600}
.insight-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.insight-card{background:rgba(0,212,255,.04);border:1px solid rgba(0,212,255,.08);border-radius:10px;padding:16px}
.insight-card .icon{font-size:24px;margin-bottom:6px}
.insight-card h4{font-size:13px;font-weight:600;margin-bottom:4px}
.insight-card p{font-size:12px;color:#8892b0;line-height:1.5}
.chat-bubble{background:rgba(0,0,0,.25);border-radius:12px;padding:14px 16px;margin-bottom:10px}
.chat-bubble p{font-size:12px;line-height:1.6;color:#c0c8e0;word-break:break-word}
.chat-bubble .meta{font-size:10px;color:#8892b0;margin-top:6px}
</style>
</head><body>
<div class="container">
<div class="header">
  <div class="logo">📊 Weekly Report</div>
  <h1>Yoyo Creative Studio</h1>
  <div class="subtitle">${periodLabel} · ${dateStr} · 自动生成</div>
  <span class="badge">🤖 GitHub Actions</span>
</div>

<div class="kpi-grid">
  <div class="kpi-card"><div class="label">📢 公开频道消息</div><div class="value blue">${mT}</div><div class="change ${mC>=0?"up":"down"}">↗ ${prevPeriodLabel} ${pT}条 · ${mC>=0?"+":""}${mC}%</div><div class="mini">日均 ${(mT/7).toFixed(0)}条/天</div></div>
  <div class="kpi-card"><div class="label">👥 发言人数</div><div class="value green">${mA}</div><div class="change ${aC>=0?"up":"down"}">↗ ${prevPeriodLabel} ${pA}人 · ${aC>=0?"+":""}${aC}%</div><div class="mini">本周活跃创作者</div></div>
  <div class="kpi-card"><div class="label">💬 KOC私信对接</div><div class="value purple">${KOC_DM_STATIC.total_creators}+</div><div class="change up">↗ 持续运营中</div><div class="mini">创作者私信运营</div></div>
  <div class="kpi-card"><div class="label">📝 私信消息量</div><div class="value orange">${KOC_DM_STATIC.total_dm}+</div><div class="change up">↗ 日均 ${Math.round(KOC_DM_STATIC.total_dm/30)}条</div><div class="mini">覆盖全链路运营</div></div>
  <div class="kpi-card"><div class="label">🎨 作品分享</div><div class="value pink">${wS}</div><div class="change ${wC>=0?"up":"down"}">↗ ${prevPeriodLabel} ${pW}条 · ${wC>=0?"+":""}${wC}%</div><div class="mini">UGC产出</div></div>
  <div class="kpi-card"><div class="label">💝 正向反馈</div><div class="value green">${fB}</div><div class="change ${fC>=0?"up":"down"}">↗ ${prevPeriodLabel} ${pF}条 · ${fC>=0?"+":""}${fC}%</div><div class="mini">社群氛围积极</div></div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">📊</span> 核心指标对比</div>
  <table class="data-table">
    <tr><th>指标</th><th class="num">${prevPeriodLabel}</th><th class="num">${periodLabel}</th><th class="num">环比</th></tr>
    <tr><td>公开频道消息总量</td><td class="num">${pT}</td><td class="num">${mT}</td><td class="num ${mC>=0?"up":"down"}">${mC>=0?"📈":"📉"} ${mC>=0?"+":""}${mC}%</td></tr>
    <tr><td>日均消息</td><td class="num">${(pT/7).toFixed(0)}</td><td class="num">${(mT/7).toFixed(0)}</td><td class="num ${mC>=0?"up":"down"}">${mC>=0?"📈":"📉"} ${mC>=0?"+":""}${mC}%</td></tr>
    <tr><td>发言人数</td><td class="num">${pA}</td><td class="num">${mA}</td><td class="num ${aC>=0?"up":"down"}">${aC>=0?"📈":"📉"} ${aC>=0?"+":""}${aC}%</td></tr>
    ${rows}
  </table>
</div>

<div class="section">
  <div class="section-title"><span class="icon">🎯</span> 内容画像 (creators-exchange)</div>
  <div class="bar-chart">
    ${bars.map(t=>`<div class="bar-row"><div class="bar-label">${t.key}</div><div class="bar-fill"><div class="bar ${t.color}" style="width:${t.pct}%"></div></div><div class="bar-val">${t.count}</div><div style="min-width:60px;font-size:11px;color:${t.hex}">${t.change}</div></div>`).join("\\n    ")}
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">💬</span> 大家都在聊什么？公开频道</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
    <div>${samples.slice(0,mid).map(m=>chatBubble(m,m.category,pcts[m.category])).join("\\n")}</div>
    <div>${samples.slice(mid).map(m=>chatBubble(m,m.category,pcts[m.category])).join("\\n")}</div>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">💌</span> KOC私信 · 工作内容结构</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
    <div>${dmE.slice(0,dM).map(([n,d])=>dmBubble(n,d)).join("\\n")}</div>
    <div>${dmE.slice(dM).map(([n,d])=>dmBubble(n,d)).join("\\n")}</div>
  </div>
</div>

<div class="section">
  <div class="section-title"><span class="icon">💡</span> 关键洞察</div>
  <div class="insight-grid">
    <div class="insight-card"><div class="icon">📈</div><h4>${mC>=0?"社群活跃度提升":"社群活跃度下降"}</h4><p>公开频道消息量 ${periodLabel}: ${mT} 条（${prevPeriodLabel}: ${pT} 条），变化 ${mC>=0?"+":""}${mC}%。${mC>=5?"社群增长势头良好。":mC<-5?"需要关注可能的原因。":"基本保持稳定。"}</p></div>
    <div class="insight-card"><div class="icon">👥</div><h4>创作者参与度</h4><p>${mA} 位创作者参与讨论（${prevPeriodLabel}: ${pA} 人），${aC>=0?"社群正在扩大。":"部分创作者活跃度降低。"}</p></div>
    <div class="insight-card"><div class="icon">🎨</div><h4>内容生产趋势</h4><p>作品分享 ${wS} 条（${prevPeriodLabel}: ${pW} 条），${wC>=0?"UGC 产出活跃。":"建议鼓励更多创作分享。"}</p></div>
  </div>
</div>

<div class="section" style="text-align:center;padding:20px">
  <p style="color:#8892b0;font-size:12px">🤖 由 GitHub Actions 自动生成 · ${dateStr}</p>
  <p style="color:#8892b0;font-size:12px;margin-top:4px">Discord Bot: Mochi's bot · 数据: #creators-exchange 公开频道</p>
</div>
</div></body></html>`;
}

async function pushFeishu(current, previous, periodLabel, prevPeriodLabel) {
  if (!FEISHU_WEBHOOK) { console.log("Skip Feishu push"); return; }
  const mT=current.total_messages, pT=previous.total_messages||1, mC=((mT-pT)/pT*100).toFixed(1);
  const mA=current.total_authors, pA=previous.total_authors||1, aC=((mA-pA)/pA*100).toFixed(1);

  const card = { config:{wide_screen_mode:true}, header:{title:{tag:"plain_text",content:`📊 Yoyo Creative Studio · ${periodLabel}社区报告`},template:"blue"},
    elements:[
      {tag:"div",text:{tag:"lark_md",content:"**📈 核心数据**"}},
      {tag:"column_set",flex_mode:"none",background_style:"default",columns:[
        {tag:"column",width:"weighted",weight:1,elements:[{tag:"div",text:{tag:"lark_md",content:`**📢 公开频道消息**\\n${mT} 条\\n↗ ${mC}%`}}]},
        {tag:"column",width:"weighted",weight:1,elements:[{tag:"div",text:{tag:"lark_md",content:`**👥 发言人数**\\n${mA} 人\\n↗ ${aC}%`}}]},
        {tag:"column",width:"weighted",weight:1,elements:[{tag:"div",text:{tag:"lark_md",content:`**💬 KOC私信**\\n${KOC_DM_STATIC.total_creators}+ 人\\n${KOC_DM_STATIC.total_dm}+ 条`}}]}
      ]},
      {tag:"hr"},
      {tag:"action",actions:[{tag:"button",text:{tag:"plain_text",content:"🔗 查看完整报告"},type:"primary",url:REPORT_URL,multi_url:{url:REPORT_URL}}]},
      {tag:"note",elements:[{tag:"plain_text",content:`Yoyo Creative Studio · ${periodLabel} · 自动生成`}]}
    ]
  };
  const res = await fetch(FEISHU_WEBHOOK, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({msg_type:"interactive",card})});
  const d = await res.json();
  console.log("Feishu:", d.code===0?"✅ OK":"❌ FAIL", d);
}

async function main() {
  if (!DISCORD_TOKEN) { console.error("Missing DISCORD_BOT_TOKEN"); process.exit(1); }
  console.log("Starting weekly report...");
  const thisW = await fetchDiscordMessages(CHANNEL_IDS[0], 7);
  const lastW = await fetchDiscordMessages(CHANNEL_IDS[0], 14);
  const ids = new Set(thisW.map(m=>m.id));
  const lastOnly = lastW.filter(m=>!ids.has(m.id));
  console.log(`This: ${thisW.length}, Last: ${lastOnly.length}`);
  const cur = analyzeMessages(thisW), prev = analyzeMessages(lastOnly);

  const now = new Date();
  const ws = new Date(now); ws.setDate(ws.getDate()-ws.getDay()-6);
  const we = new Date(now); we.setDate(we.getDate()-we.getDay());
  const fmt=d=>`${d.getMonth()+1}/${d.getDate()}`;
  const periodLabel = `${fmt(ws)}-${fmt(we)}`;
  const prevFmt = d=>{const p=new Date(d);p.setDate(p.getDate()-7);const pe=new Date(p);pe.setDate(pe.getDate()+6);return `${fmt(p)}-${fmt(pe)}`;};

  const html = generateHTML(cur, prev, periodLabel, prevFmt(now));
  require("fs").writeFileSync("index.html", html, "utf-8");
  console.log("✅ Saved to index.html");
  console.log(`📊 ${periodLabel}: ${cur.total_messages} msgs, ${cur.total_authors} authors`);
  await pushFeishu(cur, prev, periodLabel, prevFmt(now));
}

main().catch(e=>{console.error("❌",e.message);process.exit(1);});