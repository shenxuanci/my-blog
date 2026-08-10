import { routeUrl } from "./router.js";

export const CATEGORY_LABELS = { ai: "AI", tech: "互联网/科技", finance: "财经", society: "社会", world: "国际" };
const CATEGORY_KEYS = Object.keys(CATEGORY_LABELS);
const STATUS_CLASSES = new Set(["已确认", "发展中", "有争议", "仅传言"]);
const CONTENT_TYPE_LABELS = { reporting: "报道", analysis: "分析", opinion: "观点" };
const MISS_REASON_LABELS = { important_event: "重要事件", deep_read: "值得深读", missing_perspective: "缺少视角" };
export const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
// 渲染的 URL 来自 LLM 管线处理过的第三方内容，管线侧 `_is_valid_http_url` 已经拦掉
// 非 http(s) 和带空白的 URL；这里再独立挡一层，别让前端的正确性依赖上游没出 bug。
// 控制字符先拒后判协议：escapeHtml 不编码制表符、换行和 NUL。引号编码其实已经
// 防住属性逃逸（实测 jsdom 解析不出多余属性），但带控制字符的 URL 本就是不该
// 渲染成链接的脏数据。与后台 `safeMarkdownUrl` 同口径，含拒掉协议相对的 `//`。
export const safeUrl = (value) => {
  const url = String(value ?? "");
  if (/[\u0000-\u001f\u007f]/.test(url) || url.startsWith("//")) return "#";
  return /^https?:\/\//i.test(url) ? escapeHtml(url) : "#";
};

function detailParagraphs(value) {
  return String(value ?? "")
    .replace(/\r\n?/g, "\n")
    .split(/\n\s*\n+/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
    .join("");
}

function annualIssue(date) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || "");
  if (!match) return "";
  const [, yearText, monthText, dayText] = match;
  const year = Number(yearText); const month = Number(monthText); const day = Number(dayText);
  const stamp = Date.UTC(year, month - 1, day);
  const parsed = new Date(stamp);
  if (parsed.getUTCFullYear() !== year || parsed.getUTCMonth() !== month - 1 || parsed.getUTCDate() !== day) return "";
  const issue = Math.floor((stamp - Date.UTC(year, 0, 1)) / 86400000) + 1;
  return `${year} · 第${issue}期`;
}

function displayDate(date) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || "");
  return match ? `${Number(match[2])}月${Number(match[3])}日` : "今日日报";
}

const BEIJING_STAMP = new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });

function detailMeta(item) {
  const time = item.time ? new Date(item.time) : null;
  const stamp = time && !Number.isNaN(time.getTime()) ? BEIJING_STAMP.format(time) : "";
  const category = CATEGORY_LABELS[item.category] || item.category || "";
  const parts = [stamp ? `发布 ${stamp}` : "", category].filter(Boolean);
  return parts.length ? `<div class="detail-meta">${parts.map((part) => `<span>${escapeHtml(part)}</span>`).join("")}</div>` : "";
}

