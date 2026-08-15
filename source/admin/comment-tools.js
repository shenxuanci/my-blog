(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.AoiAdminCommentTools = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  const VERSION = 1;
  const MAX_READ_ITEMS = 5000;
  const COMMENT_ID_PATTERN = /^[A-Za-z0-9_-]{1,80}$/;

  function emptyReadState() {
    return { version: VERSION, items: {} };
  }

  function pruneItems(items) {
    const entries = Object.entries(items)
      .filter(([id, readAt]) => COMMENT_ID_PATTERN.test(id)
        && Number.isFinite(readAt)
        && readAt > 0)
      .sort((left, right) => right[1] - left[1])
      .slice(0, MAX_READ_ITEMS);
    return Object.fromEntries(entries);
  }

  function parseReadState(raw) {
    try {
      const value = typeof raw === 'string' ? JSON.parse(raw) : raw;
      if (!value || typeof value !== 'object' || Array.isArray(value)
        || value.version !== VERSION
        || !value.items || typeof value.items !== 'object' || Array.isArray(value.items)) {
        return emptyReadState();
      }
      return { version: VERSION, items: pruneItems(value.items) };
    } catch {
      return emptyReadState();
    }
  }

  function readIds(state) {
    return Object.keys(parseReadState(state).items);
  }

  function markRead(state, id, readAt = Date.now()) {
    const current = parseReadState(state);
    if (!COMMENT_ID_PATTERN.test(String(id || '')) || !Number.isFinite(readAt) || readAt <= 0) {
      return current;
    }
    return {
      version: VERSION,
      items: pruneItems({ ...current.items, [id]: readAt })
    };
  }

  function markUnread(state, id) {
    const current = parseReadState(state);
    const items = { ...current.items };
    delete items[id];
    return { version: VERSION, items };
  }

  function publicPath(article) {
    const permalink = String(article?.permalink || '');
    if (/^\/(?!\/)[^?#]*\/$/.test(permalink)) return permalink;
    const date = String(article?.date || '').slice(0, 10);
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
    const filename = String(article?.filePath || '').split('/').pop() || '';
    const slug = filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/i, '');
    if (!match || !slug || !/^[A-Za-z0-9_-]+$/.test(slug)) return '';
    return `/${match[1]}/${match[2]}/${match[3]}/${slug}/`;
  }

  function buildArticleIndex(articles) {
    const byCommentPath = Object.create(null);
    for (const article of Array.isArray(articles) ? articles : []) {
      const path = publicPath(article);
      if (!path) continue;
      const entry = { label: String(article.title || path), path };
      const legacy = String(article.twikooPath || '');
      if (legacy) byCommentPath[legacy] = entry;
      byCommentPath[path] = entry;
    }
    return byCommentPath;
  }

  function resolveCommentTarget(comment, articleIndex) {
    const id = String(comment?.id || '');
    const path = String(comment?.path || '');
    if (path === '/' && COMMENT_ID_PATTERN.test(id)) {
      return { label: '留言板', url: `/guestbook/#${id}` };
    }
    const article = articleIndex?.[path];
    if (article && COMMENT_ID_PATTERN.test(id)) {
      return { label: article.label, url: `${article.path}#${id}` };
    }
    return { label: path || '未知页面', url: '' };
  }

  function initials(nick) {
    return Array.from(String(nick || '匿').trim() || '匿')[0].toUpperCase();
  }

  function commentPageForTotal(page, pageSize, total) {
    const safePage = Number.isSafeInteger(page) && page > 0 ? page : 1;
    const safePageSize = Number.isSafeInteger(pageSize) && pageSize > 0 ? pageSize : 20;
    const safeTotal = Number.isSafeInteger(total) && total > 0 ? total : 0;
    return Math.min(safePage, Math.max(1, Math.ceil(safeTotal / safePageSize)));
  }

  return {
    VERSION,
    MAX_READ_ITEMS,
    parseReadState,
    readIds,
    markRead,
    markUnread,
    publicPath,
    buildArticleIndex,
    resolveCommentTarget,
    initials,
    commentPageForTotal
  };
});
