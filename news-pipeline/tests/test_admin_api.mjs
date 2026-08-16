import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const github = require("../../api/_github.js");
const loginGuard = require("../../api/_loginGuard.js");
const adminArticles = require("../../api/adminArticles.js");
const adminSession = require("../../api/adminSession.js");
const adminSettings = require("../../api/adminSettings.js");
const adminUpload = require("../../api/adminUpload.js");
const newsState = require("../../api/newsState.js");

function jsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(data)
  };
}

function mockResponse() {
  return {
    statusCode: 200,
    body: null,
    headers: {},
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; },
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
    end() { return this; }
  };
}

function withRepoEnv(fn) {
  const before = { ...process.env };
  Object.assign(process.env, {
    ADMIN_TOKEN: "admin-secret",
    GITHUB_TOKEN: "github-secret",
    GITHUB_OWNER: "owner",
    GITHUB_REPO: "repo",
    GITHUB_BRANCH: "main"
  });
  return Promise.resolve(fn()).finally(() => {
    process.env = before;
  });
}

test("admin session is signed, expires, and never contains the admin token", () => {
  const now = Date.UTC(2026, 6, 17, 0, 0, 0);
  const value = github.createAdminSession("admin-secret", now);
  assert.doesNotMatch(value, /admin-secret/);
  assert.equal(github.verifyAdminSession(value, "admin-secret", now + 60_000), true);
  assert.equal(github.verifyAdminSession(value, "admin-secret", now + 9 * 60 * 60_000), false);
});

test("session scope is signed, so a personal cookie cannot reach admin writes", async () => {
  await withRepoEnv(() => {
    const now = Date.now();
    const personal = github.createAdminSession("admin-secret", now, "personal");
    const admin = github.createAdminSession("admin-secret", now, "admin");
    const withCookie = (value) => ({ headers: { cookie: `aoiblog_admin_session=${value}` } });

    // 两种 scope 都算「已登录的个人会话」，日报状态接口都放行。
    assert.doesNotThrow(() => github.requireAdminSession(withCookie(personal), now));
    assert.doesNotThrow(() => github.requireAdminSession(withCookie(admin), now));

    // 写接口只认 admin scope。
    assert.throws(
      () => github.requireAdminScope(withCookie(personal), now),
      (error) => error.status === 401,
    );
    assert.doesNotThrow(() => github.requireAdminScope(withCookie(admin), now));
    assert.doesNotThrow(() => github.requireAdminWrite(withCookie(admin), now));
    assert.throws(
      () => github.requireAdminWrite(withCookie(personal), now),
      (error) => error.status === 401,
    );

    // scope 参与签名：把 personal 改写成 admin 必然签名失配。
    const forged = admin.replace(/\.admin\./, ".personal.");
    assert.equal(github.verifyAdminSession(forged, "admin-secret", now), false);
    // 升级前的两段格式（expires.signature）一律作废，不得沉默地当成 admin。
    const legacy = `${now + 60_000}.whatever`;
    assert.equal(github.verifyAdminSession(legacy, "admin-secret", now), false);
  });
});

test("bearer admin auth is rate limited exactly like the cookie login", async () => {
  await withRepoEnv(async () => {
    loginGuard.resetLoginAttempts();
    try {
      const request = () => ({
        method: "GET",
        headers: {
          "x-vercel-forwarded-for": "203.0.113.77",
          authorization: "Bearer wrong-secret",
        },
        query: {},
      });
      for (let attempt = 0; attempt < loginGuard.MAX_FAILED_ATTEMPTS; attempt += 1) {
        const res = mockResponse();
        await adminArticles(request(), res);
        assert.equal(res.statusCode, 401);
      }
      const blocked = mockResponse();
      await adminArticles(request(), blocked);
      assert.equal(blocked.statusCode, 429);
      assert.ok(Number(blocked.headers["retry-after"]) > 0);

      // 换成 cookie 登录也应当被同一份计数拦住——两条路共用一个锁。
      const shared = mockResponse();
      await adminSession({
        method: "POST",
        headers: { "x-vercel-forwarded-for": "203.0.113.77" },
        body: { token: "admin-secret" },
      }, shared);
      assert.equal(shared.statusCode, 429);
    } finally {
      loginGuard.resetLoginAttempts();
    }
  });
});

test("missing credentials never burn the lockout budget", async () => {
  await withRepoEnv(async () => {
    loginGuard.resetLoginAttempts();
    try {
      const req = { method: "GET", headers: { "x-vercel-forwarded-for": "203.0.113.78" }, query: {} };
      for (let attempt = 0; attempt < loginGuard.MAX_FAILED_ATTEMPTS + 3; attempt += 1) {
        const res = mockResponse();
        await adminArticles(req, res);
        assert.equal(res.statusCode, 401);
      }
      assert.equal(loginGuard.retryAfterSeconds(req), 0);
    } finally {
      loginGuard.resetLoginAttempts();
    }
  });
});

test("JSON body reader rejects malformed and oversized pre-parsed bodies", async () => {
  await assert.rejects(
    github.readJsonBody({ body: '{"broken"' }),
    (error) => error.status === 400 && error.message === "Invalid JSON body",
  );
  await assert.rejects(
    github.readJsonBody({ body: { value: "x".repeat(32) } }, 16),
    (error) => error.status === 413 && error.message === "JSON body too large",
  );
  const streamed = {
    async *[Symbol.asyncIterator]() {
      yield Buffer.from('{"value":"');
      yield Buffer.from("x".repeat(32));
    },
  };
  await assert.rejects(
    github.readJsonBody(streamed, 16),
    (error) => error.status === 413 && error.message === "JSON body too large",
  );
});

test("malformed personal-session cookies are rejected as unauthorized", async () => {
  await withRepoEnv(async () => {
    const req = {
      method: "GET",
      headers: { cookie: "aoiblog_admin_session=%E0%A4%A" },
      query: { type: "misses" },
    };
    const res = mockResponse();
    await newsState(req, res);
    assert.equal(res.statusCode, 401);
    assert.equal(res.body.error, "Unauthorized");
  });
});

test("admin session rate limits repeated failed logins from one client", async () => {
  await withRepoEnv(async () => {
    adminSession._test.resetLoginAttempts();
    const request = () => ({
      method: "POST",
      headers: { "x-vercel-forwarded-for": "203.0.113.10" },
      body: { token: "wrong-secret" },
    });
    try {
      for (let attempt = 0; attempt < adminSession._test.MAX_FAILED_ATTEMPTS; attempt += 1) {
        const res = mockResponse();
        await adminSession(request(), res);
        assert.equal(res.statusCode, 401);
      }
      const blocked = mockResponse();
      await adminSession(request(), blocked);
      assert.equal(blocked.statusCode, 429);
      assert.match(blocked.body.error, /too many login attempts/i);
      assert.ok(Number(blocked.headers["retry-after"]) > 0);
    } finally {
      adminSession._test.resetLoginAttempts();
    }
  });
});