function primarySourceLink(item) {
  const sources = item.sources?.length ? item.sources : (item.url ? [{ name: item.source || "原文", url: item.url }] : []);
  const factual = sources.find((source) => source?.type === "事实源" && /^https?:\/\//i.test(source.url || ""));
  const source = factual || sources.find((entry) => /^https?:\/\//i.test(entry?.url || ""));
  if (!source) return "";
  let host = "";
  try { host = new URL(source.url).hostname.replace(/^www\./, ""); } catch { host = ""; }
  const label = host || source.name || "原文";
  return `<a class="detail-readorigin" href="${safeUrl(source.url)}" target="_blank" rel="noopener noreferrer">↗ 阅读原文 · ${escapeHtml(label)}</a>`;
}

export function sourceLinks(item) {
  const sources = item.sources?.length ? item.sources : (item.url ? [{ name: item.source || "原文", url: item.url }] : []);
  return sources.map((source) => `<a href="${safeUrl(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.name || "原文")}</a>`).join("");
}

// 事实源排前：先看事实、再看别人的判断，与详情页「事实先行」的区块顺序同一原则。
const SOURCE_TYPE_ORDER = { 事实源: 0, 分析源: 1, 舆论源: 2 };

function relatedLinks(item) {
  const sources = item.sources?.length ? item.sources : (item.url ? [{ name: item.source || "原文", url: item.url }] : []);
  const rows = sources.filter((source) => /^https?:\/\//i.test(source?.url || ""));
  if (!rows.length) return "";
  const ordered = rows
    .map((source, index) => ({ source, index }))
    .sort((a, b) => (SOURCE_TYPE_ORDER[a.source.type] ?? 9) - (SOURCE_TYPE_ORDER[b.source.type] ?? 9) || a.index - b.index);
  return `<section class="detail-links"><h2 class="detail-sec-t">相关链接</h2><ul class="link-list">${ordered.map(({ source }) => {
    let host = "";
    try { host = new URL(source.url).hostname.replace(/^www\./, ""); } catch { host = ""; }
    const type = Object.hasOwn(SOURCE_TYPE_ORDER, source.type) ? `<span class="tag src-type${source.type === "事实源" ? " t-fact" : ""}">${escapeHtml(source.type)}</span>` : "";
    return `<li><a href="${safeUrl(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.name || host || "原文")}</a>${type}${host ? `<span class="link-host">${escapeHtml(host)}</span>` : ""}</li>`;
  }).join("")}</ul></section>`;
}

export function actionButtons(item, options = {}) {
  const { personal = false, date = "", type = "news" } = options;
  if (!personal) return "";
  const ref = escapeHtml(item.id); const event = item.event_id;
  // 渲染层的不变式：进入 HTML 的插值一律过 escapeHtml，没有例外。
  // date/type 目前由管线与路由产生，但「因为上游可信所以这里可以不转义」是一条
  // 只要上游变一次就会破的规则，不如让它扫一眼就能确认。
  const safeDate = escapeHtml(date); const safeType = escapeHtml(type);
  const key = `${date}:${item.id}`; const state = options;
  const readLater = Boolean(state.readLater?.[key]); const favorite = Boolean(state.favorites?.[key]); const liked = Boolean(state.liked?.[key]); const tracked = Boolean(event && state.tracked?.[event]);
  const readLaterButton = `<button type="button" class="act ${readLater ? "done" : ""}" data-action="read-later" data-ref="${ref}" data-date="${safeDate}" data-type="${safeType}">${readLater ? "✓ 已收" : "⏳ 稍后读"}</button>`;
  const favoriteButton = `<button type="button" class="act ${favorite ? "done" : ""}" data-action="favorite" data-ref="${ref}" data-date="${safeDate}" data-type="${safeType}">${favorite ? "★ 已藏" : "⭐ 收藏"}</button>`;
  const newsMenu = type === "news" ? `<button type="button" class="act ${liked ? "done" : ""}" data-action="like" data-ref="${ref}" data-date="${safeDate}">${liked ? "👍 已记录" : "👍 更多类似"}</button>${event ? `<button type="button" class="act ${tracked ? "done" : ""}" data-action="track" data-ref="${ref}" data-event="${escapeHtml(event)}" data-date="${safeDate}">${tracked ? "📌 追踪中" : "📌 追踪"}</button>` : ""}<button type="button" class="act" data-action="source" data-ref="${ref}" data-date="${safeDate}">🚫 来源</button>` : "";
  return `<div class="acts" aria-label="个人操作">
    ${type === "news" ? `<button type="button" class="act" data-action="not-interested" data-ref="${ref}" data-date="${safeDate}">✕ 不感兴趣</button>` : ""}
    ${favoriteButton}
    <details class="action-overflow"><summary class="act" aria-label="更多操作">⋯</summary><div class="action-menu">${readLaterButton}${newsMenu}</div></details>
  </div><div class="fb-panel" aria-live="polite"></div>`;
}

function continuationLink(item, enabled = true) {
  if (!enabled) return "";
  if (item.trusted_continuation !== true || !Number.isInteger(item.day_count) || item.day_count < 2 || !Array.isArray(item.history) || !item.history.length) return "";
  const previous = item.history[0];
  if (!/^\d{4}-\d{2}-\d{2}$/.test(previous?.date || "")) return "";
  const exact = /^(\d{4}-\d{2}-\d{2}):(.+)$/.exec(previous.item_ref || "");
  const target = exact
    ? { view: "detail", date: exact[1], type: "news", item: exact[2] }
    : { view: "reports", period: "day", date: previous.date };
  return `<a class="continuation-link" href="${routeUrl(target)}" data-route>第 ${item.day_count} 天·延续</a>`;
}

export function dailyCard(item, date, options = {}) {
  const timeline = options.timeline || null;
  const trajectoryEnabled = options.trajectoryEnabled !== false;
  return `<article class="card report-card${timeline ? ` timeline-entry${timeline.continuation ? " is-continuation" : ""}` : ""}" data-item-id="${escapeHtml(item.id)}">
    <div class="card-top">${timeline?.time ? `<time class="timeline-time" datetime="${escapeHtml(item.time || "")}">${escapeHtml(timeline.time)}</time>` : ""}<span class="tag cat-${escapeHtml(item.category)}">${escapeHtml(CATEGORY_LABELS[item.category] || item.category)}</span>${item.is_update ? '<span class="tag update-mark">重大更新</span>' : ""}${timeline?.continuation ? '<span class="continuation-mark">延续</span>' : ""}${item.status ? `<span class="tag${STATUS_CLASSES.has(item.status) ? ` st-${item.status}` : ""}">${escapeHtml(item.status)}</span>` : ""}${continuationLink(item, trajectoryEnabled)}${Number.isFinite(item.score) ? `<span class="score-num">${item.score}</span>` : ""}</div>
    <h3><a href="${routeUrl({ view: "detail", date, type: "news", item: item.id })}" data-route>${escapeHtml(item.title)}</a></h3>
    ${item.summary ? `<p class="sum">${escapeHtml(item.summary)}</p>` : ""}
    ${trajectoryEnabled && item.watch ? `<div class="kv watch"><b>走向：</b>${escapeHtml(item.watch)}</div>` : ""}
    <div class="srcs">${sourceLinks(item)}</div>${actionButtons(item, { ...options, date, type: "news" })}
  </article>`;
}

function textMinutes(parts) {
  const length = parts.filter((part) => typeof part === "string" && part).join("").length;
  return Math.max(1, Math.ceil(length / 300));
}

function coreReadMinutes(data, picks) {
  const trajectoryEnabled = data.trajectory_enabled !== false;
  return textMinutes([
    data.lead || data.brief,
    ...(data.themes || []).slice(0, 3).flatMap((theme) => [theme.title, theme.overview || theme.one_liner]),
    ...picks.flatMap((item) => [item.title, item.summary, trajectoryEnabled ? item.watch : ""]),
  ]);
}

function supplementalReadMinutes(data) {
  const contentParts = (items, type) => (items || []).flatMap((item) => [
    item.title_zh || item.title,
    item.summary || item.brief || item.why_hot,
    item.why || item.takeaway || (type === "opinion" ? item.mechanism : ""),
  ]);
  return textMinutes([
    ...(data.tracking || []).flatMap((item) => [item.title, ...(item.history || []).map((row) => row.summary)]),
    ...contentParts(data.deep, "deep"),
    ...contentParts(data.papers, "paper"),
    ...contentParts(data.opinion, "opinion"),
    ...(data.items || []).filter((item) => item.tier === "more").flatMap((item) => [item.title, item.summary]),
  ]);
}

function contentCard(item, type, date, options) {
  const title = item.title_zh || item.title || item.summary || "未命名";
  const detail = type === "opinion" ? "" : routeUrl({ view: "detail", date, type, item: item.id });
  const contentType = type === "deep" && Object.hasOwn(CONTENT_TYPE_LABELS, item.content_type) ? `<span class="tag content-type">${CONTENT_TYPE_LABELS[item.content_type]}</span>` : "";
  return `<article class="deep ${type === "paper" ? "paper" : type === "opinion" ? "pulse" : ""}" data-item-id="${escapeHtml(item.id)}">
    ${contentType}
    <h3>${detail ? `<a href="${detail}" data-route>${escapeHtml(title)}</a>` : escapeHtml(title)}</h3>
    ${item.summary || item.brief || item.why_hot ? `<p>${escapeHtml(item.summary || item.brief || item.why_hot)}</p>` : ""}${item.why || item.takeaway || (type === "opinion" && item.mechanism) ? `<div class="kv why"><b>${type === "opinion" ? "传播机制" : "值得读"}：</b>${escapeHtml(item.why || item.takeaway || item.mechanism)}</div>` : ""}
    <div class="srcs">${sourceLinks(item)}</div>${type !== "opinion" ? actionButtons(item, { ...options, date, type }) : ""}
  </article>`;
}

export function collectionCard(item, type, date, options = {}) {
  return type === "news" ? dailyCard(item, date, options) : contentCard(item, type, date, options);
}

function trackingCard(item, date, options) {
  return `<article class="trk"><div class="trk-top"><h3>${escapeHtml(item.title)}</h3>${options.personal ? `<button type="button" class="act" data-action="untrack" data-event="${escapeHtml(item.event_id)}" data-date="${escapeHtml(date)}">取消追踪</button>` : ""}</div><div class="trk-hist">${(item.history || []).map((row) => `<p><a href="${routeUrl({ view: "reports", period: "day", date: row.date })}" data-route>${escapeHtml(row.date)}</a> ${escapeHtml(row.summary)}</p>`).join("") || "暂无进展"}</div></article>`;
}

function moreCard(item, date) {
  const url = item.url || item.sources?.[0]?.url;
  return `<article class="row"><strong>${escapeHtml(item.title)}</strong>${item.summary ? `<span>${escapeHtml(item.summary)}</span>` : ""}${url ? `<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">原文</a>` : ""}<a href="${routeUrl({ view: "detail", date, type: "news", item: item.id })}" data-route>详情</a></article>`;
}

function renderMissRow(entry, { showDate = false } = {}) {
  const label = MISS_REASON_LABELS[entry.reason] || "";
  const content = entry.url
    ? `<a href="${safeUrl(entry.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(entry.title || entry.url)}</a>`
    : `<span>${escapeHtml(entry.title || "")}</span>`;
  return `<div class="miss-row">${showDate ? `<time datetime="${escapeHtml(entry.date)}">${escapeHtml(entry.date)}</time>` : ""}<span class="tag">${escapeHtml(label)}</span>${content}<button type="button" class="act" data-action="remove-miss" data-id="${escapeHtml(entry.id)}">撤销</button></div>`;
}

