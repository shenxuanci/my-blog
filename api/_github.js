const crypto = require('crypto');
const { pinyin } = require('pinyin-pro');
const {
  clearLoginAttempts,
  recordFailedLogin,
  retryAfterSeconds
} = require('./_loginGuard');

const POSTS_DIR = 'source/_posts';
const COVER_MAP_PATH = 'source/_data/category-covers.json';
const FALLBACK_COVER = '/images/covers/defaults/fallback.webp';
const ADMIN_SESSION_COOKIE = 'aoiblog_admin_session';
const ADMIN_SESSION_TTL_MS = 8 * 60 * 60 * 1000;
// personal：只读写日报个人状态；admin：还可发文章、改设置、传图。
// 目前只有 /admin/ 的登录会签发会话，因此签发的都是 admin；personal 留给
// 将来可能出现的「只登日报」入口，也让权限判定在代码里是显式的。
const ADMIN_SESSION_SCOPES = new Set(['personal', 'admin']);
const DEFAULT_JSON_BODY_BYTES = 1024 * 1024;

function setCors(res) {
  // 管理接口仅允许同源调用；不返回 Allow-Origin，避免第三方站点探测认证状态。
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,POST,DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  // 这些接口会返回后台文章、站点设置或个人状态。即使 Vercel 当前默认不缓存
  // Serverless 响应，也要把浏览器和未来代理的行为钉死，避免认证响应落入缓存。
  res.setHeader('Cache-Control', 'no-store');
}

function sendJson(res, status, body) {
  return res.status(status).json(body);
}

function createHttpError(status, message) {
  const error = new Error(message);
  error.status = status;
  return error;
}

// 统一的错误出口：把 429 附带的 Retry-After 真正写进响应头，
// 否则限流对客户端只是一个没有退避提示的 429。
function sendError(res, error, fallbackStatus = 500) {
  if (error?.retryAfter) res.setHeader('Retry-After', String(error.retryAfter));
  return sendJson(res, error?.status || fallbackStatus, {
    success: false,
    error: error?.message || 'Request failed'
  });
}

function timingSafeEqual(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  return bufA.length === bufB.length && crypto.timingSafeEqual(bufA, bufB);
}

function tooManyAttempts(retryAfter) {
  const error = createHttpError(429, 'Too many failed attempts');
  error.retryAfter = retryAfter;
  return error;
}

// 缺失凭证不是猜测，不计入锁定——否则未认证的探测就能把管理员自己锁在门外。
// 只有「带了 Authorization 但值不对」才记账。
function requireAdmin(req) {
  const expected = process.env.ADMIN_TOKEN;
  if (!expected) {
    throw createHttpError(500, 'ADMIN_TOKEN is not configured');
  }

  const supplied = req.headers?.authorization || '';
  if (!supplied) {
    throw createHttpError(401, 'Unauthorized');
  }

  const retryAfter = retryAfterSeconds(req);
  if (retryAfter) throw tooManyAttempts(retryAfter);

  if (!timingSafeEqual(supplied, `Bearer ${expected}`)) {
    recordFailedLogin(req);
    throw createHttpError(401, 'Unauthorized');
  }
  clearLoginAttempts(req);
}

function createAdminSession(secret, now = Date.now(), scope = 'admin') {
  if (!ADMIN_SESSION_SCOPES.has(scope)) {
    throw new TypeError(`unknown admin session scope: ${scope}`);
  }
  const expires = now + ADMIN_SESSION_TTL_MS;
  const payload = `${expires}.${scope}`;
  const signature = crypto
    .createHmac('sha256', secret)
    .update(`admin-session:${payload}`)
    .digest('base64url');
  return `${payload}.${signature}`;
}

// 返回会话内容或 null。scope 参与签名，所以改 scope 必然签名失配；
// 旧的两段格式（expires.signature）解出的 scope 不在白名单里，一律作废——
// 会话本来就只有 8 小时寿命，重登一次即可。
function readAdminSession(value, secret, now = Date.now()) {
  const [expiresText, scope, signature, ...rest] = String(value || '').split('.');
  const expires = Number(expiresText);
  if (rest.length
    || !ADMIN_SESSION_SCOPES.has(scope)
    || !Number.isSafeInteger(expires)
    || expires <= now
    || expires > now + ADMIN_SESSION_TTL_MS) {
    return null;
  }
  const expected = crypto
    .createHmac('sha256', secret)
    .update(`admin-session:${expiresText}.${scope}`)
    .digest('base64url');
  return timingSafeEqual(signature, expected) ? { expires, scope } : null;
}

