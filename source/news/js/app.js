import { announce, installMobileSearch, installThemeToggles, updateNavigation } from "./accessibility.js";
import { createAllState, renderAllDynamics, decoratePickedEntries } from "./all-view.js";
import { createApiClient } from "./api-client.js";
import { browserDataApi } from "./data-loader.js";
import { renderFavorites } from "./favorites-view.js";
import { installPersonalActions } from "./personal-actions.js";
import { installReadLater } from "./read-later.js";
import { renderDailyReport, renderDetail, renderWeeklyReport } from "./reports.js";
import { parseRoute, routeUrl } from "./router.js";
import { installSearch } from "./search-view.js";
import { createStorage, STORAGE_KEYS } from "./storage.js";
import { createTimelineState, renderTimeline } from "./timeline-view.js";
import { installTopicInteractions, renderTopics } from "./topics-view.js";

export async function resolvePersonalSession(fetchFn, setTimeoutFn = setTimeout, clearTimeoutFn = clearTimeout, timeoutMs = 800) {
  let timer;
  try {
    return await Promise.race([
      Promise.resolve()
        .then(() => fetchFn("/api/adminSession", { credentials: "same-origin" }))
        .then((response) => response.ok)
        .catch(() => false),
      new Promise((resolve) => { timer = setTimeoutFn(() => resolve(false), timeoutMs); }),
    ]);
  } finally {
    if (timer !== undefined) clearTimeoutFn(timer);
  }
}

