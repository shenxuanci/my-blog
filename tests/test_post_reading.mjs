import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ejs from "ejs";
import { marked } from "marked";
import { JSDOM } from "jsdom";

const scriptSource = await readFile(
  new URL("../source/js/aoiblog-home.js", import.meta.url),
  "utf8",
);
const postCssSource = await readFile(
  new URL("../source/css/aoiblog-post.css", import.meta.url),
  "utf8",
);
const homeCssSource = await readFile(
  new URL("../source/css/aoiblog-home.css", import.meta.url),
  "utf8",
);
const highlightToggleSource = await readFile(
  new URL("../scripts/highlight-dark-toggle.js", import.meta.url),
  "utf8",
);
const vercelConfig = JSON.parse(await readFile(
  new URL("../vercel.json", import.meta.url),
  "utf8",
));
const legacyArticlesHtml = await readFile(
  new URL("../source/articles.html", import.meta.url),
  "utf8",
);
const twikooPathScript = await readFile(
  new URL("../scripts/twikoo-path.js", import.meta.url),
  "utf8",
);

function createPostDom(body, { desktop = false, height = 500 } = {}) {
  const dom = new JSDOM(
    `<!doctype html><html><body>${body}</body></html>`,
    {
      runScripts: "outside-only",
      url: "https://aoiblog.top/2026/07/23/example/",
    },
  );
  const { window } = dom;

  Object.defineProperty(window, "innerHeight", {
    configurable: true,
    value: height,
  });
  Object.defineProperty(window, "scrollY", {
    configurable: true,
    writable: true,
    value: 0,
  });

  window.matchMedia = (query) => ({
    matches: query.includes("min-width") ? desktop : !desktop,
    media: query,
    addEventListener() {},
    removeEventListener() {},
  });
  window.requestAnimationFrame = (callback) => {
    callback();
    return 1;
  };
  window.cancelAnimationFrame = () => {};

  const article = window.document.querySelector(".post-content");
  if (article) {
    article.getBoundingClientRect = () => ({
      top: 50 - window.scrollY,
      bottom: 1550 - window.scrollY,
      left: 0,
      right: 720,
      width: 720,
      height: 1500,
      x: 0,
      y: 50 - window.scrollY,
      toJSON() {},
    });
  }
  const markdown = window.document.querySelector(".markdown-body");
  if (markdown) {
    markdown.getBoundingClientRect = () => ({
      top: 100 - window.scrollY,
      bottom: 1200 - window.scrollY,
      left: 0,
      right: 720,
      width: 720,
      height: 1100,
      x: 0,
      y: 100 - window.scrollY,
      toJSON() {},
    });
  }

  return dom;
}

function runReadingScript(dom) {
  dom.window.eval(scriptSource);
}

