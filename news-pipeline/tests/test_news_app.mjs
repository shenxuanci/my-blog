import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import { createRequire } from "node:module";

import { createNewsApp } from "../../source/news/js/app.js";
import { renderDailyReport, renderWeeklyReport } from "../../source/news/js/reports.js";
import { createStorage, STORAGE_KEYS } from "../../source/news/js/storage.js";
const TimelineCore = createRequire(import.meta.url)("../../source/news/news-timeline.js");
const NewsState = createRequire(import.meta.url)("../../api/newsState.js");

const day = {
  date: "2026-07-15", lead: "导语", themes: [], tracking: [{ event_id: "evt-1", title: "追踪事件", history: [] }],
  items: [
    { id: "pick-1", event_id: "evt-1", tier: "pick", category: "ai", title: "隐藏候选", summary: "摘要", why: "意义", sources: [{ name: "官方", url: "https://example.com/a" }] },
    { id: "pick-2", tier: "pick", category: "tech", title: "保留新闻", summary: "摘要二", why: "意义二", sources: [] },
    { id: "more-1", tier: "more", category: "world", title: "更多新闻", summary: "更多摘要", sources: [{ name: "原文", url: "https://example.com/m" }] },
  ],
  deep: [{ id: "deep-1", title: "Deep", title_zh: "深读", takeaway: "要点", key_points: ["关键点"], audience: "读者", url: "https://example.com/deep" }],
  papers: [{ id: "paper-1", title: "Paper", title_zh: "论文", takeaway: "结论", contribution: "贡献", evidence: "证据", limitations: "局限", url: "https://example.com/paper" }],
  opinion: [{ id: "op-1", title: "舆论", summary: "舆论说明", source: "X" }],
};

function shell(url = "https://example.test/news/?view=day&date=2026-07-15") {
  return new JSDOM(`<!doctype html><body><a data-view="timeline"></a><a data-view="all"></a><a data-view="reports"></a><a data-view="topics"></a><a id="favoritesNav" data-view="favs" hidden></a><div id="reportControls"><a data-period="day"></a><a data-period="week"></a><div id="dayArchive"><select id="dateSel"></select></div><div id="weekArchive"><select id="weekSel"></select></div></div><span id="dayCtrls"><button id="prevBtn"></button><button id="nextBtn"></button></span><input id="searchInput"><div id="searchRes"></div><main id="app"></main><div id="liveStatus"></div></body>`, { url, pretendToBeVisual: true });
}

test("mobile search toggle opens, focuses and closes its overlay", async () => {
  const dom = new JSDOM(`<!doctype html><body><button id="mobileSearchToggle" aria-controls="mobileSearchPanel" aria-expanded="false"></button><div id="mobileSearchPanel" hidden><input id="searchInput"><button id="mobileSearchClose"></button></div><main id="app"></main></body>`, { pretendToBeVisual: true });
  const { installMobileSearch } = await import("../../source/news/js/accessibility.js");
  installMobileSearch(dom.window.document);
  const toggle = dom.window.document.querySelector("#mobileSearchToggle");
  toggle.click();
  assert.equal(toggle.getAttribute("aria-expanded"), "true");
  assert.equal(dom.window.document.querySelector("#mobileSearchPanel").hidden, false);
  assert.equal(dom.window.document.activeElement.id, "searchInput");
  dom.window.document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.equal(toggle.getAttribute("aria-expanded"), "false");
  assert.equal(dom.window.document.querySelector("#mobileSearchPanel").hidden, true);
  assert.equal(dom.window.document.activeElement, toggle);
});

test("desktop search ignores Escape and remains available", async () => {
  const dom = new JSDOM(`<!doctype html><body><button id="mobileSearchToggle" aria-controls="mobileSearchPanel" aria-expanded="false"></button><div id="mobileSearchPanel" role="dialog" aria-modal="true" hidden><input id="searchInput"><button id="mobileSearchClose"></button></div></body>`, { pretendToBeVisual: true });
  dom.window.matchMedia = () => ({ matches: true, addEventListener() {} });
  const { installMobileSearch } = await import("../../source/news/js/accessibility.js");
  installMobileSearch(dom.window.document);
  const panel = dom.window.document.querySelector("#mobileSearchPanel");
  const input = dom.window.document.querySelector("#searchInput");
  input.focus();
  dom.window.document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.equal(panel.hidden, false);
  assert.equal(dom.window.document.activeElement, input);
  assert.equal(panel.getAttribute("role"), null);
  assert.equal(panel.getAttribute("aria-modal"), null);
});

test("daily report separates visible core, supplemental digest and deep reading time", () => {
  const html = renderDailyReport({
    date: "2026-07-15",
    lead: "导语",
    read_minutes: 12,
    items: [],
    deep: [
      { id: "deep-valid", title: "A", read_minutes: 20, content_type: "analysis", url: "https://example.com/a" },
      { id: "deep-invalid", title: "B", read_minutes: 7, content_type: "invalid", url: "https://example.com/b" },
      { id: "deep-legacy", title: "C", read_minutes: 3, url: "https://example.com/c" },
    ],
  });
  const dom = new JSDOM(`<main>${html}</main>`);
  const text = dom.window.document.querySelector("main").textContent;
  assert.match(text, /核心日报约 1 分钟/);
  assert.match(text, /附栏导读约 1 分钟/);
  assert.doesNotMatch(text, /日报约 12 分钟/);
  assert.match(text, /原文约 30 分钟/);
  assert.deepEqual(
    [...dom.window.document.querySelectorAll(".content-type")].map((node) => node.textContent.trim()),
    ["分析"],
  );
});