function renderMissesTool(date, entries = [], loadError = "") {
  const rows = entries
    .filter((entry) => entry?.date === date && entry.id)
    .sort((a, b) => String(b.ts || "").localeCompare(String(a.ts || "")));
  return `<section class="misses-tool" aria-labelledby="misses-title">
    <div class="misses-head"><div><h2 id="misses-title">补记遗漏</h2><p>记录会写入公开仓库，请勿填写隐私信息。</p></div></div>
    ${loadError ? `<p class="misses-error" role="alert">已有遗漏加载失败：${escapeHtml(loadError)}。<button type="button" class="act" data-action="retry-misses">重试</button></p>` : ""}
    <div class="misses-form">
      <label>标题（与链接至少填一项）<input type="text" maxlength="200" data-miss-field="title"></label>
      <label>链接（可选）<input type="url" maxlength="500" placeholder="https://" data-miss-field="url"></label>
      <label>原因<select data-miss-field="reason">${Object.entries(MISS_REASON_LABELS).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}</select></label>
      <button type="button" class="fb-go" data-action="submit-miss" data-date="${escapeHtml(date)}">记录遗漏</button>
    </div>
    ${rows.length ? `<div class="misses-list">${rows.map((entry) => renderMissRow(entry)).join("")}</div>` : ""}
  </section>`;
}

