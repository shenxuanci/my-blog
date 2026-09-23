import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const frontMatterCases = JSON.parse(await readFile(
  new URL("./fixtures/markdown-front-matter-cases.json", import.meta.url),
  "utf8",
));
let editorTools = null;
try {
  editorTools = require("../source/admin/editor-tools.js");
} catch {
  // The first TDD run deliberately proves the helper does not exist yet.
}

test("Word clipboard text becomes blank-line-separated Markdown paragraphs", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const result = editorTools.wordPasteReplacement({
    html: '<html xmlns:o="urn:schemas-microsoft-com:office:office"><p class="MsoNormal">第一段</p><p class="MsoNormal">第二段</p></html>',
    text: "第一段\r\n第二段\r\n\r\n第三段",
    value: "开头\n\n结尾",
    selectionStart: 4,
    selectionEnd: 4,
  });

  assert.deepEqual(result, {
    value: "开头\n\n第一段\n\n第二段\n\n第三段结尾",
    selectionStart: 17,
    selectionEnd: 17,
  });
});

test("non-Word clipboard content is left to the browser", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.equal(editorTools.wordPasteReplacement({
    html: "<p>普通网页</p>",
    text: "普通网页",
    value: "",
    selectionStart: 0,
    selectionEnd: 0,
  }), null);
});

test("Enter creates a paragraph and replaces the current selection", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.editorEnterReplacement({
    value: "第一段待替换文字",
    selectionStart: 3,
    selectionEnd: 7,
    shiftKey: false,
  }), {
    value: "第一段\n\n字",
    selectionStart: 5,
    selectionEnd: 5,
  });
});

test("Shift+Enter writes a portable Markdown hard break", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.editorEnterReplacement({
    value: "同一段",
    selectionStart: 3,
    selectionEnd: 3,
    shiftKey: true,
  }), {
    value: "同一段  \n",
    selectionStart: 6,
    selectionEnd: 6,
  });
});

test("Shift+Enter replaces the selected text with a portable hard break", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.editorEnterReplacement({
    value: "before selected after",
    selectionStart: 6,
    selectionEnd: 16,
    shiftKey: true,
  }), {
    value: "before  \nafter",
    selectionStart: 9,
    selectionEnd: 9,
  });
});

test("Markdown structures keep standard single-line Enter behavior", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const cases = [
    "- 列表项",
    "> 引用",
    "| 表格 |",
    "Column A | Column B",
    "# 标题",
    "```js\nconst value = 1;",
  ];

  for (const value of cases) {
    const result = editorTools.editorEnterReplacement({
      value,
      selectionStart: value.length,
      selectionEnd: value.length,
      shiftKey: false,
    });
    assert.equal(result.value, `${value}\n`, value);
  }
});

test("Enter keeps a single line break throughout top-level Markdown structures", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const cases = [
    { value: "````markdown\n```\nstill fenced", cursor: "````markdown\n```\nstill fenced".length },
    { value: "~~~~text\n~~~\nstill fenced", cursor: "~~~~text\n~~~\nstill fenced".length },
    { value: "<section>\nraw html", cursor: "<section>\nraw html".length },
    { value: "- list item\n  continuation", cursor: "- list item\n  continuation".length },
    { value: "> quote\n> continuation", cursor: "> quote\n> continuation".length },
    { value: "Column A | Column B\n--- | ---\none | two", cursor: "Column A | Column B\n--- | ---\none | two".length },
    { value: "Setext heading\n--------------", cursor: "Setext heading\n--------------".length },
    { value: "[ref]: /target\n  continued title", cursor: "[ref]: /target\n  continued title".length },
    { value: "[^note]: first line\n  continuation", cursor: "[^note]: first line\n  continuation".length },
  ];

  for (const { value, cursor } of cases) {
    const result = editorTools.editorEnterReplacement({
      value,
      selectionStart: cursor,
      selectionEnd: cursor,
      shiftKey: false,
    });
    assert.equal(result.value, `${value}\n`, value);
  }
});

