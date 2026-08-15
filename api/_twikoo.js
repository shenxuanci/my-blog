const crypto = require('node:crypto');
const { createHttpError } = require('./_github');

const TWIKOO_ENDPOINT = 'https://twikoo.aoiblog.top';
const TWIKOO_TIMEOUT_MS = 8000;
const ADMIN_PAGE_SIZE = 100;
const MAX_SCAN_COMMENTS = 2000;
const COMMENT_ID_PATTERN = /^[A-Za-z0-9_-]{1,80}$/;

function adminAccessToken() {
  const secret = process.env.ADMIN_TOKEN;
  if (!secret) throw createHttpError(500, 'ADMIN_TOKEN is not configured');
  return crypto.createHash('md5').update(secret).digest('hex');
}

function decodeEntities(value) {
  const named = {
    amp: '&', apos: "'", gt: '>', lt: '<', nbsp: ' ', quot: '"'
  };
  return String(value || '').replace(/&(#x[0-9a-f]+|#\d+|amp|apos|gt|lt|nbsp|quot);/gi, (match, entity) => {
    if (entity[0] !== '#') return named[entity.toLowerCase()] ?? match;
    const hex = entity[1].toLowerCase() === 'x';
    const codePoint = Number.parseInt(entity.slice(hex ? 2 : 1), hex ? 16 : 10);
    if (!Number.isInteger(codePoint) || codePoint < 0 || codePoint > 0x10ffff) return match;
    try {
      return String.fromCodePoint(codePoint);
    } catch {
      return match;
    }
  });
}

function htmlToText(value) {
  const blockEnd = /<\/(?:address|article|aside|blockquote|div|dl|fieldset|figcaption|figure|footer|form|h[1-6]|header|li|main|nav|ol|p|pre|section|table|tbody|td|tfoot|th|thead|tr|ul)>/gi;
  const text = String(value || '')
    .replace(/<(?:script|style|template|noscript)\b[^>]*>[\s\S]*?<\/(?:script|style|template|noscript)\s*>/gi, '')
    .replace(/<img\b[^>]*>/gi, '\n[图片]\n')
    .replace(/<br\s*\/?\s*>/gi, '\n')
    .replace(blockEnd, '\n')
    .replace(/<[^>]*>/g, '');

  return decodeEntities(text)
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .map((line) => line.replace(/[\t\f\v ]+/g, ' ').trim())
    .filter(Boolean)
    .join('\n')
    .trim();
}

function safeUrl(value, { httpsOnly = false } = {}) {
  try {
    const parsed = new URL(String(value || ''));
    if (httpsOnly ? parsed.protocol !== 'https:' : !['http:', 'https:'].includes(parsed.protocol)) {
      return '';
    }
    if (parsed.username || parsed.password) return '';
    return parsed.href;
  } catch {
    return '';
  }
}

function assertCommentId(value) {
  const id = String(value || '');
  if (!COMMENT_ID_PATTERN.test(id)) {
    throw createHttpError(400, 'Invalid comment id');
  }
  return id;
}

function upstreamCommentId(value) {
  const id = String(value || '');
  if (!COMMENT_ID_PATTERN.test(id)) {
    throw createHttpError(502, 'Twikoo returned an invalid comment record');
  }
  return id;
}

function normalizeComment(comment) {
  const id = upstreamCommentId(comment?._id);
  const rootId = comment?.rid ? upstreamCommentId(comment.rid) : id;
  const parentId = comment?.pid ? upstreamCommentId(comment.pid) : '';
  const created = Number(comment?.created);
  return {
    id,
    rootId,
    parentId,
    kind: comment?.rid ? 'reply' : 'root',
    nick: String(comment?.nick || '匿名').slice(0, 100),
    avatarUrl: safeUrl(comment?.avatar, { httpsOnly: true }),
    websiteUrl: safeUrl(comment?.link),
    text: htmlToText(comment?.comment).slice(0, 20000),
    path: String(comment?.url || '').slice(0, 500),
    created: Number.isFinite(created) && !Number.isNaN(new Date(created).getTime()) ? created : 0,
    hidden: comment?.isSpam === true,
    pinned: !comment?.rid && comment?.top === true
  };
}