export function renderDailyReport(data, options = {}) {
  if (!data) return '<div class="empty" role="status">暂无日报数据</div>';
  const hidden = options.hidden || {};
  const picks = (data.items || []).filter((item) => item.tier === "pick" && !hidden[`${data.date}:${item.id}`]);
  const hiddenCount = (data.items || []).filter((item) => item.tier === "pick" && hidden[`${data.date}:${item.id}`]).length;
  const renderOptions = { ...options, trajectoryEnabled: data.trajectory_enabled !== false };
  const continued = renderOptions.trajectoryEnabled ? picks.filter((item) => item.trusted_continuation === true && Number(item.day_count || 0) >= 2).length : 0;
  const sections = CATEGORY_KEYS.map((category) => {
    const rows = picks.filter((item) => item.category === category);
    return `<section class="report-section" data-category="${category}" aria-labelledby="cat-${category}"><h2 id="cat-${category}" class="sec-title">${CATEGORY_LABELS[category]} <span class="n">${rows.length} 篇</span></h2><div class="report-list">${rows.length ? rows.map((item) => dailyCard(item, data.date, renderOptions)).join("") : '<p class="section-empty">今日暂无精选</p>'}</div></section>`;
  }).join("");
  const themes = (data.themes || []).slice(0, 3);
  const jumpLinks = CATEGORY_KEYS.map((category) => {
    const count = picks.filter((item) => item.category === category).length;
    return count ? `<a href="#cat-${category}">${CATEGORY_LABELS[category]} ${count}</a>` : "";
  }).filter(Boolean).join("");
  const deepItems = data.deep || [];
  const deepMinutes = deepItems.reduce((total, item) => total + (Number.isFinite(item.read_minutes) && item.read_minutes > 0 ? item.read_minutes : 0), 0);
  const tracked = options.tracked || {};
  const trackedItems = (data.tracking || []).filter(
    (item) => !Object.hasOwn(tracked, item.event_id) || tracked[item.event_id] !== false,
  );
  const supplementary = [
    ["追踪中", "tracking", trackedItems.map((item) => trackingCard(item, data.date, options)), ""],
    ["深度阅读", "deep", deepItems.map((item) => contentCard(item, "deep", data.date, options)), deepMinutes ? `<span class="n">${deepItems.length} 篇 · 原文约 ${deepMinutes} 分钟</span>` : ""],
    ["今日论文", "papers", (data.papers || []).map((item) => contentCard(item, "paper", data.date, options)), ""],
    ["舆论观察", "opinion", (data.opinion || []).map((item) => contentCard(item, "opinion", data.date, options)), ""],
    ["更多资讯", "more", (data.items || []).filter((item) => item.tier === "more").map((item) => moreCard(item, data.date)), ""],
  ].filter(([, , rows]) => rows.length).map(([title, kind, rows, meta]) => `<section class="supplemental" data-kind="${kind}"><h2 class="sec-title">${title}${meta ? ` ${meta}` : ""}</h2><div class="more-list">${rows.join("")}</div></section>`).join("");
  const supplementalLoad = supplementary ? `<div class="supplemental-load">附栏导读约 ${supplementalReadMinutes(data)} 分钟</div>` : "";
  const dateLabel = displayDate(data.date); const issue = annualIssue(data.date);
  const missesTool = options.personal ? renderMissesTool(data.date, options.misses, options.missesError) : "";
  return `<article class="daily-report"><header class="masthead"><div class="mast-plate"><span class="date-seal" aria-hidden="true"><b>${dateLabel.replace("月", "月<br>")}</b></span><span class="mast-name">每日驾驶舱</span>${issue ? `<span class="mast-issue">${issue}</span>` : ""}</div><div class="mast-meta"><time datetime="${escapeHtml(data.date || "")}">${escapeHtml(dateLabel)}</time><span>核心日报约 ${coreReadMinutes(data, picks)} 分钟</span><span>今日新事件 <b>${picks.length - continued}</b></span><span>延续事件 <b>${continued}</b></span></div><h1 class="mast-lead">${escapeHtml(data.lead || data.brief || "今日日报")}</h1></header>${missesTool}${themes.length ? `<section class="mainlines"><h2 class="ml-h">今日主线</h2>${themes.map((theme) => `<article class="ml-item"><h3 class="ml-t">${escapeHtml(theme.title)}</h3><p class="ml-o">${escapeHtml(theme.overview || theme.one_liner || "")}</p></article>`).join("")}</section>` : ""}${jumpLinks ? `<nav class="report-jump" aria-label="日报类目跳转">${jumpLinks}</nav>` : ""}${hiddenCount ? `<div class="hidden-bar">已隐藏 ${hiddenCount} 条 <button type="button" class="act" data-action="restore-hidden" data-date="${escapeHtml(data.date)}">全部恢复</button></div>` : ""}${sections}${supplementalLoad}${supplementary}</article>`;
}

