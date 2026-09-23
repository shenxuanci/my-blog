(function initAdminEditorTools(root, factory) {
  const tools = factory(root);
  if (typeof module === "object" && module.exports) module.exports = tools;
  if (root) root.AoiAdminEditorTools = tools;
}(typeof globalThis !== "undefined" ? globalThis : this, function createAdminEditorTools(root) {
  function replaceSelection(value, selectionStart, selectionEnd, insertedText) {
    const nextValue = value.slice(0, selectionStart) + insertedText + value.slice(selectionEnd);
    const nextSelection = selectionStart + insertedText.length;
    return {
      value: nextValue,
      selectionStart: nextSelection,
      selectionEnd: nextSelection,
    };
  }

  function isWordHtml(html) {
    return /(?:\bMso[A-Za-z]|\bmso-|urn:schemas-microsoft-com:office|Microsoft Word)/i.test(String(html || ""));
  }

  function normalizeWordText(text) {
    const lines = String(text || "")
      .replace(/\r\n?/g, "\n")
      .split("\n")
      .map((line) => line.replace(/[\t ]+$/g, ""));

    while (lines.length && !lines[0].trim()) lines.shift();
    while (lines.length && !lines[lines.length - 1].trim()) lines.pop();

    return lines.filter((line) => line.trim()).join("\n\n");
  }

  function wordPasteReplacement({ html, text, value, selectionStart, selectionEnd }) {
    if (!isWordHtml(html)) return null;
    return replaceSelection(
      String(value || ""),
      selectionStart,
      selectionEnd,
      normalizeWordText(text),
    );
  }

  function markedApi() {
    if (root?.marked?.lexer) return root.marked;
    if (typeof require === "function") {
      const markedModule = require("marked");
      const marked = markedModule.marked || markedModule;
      if (marked?.lexer) return markedModule.Lexer ? markedModule : marked;
    }
    throw new Error("Markdown parser is unavailable");
  }

  function defaultLexer(source) {
    return markedApi().lexer(source, { gfm: true });
  }

  function tokenContainsRange(source, tokens, range) {
    for (const token of tokens) {
      if (!token.raw) continue;
      let position = source.indexOf(token.raw);
      while (position >= 0) {
        if (position <= range.start && position + token.raw.length >= range.contentEnd) {
          return true;
        }
        position = source.indexOf(token.raw, position + 1);
      }
    }
    return false;
  }

  function referenceDefinitionRanges(source, tokens) {
    const rule = markedApi().Lexer?.rules?.block?.gfm?.def;
    if (!rule) return [];
    const ranges = [];
    let position = 0;
    while (position < source.length) {
      rule.lastIndex = 0;
      const match = rule.exec(source.slice(position));
      if (match) {
        const trailingNewlines = /\n+$/.exec(match[0])?.[0].length || 0;
        const range = {
          start: position,
          end: position + match[0].length,
          contentEnd: position + match[0].length - trailingNewlines,
        };
        if (!tokenContainsRange(source, tokens, range)) ranges.push(range);
        position += match[0].length;
        continue;
      }
      const newline = source.indexOf("\n", position);
      if (newline < 0) break;
      position = newline + 1;
    }
    return ranges;
  }

  function tokenStartOutsideRanges(source, raw, cursor, ranges) {
    let position = source.indexOf(raw, cursor);
    while (position >= 0) {
      const end = position + raw.length;
      const overlapsDefinition = ranges.some((range) => position < range.end && end > range.start);
      if (!overlapsDefinition) return position;
      position = source.indexOf(raw, position + 1);
    }
    return -1;
  }

  function paragraphHasStructuralSyntax(source, position) {
    const before = source.slice(0, position);
    const separator = before.lastIndexOf("\n\n");
    const block = before.slice(separator < 0 ? 0 : separator + 2);
    const lines = block.split("\n");
    const line = lines[lines.length - 1] || "";
    return /^\s*(?:\[(?:\^[^\]]+|[^\]]+)\]:|[-+*]\s+|\d+[.)]\s+|>\s?|#{1,6}\s+| {4}\S)/.test(block)
      || /^\s*\|.*\|\s*$/.test(line)
      || /\S\s*\|\s*\S/.test(line);
  }

  function isTopLevelParagraphAt(source, position) {
    let tokens;
    try {
      tokens = defaultLexer(source);
    } catch {
      // A missing or broken parser must not make structural Markdown destructive.
      return false;
    }
    if (!Array.isArray(tokens)) return false;
    const definitionRanges = referenceDefinitionRanges(source, tokens);
    let cursor = 0;
    for (const token of tokens) {
      if (!token.raw) continue;
      const start = tokenStartOutsideRanges(
        source,
        token.raw,
        cursor,
        token.type === "paragraph" ? definitionRanges : [],
      );
      if (start < 0) return false;
      const end = start + token.raw.length;
      if (position >= start && position <= end) {
        return token.type === "paragraph" && !paragraphHasStructuralSyntax(source, position);
      }
      cursor = end;
    }
    return false;
  }

  function editorEnterReplacement({ value, selectionStart, selectionEnd, shiftKey }) {
    const text = String(value || "");
    const insertedText = shiftKey
      ? "  \n"
      : isTopLevelParagraphAt(text, selectionStart) ? "\n\n" : "\n";
    return replaceSelection(text, selectionStart, selectionEnd, insertedText);
  }

  function safeMarkdownUrl(value) {
    const url = String(value || "").trim();
    if (!url || /[\u0000-\u001f\u007f]/.test(url) || /^\/\//.test(url)) return "#";
    if (url.startsWith("#")) return url;
    try {
      const parsed = new URL(url, "https://preview.invalid/admin/");
      if (!["http:", "https:", "mailto:", "tel:"].includes(parsed.protocol)) return "#";
      return url;
    } catch {
      return "#";
    }
  }

  const SESSION_DRAFT_VERSION = 1;

  function createSessionDraft(fields, uploaded = false, savedAt = Date.now()) {
    const source = fields && typeof fields === "object" ? fields : {};
    return {
      version: SESSION_DRAFT_VERSION,
      filePath: String(source.filePath || ""),
      sha: String(source.sha || ""),
      title: String(source.title || ""),
      date: String(source.date || ""),
      category: String(source.category || ""),
      index_img: String(source.index_img || ""),
      content: String(source.content || ""),
      uploaded: Boolean(uploaded),
      savedAt: Number.isFinite(Number(savedAt)) ? Number(savedAt) : Date.now(),
    };
  }

  function parseSessionDraft(value) {
    try {
      const parsed = typeof value === "string" ? JSON.parse(value) : value;
      if (!parsed || typeof parsed !== "object" || parsed.version !== SESSION_DRAFT_VERSION) return null;
      for (const key of ["filePath", "sha", "title", "date", "category", "index_img", "content"]) {
        if (typeof parsed[key] !== "string") return null;
      }
      return createSessionDraft(parsed, parsed.uploaded, parsed.savedAt);
    } catch {
      return null;
    }
  }

  function draftRestoreState(draft, article) {
    if (!draft || !article || draft.filePath !== String(article.filePath || "")) return "conflict";
    return draft.sha === String(article.sha || "") ? "restore" : "conflict";
  }

  function draftDiscardMessage(draft) {
    return draft?.uploaded
      ? "文章尚未保存，确认放弃吗？已上传的图片会继续保留在仓库中。"
      : "文章尚未保存，确认放弃吗？";
  }

  const ARTICLE_FRONT_MATTER_KEYS = new Set([
    "title",
    "date",
    "updated",
    "categories",
    "tags",
    "layout",
    "permalink",
    "index_img",
    "old_id",
    "twikooPath",
  ]);

  function yamlApi() {
    if (root?.jsyaml?.load) return root.jsyaml;
    if (typeof require === "function") return require("js-yaml");
    throw new Error("YAML parser is unavailable");
  }

  function leadingFrontMatter(text) {
    const match = /^---[ \t]*\n(?:([\s\S]*?)\n)?---[ \t]*(?:\n|$)/.exec(text);
    if (!match) return null;
    const parser = yamlApi();
    try {
      const parsed = parser.load(match[1] || "");
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
      return Object.keys(parsed).some((key) => ARTICLE_FRONT_MATTER_KEYS.has(key))
        ? match
        : null;
    } catch {
      return null;
    }
  }

  function splitImportedMarkdown(source) {
    let body = String(source || "")
      .replace(/^\uFEFF/, "")
      .replace(/\r\n?/g, "\n");
    const frontMatter = leadingFrontMatter(body);
    if (frontMatter) body = body.slice(frontMatter[0].length);

    const leadingHeading = /^(?:[ \t]*\n)*#\s+([^\n]+)(?:\n|$)/.exec(body);

    return {
      heading: leadingHeading ? leadingHeading[1].trim() : "",
      headingLength: leadingHeading ? leadingHeading[0].length : 0,
      body,
    };
  }

  function normalizeParagraphToken(raw) {
    if (/^\[\^[^\]]+\]:/.test(raw)) return raw;
    const lines = raw.split("\n");
    let result = lines[0] || "";
    for (let index = 1; index < lines.length; index += 1) {
      const previous = lines[index - 1];
      const trailingSlashes = /\\+$/.exec(previous)?.[0].length || 0;
      const hardBreak = / {2,}$/.test(previous) || trailingSlashes % 2 === 1;
      result += `${hardBreak ? "\n" : "\n\n"}${lines[index]}`;
    }
    return result;
  }

  function markdownImportReplacement({ source, title, lexer }) {
    const imported = splitImportedMarkdown(source);
    const existingTitle = String(title || "").trim();
    // 标题框已有内容时不再消费开头 H1：旧实现把 H1 从正文删掉又丢弃 imported.heading，
    // 那一行会彻底消失（既不在正文也不在标题框）。
    const body = existingTitle
      ? imported.body
      : imported.body.slice(imported.headingLength);
    const tokens = (lexer || defaultLexer)(body);
    if (!Array.isArray(tokens)) throw new Error("Markdown parser returned invalid tokens");
    const definitionRanges = referenceDefinitionRanges(body, tokens);
    let cursor = 0;
    let value = "";
    for (const token of tokens) {
      if (!token.raw) continue;
      const tokenStart = tokenStartOutsideRanges(
        body,
        token.raw,
        cursor,
        token.type === "paragraph" ? definitionRanges : [],
      );
      if (tokenStart < 0) throw new Error("Markdown parser returned inconsistent tokens");
      value += body.slice(cursor, tokenStart);
      value += token.type === "paragraph" ? normalizeParagraphToken(token.raw) : token.raw;
      cursor = tokenStart + token.raw.length;
    }
    value = `${value}${body.slice(cursor)}`.replace(/^\n+|\n+$/g, "");
    return {
      title: existingTitle || imported.heading,
      value,
    };
  }

  return {
    createSessionDraft,
    draftDiscardMessage,
    draftRestoreState,
    editorEnterReplacement,
    markdownImportReplacement,
    normalizeWordText,
    parseSessionDraft,
    safeMarkdownUrl,
    wordPasteReplacement,
  };
}));