test("mobile search is a labelled modal dialog and traps Tab in its controls", async () => {
  const dom = new JSDOM(`<!doctype html><body><button id="mobileSearchToggle" aria-controls="mobileSearchPanel" aria-expanded="false"></button><div id="mobileSearchPanel" aria-label="搜索历史条目" hidden><input id="searchInput"><button id="mobileSearchClose"></button><div id="searchRes"><a id="resultOne" href="#one">一</a><a id="resultTwo" href="#two">二</a></div><button id="hiddenTheme" style="display:none">主题</button></div><a id="outside" href="#">外部</a></body>`, { pretendToBeVisual: true });
  const { installMobileSearch } = await import("../../source/news/js/accessibility.js"); installMobileSearch(dom.window.document);
  const toggle = dom.window.document.querySelector("#mobileSearchToggle"); const input = dom.window.document.querySelector("#searchInput"); const close = dom.window.document.querySelector("#mobileSearchClose");
  toggle.click();
  assert.equal(dom.window.document.querySelector("#mobileSearchPanel").getAttribute("role"), "dialog");
  assert.equal(dom.window.document.querySelector("#mobileSearchPanel").getAttribute("aria-modal"), "true");
  const lastResult = dom.window.document.querySelector("#resultTwo");
  close.focus(); const middleTab = new dom.window.KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }); close.dispatchEvent(middleTab); assert.equal(middleTab.defaultPrevented, false); assert.notEqual(dom.window.document.activeElement, input);
  lastResult.focus(); lastResult.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true })); assert.equal(dom.window.document.activeElement, input); assert.notEqual(dom.window.document.activeElement?.id, "hiddenTheme");
  input.focus(); input.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true, cancelable: true })); assert.equal(dom.window.document.activeElement, lastResult);
  close.click(); assert.equal(dom.window.document.activeElement, toggle); assert.equal(dom.window.document.querySelector("#mobileSearchPanel").getAttribute("role"), null); assert.equal(dom.window.document.querySelector("#mobileSearchPanel").getAttribute("aria-modal"), null);
});

function dataApi() {
  return {
    daily: async (date) => date === day.date ? structuredClone(day) : null,
    weeklyManifest: async () => ["2026-W28", "2026-W27"],
    weekly: async (week) => ({ week, coverage: { daily_count: 6, expected_days: 7, missing_dates: [] }, lead: { title: `周报 ${week}` }, threads: [] }),
    allManifest: async () => [day.date],
    allDay: async () => ({ date: day.date, min_score: 40, items: [{ id: "all-1", c: "ai", title: "全部动态一", score: 60, url: "https://example.com/all" }] }),
    index: async () => [[day.date, "pick-2", "pick", "tech", "保留新闻", "标签"]],
    events: async () => ({ events: [{ event_id: "evt-1", title: "主题事件", status: "active", pinned: false, history: [{ date: day.date, summary: "进展" }] }] }),
  };
}

test("local personal-state maps recover from valid but incompatible JSON", () => {
  const values = new Map([
    [STORAGE_KEYS.hidden, "null"],
    [STORAGE_KEYS.liked, "[]"],
    [STORAGE_KEYS.tracked, '"text"'],
    [STORAGE_KEYS.seenDays, "1"],
  ]);
  const localStorage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
  const storage = createStorage(localStorage);

  for (const key of values.keys()) assert.deepEqual(storage.get(key), {});
  assert.equal(storage.toggle(STORAGE_KEYS.liked, "2026-07-15:pick-1"), true);
  assert.doesNotThrow(() => storage.markSeen("2026-07-15"));
});

test("app rewrites old route, marks seen and respects hidden state", async () => {
  const dom = shell();
  dom.window.localStorage.setItem("news_hidden", JSON.stringify({ "2026-07-15:pick-1": true }));
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi() });
  await app.start();
  assert.equal(dom.window.location.search, "?view=reports&period=day&date=2026-07-15");
  assert.equal(JSON.parse(dom.window.localStorage.getItem("news_seen_days"))[day.date], 1);
  assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /隐藏候选/);
  assert.match(dom.window.document.querySelector("main").textContent, /深度阅读|今日论文|追踪中|舆论观察|更多资讯/);
  assert.ok(dom.window.document.querySelector("main h1"));
  assert.equal(dom.window.document.querySelector("#weekArchive").hidden, true);
  assert.equal(dom.window.document.querySelectorAll('div[role="button"],span[onclick],div[onclick]').length, 0);
});

test("bare and unknown routes open the latest daily report", async () => {
  for (const url of ["https://example.test/news/", "https://example.test/news/?view=unknown"]) {
    const dom = shell(url);
    const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), manifests: { daily: [day.date] } });
    await app.start();
    assert.equal(dom.window.location.search, "?view=reports&period=day&date=2026-07-15");
    assert.match(dom.window.document.querySelector("main").textContent, /导语/);
  }
});

test("report route exposes a stable shell state and removes it after navigation", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi() });
  await app.start();
  assert.equal(dom.window.document.body.classList.contains("reports-view"), true);
  await app.go({ view: "timeline" });
  assert.equal(dom.window.document.body.classList.contains("reports-view"), false);
});

test("weekly archive, browser Back and old week route are integrated", async () => {
  const dom = shell("https://example.test/news/?view=week&week=2026-W27");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi() });
  await app.start();
  assert.equal(dom.window.location.search, "?view=reports&period=week&week=2026-W27");
  assert.match(dom.window.document.querySelector("main").textContent, /周报 2026-W27/);
  assert.equal(dom.window.document.querySelector("#dayArchive").hidden, true);
  dom.window.document.querySelector("#weekSel").value = "2026-W28";
  dom.window.document.querySelector("#weekSel").dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  await app.idle();
  assert.equal(dom.window.location.search, "?view=reports&period=week&week=2026-W28");
  dom.window.history.back();
  await new Promise((resolve) => dom.window.setTimeout(resolve, 10));
  await app.idle();
  assert.match(dom.window.document.querySelector("main").textContent, /周报 2026-W27/);
});

test("personal weekly report shows the selected seven-day misses and reason summary", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=week&week=2026-W28");
  const misses = [
    { id: "m1", ts: "2026-07-06T01:00:00.000Z", date: "2026-07-06", title: "周内事件", reason: "important_event" },
    { id: "m2", ts: "2026-07-10T01:00:00.000Z", date: "2026-07-10", url: "https://example.com/deep", reason: "deep_read" },
    { id: "m3", ts: "2026-07-12T01:00:00.000Z", date: "2026-07-12", title: "另一事件", reason: "important_event" },
    { id: "outside", ts: "2026-07-13T01:00:00.000Z", date: "2026-07-13", title: "周外事件", reason: "missing_perspective" },
  ];
  const fetchStub = async (url) => {
    assert.match(String(url), /type=misses/);
    return { ok: true, json: async () => ({ success: true, data: { version: 1, entries: misses } }) };
  };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), personal: true, fetch: fetchStub });
  await app.start();
  const panel = dom.window.document.querySelector(".weekly-misses");
  assert.ok(panel);
  assert.match(panel.textContent, /近 7 天遗漏|重要事件 2|值得深读 1|周内事件|另一事件/);
  assert.doesNotMatch(panel.textContent, /周外事件/);
  assert.equal(panel.querySelectorAll('[data-action="remove-miss"]').length, 3);

  const publicHtml = renderWeeklyReport(
    { week: "2026-W28", lead: { title: "公开周报" }, threads: [] },
    { personal: false, misses },
  );
  assert.doesNotMatch(publicHtml, /weekly-misses|周内事件/);
});