export function createNewsApp(options) {
  const win = options.window; const doc = options.document; const dataApi = options.dataApi || browserDataApi;
  try { win.localStorage.removeItem("aoiblog_admin_token"); } catch (_) {}
  const dailyManifest = options.manifests?.daily ?? win.NEWS_MANIFEST ?? [];
  const personal = Boolean(options.personal);
  const timelineApi = options.timelineApi || win.NewsTimeline;
  const storage = createStorage(win.localStorage); const fetchFn = options.fetch || win.fetch?.bind(win) || globalThis.fetch;
  const api = createApiClient({ fetch: fetchFn }); const app = doc.getElementById("app"); const itemIndex = new Map();
  let pending = Promise.resolve(); let started = false; let currentRoute = null;
  const timelineState = createTimelineState(); const allState = createAllState(); const favoritesState = { type: "all" };
  let renderRequest = 0; let timelineSearchTimer = null; let timelineCaret = 0; let restoreTimelineFocus = false;
  let allSearchTimer = null; let allCaret = 0; let restoreAllFocus = false;
  const trackPromise = (promise) => { pending = Promise.resolve(promise); return pending; };
  const isCurrent = (requestId) => requestId === renderRequest;
  const idle = async () => { await pending; await Promise.resolve(); };
  const toast = (message, error = false) => { const node = doc.createElement("div"); node.className = `toast${error ? " err" : ""}`; node.textContent = message; doc.body.appendChild(node); win.setTimeout(() => node.remove(), 2600); };

  function indexData(data, date) {
    for (const bucket of [data?.items, data?.deep, data?.papers, data?.opinion]) for (const item of bucket || []) itemIndex.set(`${date}:${item.id}`, { ...item, _date: date });
  }
  const resolveItem = (date, id) => itemIndex.get(`${date}:${id}`);
  const personalState = () => ({ readLater: storage.get(STORAGE_KEYS.readLater), favorites: storage.get(STORAGE_KEYS.favorites), liked: storage.get(STORAGE_KEYS.liked), tracked: storage.get(STORAGE_KEYS.tracked) });
  const loadMisses = () => personal
    ? api.get("misses")
      .then((state) => ({ state, error: "" }))
      .catch((error) => ({ state: { entries: [] }, error: String(error?.message || error) }))
    : Promise.resolve({ state: { entries: [] }, error: "" });
  const prefersReducedMotion = () => Boolean(win.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  const scrollTop = () => {
    if (/jsdom/i.test(win.navigator?.userAgent || "")) return;
    (options.scrollTo || win.scrollTo)?.call(win, { top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
  };

  function replaceSelectOptions(select, values, label = (value) => value) {
    if (!select) return;
    const optionNodes = values.map((value) => {
      const option = doc.createElement("option");
      option.value = String(value);
      option.textContent = String(label(value));
      return option;
    });
    select.replaceChildren(...optionNodes);
  }

  function syncChrome(route) {
    const active = route.view === "detail" ? "reports" : route.view;
    doc.body?.classList.toggle("reports-view", route.view === "reports");
    updateNavigation(doc, active);
    const controls = doc.getElementById("reportControls"); if (controls) controls.hidden = route.view !== "reports";
    const dayArchive = doc.getElementById("dayArchive"); if (dayArchive) dayArchive.hidden = route.view !== "reports" || route.period === "week";
    const weekArchive = doc.getElementById("weekArchive"); if (weekArchive) weekArchive.hidden = route.view !== "reports" || route.period !== "week";
    const dayControls = doc.getElementById("dayCtrls"); if (dayControls) dayControls.hidden = route.view !== "reports" || route.period === "week";
    doc.querySelectorAll("[data-period]").forEach((node) => { if (node.dataset.period === route.period) node.setAttribute("aria-current", "page"); else node.removeAttribute("aria-current"); });
  }

  async function renderRoute() {
    const requestId = ++renderRequest;
    let route = parseRoute(win.location.search); currentRoute = route; syncChrome(route);
    try {
      if (route.view === "reports" && route.period === "day") {
        const date = route.date || dailyManifest[0];
        if (!date) { app.innerHTML = '<div class="empty" role="status">还没有任何日报数据。</div>'; return; }
        if (!route.date || win.location.search !== routeUrl({ ...route, date })) win.history.replaceState({}, "", routeUrl({ ...route, date }));
        const [data, missesResult] = await Promise.all([
          dataApi.daily(date),
          loadMisses(),
        ]);
        if (!isCurrent(requestId)) return; indexData(data, date); storage.markSeen(date);
        const select = doc.getElementById("dateSel"); if (select) { select.value = date; const option = [...select.options].find((node) => node.value === date); if (option && !option.textContent.startsWith("✓ ")) option.textContent = `✓ ${date}`; }
        app.innerHTML = renderDailyReport(data, { personal, misses: missesResult.state.entries || [], missesError: missesResult.error, hidden: storage.get(STORAGE_KEYS.hidden), ...personalState() }); announce(`已加载 ${date} 日报`, doc); currentRoute = { ...route, date }; return;
      }
      if (route.view === "reports" && route.period === "week") {
        const weeks = await dataApi.weeklyManifest(); if (!isCurrent(requestId)) return; const select = doc.getElementById("weekSel"); replaceSelectOptions(select, weeks);
        const week = route.week || weeks[0]; if (!week) { app.innerHTML = '<div class="empty" role="status">暂无周报数据</div>'; return; }
        if (!route.week || win.location.search !== routeUrl({ ...route, week })) win.history.replaceState({}, "", routeUrl({ ...route, week }));
        const [weekly, missesResult] = await Promise.all([
          dataApi.weekly(week),
          loadMisses(),
        ]);
        if (!isCurrent(requestId)) return; if (select) select.value = week; app.innerHTML = renderWeeklyReport(weekly, { personal, misses: missesResult.state.entries || [], missesError: missesResult.error }); announce(`已加载 ${week} 周报`, doc); currentRoute = { ...route, week }; return;
      }
      if (route.view === "detail") {
        const data = await dataApi.daily(route.date); if (!isCurrent(requestId)) return; indexData(data, route.date); const bucket = route.type === "deep" ? "deep" : route.type === "paper" ? "papers" : "items"; const item = (data?.[bucket] || []).find((row) => row.id === route.item);
        app.innerHTML = renderDetail(item, route.type, route.date, { personal, ...personalState() }); announce(item ? `已打开 ${item.title_zh || item.title}` : "找不到这条内容", doc); return;
      }
      if (route.view === "timeline") { const tag = new URLSearchParams(win.location.search).get("tag"); if (tag) timelineState.tag = tag; const html = await renderTimeline({ dates: dailyManifest, dataApi, hidden: storage.get(STORAGE_KEYS.hidden), personal, state: timelineState, onData: (data, date) => { if (isCurrent(requestId)) indexData(data, date); }, timelineApi, now: options.now, ...personalState() }); if (!isCurrent(requestId)) return; app.innerHTML = html; if (restoreTimelineFocus) { const input = doc.getElementById("timelineSearch"); input?.focus(); input?.setSelectionRange(timelineCaret, timelineCaret); restoreTimelineFocus = false; } }
      else if (route.view === "all") { const html = await renderAllDynamics({ dataApi, state: allState }); if (!isCurrent(requestId)) return; app.innerHTML = html; if (restoreAllFocus) { const input = app.querySelector('[data-all-action="search"]'); input?.focus(); input?.setSelectionRange(allCaret, allCaret); restoreAllFocus = false; } const latest = app.querySelector(".all-day[data-date]")?.dataset.date; if (latest) decoratePickedEntries({ dataApi, root: app, date: latest, stillCurrent: () => isCurrent(requestId) }); }
      else if (route.view === "topics") { const html = await renderTopics({ dataApi, personal, tracked: storage.get(STORAGE_KEYS.tracked) }); if (!isCurrent(requestId)) return; app.innerHTML = html; }
      else if (route.view === "favs") {
        if (!personal) { app.innerHTML = '<section><h1>收藏</h1><div class="empty" role="status">登录后可查看收藏</div></section>'; }
        else { const html = await renderFavorites({ storage, dataApi, api, personal, state: favoritesState, isCurrent: () => isCurrent(requestId), onData: indexData, ...personalState() }); if (!isCurrent(requestId)) return; app.innerHTML = html; }
      }
      else { win.history.replaceState({}, "", routeUrl({ view: "timeline" })); const html = await renderTimeline({ dates: dailyManifest, dataApi, hidden: storage.get(STORAGE_KEYS.hidden), personal, state: timelineState, onData: indexData, timelineApi, now: options.now, ...personalState() }); if (requestId === renderRequest) app.innerHTML = html; }
    } catch (error) {
      if (!isCurrent(requestId)) return;
      app.innerHTML = '<div class="empty" role="alert"></div>';
      app.firstElementChild.textContent = `加载失败：${String(error?.message || error)}`;
    }
  }

  function rerender() { return trackPromise(renderRoute()); }
  async function go(route, { replace = false } = {}) { win.history[replace ? "replaceState" : "pushState"]({}, "", routeUrl(route)); await rerender(); scrollTop(); }

  function install() {
    if (started) return; started = true;
    installMobileSearch(doc);
    installThemeToggles(doc, win);
    const dateSelect = doc.getElementById("dateSel"); if (dateSelect) { replaceSelectOptions(dateSelect, dailyManifest, (date) => `${storage.get(STORAGE_KEYS.seenDays)[date] ? "✓ " : ""}${date}`); dateSelect.addEventListener("change", () => go({ view: "reports", period: "day", date: dateSelect.value })); }
    doc.getElementById("weekSel")?.addEventListener("change", (event) => go({ view: "reports", period: "week", week: event.target.value }));
    doc.getElementById("prevBtn")?.addEventListener("click", () => { const index = dailyManifest.indexOf(currentRoute?.date); if (index < dailyManifest.length - 1) go({ view: "reports", period: "day", date: dailyManifest[index + 1] }); });
    doc.getElementById("nextBtn")?.addEventListener("click", () => { const index = dailyManifest.indexOf(currentRoute?.date); if (index > 0) go({ view: "reports", period: "day", date: dailyManifest[index - 1] }); });
    doc.addEventListener("click", (event) => { const link = event.target.closest("a[data-route]"); if (!link) return; event.preventDefault(); const url = new URL(link.href, win.location.href); win.history.pushState({}, "", `${url.pathname}${url.search}`); rerender(); });
    app.addEventListener("click", (event) => {
      const timeline = event.target.closest("button[data-timeline-action]");
      if (timeline) { const action = timeline.dataset.timelineAction; if (action === "more") timelineState.days += 5; if (action === "set-cat") { timelineState.cat = timeline.dataset.value; timelineState.tag = null; } if (action === "set-tag") timelineState.tag = timelineState.tag === timeline.dataset.value ? null : timeline.dataset.value; rerender(); return; }
      const all = event.target.closest("button[data-all-action]");
      if (all) { const action = all.dataset.allAction; if (action === "more") allState.days += 7; if (action === "show-all") allState.showAll = !allState.showAll; if (action === "set-cat") allState.cat = all.dataset.value; rerender(); }
      const favorite = event.target.closest("button[data-favorites-action]");
      if (favorite) { favoritesState.type = favorite.dataset.value; rerender(); }
    });
    app.addEventListener("input", (event) => { if (event.target.matches('[data-timeline-action="search"]')) { timelineState.query = event.target.value.trim(); timelineCaret = event.target.selectionStart ?? timelineState.query.length; restoreTimelineFocus = true; renderRequest++; win.clearTimeout(timelineSearchTimer); const delayed = new Promise((resolve) => { timelineSearchTimer = win.setTimeout(() => Promise.resolve(renderRoute()).finally(resolve), 120); }); trackPromise(delayed); } else if (event.target.matches('[data-all-action="search"]')) { allState.query = event.target.value.trim(); allCaret = event.target.selectionStart ?? allState.query.length; restoreAllFocus = true; renderRequest++; win.clearTimeout(allSearchTimer); const delayed = new Promise((resolve) => { allSearchTimer = win.setTimeout(() => Promise.resolve(renderRoute()).finally(resolve), 120); }); trackPromise(delayed); } });
    app.addEventListener("change", (event) => { if (event.target.matches('[data-all-action="source"]')) { allState.source = event.target.value; rerender(); } });
    win.addEventListener("popstate", () => rerender());
    installPersonalActions(app, { storage, api, resolveItem, rerender, trackPromise, toast, onFavoriteChange: ({ removed, button }) => { if (removed && currentRoute?.view === "favs") button.closest("article")?.remove(); } });
    installTopicInteractions(app, { onTrack: (eventId, next, date) => { const tracked = storage.get(STORAGE_KEYS.tracked); const hadOverride = Object.hasOwn(tracked, eventId); const previous = tracked[eventId]; tracked[eventId] = next; storage.set(STORAGE_KEYS.tracked, tracked); trackPromise(api.postFeedback({ date, item_id: eventId, title: "", category: "", action: next ? "track" : "untrack", event_id: eventId }).then(() => rerender()).catch((error) => { const current = storage.get(STORAGE_KEYS.tracked); if (hadOverride) current[eventId] = previous; else delete current[eventId]; storage.set(STORAGE_KEYS.tracked, current); toast(error.message, true); return rerender(); })); } });
    installSearch({ input: doc.getElementById("searchInput"), results: doc.getElementById("searchRes"), dataApi, trackPromise });
    if (personal) { doc.querySelectorAll("[data-personal-nav]").forEach((fav) => { fav.hidden = false; }); const read = doc.getElementById("readLaterBtn"); if (read) read.hidden = false; installReadLater({ button: read, drawer: doc.getElementById("rlDrawer"), api, storage, trackPromise }); }
  }

  async function start() { install(); const parsed = parseRoute(win.location.search); const canonical = routeUrl(parsed); if (win.location.search !== canonical && !["reports", "detail"].includes(parsed.view)) win.history.replaceState({}, "", canonical); await rerender(); }
  return { start, go, idle, render: rerender };
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  try { window.localStorage.removeItem("aoiblog_admin_token"); } catch (_) {}
  resolvePersonalSession(window.fetch.bind(window), window.setTimeout.bind(window), window.clearTimeout.bind(window))
    .then((personal) => createNewsApp({ window, document, personal }).start());
}