function verifyAdminSession(value, secret, now = Date.now(), requiredScope = null) {
  const session = readAdminSession(value, secret, now);
  if (!session) return false;
  return requiredScope ? session.scope === requiredScope : true;
}

function readCookie(req, name) {
  const cookie = String(req.headers?.cookie || '');
  for (const part of cookie.split(';')) {
    const [key, ...value] = part.trim().split('=');
    if (key === name) {
      try {
        return decodeURIComponent(value.join('='));
      } catch {
        return '';
      }
    }
  }
  return '';
}

function requireAdminSession(req, now = Date.now(), requiredScope = null) {
  const expected = process.env.ADMIN_TOKEN;
  if (!expected) throw createHttpError(500, 'ADMIN_TOKEN is not configured');
  if (!verifyAdminSession(readCookie(req, ADMIN_SESSION_COOKIE), expected, now, requiredScope)) {
    throw createHttpError(401, 'Unauthorized');
  }
}

function requireAdminScope(req, now = Date.now()) {
  return requireAdminSession(req, now, 'admin');
}

// 写接口的统一入口：带了 Authorization 就走受限流的 Bearer（留给脚本/CLI），
// 否则走 HttpOnly 的 admin 会话 cookie（浏览器后台用，JS 读不到、8 小时过期）。
// 后台页因此不再需要把明文主口令留在内存里。
function requireAdminWrite(req, now = Date.now()) {
  if (req.headers?.authorization) return requireAdmin(req);
  return requireAdminScope(req, now);
}

function repoConfig() {
  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER || process.env.GITHUB_REPOSITORY_OWNER;
  const repo =
    process.env.GITHUB_REPO ||
    (process.env.GITHUB_REPOSITORY || '').split('/')[1];
  const branch = process.env.GITHUB_BRANCH || 'main';

  if (!token || !owner || !repo) {
    throw createHttpError(500, 'GitHub repository environment is not configured');
  }

  return { token, owner, repo, branch };
}

function encodePath(filePath) {
  return filePath.split('/').map(encodeURIComponent).join('/');
}

async function githubRequest(filePath, options = {}) {
  const { token, owner, repo, branch } = repoConfig();
  const method = options.method || 'GET';
  const url = new URL(`https://api.github.com/repos/${owner}/${repo}/contents/${encodePath(filePath)}`);

  if (method === 'GET') {
    url.searchParams.set('ref', branch);
  }

  const response = await fetch(url, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
      'User-Agent': 'aoiblog-admin'
    },
    body: options.body ? JSON.stringify({ ...options.body, branch }) : undefined
  });

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      // GitHub 偶发 502 返回 HTML，保留原状态码而不是抛裸 SyntaxError
      data = null;
    }
  }

  if (!response.ok) {
    const message = data?.message || `GitHub request failed: ${response.status}`;
    throw createHttpError(response.status, message);
  }

  if (text && data === null) {
    throw createHttpError(502, 'GitHub returned a non-JSON response');
  }

  return data;
}