test("personal not-interested stays in module layout and deep/paper details retain type fields", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), personal: true, fetch: async () => ({ ok: true, json: async () => ({ success: true, data: {} }) }) });
  await app.start();
  const hide = dom.window.document.querySelector('[data-action="not-interested"][data-ref="pick-1"]');
  hide.click();
  const submit = dom.window.document.querySelector('[data-action="submit-not-interested"]');
  submit.click();
  await app.idle();
  assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /隐藏候选/);
  assert.match(dom.window.document.querySelector("main").textContent, /保留新闻/);
  await app.go({ view: "detail", date: day.date, type: "deep", item: "deep-1" });
  assert.match(dom.window.document.querySelector("main").textContent, /关键点|读者/);
  await app.go({ view: "detail", date: day.date, type: "paper", item: "paper-1" });
  assert.match(dom.window.document.querySelector("main").textContent, /贡献|证据|局限/);
});

test("empty manifest degrades and rendered interactions use native controls", async () => {
  const dom = shell("https://example.test/news/?view=timeline");
  const emptyApi = { ...dataApi(), daily: async () => null };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: emptyApi, manifests: { daily: [] } });
  await app.start();
  assert.match(dom.window.document.querySelector("main").textContent, /还没有任何日报数据|暂无/);
  assert.equal(dom.window.document.querySelectorAll('div[role="button"],span[onclick],div[onclick]').length, 0);
});

test("personal actions preserve newsState storage and API contracts", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  const requests = [];
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), personal: true, fetch: async (_url, init) => { requests.push(JSON.parse(init.body)); return { ok: true, json: async () => ({ success: true, data: {} }) }; } });
  await app.start();
  const like = dom.window.document.querySelector('[data-action="like"][data-ref="pick-1"]');
  const menu = like.closest("details");
  menu.open = true;
  like.click();
  assert.equal(menu.open, false);
  dom.window.document.querySelector('[data-action="favorite"][data-ref="pick-1"]').click();
  dom.window.document.querySelector('[data-action="read-later"][data-ref="pick-1"]').click();
  const source = dom.window.document.querySelector('[data-action="source"][data-ref="pick-1"]');
  source.closest("details").open = true;
  source.click();
  assert.equal(source.closest("details").open, false);
  assert.ok(dom.window.document.querySelector('[data-action="down-source"]'));
  dom.window.document.querySelector('[data-action="down-source"]').click();
  await app.idle();
  assert.ok(requests.some((request) => request.type === "feedback" && request.payload.action === "more_like_this"));
  assert.ok(requests.some((request) => request.type === "feedback" && request.payload.action === "low_quality_source"));
  assert.ok(requests.some((request) => request.type === "favorites"));
  assert.ok(requests.some((request) => request.type === "read_later"));
  assert.equal(JSON.parse(dom.window.localStorage.getItem("news_like"))["2026-07-15:pick-1"], true);
});

test("daily tracking cancellation keeps a false override and hides the tracking card", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  const requests = [];
  const app = createNewsApp({
    window: dom.window,
    document: dom.window.document,
    dataApi: dataApi(),
    personal: true,
    fetch: async (_url, init) => {
      requests.push(JSON.parse(init.body));
      return { ok: true, json: async () => ({ success: true, data: {} }) };
    },
  });
  await app.start();

  dom.window.document.querySelector('[data-action="untrack"][data-event="evt-1"]').click();
  await app.idle();

  assert.equal(
    JSON.parse(dom.window.localStorage.getItem(STORAGE_KEYS.tracked) || "{}")["evt-1"],
    false,
  );
  assert.equal(dom.window.document.querySelector('[data-action="untrack"][data-event="evt-1"]'), null);
  assert.ok(requests.some((request) => request.payload.action === "untrack"));
});

test("failed personal-state writes roll back optimistic card actions", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  const fetchStub = async (_url, init = {}) => {
    if (!init.method) {
      return { ok: true, json: async () => ({ success: true, data: { version: 1, entries: [] } }) };
    }
    return {
      ok: false,
      status: 503,
      json: async () => ({ success: false, error: "repository unavailable" }),
    };
  };
  const app = createNewsApp({
    window: dom.window,
    document: dom.window.document,
    dataApi: dataApi(),
    personal: true,
    fetch: fetchStub,
  });
  await app.start();
  const key = `${day.date}:pick-1`;

  dom.window.document.querySelector('[data-action="like"][data-ref="pick-1"]').click();
  await app.idle();
  assert.equal(JSON.parse(dom.window.localStorage.getItem(STORAGE_KEYS.liked) || "{}")[key], undefined);
  assert.equal(dom.window.document.querySelector('[data-action="like"][data-ref="pick-1"]').classList.contains("done"), false);

  dom.window.document.querySelector('[data-action="favorite"][data-ref="pick-1"]').click();
  await app.idle();
  assert.equal(JSON.parse(dom.window.localStorage.getItem(STORAGE_KEYS.favorites) || "{}")[key], undefined);
  assert.equal(dom.window.document.querySelector('[data-action="favorite"][data-ref="pick-1"]').classList.contains("done"), false);

  dom.window.document.querySelector('[data-action="read-later"][data-ref="pick-1"]').click();
  await app.idle();
  assert.equal(JSON.parse(dom.window.localStorage.getItem(STORAGE_KEYS.readLater) || "{}")[key], undefined);
  assert.equal(dom.window.document.querySelector('[data-action="read-later"][data-ref="pick-1"]').classList.contains("done"), false);

  dom.window.document.querySelector('[data-action="untrack"][data-event="evt-1"]').click();
  await app.idle();
  assert.equal(
    Object.hasOwn(JSON.parse(dom.window.localStorage.getItem(STORAGE_KEYS.tracked) || "{}"), "evt-1"),
    false,
  );
  assert.ok(dom.window.document.querySelector('[data-action="untrack"][data-event="evt-1"]'));

  dom.window.document.querySelector('[data-action="not-interested"][data-ref="pick-1"]').click();
  dom.window.document.querySelector('[data-action="submit-not-interested"]').click();
  await app.idle();
  assert.equal(JSON.parse(dom.window.localStorage.getItem(STORAGE_KEYS.hidden) || "{}")[key], undefined);
  assert.match(dom.window.document.querySelector("main").textContent, /隐藏候选/);
});

