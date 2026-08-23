# 个人博客工作区：文件分类与命名规范

基于当前项目架构（Hexo + Fluid + Vercel）以及已有的 `CLAUDE.md` / `AGENTS.md` 约束，特制定以下工作区文件创建、命名与分类规范，确保项目持续迭代过程中的整洁与可维护性。

## 1. 目录架构与分类规则

文件存放必须严格遵循其功能作用域，**严禁在根目录或不相关的目录下堆放临时文件。**

| 目录层级 | 存放内容说明 | 存放规则与边界 |
| :--- | :--- | :--- |
| **根目录 `/`** | 项目级配置与规范文档 | 仅限全局配置（如 `package.json`, `_config.yml`, `_config.fluid.yml`）和全局规范文档（`CLAUDE.md`, `AGENTS.md`, `readme.md`, `CONTEXT.md`）。绝不能放具体业务代码、测试文件、临时记忆或一次性 skill 清单。 |
| **`/source`** | Hexo 内容源 | 所有博客内容存放于此，Hexo 构建时以这里为入口。 |
| ├── `/source/_posts` | 文章 Markdown | 文件名格式 `YYYY-MM-DD-slug.md`，包含 front matter（title, date, categories, index_img 等）。 |
| ├── `/source/images` | 图片资源 | 存放博客文章插图、头像等（如 `my-avatar.jpg`, `img_*.png`），含 `covers/` 子目录。 |
| ├── `/source/admin` | 在线后台页面 | 存放 `index.html`，通过 `/admin/` 访问。 |
| ├── `/source/js` & `/source/css` | 自定义前端脚本和样式 | 存放如 `aoiblog-home.js`、`aoiblog-home.css` 等自定义资源。 |
| ├── `/source/about` | 关于页面 | 存放 `index.md`。 |
| ├── `/source/friends` | 友情链接页面 | 存放 `index.md`。 |
| ├── `/source/guestbook` | 留言板页面 | 存放 `index.md`。 |
| ├── `/source/news` | 每日日报静态页 | `index.html` 只保留语义页面骨架，`news.css` 存放独立样式，`js/` 存放原生 ES Modules，`fonts/` 只存上线所需的 WOFF2、生成 CSS 和字体许可证，`data/` 主要由管线和页面 API 产出。个人状态文件虽由 Hexo `exclude` 与 `.vercelignore` 排除出静态部署，仍以公开 Git 仓库为后端，不得写入秘密或可识别个人身份的信息。可人工维护 `source/news/data/interest_profile.md` 的兴趣画像要点，其余数据优先通过管线或页面操作生成。 |
| **`/api`** | Vercel Serverless 接口 | 后端业务逻辑。**一个文件对应一个明确的接口职责**。包括后台文章/设置接口，以及日报反馈、收藏、稍后读和漏读写回接口；非接口逻辑不要放进这里。 |
| **`/tools`** | 迁移和维护工具 | 存放如 `clean-post-inline-styles.mjs`、字体字符清单与生成脚本等一次性或维护工具；字体源 OTF 和工具中间产物不得入库。 |
| **`/tests`** | 文章页与后台的 Node 回归 | 只放 `npm run test:post` 的套件（当前为 `test_post_reading.mjs`、`test_admin_editor.mjs`、`test_admin_comments.mjs`），命名 `test_<范围>.mjs`。日报相关测试一律归 `/news-pipeline/tests`；这里不放临时调试脚本，用完即删。 |
| **`/scripts`** | Hexo 构建期扩展 | Hexo 启动时自动加载的脚本，如 `twikoo-path.js` 覆盖主题注入点。只放构建期逻辑，前端资源仍归 `/source/js` 与 `/source/css`。 |
| **`/news-pipeline`** | 每日日报生成管线 | Python 管线、新闻源、评分配置和测试。改日报生成逻辑只在这里动手。 |
| **`/.github/workflows`** | GitHub Actions | 仅存放仓库自动化工作流：每日生成与云端五项质量台账 `daily-news.yml`、手动只读夹具质量探针 `objectivity-acceptance.yml`、人工复核回填 `rollout-manual-review.yml`、台账缺口检测 `rollout-heartbeat.yml`。只有 `daily-news.yml` 允许自动 push，且仅限 `main` 分支上的 `source/news/data/`（commit 步骤同时判 `github.ref`，并显式 `git push origin HEAD:main`）。 |
| **`/docs`** | 项目维护文档 | 根层存现行维护规范；`adr/` 存架构决策记录（顺序编号，只增不改）；`agents/` 存工程 Skill 的仓库级读写约定；`archive/` 只存仍有兼容、迁移或排障价值的历史记录；`visual-baselines/` 存页面回归基准图。完成的实施计划和一次性分析报告在结论并入对应维护文档后删除。 |

---

## 2. 文件命名规范

为保持代码库的统一性，不同类型的文件采用不同的命名风格：