async function githubApiRequest(endpoint, options = {}) {
  const { token, owner, repo } = repoConfig();
  const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/${endpoint}`, {
    method: options.method || 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
      'User-Agent': 'aoiblog-admin'
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  });
  const text = await response.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = null; }
  }
  if (!response.ok) {
    throw createHttpError(response.status, data?.message || `GitHub request failed: ${response.status}`);
  }
  if (text && data === null) throw createHttpError(502, 'GitHub returned a non-JSON response');
  return data;
}

async function putTextFilesAtomic(files, message, options = {}) {
  if (!files.length) return null;
  const { branch } = repoConfig();
  const refPath = `git/ref/heads/${encodePath(branch)}`;
  const updateRefPath = `git/refs/heads/${encodePath(branch)}`;
  const ref = await githubApiRequest(refPath);
  const headSha = ref.object?.sha;
  const head = await githubApiRequest(`git/commits/${headSha}`);
  if (options.expectedFiles?.length) {
    const currentTree = await githubApiRequest(`git/trees/${head.tree?.sha}?recursive=1`);
    const blobs = new Map((currentTree.tree || [])
      .filter((entry) => entry.type === 'blob')
      .map((entry) => [entry.path, entry.sha]));
    const stale = options.expectedFiles.some((file) => blobs.get(file.path) !== file.sha);
    if (stale) throw createHttpError(409, 'Repository changed since settings were opened; reload before saving');
  }
  const entries = await Promise.all(files.map(async (file) => {
    const blob = await githubApiRequest('git/blobs', {
      method: 'POST',
      body: { content: file.content, encoding: 'utf-8' }
    });
    return { path: file.path, mode: '100644', type: 'blob', sha: blob.sha };
  }));
  const tree = await githubApiRequest('git/trees', {
    method: 'POST',
    body: { base_tree: head.tree?.sha, tree: entries }
  });
  const commit = await githubApiRequest('git/commits', {
    method: 'POST',
    body: { message, tree: tree.sha, parents: [headSha] }
  });
  await githubApiRequest(updateRefPath, {
    method: 'PATCH',
    body: { sha: commit.sha, force: false }
  });
  return commit;
}

function parseJsonBody(raw) {
  try {
    return raw ? JSON.parse(raw) : {};
  } catch {
    throw createHttpError(400, 'Invalid JSON body');
  }
}

function assertJsonBodySize(value, maxBytes) {
  let serialized;
  try {
    serialized = typeof value === 'string' ? value : JSON.stringify(value);
  } catch {
    throw createHttpError(400, 'Invalid JSON body');
  }
  if (Buffer.byteLength(serialized || '', 'utf8') > maxBytes) {
    throw createHttpError(413, 'JSON body too large');
  }
}

async function readJsonBody(req, maxBytes = DEFAULT_JSON_BODY_BYTES) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0) {
    throw new TypeError('maxBytes must be a positive safe integer');
  }
  if (req.body && typeof req.body === 'object') {
    assertJsonBodySize(req.body, maxBytes);
    return req.body;
  }
  if (typeof req.body === 'string') {
    assertJsonBodySize(req.body, maxBytes);
    return parseJsonBody(req.body);
  }

  const chunks = [];
  let totalBytes = 0;
  for await (const chunk of req) {
    totalBytes += Buffer.byteLength(chunk);
    if (totalBytes > maxBytes) {
      throw createHttpError(413, 'JSON body too large');
    }
    chunks.push(chunk);
  }

  const raw = Buffer.concat(chunks).toString('utf8');
  return parseJsonBody(raw);
}

async function listDirectory(dirPath) {
  const data = await githubRequest(dirPath);
  return Array.isArray(data) ? data : [];
}

async function readTextFile(filePath) {
  const data = await githubRequest(filePath);
  const content = Buffer.from(String(data.content || '').replace(/\n/g, ''), 'base64').toString('utf8');
  return { content, sha: data.sha };
}

async function putTextFile(filePath, content, message, sha) {
  return githubRequest(filePath, {
    method: 'PUT',
    body: {
      message,
      content: Buffer.from(content, 'utf8').toString('base64'),
      sha
    }
  });
}

async function putBase64File(filePath, contentBase64, message) {
  return githubRequest(filePath, {
    method: 'PUT',
    body: {
      message,
      content: contentBase64
    }
  });
}

async function deleteFile(filePath, message, sha) {
  return githubRequest(filePath, {
    method: 'DELETE',
    body: { message, sha }
  });
}

// 白名单式校验：文章一律是 source/_posts/ 下的单层 .md 文件（仓库里 21 篇
// 都是这个形状，listPosts 也只列顶层）。原先靠「前缀 + 后缀 + 不含 ..」的黑名单
// 放行了子目录、NUL 字节和 %2e%2e 这类字面量目录名——都逃不出 _posts，但黑名单
// 要靠穷举漏洞形状才成立，正则白名单直接把形状钉死。
const POST_FILE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*\.md$/;

function validatePostPath(filePath) {
  const value = String(filePath || '');
  const name = value.startsWith(`${POSTS_DIR}/`) ? value.slice(POSTS_DIR.length + 1) : '';
  if (!POST_FILE_PATTERN.test(name) || name.includes('..')) {
    throw createHttpError(400, 'Invalid post path');
  }
  return value;
}

function yamlString(value) {
  return JSON.stringify(String(value ?? ''));
}

function unquote(value) {
  const text = String(value || '').trim();
  if (text.startsWith('"') && text.endsWith('"')) {
    try {
      return JSON.parse(text);
    } catch {
      return text.slice(1, -1);
    }
  }
  if (text.startsWith("'") && text.endsWith("'")) {
    return text.slice(1, -1).replace(/''/g, "'");
  }
  return text;
}

function readScalar(frontMatter, key) {
  const match = frontMatter.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
  return match ? unquote(match[1]) : '';
}

function readList(frontMatter, key) {
  const match = frontMatter.match(new RegExp(`^${key}:\\n((?:\\s+-\\s*.+\\n?)+)`, 'm'));
  if (!match) return [];
  return match[1]
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s+-\s*/, '').trim())
    .filter(Boolean)
    .map(unquote);
}

function splitLegacyComments(content) {
  const match = content.match(/\n*<section class="legacy-comments">[\s\S]*?<\/section>\s*$/);
  return {
    editableContent: match ? content.slice(0, match.index).trimEnd() : content.trimEnd(),
    legacySuffix: match ? match[0].trim() : ''
  };
}

function parsePost(filePath, source, sha, includeContent = false) {
  const match = source.match(/^---\n([\s\S]*?)\n---\n?/);
  const frontMatter = match ? match[1] : '';
  const rawContent = match ? source.slice(match[0].length) : source;
  const { editableContent, legacySuffix } = splitLegacyComments(rawContent);
  const categories = readList(frontMatter, 'categories');

  const article = {
    filePath,
    sha,
    title: readScalar(frontMatter, 'title') || filePath.replace(/^.*\/|\.md$/g, ''),
    date: readScalar(frontMatter, 'date'),
    updated: readScalar(frontMatter, 'updated'),
    category: categories[0] || '未分类',
    categories,
    index_img: readScalar(frontMatter, 'index_img'),
    old_id: readScalar(frontMatter, 'old_id'),
    twikooPath: readScalar(frontMatter, 'twikooPath'),
    excerpt: editableContent.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim().slice(0, 160)
  };

  const permalink = readScalar(frontMatter, 'permalink');
  if (permalink) article.permalink = permalink;

  if (includeContent) {
    article.content = editableContent;
    article.legacySuffix = legacySuffix;
  }

  // The original block is server-only editing state. Keeping it non-enumerable
  // prevents it from changing the public API response while allowing precise edits.
  Object.defineProperty(article, '_frontMatter', {
    value: frontMatter,
    enumerable: false,
    configurable: false,
    writable: false
  });

  return article;
}

function normalizeDate(value) {
  const text = String(value || '').trim();
  if (!text) return today();
  // 接受纯日期或带时间的日期（原样保留，日期变了 permalink 就变了）
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(text);
  if (match) {
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const hour = Number(match[4] || 0);
    const minute = Number(match[5] || 0);
    const second = Number(match[6] || 0);
    const parsed = new Date(0);
    parsed.setUTCHours(hour, minute, second, 0);
    parsed.setUTCFullYear(year, month - 1, day);
    if (
      hour <= 23
      && minute <= 59
      && second <= 59
      && parsed.getUTCFullYear() === year
      && parsed.getUTCMonth() === month - 1
      && parsed.getUTCDate() === day
    ) {
      return text;
    }
  }
  // 无法解析的日期直接报错，静默回退到今天会改文章 URL、断开评论关联
  throw createHttpError(400, `Invalid date: ${text}`);
}

function today() {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
  return formatter.format(new Date());
}

function timestamp() {
  const formatter = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
  return formatter
    .formatToParts(new Date())
    .filter((part) => part.type !== 'literal')
    .map((part) => part.value)
    .join('');
}

function slugify(title, fallback = 'post') {
  const latin = pinyin(String(title || ''), {
    toneType: 'none',
    type: 'array',
    nonZh: 'consecutive'
  }).join(' ');

  const slug = latin
    .toLowerCase()
    .replace(/['"]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-');

  return slug || fallback;
}

function stripFrontMatter(content) {
  return String(content || '').replace(/^---\n[\s\S]*?\n---\n?/, '').trim();
}

// 封面只有两种合法形态：站内绝对路径（/images/covers/...）或外部 http(s) 图片。
// 主题用 <%= url_for(index_img) %> 输出到 <img src>，EJS 转义挡住了属性逃逸，
// 所以这里不是可利用的 XSS；但 index_img 是唯一没做协议校验的用户可控 URL，
// 而 adminSettings 与前端 safeUrl() 都校验了——补齐这处纵深防御的缺口。
function validateCoverUrl(value) {
  const text = String(value ?? '').trim();
  if (!text) return '';
  if (/[\r\n<>"']/.test(text)) {
    throw createHttpError(400, 'Cover URL must not contain line breaks or markup characters');
  }
  if (text.startsWith('//')) {
    throw createHttpError(400, 'Cover URL must be a site path or an http(s) URL');
  }
  if (text.startsWith('/')) return text;
  if (/^https?:\/\/\S+$/i.test(text)) return text;
  throw createHttpError(400, 'Cover URL must be a site path or an http(s) URL');
}

// 分类名是用户可控的（后台新建分类即可），而 coverMap 来自仓库里的 JSON。
// 两个坑都必须在这里挡住：
// ① 原型键。`coverMap[category]` 是裸对象取值，分类名叫 `toString` / `valueOf`
//    时取出的是继承来的**函数**，随后 `yamlString` 会把它写成
//    `index_img: "function toString() { [native code] }"`——文章封面直接坏掉。
//    分类名叫 `constructor` 且 JSON 里有同名键时还能绕过下面的 URL 校验。
// ② 未校验的 URL。`index_img` 走 validateCoverUrl，但 map 里的值此前只做过
//    `typeof === 'string'`，等于同一个 sink 有一条没校验的旁路。
function coverForCategory(coverMap, category, explicitCover) {
  if (explicitCover) return explicitCover;
  const map = coverMap && typeof coverMap === 'object' ? coverMap : {};
  for (const key of [category, 'default']) {
    if (!Object.hasOwn(map, key)) continue;
    const value = map[key];
    if (typeof value !== 'string') continue;
    try {
      const safe = validateCoverUrl(value);
      if (safe) return safe;
    } catch {
      // 仓库里的封面映射坏了不该让发文章整体失败，回退到兜底封面。
    }
  }
  return FALLBACK_COVER;
}

function postSlugFromPath(filePath) {
  return String(filePath || '')
    .replace(/^.*\//, '')
    .replace(/\.md$/, '')
    .replace(/^\d{4}-\d{2}-\d{2}-/, '');
}

function permalinkSlug(permalink, fallback) {
  const match = /^\/\d{4}\/\d{2}\/\d{2}\/([^/]+)\/$/.exec(String(permalink || ''));
  return match ? match[1] : fallback;
}

function datedPermalink(day, slug) {
  if (!slug) throw createHttpError(500, 'Cannot create a permalink without a post slug');
  return `/${day.replace(/-/g, '/')}/${slug}/`;
}

function replaceFrontMatterScalar(frontMatter, key, value) {
  const line = `${key}: ${yamlString(value)}`;
  const pattern = new RegExp(`^${key}:.*$`, 'm');
  if (pattern.test(frontMatter)) return frontMatter.replace(pattern, line);
  return `${frontMatter}${frontMatter ? '\n' : ''}${line}`;
}

function replacePrimaryCategory(frontMatter, category) {
  const list = /^categories:\s*\n((?:[ \t]+-[^\n]*(?:\n|$))*)/m;
  const match = list.exec(frontMatter);
  if (!match) return `${frontMatter}${frontMatter ? '\n' : ''}categories:\n  - ${yamlString(category)}`;
  const items = match[1];
  if (!items) {
    return frontMatter.replace(match[0], `categories:\n  - ${yamlString(category)}\n`);
  }
  const updatedItems = items.replace(/^([ \t]+-)[^\n]*/m, `$1 ${yamlString(category)}`);
  return `${frontMatter.slice(0, match.index)}categories:\n${updatedItems}${frontMatter.slice(match.index + match[0].length)}`;
}

function patchExistingFrontMatter(frontMatter, values) {
  let next = String(frontMatter || '');
  next = replaceFrontMatterScalar(next, 'title', values.title);
  next = replaceFrontMatterScalar(next, 'date', values.date);
  if (values.permalink) next = replaceFrontMatterScalar(next, 'permalink', values.permalink);
  next = replaceFrontMatterScalar(next, 'updated', values.updated);
  next = replacePrimaryCategory(next, values.category);
  next = replaceFrontMatterScalar(next, 'index_img', values.indexImg);
  return next;
}

function composePost(article, coverMap, existing, filePath = article.filePath) {
  const title = String(article.title || '').trim();
  if (!title) throw createHttpError(400, 'Title is required');

  const category = String(article.category || existing?.category || '未分类').trim() || '未分类';
  const requestedInput = String(article.date || existing?.date || '').trim();
  const requestedDate = normalizeDate(requestedInput);
  const requestedDay = requestedDate.slice(0, 10);
  const requestedHasTime = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(requestedInput);
  const existingDate = existing?.date ? normalizeDate(existing.date) : '';
  const dateChanged = Boolean(existingDate && existingDate.slice(0, 10) !== requestedDay);
  const date = existingDate && !requestedHasTime && existingDate.slice(0, 10) === requestedDay
    ? existing.date
    : requestedHasTime
      ? requestedDate
      : `${requestedDay} 00:00:00`;
  const updated = today();
  const indexImg = coverForCategory(coverMap, category, validateCoverUrl(article.index_img));
  const oldId = existing?.old_id || '';
  const twikooPath = existing?.twikooPath || '';
  const fileSlug = postSlugFromPath(filePath);
  let permalink = '';
  if (!existing) {
    permalink = datedPermalink(requestedDay, fileSlug);
  } else if (existing.permalink) {
    permalink = dateChanged
      ? datedPermalink(requestedDay, permalinkSlug(existing.permalink, fileSlug))
      : existing.permalink;
  } else if (dateChanged) {
    permalink = datedPermalink(requestedDay, fileSlug);
  }
  let body = stripFrontMatter(article.content);

  if (existing?.legacySuffix && !body.includes('legacy-comments')) {
    body = `${body}\n\n${existing.legacySuffix}`;
  }

  let frontMatter;
  if (existing && Object.hasOwn(existing, '_frontMatter')) {
    frontMatter = patchExistingFrontMatter(existing._frontMatter, {
      title,
      date,
      permalink,
      updated,
      category,
      indexImg
    });
  } else {
    const lines = [
      `title: ${yamlString(title)}`,
      `date: ${yamlString(date)}`,
      ...(permalink ? [`permalink: ${yamlString(permalink)}`] : []),
      `updated: ${yamlString(updated)}`,
      'categories:',
      `  - ${yamlString(category)}`,
      `index_img: ${yamlString(indexImg)}`
    ];
    if (oldId) lines.push(`old_id: ${yamlString(oldId)}`);
    if (twikooPath) lines.push(`twikooPath: ${yamlString(twikooPath)}`);
    frontMatter = lines.join('\n');
  }

  return {
    content: `---\n${frontMatter}\n---\n${body.trim()}\n`,
    date,
    category,
    indexImg,
    title
  };
}

async function readCoverMap() {
  try {
    const { content } = await readTextFile(COVER_MAP_PATH);
    let parsed;
    try {
      parsed = JSON.parse(content);
    } catch {
      throw createHttpError(502, 'Category cover map contains invalid JSON');
    }
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object'
      || Object.values(parsed).some((value) => typeof value !== 'string')) {
      throw createHttpError(502, 'Category cover map must be an object of string paths');
    }
    return parsed;
  } catch (error) {
    if (error?.status === 404) return { default: FALLBACK_COVER };
    throw error;
  }
}

module.exports = {
  POSTS_DIR,
  setCors,
  sendJson,
  sendError,
  createHttpError,
  requireAdmin,
  requireAdminSession,
  requireAdminScope,
  requireAdminWrite,
  createAdminSession,
  verifyAdminSession,
  readAdminSession,
  ADMIN_SESSION_COOKIE,
  readJsonBody,
  listDirectory,
  readTextFile,
  putTextFile,
  putBase64File,
  putTextFilesAtomic,
  deleteFile,
  validatePostPath,
  validateCoverUrl,
  parsePost,
  composePost,
  readCoverMap,
  slugify,
  timestamp,
  normalizeDate
};