function trajectoryRecap(context) {
  if (typeof context !== "string" || !context) return null;
  const match = /(^|[。！？\n])走向回对（(兑现|部分兑现|未兑现|反转)）：([^。！？\n]+[。！？]?)$/u.exec(context);
  if (!match) return null;
  return {
    context: `${context.slice(0, match.index)}${match[1]}`.trim(),
    status: match[2],
    text: match[3].trim(),
  };
}

function claimsHtml(item) {
  const claims = (item.claims || []).filter((claim) => claim?.text);
  const kindLabels = { fact: "事实", analysis: "分析", uncertain: "待核实" };
  return claims.length ? `<section><h2 class="detail-sec-t">事实与判断</h2><ul class="detail-claims">${claims.map((claim) => {
    const kind = Object.hasOwn(kindLabels, claim.kind) ? claim.kind : "uncertain";
    const sources = Array.isArray(claim.sources) ? claim.sources.filter((source) => typeof source === "string" && source.trim()) : [];
    return `<li class="detail-claim kind-${kind}"><span class="claim-kind">${kindLabels[kind]}</span>${escapeHtml(claim.text)}${sources.length ? `<div class="claim-sources">来源：${sources.map(escapeHtml).join("、")}</div>` : ""}</li>`;
  }).join("")}</ul></section>` : "";
}