### 2.1 文章文件 (YYYY-MM-DD-slug)
- **规则**：日期前缀 + 英文 slug，全小写连字符。
- **适用范围**：`/source/_posts/`。
- **示例**：`2026-04-03-markdown-yu-fa-bi-ji.md`。

### 2.2 静态资源 (lowercase / kebab-case)
- **规则**：全小写，单词间用连字符 `-` 连接。因为这些文件名通常直接暴露在 URL 中。
- **适用范围**：`/source/images/`、`/source/js/`、`/source/css/`。
- **示例**：`friend-avatar.jpg`、`aoiblog-home.css`。
- *注：通过工具自动上传生成的图片，保留原时间戳格式即可（如 `img_1774010498471.png`）。*

### 2.3 后端接口文件 (camelCase)
- **规则**：小驼峰命名法，清晰表达接口意图。
- **适用范围**：`/api/` 目录下的 Serverless 函数。
- **示例**：`adminArticles.js`、`adminSettings.js`、`adminUpload.js`、`adminSession.js`、`newsState.js`。
- **特殊约定**：内部共享的工具模块，使用下划线前缀以区分对外接口，如 `_github.js`。

### 2.4 文档与配置文件
- **规则**：遵循业界常规（通常为全小写）。
- **示例**：`package.json`、`readme.md`。
- **特殊约定**：最高约束文档保持全大写 `CLAUDE.md` / `AGENTS.md` 以示强调。
- **代理文档分工**：`AGENTS.md` 是跨编码代理共享项目规则的唯一真身；`CLAUDE.md` 通过 `@AGENTS.md` 导入共享规则，只保留 Claude 专用的 skill 入口与导航。共享架构、安全、验证和 Git 规则只改 `AGENTS.md`，不再复制到 `CLAUDE.md`。
- **根目录边界**：不要再新增 `memory.md`、`skill.md` 这类一次性索引；持久规则进入 `AGENTS.md` / `CLAUDE.md`，面向维护者的说明进入 `readme.md` 或 `docs/`。

---

## 3. 文件创建决策指南（当你需要加东西时）

**场景 1：我要发布一篇新文章**
👉 **动作**：优先通过 `/admin/` 发布；需要手工维护时，在 `source/_posts/` 创建 `YYYY-MM-DD-slug.md`。草稿、Front Matter 与永久链接约束见 [博客维护手册](blog-maintenance.md#内容与配置)。

**场景 2：我要上传一张说明图，并在文章中引用**
👉 **动作**：将图片放入 `source/images/`，使用有语义的 kebab-case 文件名，并以 `/images/<filename>` 引用；后台上传与复用边界见 [博客维护手册](blog-maintenance.md#发布文章)。

**场景 3：我要给后台或日报页增加一个写回功能**
👉 **动作**：在 `/api/` 下创建职责明确的小驼峰文件，例如 `adminSummary.js` 或 `newsState.js`；一个文件只处理一类接口职责。

**场景 4：我要调整每日日报新闻源**
👉 **动作**：修改 `news-pipeline/sources.yaml`；不要直接编辑 `source/news/data/` 下的生成数据。

**场景 5：我要调整每日日报评分、阈值、分类偏好或成本护栏**
👉 **动作**：修改 `news-pipeline/config.yaml`，按 [日报维护手册](news-maintenance.md#验证) 运行对应回归；阈值、台账与退役上线门的取舍只在相关 ADR 中解释。

**场景 6：我要人工修正每日日报兴趣画像**
👉 **动作**：修改 `source/news/data/interest_profile.md`，只编辑以 `- ` 开头的偏好要点；不要手工改 `daily/*.js`、`events.json`、`source_health.json`、`score_history.json`、`feed.xml` 或 `search_index.js`，这些由管线产出或重建。`score_history.json` 是动态精选线的内部账本，损坏时应让管线按静态线回退并重建，不要人工补历史分数。`vocab/*.js` 是已停用单词本的历史数据，也不要手工维护。

**场景 7：我要维护日报个人状态**
👉 **动作**：优先通过 `/news/` 页面操作，由 `api/newsState.js` 写入；数据与隐私边界见 [日报维护手册](news-maintenance.md#数据与隐私边界)。

**场景 8：我要记录一个 Vercel 部署相关的深坑经验**
👉 **动作**：博客后台、API 与评论知识写入 `docs/blog-maintenance.md`，日报运行与部署知识写入 `docs/news-maintenance.md`；只有项目定位、安装方式或顶层入口变化才修改根目录 `readme.md`。如果是代理必须始终遵守的规则边界，再同步 `AGENTS.md` / `CLAUDE.md`。

**场景 9：我要更新日报衬线字体**
👉 **动作**：按 [日报维护手册](news-maintenance.md#字体维护) 同步生成字符清单和字体分片，并运行 `npm run test:news`；字体覆盖与预算理由见 ADR 0013。
