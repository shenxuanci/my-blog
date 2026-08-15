import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const adminComments = require("../../api/adminComments.js");
const twikoo = require("../../api/_twikoo.js");

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

async function withAdminEnv(fn) {
  const before = { ...process.env };
  const originalFetch = globalThis.fetch;
  process.env.ADMIN_TOKEN = "admin-secret";
  try {
    return await fn();
  } finally {
    globalThis.fetch = originalFetch;
    process.env = before;
  }
}

function request(method, body) {
  return {
    method,
    headers: { authorization: "Bearer admin-secret" },
    body
  };
}

const root = {
  _id: "root01",
  nick: "Alice",
  avatar: "https://avatar.example/alice.png",
  link: "https://alice.example/",
  mail: "private@example.com",
  ip: "203.0.113.1",
  ipRegion: "Private Region",
  ua: "Private Agent",
  uid: "private-uid",
  href: "https://attacker.example/forged",
  comment: "<p>Hello &amp; <a href=\"https://example.com\">world</a><br><img src=\"x\"></p><script>alert(1)</script>",
  url: "article_1",
  created: 20,
  isSpam: false,
  top: true
};

const reply = {
  _id: "reply01",
  rid: "root01",
  pid: "root01",
  nick: "Bob",
  mail: "needle-only-in-private-mail@example.com",
  comment: "<p>Public reply</p>",
  url: "article_1",
  created: 10,
  isSpam: true
};

test("Twikoo normalization returns only public moderation fields and plain text", () => {
  const item = twikoo.normalizeComment(root);
  assert.deepEqual(Object.keys(item).sort(), [
    "avatarUrl", "created", "hidden", "id", "kind", "nick", "parentId",
    "path", "pinned", "rootId", "text", "websiteUrl"
  ]);
  assert.equal(item.text, "Hello & world\n[图片]");
  assert.equal(item.kind, "root");
  assert.equal(item.rootId, "root01");
  assert.equal(item.avatarUrl, "https://avatar.example/alice.png");
  assert.equal(item.websiteUrl, "https://alice.example/");
  assert.doesNotMatch(JSON.stringify(item), /private|attacker|script|href|mail|203\.0\.113/);
  assert.equal(twikoo.normalizeComment({ ...root, created: 1e100 }).created, 0);
  const credentialUrls = twikoo.normalizeComment({
    ...root,
    avatar: "https://user:pass@avatar.example/image.png",
    link: "https://user:pass@example.com/"
  });
  assert.equal(credentialUrls.avatarUrl, "");
  assert.equal(credentialUrls.websiteUrl, "");
});

test("normal admin pagination delegates one page and never exposes the Twikoo token", async () => {
  await withAdminEnv(async () => {
    const calls = [];
    globalThis.fetch = async (_url, options) => {
      const body = JSON.parse(options.body);
      calls.push(body);
      return jsonResponse({ code: 0, count: 1, data: [root] });
    };

    const res = mockResponse();
    await adminComments(request("POST", {
      page: 2,
      pageSize: 20,
      keyword: "",
      visibility: "hidden",
      read: "all",
      readIds: []
    }), res);

    assert.equal(res.statusCode, 200);
    assert.equal(calls.length, 1);
    assert.deepEqual(
      { event: calls[0].event, page: calls[0].page, per: calls[0].per, type: calls[0].type },
      { event: "COMMENT_GET_FOR_ADMIN", page: 2, per: 20, type: "HIDDEN" }
    );
    assert.equal(calls[0].accessToken, createHash("md5").update("admin-secret").digest("hex"));
    assert.doesNotMatch(JSON.stringify(res.body), /admin-secret|private@example|203\.0\.113/);
    assert.equal(res.body.data.items[0].id, "root01");
  });
});

test("Twikoo calls reject redirects, missing business codes, and slow response bodies", async () => {
  await withAdminEnv(async () => {
    let fetchOptions;
    globalThis.fetch = async (_url, options) => {
      fetchOptions = options;
      return jsonResponse({});
    };
    await assert.rejects(
      twikoo.callTwikoo("COMMENT_SET_FOR_ADMIN", { id: "root01", set: { isSpam: true } }),
      (error) => error.status === 502
    );
    assert.equal(fetchOptions.redirect, "error");

    globalThis.fetch = async (_url, options) => ({
      ok: true,
      text: () => new Promise((_resolve, reject) => {
        options.signal.addEventListener("abort", () => {
          const error = new Error("aborted");
          error.name = "AbortError";
          reject(error);
        }, { once: true });
      })
    });
    await assert.rejects(
      twikoo.callTwikoo("COMMENT_GET_FOR_ADMIN", { page: 1, per: 20 }, { timeoutMs: 10 }),
      (error) => error.status === 503 && /timed out/i.test(error.message)
    );
  });
});

test("full scans reject pagination drift and duplicate records", async () => {
  await withAdminEnv(async () => {
    const records = Array.from({ length: 100 }, (_, index) => ({
      ...root,
      _id: `comment_${index}`
    }));
    globalThis.fetch = async (_url, options) => {
      const body = JSON.parse(options.body);
      if (body.page === 1) return jsonResponse({ code: 0, count: 101, data: records });
      return jsonResponse({ code: 0, count: 101, data: [{ ...root, _id: "comment_0" }] });
    };

    const duplicate = mockResponse();
    await adminComments(request("POST", {
      page: 1,
      pageSize: 20,
      keyword: "hello",
      visibility: "all",
      read: "all",
      readIds: []
    }), duplicate);
    assert.equal(duplicate.statusCode, 502);

    globalThis.fetch = async (_url, options) => {
      const body = JSON.parse(options.body);
      if (body.page === 1) return jsonResponse({ code: 0, count: 101, data: records });
      return jsonResponse({ code: 0, count: 102, data: [{ ...root, _id: "comment_100" }] });
    };
    const drift = mockResponse();
    await adminComments(request("DELETE", { id: "comment_0" }), drift);
    assert.equal(drift.statusCode, 502);
    assert.doesNotMatch(JSON.stringify(drift.body), /comment_100/);
  });
});