function evidenceHtml(item) {
  const evidence = item.evidence;
  const basisLabels = { fulltext: "全文证据", mixed: "混合证据", snippet: "摘要证据" };
  const sources = item.sources;
  if (!evidence || typeof evidence !== "object" || Array.isArray(evidence)
    || !Object.hasOwn(basisLabels, evidence.basis)
    || typeof evidence.degraded !== "boolean"
    || !Number.isInteger(evidence.publisher_count) || evidence.publisher_count < 1
    || !Number.isInteger(evidence.independent_chain_count) || evidence.independent_chain_count < 0
    || evidence.independent_chain_count > evidence.publisher_count
    || !Array.isArray(sources) || sources.length === 0) return "";
  const mappingValid = sources.every((source) => source && typeof source === "object" && !Array.isArray(source)
    && typeof source.name === "string" && source.name.trim()
    && typeof source.url === "string" && source.url.trim()
    && (source.evidence_basis === "fulltext" || source.evidence_basis === "snippet")
    && (!Object.hasOwn(source, "evidence_chain")
      || (typeof source.evidence_chain === "string" && source.evidence_chain.trim())));
  if (!mappingValid) return "";
  const publisherKeys = sources.map((source) => source.name.trim().toLocaleLowerCase());
  const sourceUrls = sources.map((source) => source.url.trim());
  if (new Set(publisherKeys).size !== sources.length || new Set(sourceUrls).size !== sources.length) return "";
  const chainKeys = new Set(sources
    .filter((source) => Object.hasOwn(source, "evidence_chain"))
    .map((source) => source.evidence_chain.trim().toLocaleLowerCase()));
  const sourceBases = sources.map((source) => source.evidence_basis);
  const derivedBasis = sourceBases.every((basis) => basis === "fulltext")
    ? "fulltext" : sourceBases.some((basis) => basis === "fulltext") ? "mixed" : "snippet";
  if (evidence.publisher_count !== publisherKeys.length
    || evidence.independent_chain_count !== chainKeys.size
    || evidence.basis !== derivedBasis) return "";
  const publishers = evidence.publisher_count === 1 ? "单一发布源" : `${evidence.publisher_count} 个发布源`;
  return `<section class="detail-evidence" aria-label="证据概览"><h2 class="detail-sec-t">证据概览</h2><div class="evidence-meta"><span>${publishers}</span><span>独立证据链 ${evidence.independent_chain_count} 条</span><span>${basisLabels[evidence.basis]}</span>${evidence.degraded === true ? '<span class="evidence-degraded">证据降级</span>' : ""}</div></section>`;
}