test("failed topic tracking restores the prior local override", async () => {
  const dom = shell("https://example.test/news/?view=topics");
  const api = dataApi();
  api.events = async () => ({
    events: [{
      event_id: "evt-1",
      title: "主题事件",
      status: "active",
      pinned: false,
      history: [
        { date: "2026-07-14", summary: "前序进展" },
        { date: day.date, summary: "最新进展" },
      ],
    }],
  });
  const app = createNewsApp({
    window: dom.window,
    document: dom.window.document,
    dataApi: api,
    manifests: { daily: [day.date] },
    personal: true,
    fetch: async () => ({
      ok: false,
      status: 503,
      json: async () => ({ success: false, error: "repository unavailable" }),
    }),
  });
  await app.start();

  dom.window.document.querySelector('[data-action="track-topic"]').click();
  await app.idle();
  assert.equal(
    Object.hasOwn(JSON.parse(dom.window.localStorage.getItem(STORAGE_KEYS.tracked) || "{}"), "evt-1"),
    false,
  );
  assert.match(dom.window.document.querySelector('[data-action="track-topic"]').textContent, /追踪/);
  assert.doesNotMatch(dom.window.document.querySelector('[data-action="track-topic"]').textContent, /取消/);
});

test("misses state is independent, constrained, removable, and capped", () => {
  const { STATE_FILES, validateEntry, appendEntry, emptyState } = NewsState._test;
  assert.equal(STATE_FILES.misses, "source/news/data/misses.json");
  const titleOnly = validateEntry("misses", {
    date: day.date,
    title: "漏掉的重要事件",
    reason: "important_event",
    note: "must not persist",
    category: "ai",
  });
  assert.deepEqual(titleOnly, {
    op: "add",
    date: day.date,
    title: "漏掉的重要事件",
    reason: "important_event",
  });
  const urlOnly = validateEntry("misses", {
    date: day.date,
    url: "https://example.com/missed",
    reason: "deep_read",
  });
  assert.equal(urlOnly.url, "https://example.com/missed");
  assert.throws(
    () => validateEntry("misses", { date: day.date, reason: "important_event" }),
    /title or payload\.url/i,
  );
  assert.throws(
    () => validateEntry("misses", { date: day.date, url: "javascript:alert(1)", reason: "deep_read" }),
    /http\(s\)/i,
  );
  assert.throws(
    () => validateEntry("misses", { date: day.date, title: "x", reason: "other" }),
    /reason/i,
  );
  const added = appendEntry(emptyState("misses"), "misses", { id: "miss-1", ...titleOnly }, "2026-07-15T00:00:00.000Z");
  assert.deepEqual(added.state.entries[0], {
    id: "miss-1",
    ts: "2026-07-15T00:00:00.000Z",
    date: day.date,
    title: "漏掉的重要事件",
    reason: "important_event",
  });
  const removed = appendEntry(
    added.state,
    "misses",
    validateEntry("misses", { op: "remove", id: "miss-1" }),
    "2026-07-15T01:00:00.000Z",
  );
  assert.equal(removed.state.entries.length, 0);
  const full = { version: 1, entries: Array.from({ length: 1000 }, (_, index) => ({ id: `old-${index}` })) };
  const capped = appendEntry(full, "misses", { id: "miss-new", ...titleOnly }, "2026-07-15T00:00:00.000Z");
  assert.equal(capped.state.entries.length, 1000);
  assert.equal(capped.state.entries.at(-1).id, "miss-new");
  assert.equal(capped.state.entries.some((entry) => entry.id === "old-0"), false);
});

test("personal daily report records and removes public misses from the top tool", async () => {
  const requests = [];
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  const fetchStub = async (url, init = {}) => {
    if (!init.method && String(url).includes("type=misses")) {
      return {
        ok: true,
        json: async () => ({
          success: true,
          data: {
            version: 1,
            entries: [{ id: "miss-existing", ts: "2026-07-15T00:00:00.000Z", date: day.date, title: "已有遗漏", reason: "missing_perspective" }],
          },
        }),
      };
    }
    requests.push(JSON.parse(init.body));
    return { ok: true, json: async () => ({ success: true, data: {} }) };
  };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), personal: true, fetch: fetchStub });
  await app.start();
  const tool = dom.window.document.querySelector(".misses-tool");
  assert.ok(tool);
  assert.equal(tool.previousElementSibling.classList.contains("masthead"), true);
  assert.match(tool.textContent, /补记遗漏|公开仓库/);
  tool.querySelector('[data-miss-field="title"]').value = "新遗漏";
  tool.querySelector('[data-miss-field="url"]').value = "https://example.com/new";
  tool.querySelector('[data-miss-field="reason"]').value = "deep_read";
  tool.querySelector('[data-action="submit-miss"]').click();
  await app.idle();
  assert.ok(requests.some((request) => request.type === "misses"
    && request.payload.title === "新遗漏"
    && request.payload.reason === "deep_read"));
  dom.window.document.querySelector('[data-action="remove-miss"][data-id="miss-existing"]').click();
  await app.idle();
  assert.ok(requests.some((request) => request.type === "misses"
    && request.payload.op === "remove"
    && request.payload.id === "miss-existing"));

  const publicHtml = renderDailyReport(day, { personal: false, misses: [{ id: "hidden", date: day.date, title: "不公开展示" }] });
  assert.doesNotMatch(publicHtml, /misses-tool|不公开展示/);
});