test("preview URLs reject script schemes even when control characters disguise them", () => {
  assert.ok(editorTools, "editor tools module should exist");
  for (const value of [
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    "java\tscript:alert(1)",
    "java\nscript:alert(1)",
    "data:text/html,alert(1)",
    "vbscript:msgbox(1)",
    "//evil.example/path",
  ]) {
    assert.equal(editorTools.safeMarkdownUrl(value), "#", value);
  }

  for (const value of [
    "https://example.com/path",
    "http://example.com/path",
    "/images/example.webp",
    "./relative",
    "../relative",
    "relative/path",
    "#heading",
  ]) {
    assert.equal(editorTools.safeMarkdownUrl(value), value, value);
  }
});

test("session drafts validate their shape and distinguish safe restore from conflicts", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const draft = editorTools.createSessionDraft({
    filePath: "source/_posts/example.md",
    sha: "opened-sha",
    title: "Draft title",
    date: "2026-08-01",
    category: "Essay",
    index_img: "/cover.webp",
    content: "Draft body",
  }, true, 1234);

  assert.equal(editorTools.parseSessionDraft(JSON.stringify(draft)).content, "Draft body");
  assert.equal(editorTools.parseSessionDraft("not json"), null);
  assert.equal(editorTools.parseSessionDraft(JSON.stringify({ version: 999 })), null);
  assert.equal(editorTools.draftRestoreState(draft, {
    filePath: "source/_posts/example.md",
    sha: "opened-sha",
  }), "restore");
  assert.equal(editorTools.draftRestoreState(draft, {
    filePath: "source/_posts/example.md",
    sha: "new-sha",
  }), "conflict");
  assert.match(editorTools.draftDiscardMessage(draft), /图片|上传/);
});

test("Markdown import normalizes BOM and CRLF before reading front matter and a leading H1", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.markdownImportReplacement({
    source: '\uFEFF---\r\ntitle: "Front matter title"\r\n---\r\n\r\n# Imported title\r\nFirst paragraph\r\nSecond paragraph\r\n',
    title: "",
    value: "unchanged",
  }), {
    title: "Imported title",
    value: "First paragraph\n\nSecond paragraph",
  });
});

test("Markdown import keeps the leading H1 when the title box already has a value", () => {
  assert.ok(editorTools, "editor tools module should exist");
  // 旧实现把 H1 从正文删掉又丢弃导入的标题，那一行会彻底消失。
  const result = editorTools.markdownImportReplacement({
    source: "---\ntitle: old\n---\n\n# Kept heading\nFirst paragraph\n",
    title: "Existing title",
    value: "unchanged",
  });
  assert.equal(result.title, "Existing title");
  assert.match(result.value, /^# Kept heading/);
  assert.match(result.value, /First paragraph/);
});

test("Markdown import does not treat --- delimited prose as front matter", () => {
  assert.ok(editorTools, "editor tools module should exist");
  // 旧的非贪婪正则会把两行 --- 之间的正文整段吃掉。
  const result = editorTools.markdownImportReplacement({
    source: "---\n\nFirst paragraph\n\n---\n\nSecond paragraph\n",
    title: "",
    value: "unchanged",
  });
  assert.equal(result.title, "");
  assert.match(result.value, /First paragraph/);
  assert.match(result.value, /Second paragraph/);
});

test("Markdown import strips only parseable article metadata", () => {
  assert.ok(editorTools, "editor tools module should exist");
  for (const fixture of frontMatterCases) {
    const result = editorTools.markdownImportReplacement({
      source: fixture.source,
      title: "Existing title",
    });
    assert.equal(result.value, fixture.expectedBody, fixture.name);
  }
});

test("Markdown import changes only top-level prose soft breaks", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const source = [
    "First prose line",
    "Second prose line",
    "Hard break with spaces  ",
    "same paragraph after spaces",
    "Hard break with slash\\",
    "same paragraph after slash",
    "Literal slash pair\\\\",
    "new paragraph after literal slashes",
    "",
    "Setext heading",
    "--------------",
    "",
    "- list item",
    "  continuation",
    "  - nested item",
    "",
    "> quote line",
    "> quote continuation",
    "",
    "Column A | Column B",
    "-------- | --------",
    "one | two",
    "",
    "| Left | Right |",
    "| --- | --- |",
    "| a | b |",
    "",
    "```js",
    "const value = 1;",
    "```",
    "",
    "    indented code",
    "",
    "<section>",
    "raw html",
    "</section>",
    "",
    "[ref]: https://example.com",
    "[^note]: footnote definition",
    "",
    "![image](/images/example.webp)",
  ].join("\n");

  const result = editorTools.markdownImportReplacement({
    source,
    title: "Existing title",
    value: "unchanged",
  });

  assert.equal(result.title, "Existing title");
  assert.match(result.value, /^First prose line\n\nSecond prose line/);
  assert.match(result.value, /Hard break with spaces  \nsame paragraph after spaces/);
  assert.match(result.value, /Hard break with slash\\\nsame paragraph after slash/);
  assert.match(result.value, /Literal slash pair\\\\\n\nnew paragraph after literal slashes/);
  for (const structure of [
    "Setext heading\n--------------",
    "- list item\n  continuation\n  - nested item",
    "> quote line\n> quote continuation",
    "Column A | Column B\n-------- | --------\none | two",
    "| Left | Right |\n| --- | --- |\n| a | b |",
    "```js\nconst value = 1;\n```",
    "    indented code",
    "<section>\nraw html\n</section>",
    "[ref]: https://example.com",
    "[^note]: footnote definition",
    "![image](/images/example.webp)",
  ]) {
    assert.ok(result.value.includes(structure), structure);
  }
});