export function renderDetail(item, type = "news", date = "", options = {}) {
  if (!item) return '<div class="empty">找不到这条内容（可能数据未加载）</div>';
  const title = item.title_zh || item.title;
  // news 也走 lede：摘要是详情页唯一 100% 有的字段，而搜索、周报引用、延续链接
  // 这三条入口进来时读者没见过卡片，删掉就是纯丢信息。降级成无标题导语既去掉
  // 与卡片的「重复区块」观感，又一个字不丢。
  const common = (item.summary || item.brief) ? `<p class="detail-lede">${escapeHtml(item.summary || item.brief)}</p>` : "";
  const update = type === "news" && item.is_update ? `<div class="detail-update"><b>重大更新</b>${item.first_seen ? ` · 首次收录：${escapeHtml(item.first_seen)}` : ""}</div>` : "";
  let body = "";
  if (type === "news") {
    const recapData = item.trusted_continuation === true ? trajectoryRecap(item.context) : null;
    const contextText = recapData ? recapData.context : item.context;
    const contextLabel = item.trusted_continuation === true ? "来龙" : "起因";
    const context = contextText ? `<section data-trajectory="context"><h2 class="detail-sec-t">${contextLabel}</h2><div class="kv detail-body">${detailParagraphs(contextText)}</div></section>` : "";
    const bodyPart = item.detail ? `<section data-trajectory="body"><h2 class="detail-sec-t">现状</h2><div class="detail-body">${detailParagraphs(item.detail)}</div></section>` : "";
    const recap = recapData ? `<div class="trajectory-recap recap-${recapData.status}"><span>走向回对 · ${recapData.status}</span>${escapeHtml(recapData.text)}</div>` : "";
    const watchText = typeof item.watch_detail === "string" && item.watch_detail.trim()
      ? item.watch_detail : item.watch;
    const watch = watchText ? `<section data-trajectory="watch"><h2 class="detail-sec-t">走向</h2><div class="kv watch detail-body">${detailParagraphs(watchText)}</div></section>` : "";
    body = `<div class="detail-trajectory">${context}${bodyPart}${recap}${watch}</div>${evidenceHtml(item)}${claimsHtml(item)}`;
  }
  if (type === "deep") body = `${item.why ? `<div class="kv why"><b>为什么值得读：</b>${escapeHtml(item.why)}</div>` : ""}${item.takeaway ? `<div class="detail-takeaway"><b>核心观点：</b>${escapeHtml(item.takeaway)}</div>` : ""}${(item.key_points || []).length ? `<section><h2 class="detail-sec-t">关键点</h2><ul>${item.key_points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul></section>` : ""}${item.audience ? `<div class="kv"><b>适合读者：</b>${escapeHtml(item.audience)}</div>` : ""}`;
  if (type === "paper") body = `${item.why ? `<div class="kv why"><b>为什么值得读：</b>${escapeHtml(item.why)}</div>` : ""}${item.takeaway ? `<div class="detail-takeaway"><b>研究结论：</b>${escapeHtml(item.takeaway)}</div>` : ""}${[["贡献", item.contribution], ["证据", item.evidence], ["局限", item.limitations]].filter(([, value]) => value).map(([label, value]) => `<div class="kv"><b>${label}：</b>${escapeHtml(value)}</div>`).join("")}`;
  const head = type === "news" ? `${detailMeta(item)}${primarySourceLink(item)}` : "";
  const sources = type === "news" ? relatedLinks(item) : `<div class="srcs">${sourceLinks(item)}</div>`;
  return `<article class="detail-wrap reading-view"><a class="dback" href="${routeUrl({ view: "reports", period: "day", date })}" data-route>← 返回 ${escapeHtml(date)} 当日</a><h1 class="detail-title">${escapeHtml(title)}</h1>${head}${common}${update}${body}${sources}${actionButtons(item, { ...options, date, type })}</article>`;
}

function refLink(ref, title) { const [date, ...rest] = String(ref || "").split(":"); const item = rest.join(":"); if (!date || !item) return ""; const type = item.startsWith("deep-") ? "deep" : item.startsWith("paper-") ? "paper" : "news"; return `<a data-ref="${escapeHtml(ref)}" href="${routeUrl({ view: "detail", date, type, item })}" data-route>${escapeHtml(title || ref)}</a>`; }

function isoWeekRange(week) {
  const match = /^(\d{4})-W(\d{2})$/.exec(week || "");
  if (!match) return null;
  const year = Number(match[1]); const weekNumber = Number(match[2]);
  if (weekNumber < 1 || weekNumber > 53) return null;
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const jan4Day = jan4.getUTCDay() || 7;
  const start = new Date(jan4);
  start.setUTCDate(jan4.getUTCDate() - jan4Day + 1 + (weekNumber - 1) * 7);
  const end = new Date(start);
  end.setUTCDate(start.getUTCDate() + 6);
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)];
}