test("timeline renders a continuous Beijing-time stream with a light mainline and filters", async () => {
  const dates = Array.from({ length: 7 }, (_, index) => `2026-07-${String(15 - index).padStart(2, "0")}`);
  const api = dataApi(); api.daily = async (date) => ({ ...structuredClone(day), date, items: day.items.map((item) => ({ ...item, score: 82, time: `${date}T01:00:00Z`, tags: item.id === "pick-2" ? ["Agent"] : ["模型"] })) });
  const dom = shell("https://example.test/news/?view=timeline");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: dates } });
  await app.start();
  assert.ok(dom.window.document.querySelector(".timeline-mainline"));
  assert.equal(dom.window.document.querySelector(".hotbox"), null);
  assert.equal(dom.window.document.querySelector('[data-timeline-action="toggle-day"]'), null);
  assert.equal(dom.window.document.querySelector(".timeline-day .grid"), null);
  assert.ok(dom.window.document.querySelector(".timeline-stream"));
  assert.ok(dom.window.document.querySelector('[data-timeline-action="set-cat"]'));
  assert.ok(dom.window.document.querySelector('[data-timeline-action="set-tag"]'));
  const older = dom.window.document.querySelector('[data-timeline-action="more"]'); older.click(); await app.idle();
  const olderDate = dom.window.document.querySelector('time[datetime="2026-07-09"]');
  assert.equal(olderDate?.textContent, "7月9日 周四");
  const search = dom.window.document.querySelector("#timelineSearch"); search.value = "保留"; search.dispatchEvent(new dom.window.Event("input", { bubbles: true })); await app.idle();
  assert.match(dom.window.document.querySelector("main").textContent, /保留新闻/);
});

test("timeline uses production timeline helpers for publish-day grouping, continuation collapse and decayed event hotness", async () => {
  const dates = ["2026-07-15", "2026-07-14"];
  const api = dataApi(); api.daily = async (date) => ({ date, items: [{ id: `pick-${date}`, tier: "pick", category: "ai", event_id: "evt-same", title: "同一事件", summary: "相同进展", score: 82, time: date === dates[0] ? "2026-07-14T16:30:00Z" : "2026-07-14T10:00:00Z", sources: [{ name: date, url: `https://${date}.example.com/story` }] }] });
  const dom = shell("https://example.test/news/?view=timeline"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: dates }, timelineApi: TimelineCore, now: new Date("2026-07-15T02:00:00Z").getTime() }); await app.start();
  assert.equal(dom.window.document.querySelectorAll(".timeline-day .report-card").length, 1);
  assert.match(dom.window.document.querySelector(".timeline-day").textContent, /2026-07-15/);
  assert.equal(dom.window.document.querySelectorAll(".timeline-mainline a").length, 1);
  assert.match(dom.window.document.querySelector(".timeline-mainline").textContent, /2 个独立信源/);
});

test("timeline mainline only uses events from the newest report day", async () => {
  const dates = ["2026-07-15", "2026-07-14", "2026-07-13"];
  const api = dataApi(); api.daily = async (date) => ({ date, items: date === dates[0]
    ? [{ id: "today", tier: "pick", category: "ai", title: "今日普通进展", score: 50, time: "2026-07-15T01:00:00Z", sources: [] }]
    : [{ id: `old-${date}`, tier: "pick", category: "ai", title: `旧日高分 ${date}`, score: 99, time: `${date}T01:00:00Z`, sources: [{ name: "A", url: "https://a.example.com/x" }, { name: "B", url: "https://b.example.com/x" }] }] });
  const dom = shell("https://example.test/news/?view=timeline"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: dates }, timelineApi: TimelineCore, now: new Date("2026-07-15T02:00:00Z").getTime() }); await app.start();
  assert.doesNotMatch(dom.window.document.querySelector(".timeline-mainline")?.textContent || "", /旧日高分/);
});

test("timeline mainline encodes item ids instead of creating injected attributes", async () => {
  const maliciousId = 'pick" onmouseover="alert(1)';
  const api = dataApi(); api.daily = async (date) => ({ date, items: [{
    id: maliciousId, tier: "pick", category: "ai", title: "编码测试", score: 99,
    time: `${date}T01:00:00Z`, sources: [
      { name: "A", url: "https://a.example.com/x" },
      { name: "B", url: "https://b.example.com/x" },
    ],
  }] });
  const dom = shell("https://example.test/news/?view=timeline");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] } });
  await app.start();
  const link = dom.window.document.querySelector(".timeline-mainline a");
  assert.ok(link);
  assert.equal(link.hasAttribute("onmouseover"), false);
  assert.equal(new URL(link.href).searchParams.get("item"), maliciousId);
});

test("timeline labels missing and invalid publication times as uncertain", async () => {
  const api = dataApi(); api.daily = async (date) => ({ date, items: [
    { id: "missing-time", tier: "pick", category: "ai", title: "缺失时间", summary: "A" },
    { id: "invalid-time", tier: "pick", category: "ai", title: "非法时间", summary: "B", time: "not-a-time" },
  ] });
  const dom = shell("https://example.test/news/?view=timeline"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] } }); await app.start();
  const times = [...dom.window.document.querySelectorAll(".timeline-time")].map((node) => node.textContent);
  assert.deepEqual(times, ["时间待确认", "时间待确认"]);
  assert.doesNotMatch(times.join(" "), /08:00/);
});

test("timeline marks continuations and keeps card links separate from external and personal actions", async () => {
  const dates = ["2026-07-15", "2026-07-14"];
  const api = dataApi(); api.daily = async (date) => ({ date, items: [{ id: `pick-${date}`, tier: "pick", category: "ai", event_id: "evt", title: date === dates[0] ? "事件新进展" : "事件起点", summary: date, why: "重要", time: `${date}T01:00:00Z`, sources: [{ name: "来源", url: "https://example.com/story" }] }] });
  const dom = shell("https://example.test/news/?view=timeline");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: dates }, timelineApi: TimelineCore, personal: true, fetch: async () => ({ ok: true, json: async () => ({ success: true, data: {} }) }) }); await app.start();
  const continuation = dom.window.document.querySelector(".timeline-entry.is-continuation");
  assert.ok(continuation?.querySelector(".continuation-mark"));
  assert.ok(continuation.querySelector('h3 a[data-route]'));
  assert.ok(continuation.querySelector('.srcs a[target="_blank"]'));
  assert.ok(continuation.querySelector('button[data-action="favorite"]'));
});

