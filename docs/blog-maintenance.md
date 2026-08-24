# 博客维护手册

本文记录博客文章、在线后台、Vercel API、Twikoo 评论和永久链接的现行维护方式。项目入口、命令和文档地图见根目录 [README](../readme.md)。

## 内容与配置

### 发布文章

优先通过 `/admin/` 发布或编辑文章。后台支持文章字段、封面与正文图片、草稿恢复和远端版本冲突提示，最终内容写入 `source/_posts/`。

手工发布时：

1. 在 `source/_posts/` 创建 `YYYY-MM-DD-slug.md`。
2. 填写 `title`、`date`、`categories` 与可选的 `index_img`。
3. 把图片放入 `source/images/`，正文使用 `/images/<filename>`。
4. 运行 `npm run build`，并检查文章页和永久链接。

后台选图后会立即提交图片资产；放弃文章不会自动删除已经上传的文件。相同内容只在相同用途和目录范围内复用，不跨用途清理。

### 后台编辑约束

- Word 粘贴按纯文本导入并转换为 Markdown 段落；Markdown 导入只规范化顶层普通正文的单换行。
- 当前标签页只保存一份 `sessionStorage` 会话草稿；保存、明确放弃或切换文章后清除，关闭标签页后不长期保留私人内容。
- 编辑旧文章时，服务端以原 Front Matter 为底稿，只更新后台受控字段；未知字段、额外分类、`old_id` 与 `twikooPath` 保持不变。
- 编辑和删除必须提交打开文章时的 GitHub blob SHA；远端已经变化时返回 `409`，刷新后重新处理，不能覆盖新版本。
- 站点设置同时修改 `_config.yml` 与 `_config.fluid.yml` 时使用一个 Git commit；任一源文件版本过期都会拒绝整次更新。

### 修改站点内容

| 内容 | 维护入口 |
| --- | --- |
| 站点标题、副标题、首页标语、页脚、关于页简介、导航显示名 | `/admin/` 的“站点设置” |
| 域名、语言、构建目录 | `_config.yml` |
| 导航链接、图标、头像、背景图、主题开关 | `_config.fluid.yml` |
| 关于、友链、留言板正文 | `source/about/`、`source/friends/`、`source/guestbook/` |
| 分类默认封面 | `source/_data/category-covers.json` |

站点设置中的展示文本按纯文本保存。导航名和 YAML 文本字段的校验属于构建安全边界，不要绕过后台校验直接写入不受支持的引号、反斜杠或换行结构。

## 永久链接与旧站兼容

- 文章 URL 使用 `/:year/:month/:day/:title/`；后台新文章写入显式 `permalink`，避免构建时区改变 URL。
- 主动修改日期时只更新永久链接的日期段并保留稳定 slug；普通编辑保留旧文章现有链接。
- 迁移文章的 `old_id` 与 `twikooPath` 维持旧链接和历史评论关联，不能随意删除或改写。
- 旧 `/articles.html#article_id` 链接由 `source/articles.html` 跳转到新地址。

迁移过程和已退役工具见 [Hexo 迁移记录](archive/2026-06-18-hexo-fluid-migration.md)。

## 在线后台与 API

### 环境变量

| 变量 | 用途 |
| --- | --- |
| `ADMIN_TOKEN` | 后台登录口令、会话签名和 Twikoo 管理凭据来源 |
| `GITHUB_TOKEN` | GitHub contents 写权限 |
| `GITHUB_OWNER` | 目标仓库 owner；可由部署环境推导 |
| `GITHUB_REPO` | 目标仓库名；可由部署环境推导 |
| `GITHUB_BRANCH` | 写入分支，默认 `main` |

凭证只能配置在 Vercel 环境变量中。`ADMIN_TOKEN` 登录成功后从页面内存清除，不写 `localStorage`；会话 Cookie 为 `HttpOnly + Secure + SameSite=Strict`，有效期 8 小时，作用域限定在 `/api`。

### 接口职责

- `api/adminSession.js`：建立、探测和退出后台会话。
- `api/adminArticles.js`：读取、发布、编辑和删除文章。
- `api/adminSettings.js`：读取和更新站点设置。
- `api/adminUpload.js`：校验并上传图片。
- `api/adminComments.js`：代理 Twikoo 评论管理。
- `api/newsState.js`：读写日报反馈、收藏、稍后读和漏读。

`api/vocab.js` 已删除；单词本历史数据只为恢复能力保留，不存在可写端点。

浏览器后台使用 `scope=admin` 的签名会话；脚本或 CLI 可以使用 `Authorization: Bearer <ADMIN_TOKEN>`。两条认证路径校验同一个口令并共享失败计数。高权限写接口只接受 admin 会话；日报个人状态接口接受签名个人会话。

所有 JSON 接口先检查请求体大小和 JSON 结构，响应带 `Cache-Control: no-store`。后台和日报 CSP、URL 校验、HTML 转义以及 `Object.hasOwn` 白名单检查属于纵深防御，修改相关代码时必须保留并运行 API 回归。

## Twikoo 评论

- Twikoo 后端固定为 `https://twikoo.aoiblog.top`；文章页与留言板共用同一后端。
- `_config.fluid.yml` 必须同时启用 `post.comments.enable`、设置 `post.comments.type: twikoo` 并配置 `twikoo.envId`。
- `scripts/twikoo-path.js` 覆盖 Fluid 评论注入点，评论 path 取 `page.twikooPath || url_for(page.path)`；不要在主题配置中写字面量 `twikoo.path`。
- 留言板使用 `comment: true` 和 `twikooPath: "/"`。Fluid 在构建期读取的是单数 `comment`。
- 页面只保留 Fluid 注入的一个评论容器，不要恢复旧正文中的 legacy 评论块。

后台评论管理只向浏览器返回脱敏字段，关键词搜索只覆盖昵称、正文、公开网站和评论 path。隐藏是可恢复状态；永久删除顶层评论前会检查回复，但检查与删除不是事务，有讨论内容时优先隐藏。

评论代理固定连接上述 Twikoo 主机、拒绝重定向并限制总超时。Twikoo 管理访问令牌由 `ADMIN_TOKEN` 按其非腾讯云协议派生，等同管理凭据；轮换后台口令时应先备份评论数据，在受控环境同步更新 Twikoo 管理密码和 Vercel `ADMIN_TOKEN`，全程不得输出摘要或明文。

## 前端维护入口

- 文章阅读交互：`source/js/aoiblog-home.js`、`source/css/aoiblog-post.css` 与 `source/css/aoiblog-home.css`。
- 首页文章卡片：`source/css/aoiblog-home.css`。
- 站内搜索：Fluid `local_search` 配置与主题生成的搜索索引。
- TOC：Fluid 主题配置和文章标题层级；移动端交互由文章阅读回归覆盖。
- 后台页面：`source/admin/index.html`。
- 评论注入：`scripts/twikoo-path.js`。

UI 调整只改样式和交互时，不要顺带修改现有展示文案。

## 验证

| 改动 | 验证 |
| --- | --- |
| 文章阅读页、博客脚本或样式 | `npm run test:post` 与 `npm run test:news` |
| 后台页面 | `npm run test:post` 与 `npm run test:news` |
| `api/` | `npm run test:news` |
| 评论注入脚本 | `npm run test:post` |
| 配置、依赖或完整交付 | `npm run build` |

验证后确认文章页、`/admin/`、评论区和永久链接仍能加载；检查 `git status --short`，清理测试或预览产生的临时文件。
