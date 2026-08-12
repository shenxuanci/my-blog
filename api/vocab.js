const {
  setCors,
  sendJson,
  sendError,
  createHttpError,
  requireAdminWrite,
  readJsonBody,
  readTextFile,
  putTextFile
} = require('./_github');

// 日报英语单词本写回通道：收藏候选 / 手动加词 / 标掌握 / 移除。
// 仅本人（ADMIN_TOKEN）可用；管线次日读 vocab-book.json 做去重 + 补全手动裸词。
const BOOK_FILE = 'source/news/data/vocab-book.json';
const OPS = ['collect', 'add', 'master', 'unmaster', 'remove'];
const MAX_WORDS = 5000;
const MAX_PENDING = 500;
const MAX_PAYLOAD_BYTES = 4096;

function emptyBook() {
  return { version: 1, words: [], pending: [] };
}

function clip(value, max) {
  return String(value ?? '').slice(0, max);
}

// 与管线 normalize_word 一致：小写、只留字母，作为词元去重键
function lemmaKey(word) {
  return String(word ?? '').trim().toLowerCase().replace(/[^a-z]/g, '');
}

function normalizeBook(parsed) {
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return emptyBook();
  return {
    version: parsed.version || 1,
    words: Array.isArray(parsed.words) ? parsed.words : [],
    pending: Array.isArray(parsed.pending) ? parsed.pending : []
  };
}

function isStoredBook(value) {
  return Boolean(value)
    && typeof value === 'object'
    && !Array.isArray(value)
    && value.version === 1
    && Array.isArray(value.words)
    && value.words.every((entry) => entry && typeof entry === 'object' && !Array.isArray(entry))
    && Array.isArray(value.pending)
    && value.pending.every((entry) => entry && typeof entry === 'object' && !Array.isArray(entry));
}

function validate(op, payload) {
  if (!OPS.includes(op)) {
    throw createHttpError(400, `Invalid op: ${op}`);
  }
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw createHttpError(400, 'payload must be an object');
  }
  if (Buffer.byteLength(JSON.stringify(payload), 'utf8') > MAX_PAYLOAD_BYTES) {
    throw createHttpError(400, 'payload too large');
  }
  const word = String(payload.word || '').trim();
  const lemma = lemmaKey(payload.lemma || word);
  if (!lemma) {
    throw createHttpError(400, 'payload.word must contain letters');
  }
  return { word, lemma };
}

// 在 words + pending 里按词元查找是否已存在
function hasLemma(book, lemma) {
  const inWords = book.words.some((w) => (w.lemma || lemmaKey(w.word)) === lemma);
  const inPending = book.pending.some((p) => (p.lemma || lemmaKey(p.word)) === lemma);
  return inWords || inPending;
}

// 返回 { book, changed }：changed=false 表示幂等命中，无需写回
function applyOp(book, op, payload, key, now) {
  const { word, lemma } = key;

  if (op === 'collect') {
    if (hasLemma(book, lemma)) return { book, changed: false };
    const card = {
      word,
      lemma,
      phonetic: clip(payload.phonetic, 40),
      pos: clip(payload.pos, 20),
      sense_zh: clip(payload.sense_zh, 40),
      example_en: clip(payload.example_en, 400),
      item_id: clip(payload.item_id, 60),
      item_title: clip(payload.item_title, 200),
      date: clip(payload.date, 10),
      source: 'auto',
      collected_ts: now,
      mastered: false
    };
    return { book: { ...book, words: [...book.words, card].slice(-MAX_WORDS) }, changed: true };
  }

  if (op === 'add') {
    if (hasLemma(book, lemma)) return { book, changed: false };
    const entry = {
      word,
      lemma,
      date: clip(payload.date, 10),
      item_id: clip(payload.item_id, 60),
      item_title: clip(payload.item_title, 200),
      context: clip(payload.context, 400),
      ts: now
    };
    return { book: { ...book, pending: [...book.pending, entry].slice(-MAX_PENDING) }, changed: true };
  }

  if (op === 'master' || op === 'unmaster') {
    const want = op === 'master';
    let changed = false;
    const words = book.words.map((w) => {
      if ((w.lemma || lemmaKey(w.word)) === lemma && Boolean(w.mastered) !== want) {
        changed = true;
        return { ...w, mastered: want, mastered_ts: want ? now : undefined };
      }
      return w;
    });
    return { book: { ...book, words }, changed };
  }

  // remove：从 words 和 pending 里都删掉该词元
  const words = book.words.filter((w) => (w.lemma || lemmaKey(w.word)) !== lemma);
  const pending = book.pending.filter((p) => (p.lemma || lemmaKey(p.word)) !== lemma);
  const changed = words.length !== book.words.length || pending.length !== book.pending.length;
  return { book: { ...book, words, pending }, changed };
}

async function readBook() {
  try {
    const { content, sha } = await readTextFile(BOOK_FILE);
    const parsed = JSON.parse(content);
    if (!isStoredBook(parsed)) {
      throw createHttpError(500, `${BOOK_FILE} is corrupted`);
    }
    return { book: normalizeBook(parsed), sha };
  } catch (error) {
    if (error.status === 404) return { book: emptyBook(), sha: undefined };
    if (error instanceof SyntaxError) {
      throw createHttpError(500, `${BOOK_FILE} is corrupted`);
    }
    throw error;
  }
}

async function writeOp(op, payload, key, now) {
  const attempt = async () => {
    const { book, sha } = await readBook();
    const { book: next, changed } = applyOp(book, op, payload, key, now);
    if (changed) {
      await putTextFile(
        BOOK_FILE,
        JSON.stringify(next, null, 1) + '\n',
        `news: vocab ${op} ${key.word}`,
        sha
      );
    }
    return { changed, words: next.words.length, pending: next.pending.length };
  };

  try {
    return await attempt();
  } catch (error) {
    // sha 过期（与管线/其他提交撞车）重读重试一次
    if (error.status === 409 || error.status === 422) {
      return attempt();
    }
    throw error;
  }
}

async function handler(req, res) {
  setCors(res);

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    requireAdminWrite(req);

    if (req.method === 'GET') {
      const { book } = await readBook();
      return sendJson(res, 200, { success: true, data: book });
    }

    if (req.method === 'POST') {
      const body = await readJsonBody(req);
      const op = String(body.op || '');
      const key = validate(op, body.payload);
      const now = new Date().toISOString();
      const result = await writeOp(op, body.payload, key, now);
      return sendJson(res, 200, {
        success: true,
        data: { op, changed: result.changed, words: result.words, pending: result.pending }
      });
    }

    return sendJson(res, 405, { success: false, error: 'Method not allowed' });
  } catch (error) {
    return sendError(res, error);
  }
}

handler._test = { OPS, emptyBook, normalizeBook, validate, applyOp, hasLemma, lemmaKey };

module.exports = handler;