test("timeline renders actual published-date groups even when they differ from selected report dates", async () => {
  const api = dataApi(); api.daily = async () => ({ date: day.date, items: [{ id: "pick-old", tier: "pick", category: "ai", title: "前日发布", summary: "摘要", score: 80, time: "2026-07-13T16:30:00Z", sources: [] }] }); api.index = async () => [[day.date, "pick-old", "pick", "ai", "前日发布", "模型"]];
  const make = async (url) => { const dom = shell(url); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] }, timelineApi: TimelineCore }); await app.start(); return { dom, app }; };
  const ordinary = await make("https://example.test/news/?view=timeline"); assert.equal(ordinary.dom.window.document.querySelector('.timeline-day time[datetime="2026-07-14"]')?.textContent, "7月14日 周二"); assert.match(ordinary.dom.window.document.querySelector(".timeline-day").textContent, /前日发布/);
  const searched = await make("https://example.test/news/?view=timeline"); const input = searched.dom.window.document.querySelector("#timelineSearch"); input.value = "前日"; input.dispatchEvent(new searched.dom.window.Event("input", { bubbles: true })); await new Promise((resolve) => setTimeout(resolve, 160)); await searched.app.idle(); assert.equal(searched.dom.window.document.querySelector('.timeline-day time[datetime="2026-07-14"]')?.textContent, "7月14日 周二"); assert.match(searched.dom.window.document.querySelector(".timeline-day").textContent, /前日发布/);
});

test("timeline search debounces typing, restores focus/caret and rejects stale async results", async () => {
  let calls = 0; const api = dataApi(); api.index = async () => { calls++; await new Promise((resolve) => setTimeout(resolve, calls === 1 ? 80 : 5)); return [[day.date, "pick-a", "pick", "tech", "保X", "Agent"], [day.date, "pick-2", "pick", "tech", "保留新闻", "Agent"]]; }; api.daily = async () => ({ ...structuredClone(day), items: [...day.items, { id: "pick-a", tier: "pick", category: "tech", title: "保X", summary: "A", tags: ["Agent"] }].map((item) => ({ ...item, tags: item.tags || ["Agent"] })) });
  const dom = shell("https://example.test/news/?view=timeline"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] } }); await app.start();
  let input = dom.window.document.querySelector("#timelineSearch"); input.focus(); input.value = "保"; input.setSelectionRange(1, 1); input.dispatchEvent(new dom.window.Event("input", { bubbles: true })); await new Promise((resolve) => setTimeout(resolve, 140));
  input = dom.window.document.querySelector("#timelineSearch"); input.value = "保留"; input.setSelectionRange(2, 2); input.dispatchEvent(new dom.window.Event("input", { bubbles: true })); await new Promise((resolve) => setTimeout(resolve, 220)); await app.idle();
  const cardText = [...dom.window.document.querySelectorAll(".timeline-day .report-card")].map((node) => node.textContent).join(" "); assert.match(cardText, /保留新闻/); assert.doesNotMatch(cardText, /保X/); assert.equal(dom.window.document.activeElement.id, "timelineSearch"); assert.equal(dom.window.document.activeElement.selectionStart, 2);
});

test("all dynamics restores score threshold, category, show-all and older loading", async () => {
  const api = dataApi(); api.allManifest = async () => Array.from({ length: 8 }, (_, index) => `2026-07-${String(15 - index).padStart(2, "0")}`); api.allDay = async (date) => ({ date, min_score: 40, items: [{ id: "high", c: "ai", t: "高分", sn: "模型发布", source: "官方", score: 60 }, { id: "low", c: "world", t: "低分", source: "媒体", score: 20 }] });
  const dom = shell("https://example.test/news/?view=all"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api }); await app.start();
  assert.match(dom.window.document.querySelector("main").textContent, /高分/); assert.doesNotMatch([...dom.window.document.querySelectorAll("main article strong")].map((node) => node.textContent).join(" "), /低分/);
  dom.window.document.querySelector('[data-all-action="show-all"]').click(); await app.idle(); assert.match([...dom.window.document.querySelectorAll("main article strong")].map((node) => node.textContent).join(" "), /低分/);
  assert.ok(dom.window.document.querySelector('[data-all-action="set-cat"]')); dom.window.document.querySelector('[data-all-action="more"]').click(); await app.idle(); assert.match(dom.window.document.querySelector("main").textContent, /2026-07-08/);
  assert.ok(dom.window.document.querySelector(".all-timeline"));
  assert.equal(dom.window.document.querySelector(".all-timeline .more-list"), null);
  let search = dom.window.document.querySelector('[data-all-action="search"]'); search.value = "不存在"; search.dispatchEvent(new dom.window.Event("input", { bubbles: true })); await app.idle(); assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /高分/);
  search = dom.window.document.querySelector('[data-all-action="search"]'); search.value = ""; search.dispatchEvent(new dom.window.Event("input", { bubbles: true })); await app.idle();
  const source = dom.window.document.querySelector('[data-all-action="source"]'); source.value = "官方"; source.dispatchEvent(new dom.window.Event("change", { bubbles: true })); await app.idle(); assert.doesNotMatch([...dom.window.document.querySelectorAll(".all-entry")].map((node) => node.textContent).join(" "), /低分/);
});

test("all dynamics search debounces typing and restores focus and caret", async () => {
  const api = dataApi(); api.allDay = async () => ({ date: day.date, min_score: 40, items: [{ id: "one", c: "ai", t: "模型发布", sn: "逐字检索", source: "官方", score: 60 }] });
  const dom = shell("https://example.test/news/?view=all"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api }); await app.start();
  let input = dom.window.document.querySelector('[data-all-action="search"]'); input.focus(); input.value = "模"; input.setSelectionRange(1, 1); input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  assert.equal(dom.window.document.activeElement, input);
  input.value = "模型"; input.setSelectionRange(2, 2); input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  await new Promise((resolve) => dom.window.setTimeout(resolve, 160)); await app.idle();
  input = dom.window.document.querySelector('[data-all-action="search"]');
  assert.equal(dom.window.document.activeElement, input); assert.equal(input.selectionStart, 2); assert.equal(input.value, "模型");
});

test("stale all search response cannot overwrite a newer route or restore stale focus", async () => {
  let releaseStale; let allDayCalls = 0;
  const stale = new Promise((resolve) => { releaseStale = resolve; });
  const api = dataApi(); api.allDay = async () => {
    allDayCalls++;
    if (allDayCalls === 1) return { date: day.date, min_score: 40, items: [{ id: "initial", c: "ai", t: "初始动态", score: 60 }] };
    return stale;
  };
  const dom = shell("https://example.test/news/?view=all"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] } }); await app.start();
  const input = dom.window.document.querySelector('[data-all-action="search"]'); input.focus(); input.value = "旧"; input.setSelectionRange(1, 1); input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  await new Promise((resolve) => dom.window.setTimeout(resolve, 140));
  await app.go({ view: "timeline" });
  assert.ok(dom.window.document.querySelector(".timeline-view"));
  releaseStale({ date: day.date, min_score: 40, items: [{ id: "stale", c: "ai", t: "旧请求结果", score: 60 }] });
  await new Promise((resolve) => dom.window.setTimeout(resolve, 0));
  assert.ok(dom.window.document.querySelector(".timeline-view"));
  assert.equal(dom.window.document.querySelector('[data-all-action="search"]'), null);
  assert.notEqual(dom.window.document.activeElement?.getAttribute("data-all-action"), "search");
});

