const {
  setCors,
  sendJson,
  sendError,
  createHttpError,
  requireAdminWrite,
  readJsonBody
} = require('./_github');
const {
  COMMENT_ID_PATTERN,
  assertCommentId,
  normalizeComment,
  callTwikoo,
  fetchAdminPage,
  fetchAllAdminComments
} = require('./_twikoo');

const PAGE_SIZES = new Set([10, 20, 50]);
const VISIBILITIES = new Set(['all', 'visible', 'hidden']);
const READ_FILTERS = new Set(['all', 'unread']);
const ACTIONS = Object.freeze({
  hide: { isSpam: true },
  show: { isSpam: false },
  pin: { top: true },
  unpin: { top: false }
});
const MAX_READ_IDS = 5000;

function integer(value, label, { min = 1, max = Number.MAX_SAFE_INTEGER } = {}) {
  if (!Number.isSafeInteger(value) || value < min || value > max) {
    throw createHttpError(400, `${label} is invalid`);
  }
  return value;
}

function validateListRequest(body) {
  const page = integer(body?.page, 'page');
  const pageSize = integer(body?.pageSize, 'pageSize');
  if (!PAGE_SIZES.has(pageSize)) throw createHttpError(400, 'pageSize is invalid');
  const keyword = String(body?.keyword || '').trim();
  if (keyword.length > 100) throw createHttpError(400, 'keyword is too long');
  const visibility = String(body?.visibility || 'all');
  if (!VISIBILITIES.has(visibility)) throw createHttpError(400, 'visibility is invalid');
  const read = String(body?.read || 'all');
  if (!READ_FILTERS.has(read)) throw createHttpError(400, 'read is invalid');
  const readIds = body?.readIds === undefined ? [] : body.readIds;
  if (!Array.isArray(readIds) || readIds.length > MAX_READ_IDS) {
    throw createHttpError(400, 'readIds is invalid');
  }
  if (read === 'all' && readIds.length) {
    throw createHttpError(400, 'readIds is only allowed for unread filtering');
  }
  const uniqueReadIds = [];
  const seen = new Set();
  for (const value of readIds) {
    const id = String(value || '');
    if (!COMMENT_ID_PATTERN.test(id)) throw createHttpError(400, 'readIds is invalid');
    if (!seen.has(id)) {
      seen.add(id);
      uniqueReadIds.push(id);
    }
  }
  return { page, pageSize, keyword, visibility, read, readIds: uniqueReadIds };
}

function publicSearchText(comment) {
  return [comment.nick, comment.text, comment.websiteUrl, comment.path]
    .join('\n')
    .toLocaleLowerCase();
}

async function listComments(input) {
  const needsScan = Boolean(input.keyword) || input.read === 'unread';
  if (!needsScan) {
    const result = await fetchAdminPage({
      page: input.page,
      per: input.pageSize,
      visibility: input.visibility
    });
    return {
      items: result.data.map(normalizeComment),
      page: input.page,
      pageSize: input.pageSize,
      total: result.count
    };
  }

  const readIds = new Set(input.readIds);
  const keyword = input.keyword.toLocaleLowerCase();
  const comments = (await fetchAllAdminComments({ visibility: input.visibility }))
    .map(normalizeComment)
    .filter((comment) => !keyword || publicSearchText(comment).includes(keyword))
    .filter((comment) => input.read !== 'unread' || !readIds.has(comment.id))
    .sort((left, right) => right.created - left.created);
  const start = (input.page - 1) * input.pageSize;
  return {
    items: comments.slice(start, start + input.pageSize),
    page: input.page,
    pageSize: input.pageSize,
    total: comments.length
  };
}

async function findComment(id) {
  const comments = await fetchAllAdminComments({ visibility: 'all' });
  const comment = comments.find((item) => String(item?._id || '') === id);
  if (!comment) throw createHttpError(404, 'Comment not found');
  return { comment, comments };
}

async function handlePatch(body) {
  const id = assertCommentId(body?.id);
  const action = String(body?.action || '');
  if (!Object.hasOwn(ACTIONS, action)) throw createHttpError(400, 'Invalid comment action');
  const { comment } = await findComment(id);
  if (comment.rid && (action === 'pin' || action === 'unpin')) {
    throw createHttpError(400, 'Replies cannot be pinned');
  }
  const result = await callTwikoo('COMMENT_SET_FOR_ADMIN', { id, set: ACTIONS[action] });
  if (!Number.isSafeInteger(result.updated) || result.updated < 1) {
    throw createHttpError(502, 'Twikoo returned an invalid moderation result');
  }
  return { id, action };
}

async function handleDelete(body) {
  const id = assertCommentId(body?.id);
  const { comment, comments } = await findComment(id);
  if (!comment.rid && comments.some((item) => String(item?.rid || '') === id)) {
    throw createHttpError(409, 'Delete replies first or hide the comment thread');
  }
  const result = await callTwikoo('COMMENT_DELETE_FOR_ADMIN', { id });
  if (!Number.isSafeInteger(result.deleted) || result.deleted < 1) {
    throw createHttpError(502, 'Twikoo returned an invalid deletion result');
  }
  return { id };
}

async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    requireAdminWrite(req);
    if (req.method === 'POST') {
      const body = await readJsonBody(req);
      return sendJson(res, 200, { success: true, data: await listComments(validateListRequest(body)) });
    }
    if (req.method === 'PATCH') {
      const body = await readJsonBody(req);
      return sendJson(res, 200, { success: true, data: await handlePatch(body) });
    }
    if (req.method === 'DELETE') {
      const body = await readJsonBody(req);
      return sendJson(res, 200, { success: true, data: await handleDelete(body) });
    }
    return sendJson(res, 405, { success: false, error: 'Method not allowed' });
  } catch (error) {
    return sendError(res, error);
  }
}

handler._test = {
  PAGE_SIZES,
  VISIBILITIES,
  READ_FILTERS,
  ACTIONS,
  MAX_READ_IDS,
  validateListRequest,
  listComments
};

module.exports = handler;