test("Markdown import preserves existing blank lines", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const result = editorTools.markdownImportReplacement({
    source: "First paragraph\n\nSecond paragraph\n\n\nThird paragraph",
    title: "",
    value: "unchanged",
  });
  assert.equal(result.value, "First paragraph\n\nSecond paragraph\n\n\nThird paragraph");
});

test("Markdown import never mistakes a multiline reference definition for prose", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const source = [
    '[reference]: /target "Repeated',
    'prose"',
    "",
    "Repeated",
    "prose",
  ].join("\n");
  const result = editorTools.markdownImportReplacement({ source, title: "", value: "unchanged" });
  assert.equal(result.value, [
    '[reference]: /target "Repeated',
    'prose"',
    "",
    "Repeated",
    "",
    "prose",
  ].join("\n"));
});

test("Markdown import preserves definition-like text inside fenced code", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const source = [
    "```markdown",
    "[reference]: /target",
    "```",
  ].join("\n");
  assert.equal(
    editorTools.markdownImportReplacement({ source, title: "", value: "unchanged" }).value,
    source,
  );
});

test("Markdown import keeps definition-like lines that belong to a prose paragraph", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const source = [
    "Intro",
    "[reference]: /target",
    "Continuation",
  ].join("\n");
  assert.equal(
    editorTools.markdownImportReplacement({ source, title: "", value: "unchanged" }).value,
    ["Intro", "", "[reference]: /target", "", "Continuation"].join("\n"),
  );
});

test("Markdown import failure leaves the current editor state available to the caller", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.throws(
    () => editorTools.markdownImportReplacement({
      source: "Replacement",
      title: "Current title",
      value: "Current body",
      lexer: () => { throw new Error("parser failed"); },
    }),
    /parser failed/,
  );
});

test("admin loads the vendored Markdown and YAML parsers before editor tools", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  const markedIndex = html.indexOf('<script src="/admin/marked.min.js"></script>');
  const yamlIndex = html.indexOf('<script src="/admin/js-yaml.min.js"></script>');
  const toolsIndex = html.indexOf('<script src="/admin/editor-tools.js"></script>');
  assert.ok(markedIndex >= 0);
  assert.ok(yamlIndex > markedIndex);
  assert.ok(toolsIndex > yamlIndex);
  const markedSource = await readFile(new URL("../source/admin/marked.min.js", import.meta.url), "utf8");
  const yamlSource = await readFile(new URL("../source/admin/js-yaml.min.js", import.meta.url), "utf8");
  assert.match(markedSource, /marked/i);
  assert.match(yamlSource, /jsyaml/i);
});