test("stale all search rejection cannot replace a newer route with an error", async () => {
  let rejectStale; let allDayCalls = 0;
  const stale = new Promise((_resolve, reject) => { rejectStale = reject; });
  const api = dataApi(); api.allDay = async () => {
    allDayCalls++;
    if (allDayCalls === 1) return { date: day.date, min_score: 40, items: [{ id: "initial", c: "ai", t: "初始动态", score: 60 }] };
    return stale;
  };
  const dom = shell("https://example.test/news/?view=all"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] } }); await app.start();
  const input = dom.window.document.querySelector('[data-all-action="search"]'); input.value = "旧"; input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  await new Promise((resolve) => dom.window.setTimeout(resolve, 140));
  await app.go({ view: "timeline" });
  rejectStale(new Error("旧请求失败"));
  await new Promise((resolve) => dom.window.setTimeout(resolve, 0));
  assert.ok(dom.window.document.querySelector(".timeline-view"));
  assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /加载失败|旧请求失败/);
});

test("stale daily request cannot mark seen, mutate archive or overwrite a newer page", async () => {
  let releaseDaily; const slowDaily = new Promise((resolve) => { releaseDaily = resolve; });
  const api = dataApi(); api.daily = async () => slowDaily;
  const dom = shell("https://example.test/news/?view=all"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] } }); await app.start();
  const slowNavigation = app.go({ view: "reports", period: "day", date: day.date });
  await new Promise((resolve) => dom.window.setTimeout(resolve, 0));
  await app.go({ view: "all" });
  releaseDaily(structuredClone(day)); await slowNavigation;
  assert.equal(JSON.parse(dom.window.localStorage.getItem("news_seen_days") || "{}")[day.date], undefined);
  assert.doesNotMatch(dom.window.document.querySelector("#dateSel").textContent, /✓/);
  assert.match(dom.window.document.querySelector("main").textContent, /全部动态/);
});

test("stale topics request cannot overwrite a newer timeline", async () => {
  let releaseEvents; const events = new Promise((resolve) => { releaseEvents = resolve; });
  const api = dataApi(); api.events = async () => events;
  const dom = shell("https://example.test/news/?view=all"); const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] } }); await app.start();
  const slowNavigation = app.go({ view: "topics" }); await new Promise((resolve) => dom.window.setTimeout(resolve, 0));
  await app.go({ view: "timeline" }); releaseEvents({ events: [{ event_id: "late", title: "迟到主题", status: "active", history: [] }] }); await slowNavigation;
  assert.ok(dom.window.document.querySelector(".timeline-view")); assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /迟到主题/);
});

test("topics restores groups/map and local tracked override has stable direction", async () => {
  const api = dataApi(); api.events = async () => ({ events: [
    { event_id: "pin", title: "追踪主题", status: "active", pinned: true, history: [{ date: day.date, summary: "A" }, { date: "2026-07-14", summary: "B" }] },
    { event_id: "run", title: "进行主题", status: "active", pinned: false, history: [{ date: day.date, summary: "A" }, { date: "2026-07-14", summary: "B" }] },
    { event_id: "arc", title: "归档主题", status: "archived", history: [{ date: day.date, summary: "A" }, { date: "2026-07-14", summary: "B" }] },
  ] }); api.index = async () => [[day.date, "pick-1", "pick", "ai", "新闻", "Agent|模型"], [day.date, "deep-1", "deep", "ai", "深读", "不应统计"]]; api.daily = async () => ({ ...structuredClone(day), items: day.items.map((item) => ({ ...item, tags: ["Agent"] })) });
  const requests = []; const dom = shell("https://example.test/news/?view=topics");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api, manifests: { daily: [day.date] }, personal: true, fetch: async (_url, init) => { requests.push(JSON.parse(init.body)); return { ok: true, json: async () => ({ success: true, data: {} }) }; } }); await app.start();
  assert.match(dom.window.document.querySelector("main").textContent, /追踪中|进行中|已归档|题材地图/);
  const untrack = dom.window.document.querySelector('[data-event="pin"]'); assert.match(untrack.textContent, /取消追踪/); untrack.click(); await app.idle();
  assert.equal(JSON.parse(dom.window.localStorage.getItem("news_tracked")).pin, false);
  const untrackRequest = requests.find((request) => request.payload.action === "untrack");
  assert.equal(untrackRequest.payload.date, day.date);
  assert.doesNotThrow(() => NewsState._test.validateEntry("feedback", untrackRequest.payload));
  assert.match(dom.window.document.querySelector('[data-event="pin"]').textContent, /追踪/);
  assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /不应统计/); const agent = [...dom.window.document.querySelectorAll(".topic-card")].find((node) => node.textContent.includes("Agent")); agent.click(); await app.idle(); assert.match(dom.window.document.querySelector("main").textContent, /保留新闻/);
});

