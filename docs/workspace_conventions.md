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
| **`/tests`** | 文章页与后台的 Node 回归 | 只放 `npm run test:post` 的套件（当前为 `test_post_reading.mjs`、`test_admin_editor.mjs`），命名 `test_<范围>.mjs`。日报相关测试一律归 `/news-pipeline/tests`；这里不放临时调试脚本，用完即删。 |
| **`/scripts`** | Hexo 构建期扩展 | Hexo 启动时自动加载的脚本，如 `twikoo-path.js` 覆盖主题注入点。只放构建期逻辑，前端资源仍归 `/source/js` 与 `/source/css`。 |
| **`/news-pipeline`** | 每日日报生成管线 | Python 管线、新闻源、评分配置和测试。改日报生成逻辑只在这里动手。 |
| **`/.github/workflows`** | GitHub Actions | 仅存放仓库自动化工作流：每日生成与云端五项质量台账 `daily-news.yml`、手动只读夹具质量探针 `objectivity-acceptance.yml`、人工复核回填 `rollout-manual-review.yml`、台账缺口检测 `rollout-heartbeat.yml`。只有 `daily-news.yml` 允许自动 push，且仅限 `main` 分支上的 `source/news/data/`（commit 步骤同时判 `github.ref`，并显式 `git push origin HEAD:main`）。 |
| **`/docs`** | 项目维护文档 | 根层存现行维护规范；`adr/` 存架构决策记录（顺序编号，只增不改）；`agents/` 存工程 Skill 的仓库级读写约定；`archive/` 只存仍有兼容、迁移或排障价值的历史记录；`visual-baselines/` 存页面回归基准图。完成的实施计划和一次性分析报告在结论并入 `readme.md` 后删除。 |

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
👉 **动作**：优先通过 `/admin/` 发布；从 Word 粘贴时后台只保留纯文本并转换成 Markdown 空行分段，导入 Markdown 时也只规范化顶层普通正文。普通正文用 `Enter` 新建段落，`Shift+Enter` 写入两个行尾空格加换行的 Markdown 硬换行；列表、续行、引用、表格、标题、代码、原始 HTML 与引用/脚注定义内使用单换行。当前标签页会用 `sessionStorage` 保存一份文章会话草稿，远端 SHA 未变时可在刷新或重新登录后恢复，发生冲突时必须复制内容或明确恢复；关闭标签页后不长期保留。后台新文章使用纯日期午夜值并写入显式 `permalink`；旧文章普通编辑保留原日期和链接，并原样保留未知 Front Matter、额外分类、`old_id` 与 `twikooPath`，主动改日期时更新链接日期段并保留稳定 slug。需要手工维护时，在 `/source/_posts/` 下创建 `YYYY-MM-DD-slug.md` 并填写 front matter。

**场景 2：我要上传一张说明图，并在文章中引用**
👉 **动作**：将图片放入 `/source/images/`，命名为 `xxx-architecture.png`，确保名字有语义。文章中引用路径为 `/images/xxx-architecture.png`。后台会在正文图片当月目录或自定义封面目录内按 Git blob SHA 复用相同文件，但不会跨用途、跨月份清理历史图片。后台选择图片后会立即提交资产；放弃文章只提示图片继续保留，不自动删除上传文件。

**场景 3：我要给后台或日报页增加一个写回功能**
👉 **动作**：在 `/api/` 下创建职责明确的小驼峰文件，例如 `adminSummary.js` 或 `newsState.js`；一个文件只处理一类接口职责。

**场景 4：我要调整每日日报新闻源**
👉 **动作**：修改 `news-pipeline/sources.yaml`；不要直接编辑 `source/news/data/` 下的生成数据。

**场景 5：我要调整每日日报评分、阈值、分类偏好或成本护栏**
👉 **动作**：修改 `news-pipeline/config.yaml`，运行 `py -3.12 -m pytest news-pipeline/tests -q` 做完整回归；历史独立脚本 `news-pipeline/tests/test_pipeline.py` 不作为交付验收入口。会改变候选样本的归并调用上限和候选阈值属于共享运行时指纹，首次有效 publish 会重置台账的五项计数（不再阻塞任何上线动作，见 `docs/adr/0016-retire-five-gate-rollout-acceptance.md`）；只调整生成或 shadow 成本告警线不会重置。

**场景 6：我要人工修正每日日报兴趣画像**
👉 **动作**：修改 `source/news/data/interest_profile.md`，只编辑以 `- ` 开头的偏好要点；不要手工改 `daily/*.js`、`events.json`、`source_health.json`、`score_history.json`、`feed.xml` 或 `search_index.js`，这些由管线产出或重建。`score_history.json` 是动态精选线的内部账本，损坏时应让管线按静态线回退并重建，不要人工补历史分数。`vocab/*.js` 是已停用单词本的历史数据，也不要手工维护。

**场景 7：我要维护日报个人状态**
👉 **动作**：优先通过 `/news/` 页面操作，由 `api/newsState.js` 写 `feedback.json`、`read_later.json`、`favorites.json` 或 `misses.json`；不要绕过 API 直接编辑这些状态文件，除非是在排障时做最小修复。新增或调整状态文件时，还要同步检查 `_config.yml` 的 `exclude` 与 `.vercelignore`。这两层只阻止静态发布，不会把 Git 后端变成私有存储；漏读记录不能写自由备注或类别，任何状态文件都不得保存敏感内容。单词本已停用，`api/vocab.js` 已于 2026-08-16 删除，`vocab-book.json` 与 `vocab/*.js` 仅为恢复能力保留。

**场景 8：我要记录一个 Vercel 部署相关的深坑经验**
👉 **动作**：不要新建文档，直接修改根目录的 `readme.md`；如果是规则边界，再同步 `AGENTS.md` / `CLAUDE.md`。

**场景 9：我要更新日报衬线字体**
👉 **动作**：字符清单只是首屏热区、不是覆盖契约，语料增长时无需重跑。**要重新调优首屏字节数时，字符清单和字体必须在同一个 commit 里一起重新生成**——只重跑清单会让首屏命中的分包数变化（2026-08-07 实测 38 片 → 72 片）而字体一个字节没变，冷传输护栏会因此失败。改字体本身则用固定版本工具运行 `tools/generate-news-font.cjs`，生成前清空目录里的旧 WOFF2。`source/news/fonts/` 只保留 WOFF2、`result.css` 与 `OFL.txt`；不得提交 OTF、`index.proto`、预览页或临时依赖目录。新增使用 `--serif` 的样式必须显式写 `font-weight:700`（只托管这一个字面）。改字体资产或冷传输护栏后跑 `npm run test:news`。