function renderWeeklyMisses(week, entries = [], loadError = "") {
  const range = isoWeekRange(week);
  const rows = range ? entries
    .filter((entry) => entry?.id && entry.date >= range[0] && entry.date <= range[1])
    .sort((a, b) => String(b.date || "").localeCompare(String(a.date || ""))
      || String(b.ts || "").localeCompare(String(a.ts || ""))) : [];
  const counts = Object.fromEntries(Object.keys(MISS_REASON_LABELS).map((reason) => [
    reason,
    rows.filter((entry) => entry.reason === reason).length,
  ]));
  const summary = Object.entries(MISS_REASON_LABELS)
    .filter(([reason]) => counts[reason])
    .map(([reason, label]) => `<span>${label} ${counts[reason]}</span>`)
    .join("");
  return `<section class="weekly-section weekly-misses"><h2 class="sec-title">近 7 天遗漏</h2>
    ${loadError ? `<p class="misses-error" role="alert">遗漏记录加载失败：${escapeHtml(loadError)}。<button type="button" class="act" data-action="retry-misses">重试</button></p>` : ""}
    ${summary ? `<div class="misses-summary">${summary}</div>` : ""}
    <div class="misses-list">${rows.length ? rows.map((entry) => renderMissRow(entry, { showDate: true })).join("") : '<p class="section-empty">近 7 天暂无补记遗漏</p>'}</div>
  </section>`;
}

export function renderWeeklyReport(data, options = {}) {
  if (!data) return '<div class="empty" role="status">暂无周报数据</div>';
  const coverage = data.coverage || {}; const lead = typeof data.lead === "string" ? { title: data.lead } : (data.lead || {}); const stats = data.stats || {}; const missing = coverage.missing_dates || [];
  const reading = Array.isArray(data.reading) ? data.reading : [
    ...(data.reading?.deep || []), ...(data.reading?.papers || []),
    ...(data.reading?.deep_refs || []).map((ref) => ({ ref, title: "深度阅读" })),
    ...(data.reading?.paper_refs || []).map((ref) => ({ ref, title: "研究论文" })),
  ];
  const missesPanel = options.personal
    ? renderWeeklyMisses(data.week, options.misses, options.missesError)
    : "";
  return `<article class="weekly-report weekly-reading"><header class="brief"><div class="bt">${escapeHtml(data.week || "周报")}</div><h1>${escapeHtml(lead.title || "本周综述")}</h1>${lead.summary ? `<p>${escapeHtml(lead.summary)}</p>` : ""}${coverage.daily_count != null ? `<p class="coverage">覆盖 ${coverage.daily_count}/${coverage.expected_days || 7} 期${missing.length ? ` · 缺失：${missing.map(escapeHtml).join("、")}` : ""}</p>` : ""}</header>${missesPanel}${Object.keys(stats).length ? `<dl class="weekly-stats"><div><dt>精选</dt><dd>${escapeHtml(stats.pick_count ?? 0)}</dd></div><div><dt>独立事件</dt><dd>${escapeHtml(stats.event_count ?? stats.unique_event_count ?? 0)}</dd></div><div><dt>信源</dt><dd>${escapeHtml(stats.source_count ?? 0)}</dd></div><div><dt>阅读</dt><dd>${escapeHtml(stats.read_minutes ?? 0)} 分钟</dd></div></dl>` : ""}<section class="weekly-section weekly-threads"><h2 class="sec-title">动态主题</h2>${(data.threads || []).map((thread) => `<article class="wk-thread"><h3>${escapeHtml(thread.title)} ${thread.direction ? `<span class="tag dir-${escapeHtml(thread.direction)}">${escapeHtml(thread.direction)}</span>` : ""}</h3><p>${escapeHtml(thread.summary || thread.one_liner || thread.detail || "")}</p><div class="representatives">${(thread.representative_refs || []).map((ref) => refLink(ref, "代表报道")).join("")}</div></article>`).join("") || '<p class="section-empty">暂无主题</p>'}</section>${(data.watch_recap || []).length ? `<section class="weekly-section"><h2 class="sec-title">上周判断回收</h2>${data.watch_recap.map((row) => `<article class="wk-recap"><strong>${escapeHtml(row.title || row.watch)}</strong><span>${escapeHtml(row.note || row.result || "")}</span>${(row.evidence_refs || []).map((ref) => refLink(ref, "支撑报道")).join("")}</article>`).join("")}</section>` : ""}${reading.length ? `<section class="weekly-section"><h2 class="sec-title">本周值得读</h2><div class="reading-list">${reading.map((row) => refLink(row.ref || row.item_ref, row.title || row.ref)).join("")}</div></section>` : ""}${(data.outlook || []).length ? `<section class="weekly-section"><h2 class="sec-title">下周信号</h2><ul>${data.outlook.map((row) => `<li>${escapeHtml(typeof row === "string" ? row : row.text || row.title)}</li>`).join("")}</ul></section>` : ""}</article>`;
}