test("favorites uses server truth, backfills local/index, and read-later supports done/remove", async () => {
  const dom = shell("https://example.test/news/?view=favs"); dom.window.document.body.insertAdjacentHTML("beforeend", '<button id="readLaterBtn" hidden></button><aside id="rlDrawer" hidden inert></aside>');
  const requests = [];
  const fetchStub = async (url, init = {}) => {
    if (!init.method && String(url).includes("type=favorites")) return { ok: true, json: async () => ({ success: true, data: { items: [{ date: day.date, item_id: "pick-2", title: "保留新闻", category: "tech" }] } }) };
    if (!init.method && String(url).includes("type=read_later")) return { ok: true, json: async () => ({ success: true, data: { items: [{ date: day.date, item_id: "deep-1", title: "深读", url: "https://example.com/deep", done: false }] } }) };
    requests.push(JSON.parse(init.body)); return { ok: true, json: async () => ({ success: true, data: {} }) };
  };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), personal: true, fetch: fetchStub }); await app.start();
  assert.match(dom.window.document.querySelector("main").textContent, /保留新闻/); assert.equal(JSON.parse(dom.window.localStorage.getItem("news_fav"))[`${day.date}:pick-2`], 1);
  dom.window.document.querySelector('[data-action="favorite"][data-ref="pick-2"]').click(); await app.idle(); assert.ok(requests.some((request) => request.type === "favorites" && request.payload.item_id === "pick-2")); assert.doesNotMatch(dom.window.document.querySelector("main").textContent, /保留新闻/);
  dom.window.document.querySelector("#readLaterBtn").click(); await app.idle(); assert.equal(dom.window.document.querySelector("#rlDrawer").hidden, false); assert.ok(dom.window.document.querySelector('[data-read-later-op="done"]')); dom.window.document.querySelector('[data-read-later-op="done"]').click(); await app.idle(); assert.ok(requests.some((request) => request.type === "read_later" && request.payload.op === "done")); dom.window.document.querySelector('[data-read-later-op="remove"]').click(); await app.idle(); assert.ok(requests.some((request) => request.type === "read_later" && request.payload.op === "remove")); dom.window.document.querySelector("[data-close-drawer]").click(); assert.equal(dom.window.document.querySelector("#rlDrawer").hidden, true); assert.equal(dom.window.document.activeElement.id, "readLaterBtn");
});

test("logged-out favorites route keeps its URL and renders a clear fallback", async () => {
  const dom = shell("https://example.test/news/?view=favs");
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), manifests: { daily: [day.date] } });
  await app.start();
  assert.equal(dom.window.location.search, "?view=favs");
  assert.equal(dom.window.document.querySelector("main h1")?.textContent, "收藏");
  assert.match(dom.window.document.querySelector('main [role="status"]')?.textContent || "", /登录后可查看收藏/);
  assert.equal(dom.window.document.querySelector("#favoritesNav").hidden, true);
});

test("favorites sorts by saved time and filters news deep and paper through app state", async () => {
  const dom = shell("https://example.test/news/?view=favs");
  const fetchStub = async (url) => String(url).includes("type=favorites") ? { ok: true, json: async () => ({ success: true, data: { items: [
    { date: day.date, item_id: "pick-2", title: "保留新闻", ts: "2026-07-15T01:00:00Z" },
    { date: day.date, item_id: "deep-1", title: "深读", ts: "2026-07-15T03:00:00Z" },
    { date: day.date, item_id: "paper-1", title: "论文", ts: "2026-07-15T02:00:00Z" },
  ] } }) } : { ok: true, json: async () => ({ success: true, data: {} }) };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), personal: true, fetch: fetchStub }); await app.start();
  assert.deepEqual([...dom.window.document.querySelectorAll(".favorites-list > article h3")].map((node) => node.textContent.trim()), ["深读", "论文", "保留新闻"]);
  dom.window.document.querySelector('[data-favorites-action="type"][data-value="paper"]').click(); await app.idle();
  assert.match(dom.window.document.querySelector(".favorites-list").textContent, /论文/); assert.doesNotMatch(dom.window.document.querySelector(".favorites-list").textContent, /深读|保留新闻/);
});

test("route load errors render malicious week values as text", async () => {
  const payload = '"></option></select><img src=x onerror="globalThis.pwned=1"><script>globalThis.pwned=2</script>';
  const dom = shell(`https://example.test/news/?view=reports&period=week&week=${encodeURIComponent(payload)}`);
  const api = { ...dataApi(), weeklyManifest: async () => [payload], weekly: async () => { throw new Error(`坏周报 ${payload}`); } };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: api });
  await app.start();
  const main = dom.window.document.querySelector("main");
  assert.equal(main.querySelector("img,script"), null);
  assert.equal(dom.window.document.querySelector("#weekArchive img, #weekArchive script"), null);
  assert.equal(dom.window.document.querySelector("#weekSel").options[0].value, payload);
  assert.equal(dom.window.document.querySelector("#weekSel").options[0].textContent, payload);
  assert.match(main.textContent, /坏周报 .*<img/);
  assert.equal(dom.window.pwned, undefined);
});

test("daily archive renders manifest values as option text", async () => {
  const payload = '"></option></select><img src=x onerror="globalThis.pwned=1">';
  const dom = shell();
  const app = createNewsApp({
    window: dom.window,
    document: dom.window.document,
    dataApi: dataApi(),
    manifests: { daily: [payload] },
  });
  await app.start();
  const select = dom.window.document.querySelector("#dateSel");
  assert.equal(dom.window.document.querySelector("#dayArchive img"), null);
  assert.equal(select.options[0].value, payload);
  assert.equal(select.options[0].textContent, payload);
  assert.equal(dom.window.pwned, undefined);
});

test("read-later rejects unsafe URLs and escapes quoted data attributes", async () => {
  const dom = shell("https://example.test/news/?view=reports&period=day&date=2026-07-15");
  dom.window.document.body.insertAdjacentHTML("beforeend", '<button id="readLaterBtn" hidden></button><aside id="rlDrawer" hidden inert></aside>');
  const malicious = { date: '2026-07-15" autofocus="', item_id: 'deep-1" data-evil="1', title: "<b>标题</b>", url: "javascript:alert(1)", done: false };
  const fetchStub = async (url) => String(url).includes("type=read_later")
    ? { ok: true, json: async () => ({ success: true, data: { items: [malicious] } }) }
    : { ok: true, json: async () => ({ success: true, data: {} }) };
  const app = createNewsApp({ window: dom.window, document: dom.window.document, dataApi: dataApi(), personal: true, fetch: fetchStub });
  await app.start();
  dom.window.document.querySelector("#readLaterBtn").click();
  await app.idle();
  const drawer = dom.window.document.querySelector("#rlDrawer");
  assert.equal(drawer.querySelector("a").getAttribute("href"), "#");
  assert.equal(drawer.querySelector("b"), null);
  assert.match(drawer.textContent, /<b>标题<\/b>/);
  assert.equal(drawer.querySelector("[autofocus], [data-evil]"), null);
  assert.equal(drawer.querySelector('[data-read-later-op="done"]').dataset.date, malicious.date);
  assert.equal(drawer.querySelector('[data-read-later-op="done"]').dataset.item, malicious.item_id);
});