function visibilityType(visibility) {
  if (visibility === 'visible') return 'VISIBLE';
  if (visibility === 'hidden') return 'HIDDEN';
  return '';
}

async function callTwikoo(event, data = {}, { timeoutMs = TWIKOO_TIMEOUT_MS } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Math.max(1, timeoutMs));
  let response;
  try {
    response = await fetch(TWIKOO_ENDPOINT, {
      method: 'POST',
      redirect: 'error',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...data,
        event,
        accessToken: adminAccessToken(),
        envId: TWIKOO_ENDPOINT
      }),
      signal: controller.signal
    });
    if (!response.ok) throw createHttpError(502, 'Twikoo returned an invalid response');
    let result;
    try {
      result = JSON.parse(await response.text());
    } catch (error) {
      if (error?.name === 'AbortError') throw error;
      throw createHttpError(502, 'Twikoo returned an invalid response');
    }
    if (!result || typeof result !== 'object' || Array.isArray(result)
      || !Number.isSafeInteger(result.code)) {
      throw createHttpError(502, 'Twikoo returned an invalid response');
    }
    if (result.code !== 0) {
      const message = String(result.message || '');
      if (/登录|login|password|密码/i.test(message)) {
        throw createHttpError(503, 'Twikoo admin is not initialized or ADMIN_TOKEN does not match');
      }
      throw createHttpError(502, 'Twikoo rejected the request');
    }
    return result;
  } catch (error) {
    if (error?.status) throw error;
    throw createHttpError(503, error?.name === 'AbortError'
      ? 'Twikoo request timed out'
      : 'Twikoo is unavailable');
  } finally {
    clearTimeout(timer);
  }
}

async function fetchAdminPage({ page, per, visibility = 'all', timeoutMs } = {}) {
  const result = await callTwikoo('COMMENT_GET_FOR_ADMIN', {
    page,
    per,
    type: visibilityType(visibility)
  }, { timeoutMs });
  if (!Number.isSafeInteger(result.count) || result.count < 0 || !Array.isArray(result.data)
    || result.data.length > per) {
    throw createHttpError(502, 'Twikoo returned an invalid comment list');
  }
  return { count: result.count, data: result.data };
}

async function fetchAllAdminComments({ visibility = 'all' } = {}) {
  const deadline = Date.now() + TWIKOO_TIMEOUT_MS;
  const first = await fetchAdminPage({
    page: 1,
    per: ADMIN_PAGE_SIZE,
    visibility,
    timeoutMs: deadline - Date.now()
  });
  if (first.count > MAX_SCAN_COMMENTS) {
    throw createHttpError(422, 'Too many comments for this operation; use normal pagination');
  }
  const comments = [];
  const ids = new Set();
  const appendPage = (result, expectedLength) => {
    if (result.count !== first.count || result.data.length !== expectedLength) {
      throw createHttpError(502, 'Twikoo comment list changed during the operation');
    }
    for (const item of result.data) {
      const id = normalizeComment(item).id;
      if (ids.has(id)) throw createHttpError(502, 'Twikoo returned a duplicate comment record');
      ids.add(id);
      comments.push(item);
    }
  };
  appendPage(first, Math.min(ADMIN_PAGE_SIZE, first.count));
  const pages = Math.ceil(first.count / ADMIN_PAGE_SIZE);
  for (let page = 2; page <= pages; page += 1) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw createHttpError(503, 'Twikoo request timed out');
    const next = await fetchAdminPage({
      page,
      per: ADMIN_PAGE_SIZE,
      visibility,
      timeoutMs: remaining
    });
    appendPage(next, Math.min(ADMIN_PAGE_SIZE, first.count - ((page - 1) * ADMIN_PAGE_SIZE)));
  }
  if (comments.length !== first.count) {
    throw createHttpError(502, 'Twikoo returned an incomplete comment list');
  }
  return comments.slice(0, first.count);
}

module.exports = {
  TWIKOO_ENDPOINT,
  TWIKOO_TIMEOUT_MS,
  MAX_SCAN_COMMENTS,
  COMMENT_ID_PATTERN,
  assertCommentId,
  htmlToText,
  normalizeComment,
  callTwikoo,
  fetchAdminPage,
  fetchAllAdminComments
};
