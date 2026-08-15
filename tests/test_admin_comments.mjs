import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const tools = require("../source/admin/comment-tools.js");

test("comment read state recovers from corruption and toggles one item", () => {
  assert.deepEqual(tools.parseReadState("broken"), { version: 1, items: {} });
  assert.deepEqual(tools.parseReadState('{"version":2,"items":{}}'), { version: 1, items: {} });

  const read = tools.markRead({ version: 1, items: {} }, "comment_1", 1234);
  assert.equal(read.items.comment_1, 1234);
  assert.deepEqual(tools.readIds(read), ["comment_1"]);
  const unread = tools.markUnread(read, "comment_1");
  assert.deepEqual(unread, { version: 1, items: {} });
  assert.equal(read.items.comment_1, 1234, "helpers must not mutate caller state");
});

test("comment read state keeps the newest 5000 entries", () => {
  const items = {};
  for (let index = 0; index < 5001; index += 1) items[`comment_${index}`] = index + 1;
  const state = tools.parseReadState(JSON.stringify({ version: 1, items }));
  assert.equal(Object.keys(state.items).length, 5000);
  assert.equal(Object.hasOwn(state.items, "comment_0"), false);
  assert.equal(state.items.comment_5000, 5001);
});

test("comment paths map through legacy Twikoo paths, permalinks, and the guestbook", () => {
  const articles = [
    {
      filePath: "source/_posts/2026-03-20-old-post.md",
      date: "2026-03-20 00:00:00",
      title: "Old post",
      twikooPath: "article_legacy"
    },
    {
      filePath: "source/_posts/2026-08-01-new-post.md",
      date: "2026-08-01 00:00:00",
      title: "New post",
      permalink: "/2026/08/01/new-post/"
    }
  ];
  const index = tools.buildArticleIndex(articles);

  assert.deepEqual(tools.resolveCommentTarget({ id: "abc_1", path: "article_legacy" }, index), {
    label: "Old post",
    url: "/2026/03/20/old-post/#abc_1"
  });
  assert.deepEqual(tools.resolveCommentTarget({ id: "abc_2", path: "/2026/08/01/new-post/" }, index), {
    label: "New post",
    url: "/2026/08/01/new-post/#abc_2"
  });
  assert.deepEqual(tools.resolveCommentTarget({ id: "abc_3", path: "/" }, index), {
    label: "留言板",
    url: "/guestbook/#abc_3"
  });
  assert.deepEqual(tools.resolveCommentTarget({ id: "abc_4", path: "unknown" }, index), {
    label: "unknown",
    url: ""
  });
});

test("comment pagination clamps to the last available page", () => {
  assert.equal(tools.commentPageForTotal(3, 20, 39), 2);
  assert.equal(tools.commentPageForTotal(2, 20, 0), 1);
  assert.equal(tools.commentPageForTotal(1, 20, 100), 1);
});

test("admin comment UI is lazy, uses safe DOM rendering, and loads its helper", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  assert.match(html, /id="commentsViewBtn"[^>]*>评论管理</);
  assert.match(html, /id="commentsView"[^>]*class="[^\"]*hidden/);
  assert.match(html, /<script src="\/admin\/comment-tools\.js"><\/script>/);
  assert.match(html, /function renderComments\(\)/);
  assert.match(html, /commentText\.textContent\s*=\s*comment\.text/);
  assert.doesNotMatch(html, /comment(?:Text|Content)\.innerHTML\s*=/);
  assert.match(html, /referrerPolicy\s*=\s*'no-referrer'/);
  assert.match(html, /link\.rel\s*=\s*'noopener noreferrer'/);
  const viewOriginalHandler = /link\.addEventListener\('click', \(\) => \{([\s\S]*?)\n\s{10}\}\);/.exec(html)?.[1] || "";
  assert.match(viewOriginalHandler, /state\.comments\.read === 'unread'/);
  assert.match(viewOriginalHandler, /loadComments\(\)/);
  assert.match(html, /async function showCommentsView\(\)[\s\S]*loadComments/);
  assert.match(html, /requestId:\s*0/);
  assert.match(html, /const requestId = \+\+state\.comments\.requestId/);
  assert.match(html, /requestId !== state\.comments\.requestId/);
  assert.match(html, /commentTools\.commentPageForTotal/);
});