function waitForDomWork(window) {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

test("updates article progress and desktop reading state from scroll position", () => {
  const dom = createPostDom(
    `
      <div class="side-col"></div>
      <article class="post-content"><div class="markdown-body"><p>正文</p></div></article>
      <div class="side-col"></div>
    `,
    { desktop: true },
  );
  const { window } = dom;

  runReadingScript(dom);
  window.scrollY = 400;
  window.dispatchEvent(new window.Event("scroll"));

  const progress = window.document.querySelector(".aoi-reading-progress__bar");
  assert.ok(progress, "文章页应创建阅读进度线");
  assert.equal(progress.style.transform, "scaleX(0.5)");
  assert.equal(window.document.body.classList.contains("aoi-reading-active"), true);

  dom.window.close();
});

test("does not initialize article reading UI on a date-like non-post page", () => {
  const dom = createPostDom(`
    <main class="page-content"><h1>Not found</h1></main>
  `);
  const { document } = dom.window;

  runReadingScript(dom);

  assert.equal(document.body.hasAttribute("data-aoi-post-reading"), false);
  assert.equal(document.body.classList.contains("aoiblog-post"), false);
  assert.equal(document.querySelector(".aoiblog-paper-texture"), null);
  assert.equal(document.querySelector(".aoi-reading-progress"), null);

  dom.window.close();
});

test("remeasures reading progress when article content height changes", () => {
  const dom = createPostDom(
    `<article class="post-content"><div class="markdown-body"><p>正文</p></div></article>`,
  );
  const { window } = dom;
  const observers = [];
  window.ResizeObserver = class {
    constructor(callback) {
      this.callback = callback;
      observers.push(this);
    }

    observe(target) {
      this.target = target;
    }
  };

  runReadingScript(dom);
  window.scrollY = 400;
  window.dispatchEvent(new window.Event("scroll"));
  assert.equal(
    window.document.querySelector(".aoi-reading-progress__bar").style.transform,
    "scaleX(0.5)",
  );
  assert.equal(observers.length, 1);

  const markdown = window.document.querySelector(".markdown-body");
  markdown.getBoundingClientRect = () => ({
    top: 100 - window.scrollY,
    bottom: 1800 - window.scrollY,
    left: 0,
    right: 720,
    width: 720,
    height: 1700,
    x: 0,
    y: 100 - window.scrollY,
    toJSON() {},
  });
  observers[0].callback([{ target: markdown }]);

  assert.equal(
    window.document.querySelector(".aoi-reading-progress__bar").style.transform,
    "scaleX(0.25)",
  );

  dom.window.close();
});

test("mobile TOC is idempotent and restores focus when Escape closes it", async () => {
  const dom = createPostDom(`
    <button id="before">打开前焦点</button>
    <article class="post-content">
      <div class="markdown-body"><h2 id="section">章节</h2></div>
    </article>
    <aside><div id="toc-body"><a class="tocbot-link" href="#section">章节</a></div></aside>
  `);
  const { window } = dom;
  const triggerBeforeOpen = window.document.getElementById("before");
  triggerBeforeOpen.focus();

  runReadingScript(dom);
  runReadingScript(dom);
  await waitForDomWork(window);

  assert.equal(window.document.querySelectorAll("#aoi-toc-btn").length, 1);
  assert.equal(window.document.querySelectorAll("#aoi-toc-panel").length, 1);

  const button = window.document.getElementById("aoi-toc-btn");
  button.focus();
  button.click();
  assert.equal(window.document.body.classList.contains("aoi-toc-open"), true);
  assert.equal(window.document.activeElement.id, "aoi-toc-close");

  window.document.dispatchEvent(
    new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
  );
  assert.equal(window.document.body.classList.contains("aoi-toc-open"), false);
  assert.equal(window.document.activeElement, button);

  dom.window.close();
});

test("closed mobile TOC is inert and becomes inert again after closing", async () => {
  const dom = createPostDom(`
    <article class="post-content">
      <div class="markdown-body"><h2 id="section">章节</h2></div>
    </article>
    <aside><div id="toc-body"><a class="tocbot-link" href="#section">章节</a></div></aside>
  `);
  const { window } = dom;

  runReadingScript(dom);
  await waitForDomWork(window);

  const panel = window.document.getElementById("aoi-toc-panel");
  const button = window.document.getElementById("aoi-toc-btn");
  assert.equal(panel.hasAttribute("inert"), true);

  button.click();
  assert.equal(panel.hasAttribute("inert"), false);

  window.document.dispatchEvent(
    new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
  );
  assert.equal(panel.hasAttribute("inert"), true);

  dom.window.close();
});

test("open mobile TOC traps keyboard focus inside the dialog", async () => {
  const dom = createPostDom(`
    <article class="post-content">
      <div class="markdown-body"><h2 id="section">章节</h2></div>
    </article>
    <aside><div id="toc-body"><a class="tocbot-link" href="#section">章节</a></div></aside>
  `);
  const { window } = dom;

  runReadingScript(dom);
  await waitForDomWork(window);

  window.document.getElementById("aoi-toc-btn").click();
  const closeButton = window.document.getElementById("aoi-toc-close");
  const lastLink = window.document.querySelector("#aoi-toc-panel .tocbot-link");
  lastLink.focus();
  lastLink.dispatchEvent(
    new window.KeyboardEvent("keydown", {
      key: "Tab",
      bubbles: true,
      cancelable: true,
    }),
  );

  assert.equal(window.document.activeElement, closeButton);

  dom.window.close();
});

test("code wrapping toggles per block without changing copied code", () => {
  const dom = createPostDom(`
    <article class="post-content">
      <div class="markdown-body">
        <pre><code>const longLine = "unchanged";</code></pre>
        <figure class="highlight python"><table><tbody><tr><td><pre><span class="line">print("unchanged")</span></pre></td></tr></tbody></table></figure>
      </div>
    </article>
  `);
  const { window } = dom;

  runReadingScript(dom);

  const toggles = window.document.querySelectorAll(".aoi-code-wrap-toggle");
  const blocks = window.document.querySelectorAll(".aoi-code-block");
  assert.equal(toggles.length, 2);
  assert.equal(blocks.length, 2);

  const originalCode = blocks[0].textContent;
  toggles[0].click();
  assert.equal(blocks[0].classList.contains("is-code-wrapped"), true);
  assert.equal(toggles[0].getAttribute("aria-pressed"), "true");
  assert.equal(blocks[1].classList.contains("is-code-wrapped"), false);
  assert.equal(blocks[0].textContent, originalCode);

  dom.window.close();
});

test("wraps content tables but leaves syntax-highlight tables untouched", () => {
  const dom = createPostDom(`
    <article class="post-content">
      <div class="markdown-body">
        <table id="content-table"><tbody><tr><td>内容</td></tr></tbody></table>
        <figure class="highlight"><table id="code-table"><tbody><tr><td>代码</td></tr></tbody></table></figure>
      </div>
    </article>
  `);
  const { window } = dom;

  runReadingScript(dom);

  const contentTable = window.document.getElementById("content-table");
  const codeTable = window.document.getElementById("code-table");
  assert.equal(contentTable.parentElement.classList.contains("aoi-table-scroll"), true);
  assert.equal(contentTable.parentElement.tabIndex, 0);
  assert.equal(codeTable.parentElement.classList.contains("aoi-table-scroll"), false);

  dom.window.close();
});

test("highlight wrapping changes code whitespace without changing figure table layout", () => {
  const dom = new JSDOM(`
    <!doctype html>
    <html>
      <head><style>${postCssSource}</style></head>
      <body>
        <article class="post-content">
          <figure class="highlight aoi-code-block is-code-wrapped">
            <table><tbody><tr>
              <td class="gutter"><pre>1</pre></td>
              <td class="code"><pre>long code</pre></td>
            </tr></tbody></table>
          </figure>
        </article>
      </body>
    </html>
  `);
  const { window } = dom;
  const figure = window.document.querySelector("figure");
  const table = window.document.querySelector("table");
  const gutterPre = window.document.querySelector(".gutter pre");
  const codeCell = window.document.querySelector(".code");
  const codePre = window.document.querySelector(".code pre");

  assert.notEqual(window.getComputedStyle(figure).whiteSpace, "pre-wrap");
  assert.notEqual(window.getComputedStyle(table).tableLayout, "fixed");
  assert.notEqual(window.getComputedStyle(gutterPre).whiteSpace, "pre-wrap");
  assert.equal(window.getComputedStyle(codeCell).verticalAlign, "top");
  assert.equal(window.getComputedStyle(codePre).whiteSpace, "pre-wrap");

  dom.window.close();
});

test("indents only top-level text paragraphs in article content", () => {
  const dom = new JSDOM(`
    <!doctype html>
    <html>
      <head><style>${postCssSource}</style></head>
      <body>
        <article class="post-content">
          <div class="markdown-body">
            <p id="text-paragraph">正文段落</p>
            <p id="image-paragraph"><img src="/images/example.png" alt="示例"></p>
            <blockquote><p id="quote-paragraph">引用段落</p></blockquote>
          </div>
        </article>
      </body>
    </html>
  `);
  const { window } = dom;

  assert.equal(
    window.getComputedStyle(window.document.getElementById("text-paragraph")).textIndent,
    "2em",
  );
  assert.notEqual(
    window.getComputedStyle(window.document.getElementById("image-paragraph")).textIndent,
    "2em",
  );
  assert.notEqual(
    window.getComputedStyle(window.document.getElementById("quote-paragraph")).textIndent,
    "2em",
  );

  dom.window.close();
});

test("homepage article titles override Fluid truncation and remain fully visible", () => {
  const dom = new JSDOM(`
    <!doctype html>
    <html>
      <head>
        <style>
          .index-header {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
          }
        </style>
        <style>${homeCssSource}</style>
      </head>
      <body>
        <main id="board">
          <h2 class="index-header">
            <a>2026年的这个夏天，我究竟在如何理解这个世界？</a>
          </h2>
        </main>
      </body>
    </html>
  `);
  const title = dom.window.document.querySelector(".index-header");
  const style = dom.window.getComputedStyle(title);

  assert.equal(style.whiteSpace, "normal");
  assert.equal(style.overflow, "visible");
  assert.equal(style.textOverflow, "clip");
  assert.equal(style.getPropertyValue("-webkit-line-clamp"), "none");

  dom.window.close();
});

test("the deleted essay URL permanently redirects to the current essay URL", () => {
  const redirect = vercelConfig.redirects?.find((entry) => (
    entry.source === "/2026/07/31/2026-nian-de-zhe-ge-xia-tian-wo-jiu-jing-zai-ru-he-li-jie-zhe-ge-shi-jie/"
  ));
  assert.deepEqual(redirect, {
    source: "/2026/07/31/2026-nian-de-zhe-ge-xia-tian-wo-jiu-jing-zai-ru-he-li-jie-zhe-ge-shi-jie/",
    destination: "/2026/07/31/2026-nian-xia-tian-de-wo-jiu-jing-zai-ru-he-li-jie-zhe-ge-shi-jie/",
    permanent: true,
  });
});

test("legacy article redirect falls back when the URL hash is malformed", () => {
  const script = /<script>([\s\S]*?)<\/script>/.exec(legacyArticlesHtml)?.[1];
  assert.ok(script);
  let target = "";
  const context = vm.createContext({
    decodeURIComponent,
    window: {
      location: {
        hash: "#%E0%A4%A",
        replace(value) { target = value; },
      },
    },
  });
  assert.doesNotThrow(() => vm.runInContext(script, context));
  assert.equal(target, "/archives/");
});

function createHighlightDom(themeCss) {
  return new JSDOM(`
    <!doctype html>
    <html>
      <head>
        <style>${themeCss}</style>
        <!-- 主题的两条关键规则，缺了它们这个夹具复现不出真实的错位 -->
        <style>
          .markdown-body pre { font-size: 85% !important; }
          .markdown-body .highlight pre, .markdown-body pre { padding: 1.45rem 1rem; }
          figure.highlight td.gutter pre { padding: 0 .75rem; }
        </style>
        <style>${postCssSource}</style>
      </head>
      <body>
        <article class="post-content">
          <div class="markdown-body">
            <p><code id="inline-code">inline</code></p>
            <figure class="highlight py"><table><tbody><tr>
              <td class="gutter"><pre><span class="line">1</span></pre></td>
              <td class="code"><pre><code id="block-code" class="hljs py">x</code></pre></td>
            </tr></tbody></table></figure>
          </div>
        </article>
      </body>
    </html>
  `);
}

// 行号列与代码列是两个各自独立的 <pre>，字号、行高、垂直内边距任一只改一侧就会错位。
test("line number column stays aligned with the code column", () => {
  const dom = createHighlightDom("");
  const { window, window: { document } } = dom;
  const gutterPre = window.getComputedStyle(document.querySelector("td.gutter pre"));
  const codePre = window.getComputedStyle(document.querySelector("td.code pre"));
  const codeInner = window.getComputedStyle(document.querySelector("td.code pre code"));

  // 代码侧多一层 <code>：它不能自带独立的相对字号，否则会在主题的 85% 之上再乘一次
  // （浏览器实测 13.6px vs 12.24px，36 行累积错开近一整行）。两侧字号必须一致。
  assert.equal(codeInner.fontSize, gutterPre.fontSize);
  assert.doesNotMatch(codeInner.fontSize, /^0?\.\d+em$/);
  // 行高两侧同值，且必须带单位——unitless 会各自乘以本侧字号
  assert.equal(gutterPre.lineHeight, codeInner.lineHeight);
  assert.match(gutterPre.lineHeight, /(rem|px)$/);
  // 主题把行号侧的垂直内边距重置成 0，必须补回与代码侧相同的值
  assert.equal(gutterPre.paddingTop, codePre.paddingTop);
  assert.equal(gutterPre.paddingBottom, codePre.paddingBottom);
  // 左右内边距保持主题原值，不动行号与代码之间的分隔线间距
  assert.equal(gutterPre.paddingLeft, "0.75rem");

  dom.window.close();
});


// 行内代码的强调色不能渗进代码块：它不随代码块背景走，暗色下会糊成一片。
test("code blocks take their foreground from the highlight theme, not the inline code accent", () => {
  const themeCss = ".hljs { color: #ddd; background: #303030 }";
  const dom = createHighlightDom(themeCss);
  const { window } = dom;
  const block = window.getComputedStyle(window.document.getElementById("block-code"));
  const inline = window.getComputedStyle(window.document.getElementById("inline-code"));

  assert.equal(block.color, "rgb(221, 221, 221)");
  assert.notEqual(block.color, inline.color);
  // 行内代码保留自己的胶囊样式
  assert.equal(inline.color, "var(--aoi-accent-strong)");
  assert.equal(inline.padding, "0.1em 0.4em");
  // 代码块不继承胶囊的内边距和背景
  assert.equal(block.padding, "0px");
  assert.equal(block.backgroundColor, "rgba(0, 0, 0, 0)");

  dom.window.close();
});

// 把行内代码的作用域收窄到 `:not(pre) > code` 时容易漏掉两类情况，都实际回归过。
test("narrowing the inline code selector keeps every code shape styled correctly", () => {
  const dom = new JSDOM(`
    <!doctype html>
    <html>
      <head>
        <style>.markdown-body pre { font-size: 85% !important; }</style>
        <style>${postCssSource}</style>
      </head>
      <body>
        <article class="post-content">
          <div class="markdown-body">
            <p><code id="in-para">p</code></p>
            <code id="bare">直接挂在 markdown-body 下的行内代码</code>
            <pre><code id="plain-block" class="hljs">不带行号的代码块</code></pre>
            <figure class="highlight"><table><tbody><tr>
              <td class="gutter"><pre><span class="line">1</span></pre></td>
              <td class="code"><pre><code id="fig-block" class="hljs">带行号的代码块</code></pre></td>
            </tr></tbody></table></figure>
          </div>
        </article>
      </body>
    </html>
  `);
  const { window, window: { document } } = dom;
  const styleOf = (id) => window.getComputedStyle(document.getElementById(id));

  // 行内代码都要有胶囊，包括没有包裹元素、直接挂在 markdown-body 下的那种
  for (const id of ["in-para", "bare"]) {
    assert.equal(styleOf(id).padding, "0.1em 0.4em", `${id} 应保留行内胶囊`);
    assert.equal(styleOf(id).color, "var(--aoi-accent-strong)");
  }
  // 代码块都不要胶囊
  for (const id of ["plain-block", "fig-block"]) {
    assert.equal(styleOf(id).padding, "0px", `${id} 不应有胶囊内边距`);
    assert.equal(styleOf(id).backgroundColor, "rgba(0, 0, 0, 0)");
  }

  dom.window.close();
});

// 字号这条只能查 CSS 文本：jsdom 不做 em 的逐层相乘，正是当初 0.9em 叠在主题
// 85% 之上（13.6px vs 12.24px）能躲过 DOM 断言、只在浏览器里暴露的原因。
test("no code block rule stacks a relative font size on top of the theme's 85%", () => {
  // 先去注释再切规则：否则注释里的花括号和文字会混进 selector，失败信息没法看
  const stripped = postCssSource.replace(/\/\*[\s\S]*?\*\//g, "");
  const blocks = [...stripped.matchAll(/([^{}]+)\{([^}]*)\}/g)]
    .map(([, selector, body]) => ({
      selector: selector.replace(/\s+/g, " ").trim(),
      body,
    }))
    // 只看落在代码块 <pre>/<code> 上的规则，行内代码的 0.92em 与本约束无关
    .filter(({ selector }) => /\bpre\b/.test(selector) && !/:not\(pre\)/.test(selector));

  assert.ok(blocks.length > 0, "应能解析出针对代码块的规则");

  for (const { selector, body } of blocks) {
    const fontSize = /font-size:\s*([^;]+)/.exec(body);
    if (!fontSize) continue;
    const value = fontSize[1].trim();
    assert.doesNotMatch(
      value,
      /^\d*\.?\d+(em|%)$/,
      `「${selector}」用了相对字号 ${value}：主题的 .markdown-body pre 已有 `
      + "font-size: 85% !important，再叠一层会让行号列和代码列错位",
    );
  }
});




// Fluid 的模板不给暗色高亮表输出 disabled，而 color-schema.js 的切换逻辑假定它有；
// 两张表同时生效时后加载的暗色表会压住亮色表。
test("the dark highlight stylesheet ships disabled so the runtime toggle stays correct", () => {
  const applyFilter = (html) => {
    let output;
    const hexoStub = {
      extend: { filter: { register: (_event, fn) => { output = fn; } } },
    };
    const run = new Function("hexo", `${highlightToggleSource}\nreturn true;`);
    run(hexoStub);
    return output(html);
  };

  const html = [
    '<link id="highlight-css" rel="stylesheet" href="/css/highlight.css" />',
    '<link id="highlight-css-dark" rel="stylesheet" href="/css/highlight-dark.css" />',
  ].join("\n");
  const once = applyFilter(html);

  assert.match(once, /id="highlight-css-dark"[^>]*\sdisabled/);
  // 亮色表不能被误伤
  assert.doesNotMatch(once, /id="highlight-css"[^>]*\sdisabled/);
  // 幂等：主题将来自己补上也不会重复插入
  assert.equal(applyFilter(once), once);
  assert.equal((once.match(/disabled/g) || []).length, 1);
  // 只加 " disabled" 这 9 个字符，不动页面其它任何内容
  assert.equal(once.length - html.length, " disabled".length);

  // 属性值里含 `>` 时宁可不改，也不能把 disabled 插进属性值中间写坏 HTML
  const tricky = '<link id="highlight-css-dark" data-x="a>b" href="/d.css" />';
  assert.doesNotMatch(applyFilter(tricky), /="[^"]*\sdisabled[^"]*"/);
  // id 只是前缀的 link 不能命中
  assert.equal(
    applyFilter('<link id="highlight-css-dark-extra" href="/x.css" />'),
    '<link id="highlight-css-dark-extra" href="/x.css" />',
  );
  // 已带 disabled 的各种写法都不再重复插入
  for (const tag of [
    '<link id="highlight-css-dark" href="/d.css" disabled />',
    '<link id="highlight-css-dark" disabled="" href="/d.css" />',
    '<link disabled id="highlight-css-dark" href="/d.css" />',
  ]) {
    assert.equal(applyFilter(tag), tag);
  }
});

test("Twikoo path serialization keeps front matter from breaking the inline script", () => {
  const templateMatch = twikooPathScript.match(
    /const TWIKOO_VIEW = `([\s\S]*?)`;\s*\n\s*hexo\.extend/,
  );
  assert.ok(templateMatch, "Twikoo injection template should remain discoverable");

  const hostilePath = "line-one\nline-two'\\</script>";
  const html = ejs.render(templateMatch[1], {
    is_post: () => true,
    is_page: () => false,
    page: { comments: true, path: "fallback/", twikooPath: hostilePath },
    theme: {
      post: { comments: { enable: true } },
      static_prefix: { twikoo: "https://cdn.example/" },
      twikoo: { envId: "test-env", lang: "zh-CN" },
    },
    url_for: (value) => `/${value}`,
    url_join: (base, file) => `${base}${file}`,
  });
  const dom = new JSDOM(html);
  const inlineScript = dom.window.document.querySelector("script")?.textContent;
  assert.ok(inlineScript, "Twikoo inline script should be rendered");

  let receivedPath;
  vm.runInNewContext(inlineScript, {
    Fluid: {
      plugins: { fancyBox() {}, imageCaption() {} },
      utils: {
        createScript: (_url, callback) => callback(),
        listenDOMLoaded: (callback) => callback(),
        loadComments: (_selector, callback) => callback(),
      },
    },
    twikoo: { init: ({ path }) => { receivedPath = path; } },
  });
  assert.equal(receivedPath, hostilePath);
  dom.window.close();
});