test("checking a full login-guard map does not evict an already blocked client", () => {
  loginGuard.resetLoginAttempts();
  const blocked = { headers: { "x-vercel-forwarded-for": "203.0.113.1" } };
  try {
    for (let attempt = 0; attempt < loginGuard.MAX_FAILED_ATTEMPTS; attempt += 1) {
      loginGuard.recordFailedLogin(blocked, 1_000);
    }
    for (let index = 2; index <= loginGuard.MAX_TRACKED_CLIENTS; index += 1) {
      loginGuard.recordFailedLogin({
        headers: { "x-vercel-forwarded-for": `198.51.${Math.floor(index / 256)}.${index % 256}` },
      }, 1_000);
    }
    assert.ok(loginGuard.retryAfterSeconds(blocked, 2_000) > 0);
  } finally {
    loginGuard.resetLoginAttempts();
  }
});

test("misses state requires an authenticated personal session", async () => {
  await withRepoEnv(async () => {
    const req = { method: "GET", headers: {}, query: { type: "misses" } };
    const res = mockResponse();
    await newsState(req, res);
    assert.equal(res.statusCode, 401);
    assert.equal(res.body.success, false);
  });
});

test("personal state rejects an invalid stored shape without overwriting it", async () => {
  await withRepoEnv(async () => {
    const originalFetch = globalThis.fetch;
    let writes = 0;
    globalThis.fetch = async (url, options = {}) => {
      if ((options.method || "GET") === "PUT") {
        writes += 1;
        return jsonResponse({ content: { sha: "next-sha" } });
      }
      return jsonResponse({
        content: Buffer.from('{"version":1,"items":"corrupted"}\n', "utf8").toString("base64"),
        sha: "state-sha",
      });
    };
    try {
      const session = github.createAdminSession("admin-secret", Date.now());
      const res = mockResponse();
      await newsState({
        method: "POST",
        headers: { cookie: `aoiblog_admin_session=${session}` },
        body: {
          type: "favorites",
          payload: { date: "2026-08-12", item_id: "pick-1", op: "add" },
        },
      }, res);
      assert.equal(res.statusCode, 500);
      assert.match(res.body.error, /corrupted/i);
      assert.equal(writes, 0);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});

test("misses API persists create, read, and remove through the repository file", async () => {
  await withRepoEnv(async () => {
    let stored = { version: 1, entries: [] };
    let sha = "sha-0";
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url, options = {}) => {
      assert.match(String(url), /contents\/source\/news\/data\/misses\.json/);
      if ((options.method || "GET") === "GET") {
        return jsonResponse({
          content: Buffer.from(`${JSON.stringify(stored)}\n`, "utf8").toString("base64"),
          sha,
        });
      }
      assert.equal(options.method, "PUT");
      const body = JSON.parse(options.body);
      stored = JSON.parse(Buffer.from(body.content, "base64").toString("utf8"));
      sha = `sha-${Number(sha.split("-")[1]) + 1}`;
      return jsonResponse({ content: { sha } });
    };
    try {
      const session = github.createAdminSession("admin-secret", Date.now());
      const headers = { cookie: `aoiblog_admin_session=${session}` };

      const createRes = mockResponse();
      await newsState({
        method: "POST",
        headers,
        body: {
          type: "misses",
          payload: {
            date: "2026-07-15",
            title: "遗漏事件",
            url: "https://example.com/missed",
            reason: "important_event",
          },
        },
      }, createRes);
      assert.equal(createRes.statusCode, 200);
      assert.equal(stored.entries.length, 1);
      assert.match(stored.entries[0].id, /^[0-9a-f-]{36}$/);

      const readRes = mockResponse();
      await newsState({
        method: "GET",
        headers,
        query: { type: "misses" },
      }, readRes);
      assert.equal(readRes.statusCode, 200);
      assert.deepEqual(readRes.body.data, stored);

      const removeRes = mockResponse();
      await newsState({
        method: "POST",
        headers,
        body: {
          type: "misses",
          payload: { op: "remove", id: stored.entries[0].id },
        },
      }, removeRes);
      assert.equal(removeRes.statusCode, 200);
      assert.deepEqual(stored.entries, []);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});

test("misses URL validation rejects malformed HTTP prefixes", () => {
  for (const url of ["https://", "https://not a url", "javascript:alert(1)"]) {
    assert.throws(
      () => newsState._test.validateEntry("misses", {
        date: "2026-07-15",
        url,
        reason: "deep_read",
      }),
      /http\(s\)/i,
    );
  }
});

test("misses date validation rejects impossible calendar dates", () => {
  for (const date of ["2026-02-29", "2026-02-30", "2026-13-01", "2026-00-10"]) {
    assert.throws(
      () => newsState._test.validateEntry("misses", {
        date,
        title: "Missed event",
        reason: "important_event",
      }),
      /real calendar date/i,
    );
  }
  assert.doesNotThrow(() => newsState._test.validateEntry("misses", {
    date: "2024-02-29",
    title: "Leap-day event",
    reason: "important_event",
  }));
});

test("all personal state types reject impossible calendar dates", () => {
  for (const type of ["feedback", "read_later", "favorites"]) {
    assert.throws(
      () => newsState._test.validateEntry(type, {
        date: "2026-99-99",
        item_id: "pick-1",
        action: "not_interested",
        op: "add",
        url: "https://example.com/a",
      }),
      /real calendar date/i,
    );
  }
});

test("admin article dates reject impossible calendar dates", () => {
  for (const date of [
    "2026-02-29",
    "2026-02-30",
    "2026-13-01",
    "2026-00-10",
    "2026-07-01 24:00",
    "2026-07-01 23:60",
    "2026-07-01 23:59:60",
  ]) {
    assert.throws(
      () => github.normalizeDate(date),
      /invalid date/i,
    );
  }
  assert.equal(github.normalizeDate("2024-02-29"), "2024-02-29");
  assert.equal(github.normalizeDate("2024-02-29 08:30:00"), "2024-02-29 08:30:00");
});

test("read-later rejects HTTP prefixes without a valid URL", () => {
  for (const url of ["http://", "https://not a url", "javascript:alert(1)"]) {
    assert.throws(
      () => newsState._test.validateEntry("read_later", {
        date: "2026-07-15",
        item_id: "pick-1",
        op: "add",
        url,
      }),
      /http\(s\)/i,
    );
  }
});

test("personal state rejects unknown operations instead of silently adding entries", () => {
  for (const type of ["read_later", "favorites"]) {
    assert.throws(
      () => newsState._test.validateEntry(type, {
        date: "2026-07-15",
        item_id: "pick-1",
        op: "typo",
        url: "https://example.com/a",
      }),
      /payload\.op/i,
    );
  }
});

test("personal state normalizes identifiers and validates optional favorite URLs", () => {
  const entry = newsState._test.validateEntry("favorites", {
    date: "2026-07-15",
    item_id: "  pick-1  ",
    op: "add",
    url: "https://example.com/a",
  });
  assert.equal(entry.item_id, "pick-1");

  assert.throws(
    () => newsState._test.validateEntry("favorites", {
      date: "2026-07-15",
      item_id: `${" ".repeat(60)}x`,
      op: "add",
    }),
    /item_id/i,
  );
  assert.throws(
    () => newsState._test.validateEntry("favorites", {
      date: "2026-07-15",
      item_id: "pick-1",
      op: "add",
      url: "https://",
    }),
    /http\(s\)/i,
  );
});

test("state type allowlist rejects inherited object keys", () => {
  // 取值判真会让 __proto__ / constructor 通过白名单，并把 Object.prototype
  // 当作写入路径送进 GitHub 接口；未知 type 还会落进 favorites 的兜底分支。
  for (const type of ["__proto__", "constructor", "toString", "hasOwnProperty", "valueOf"]) {
    assert.throws(
      () => newsState._test.validateEntry(type, {
        date: "2026-07-15",
        item_id: "pick-1",
        op: "add",
      }),
      /Invalid type/i,
      `${type} must not pass the allowlist`,
    );
  }
});

test("state type allowlist still accepts the four real types", () => {
  for (const type of Object.keys(newsState._test.STATE_FILES)) {
    assert.doesNotThrow(() => newsState._test.validateEntry(type, {
      date: "2026-07-15",
      item_id: "pick-1",
      title: "标题",
      action: "not_interested",
      reason: "deep_read",
      op: "add",
      url: "https://example.com/a",
    }), `${type} must remain valid`);
  }
});

test("admin frontend does not persist the bearer token in browser storage", async () => {
  const source = await readFile(new URL("../../source/admin/index.html", import.meta.url), "utf8");
  assert.doesNotMatch(source, /localStorage\.(?:getItem|setItem)\(['"]aoiblog_admin_token/);
  assert.match(source, /localStorage\.removeItem\(['"]aoiblog_admin_token/);
});

test("admin new-post dates use the Beijing calendar instead of UTC", async () => {
  const source = await readFile(new URL("../../source/admin/index.html", import.meta.url), "utf8");
  assert.doesNotMatch(source, /new Date\(\)\.toISOString\(\)\.slice\(0, 10\)/);
  assert.match(source, /timeZone:\s*['"]Asia\/Shanghai['"]/);
});

test("footer settings escape active HTML while preserving the editor value", () => {
  const siteConfig = 'title: "Blog"\nsubtitle: "Notes"\n';
  const fluidConfig = [
    "footer:",
    '  content: "<span>Current</span>"',
    "",
  ].join("\n");
  const footerText = 'Hello </span><script>alert("xss")</script> & goodbye';

  const next = adminSettings._test.applySettings(siteConfig, fluidConfig, { footerText });

  assert.doesNotMatch(next.fluidConfig, /<script>/i);
  assert.match(next.fluidConfig, /&lt;script&gt;/);
  assert.equal(
    adminSettings._test.extractSettings(next.siteConfig, next.fluidConfig).footerText,
    footerText,
  );
});

test("nav labels that would break the YAML round trip are rejected", () => {
  const fluidConfig = [
    "navbar:",
    "  menu:",
    '    - { key: "home", name: "首页", link: "/" }',
    "",
  ].join("\n");

  // 引号在第一次保存时还合法，第二次保存会让 "([^"]*)" 在反斜杠处截断，
  // 替换出 name: "新值"旧尾" —— YAML 解析失败，站点构建不出来。
  assert.throws(
    () => adminSettings._test.applySettings("", fluidConfig, { nav: { home: 'a"b' } }),
    (error) => error.status === 400 && /quotes/i.test(error.message),
  );
  assert.throws(
    () => adminSettings._test.applySettings("", fluidConfig, { nav: { home: "a\nb" } }),
    (error) => error.status === 400 && /line breaks/i.test(error.message),
  );
  assert.throws(
    () => adminSettings._test.applySettings("", fluidConfig, {
      nav: { home: "x".repeat(adminSettings._test.NAV_VALUE_MAX + 1) },
    }),
    (error) => error.status === 400 && /characters/i.test(error.message),
  );

  const ok = adminSettings._test.applySettings("", fluidConfig, { nav: { home: "主页" } });
  assert.match(ok.fluidConfig, /- \{ key: "home", name: "主页", link: "\/" \}/);
  assert.equal(adminSettings._test.extractSettings("", ok.fluidConfig).nav.home, "主页");
});

test("settings writes stay inside their own YAML block", () => {
  // about.name 和 footer.content 在别的块里各有一个同缩进的同名 key：
  // 未锚定的正则会改中第一个，把不相干的配置写坏。
  const fluidConfig = [
    "post:",
    '  name: "文章作者"',
    '  content: "文章底部"',
    "about:",
    '  name: "Aoitsuki"',
    '  intro: "工科生"',
    "footer:",
    '  content: "<span>Aoitsuki</span>"',
    "",
  ].join("\n");

  const next = adminSettings._test.applySettings("", fluidConfig, {
    aboutName: "新名字",
    footerText: "新页脚",
  });

  assert.match(next.fluidConfig, /post:\n {2}name: "文章作者"\n {2}content: "文章底部"/);
  assert.match(next.fluidConfig, /about:\n {2}name: "新名字"/);
  assert.match(next.fluidConfig, /footer:\n {2}content: "<span>新页脚<\/span>"/);
  const read = adminSettings._test.extractSettings("", next.fluidConfig);
  assert.equal(read.aboutName, "新名字");
  assert.equal(read.footerText, "新页脚");
});

test("admin frontend authenticates by cookie, never by an in-page bearer token", async () => {
  const source = await readFile(new URL("../../source/admin/index.html", import.meta.url), "utf8");
  assert.doesNotMatch(source, /Authorization/);
  assert.doesNotMatch(source, /state\.token/);
  assert.match(source, /credentials:\s*['"]same-origin['"]/);
  // 代码块回填必须用函数形式，否则代码里的 $& / $` / $' 会被当成替换模式展开。
  assert.match(source, /html\.replace\(`@@CODE_BLOCK_\$\{index\}@@`, \(\) => block\)/);
});

test("admin upload rejects bytes that do not match the claimed image type", async () => {
  await withRepoEnv(async () => {
    const originalFetch = globalThis.fetch;
    let writes = 0;
    globalThis.fetch = async () => {
      writes += 1;
      return jsonResponse({ content: { sha: "unexpected" } });
    };
    const req = {
      method: "POST",
      headers: { authorization: "Bearer admin-secret" },
      body: {
        fileName: "not-an-image.png",
        contentBase64: Buffer.from("<script>alert(1)</script>", "utf8").toString("base64"),
      },
    };
    const res = mockResponse();
    try {
      await adminUpload(req, res);
    } finally {
      globalThis.fetch = originalFetch;
    }
    assert.equal(res.statusCode, 400);
    assert.match(res.body.error, /content does not match/i);
    assert.equal(writes, 0);
  });
});

function gitBlobSha(buffer) {
  return createHash("sha1")
    .update(`blob ${buffer.length}\0`)
    .update(buffer)
    .digest("hex");
}

function currentUploadDirectory() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `source/images/uploads/${value.year}/${value.month}`;
}

test("admin content upload reuses an identical Git blob in the current month", async () => {
  await withRepoEnv(async () => {
    const png = Buffer.from("89504e470d0a1a0a00000000", "hex");
    const directory = currentUploadDirectory();
    const existingPath = `${directory}/existing-image.png`;
    const originalFetch = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, options = {}) => {
      calls.push({ url: String(url), method: options.method || "GET" });
      assert.equal(options.method || "GET", "GET");
      assert.match(decodeURIComponent(String(url)), new RegExp(directory.replaceAll("/", "\\/")));
      return jsonResponse([{
        type: "file",
        name: "existing-image.png",
        path: existingPath,
        sha: gitBlobSha(png),
      }]);
    };
    const res = mockResponse();
    try {
      await adminUpload({
        method: "POST",
        headers: { authorization: "Bearer admin-secret" },
        body: { fileName: "copy.png", contentBase64: png.toString("base64"), purpose: "content" },
      }, res);
    } finally {
      globalThis.fetch = originalFetch;
    }
    assert.equal(res.statusCode, 200);
    assert.equal(res.body.data.path, existingPath);
    assert.equal(res.body.data.url, `/${existingPath.replace(/^source\//, "")}`);
    assert.equal(calls.length, 1);
  });
});

test("admin cover upload scopes deduplication to the cover directory and uploads different bytes", async () => {
  await withRepoEnv(async () => {
    const png = Buffer.from("89504e470d0a1a0a00000001", "hex");
    const originalFetch = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, options = {}) => {
      calls.push({ url: decodeURIComponent(String(url)), method: options.method || "GET" });
      if ((options.method || "GET") === "GET") {
        return jsonResponse([{ type: "file", path: "source/images/covers/custom/other.png", sha: "different" }]);
      }
      return jsonResponse({ content: { sha: "saved" } });
    };
    const res = mockResponse();
    try {
      await adminUpload({
        method: "POST",
        headers: { authorization: "Bearer admin-secret" },
        body: { fileName: "cover.png", contentBase64: png.toString("base64"), purpose: "cover" },
      }, res);
    } finally {
      globalThis.fetch = originalFetch;
    }
    assert.equal(res.statusCode, 200);
    assert.match(calls[0].url, /source\/images\/covers\/custom/);
    assert.equal(calls[0].method, "GET");
    assert.equal(calls[1].method, "PUT");
  });
});

test("admin upload treats a missing target directory as empty", async () => {
  await withRepoEnv(async () => {
    const png = Buffer.from("89504e470d0a1a0a00000002", "hex");
    const originalFetch = globalThis.fetch;
    const methods = [];
    globalThis.fetch = async (_url, options = {}) => {
      const method = options.method || "GET";
      methods.push(method);
      if (method === "GET") return jsonResponse({ message: "Not Found" }, 404);
      return jsonResponse({ content: { sha: "saved" } });
    };
    const res = mockResponse();
    try {
      await adminUpload({
        method: "POST",
        headers: { authorization: "Bearer admin-secret" },
        body: { fileName: "new.png", contentBase64: png.toString("base64"), purpose: "content" },
      }, res);
    } finally {
      globalThis.fetch = originalFetch;
    }
    assert.equal(res.statusCode, 200);
    assert.deepEqual(methods, ["GET", "PUT"]);
  });
});

test("admin upload surfaces non-404 directory lookup failures without writing", async () => {
  await withRepoEnv(async () => {
    const png = Buffer.from("89504e470d0a1a0a00000003", "hex");
    const originalFetch = globalThis.fetch;
    const methods = [];
    globalThis.fetch = async (_url, options = {}) => {
      methods.push(options.method || "GET");
      return jsonResponse({ message: "upstream failed" }, 502);
    };
    const res = mockResponse();
    try {
      await adminUpload({
        method: "POST",
        headers: { authorization: "Bearer admin-secret" },
        body: { fileName: "failed.png", contentBase64: png.toString("base64"), purpose: "content" },
      }, res);
    } finally {
      globalThis.fetch = originalFetch;
    }
    assert.equal(res.statusCode, 502);
    assert.deepEqual(methods, ["GET"]);
  });
});

test("production dependency lock excludes known vulnerable build-chain versions", async () => {
  const lock = JSON.parse(
    await readFile(new URL("../../package-lock.json", import.meta.url), "utf8"),
  );
  const packages = Object.entries(lock.packages || {});
  const versions = (name) => packages
    .filter(([path]) => path === `node_modules/${name}` || path.endsWith(`/node_modules/${name}`))
    .map(([, metadata]) => metadata.version);
  const parts = (version) => String(version).split(".").map(Number);
  const compare = (version, target) => {
    const left = parts(version);
    const right = parts(target);
    for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
      if ((left[index] || 0) !== (right[index] || 0)) {
        return (left[index] || 0) < (right[index] || 0) ? -1 : 1;
      }
    }
    return 0;
  };

  // GHSA-rgw5-rvv9-x895 patches each major line separately, so a single
  // ">= 5.0.9" floor would reject 1.1.18 even though it carries the fix.
  // minimatch@3 needs the 1.x line: 5.x still ships a CommonJS build but
  // exports { expand, ... } instead of the bare function minimatch@3 calls.
  const braceExpansionFloor = { 1: "1.1.18", 2: "2.1.4", 3: "3.0.6", 4: "5.0.9", 5: "5.0.9" };
  assert.ok(
    versions("brace-expansion").every((version) => {
      const floor = braceExpansionFloor[parts(version)[0]];
      return floor ? compare(version, floor) >= 0 : false;
    }),
    "brace-expansion must be patched for unbounded expansion on its own major line",
  );
  assert.ok(
    versions("jake").every((version) => (
      compare(version, "10.6.1") < 0 || compare(version, "10.9.4") > 0
    )),
    "jake 10.6.1 through 10.9.4 pulls a vulnerable filelist chain",
  );
});

test("the stylus build chain can still brace-expand after security overrides", () => {
  // brace-expansion 5.x moved from `module.exports = expand` to a named-export
  // object, so overriding it into minimatch@3 leaves that package's
  // `require('brace-expansion')(pattern)` call throwing "expand is not a
  // function". Version assertions cannot see an export-shape mismatch, so
  // exercise the real call path.
  //
  // Resolve through require.resolve rather than a hardcoded ../../node_modules
  // URL: a git worktree has no node_modules of its own, and only require()
  // resolution climbs to the parent repo. new URL() and glob's cwd-relative
  // patterns do not, so the old form failed in every worktree whether or not
  // the override was actually broken.
  const stylusRequire = createRequire(require.resolve("stylus"));
  const glob = stylusRequire("glob");
  const fluidRoot = require.resolve("hexo-theme-fluid/package.json")
    .replace(/[\\/]package\.json$/, "")
    .replace(/\\/g, "/");
  const matched = glob.sync(`${fluidRoot}/source/css/{main,highlight}.styl`);
  assert.equal(matched.length, 2, "brace expansion must resolve both branches");
});

test("post paths are restricted to a single flat .md file under source/_posts", () => {
  const accepted = [
    "source/_posts/2026-03-20-ce-shi.md",
    "source/_posts/2026-08-06-a-b-c.md",
  ];
  for (const filePath of accepted) {
    assert.equal(github.validatePostPath(filePath), filePath);
  }

  // A prefix+suffix blacklist let these through. None escaped source/_posts,
  // but the shape should be pinned by an allowlist rather than by enumerating
  // the traversal spellings an attacker might try.
  const rejected = [
    "source/_posts/../../../.github/workflows/evil.md",
    "source/_posts/sub/dir/deep.md",
    "source/_posts/%2e%2e/evil.md",
    "source/_posts/.md",
    "source/_posts/..md",
    "source/_posts/a\0.md",
    "source/_postsevil.md",
    "",
  ];
  for (const filePath of rejected) {
    assert.throws(() => github.validatePostPath(filePath), /Invalid post path/, filePath);
  }
});

test("cover URLs accept site paths and http(s) only", () => {
  assert.equal(github.validateCoverUrl(""), "");
  assert.equal(github.validateCoverUrl("/images/covers/custom/x.webp"), "/images/covers/custom/x.webp");
  assert.equal(github.validateCoverUrl("https://cdn.example.com/a.png"), "https://cdn.example.com/a.png");

  // The theme renders index_img through <%= url_for(...) %>, so EJS escaping
  // already blocks attribute escapes. This keeps the one user-controlled URL
  // that had no protocol check aligned with adminSettings and safeUrl().
  for (const value of [
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "//evil.com/a.png",
    '" onerror="alert(1)',
    "/images/a.png\nX-Injected: 1",
  ]) {
    assert.throws(() => github.validateCoverUrl(value), /Cover URL must/, value);
  }
});

test("composing a post rejects a hostile cover URL", () => {
  assert.throws(() => github.composePost({
    title: "Hostile cover",
    date: "2026-08-06",
    category: "随笔",
    content: "Body",
    index_img: "javascript:alert(1)",
  }, { default: "/fallback.webp" }, null, "source/_posts/2026-08-06-hostile-cover.md"), /Cover URL must/);
});

test("a category named after a prototype key cannot leak a function into front matter", () => {
  // `coverForCategory` reads `coverMap[category]` and the category name is
  // user-controlled (the admin creates categories freely). A post filed under
  // "toString" used to resolve to the inherited *function*, which yamlString
  // then wrote out as `index_img: "function toString() { [native code] }"` --
  // a visibly broken cover on a real page, with no error anywhere.
  const map = { default: "/images/covers/defaults/fallback.webp" };
  for (const category of ["toString", "valueOf", "constructor", "hasOwnProperty", "__proto__"]) {
    const post = github.composePost({
      title: "Prototype category",
      date: "2026-08-11",
      category,
      content: "Body",
    }, map, null, "source/_posts/2026-08-11-prototype-category.md");
    assert.match(post.content, /index_img: "\/images\/covers\/defaults\/fallback\.webp"/, category);
    assert.doesNotMatch(post.content, /native code|function /, category);
  }
});

test("cover map values are validated on read, not only when set", () => {
  // adminSettings validates a cover URL when it is written, but the map lives in
  // source/_data/category-covers.json and is also hand-edited. Without a check
  // on read, a bad value there reached front matter through a path that skipped
  // validateCoverUrl entirely -- the same sink, one unvalidated bypass.
  const hostile = {
    A: "javascript:alert(1)",
    B: "//evil.example/a.png",
    C: "/ok.webp\nX-Injected: 1",
    default: "/images/covers/defaults/fallback.webp",
  };
  for (const category of ["A", "B", "C"]) {
    const post = github.composePost({
      title: "Poisoned map",
      date: "2026-08-11",
      category,
      content: "Body",
    }, hostile, null, "source/_posts/2026-08-11-poisoned-map.md");
    assert.match(post.content, /index_img: "\/images\/covers\/defaults\/fallback\.webp"/, category);
  }
  // A legitimate mapping must still win over the fallback.
  const good = github.composePost({
    title: "Normal",
    date: "2026-08-11",
    category: "技术学习",
    content: "Body",
  }, { 技术学习: "/images/covers/defaults/technology-learning.webp" }, null,
    "source/_posts/2026-08-11-normal.md");
  assert.match(good.content, /index_img: "\/images\/covers\/defaults\/technology-learning\.webp"/);
});

test("news frontend no longer reads or sends the bearer token", async () => {
  const app = await readFile(new URL("../../source/news/js/app.js", import.meta.url), "utf8");
  const client = await readFile(new URL("../../source/news/js/api-client.js", import.meta.url), "utf8");
  const publicScript = await readFile(new URL("../../source/js/twikoo-legacy-path.js", import.meta.url), "utf8");
  assert.doesNotMatch(app, /localStorage\.(?:getItem|setItem)\(['"]aoiblog_admin_token/);
  assert.match(app, /localStorage\.removeItem\(['"]aoiblog_admin_token/);
  assert.match(publicScript, /localStorage\.removeItem\(['"]aoiblog_admin_token/);
  assert.ok(app.indexOf('removeItem("aoiblog_admin_token")') < app.indexOf("resolvePersonalSession(window.fetch.bind(window)"));
  assert.doesNotMatch(client, /Authorization/);
  assert.match(client, /credentials:\s*["']same-origin["']/);
});

test("news session detection falls back when the session endpoint hangs", async () => {
  const { resolvePersonalSession } = await import("../../source/news/js/app.js");
  const personal = await resolvePersonalSession(
    () => new Promise(() => {}),
    (callback) => { callback(); return 1; },
    () => {}
  );
  assert.equal(personal, false);
});

test("shipped source files contain no Unicode replacement characters", async () => {
  const paths = [
    "../../source/js/aoiblog-home.js",
    "../../source/admin/index.html",
    "../../source/news/js/app.js"
  ];
  for (const path of paths) {
    const source = await readFile(new URL(path, import.meta.url), "utf8");
    assert.doesNotMatch(source, /\uFFFD/, `${path} contains broken text encoding`);
  }
});

test("write-enabled workflow pins actions and Python packages immutably", async () => {
  const workflow = await readFile(new URL("../../.github/workflows/daily-news.yml", import.meta.url), "utf8");
  const requirements = await readFile(new URL("../requirements.txt", import.meta.url), "utf8");
  assert.match(workflow, /actions\/checkout@[a-f0-9]{40}/);
  assert.match(workflow, /actions\/setup-python@[a-f0-9]{40}/);
  assert.doesNotMatch(workflow, /uses:\s+actions\/(?:checkout|setup-python)@v\d/);
  const packageLines = requirements.split(/\r?\n/).filter((line) => line && !/^\s*[#-]/.test(line));
  assert.ok(packageLines.length > 4, "transitive dependencies must be locked");
  assert.ok(packageLines.every((line) => /==[^\s\\]+/.test(line) || /\/[^/]+-\d+(?:\.\d+)+-[^/]+\.whl/.test(line)), "every dependency must use an exact version or a versioned wheel");
  assert.match(requirements, /--hash=sha256:/);
  assert.match(requirements, /news-pipeline\/vendor\/sgmllib3k-1\.0\.0-py3-none-any\.whl/);
  assert.doesNotMatch(requirements, /^sgmllib3k==/m);
});

test("deployment headers prevent MIME sniffing and admin clickjacking", async () => {
  const config = JSON.parse(
    await readFile(new URL("../../vercel.json", import.meta.url), "utf8"),
  );
  const headersFor = (source) => Object.fromEntries(
    config.headers
      .filter((rule) => rule.source === source)
      .flatMap((rule) => rule.headers)
      .map(({ key, value }) => [key.toLowerCase(), value]),
  );

  assert.equal(headersFor("/(.*)")["x-content-type-options"], "nosniff");
  assert.equal(headersFor("/admin/(.*)")["x-frame-options"], "DENY");
  const adminPolicy = headersFor("/admin/(.*)")["content-security-policy"];
  assert.match(adminPolicy, /(?:^|; )script-src 'self' 'sha256-[A-Za-z0-9+/=]+'(?:;|$)/);
  assert.doesNotMatch(adminPolicy, /'unsafe-inline'|'unsafe-eval'/);
  assert.match(adminPolicy, /(?:^|; )object-src 'none'(?:;|$)/);
  assert.match(adminPolicy, /(?:^|; )base-uri 'none'(?:;|$)/);
  assert.match(adminPolicy, /(?:^|; )frame-ancestors 'none'(?:;|$)/);
  assert.equal(headersFor("/admin")["content-security-policy"], adminPolicy);
  const adminHtml = await readFile(new URL("../../source/admin/index.html", import.meta.url), "utf8");
  assert.doesNotMatch(adminHtml, /\s(?:style|on[a-z]+)\s*=/i);
  const inlineScript = /<script>([\s\S]*?)<\/script>\s*<\/body>/.exec(adminHtml)?.[1];
  const inlineStyle = /<style>([\s\S]*?)<\/style>/.exec(adminHtml)?.[1];
  assert.ok(inlineScript && inlineStyle);
  // Git stores this text as LF and the HTML parser normalizes source newlines
  // before CSP hashes inline blocks. A hash of a Windows CRLF checkout works
  // only in the local file and blocks the deployed admin page.
  const cspHash = (value) => createHash("sha256")
    .update(value.replace(/\r\n?/g, "\n"))
    .digest("base64");
  assert.ok(adminPolicy.includes(`script-src 'self' 'sha256-${cspHash(inlineScript)}'`));
  assert.ok(adminPolicy.includes(`style-src 'self' 'sha256-${cspHash(inlineStyle)}'`));
  const newsPolicy = headersFor("/news/(.*)")["content-security-policy"];
  assert.match(newsPolicy, /(?:^|; )script-src 'self'(?:;|$)/);
  assert.match(newsPolicy, /(?:^|; )object-src 'none'(?:;|$)/);
  assert.match(newsPolicy, /(?:^|; )base-uri 'none'(?:;|$)/);
  assert.match(newsPolicy, /(?:^|; )frame-ancestors 'none'(?:;|$)/);
  assert.equal(headersFor("/news")["content-security-policy"], newsPolicy);
});

test("authenticated API responses are explicitly non-cacheable", () => {
  const res = mockResponse();
  github.setCors(res);
  assert.equal(res.headers["cache-control"], "no-store");
  assert.equal(res.headers["access-control-allow-origin"], undefined);
});

test("personal state files are excluded from static deployments", async () => {
  const hexoConfig = await readFile(new URL("../../_config.yml", import.meta.url), "utf8");
  const vercelIgnore = await readFile(new URL("../../.vercelignore", import.meta.url), "utf8");
  const privateFiles = [
    "feedback.json",
    "read_later.json",
    "favorites.json",
    "misses.json",
    "vocab-book.json",
    "interest_profile.md",
  ];

  for (const file of privateFiles) {
    const relativePath = `news/data/${file}`;
    assert.match(hexoConfig, new RegExp(`- ["']${relativePath.replace(".", "\\.")}["']`));
    assert.match(vercelIgnore, new RegExp(`^source/${relativePath.replace(".", "\\.")}$`, "m"));
  }
});

test("atomic multi-file update creates one commit and advances the branch once", async () => {
  await withRepoEnv(async () => {
    const calls = [];
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url, options = {}) => {
      const method = options.method || "GET";
      const body = options.body ? JSON.parse(options.body) : null;
      calls.push({ url: String(url), method, body });
      if (String(url).endsWith("/git/ref/heads/main")) return jsonResponse({ object: { sha: "head-sha" } });
      if (String(url).endsWith("/git/commits/head-sha")) return jsonResponse({ tree: { sha: "base-tree" } });
      if (String(url).endsWith("/git/blobs")) return jsonResponse({ sha: `blob-${calls.filter((call) => call.url.endsWith("/git/blobs")).length}` }, 201);
      if (String(url).endsWith("/git/trees")) return jsonResponse({ sha: "next-tree" }, 201);
      if (String(url).endsWith("/git/commits")) return jsonResponse({ sha: "next-commit" }, 201);
      if (String(url).endsWith("/git/refs/heads/main")) return jsonResponse({ object: { sha: "next-commit" } });
      throw new Error(`Unexpected request: ${method} ${url}`);
    };
    try {
      await github.putTextFilesAtomic([
        { path: "_config.yml", content: "title: next" },
        { path: "_config.fluid.yml", content: "footer: next" }
      ], "update settings");
    } finally {
      globalThis.fetch = originalFetch;
    }

    const commits = calls.filter((call) => call.url.endsWith("/git/commits") && call.method === "POST");
    const updates = calls.filter((call) => call.url.endsWith("/git/refs/heads/main") && call.method === "PATCH");
    assert.equal(commits.length, 1);
    assert.equal(updates.length, 1);
    assert.deepEqual(commits[0].body.parents, ["head-sha"]);
    assert.equal(calls.find((call) => call.url.endsWith("/git/trees") && call.method === "POST").body.tree.length, 2);
  });
});

test("atomic multi-file update rejects stale source blobs before creating a commit", async () => {
  await withRepoEnv(async () => {
    const calls = [];
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url, options = {}) => {
      calls.push({ url: String(url), method: options.method || "GET" });
      if (String(url).endsWith("/git/ref/heads/main")) return jsonResponse({ object: { sha: "head-sha" } });
      if (String(url).endsWith("/git/commits/head-sha")) return jsonResponse({ tree: { sha: "base-tree" } });
      if (String(url).includes("/git/trees/base-tree?recursive=1")) {
        return jsonResponse({ tree: [{ path: "_config.yml", type: "blob", sha: "newer-sha" }] });
      }
      return jsonResponse({ sha: "unexpected" }, 201);
    };
    try {
      await assert.rejects(
        github.putTextFilesAtomic(
          [{ path: "_config.yml", content: "title: stale" }],
          "update settings",
          { expectedFiles: [{ path: "_config.yml", sha: "editor-sha" }] }
        ),
        (error) => error.status === 409
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
    assert.equal(calls.some((call) => call.url.endsWith("/git/commits") && call.method === "POST"), false);
  });
});

test("article save rejects a stale editor SHA without writing", async () => {
  await withRepoEnv(async () => {
    const originalFetch = globalThis.fetch;
    let writes = 0;
    globalThis.fetch = async (url, options = {}) => {
      const path = String(url);
      if ((options.method || "GET") === "PUT") { writes += 1; return jsonResponse({ content: { sha: "saved" } }); }
      if (path.includes("category-covers.json")) return jsonResponse({ sha: "covers", content: Buffer.from('{"default":"/fallback.webp"}').toString("base64") });
      if (path.includes("source/_posts/post.md")) return jsonResponse({ sha: "current-sha", content: Buffer.from('---\ntitle: "Current"\ndate: "2026-07-17"\ncategories:\n  - "技术"\n---\nCurrent body\n').toString("base64") });
      throw new Error(`Unexpected request: ${path}`);
    };
    const req = { method: "POST", headers: { authorization: "Bearer admin-secret" }, query: {}, body: { article: { filePath: "source/_posts/post.md", sha: "editor-sha", title: "Edited", date: "2026-07-17", category: "技术", content: "Edited body" } } };
    const res = mockResponse();
    try { await adminArticles(req, res); } finally { globalThis.fetch = originalFetch; }
    assert.equal(res.statusCode, 409);
    assert.equal(writes, 0);
  });
});

test("article delete rejects a stale editor SHA without deleting", async () => {
  await withRepoEnv(async () => {
    const originalFetch = globalThis.fetch;
    let deletes = 0;
    globalThis.fetch = async (url, options = {}) => {
      if ((options.method || "GET") === "DELETE") { deletes += 1; return jsonResponse({}); }
      return jsonResponse({ sha: "current-sha", content: Buffer.from("post").toString("base64") });
    };
    const req = { method: "DELETE", headers: { authorization: "Bearer admin-secret" }, query: {}, body: { filePath: "source/_posts/post.md", sha: "editor-sha" } };
    const res = mockResponse();
    try { await adminArticles(req, res); } finally { globalThis.fetch = originalFetch; }
    assert.equal(res.statusCode, 409);
    assert.equal(deletes, 0);
  });
});

test("new articles serialize a timezone-stable midnight", () => {
  const composed = github.composePost({
    title: "New post",
    date: "2026-08-01",
    category: "随笔",
    content: "Body",
  }, { default: "/fallback.webp" }, null, "source/_posts/2026-08-01-new-post.md");

  assert.match(composed.content, /^date: "2026-08-01 00:00:00"$/m);
  assert.match(composed.content, /^permalink: "\/2026\/08\/01\/new-post\/"$/m);
});

test("new articles preserve an explicit publication time", () => {
  const composed = github.composePost({
    title: "Scheduled post",
    date: "2026-08-01 09:30:00",
    category: "随笔",
    content: "Body",
  }, { default: "/fallback.webp" }, null, "source/_posts/2026-08-01-scheduled-post.md");

  assert.match(composed.content, /^date: "2026-08-01 09:30:00"$/m);
  assert.match(composed.content, /^permalink: "\/2026\/08\/01\/scheduled-post\/"$/m);
});

test("editing an existing article preserves its original date scalar", () => {
  const existing = {
    date: "2026-07-23",
    category: "随笔",
    index_img: "/cover.webp",
  };
  const composed = github.composePost({
    title: "Existing post",
    date: "2026-07-23",
    category: "随笔",
    content: "Updated body",
  }, { default: "/fallback.webp" }, existing, "source/_posts/2026-07-23-existing-post.md");

  assert.match(composed.content, /^date: "2026-07-23"$/m);
  assert.doesNotMatch(composed.content, /^date: "2026-07-23 00:00:00"$/m);
  assert.doesNotMatch(composed.content, /^permalink:/m);
});

test("changing an existing article date uses timezone-stable midnight", () => {
  const existing = {
    date: "2026-07-23",
    category: "随笔",
    index_img: "/cover.webp",
  };
  const composed = github.composePost({
    title: "Rescheduled post",
    date: "2026-08-02",
    category: "随笔",
    content: "Updated body",
  }, { default: "/fallback.webp" }, existing, "source/_posts/2026-07-23-rescheduled-post.md");

  assert.match(composed.content, /^date: "2026-08-02 00:00:00"$/m);
  assert.match(composed.content, /^permalink: "\/2026\/08\/02\/rescheduled-post\/"$/m);
});

test("editing an explicit publication time on the same day uses the new time", () => {
  const existing = {
    date: "2026-08-01 08:00:00",
    category: "随笔",
    index_img: "/cover.webp",
  };
  const composed = github.composePost({
    title: "Rescheduled post",
    date: "2026-08-01 09:30:00",
    category: "随笔",
    content: "Updated body",
  }, { default: "/fallback.webp" }, existing, "source/_posts/2026-08-01-rescheduled-post.md");

  assert.match(composed.content, /^date: "2026-08-01 09:30:00"$/m);
  assert.doesNotMatch(composed.content, /^date: "2026-08-01 08:00:00"$/m);
  assert.doesNotMatch(composed.content, /^permalink:/m);
});

test("editing title or time preserves an existing explicit permalink", () => {
  const existing = {
    date: "2026-08-01 08:00:00",
    permalink: "/2026/07/31/stable-slug/",
    category: "随笔",
    index_img: "/cover.webp",
  };
  const composed = github.composePost({
    title: "Renamed post",
    date: "2026-08-01 09:30:00",
    category: "随笔",
    content: "Updated body",
  }, { default: "/fallback.webp" }, existing, "source/_posts/2026-08-01-file-slug.md");

  assert.match(composed.content, /^permalink: "\/2026\/07\/31\/stable-slug\/"$/m);
});

test("changing the calendar date updates only the date segments of an explicit permalink", () => {
  const existing = {
    date: "2026-08-01",
    permalink: "/2026/07/31/stable-slug/",
    category: "随笔",
    index_img: "/cover.webp",
  };
  const composed = github.composePost({
    title: "Renamed post",
    date: "2026-08-03",
    category: "随笔",
    content: "Updated body",
  }, { default: "/fallback.webp" }, existing, "source/_posts/2026-08-01-file-slug.md");

  assert.match(composed.content, /^permalink: "\/2026\/08\/03\/stable-slug\/"$/m);
});

test("post parsing exposes an optional explicit permalink", () => {
  const source = [
    "---",
    'title: "Pinned"',
    'date: "2026-08-01 00:00:00"',
    'permalink: "/2026/07/31/pinned/"',
    "---",
    "Body",
    "",
  ].join("\n");
  assert.equal(
    github.parsePost("source/_posts/2026-08-01-pinned.md", source, "sha").permalink,
    "/2026/07/31/pinned/",
  );
});

test("post parsing omits permalink for historical articles that do not define one", () => {
  const source = [
    "---",
    'title: "Historical"',
    'date: "2026-07-23"',
    "---",
    "Body",
    "",
  ].join("\n");
  const article = github.parsePost("source/_posts/2026-07-23-historical.md", source, "sha");
  assert.equal(Object.hasOwn(article, "permalink"), false);
});

test("quoted front matter scalars survive repeated parse and save cycles", () => {
  const source = [
    "---",
    'title: "A \\"quoted\\" \\\\ title"',
    'date: "2026-08-01 00:00:00"',
    "categories:",
    '  - "Essay"',
    'index_img: "/cover.webp"',
    "---",
    "Body",
    "",
  ].join("\n");
  const first = github.parsePost("source/_posts/2026-08-01-example.md", source, "sha", true);
  assert.equal(first.title, 'A "quoted" \\ title');

  const saved = github.composePost({ ...first, content: first.content }, { default: "/fallback.webp" }, first, first.filePath);
  const second = github.parsePost(first.filePath, saved.content, "sha-2", true);
  assert.equal(second.title, first.title);
  const savedAgain = github.composePost({ ...second, content: second.content }, { default: "/fallback.webp" }, second, second.filePath);
  assert.equal(savedAgain.content, saved.content);
});

test("editing a post preserves uncontrolled front matter and additional categories", () => {
  const source = [
    "---",
    'title: "Original"',
    'date: "2026-08-01 00:00:00"',
    'updated: "2026-08-01"',
    "categories:",
    '  - "Essay"',
    '  - "Personal"',
    "tags:",
    '  - "kept"',
    "custom:",
    "  nested: true",
    "sticky: 3",
    'index_img: "/cover.webp"',
    'old_id: "legacy-id"',
    'twikooPath: "/legacy/comments/"',
    "---",
    "Body",
    "",
  ].join("\n");
  const existing = github.parsePost("source/_posts/2026-08-01-original.md", source, "sha", true);
  assert.equal(Object.keys(existing).some((key) => /front/i.test(key)), false);

  const composed = github.composePost({
    ...existing,
    title: "Renamed",
    category: "Updated essay",
    content: "Updated body",
  }, { default: "/fallback.webp" }, existing, existing.filePath);

  for (const unchanged of [
    '  - "Personal"',
    'tags:\n  - "kept"',
    'custom:\n  nested: true',
    'sticky: 3',
    'old_id: "legacy-id"',
    'twikooPath: "/legacy/comments/"',
  ]) {
    assert.ok(composed.content.includes(unchanged), unchanged);
  }
  assert.match(composed.content, /^  - "Updated essay"$/m);
  assert.deepEqual(github.parsePost(existing.filePath, composed.content, "sha-2").categories, ["Updated essay", "Personal"]);
});

test("category cover lookup falls back only for a missing mapping file", async () => {
  await withRepoEnv(async () => {
    const originalFetch = global.fetch;
    try {
      global.fetch = async () => jsonResponse({ message: "Not Found" }, 404);
      assert.deepEqual(await github.readCoverMap(), { default: "/images/covers/defaults/fallback.webp" });

      global.fetch = async () => jsonResponse({ message: "server error" }, 500);
      await assert.rejects(github.readCoverMap(), (error) => error.status === 500);

      global.fetch = async () => jsonResponse({ content: Buffer.from("not json").toString("base64"), sha: "sha" });
      await assert.rejects(github.readCoverMap(), /cover map|JSON/i);

      global.fetch = async () => jsonResponse({ content: Buffer.from("[]").toString("base64"), sha: "sha" });
      await assert.rejects(github.readCoverMap(), /cover map|object/i);
    } finally {
      global.fetch = originalFetch;
    }
  });
});