test("admin wires session-only draft recovery, dirty guards, and the shared URL validator", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  assert.match(html, /sessionStorage\.setItem\(DRAFT_KEY/);
  assert.match(html, /sessionStorage\.removeItem\(DRAFT_KEY/);
  assert.doesNotMatch(html, /localStorage\.setItem\([^)]*draft/i);
  assert.match(html, /addEventListener\(['"]beforeunload['"]/);
  assert.match(html, /draftRestoreState/);
  assert.match(html, /response\.status === 401/);
  assert.match(html, /settingsBaseline/);
  assert.match(html, /editorTools\.safeMarkdownUrl/);
});

test("vendored parsers and editor tools work together through browser globals", async () => {
  const context = vm.createContext({});
  const markedSource = await readFile(new URL("../source/admin/marked.min.js", import.meta.url), "utf8");
  const yamlSource = await readFile(new URL("../source/admin/js-yaml.min.js", import.meta.url), "utf8");
  const toolsSource = await readFile(new URL("../source/admin/editor-tools.js", import.meta.url), "utf8");
  vm.runInContext(markedSource, context);
  vm.runInContext(yamlSource, context);
  vm.runInContext(toolsSource, context);
  const result = context.AoiAdminEditorTools.markdownImportReplacement({
    source: "First line\nSecond line",
    title: "",
    value: "unchanged",
  });
  assert.equal(result.value, "First line\n\nSecond line");
  for (const fixture of frontMatterCases) {
    const imported = context.AoiAdminEditorTools.markdownImportReplacement({source: fixture.source, title: 'Existing'});
    assert.equal(imported.value, fixture.expectedBody, fixture.name);
  }
});

test('cover maintenance preserves body examples and literal dollar characters with BOM/CRLF', async () => {
  const { mkdtemp, mkdir, writeFile, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const { execFileSync } = await import('node:child_process');
  const directory = await mkdtemp(join(tmpdir(), 'blog-cover-test-'));
  try {
    await mkdir(join(directory, 'source/_posts'), {recursive: true});
    await mkdir(join(directory, 'source/_data'), {recursive: true});
    const cover = "/images/$&-$'-$$.webp";
    await writeFile(join(directory, 'source/_data/category-covers.json'), JSON.stringify({default: cover}));
    const body = '```yaml\r\nindex_img: "example"old_id: demo\r\n```\r\n';
    const source = '\uFEFF---\r\ntitle: "$& example"\r\n\r\n---\r\n' + body;
    const postPath = join(directory, 'source/_posts/test.md');
    await writeFile(postPath, source);
    const script = fileURLToPath(new URL('../tools/apply-category-covers.mjs', import.meta.url));
    execFileSync(process.execPath, [script], {cwd: directory});
    const saved = await readFile(postPath, 'utf8');
    assert.ok(saved.startsWith('\uFEFF---\r\n'));
    assert.ok(saved.endsWith(body));
    assert.ok(saved.includes('index_img: ' + JSON.stringify(cover)));
    assert.doesNotMatch(saved, /(?<!\r)\n/);
    execFileSync(process.execPath, [script], {cwd: directory});
    assert.equal(await readFile(postPath, 'utf8'), saved);
  } finally {
    await rm(directory, {recursive: true, force: true});
  }
});

test("admin default cover ignores inherited object keys", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  const match = html.match(/^    function defaultCover\(category\) \{[\s\S]*?^    \}/m);
  assert.ok(match, "defaultCover should be present in the admin script");
  const context = vm.createContext({ state: { coverMap: { default: "/fallback.webp", Essay: "/essay.webp" } } });
  vm.runInContext(match[0], context);
  for (const category of ["toString", "constructor", "valueOf", "__proto__"]) {
    assert.equal(context.defaultCover(category), "/fallback.webp", category);
  }
  assert.equal(context.defaultCover("Essay"), "/essay.webp");
});

test("admin preview does not confuse prose with its code-block placeholder", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  const match = html.match(/^    function renderMarkdown\(markdown\) \{[\s\S]*?^    \}/m);
  assert.ok(match);
  const context = vm.createContext({
    escapeHtml: (value) => String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;"),
    safeMarkdownUrl: (value) => value,
  });
  vm.runInContext(match[0], context);
  const preview = context.renderMarkdown("@@CODE_BLOCK_0@@\n\n```js\nconst value = 1;\n```");
  assert.match(preview, /<p>@@CODE_BLOCK_0@@<\/p>/);
  assert.match(preview, /<pre><code>js\nconst value = 1;<\/code><\/pre>/);
  assert.ok(preview.indexOf("@@CODE_BLOCK_0@@") < preview.indexOf("<pre>"));
});

test("admin lists oversized posts as disabled without opening an editor", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  const match = html.match(/^    function renderArticles\(\) \{[\s\S]*?^    \}/m);
  assert.ok(match, "renderArticles should be present in the admin script");
  const list = { innerHTML: "" };
  const listeners = [];
  const context = vm.createContext({
    state: { articles: [
      { filePath: "source/_posts/large.md", title: "large.md", editable: false },
      { filePath: "source/_posts/invalid.md", title: "invalid.md", editable: false, unavailableReason: "Front Matter 无效，需在本地修复" },
      { filePath: "source/_posts/small.md", title: "Small", date: "2026-01-01", category: "Essay" },
    ] },
    $: () => list,
    escapeHtml: (value) => String(value),
    document: { querySelectorAll: (selector) => {
      assert.equal(selector, ".article-item:not(:disabled)");
      return [{ dataset: { path: "source/_posts/small.md" }, addEventListener: (_, callback) => listeners.push(callback) }];
    } },
    editPost: (path) => { context.opened = path; },
  });
  vm.runInContext(match[0], context);
  context.renderArticles();
  assert.match(list.innerHTML, /data-path="source\/_posts\/large\.md" disabled/);
  assert.match(list.innerHTML, /文章超过 1 MiB，需在本地编辑/);
  assert.match(list.innerHTML, /Front Matter 无效，需在本地修复/);
  assert.doesNotMatch(list.innerHTML, /data-path="source\/_posts\/small\.md" disabled/);
  assert.equal(listeners.length, 1);
  listeners[0]();
  assert.equal(context.opened, "source/_posts/small.md");
});

test("cover maintenance reads inline YAML categories and never writes inherited values", async () => {
  const { mkdtemp, mkdir, writeFile, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const { execFileSync } = await import('node:child_process');
  const directory = await mkdtemp(join(tmpdir(), 'blog-cover-categories-'));
  try {
    await mkdir(join(directory, 'source/_posts'), {recursive: true});
    await mkdir(join(directory, 'source/_data'), {recursive: true});
    await writeFile(join(directory, 'source/_data/category-covers.json'), JSON.stringify({
      default: '/fallback.webp', Essay: '/essay.webp'
    }));
    const inlinePath = join(directory, 'source/_posts/inline.md');
    const inheritedPath = join(directory, 'source/_posts/inherited.md');
    await writeFile(inlinePath, '---\ntitle: Inline\ncategories: [Essay, Notes]\n---\nBody\n');
    await writeFile(inheritedPath, '---\ntitle: Inherited\ncategories:\n  - toString\n---\nBody\n');
    const script = fileURLToPath(new URL('../tools/apply-category-covers.mjs', import.meta.url));
    execFileSync(process.execPath, [script], {cwd: directory});
    assert.match(await readFile(inlinePath, 'utf8'), /index_img: "\/essay\.webp"/);
    const inherited = await readFile(inheritedPath, 'utf8');
    assert.match(inherited, /index_img: "\/fallback\.webp"/);
    assert.doesNotMatch(inherited, /native code/);
  } finally {
    await rm(directory, {recursive: true, force: true});
  }
});

test("cover maintenance leaves a post untouched when its YAML cannot be parsed", async () => {
  const { mkdtemp, mkdir, writeFile, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const { execFileSync } = await import('node:child_process');
  const directory = await mkdtemp(join(tmpdir(), 'blog-cover-invalid-'));
  try {
    await mkdir(join(directory, 'source/_posts'), {recursive: true});
    await mkdir(join(directory, 'source/_data'), {recursive: true});
    await writeFile(join(directory, 'source/_data/category-covers.json'), JSON.stringify({default: '/fallback.webp'}));
    const postPath = join(directory, 'source/_posts/invalid.md');
    const source = '---\ntitle: [unclosed\ncategories: Essay\n---\nBody\n';
    await writeFile(postPath, source);
    const script = fileURLToPath(new URL('../tools/apply-category-covers.mjs', import.meta.url));
    assert.throws(() => execFileSync(process.execPath, [script], {cwd: directory, stdio: 'ignore'}));
    assert.equal(await readFile(postPath, 'utf8'), source);
  } finally {
    await rm(directory, {recursive: true, force: true});
  }
});

test("browser editor reports a missing Markdown parser instead of changing content", async () => {
  const context = vm.createContext({});
  const toolsSource = await readFile(new URL("../source/admin/editor-tools.js", import.meta.url), "utf8");
  vm.runInContext(toolsSource, context);
  assert.throws(
    () => context.AoiAdminEditorTools.markdownImportReplacement({
      source: "Replacement",
      title: "Current title",
      value: "Current body",
    }),
    /parser is unavailable/,
  );
});

// `overflow: hidden` 上的 sticky 是静默失效：不报错、不告警，底栏只是不再跟随视口。
// 这组断言锁住 clip 与 sticky 的配对，以免将来有人为别的目的把 .workspace 改回 hidden。
test("admin keeps the action bar sticky and its scroll ancestor clipped, not hidden", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  // 先剥掉注释再断言：这两条规则的注释本身就在解释 hidden 为何不行，
  // 连注释一起扫会让「改注释措辞」误触发失败。
  const rule = (selector) => {
    const match = html.match(new RegExp(`\\${selector}\\s*\\{[^}]*\\}`));
    assert.ok(match, `${selector} rule should exist`);
    return match[0].replace(/\/\*[\s\S]*?\*\//g, "");
  };

  const workspaceRule = rule(".workspace");
  assert.match(workspaceRule, /overflow:\s*clip/);
  assert.doesNotMatch(workspaceRule, /overflow:\s*hidden/);

  const actionsRule = rule(".form-actions");
  assert.match(actionsRule, /position:\s*sticky/);
  assert.match(actionsRule, /bottom:\s*0/);
  // 半透明底栏会让正文从按钮下透出来，背景必须是实心的 surface token。
  assert.match(actionsRule, /background:\s*var\(--surface\)/);
});

// 长报错（GitHub 超时那种上百字符的）曾把底栏撑到视口 24% 高、按钮换行三排。
// 状态位必须独占整行且限高，按钮行高度才与消息长度无关。
test("admin keeps status text from competing with the action buttons for row space", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  const statusRule = html.match(/\.form-actions \.status\s*\{[^}]*\}/);
  assert.ok(statusRule, ".form-actions .status rule should exist");
  const body = statusRule[0].replace(/\/\*[\s\S]*?\*\//g, "");
  // flex-basis 100% => 独占整行，不与按钮抢空间；flex-grow 必须是 0。
  assert.match(body, /flex:\s*1\s+0\s+100%/);
  assert.match(body, /max-height:/);
  assert.match(body, /overflow:\s*hidden/);
  // 空消息时不该占掉垂直空间。
  assert.match(html, /\.form-actions \.status:empty\s*\{\s*display:\s*none/);
});

test("admin mirrors status text into the sticky bars so feedback stays on screen", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  assert.match(html, /id="editorStatus"/);
  assert.match(html, /id="settingsStatus"/);
  // 默认调用必须同时写顶部与两个镜像；显式传 target 的登录提示保持原行为。
  assert.match(html, /for \(const id of \['status', 'editorStatus', 'settingsStatus'\]\)/);
  assert.match(html, /setStatus\([^)]*\$\('loginStatus'\)\)/);
});

test("admin separates the destructive action from the primary one in the action bar", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  const actions = html.match(/<div class="form-actions">[\s\S]*?<\/div>\s*<\/form>/);
  assert.ok(actions, "editor form actions should exist");
  const saveIndex = actions[0].indexOf('id="saveBtn"');
  const statusIndex = actions[0].indexOf('id="editorStatus"');
  const deleteIndex = actions[0].indexOf('id="deleteBtn"');
  assert.ok(saveIndex >= 0 && statusIndex > saveIndex && deleteIndex > statusIndex);
  assert.match(actions[0], /id="deleteBtn" class="danger hidden"/);
  // 两组按钮 + space-between 才有把「发布」和「删除」推到两端的物理距离；
  // 少了任一半，两个按钮会挨在一起，防误点就没了。
  assert.equal((actions[0].match(/class="inline-actions"/g) || []).length, 2);
  const actionsRule = html.match(/\.form-actions\s*\{[^}]*\}/)[0];
  assert.match(actionsRule, /justify-content:\s*space-between/);
});