test("keyword and unread filtering scan sanitized public fields before pagination", async () => {
  await withAdminEnv(async () => {
    const calls = [];
    globalThis.fetch = async (_url, options) => {
      const body = JSON.parse(options.body);
      calls.push(body);
      return jsonResponse({ code: 0, count: 2, data: [root, reply] });
    };

    const privateNeedle = mockResponse();
    await adminComments(request("POST", {
      page: 1,
      pageSize: 10,
      keyword: "needle-only-in-private-mail",
      visibility: "all",
      read: "all",
      readIds: []
    }), privateNeedle);
    assert.equal(privateNeedle.body.data.total, 0);
    assert.ok(calls.every((call) => !Object.hasOwn(call, "keyword")));

    const unread = mockResponse();
    await adminComments(request("POST", {
      page: 1,
      pageSize: 10,
      keyword: "",
      visibility: "all",
      read: "unread",
      readIds: ["root01"]
    }), unread);
    assert.equal(unread.body.data.total, 1);
    assert.equal(unread.body.data.items[0].id, "reply01");
  });
});

test("moderation actions are whitelisted and replies cannot be pinned", async () => {
  await withAdminEnv(async () => {
    const calls = [];
    globalThis.fetch = async (_url, options) => {
      const body = JSON.parse(options.body);
      calls.push(body);
      if (body.event === "COMMENT_GET_FOR_ADMIN") {
        return jsonResponse({ code: 0, count: 2, data: [root, reply] });
      }
      return jsonResponse({ code: 0, updated: 1 });
    };

    const blocked = mockResponse();
    await adminComments(request("PATCH", { id: "reply01", action: "pin" }), blocked);
    assert.equal(blocked.statusCode, 400);
    assert.equal(calls.filter((call) => call.event === "COMMENT_SET_FOR_ADMIN").length, 0);

    const hidden = mockResponse();
    await adminComments(request("PATCH", { id: "root01", action: "hide", set: { mail: "leak" } }), hidden);
    assert.equal(hidden.statusCode, 200);
    const mutation = calls.find((call) => call.event === "COMMENT_SET_FOR_ADMIN");
    assert.deepEqual(mutation.set, { isSpam: true });
  });
});

test("moderation mutations reject success responses without a changed record", async () => {
  await withAdminEnv(async () => {
    globalThis.fetch = async (_url, options) => {
      const body = JSON.parse(options.body);
      if (body.event === "COMMENT_GET_FOR_ADMIN") {
        return jsonResponse({ code: 0, count: 1, data: [root] });
      }
      return jsonResponse({ code: 0, updated: 0 });
    };
    const res = mockResponse();
    await adminComments(request("PATCH", { id: "root01", action: "hide" }), res);
    assert.equal(res.statusCode, 502);
  });
});

test("deleting a root with replies is blocked while deleting a reply is allowed", async () => {
  await withAdminEnv(async () => {
    const calls = [];
    globalThis.fetch = async (_url, options) => {
      const body = JSON.parse(options.body);
      calls.push(body);
      if (body.event === "COMMENT_GET_FOR_ADMIN") {
        return jsonResponse({ code: 0, count: 2, data: [root, reply] });
      }
      return jsonResponse({ code: 0, deleted: 1 });
    };

    const rootDelete = mockResponse();
    await adminComments(request("DELETE", { id: "root01" }), rootDelete);
    assert.equal(rootDelete.statusCode, 409);
    assert.equal(calls.filter((call) => call.event === "COMMENT_DELETE_FOR_ADMIN").length, 0);

    const replyDelete = mockResponse();
    await adminComments(request("DELETE", { id: "reply01" }), replyDelete);
    assert.equal(replyDelete.statusCode, 200);
    assert.equal(calls.filter((call) => call.event === "COMMENT_DELETE_FOR_ADMIN").length, 1);
  });
});

test("comment API rejects invalid input and private sessions", async () => {
  await withAdminEnv(async () => {
    const bad = mockResponse();
    await adminComments(request("POST", {
      page: 1,
      pageSize: 25,
      visibility: "all",
      read: "all",
      readIds: []
    }), bad);
    assert.equal(bad.statusCode, 400);

    const personal = mockResponse();
    await adminComments({ method: "POST", headers: {}, body: {} }, personal);
    assert.equal(personal.statusCode, 401);
  });
});

test("malformed Twikoo comment records are reported as an upstream error", async () => {
  await withAdminEnv(async () => {
    globalThis.fetch = async () => jsonResponse({
      code: 0,
      count: 1,
      data: [{ ...root, _id: "bad id" }]
    });
    const res = mockResponse();
    await adminComments(request("POST", {
      page: 1,
      pageSize: 20,
      keyword: "",
      visibility: "all",
      read: "all",
      readIds: []
    }), res);
    assert.equal(res.statusCode, 502);
    assert.doesNotMatch(res.body.error, /bad id/);
  });
});
