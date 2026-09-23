const {
  setCors,
  sendJson,
  sendError,
  createHttpError,
  requireAdminWrite,
  readJsonBody,
  readTextFile,
  putTextFilesAtomic
} = require('./_github');

const SITE_CONFIG = '_config.yml';
const FLUID_CONFIG = '_config.fluid.yml';
const NAV_KEYS = ['home', 'archive', 'category', 'about', 'links', 'guestbook'];
// 导航项写在 YAML 流式映射里（`- { key: "home", name: "首页" }`），读回来靠的是
// `"([^"]*)"`。值里出现引号时第一次保存写成 \" 仍然合法，第二次保存正则会在
// 反斜杠处截断，替换出 `name: "新值"旧尾"` —— YAML 解析失败，站点直接构建不出来。
// 所以在入口就挡掉引号和反斜杠，而不是去写一个能处理转义的正则。
const NAV_VALUE_MAX = 40;
const TEXT_VALUE_MAX = 200;

function yamlString(value) {
  return JSON.stringify(String(value ?? ''));
}

function escapeHtmlText(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function decodeHtmlText(value) {
  return String(value ?? '')
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, '>')
    .replace(/&lt;/g, '<')
    .replace(/&amp;/g, '&');
}

function yamlInlineHtml(value) {
  return yamlString(`<span>${escapeHtmlText(String(value ?? '').trim())}</span>`);
}

function unquote(value) {
  const text = String(value || '').trim();
  if (text.startsWith('"') && text.endsWith('"')) {
    try {
      return JSON.parse(text);
    } catch {
      // Fall through for legacy YAML values that are not valid JSON strings.
    }
  }
  return text.replace(/^['"]|['"]$/g, '');
}

// 返回块体在原文里的绝对区间，读写共用同一份定位：
// 只有这样 setFooter / setAboutScalar 才能保证改的是 footer: / about: 底下那一个
// key，而不是碰巧第一个同缩进的同名 key。
function topLevelBlockRange(source, blockName) {
  const startMatch = new RegExp(`^${blockName}:\\n`, 'm').exec(source);
  if (!startMatch) return null;

  const start = startMatch.index + startMatch[0].length;
  const rest = source.slice(start);
  const nextBlock = rest.search(/^\S/m);
  return { start, end: nextBlock === -1 ? source.length : start + nextBlock };
}

function readTopLevelBlock(source, blockName) {
  const range = topLevelBlockRange(source, blockName);
  return range ? source.slice(range.start, range.end) : '';
}

function replaceInBlock(source, blockName, pattern, replacer, missingMessage) {
  const range = topLevelBlockRange(source, blockName);
  const block = range ? source.slice(range.start, range.end) : '';
  if (!range || !pattern.test(block)) {
    throw createHttpError(400, missingMessage);
  }
  return source.slice(0, range.start)
    + block.replace(pattern, replacer)
    + source.slice(range.end);
}

function assertPlainValue(label, value, maxLength, { allowQuotes = true } = {}) {
  const text = String(value ?? '');
  if (/[\r\n]/.test(text)) {
    throw createHttpError(400, `${label} must not contain line breaks`);
  }
  if (!allowQuotes && /[\u0000-\u001f\u007f]/.test(text)) {
    throw createHttpError(400, `${label} must not contain control characters`);
  }
  if (!allowQuotes && /["\\]/.test(text)) {
    throw createHttpError(400, `${label} must not contain quotes or backslashes`);
  }
  if (text.length > maxLength) {
    throw createHttpError(400, `${label} must be at most ${maxLength} characters`);
  }
  return text;
}

function readScalar(source, key) {
  const match = source.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
  return match ? unquote(match[1]) : '';
}

function readNestedScalar(source, blockName, key) {
  const block = readTopLevelBlock(source, blockName);
  const match = block.match(new RegExp(`^\\s+${key}:\\s*(.+)$`, 'm'));
  return match ? unquote(match[1]) : '';
}

function readSlogan(source) {
  const match = source.match(/^index:\n[\s\S]*?^\s{2}slogan:\n[\s\S]*?^\s{4}text:\s*(.+)$/m);
  return match ? unquote(match[1]) : '';
}

function readFooter(source) {
  const raw = readNestedScalar(source, 'footer', 'content');
  const htmlMatch = raw.match(/^<span>([\s\S]*)<\/span>$/);
  return decodeHtmlText(htmlMatch ? htmlMatch[1] : raw);
}

function readNav(source) {
  const nav = {};
  for (const key of NAV_KEYS) {
    const pattern = new RegExp(`\\{ key: "${key}", name: "([^"]*)"`);
    nav[key] = source.match(pattern)?.[1] || '';
  }
  return nav;
}

function setRootScalar(source, key, value) {
  const line = `${key}: ${yamlString(value)}`;
  const pattern = new RegExp(`^${key}:\\s*.*$`, 'm');
  if (!pattern.test(source)) {
    throw createHttpError(400, `Missing config key: ${key}`);
  }
  return source.replace(pattern, () => line);
}

function setAboutScalar(source, key, value) {
  return replaceInBlock(
    source,
    'about',
    new RegExp(`^(\\s{2}${key}:\\s*).*$`, 'm'),
    (_, prefix) => prefix + yamlString(value),
    `Missing about key: ${key}`
  );
}

function setSlogan(source, value) {
  const pattern = /^(index:\n[\s\S]*?^\s{2}slogan:\n[\s\S]*?^\s{4}text:\s*).*$/m;
  if (!pattern.test(source)) {
    throw createHttpError(400, 'Missing index slogan text');
  }
  return source.replace(pattern, (_, prefix) => prefix + yamlString(value));
}

function setFooter(source, value) {
  return replaceInBlock(
    source,
    'footer',
    /^(\s{2}content:\s*).*$/m,
    (_, prefix) => prefix + yamlInlineHtml(value),
    'Missing footer content'
  );
}

function setNav(source, nav) {
  let next = source;
  for (const key of NAV_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(nav || {}, key)) continue;
    const pattern = new RegExp(`(- \\{ key: "${key}", name: )"[^"]*"`);
    if (!pattern.test(next)) {
      throw createHttpError(400, `Missing nav item: ${key}`);
    }
    next = next.replace(pattern, (_, prefix) => prefix + yamlString(nav[key]));
  }
  return next;
}

function extractSettings(siteConfig, fluidConfig) {
  return {
    title: readScalar(siteConfig, 'title'),
    subtitle: readScalar(siteConfig, 'subtitle'),
    slogan: readSlogan(fluidConfig),
    footerText: readFooter(fluidConfig),
    aboutName: readNestedScalar(fluidConfig, 'about', 'name'),
    aboutIntro: readNestedScalar(fluidConfig, 'about', 'intro'),
    nav: readNav(fluidConfig)
  };
}

// 整行替换 + JSON.parse 反解的字段 round-trip 安全，只需挡换行与超长；
// nav 走的是流式映射里的 "…" 片段，必须连引号和反斜杠一起挡。
const TEXT_FIELDS = [
  ['title', '站点标题'],
  ['subtitle', '站点副标题'],
  ['slogan', '首页标语'],
  ['footerText', '页脚文字'],
  ['aboutName', '关于页名字'],
  ['aboutIntro', '关于页简介']
];

function validateSettings(settings) {
  const safe = settings || {};
  for (const [key, label] of TEXT_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(safe, key)) {
      assertPlainValue(label, safe[key], TEXT_VALUE_MAX);
    }
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'nav')) {
    const nav = safe.nav;
    if (!nav || typeof nav !== 'object' || Array.isArray(nav)) {
      throw createHttpError(400, 'nav must be an object');
    }
    for (const key of NAV_KEYS) {
      if (!Object.prototype.hasOwnProperty.call(nav, key)) continue;
      assertPlainValue(`导航项 ${key}`, nav[key], NAV_VALUE_MAX, { allowQuotes: false });
    }
  }
  return safe;
}

