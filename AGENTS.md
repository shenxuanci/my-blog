# 项目说明

这个文件定义了本仓库中 AI 编码代理的工作规则。修改任何内容前请先阅读。

## 项目结构

- 这是一个 Hexo + Fluid + Vercel 静态博客项目。
- 文章 Markdown 位于 `source/_posts/`。
- Vercel API 路由位于 `api/`，用于在线后台发布、设置与评论管理，以及日报反馈、收藏、稍后读与漏读写回；单词本接口仅为停用功能保留。
- 在线后台页面位于 `source/admin/index.html`。
- 每日日报静态页位于 `source/news/`，数据由 `news-pipeline/` 生成。
- 维护规范放在 `docs/`，历史重构记录放在 `docs/archive/`。

## 修改边界

- 只做增量修改，并保持已部署站点稳定。
- 仅修改用户明确要求的范围。
- 除非用户明确提出，否则不要重写 API、不要大幅改动后台逻辑、不要编辑现有文章内容。
- 如果用户要求调整 UI 界面、视觉风格或样式表现，不要修改博客中的任何文本内容，包括标题、正文、按钮文案、说明文字和其他展示文本，除非用户明确要求同时修改文案。
- 不要把临时文件放在仓库根目录。根目录应只保留全局配置和项目文档，例如 `readme.md`、`AGENTS.md` 和 `CLAUDE.md`。
- 每次改动完成前，必须清理为调试、测试或预览临时创建的文件、目录和临时代码，不要把测试或临时内容留在工作区。

## 目录与命名规则

- `source/_posts/` 存放文章 Markdown 文件，格式 `YYYY-MM-DD-slug.md`。
- `source/images/` 存放图片资源，含 `covers/` 子目录。
- `source/js/` 和 `source/css/` 存放自定义前端脚本和样式。
- `scripts/` 存放 Hexo 构建期扩展（如覆盖主题注入点、改写渲染产物），由 Hexo 自动加载，不是前端资源。
- `source/admin/` 存放在线后台页面。
- `source/news/` 存放每日日报静态页面和生成数据，`source/news/data/` 是线上数据目录。
- `source/about/`、`source/friends/`、`source/guestbook/` 存放独立页面的 Markdown 源文件。
- `api/` 存放业务 API 接口。每个文件只负责一件事，使用 camelCase 命名，例如 `adminArticles.js`、`newsState.js`；`vocab.js` 是停用单词本的保留接口。
- `tools/` 存放迁移和维护工具脚本。
- `tests/` 存放文章页与后台的 Node 回归（`npm run test:post`）；日报相关测试归 `news-pipeline/tests/`，不要放这里。
- `docs/` 存放维护规范与项目文档；`docs/archive/` 只存仍有兼容、迁移或排障价值的历史记录。
- `news-pipeline/` 存放每日日报生成管线。改信源优先改 `sources.yaml`，改评分和阈值优先改 `config.yaml`。

## 产品与体验规则

- 设计应服务目标用户，尽可能让系统承担复杂度。
- 优先使用合理默认值，而不是增加不必要的用户输入。
- 让反馈能够引导用户进行下一步操作。
- 保持公开站点稳定、清晰、易读；保持后台流程实用、可预期。

## 沟通规则

- 解释默认使用中文。
- 代码、命令、文件名、分支名和提交信息保持英文。
- 先给结论，再给说明。
- 在路径明确且合理时，避免不必要的确认。

## 安全规则

- 绝不要提交密钥、令牌、凭证或私密环境变量。
- 日报个人状态文件即使已从 Hexo/Vercel 静态产物排除，仍以公开 Git 仓库为存储后端；不得写入秘密、隐私正文或可识别个人身份的信息。
- 出现错误时，要追查根因。
- 不要为了让命令通过而压掉错误。

## 验证规则

- 修改代码后，按需运行 `npm run build` 或 `npm run dev`。
- 构建通过只说明构建没断，不说明改动正确。改前端后跑 `npm run test:post` 与 `npm run test:news`；**改 `api/` 后必跑 `npm run test:news`**（`test_admin_api.mjs` 与 `test_admin_comments_api.mjs` 共同守住后台信任边界，`test:post` 不加载 `api/`）；改 `news-pipeline/` 后按 `readme.md` 验证章节跑对应 Python 回归。
- 验证页面仍能正常加载、`source/admin/index.html` 仍兼容、API 改动已正确接通。
- 验证结束后检查工作区，确认没有遗留测试文件、临时文件或临时调试代码。
- 没有说明执行过哪些验证前，不要声称工作已完成。

## 文档规则

- 动日报相关代码前，先读根目录 `CONTEXT.md`（术语表，含每个词的 `_Avoid_` 同义词禁用项）和 `docs/adr/` 里与改动区域相关的决策记录；输出里提到领域概念时用术语表的词，不要漂移到它明确避免的同义词。
- 当架构、安装方式、运行行为或可复用的排障知识发生变化时，更新 `readme.md`。
- 持久性的项目知识应写入受版本控制的文档，不要只放在临时笔记里。
- 完成的实施计划和一次性分析报告不长期保留；有复用价值的结论应并入 `readme.md` 或对应维护文档。
- `docs/archive/` 只保留仍有兼容、迁移或排障价值的历史记录，阅读时以文件日期为边界。

## Git 规则

- 使用简短的英文提交信息。
- 除非用户明确要求，否则不要执行 `git push`。
- 除非用户明确要求，否则不要回退用户自己的改动。
- 唯一例外：`.github/workflows/daily-news.yml` 可以每日自动 commit + push `main` 分支上的 `source/news/data/`，不得扩大到其他分支或路径。
