import fs from 'node:fs/promises';
import path from 'node:path';
import yaml from 'js-yaml';

const root = process.cwd();
const postsDir = path.join(root, 'source', '_posts');
const coversPath = path.join(root, 'source', '_data', 'category-covers.json');

function yamlString(value) {
  return JSON.stringify(String(value ?? ''));
}

function firstCategory(frontMatter) {
  const parsed = yaml.load(frontMatter, { schema: yaml.JSON_SCHEMA });
  if (parsed == null) return '';
  if (typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Front Matter must be a YAML mapping');
  }

  const value = Array.isArray(parsed.categories) ? parsed.categories[0] : parsed.categories;
  if (value == null) return '';
  if (!['string', 'number', 'boolean'].includes(typeof value)) {
    throw new Error('Front Matter categories must be scalar values');
  }
  return String(value);
}

function mappedCover(coverMap, category) {
  for (const key of [category, 'default']) {
    if (Object.hasOwn(coverMap, key) && typeof coverMap[key] === 'string' && coverMap[key]) {
      return coverMap[key];
    }
  }
  return '/images/covers/defaults/fallback.webp';
}

function leadingFrontMatter(source) {
  // 这里只处理仓库内的 Hexo 文章；与外部 Markdown 导入不同，文件首部的标准
  // 分隔块就是 Front Matter。正则直接兼容 BOM/CRLF，避免重写无关行尾。
  const match = /^(\uFEFF?)---[ \t]*(\r?\n)(?:([\s\S]*?)\r?\n)?---[ \t]*(?:\r?\n|$)/.exec(source);
  if (!match) return null;
  return {
    raw: match[0],
    bom: match[1],
    eol: match[2],
    frontMatter: match[3] || ''
  };
}

function addIndexImage(source, cover) {
  const match = leadingFrontMatter(source);
  if (!match) return source;

  const originalFrontMatter = match.frontMatter.replace(/\r\n?/g, '\n');
  const frontMatter = originalFrontMatter.replace(/^(index_img:[ \t]*["'][^"']+["'])(old_id:)/m, '$1\n$2');
  if (/^index_img:/m.test(frontMatter)) {
    if (frontMatter === originalFrontMatter) return source;
    return `${match.bom}---${match.eol}${frontMatter.replace(/\n/g, match.eol)}${match.eol}---${match.eol}${source.slice(match.raw.length)}`;
  }
  const categoriesMatch = frontMatter.match(/^categories:\n(?:\s+-\s*.+\n?)+/m);
  const line = `index_img: ${yamlString(cover)}`;
  const nextFrontMatter = categoriesMatch
    ? frontMatter.replace(categoriesMatch[0], () => `${categoriesMatch[0].replace(/\n?$/, '\n')}${line}\n`)
    : `${frontMatter}\n${line}`;
  const serializedFrontMatter = nextFrontMatter.replace(/\n/g, match.eol);

  return source.replace(
    match.raw,
    () => `${match.bom}---${match.eol}${serializedFrontMatter}${match.eol}---${match.eol}`
  );
}

async function main() {
  const coverMap = JSON.parse(await fs.readFile(coversPath, 'utf8'));
  const files = (await fs.readdir(postsDir)).filter((file) => file.endsWith('.md'));
  let updated = 0;

  for (const file of files) {
    const filePath = path.join(postsDir, file);
    const source = await fs.readFile(filePath, 'utf8');
    const frontMatter = leadingFrontMatter(source)?.frontMatter || '';
    const category = firstCategory(frontMatter);
    const cover = mappedCover(coverMap, category);
    const nextSource = addIndexImage(source, cover);

    if (nextSource !== source) {
      await fs.writeFile(filePath, nextSource, 'utf8');
      updated += 1;
    }
  }

  console.log(`Applied category covers to ${updated} posts.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