function applySettings(siteConfig, fluidConfig, settings) {
  const safe = validateSettings(settings);
  let nextSite = siteConfig;
  let nextFluid = fluidConfig;

  if (Object.prototype.hasOwnProperty.call(safe, 'title')) {
    nextSite = setRootScalar(nextSite, 'title', safe.title);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'subtitle')) {
    nextSite = setRootScalar(nextSite, 'subtitle', safe.subtitle);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'slogan')) {
    nextFluid = setSlogan(nextFluid, safe.slogan);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'footerText')) {
    nextFluid = setFooter(nextFluid, safe.footerText);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'aboutName')) {
    nextFluid = setAboutScalar(nextFluid, 'name', safe.aboutName);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'aboutIntro')) {
    nextFluid = setAboutScalar(nextFluid, 'intro', safe.aboutIntro);
  }
  if (Object.prototype.hasOwnProperty.call(safe, 'nav')) {
    nextFluid = setNav(nextFluid, safe.nav);
  }

  return { siteConfig: nextSite, fluidConfig: nextFluid };
}

async function handler(req, res) {
  setCors(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    requireAdminWrite(req);

    const siteFile = await readTextFile(SITE_CONFIG);
    const fluidFile = await readTextFile(FLUID_CONFIG);

    if (req.method === 'GET') {
      return sendJson(res, 200, {
        success: true,
        data: extractSettings(siteFile.content, fluidFile.content)
      });
    }

    if (req.method === 'POST') {
      const body = await readJsonBody(req);
      const next = applySettings(siteFile.content, fluidFile.content, body.settings || {});

      const files = [];
      if (next.siteConfig !== siteFile.content) files.push({ path: SITE_CONFIG, content: next.siteConfig });
      if (next.fluidConfig !== fluidFile.content) files.push({ path: FLUID_CONFIG, content: next.fluidConfig });
      await putTextFilesAtomic(files, 'update site settings', {
        expectedFiles: [
          { path: SITE_CONFIG, sha: siteFile.sha },
          { path: FLUID_CONFIG, sha: fluidFile.sha }
        ]
      });

      return sendJson(res, 200, {
        success: true,
        data: extractSettings(next.siteConfig, next.fluidConfig)
      });
    }

    return sendJson(res, 405, { success: false, error: 'Method not allowed' });
  } catch (error) {
    return sendError(res, error);
  }
}

handler._test = {
  extractSettings,
  applySettings,
  validateSettings,
  NAV_KEYS,
  NAV_VALUE_MAX,
  TEXT_VALUE_MAX
};

module.exports = handler;
