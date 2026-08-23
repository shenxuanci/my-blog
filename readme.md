# Aoitsuki Blog

Aoitsuki 的个人博客与每日新闻日报。公开站点采用 `Hexo + Fluid` 生成静态页面，Vercel 负责部署和少量写回 API。

- 生产主域：<https://www.aoiblog.top>
- 在线后台：`/admin/`
- 每日日报：`/news/`
- Node.js：`24.x`
- 日报管线：Python `3.12`

## 快速开始

```powershell
npm install
npm run dev
```

常用命令：

| 命令 | 用途 |
| --- | --- |
| `npm run dev` | 启动 Hexo 本地开发服务器 |
| `npm run build` | 清理并生成 `dist/` |
| `npm run preview` | 本地预览生成站点 |
| `npm run test:post` | 文章阅读页、后台编辑器与评论回归 |
| `npm run test:news` | 日报前端、后台 API 与安全边界回归 |

日报 Python 依赖、离线验证和手动运行方式见 [日报维护手册](docs/news-maintenance.md)。

## 项目地图

| 路径 | 职责 |
| --- | --- |
| `source/_posts/` | 文章 Markdown，文件名为 `YYYY-MM-DD-slug.md` |
| `source/images/` | 图片与文章封面 |
| `source/js/`、`source/css/` | 博客自定义前端资源 |
| `source/admin/` | 在线后台页面 |
| `api/` | Vercel API：后台、评论管理与日报个人状态写回 |
| `source/news/` | 日报静态页面、前端资源与线上数据 |
| `news-pipeline/` | 日报抓取、筛选、生成、审计和测试 |
| `scripts/` | Hexo 构建期扩展 |
| `tools/` | 迁移与维护工具 |
| `docs/` | 维护手册、ADR、历史记录与视觉基准 |

完整的目录和命名规则见 [工作区规范](docs/workspace_conventions.md)。

## 常见维护入口

- 发布或编辑文章：优先使用 `/admin/`；手工维护时修改 `source/_posts/`。
- 修改站点展示文字：优先使用后台“站点设置”；底层站点配置在 `_config.yml`，主题配置在 `_config.fluid.yml`。
- 上传图片：使用后台，或把文件放入 `source/images/` 并以 `/images/<filename>` 引用。
- 修改新闻源：编辑 `news-pipeline/sources.yaml`。
- 修改日报评分、阈值、内容生成或成本护栏：编辑 `news-pipeline/config.yaml`。
- 修改日报前端：编辑 `source/news/index.html`、`source/news/news.css` 或 `source/news/js/`。
- 维护兴趣画像：只编辑 `source/news/data/interest_profile.md` 中以 `- ` 开头的要点。
- 日报生成数据与个人状态优先由管线或页面 API 维护，不要直接手改。

博客发布、后台、API、评论与永久链接兼容详见 [博客维护手册](docs/blog-maintenance.md)。日报管线、数据、页面和字体维护详见 [日报维护手册](docs/news-maintenance.md)。

## 部署配置

Vercel 后台与 GitHub 写回需要：

```text
ADMIN_TOKEN
GITHUB_TOKEN
GITHUB_OWNER
GITHUB_REPO
GITHUB_BRANCH
```

`GITHUB_OWNER` / `GITHUB_REPO` 可由 Vercel 的仓库环境推导，`GITHUB_BRANCH` 默认 `main`。所有凭证只进入部署环境变量，不得写入代码、文档或提交。

每日新闻工作流使用仓库 Secrets `STEPFUN_API_KEY`、`DEEPSEEK_API_KEY`，自建 RSSHub 源还需要 `RSSHUB_BASE` 与 `RSSHUB_KEY`；质量台账 Issue 号使用仓库变量 `LEDGER_ISSUE`。部署探测的自愈能力需要 `VERCEL_DEPLOY_HOOK`。

## 验证

| 改动范围 | 必跑验证 |
| --- | --- |
| `source/js/`、`source/css/`、`source/admin/`、`scripts/` | `npm run test:post` 与 `npm run test:news` |
| `api/` | `npm run test:news` |
| 日报页面、脚本或字体 | `npm run test:news` |
| `news-pipeline/` | 按 [日报维护手册](docs/news-maintenance.md#验证) 运行对应 Python 回归 |
| 完整交付 | `npm run build` |

构建通过只说明产物能够生成；功能正确性仍由对应回归和人工页面检查确认。

## 文档索引

- [博客维护手册](docs/blog-maintenance.md)：文章、后台、API、Twikoo、永久链接与博客验证。
- [日报维护手册](docs/news-maintenance.md)：管线、Actions、数据、隐私、页面、字体与日报验证。
- [日报术语表](CONTEXT.md)：日报领域词汇及禁用同义词。
- [架构决策记录](docs/adr/)：难以逆转且需要解释取舍的决策。
- [日报信源待办](docs/news_source_roadmap.md)：仍未完成的信源评估，不记录现行机制。
- [历史迁移记录](docs/archive/2026-06-18-hexo-fluid-migration.md)：Astro 旧站迁入 Hexo 的兼容背景。
- [日报视觉基准](docs/visual-baselines/news-editorial/)：主要视图的人工视觉对照图。

现行行为以代码、配置和测试为准；两本维护手册提供操作入口，历史原因以 ADR 与归档文档为准。
