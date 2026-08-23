# Aoitsuki Blog

这是 Aoitsuki 的个人博客项目，当前采用 `Hexo + Fluid + Vercel` 的静态博客架构。

## 当前架构

- 博客框架：Hexo
- 主题：Fluid
- 内容源：`source/_posts/*.md`
- 静态资源：`source/images/`
- 自定义脚本：`source/js/`（前端）、`scripts/`（Hexo 构建期扩展）
- Vercel API：`api/`（在线后台，以及日报反馈、收藏、稍后读与漏读写回；停用的单词本接口仍保留）
- 在线后台：`/admin/`
- 构建输出：`dist/`
- 部署平台：Vercel
- 评论系统：Twikoo
- 规范生产主域：`https://www.aoiblog.top`；裸域 `https://aoiblog.top` 统一以 307 跳转到 `www`。

## 目录说明

```text
source/_posts/          文章 Markdown
source/images/          图片资源
source/images/covers/   文章封面图
source/js/              自定义前端脚本
source/css/             自定义前端样式
source/admin/           在线后台页面
source/_data/           分类封面等站点数据
api/                    Vercel Serverless API（后台与日报个人状态写回）
source/about/           关于页面
source/friends/         友情链接页面
source/guestbook/       留言板页面
source/news/            每日新闻日报页（静态，数据由 news-pipeline 生成）
news-pipeline/          新闻日报生成管线（GitHub Actions 每日运行）
scripts/                Hexo 构建期扩展（主题注入点覆盖等）
tools/                  迁移和维护工具
docs/                   维护规范与必要的历史记录
docs/archive/           历史架构与迁移记录（非当前运行说明）
_config.yml             Hexo 主配置
_config.fluid.yml       Fluid 主题配置
.vercelignore           Vercel 源文件排除清单
vercel.json             Vercel 路由与安全响应头
```

## 常用命令

安装依赖：

```powershell
npm install
```

本地开发：

```powershell
npm run dev
```

构建：

```powershell
npm run build
```

本地预览：

```powershell
npm run preview
```

新闻页前端回归测试：

```powershell
npm run test:news
```

文章阅读页与后台编辑器回归测试：

```powershell
npm run test:post
```

## 内容维护

- 在线后台地址是 `/admin/`。登录后可以发布、编辑、删除文章，上传文章封面和正文图片，以及管理 Twikoo 评论。
- 文章编辑器和站点设置的操作栏（`.form-actions`）是 `position: sticky` 的常驻底栏，长文章不必翻到文末才能发布；「删除」与「取消」同侧，靠与「发布」的距离防误点。**它依赖 `.workspace` 使用 `overflow: clip` 而非 `hidden`**——`hidden` 同样能裁圆角，但会创建滚动容器，让 sticky 以一个自身不滚动的祖先为参照系，底栏**静默失效、不报错也不告警**，现场没有任何线索指向元凶。顶部 `#status` 的提示同时镜像进底栏，否则按钮移近后反馈反而落在视口外。
- 底栏里的状态位用 `flex: 1 0 100%` 独占整行并限高两行，**不能给它 `flex-grow` 去和按钮抢同一行**：GitHub 超时那类上百字符的报错会把底栏撑到视口四分之一高、按钮换行三排（实测 1280px 和 375px 都会）。完整信息仍在顶部 `#status`。以上不变量（`clip`/`sticky`/实心背景/状态位不挤压按钮/两组按钮 + `space-between` 的间距）都由 `npm run test:post` 的静态断言锁定。
- 从 Microsoft Word 粘贴到后台正文框时，只导入纯文本并把 Word 段落转换成 Markdown 空行分段；Word 的加粗、标题等格式不保留。导入 Markdown 时，后台使用本地 Marked 分词，只把顶层普通正文的单换行转为空行，标题、列表、引用、表格、代码、原始 HTML、图片和引用/脚注定义保持原结构；本地解析器未加载或解析失败时会中止导入，不改动编辑器现有内容。普通正文中按 `Enter` 新建段落，按 `Shift+Enter` 写入两个行尾空格加换行的 Markdown 硬换行；列表、引用、表格、标题与代码块内继续使用 Markdown 的单换行。后台预览会按独立段落显示两格首行缩进，包含图片的段落不缩进。
- 后台文章编辑器会把当前标签页中唯一一份未保存文章写入 `sessionStorage`，刷新或 8 小时会话过期后重新登录可按打开时的 GitHub blob SHA 恢复。远端 SHA 已变化时不会自动覆盖，而是保留草稿并提示复制内容或明确恢复；切换文章、新建、取消、进入设置、退出、返回前台及关闭页面都会检查未保存修改。保存成功或明确放弃后清除草稿，关闭标签页后不长期保留私人随笔。站点设置只做离开提醒，不写浏览器存储。
- 编辑旧文章时，服务端以原始 Front Matter 为底稿，只定点更新后台受控字段；未知字段、原有顺序、额外分类、`old_id` 与 `twikooPath` 保持不变。后台生成的双引号标量按 JSON/YAML 转义规则反解，英文引号和反斜杠重复保存不会累积转义。分类封面映射只有文件确实不存在时才回退默认封面，GitHub 故障、无效 JSON 或错误数据结构会阻止写入并显示错误。
- 后台“站点设置”可以修改常用展示文本，包括站点标题、副标题、首页标语、页脚文本、关于页昵称/简介和现有导航显示名；页脚按纯文本保存并进行 HTML 转义。
- 新文章最终会写入 `source/_posts/`。
- 图片统一放入 `source/images/`，文章中使用 `/images/<filename>`；后台上传会校验 PNG、JPEG、GIF、WebP 的文件签名，扩展名与内容不一致时拒绝写入。相同内容的正文图片会在当月上传目录内复用，封面会在自定义封面目录内复用，不跨用途或跨月份扫描。
- 后台选图后会立即提交图片资产。取消或放弃文章不会自动删除已经上传的文件，以免误删后来被复用的资源；本次草稿上传过图片时，放弃确认会明确提示图片仍保留在仓库中。
- 默认分类封面配置在 `source/_data/category-covers.json`。
- **封面取值的两个坑（2026-08-10 审查修，都由 `npm run test:news` 钉住）**：分类名是用户可控的（后台随手就能建新分类），而 `coverForCategory` 从这份 JSON 里按分类名取值。①**原型键**：分类叫 `toString` / `valueOf` 时，裸对象取值取出的是继承来的**函数**，`yamlString` 会把它写成 `index_img: "function toString() { [native code] }"`——封面直接坏掉，而且没有任何报错。现在用 `Object.hasOwn` 判自有键并要求 `typeof === 'string'`。②**未校验的旁路**：单篇 `index_img` 走 `validateCoverUrl`，但映射里的值此前只做过 `typeof` 检查，等于同一个 sink 有一条没校验的路；这份 JSON 也可以手改，不是只有后台会写。现在读取时逐个过 `validateCoverUrl`，非法值回退兜底封面而不是让整次发文章失败。
- 文章 front matter 中的 `index_img` 是首页卡片封面；如果后台没有上传单篇封面，会自动使用分类默认封面。
- 首页文章卡片标题允许自然换行，桌面端和移动端都不会再使用 Fluid 默认的单行省略或两行截断；覆盖样式位于 `source/css/aoiblog-home.css`。
- 文章 URL 默认使用 `/:year/:month/:day/:title/`；后台新建文章时会按所选日期和最终文件 slug 写入显式 `permalink`，避免构建时区改变 URL。主动改日期时只更新永久链接的日期段并保留稳定 slug；普通编辑保留旧文章已有链接，没有显式链接的历史文章不会被批量迁移。
- 新文章的纯日期 `date` 写成 `YYYY-MM-DD 00:00:00`，脚本或 API 显式传入时分秒时原样保留。`date` 是发布元数据，不再承担固定 URL 的职责。
- 迁移自旧站的文章保留 `old_id` 和 `twikooPath` front matter，用于旧链接兼容和 Twikoo 评论路径。

## 在线后台环境变量

部署到 Vercel 后，后台写文章和保存站点设置需要在 Vercel 项目环境变量中配置：

```text
ADMIN_TOKEN=后台登录口令
GITHUB_TOKEN=具有目标仓库 contents 写权限的 GitHub token
GITHUB_OWNER=shenxuanci
GITHUB_REPO=my-blog
GITHUB_BRANCH=main
```

`ADMIN_TOKEN` 只在登录提交的那一次请求里出现，**换取会话后即从页面内存清除**，既不写 `localStorage`，也不再随后续请求发送。会话是 8 小时有效、`HttpOnly + Secure + SameSite=Strict` 的签名 Cookie，`scope` 参与签名：`admin` 可发文章、改设置、传图，`personal` 只能读写日报反馈、收藏、稍后读和漏读。目前只有 `/admin/` 登录会签发会话，签发的都是 `admin`。GitHub token 始终只保存在服务端环境变量中。这套 scope 设计**刻意放宽了原先「签名 cookie 不得换来发文章权限」的不变式**，换取主口令不再常驻页面内存；取舍理由、被否掉的方案和「看到相关测试别改回去」的提醒见 `docs/adr/0010-admin-writes-accept-scoped-session.md`。

### API 鉴权与并发保护

- 失败锁定由 `api/_loginGuard.js` 统一持有，**Cookie 登录和 `Authorization: Bearer` 共用同一份计数**。这一点是必须的：两条路验的是同一个 `ADMIN_TOKEN`，只给其中一条接限流等于没限流——攻击者换打 `/api/adminArticles` 就能无限次猜口令（2026-07-29 修复）。缺失凭证不计入锁定，只有「带了 `Authorization` 但值不对」才记账，否则未认证探测就能把管理员自己锁在门外。
- `POST /api/adminSession` 校验后台口令并建立个人会话；同一客户端在 15 分钟内连续失败 5 次后，该 Serverless 实例会返回 `429` 与 `Retry-After`，成功登录会清除失败记录。客户端地址优先取 Vercel 提供的 `x-vercel-forwarded-for` 首地址，缺失时回落到通用转发头或 socket 地址。失败记录最多保留 1000 个客户端且只存在当前实例内存中，因此这只是应用层兜底，不替代 Vercel Firewall 等跨实例限流。`GET` 用于探测会话（后台页刷新后据此直接恢复，不再要求重新输入口令），`DELETE` 用于退出。会话 Cookie 仅作用于 `/api`，接口不开放跨域凭据读取；畸形 Cookie 按未登录处理，不产生 500。
- `api/newsState.js` 只接受个人会话，用于日报反馈、收藏、稍后读和漏读；读取使用 `GET /api/newsState?type=feedback|read_later|favorites|misses`，写入使用 `POST /api/newsState` 与 `{ "type": "...", "payload": { ... } }`。单次 payload 上限 4096 字节，各状态最多保留 1000 条；并发写入撞到 GitHub blob SHA 时重读后重试一次。状态文件读入时必须是 `version: 1` 的普通对象，且对应 `entries` / `items` 必须是对象数组；无效 JSON 或错误结构一律报损坏并禁止覆盖，不能把异常状态静默当空列表。所有状态的 `date` 都必须是真实的 `YYYY-MM-DD` 日历日期，稍后读链接必须是带主机名的有效 HTTP(S) URL。漏读新增 payload 为 `date/title?/url?/reason`，撤销为 `op: "remove"` 加记录 `id`；标题或有效 HTTP(S) URL 至少一个，`reason` 只允许 `important_event`（重要事件）、`deep_read`（值得深读）、`missing_perspective`（缺少视角）。`adminArticles.js`、`adminSettings.js`、`adminUpload.js`、`adminComments.js` 这些高权限接口走 `requireAdminWrite`：带 `Authorization` 头时用受限流的 `Bearer <ADMIN_TOKEN>`（留给脚本/CLI），否则认 `scope=admin` 的会话 Cookie（浏览器后台用）。
- 所有 JSON 接口在业务处理前先做请求体体积检查：默认上限 1 MiB，图片上传因 8 MiB 二进制转为 data URL 后会膨胀而单独放宽到 12 MiB；超过上限返回 `413`，畸形 JSON 返回 `400`。这层应用检查不替代 Vercel 自身更低的请求体硬上限，后台仍需在浏览器端压缩图片。
- 踩坑：用查表取值判真做白名单（`if (!STATE_FILES[type])`）挡不住 `__proto__`、`constructor`、`toString`、`hasOwnProperty`、`valueOf`——这些原型键取出来都是真值，会绕过校验并把 `Object.prototype` 当成写入路径送进 GitHub 文件接口。**接口里凡是用对象做白名单，一律用 `Object.hasOwn(map, key)` 判断**（2026-07-26 修复）。
- 编辑或删除文章时必须提交打开文章时返回的 GitHub blob SHA；文件已被其他操作修改时接口返回 `409`，应刷新后重新编辑，不能覆盖较新的内容。
- 站点设置涉及 `_config.yml` 与 `_config.fluid.yml` 时通过单个 Git commit 原子更新；任一源文件版本过期都会拒绝整次更新，不留下半套配置。
- 踩坑：站点设置是用正则改 YAML 文本，两条约束不能省。①**导航名不许含 `"` 和 `\`**——写入用 JSON 转义（`\"`），读回用 `"([^"]*)"`，第一次保存还合法，第二次保存正则会在反斜杠处截断，替换出 `name: "新值"旧尾"`，YAML 解析失败、站点直接构建不出来。所有文本字段另外挡换行与超长。②**改块内字段的正则必须锚定到父块**：`^\s{2}content:` / `^\s{2}name:` 这类写法只是碰巧命中 `footer:` / `about:` 底下那一个，主题配置一旦新增同缩进同名 key 就会静默改错地方，现在统一经 `replaceInBlock` 只在目标块的区间内替换（2026-07-29 修复）。
- 所有 API 响应统一带 `Cache-Control: no-store`，避免后台数据、个人状态和鉴权失败结果被浏览器或中间缓存复用。`vercel.json` 为全部响应启用 `X-Content-Type-Options: nosniff`，禁止 `/admin` 与 `/admin/` 被第三方页面嵌入；后台 CSP 只允许同源脚本与固定 SHA-256 匹配的内联脚本/样式，不允许 `unsafe-inline`、`unsafe-eval`、对象、`base` 改写或页面嵌入，修改后台内联代码时必须同步哈希并由 API 回归校验。`/news` 及其子路径同样使用仅允许同源脚本、样式、字体、请求和表单提交的严格 CSP（图片额外允许 `data:`）。这层策略用于在内容转义与 URL 校验之外继续限制注入影响面。

## 修改网站文字

- 站点标题、副标题、首页标语、页脚、关于页昵称/简介、现有导航显示名：优先通过 `/admin/` 的“站点设置”修改。
- 站点描述、域名、语言、构建目录等底层配置：改 `_config.yml`。
- 导航链接、导航图标、头像、背景图、主题开关等主题配置：改 `_config.fluid.yml`。
- 关于页正文：改 `source/about/index.md`。
- 友链页正文：改 `source/friends/index.md`。
- 留言页正文：改 `source/guestbook/index.md`。
- 文章标题、分类、日期、封面、正文：优先通过 `/admin/` 编辑，也可以直接改 `source/_posts/*.md`。

## 评论（Twikoo）

- 后端为自托管 Twikoo 云函数，`envId: https://twikoo.aoiblog.top`（1.7.x），文章页与留言板共用同一后端。
- 文章页与留言板都走 Fluid 的评论注入点，由 `_config.fluid.yml` 三处开关控制：`post.comments.enable: true`、`post.comments.type: twikoo`、顶层 `twikoo.envId`。三者缺一不显示（`type` 默认是 `disqus`，只开 `enable` 不改 `type` 会加载错插件）。
- **评论 path 由 `scripts/twikoo-path.js` 决定**：它注册 `theme_inject` 过滤器，以同名 `default` 覆盖 Fluid 的 `postComments` / `pageComments` 注入点，path 取 `page.twikooPath || url_for(page.path)`。迁移来的旧文章用 front-matter 里的 `twikooPath`（即旧 `article_id`）读到历史评论，新文章没有该字段就自动回落到真实 URL 路径。模板会先对 path 做 JSON 序列化和 URI 编码再写入内联脚本，不得改回裸的引号插值，否则换行、反斜杠或 `</script>` 边界会破坏评论区脚本。
- 留言板（`/guestbook/`）front-matter 写 `comment: true` 和 `twikooPath: "/"`。**注意是单数 `comment`**：Fluid 的 `node_modules/hexo-theme-fluid/scripts/filters/post-filter.js` 会在 `before_generate` 阶段用单数 `comment` 重写每个页面的 `page.comments`，写复数 `comments: true` 会被它覆盖成 `false`，评论区直接不渲染。
- 踩坑（2026-07-28 修复）：`_config.fluid.yml` 里曾配置 `twikoo.path: window.location.pathname`，但 Fluid 模板写的是 `path: '<%= theme.twikoo.path %>'`——带引号且转义，线上输出的是**字面量字符串** `'window.location.pathname'`。结果所有文章的文末评论区共用同一个 path 桶，任何人在这里发的评论都会出现在全部文章下。因此 **`twikoo` 段不要再配置 `path`**，交给上面的注入脚本处理。
- 踩坑（2026-07-28 修复）：迁移工具曾给每篇文章正文尾部注入 `<section class="legacy-comments">` 挂载块，与 Fluid 自己的评论区同页并存，导致每篇文章渲染**两个评论区**、两个元素抢用 `id="twikoo"`、两个 Twikoo 版本（CDN 1.6.32 与主题内置 1.6.8）竞争。这些块已随正文清洗一并删除；`source/js/twikoo-legacy-path.js` 只在页面存在 `[data-twikoo-path]` 时才动作，正文清空后它在文章页自然不再生效。
- 踩坑：Hexo Fluid 迁移时 `post.comments.enable` 被置为 `false`，文章页评论一度整体消失；后端始终在线，恢复只需开上述三处配置，无需重建后端。

### 后台评论管理

- `/admin/` 的「评论管理」复用现有 `admin` 会话，通过 `/api/adminComments` 在服务端代理 Twikoo；浏览器不保存 Twikoo 管理令牌，也不会收到评论邮箱、IP、IP 属地、UA、内部 uid、原始 `href` 或 HTML。列表正文由服务端转为纯文本，完整排版仍去公开页面查看。
- 普通列表与显隐筛选直接使用 Twikoo 分页。关键词搜索不能透传给 Twikoo——它会同时匹配邮箱和 IP——而是在最多 2000 条评论的服务端脱敏结果中只搜索昵称、正文、公开网站和评论 path；当前浏览器的未读筛选走同一条受限扫描路径。超过上限、8 秒总超时、分页总数漂移、缺页或重复记录都会明确失败，不返回不完整结果。
- 支持隐藏／恢复、顶层置顶／取消置顶和单条永久删除。删除顶层评论前会扫描回复并在发现回复时返回 `409`；Twikoo 没有把检查和删除合成事务，仍存在极小并发竞态，因此有讨论内容时优先隐藏。已读状态只存在当前浏览器的 `aoiblog_admin_comment_reads_v1`，查看详情或原文即标记，不能当作已审核或已处理。
- 评论所在页面只由后台已读取的文章 `twikooPath` / `permalink` 构造，不信任评论提交时携带的 `href`。旧文章通过 `twikooPath` 回到现有永久链接，`/` 指向留言板，无法映射的 path 仍可管理但不生成跳转。
- 评论代理固定连接 `https://twikoo.aoiblog.top`，不接受客户端覆盖地址且禁止跟随 HTTP 重定向，避免管理令牌离开固定主机。8 秒总超时覆盖响应头和正文读取；非 2xx、非法 JSON、缺失业务码以及没有实际更新／删除记录都会安全失败。服务端用 `MD5(ADMIN_TOKEN)` 作为 Twikoo access token；这与 Twikoo 非腾讯云前端「先 MD5 明文密码、服务端再保存其 MD5」的协议一致。不要把该摘要误当成无敏感性的普通哈希，它可以直接换取评论管理权限。

#### 首次启用与口令轮换

1. 先备份 Twikoo 数据，再调用 `GET_PASSWORD_STATUS`。只有明确返回尚未初始化时才继续；如果已经设置密码，立即停止，不能覆盖未知管理员。
2. 在受控本地 shell 中从环境变量读取 `ADMIN_TOKEN`，计算 UTF-8 字节的 MD5，小写十六进制结果作为 `SET_PASSWORD.password` 提交。不得把明文或摘要写进命令参数、仓库、日志、浏览器存储或文档。
3. 用同一摘要调用 `LOGIN`，确认返回成功后清除本地变量。运行时代码只使用已经存在的密码，绝不自动注册或重置。
4. 以后轮换 `ADMIN_TOKEN` 时，先备份并按 Twikoo 官方重置流程同步设置相同的新密码，再部署新后台口令；不同步会导致文章后台登录成功但评论管理返回配置错误。

2026-08-15 已按上述流程完成首次启用：线上 Twikoo 为 1.7.4，管理密码等于当时的 `ADMIN_TOKEN`。该状态会变化，操作前必须重新查询，不能把这条记录当作当前授权。

排障线索：后台「评论管理」报 `Twikoo admin is not initialized or ADMIN_TOKEN does not match` 时，第一步是调 `GET_PASSWORD_STATUS` 看 `status` 字段，不要先查代码。这条 503 由 `api/_twikoo.js` 在 Twikoo 业务码非 0 且消息命中登录／密码关键词时抛出，覆盖「从未初始化」和「密码与 `ADMIN_TOKEN` 不一致」两种情况：`status:false` 是前者，走本节第 1–3 步；`status:true` 但 `LOGIN` 返回 `1023 密码错误` 是后者，走第 4 步的同步重置。

## 文章阅读页

- 正文排版在 `source/css/aoiblog-post.css`，**所有选择器以 `.post-content` 打头**。该类只出现在 Fluid 的 `layout/post.ejs`，因此样式精确限定在文章页，不会波及同样使用 `.markdown-body` 的关于页/友链页/留言板，也不影响 `/news/` 日报页（日报页根本不加载这份样式）。配色一律取 `aoiblog-home.css` 里的 `--aoi-*` 变量，跟随亮暗两套主题。
- 正文顶层纯文字段落统一使用 `2em` 首行缩进，桌面端与移动端口径一致；选择器只匹配 `.markdown-body` 的直接子段落，并排除包含图片的段落，因此引用、列表、代码块、嵌套组件和图片布局不受影响。该行为由 `npm run test:post` 的样式回归锁定。
- 文章标题在桌面与移动端都静态完整显示；Fluid 的打字效果只从 `post` 范围移除，首页、归档、分类、标签与独立页保持原行为。标题下隐藏固定作者名，继续显示发布日期、字数和预计阅读时长。
- 页面顶沿的细线按 `.markdown-body` 的实际阅读区间显示进度，并在懒加载图片、折叠块等改变正文高度时自动重算；短到不足一屏多的文章不显示。桌面端进入正文后，左右侧栏缩到屏幕边缘；悬停或键盘聚焦侧栏会临时展开，回到文首则完全恢复。低于 `992px` 时不启用侧栏收起。
- 移动目录复用 Fluid 已生成的 `#toc-body`，仅在目录实际包含标题时创建按钮和抽屉。抽屉支持遮罩、关闭按钮、目录跳转和 `Esc` 关闭；打开时将键盘焦点限制在目录内，关闭后把焦点交还给原控件，关闭状态的抽屉不进入 Tab 顺序。初始化必须保持幂等，避免主题刷新后出现重复按钮。
- 代码块移动端默认保持原始缩进并横向滚动，左上角按钮只切换当前代码块的视觉折行，不改变代码文本、复制结果或持久化任何偏好。普通 Markdown 表格使用独立横向滚动容器；语法高亮内部用于排版的表格必须排除，不能套入该容器。
- **代码高亮踩过的三个坑，改代码块样式前先看这条**（都由 `npm run test:post` 的三条断言锁定，每条都实测过「去掉修复即失败」）：
  - Fluid 的 `node_modules/hexo-theme-fluid/layout/_partials/css.ejs` 同时输出亮暗两张高亮样式表，但**只给 id、不给暗色那张加 `disabled`**；而负责切换的主题脚本 `node_modules/hexo-theme-fluid/source/js/color-schema.js` 里 `setHighlightCSS()` 只做 `removeAttribute('disabled')` / `setAttribute('disabled','')`，**它假定初始状态就是「暗色已禁用」**。前提不成立时两张表同时生效，后加载的暗色表压住亮色表，亮色模式下也会拿到暗色配色。本仓库的 `scripts/highlight-dark-toggle.js` 用 `after_render:html` 在产物里补回那个初始状态（幂等，且只匹配 `id="highlight-css-dark"`）。**不要改 `node_modules` 里的主题源码**——那里不进版本控制，Vercel 每次 `npm install` 都会冲掉。
  - 行内代码规则若写成 `.markdown-body code`，会连代码块里的 `<code class="hljs">` 一起命中，权重 (0,2,1) 压过高亮主题的 `.hljs` (0,1,0)，**于是主题没单独着色的 token 被刷成行内代码的强调色**；强调色不随代码块背景走，暗色下对比度极低。必须写成 `:not(pre) > code` 把作用域限回行内。同理代码块内的 `code` 不要声明 `color`（曾写过 `color: inherit`，同样盖过主题色），前景色一律交给 `.hljs`，亮暗两套主题各自带配套色值。
  - 行号列与代码列是 `<td class="gutter">`、`<td class="code">` 里**两个各自独立的 `<pre>`**，浏览器分别排版，字号/行高/垂直内边距任一只改一侧就会错位，且分两种：① 主题的 `.markdown-body pre` 带 `font-size: 85% !important`（权重压不过，别跟它抢），代码侧多一层 `<code>`，一旦在它上面写相对字号就会在 85% 之上再乘一次（实测 13.6px vs 12.24px，36 行累积错开近一整行）——所以内层 `<code>` 用 `font-size: inherit`，行高写带单位定值（unitless 会各自乘本侧字号）；② 主题给代码侧 `<pre>` 留了 `padding: 1.45rem 1rem`，却把行号侧重置成 `padding: 0 .75rem`，导致行号整体高出 1.45rem——这是**不随行数变化的固定错位**，和 ① 是两回事，两者都修掉才真正对齐（修好后浏览器实测第 1 至 36 行偏移恒为 0px）。
- 暗色高亮主题用 `atom-one-dark`（`_config.fluid.yml` 的 `code.highlight.highlightjs.style_dark`）。主题默认的 `dark` 只给 4 组 token 上色、`.hljs-subst` 干脆是空规则，未命中的 token 只能继承前景色。换主题后 `--highlight-bg-color` 会由 Fluid 从主题文件解析后自动跟随（`#282c34`），**不需要手工同步背景色**。注意 `resolveHighlight()` 会把空格转连字符，且找不到文件时**静默回退**（现有亮色 `github gist` 实际用的是 `github.css`），新增主题名后要去 `dist/css/` 确认真的换了。另外 `atom-one-dark` 的注释色 `#5c6370` 在自家背景上只有 2.32:1，中文注释几乎糊进背景，因此暗色下单独把 `.hljs-comment` 提亮到约 4.6:1。
- 方格纸纹只留在正文两侧并降低对比度；文章页新增动效必须响应 `prefers-reduced-motion`。交互逻辑由 `source/js/aoiblog-home.js` 先按日期路径筛选，再以 `.post-content .markdown-body` 确认真实文章 DOM；日期型 404、`source/news/`、`source/admin/` 与普通独立页均不进入初始化。
- 写作时可直接用原生折叠块，无需插件也无需 JS：

  ```html
  <details>
  <summary>折叠标题</summary>

  折叠内容，中间要留空行，Markdown 才会正常渲染。

  </details>
  ```

  注意 `/admin/` 的预览是自制极简渲染器（先 `escapeHtml` 再只认标题/图片/链接/粗体/代码块），折叠块在后台预览里会显示为原文，发布后线上正常。
- 左侧同分类文章列表由 `post.category_bar` 提供。主题默认 `specific: true`，要求每篇文章 front-matter 声明 `category_bar: true` 才显示；本站文章都没有该字段，等于侧栏从未渲染过，因此改成 `specific: false` 对所有文章开启，并用 `post_order_by: "date"` 按时间正序排列以贴合系列阅读顺序。
- 文末版权区展示最后更新时间（`post.copyright.update_date.enable: true`）。该行只在 `updated` 晚于 `date` 时出现，两者相同的文章不显示，属模板的正常行为。
- 旧文正文清洗（2026-07-28，经用户授权的一次性迁移）：迁移自旧 Astro 站的文章正文原本是带内联样式的裸 HTML（`text-indent: 2em`、写死的链接色与图片阴影），会绕过主题变量和暗色模式；同时正文里重复出现与标题同名的 `<h2>` 和 `# 标题`，连同模板的 `<h1>` 构成三重标题并污染右侧目录。已由 `tools/clean-post-inline-styles.mjs` 批量还原为干净 Markdown。该脚本幂等，改写前会把代码与正文分开做逐字比对，任一不一致就拒绝写入并报告。
- 顺带修复：旧文里 `<pre><code class="language-x">` 形式的代码块得不到语法高亮（Hexo 只处理围栏代码块，裸 HTML 的 `<pre>` 原样透传），清洗时已转成围栏代码块。

## 站内搜索

- `_config.fluid.yml` 的 `search.enable: true`，索引在构建时生成到 `dist/local-search.xml`，含全文，无后端依赖。
- **不要安装 `hexo-generator-search`**：Fluid 1.9.9 自带索引生成器（`node_modules/hexo-theme-fluid/scripts/generators/local-search.js`，注册名 `_hexo_generator_search`），装第三方插件只会多产出一个用不到的 `dist/search.xml`。主题 `_config.yml` 里那句"基于 hexo-generator-search 插件"的注释已经过时。

## 文章目录（TOC）

- 侧栏目录由 Fluid 内置的 tocbot 渲染，`.toc-body` 超过 `75vh` 时内部可滚动。
- 踩坑：tocbot 默认 `disableTocScrollSync: false`，即高亮项随阅读变化时会自动把目录滚回当前标题，手动向下翻看目录会被反复拽回顶部。已在 `_config.fluid.yml` 的 `post.toc.disableTocScrollSync: true` 关闭该同步（该键经 deep-merge 传入 `tocbot.init`，主题其余 toc 默认不受影响）。

## 发布新文章

推荐方式：

1. 打开 `/admin/`。
2. 输入后台口令。
3. 点击“新文章”。
4. 填标题、日期、分类和 Markdown 正文。
5. 可选上传封面；不上传时使用分类默认封面。上传的封面/正文图会在浏览器端自动缩放（封面 ≤1920px、正文 ≤1600px）并重编码为 WebP 后再提交——因为 Vercel Serverless Function 请求体硬上限为 4.5MB，手机原图直传会被平台以 413 拦掉；压缩逻辑在 `source/admin/index.html`（`compressImage`），GIF 例外（原样上传以保留动画，仅做体积拦截）。
6. 点击“发布”，后台会提交 Markdown 和图片到 GitHub，Vercel 会自动重新部署。

本地方式：

1. 在 `source/_posts/` 新建 Markdown 文件。
2. 图片放到 `source/images/`。
3. 在 front matter 中填写 `title`、`date`、`categories`、`index_img`。
4. 运行 `npm run build` 验证。

## 文档维护

- 当前架构、运行方式、环境变量和日报能力以本文件为准。
- `AGENTS.md` 提供跨编码代理的通用项目规则，`CLAUDE.md` 补充 Claude 专用约束和 skill 入口；二者职责不同、允许独立维护。`docs/workspace_conventions.md` 说明文件分类和命名。
- 完成的实施计划和一次性分析报告不长期保留；有复用价值的结论应并入本文件或对应维护文档。
- `docs/archive/` 只保留仍有兼容、迁移或排障价值的历史记录，阅读时以文件日期为边界。

## 迁移说明

本项目曾使用 `Astro + MongoDB API + public/admin.html` 架构。

2026-06-18 起迁移为 Hexo 静态博客：

- 线上公开 API 返回的 19 篇文章已迁移为 Markdown。
- 后台草稿未迁移。
- 旧 `/articles.html#article_id` 链接由 `source/articles.html` 兼容跳转到新文章地址。
- Twikoo 评论使用每篇文章的旧 `article_id` 作为 path 保留旧评论关联，现由 `scripts/twikoo-path.js` 读取 front-matter 的 `twikooPath` 实现（见「评论（Twikoo）」一节）。**改动或删除文章的 `twikooPath` / `old_id` 会直接断开历史评论。**
- 旧 Astro 前台、旧 MongoDB API 和静态后台不再作为运行入口保留；当前 `api/` 是后来建设的在线后台与日报状态接口。
- 历史迁移工具 `tools/export-articles-to-hexo.mjs` 已于 2026-07-28 删除。它会从早已不是内容真源的旧 API 整体重建并替换 `source/_posts/`，同时重新注入带内联样式的 HTML 和 legacy 评论块，留在仓库里只会把正文清洗成果一次性抹掉。内容真源现在是 `source/_posts/` 加经 `/admin/` 写入 GitHub 的提交；需要查阅该脚本请翻 git 历史。

详细决策见 `docs/archive/2026-06-18-hexo-fluid-migration.md`。

## 每日日报页（/news/）

`source/news/` 是独立的静态"每日新闻驾驶舱"页面，通过导航菜单"日报"访问（`/news/`）。公开页面与生成数据是纯静态文件，`_config.yml` 的 `skip_render: news/**` 保证 Hexo 原样拷贝、不经主题渲染；个人状态文件同时列入 Hexo `exclude` 与 `.vercelignore`，不会进入静态部署。

### 数据管线

- 主管线是 `news-pipeline/daily_news.py`：抓取（RSS / AI HOT / 逐源直连适配器）→ 跨日 URL 去重与同 URL 实质新增判定 → 预筛 → LLM 初步聚类、分类、五维打分 → 全量同日事件证据归并 → 多条事件凝聚度审计 → 代码合成最终分（含热榜 co-occurrence 公众热度加权）→ 精选与次级选位 → 同日读者可见归并、凝聚度重审、跨日实质新增门与重新选位的稳定循环 → 精选深加工与事实支撑审计 → 生成今日主线、事件追踪、深读推荐、今日论文（HF Daily Papers）、舆论观察、RSS 和搜索索引。最终分夹紧在 5-99：乘数叠加常把原始分推过 99，因此 99 是"顶格档"而非精确分，顶部多条并列 99 属预期、不是评分 bug（2026-07-23 定案，不改公式）。
- 精选展示标题以 30 字为生成软目标，语义完整优先，不按字符盲目截断。模型返回空标题或超过 120 字的异常标题时回退到完整主来源标题；公开 payload 的标题仍以现有来源输入上限 300 字做发布校验，超限报错而不是静默裁剪。该规则在 interim、shadow 和 active 三种客观性模式下保持一致。
- 改新闻源优先改 `news-pipeline/sources.yaml`；调评分、阈值、标签词表、事件追踪、深读、精选长叙述（`detail`）、RSS 和搜索保留窗口优先改 `news-pipeline/config.yaml`。
- **信源接入采用"逐源直连适配器"路线**（参考 AIHOT 的做法：RSS 优先、没 RSS 就直连公开接口/网页内嵌数据，不建万能适配层）。三类接法并存：①标准 RSS（`fetch_rss`）；②自建 RSSHub 实例（Vercel）转 RSS——当前用于科学网、澎湃热门、果壳、Anthropic news/engineering 和财联社·深度等已验证路由，`url` 写占位符 `{rsshub}/路由`，运行时由环境变量 `RSSHUB_BASE` + `RSSHUB_KEY` 拼真 URL（地址密钥不落公开仓库，`resolve_rsshub_sources`，主管线与 `deep_sources` 均支持；未配置则自动跳过）；③专用适配器——`fetch_aihot`（JSON API）、`fetch_thepaper_list`（澎湃频道页 `__NEXT_DATA__` 内嵌数据，各 `list_*` 频道同构可复用）、`fetch_weibo_hot`（genvisitor 访客握手，无需登录/浏览器）、`fetch_bilibili_hot`（公开接口）。**不再扩 RSSHub 路由、不上 Docker**。已关闭的信源线（原因见 `sources.yaml` 尾部终局结论注释）：微信公众号（需常驻中继+人肉续期）、知乎（无登录态全线 4xx）、中青报/界面（JS 壳站）、X 直连（AI 类经 AIHOT 二手接入），以及 2026-07-16 验收停用的 FT 中文网和第一财经。
- **新增信源前必须从 GitHub Actions 出口验证可达性，本地能取不算数**（2026-07-26 实证）：`*.substack.com` 在 Actions 出口被封——`importai` 连续 9 天 0 抓取而同一 URL 本地返回 HTTP 200；同为 Substack 出版物但走作者自有域名的 `interconnects.ai`、`latent.space`、`oneusefulthing.org`、`construction-physics.com` 在 CI 全部成功。因此 Substack 候选一律换自有域名（`importai` 已换 `jack-clark.net`、Noahpinion 用 `noahpinion.blog`），无自有域名者判死。另外两条同期踩坑：接入前先看 feed 最新一篇的日期，停更两三个月的源不进队列；对方 TLS 证书过期或标准 CA 包无法闭合信任链（如 `www.latepost.com`）都是硬阻塞，**不得靠关闭证书校验或私带信任锚绕过**。晚点专用适配器只跟进与配置入口同源、无内嵌凭据的 HTTP(S) 详情链接；列表页给出的跨域或非 Web URL 会被拒绝，不能把上游链接变成服务端任意地址访问入口。
- 主管线增加任何信源前，必须先用现有证据形成具体供给缺口假设：`rollout-evidence-v2` 的合格供给与入选结构、`source_health.json` 的抓取/参与评分/入选贡献，以及漏读记录。固定 14 个有效日窗口已随 ADR 0016 退役：证据必须按运行时指纹分开解读，样本是否充足由人根据当前问题判断，不拼接跨指纹计数。只有供给不足或来源集中假设成立时才手动跑 shadow，用单源高风险率、独立证据链和来源引用集中度确认；不为了凑齐证据无目的付费采样。数据与人工审查都支持后才可重议，不回填历史数据。
- 信源分为官方/事实源、分析源、舆论源，并有 T1 / T1.5 / T2 层级。纯舆论源（`source_type: opinion`）支撑的事件分数会封顶在当日有效精选阈值之下，只能进"更多资讯"，也不进入动态阈值账本；有事实源或分析源交叉佐证后才解除限制。
- 抓取健壮性：`fetch_rss`/`fetch_aihot` 统一走 `http_get`（指数退避重试），治 AIHOT 连接重置这类偶发失败——单次请求一挂整源归零。`max_per_source` 默认 18（削减 world/舆论刷屏源的 triage 噪音）；AIHOT 是 AI 深度独木、已精选噪音低，在 `fetch_aihot` 内单独放宽取量、不受该值压制。AI 一手供给以逐篇新闻站（The Decoder 等）为主，不用摘要型 newsletter（每期一条不适配事件聚类）。`source_health.json` 将抓取错误与窗口内零更新分开记录；2026-07-16 验收中，`ftcn` 连续 6 天抓取失败，`yicai` 上游头条接口停留在 2026-05-30，二者均已在 `sources.yaml` 停用。
- 精选采用按产出日等权的动态阈值：每个历史日先对非纯舆论事件最终分计算 nearest-rank P75，再取最近 14 个有效日值的中位数并钳制到 66-82；不足 5 日或账本异常时回退静态 68。五类各有 4 个保留席，优先取过线事件，不足时只从“有效阈值−8”以上补位；`pick_min: 8` 也遵守同一质量线，宁可少发。保留席不参与最终按分截断，精选最多 36 条，供给不足时少发；「更多资讯」仍最多 8 条。次级条目不跑深加工，摘要位只能回退到来源原文：中文原文照登，非中文原文一律留空（`readable_fallback_summary`，按中文字符占比 0.15 判定），不把没翻译的外语原句当成日报自己写的摘要。序列化与审计投影共用同一判定，历史数据不回填；理由与被否掉的翻译方案见 `docs/adr/0009-secondary-items-carry-no-written-summary.md`。可选 `max_per_category` 当前为空，但启用时优先于保留席。AI 与其他类目仍按分竞争，`TRIAGE_SYSTEM` 首轮未改。主题标签只允许来自 `config.yaml` 的 `topic_tags`。
- 同日事件归并使用事件标题、原始标题、摘要和来源作为证据，并要求模型结果恰好覆盖全部输入且索引不重复、不越界。全量事件按最多 40 条的有界基础批次复核；跨批候选优先取共享原始条目或规范 URL 的事件，其余必须共享至少 4 个低频标题/摘要键，再按强制候选、共享键数和稳定索引排序。URL 只代表报道文档而非事件身份，同一篇综合报道可以支撑多个不同事件，因此即使 URL 相同也只送审、不自动合并。初次归并与发布前复核在整次运行中共享最多 20 次模型调用；达到上限后停止付费审计，只合并共享同一原始条目的确定性重复，其余保留并告警。候选对、桥接批次、实际调用、延后批次和预算耗尽状态写入当日质量记录。第一层在评分前复核全部事件，第二层在精选与次级条目拟定后反复执行归并、凝聚度审计和重新选位，直到读者可见集合稳定；分数账本只记录最终结果。同一具体事件只保留一张卡，事实稿与分析稿并入其来源和观点，不同进展仍独立。
- 跨日实质新增门只审当前精选、次级和抑制后出现的新补位者：按同类目和稳定事件键从事件登记表最近 60 天内召回最多 6 条事件线，但只有严格早于产出日的历史 `pick-*` 能阻止首次精选，历史 `more-*`、仅在全部动态出现的报道和同日重跑已经写入的条目都不能。每条候选线优先通过 `item_ref` 回读历史日报证据；只有历史明确覆盖当前核心事实、同属一个事件且没有实质新增时才判为跨源复述。新结果、关键数字或影响范围变化、政策结论、正式更正，以及首次官方确认／否认改变可信状态都算实质新增；换来源、标题、背景解释、评论分析或重复基准结果不算。证据不足、类别或身份不确定、出现无法对齐的新事实、模型失败、结构非法、证据包过大或预算耗尽时一律保留候选并记降级。批次除条数上限外还有 64,000 字符的输入上限，避免多条长事件线把模型上下文撑爆。跨源复述仍在全量事件集中正常算分、回填全部动态并计入 `source_health.scored_events`，但不进精选、次级、`score_history.json`、事件登记或 `source_health.selected_events`。动态账本写入失败切换静态阈值后仍重跑同一稳定循环。连续性门只负责独立判定保留条目是否属于既有事件线，不复核被抑制条目；实质新增提示只能提高候选召回优先级，不能绕过连续性门。提示可以把 60 天窗口内的归档线送入连续性门，只有验证通过才重新激活。详见 ADR 0014。
- 可信度质量门分两层：同日事件归并后，所有含两个及以上原始条目的事件都会复核凝聚度；审计输出无效或调用失败时，该事件拆回单条、取消多源加成并把证据分降为中性值。精选深加工的模型响应只消费对象行，畸形行会被忽略并让对应事件保留基础内容；随后再核对 `context/watch/watch_detail/detail/claims` 是否由当前事件来源支撑。审计失败时保守删除全部扩展字段，只保留标题、摘要、来源、分类、状态、分数和时间等基础内容，避免未经复核的叙述进入日报。
- 面向读者的生成文字（精选 title/summary/context/detail 与今日主线）受 prompt 层"客观性规范"约束（2026-07-18 起）：只陈述可追溯事实，媒体的立场性定性必须显式归因（"X 报道称"）、不得写成事实，剥离情绪化措辞与无依据动机推断，禁止为"平衡"编造原文没有的对立观点；立场性判断优先进 `claims`（kind=analysis）。
- 精选深加工按字段分工生成：`summary` 写事实增量，`context` 一个位置承载两种前情——可信延续是轨迹生成的「来龙」，新事件是 enrich 抽取的「起因」；`detail` 是「现状」，只记录来源支持的事实过程、机制或传导链、带基准的数字、利益相关方变化与未决事实，不承接公共影响判断；`watch` 是不超过 90 字的短走向，只在全文材料档生成（摘要材料撑不起可观察路标，见 ADR 0020；跨天事件线的走向仍由轨迹阶段按事件线历史另行生成）；全文模式还可生成详情页专用的 `watch_detail`；`claims` 只承载需要显式归因的分析或不确定判断。新闻阅读顺序统一为「来龙／起因 → 现状 → 走向」。新日报不再生成、审计或序列化新闻 `why` 与历史 `significance`，RSS、卡片、详情页、周报新闻兜底和阅读估时均不消费它们，前端无条件忽略旧日报里的新闻 `why`；深读与论文的「为什么值得读」保持不变。兴趣画像仍用于精选排序、深读、论文、舆论观察和周综述，但不再传入新闻 enrich。起因可交出最多三条带来源索引的原文片段；逐条精确匹配只证明出处，全文客观性审计另行确认完整起因中的因果关系能由证据推出。任一片段非法或起因含未归因推测／动机语气时整段丢弃，拒绝数记在 `cause_evidence_rejected` / `cause_speculation_rejected`。详情走向硬上限 260 字，必须完整保留短走向的关键变量和可观察路标语义；轨迹生成与审计同时处理长短走向，但事件登记表、卡片、RSS、阅读估时和走向回对仍只保存或消费短走向。理由见 ADR 0003、ADR 0006 与 ADR 0015。
- **材料等级是每事件的，与发布模式无关（2026-08-16，ADR 0020）。** `detail` 按同一次 enrich 已有证据分级：一份归一化全文不少于 2000 字符，或两个独立且非重复来源各不少于 800 字符为「丰富材料」，目标 350–600 字、2–4 段；存在全文但未达门槛为「有限全文」，目标 180–350 字、1–3 段；只有 RSS／snippet 为「摘要材料」，安全短写且不设最低字数。全文材料档（抓到正文）`context` 约 80–180 字、硬上限 240 字，`detail` 硬上限 1200 字，截断走句边界，并生成走向；摘要材料档 `context` 硬上限 80 字、`detail` 800 字、**不生成走向**。`detail.max_chars: 1000` 不变。全文材料档 enrich 每批最多 3 个事件、序列化证据正文总量约 48,000 字以内，摘要材料档每批 6 个；单源最多 4,000 字、每事件最多 4 个来源。长字段超过软目标不截断；超过硬上限只做一次句子／段落边界缩写，仍越界或无法完整缩写就删除并记入质量统计。
- **`interim` 下哪些条目走全文材料档由 `detail.fulltext_top_n` 决定**（默认 8）：按分数降序取前 N 条抓正文，同分按标题定序。判据只能用分数——`track_events` 与 `write_brief` 都排在证据采集之后，采集时点拿不到可信延续和今日主线。**抓取失败的条目自动留在摘要材料档、不产生额外 token**，所以分层成本是上界不是估算（本机抓取成功率约 29%、CI 约 82%，本机跑管线大多退回摘要材料档）。`fulltext_top_n: 0` 表示一条正文都不抓、全部落摘要材料档；它**不等于**回到分层之前——摘要材料档不生成走向，而分层之前所有条目都生成走向再被审计删掉大半。全文材料档条目的事实支撑审计也拿正文：**生成看正文而审计只看摘要会造成结构性误杀**，把有正文支撑的内容判成无支撑并整段删除。
- **成本口径**：预算 ¥1/天 ≈ $0.14，`cost_guard.generate_warn_usd` 设在 0.12（先告警后超支）。2026-08-15 分层前基线为 104 次调用、入 341.5k token、出 33.0k、$0.0550/天；全文材料档每条约多 15k 字输入，8 条约 +$0.024，合计约 $0.079/天。供应商调价后按同一算式重算，只改 `fulltext_top_n` 一个数字。跑完在 Actions 日志的「LLM 用量结算」一行核对实际值。
- 踩坑：阶段B（enrich）分批发给模型，提示词里展示的是每条事件真实的 `picked` 下标，因此**回填时必须校验 `idx` 属于本批**，只判 `0 <= idx < len(picked)` 是不够的。放行本批以外的下标意味着一条新闻的返回可以覆盖另一条已经算好的全部读者字段——模型写错下标是这样，抓来的正文用提示注入诱导它写错下标也是这样。更麻烦的是下游 support 审计按事件自己的来源复核，覆盖的后果只表现为 `removed_fields` 无故上涨，查不到源头。越批次下标直接丢弃并记入 `enrich_out_of_batch_idx`（2026-07-29 修复）。**两档并存后批次不再连续，判据是集合成员而不是区间**（2026-08-16，ADR 0020）——判据更严，不更松。
- **公开路径当前只到这一层**：`config.yaml` 的 `objectivity.mode` 默认 `interim`，新闻正文只启用上述 prompt 规则和原有的 support-only 事实支撑审计；唯一例外是周综述在写入前始终使用有界日报证据自动初审、定向修复和复审。**正文取证自 2026-08-16 起在 `interim` 也运行，但只覆盖 `fulltext_top_n` 条精选**（ADR 0020）；独立证据链佐证、高风险单发布者佐证、新闻客观性定向修复/降级/降档仍然只在 shadow 或未来的 `active` 模式下运行；**`active` 尚未启用，线上验收尚未完成**。审计模型可用 `config.yaml` 的 `audit_llm` 段单独指定，留空则继承 `llm`。
- 完整模式的证据合同是 `evidence: {basis, publisher_count, independent_chain_count, degraded}`（`basis` 取 `fulltext|mixed|snippet`）；来源可带 `evidence_basis`/`evidence_chain`，claims 用 `sources` 标注归因，`degraded` 表示摘要退化或修复失败后的保守内容，高风险事件复审仍失败会从精选降到"更多资讯"。前端只在结构完全合法时渲染证据概览，旧数据静默降级。正文只是当次运行内存中的审计证据（每源上限 4000 字），不写入日/周报、feed、search、registry、profile、health 或 vocab 等任何数据文件；抓取器不登录、不执行页面脚本、不绕过付费墙，取不到就退回 RSS 摘要。
- **`active` 不再有既定启用路径**（2026-08-10，ADR 0016）。原先的前置条件是固定 45 条夹具三轮客观性门、同模型同价格的改动前后三轮配对成本门、7 天线上客观性 shadow 门、5 个有效日文字质量门和人工评审；这套「攒够天数再确认」的机制已退役，因为指纹每次改动都会清零计数，窗口不可达。`objectivity.mode` 永久保持 `interim`；夹具门与配对成本门降为可手动触发的质量探针（判据不变：调用数不得增加、三轮加权 token 成本不得高于基线，价格未知、截断、余额不足或运行不完整均按失败处理）。安全边界与标签接受集的决策见 `docs/adr/0005-objectivity-label-accepted-sets.md`。历史夹具证据：DeepSeek 曾于 2026-07-28 的 Run #30349424143 与 2026-08-06 从 `main@a135d84` 的 Run #31027819706 通过三轮门，但两者的运行时指纹此后都已被生产改动取代，只作历史参考。
- AI HOT 条目会带上其原生分类（模型/产品/论文/技巧）作为 `tag_hint`，在阶段 B 打标时优先入选，保证「研究论文」「技巧观点」这类内容不被大类淹没——前端现有子标签筛选即可单独筛出，无需改前端。
- 兴趣画像影响排序：`interest_profile.md` 非空时，管线对每个事件打"兴趣契合分"换算成分数乘数，幅度由 `config.yaml` 的 `scoring.fit_span` 控制（默认 ±0.30，画像明确不关注的事件被压低、更关注的被抬高）。画像以手动维护 + 低频人工校准为准、蒸馏为辅：页面反馈按钮保留，但反馈输入长期近零属预期状态、不是待修 bug（2026-07-23 定案）。
- 画像含手写的「## 学习参考系」段（长期学习方向/当前能力栈/希望积累的判断力/资讯转化偏好）。该段每晚蒸馏时由 `split_section` 摘出、绕过 LLM、原样贴回（`update_profile`），不会被自动改写冲掉；旧的「## 我的处境」段仍会被兼容保护。它继续参与兴趣契合分及精选、深读、论文、舆论观察和周综述的个性化，不进入单条新闻 enrich。
- 长尾去噪：预筛除丢弃硬垃圾外，还会给"软边角料"（体育赛果、明星八卦、猎奇轶闻、日抛热点）打标；整条来源都是软标记的事件不进"更多资讯"（不影响精选）。"更多资讯"条数由 `secondary_count` 控制（默认 8，真·漏网提醒）。

### 自动运行与本地运行

- GitHub Actions（`.github/workflows/daily-news.yml`）每天 UTC 23:00（北京 07:00 左右）以 `publish` 模式运行，校验通过后自动 commit + push `source/news/data/`，触发 Vercel 部署上线。这是"严禁自动 push"规则的唯一例外，详见 `CLAUDE.md`。例外的边界在工作流里画死：commit 步骤额外要求 `github.ref == 'refs/heads/main'`，并显式 `git push origin HEAD:main`——否则从别的分支手动 dispatch 一次 `publish` 就会把数据推到那条分支上（2026-07-29 收紧）。手动 `Run workflow` 默认是 `validate + shadow_mode:auto`：先把线上数据复制到 runner 临时目录，只运行 generate 并上传临时 artifact，不 commit/push、也不更新 Issue #15；需要连 shadow 验证时显式选 `force`，`skip` 则明确跳过。**`auto` 现在一律不跑 shadow**（含定时与显式 `publish`）——客观性 shadow 已按累计样本封顶，`shadow_status` 恒返回 `accepted`，客观性与信源计数按既有链路冻结为 `neutral`；想采样必须手动选 `force`。理由见 `docs/adr/0016-retire-five-gate-rollout-acceptance.md`：原先的 7 日／14 日门槛是唯一能关停这项付费运行的开关，而指纹每变一次就清零计数，门槛因此不可达。**`shadow-status` 刻意不做任何网络请求、不要 token、不声明 `issues: read`**：判定已是常量，读 Issue 只可能让这一步失败，而 `shadow-policy` 把非零退出当作「状态未知」并 fail-open 去跑一遍付费 shadow——一次限流就会为一个毫无疑问的结论买单十分钟管线。同理，`main()` 在回答 `shadow-status` 前不构造 `GitHubClient`，否则缺 `GITHUB_TOKEN` 或 `GITHUB_REPOSITORY` 也会触发同一条 fail-open 路径。同一 publish workflow 随后运行云端 `rollout-review`，幂等更新台账 issue；完整 `rollout-report.json` 另存为保留 14 天的 Actions artifact。
- GitHub 仓库已启用 Dependabot 漏洞告警与 Secret scanning push protection，并在 Actions 权限层强制第三方 action 使用完整 commit SHA；工作流中的现有 `uses:` 均符合该约束。Dependabot 自动安全更新仍关闭，避免未经人工确认自动创建 PR；`main` 仍不设分支保护，以兼容日报 workflow 和在线后台的既有直写合同。调整这些策略前必须同时评估两条写入路径，不能只按普通应用仓库套用默认保护。
- LLM 配置是 `config.yaml` 的命名 provider：`llm.active_provider: deepseek` 为生产默认，继续显式关闭 V4 thinking；不做自动 provider 切换。两把 key 分别存于仓库 Secrets `STEPFUN_API_KEY` / `DEEPSEEK_API_KEY`，绝不进代码。StepFun `step-explore` 的 Anthropic Messages `/v1/messages` 适配与测试继续保留，但只供人工实验：Run #30346999214 在正常新闻阶段 A 第 2 批触发 HTTP 451 `censorship_blocked`，因此不得作为生产回退。自建 RSSHub 源另需 `RSSHUB_BASE`、`RSSHUB_KEY`。OpenAI 兼容 SDK 的内建重试保持关闭，实际重试次数由管线的 `max_retries` 单独控制；provider 的 `max_tokens` 与连接/读取超时会原样进入请求，避免隐式重试绕过同次运行的预算和失败口径。
- 模型输出契约一律是**对象包裹** `{"<key>": [...]}`，提示词必须显式写明「只有一个也放进数组」，归一化统一走 `_model_rows(raw, key)`（主契约优先，裸数组兼容回退，单对象按单元素处理，其余判为整体不可用）。裸数组契约让「一个元素」和「整个结果」在 JSON 里不可区分，模型在单元素答案上会丢掉数组外壳：阶段A 因此被整跑打挂（2026-08-01，Run #30674149780，当天无日报），而阶段B、深读、论文、舆论观察中同一招只会**静默变空**，前三者当时连日志都没有。形状非法时降级不中止，且降级方向必须不丢内容——阶段A 整批不可用时每条降级为单条事件，由全量同日归并接住重复。另配 `batch_spans`：尾批不足 10 条并入前一批（历史尾批都 ≥ 13，出事那次是 2），输入太少会显著抬高单元素答案的概率。`triage_invalid_rows` / `triage_fallback_batches` / `model_unusable_responses` 只做诊断、不参与验收门。`MERGE_SYSTEM` 与 `VOCAB_*` 仍是裸数组，因生产已无调用者/功能停用而未改造，重新启用前必须先切契约。新增调用点照此办理，理由与被否掉的方案见 `docs/adr/0012-model-shape-failures-degrade-not-abort.md`。
- Vercel 生产项目固定为 `my-blog`，持有 `aoiblog.top`、`www.aoiblog.top` 与 `api.aoiblog.top`；仓库不应再把同一根目录连接到第二个 Vercel 项目。项目已启用 Vercel Authentication 的 Standard Protection，保护预览、历史部署与 Vercel 生成域名，生产域名仍公开。这些项目、域名与保护关系属于 Vercel 控制面配置，代码与 DNS 不能单独证明归属，维护时必须到对应项目的 Settings 中核对。
- 数据推上 `main` 不等于线上能读到。2026-08-01 机器人提交 `2623d4c` 后 Vercel 没有收到 webhook，日报在 `main` 上完好却一整天没上线，且完全静默（`vercel.json` 无 `ignoreCommand`、`.vercelignore` 只排除个人状态文件，已排除仓库侧原因）。`daily-news.yml` 因此新增独立 job `deploy-check`：只在确实提交了数据时运行，轮询规范生产主域 `www.aoiblog.top` 上的 `manifest.js` 最长 10 分钟；未上线则调用 Secret `VERCEL_DEPLOY_HOOK` 自愈并再等一轮，仍失败就让该 job 显红。若 Secret 未配置且首轮未上线，该 job 会输出诊断并失败，不会假装已完成或具备自愈能力。
- 2026-08-02 首次定时运行 `deploy-check` 时，探测地址误写成会 307 跳转到 `www` 的裸域，curl 又刻意不跟随重定向；响应体不含目标日期，导致两轮探测必然失败并白触发一次部署。线上健康探测必须直接使用规范主域，主域发生重定向应作为合同漂移显式失败；工作流中的线上 URL 合入前要同时验证状态码、重定向和响应内容，不能只依赖 `npm run build`。失败诊断记录 HTTP、重定向、关键缓存头和有限响应预览，只能定位探测层，不能替代 Vercel 内部构建日志。
- 发布步骤启用了 Actions 默认的 `bash -e -o pipefail`，不得用 `grep | head` 之类会由下游提前关闭管道的写法提取 manifest 日期；否则 push 已成功后仍可能因上游 SIGPIPE 中止，来不及写 `committed` / `published_date`，使 `deploy-check` 被静默跳过。发布日期必须按 manifest 赋值合同在 push 前解析，合同异常不能留下远端半完成状态。**`VERCEL_DEPLOY_HOOK` 必须对应 `my-blog` 项目中 `main` 分支的 `daily-news` Deploy Hook**；Hook 目标与 GitHub Secret 值都不在代码中，必须分别到 Vercel Settings → Git 与 GitHub Actions Secrets 核对。**`deploy-check` 刻意不进 `rollout-review` 的 `needs`**——`publication` 取自 `generate` 的结果，把部署校验塞进 `generate` 会让 Vercel 抖动被误判成当天发布失败、台账五项计数归零。Vercel 界面上对旧 commit 点 Redeploy 也解决不了 webhook 漏触发，因为它重建的是那个 commit 的树。
- 成本计量：每次运行结束会在日志里按 provider / model / 阶段列出调用次数、输入/缓存命中/输出 token 与折算美元，公开运行把合计写进 `quality-health.json`（`llm_calls` / `llm_input_tokens` / `llm_cached_input_tokens` / `llm_output_tokens` / `llm_cost_usd` / `llm_cost_known`），shadow 合计写进临时 summary。每次实际请求只要返回了 usage（包括随后重试的失败响应）就计入账本；OpenAI 兼容响应同时兼容标准的 `prompt_tokens_details.cached_tokens` 与旧缓存字段，缓存 token 不得超过总输入。相同 provider/model/阶段出现冲突价格、价格缺字段/为负数或非有限值时，成本必须标为 unknown，不能沿用合并顺序中的任一价格；持久化只接受上述 `llm_*` 白名单字段。周综述的生成和审计共用最多 100 条、按日期均衡的证据投影，只含类目、标题、摘要、最近三条历史与走向；审计证据只序列化一次，主题和回收项另传引用作用域，局部失败的修复与复审只携带失败部分。周综述费用计入公开生成账单，shadow 不再重复生成或审计周综述，也不依赖供应商缓存命中压低账面费用。新闻 `why` 移除后的零增量成本合同另由静态回归锁定阶段数、45 条批量计划、单次证据输入上限和绝对读者字段字符预算，并由三轮配对门及 5 个有效 shadow 日的每条入审精选标准化费用复核。配对门只计 enrich 与内容 audit/repair/fallback，不把独立 judge 计入日报成本；同时保留实际缓存折扣后的美元数，并以“全部输入均按 cache miss 计价”的 `llm_weighted_token_cost_usd` 决定是否通过，避免先运行的基线替后运行的候选预热缓存。调用数或标准化费用高于同模型同价格基线，以及价格未知、截断、余额／配额错误或三轮不完整，均停止上线；不减少审计、不增加预算、不切换供应商。新闻量、网络重试与周报任务的正常日间波动单独记录。`cost_guard` 默认在正式生成超过 `$0.06`、shadow 超过 `$0.09` 时发非阻断告警；它们是异常提示，不会为了省钱中止日报。跨日实质新增门默认每批 20 条、整次最多 8 次模型调用（`cross_source_novelty_batch_size` / `cross_source_novelty_max_calls`），结构非法只在预算内重试一次，随后 fail-open。`step-explore` 的 0 只表示当前账号免费授权；未知模型写 `llm_cost_usd: null` 与 `llm_cost_known: false`，不伪装成免费。成本字段不进 `daily/<date>.js`。
- 本地手动补跑（PowerShell）：先运行 `py -3.12 -m pip install --require-hashes -r news-pipeline/requirements.txt`，再按活动 provider 设置 `$env:STEPFUN_API_KEY="你的key"` 或 `$env:DEEPSEEK_API_KEY="你的key"`，执行 `py -3.12 news-pipeline/daily_news.py`。默认产物写到 `news-pipeline/data/`（已 gitignore）；验收时应把 `$env:DATA_DIR` 指向仓库外临时目录，绝不直接写 `source/news/data`。需要抓自建 RSSHub 源时再设置 RSSHub 两个环境变量。
- 两个只在 CI 里设置的可选环境变量，用于把验收证据交给台账，**本地不设即完全不写文件**，不影响日报产出：`ROLLOUT_EVIDENCE_PATH` 让 `generate` 落盘 `rollout-evidence-v2`，包含选材/轨迹聚合指标、每日 enrich 抽样 id，以及供轨迹 Judge 和 enrich 人工复核使用的有界案例；`SHADOW_SUMMARY_PATH` 让 shadow 落盘客观性聚合指标 JSON。v2 案例只保留白名单公开字段、每例最多 5 条来源标题、每条最多 400 字证据片段和适用的已验证历史，不含 URL 字段、抓取正文、环境值或密钥；抽样 id 与 enrich 案例必须一一对应。shadow summary 还记录三档证据条目数、最终审计后 `detail` 字数中位数，以及丰富材料达到 300 字且至少两段的数量和比例。两者都写到 `runner.temp` / `/tmp` 并作为保留 3 天的 artifact 上传，由 `rollout-review` 下载后喂给 `issue_ledger.py`，都不进 `source/news/data/`。
- 客观性 shadow：`python news-pipeline/daily_news.py --objectivity-shadow`。它先把当前 `DATA_DIR`（含 feedback/profile/registry/weekly 等状态）整树复制到临时快照，读写只发生在快照里，正常返回、提前返回、异常和校验失败都会还原环境并删除快照；输出只有不含正文和密钥的聚合指标及本次 LLM 用量。公开文章仍在父进程内完成 DNS 固定、TLS/SSRF 校验、流式限量和超时控制，静态 HTML 的 `trafilatura`/`lxml` 解析则由一次性子进程执行；子进程原生崩溃或超时只使该来源按既有 RSS 摘要合同降级，不能破坏长驻管线进程。周综述已经在公开生成写入前完成自动审修，shadow 只复用 artifact 中的结果，明确不调用周综述生成、初审、修复或复审。Actions 的 shadow 使用 generate 上传的同一份数据 artifact，限时 60 分钟；手动 validate 只有 `shadow_mode:force` 才运行，publish/cron 下仍为只读非阻断、不 commit/push。两项依赖门完成后，工作流用 `accepted` 表示合法跳过：选材把 shadow 依赖视为已满足，客观性和信源计数冻结而非失败。
- 客观性模型验收：`python news-pipeline/objectivity_eval.py`。语料固定为仓库内 45 条夹具（`news-pipeline/fixtures/`，受 canonical JSON 的 SHA-256 约束，不能用 CLI 换），每条先走生产 `enrich` 与完整 audit/repair/fallback，再交独立 judge 评分；生成模型和 judge 都拿不到单条夹具的分类、预期标签和验收阈值。只有活动 provider 的凭证存在才会连跑三轮，并按最差一轮决定退出码；活动 provider 首次 publish 前必须通过残留红线 0、标签一致性 ≥90%、归因 ≥95%、结构 100% 四门。Actions 的 `Objectivity Acceptance` 仅允许从 `main` 手动触发：它从当前提交的父提交抽取旧 `daily_news.py` 跑三轮成本基线，再用当前实现跑三轮候选，强制两边使用 shadow 内容合同、相同当前配置与独立 judge，并执行上述配对成本门。工作流使用活动 provider Secret，只读运行并上传保留 14 天的聚合报告，不提交任何数据。由于基线固定为当前提交的父提交，功能提交后应立即触发；后续无关提交上的重跑不能替代本次功能基线证据。
- 顶层 Python 依赖维护在 `news-pipeline/requirements.in`，使用与 Actions 一致的 Python 3.12 在仓库根目录运行 `py -3.12 -m piptools compile --generate-hashes --resolver=backtracking --output-file news-pipeline/requirements.txt news-pipeline/requirements.in`。日报与 rollout 相关 Actions 固定为 `ubuntu-24.04` + CPython `3.12.13`；升级 runner 或 Python 补丁版本时必须同步验证并更新 workflow。`sgmllib3k` 使用 `news-pipeline/vendor/` 内受控 wheel，生成后必须保持锁文件中的仓库相对路径并运行一次 `pip install --dry-run --require-hashes`，不能退回会动态下载构建工具的源码包。
- 排查信源抓取时先跑 `py -3.12 news-pipeline/daily_news.py --dry-run`，只抓取、不调 LLM。
- 踩坑：自建 RSSHub 的 `ACCESS_KEY` 是拼在 query 里的，而 requests 的异常字符串会带上整条 URL（或裸主机名）。抓取失败日志一律经 `redact()` 输出，同时盖掉 `key=` 的值、`RSSHUB_BASE` 的完整地址和它的裸主机名。**不能把 GitHub 的 secret 自动打码当作防线**——值一旦被转义或截断，打码就失效，而这是公开仓库的公开日志（2026-07-29 修复）。
- 踩坑：**`RSSHUB_BASE` 必须带 `http(s)://` 协议前缀**（结尾斜杠可有可无，会被 `rstrip`）。原先的守卫只判空——未配置时跳过并告警，配错时却把 `{rsshub}` 替换成缺协议的裸地址直接喂进 requests，报的是 `Invalid URL ... No scheme supplied`。于是「配错了」伪装成「抓取失败」，排查方向差一截：2026-08-20 迁仓重配 secret 漏了前缀，六个自建源当天全灭，丢约 96 条候选（`cls-depth` 正常日贡献 7 条精选）。现在 `resolve_rsshub_sources` 把缺前缀的 base 按未配置处理并说明原因，**base 是密钥，值不进日志**。
- 若通过 `publish.blog_dir` 把独立数据目录同步到博客，管线会完整镜像整个 `data/` 树并清理目标中的陈旧派生文件；切换使用临时目录和备份，失败时恢复旧目录，后续运行也会先恢复遗留备份。只有日报成功生成后才会进入发布同步。
- 发布闸门会解析所有读者可见的来源和深读 URL，只接受带主机名、无空白且端口可解析的 HTTP(S) 地址；只检查 `http://` / `https://` 前缀不够，`https://`、带空格的主机和畸形端口都必须拒绝。生成 RSS 时还会重新校验历史日报：无效条目的 `<link>` 回退到 `/news/`，无效来源不会进入 description 的链接列表，避免旧数据绕过新闸门。

#### 选材与可信轨迹并行上线门

- 每次登记表阶段输出一行「轨迹健康」，稳定记录候选匹配、连续性通过/拒绝、被排除的历史行、整条生成回退、审计字段/claim 回退，以及最终公开走向数/精选数和覆盖率。连续性响应缺失或非法时按拒绝计数，其历史全部计入过滤；生成回退按条目计，审计回退按未采用的字段或 claim 计。
- 离线冒烟夹具是 `news-pipeline/fixtures/trajectory_rollout.json`，固定包含一条可信延续、一条污染历史和一条缺少精确 `item_ref` 的旧行；运行 `py -3.12 news-pipeline/tests/test_trajectory_rollout.py` 不联网、不依赖额外测试包，也不写 `source/news/data/`。完整 `pytest` 回归会同时执行这组夹具。
- 选材改革与可信轨迹已随 PR #16 于 2026-07-22 合并公开。**「攒够 N 个有效日就解锁」的五门上线验收已于 2026-08-10 退役，见 `docs/adr/0016-retire-five-gate-rollout-acceptance.md`**：指纹覆盖 `daily_news.py`、`rollout_validation.py`、`article_extractor.py`、`requirements.txt` 加运行环境投影，退役前改这四个文件里的任何一个都会重置全部五项计数（含所谓「累计型」的 enrich 与信源指标），而管线平均每 1-3 天就有一次改动，最长的 14 日窗口因此不可达。台账继续每日记录作为质量仪表盘，但计数不再通往任何开关，也不再输出最终确认结论。**指纹重置本身已于 2026-08-16 一并移除**（`docs/adr/0019-ledger-streaks-are-cumulative.md`）：既然计数不再通往开关，仪表盘要读的是趋势而不是连续性，重置只剩破坏信息一个效果。**文档不钉指纹值，当前有效值只从台账 issue 最新一行的 `fingerprints.runtime` 读**。逐项计数是易变运行状态，本文件不复制快照，**只以台账 issue 的幂等记录为准**；计数现在按全部历史重算，因此跨指纹的日数可以连起来读——注意旧评论里存下的快照是按当时的重置规则算的，与今天重算出的数字不一致，以重算值为准。轨迹每天的全量初验复用 `audit_llm` 连接/模型配置并强制 `temperature: 0`；模型、schema 或评审基础设施异常一律记 `needs_review`，留给人工判断，不猜测通过。
- **台账 issue 号是部署配置，不是代码常量**（2026-08-20，ADR 0021）。号码来自 GitHub repo variable `LEDGER_ISSUE`，经 workflow 步骤级 `env:` 传入 `issue_ledger.py`；`--issue` 仅作人工排障时的显式覆盖。**没有回退默认值**：缺失或非法一律非零退出——台账是 append-only 且每天无人值守地跑，一个看似合理的错号会把当日记录静默写进别的 issue，发现得晚且撤不干净。**`shadow-status` 是刻意的例外**——它不接 `--issue`、不读 `LEDGER_ISSUE`，号码解析放在它提前返回之后，因此结构上到不了解析器；给它新增任何失败可能都会触发下游 fail-open 的付费 shadow 运行（见本节上文与 ADR 0016）。看到这处不一致不要改成一致。
- **旧台账历史已随 2026-08-20 的仓库迁移丢失。**原账号被停用后旧仓库 404/403，原 Issue #15 的逐日评论无法导出；新仓库的台账从空开始，`compute_streaks` 从零重算，`fingerprints.runtime` 在下一次成功 publish 前没有当前值。按 ADR 0016 台账已不通往任何开关，因此损失的是趋势可读性，没有流程被阻塞。
- 台账 issue 是**五项质量指标的唯一自动每日台账**（台账 state 版本 `issue-ledger-v2`）。同一北京日期的重跑只幂等更新当日记录，不多算一天；当日任一次发布失败，即使后续重跑成功，当日所有项仍都按失败处理。非发布失败时，`pass` 让对应计数 +1，`neutral` / `needs_review` 冻结该项当前计数；`fail` 只清零**连续型**项（选材、轨迹、客观性 shadow），**累计型**项（enrich、信源指标）不清零已攒的有效日，因为缺一天数据不等于观察结果变坏。**指纹变化不再清零任何一类**（2026-08-16，ADR 0019）：发布失败是唯一的清零来源。
- 云端 `rollout-review` 现在一次性给出五项判定，数据来源分别是：选材/轨迹取临时 rollout artifact；客观性 shadow 取 `shadow` job 新落盘的 `shadow-summary` artifact；enrich 安全指标取已提交的 `source/news/data/quality-health.json`；信源指标取已提交的 `source/news/data/source_health.json`。缺任一输入时只记 `needs_review` / `neutral`，绝不推断通过；证据还必须是类型正确、数值有限且内部计数一致的结构，畸形 JSON 值同样按保守状态处理，不能误判为通过。
- enrich 分成两半：机械的 `removed_fields / enrichment_audited_events` 安全指标由台账自动判（超过基线 1.2 倍即 `fail`），其中分母是实际进入事实支撑/客观性审计的读者可见事件数，不能用多来源事件的凝聚度审计数 `audited_events` 代替。历史 interim 记录会从同日 `daily/<date>.js` 的 `stats.pick_count` 补全分母；不足三个有效新口径记录时只报 `needs_review`。文字质量检查只能人工判，**已改为随时抽查、不再累计连续日**（原 5 日门的真实阻塞是人工回填从未执行，与指纹无关）。管线仍每天按日期确定性地从每个非空类目抽 1 条、最多 5 条；`rollout-evidence-v2` 在内部 artifact 的 `enrich_review_cases` 保存这些条目的最终公开字段、每例最多 5 条来源标题和每条至多 400 字证据片段，并要求与抽样 id 一一对应。超过来源上限的轨迹或 enrich 案例都必须在调用 Judge 前拒绝。原有 `review_cases` 仍只供轨迹 Judge 使用。想回填人工判断时仍可用 `Rollout Manual Review`，单条缺陷写入 `samples_passed` / `samples_total`；证据不完整时必须提交 `neutral` 且不得提交样本计数。v1 历史 artifact 不回写。
- 45 条客观性夹具由独立的手动 `Objectivity Acceptance` workflow 执行（一次 dispatch 内跑满三轮，取三轮最差值看**四项**：残留红线 0 / 标签一致性 ≥90% / 归因 ≥95% / 结构 100%），不属于每日自动台账。**按 ADR 0016 它已降为可手动触发的质量探针，不再是切换 `active` 的前置门**——`active` 不再有既定启用路径。红线只计最终候选中残留的违规；标签一致性测的是 Judge 校准，命中夹具的接受集即算一致；归因与标签均只在结构有效条目上计算，结构失败不再连带扣分。同一 workflow 内的配对成本门同样降为诊断：2026-08-09 的 Run #31294396802（`c9e6874`）质量四项全过但成本门失败（内容调用 300 → 316、标准化费用 `$0.04210262` → `$0.04326518`，截断/终止/计费错误均为 0），保留为历史诊断证据；同期公开日报实际调用数 121 → 109 → 96 呈下降，日常成本改由 `cost_guard` 的非阻断告警兜底。
- `Rollout Heartbeat`（`.github/workflows/rollout-heartbeat.yml`，每日北京 02:00）只做缺口检测：前一北京日期若完全没有台账评论，补一条 `neutral` 缺口行并告警。缺口行**冻结**所有计数（既不计入也不清零），因为没跑出日报不等于日报跑坏了。该 workflow 不调用 LLM、不写仓库内容、不关闭任何 Issue。
- Judge 返回额外顶层字段、缺行、重复行、越界编号或非法字段时，轨迹初验会以同一输入重试一次；客观性固定夹具会把非法批次递归拆小，单条仍非法时再重试一次，并用每轮 60 次调用预算限制最坏耗时。重试只修复输出结构，不改变证据、标签、红线或阈值。轨迹的确定性失败优先于 `needs_review`；走向低于 80% 时，只有未知项全部转好后仍可能达标才允许人工复核，否则直接失败。
- 台账日期在三个子命令（`sync` / `manual-review` / `heartbeat`）里都按真实日历日期强校验，非 `YYYY-MM-DD` 直接退出。**这不是格式洁癖**：日期会被插进台账条目的 HTML 注释标记，而该评论以 Actions bot 身份发布、被台账当作可信状态读回；未校验的日期能提前闭合注释并注入伪造的 state 块。`rollout-heartbeat.yml` 在写 `GITHUB_OUTPUT` 前另做一次同样的校验，避免换行伪造后续 step 输出。放宽这条校验等于放弃台账的防篡改性。
- 确需人工裁决 `needs_review` 时，使用只读证据 artifact 复核后手动触发 `Rollout Manual Review`。该工作流只能由 Actions bot 修改同一日期的可信台账，只接受与最新 run ID 和 attempt 一致的 `pass` / `fail` / `neutral`，不能覆盖发布失败或自动确定性结论；公开 Issue 仅记录固定的 `artifact_reviewed` 原因码，不接收或保存自由文本复核说明；后续新 run 或 rerun 会自动使旧人工结论失效。
- **共享运行时指纹只逐日记录作诊断，不再重置任何计数**（2026-08-16，ADR 0019）。它仍每天计算并写进台账评论，覆盖生产 Python 文件、`requirements.txt`、Python 完整版本与实现、runner OS/架构以及 workflow 显式维护的 `RUNTIME_ENVIRONMENT_EPOCH`，不读取 Secret。仅 workflow/底层环境发生语义变化而文件与版本号不变时递增 epoch。轨迹 UI 指纹同理，只记录不重置。**唯一仍按运行时变更重启的是 `window_start()`**，它喂 `evaluate_enrich` 的基线比较，那里「改动前后的数据不能混」确实成立——它和逐门计数是两个不同的 sink，不是同一个 sink 的两条入口。自动初验失败、`needs_review` 或台账写入异常只在 Actions/Issue 告警，不阻断日报发布、不改配置、不自动回滚。计数达到任何值都不再触发结论；任何情况下都不自动关闭台账 issue。
- 想人工复核轨迹质量时，检查全部可信延续并抽查若干条覆盖不同类目的一次性精选：错误串线、无依据历史/判断、错误延续跳转和主管线发布失败都应为 0。对已展示 `watch` 做质量抽样，至少 80% 同时包含具体关键变量和可观察路标；另看走向覆盖率、轨迹回退率和历史行过滤率，不为提高覆盖率放宽连续性或审计门。
- 深读源队列现行安排见 `docs/news_source_roadmap.md`：阮一峰和 Noahpinion 已通过人工抽查并保留；Marginal Revolution 曾因旧 `topic_filter: finance` 放行非财经文章而停用，确定性闸门进入 `main` 且 Actions validate Run #32629399798 通过后已于 2026-08-23 重新启用，启用后的抓取与栏目数据继续由 `deep_health.json` 复核。晚点虽已续期叶子证书，项目锁定的标准 CA 包仍无法闭合其新 TLS 信任链，继续停用；Apricitas 与 Kyla 因作者停更判死销账。
- 是否回滚由人工根据当日证据决定。轨迹回滚时把 `news-pipeline/config.yaml` 的 `trajectory.enabled` 改为 `false` 后重新生成：连续性验证和登记表兼容更新仍保留，但跳过轨迹生成，公开 payload 标记关闭并移除来龙、走向与延续投影。恢复时改回 `true`；`events.json` 的 v2 可选字段无需迁移或回滚，既有日报数据也不重写。选材参数回退时设置 `pick_dynamic.enabled: false`、`pick_max: 24`、`min_per_category: 2`；保留“保留席不被最终截断”和统一质量下限两个正确性修复，因此这是参数回退，不是恢复旧算法，账本无需迁移。

### 线上数据产物

`source/news/data/` 是线上数据目录，大多数文件由管线或后台 API 创建，不应手工改写，除非下方明确允许。

- `daily/YYYY-MM-DD.js`：每日页面数据。顶层 `quality` 记录审计事件数、拆分数、删除字段数（含 `removed_field_counts` / `removed_field_reasons` 两维分项）、跨日重复数、重大更新数、更新判定失败数、同日事件复核数（`duplicate_audited_events`）、合并数（`same_day_duplicates_merged`）、失败数（`duplicate_audit_failures`）和是否发生降级；同日归并成本护栏另记录候选对数、桥接批次数、实际模型调用数、延后批次数和预算耗尽状态（`same_day_candidate_pairs` / `same_day_bridge_batches` / `same_day_reconcile_calls` / `same_day_deferred_batches` / `same_day_budget_exhausted`）。旧数据缺少这些同日归并字段时继续兼容。`trajectory_enabled` 是当日轨迹展示开关；`themes` 为"今日主线"（2-3 条，每条含 `member_ids` 引用当日 `pick-N`/`more-N` 条目，可跨精选与更多资讯）。每条精选还可带 `context`（来龙／起因）、`detail`（现状）、`watch`（短走向）、`watch_detail`（详情走向）和 `claims`（0-4 条需归因的分析或不确定判断，形如 `{text, kind: analysis|uncertain, sources: [来源名]}`，可缺省或为空；读取端继续兼容旧数据的 `kind: fact`）；详情页优先显示 `watch_detail`，旧数据或字段缺失时回退到 `watch`。同 URL 出现实质信息增量时还会带 `is_update: true` 与 `first_seen`，页面明确标注“重大更新”。这些扩展字段只有通过事实支撑审计才会保留。深读条目带 `key_points`（≤3 条）/`audience`/`takeaway`，并可带 `content_type: reporting|analysis|opinion`；非法值或历史数据缺失时前端省略标签。论文条目带 `contribution`/`evidence`/`limitations`/`takeaway`，供详情页渲染。旧数据缺少新字段时前端静默降级。
- `manifest.js`：日报日期清单。
- `quality-health.json`：滚动保留最近 90 天的日报可信度审计统计，并汇总审计事件数、拆分数与拆分率，用于观察错误聚类趋势；`enrichment_audited_events` 单独记录 enrich 内容审计分母，不能用凝聚度审计的 `audited_events` 代替。质量记录缺少 `removed_field_counts_version` 时按 v1 读取，允许旧 `significance` 键；v2 继续兼容含 `why` 的旧分项，新记录写 v3，`removed_field_counts` 只按 `context`/`watch`/`watch_detail`/`detail`/`claims` 分，`removed_field_reasons` 仍含 `generation_invalid`，用于记录硬上限缩写失败。两个分项各自之和必须等于 `removed_fields`，对不上直接阻断发布；历史记录不回写。每日记录同时保留上述同日归并预算指标、当次公开运行的 LLM 用量与折算成本（`llm_*` 字段，不含 shadow 运行），以及可选的跨日实质新增诊断：候选数、实质新增数、跨源复述数、失败数、调用数、延后数和预算耗尽状态（`cross_source_novelty_candidates` / `cross_source_material_additions` / `cross_source_restatements` / `cross_source_novelty_failures` / `cross_source_novelty_calls` / `cross_source_novelty_deferred` / `cross_source_novelty_budget_exhausted`）。这些新指标首版只用于日志和排障，不进入 `daily/*.js` 的公开 `quality`，也不增加 rollout 阻断阈值。同日重跑会覆盖当日记录。
- `weekly-health.json`：周综述自动审修状态（v1），最近 26 周按周键记录 `pending/passed/failed/exhausted`、已消耗尝试次数、最后尝试日期、非敏感原因码和审计合同指纹，不保存周综述正文或模型输出。材料不足且尚未调用模型时保持 `pending`、不消耗次数；生成或审修失败最多跨 3 个自然日自动重试，合同或证据投影改变后指纹变化会重置该周预算。
- `source_health.json`：信源健康度，滚动保留 14 天；保留 `count/error` 区分抓取失败与窗口内无新文章，并记录逐源 `scored_events/selected_events`。某源连续 3 天抓取失败时在 Actions 输出 warning。
- `score_history.json`：动态精选线内部账本（v1），按日期保存非纯舆论且通过跨日实质新增门的最终分，同日重跑覆盖并保留最近 30 个产出日。阈值只读取当天之前的数据；账本损坏或写入失败会 warning 并回退静态线，再用剩余跨日审计预算重新执行选位稳定循环，原子写入不会遗留临时文件。
- `events.json`：跨天事件登记表（v2，兼容读取 v1）。登记表保留的全部 60 天事件线供跨日实质新增门召回，但只有历史精选能阻止跨源复述再次入选；之后管线只把保留的今日精选与近 14 天活跃事件做候选匹配，再用独立连续性门同时核对具体事件主线、最近可信进展，并逐行验证最近 7 条历史。跨日实质新增门给出的事件线提示只提高候选优先级，仍必须经过连续性门；被抑制的跨源复述不进入连续性门或登记表。同类目本身不构成延续，模型声称匹配最近进展时最新历史行也必须验证通过。只有验证通过的旧行参与公开 `day_count/history`，并进入独立批量轨迹生成和轨迹审计；审计只检查新写的 `context/watch/watch_detail/claims`。单字段被拒时恢复对应的主 enrich 已审计字段；长短走向任一被拒时两者一并恢复，防止语义失配。整条生成或审计失败时按一次性事件展示，不输出来龙或延续入口，并保留主 enrich 已审计的非 `context` 字段；可信延续绝不回退到 enrich 起因。旧 `watch` 与证据足够时，来龙可用 `兑现/部分兑现/未兑现/反转` 回对上一期走向；证据不足不输出结论。历史行只保存轨迹审计后的最终短 `watch`、来源标识和 `日期:item_id` 引用，旧行缺少这些字段时仍可读取。同日重跑优先按稳定条目引用替换当日行，即使首日标题修正也保留 `event_id`。整次登记更新先在内存完成；`daily/YYYY-MM-DD.js`、`manifest.js` 和 `events.json` 作为同一可回滚事务替换，任一文件替换失败都会恢复三者旧版本，RSS、搜索索引和质量记录只在事务成功后更新。7 天无新进展自动归档，归档超 60 天删除，文件缺失或损坏时冷启动重建。
- 事件线**身份名只在首次出现时确定**，续接不再用当天标题覆盖它——当天标题仍完整记进 history 行。旧数据中被覆盖过的名字已一次性回填为首日标题（408 条中 56 条）。
- 事务收尾会做一次**跨天事件线归并**（`reconcile_stale_event_lines`）：候选门要求同类目、日期区间重叠，**且共享至少 8 个低频标题/摘要键**，再进有界批次，由独立 LLM 审计按「是不是同一件事」而非「是不是同一主体」划分，复用同日归并的召回键、并查集与全划分校验。只用「同类目+区间重叠」远远不够——一张跨越数周、只有五个类目的登记表里几乎每对线都满足它，实测会把 408 条中的 406 条每天全量送审；加上键阈值后降到约 31 条。阈值 8 由实测标定：真正的碎片线共享 28-46 个键，噪声对绝大多数只共享 0-3 个。**只处理今天没有写入的线**——今天的线携带回填进日报条目的 `event_id` 和连续性门判定，动它等于推翻已独立验证的结论；今天新建的碎片会在它不再收到精选之后的某天被并掉。审计失败或回复不是完整划分即整批不合并并标记质量降级（漏并只留下两条线，误并毁掉事件身份）。合并以 `first_seen` 最早者为身份，history 按日期去重并保留身份线自己那行，`pinned` 与 `active` 只要有一条成立就继承。详见 `docs/adr/0007-event-lines-merge-across-days.md`。
- `feedback.json` / `read_later.json` / `favorites.json`：由 `api/newsState.js` 写入，分别保存反馈、稍后读和 ⭐ 收藏状态，各封顶 1000 条。稍后读/收藏按 `item_id + date` 去重；收藏只存 `date + item_id` 引用（外加 title/category/url 兜底字段，url 可缺省），收藏页凭引用从 `daily/*.js` 重渲染完整卡片，管线暂不消费 favorites。反馈支持删除式撤销：payload 带 `op: "remove"` 时删除最后一条同 `date + item_id + action` 的记录（页面「更多类似」再点一次即撤销）；管线当晚已蒸馏进画像的部分不回滚，需手改 `interest_profile.md`。
- `interest_profile.md`：兴趣画像，管线会把 marker（`<!-- last_feedback_ts: ... -->`）之后的新反馈蒸馏进去。这个文件可以人工编辑或删行（也可一次性手写丰富的种子画像），但偏好要写成以 `- ` 开头的要点。画像影响精选排序（兴趣契合分）及精选、深读、论文、舆论观察和周综述的个性化，不传给单条新闻 enrich。
- `deep_seen.json`：深度阅读推荐 URL 去重记录，按配置保留。
- `deep_health.json`：最近 14 天深度阅读健康度（v2），按源区分抓取成功/失败、窗口内抓取量、去重后候选、已评分、主题匹配、过线和入选；即使当日零候选也会留记录，避免把低频源误判为失效源。
- `misses.json`：仅个人签名会话可通过 `api/newsState.js` 读写的漏读记录，字段固定为 `id/ts/date/title?/url?/reason`；`date` 必须是真实的 `YYYY-MM-DD` 日历日期，标题或有效 HTTP(S) URL 至少一个，`reason` 只取 `important_event`、`deep_read`、`missing_perspective`，最多保留 1000 条并可撤销。页面分别显示为“重要事件”“值得深读”“缺少视角”。文件不进入画像、评分或信源调整。
- `feedback.json`、`read_later.json`、`favorites.json`、`misses.json`、`vocab-book.json` 与 `interest_profile.md` 通过 Hexo `exclude` 和 `.vercelignore` 排除在静态部署之外，线上 `/news/data/` 不应直接提供这些文件。它们仍以公开 Git 仓库文件为存储后端（尚未产生的文件除外），因此不得写入秘密、隐私正文或可识别个人身份的信息；若需要真正的私密状态，应迁移到私有存储，并清理已经提交过的内容及 Git 历史。
- `papers_seen.json`：今日论文（HF Daily Papers）推荐去重记录，按 `config.yaml` 的 `papers.seen_keep_days` 保留。
- `vocab/YYYY-MM-DD.js` / `vocab-book.json`：**单词本功能已于 2026-07-10 停用**（`config.yaml` 的 `vocab.enabled: false`，管线不再每日挑词；前端界面已移除）。**`api/vocab.js` 写端点已于 2026-08-16 删除**（死功能不保留可写接口，见 `docs/adr/0018-delete-dead-vocab-write-endpoint.md`），历史数据文件原地保留。想恢复时把 enabled 改回 true，并从 git 历史找回 `api/vocab.js` 与前端单词本界面。注意随接口一并移除的还有它承担的「损坏必须报错、禁止覆盖」保证：管线侧 `load_vocab_book` 对损坏数据是返回空册（`enabled: false` 下 `build_vocab` 先行 return，不会读它），所以恢复功能时必须把 `version: 1` 与 `words` / `pending` 为对象数组这条校验一起找回。
- `feed.xml`：RSS 订阅文件，地址为 `/news/data/feed.xml`，按 `config.yaml` 的 `feed_days` 收录精选，深读推荐带【深读】前缀。来源 URL 的协议校验放在发布闸门 `validate_daily_payload`（必须匹配 `^https?://`），不是放在渲染端：前端 `safeUrl` 挡得住页面，但 feed 的 `<item><link>` 是原样输出给阅读器的，闸门 fail-closed 才不用指望每个消费端各自兜底（2026-07-29 补齐）。
- 前端 `safeUrl`（`source/news/js/reports.js`）**自己也要判协议和控制字符，不能只依赖管线已经过滤**（2026-08-10 审查补齐）：管线侧 `_is_valid_http_url` 确实拦掉了非 http(s) 和带空白的 URL，但「上游会过滤所以渲染端只看前缀就行」这条规则，管线出一次 bug 或有人直接投毒 `data/*.js` 就破了。现在与后台 `safeMarkdownUrl` 同口径：先拒控制字符（`U+0000-U+001F 与 U+007F`）和协议相对的 `//`，再判 `^https?://`，其余一律渲染成 `#`。实测引号编码本来就防住了属性逃逸（jsdom 解析不出多余属性），所以这条是纵深防御而不是在补一个已知可利用的洞。
- `search_index.js`：站内搜索紧凑索引，缺失时可由管线从历史 daily 文件重建。
- `news-seen/YYYY-MM-DD.json`：普通新闻跨日去重账本，按日分片并滚动保留 90 天；同 URL 仅时间戳刷新时会在进入任何当日视图前过滤，标题或摘要变化后才交给模型判断是否有实质新增。只有模型明确判定没有实质新增才过滤；调用或结构失败时 fail-open 保留并记 `update_judge_failures`。账本缺失或损坏时从 `all/` 历史档案恢复，且只在日报通过发布校验后写入当天分片。
- `all/YYYY-MM-DD.js` + `all/manifest.js`：全量轻档——抓取窗口内通过跨日 URL 去重的全部条目轻字段（标题/链接/来源/类别/时间），滚动保留 90 天。评分阶段结束后 `backfill_all_scores` 按 URL 把完整的 `all_scored_events` 分数回填到匹配条目（被预筛砍掉的无分）；跨源复述虽不再进入读者可见选材，仍有正常分数。payload 带 `min_score`（`config.yaml` 的 `all_view_min_score`，默认 40），前端默认只显示达标条目、可切换显示全部。两步均独立故障域，失败只记日志、不阻断主管线。

### 页面能力

- 新闻页是无前端框架、无打包步骤的原生 ES Modules 页面：`source/news/index.html` 只保留语义骨架，样式位于 `source/news/news.css`，路由、数据加载、视图和个人操作拆在 `source/news/js/`。现有 `window.NEWS_*` 全局数据脚本继续兼容；数据加载器只接受真实的 `YYYY-MM-DD` 日报日期和 `YYYY-Www` 周报编号，避免 URL 参数被解释为任意脚本路径。
- 页面采用共享响应式外壳：桌面端使用固定左侧栏承载站点标识和 **时间线**、**全部动态**、**报告**、**档案**主导航；移动端使用站点栏、横向主导航和报告归档栏组成的多层顶部导航。裸地址和未知视图默认进入 manifest 最新一期日报；有效个人会话下追加 **收藏**，并显示全局稍后读入口。规范路由为 `?view=timeline`、`?view=all`、`?view=reports&period=day&date=YYYY-MM-DD`、`?view=reports&period=week&week=YYYY-Www`、`?view=topics`、`?view=favs`，旧 `view=picks/day/week` 地址会自动映射。未登录用户直达收藏路由时保留 URL 并显示登录提示，不回退或伪装成时间线。跨天条目统一使用 `日期:id` 复合引用键，反馈、收藏、稍后读和主题追踪按条目或事件最近出现日期记账。
- 新闻页虽然不继承 Fluid 导航，但始终保留博客出口：桌面端左侧栏底部显示“← 返回博客”，移动端站点栏显示首页图标，均以普通 `href="/"` 在当前标签页返回博客首页。该链接不带 `data-route`，避免被日报内部客户端路由接管。
- 时间线视图：按发布时间连续倒序呈现不折叠的单列时间轴，以北京时间日期节点分隔，日期统一显示为中文月日与星期，今天和昨天增加相对前缀；条目按原文发布时间转换为北京时间后归日，日报文件日期只代表生成批次，无有效发布时间时显示「时间待确认」。跨天事件有实质新增时保留在原时间位置并标「延续」，纯重复报道合并来源。顶部「本期优先读」只展示最新一期精选，排序时可聚合近 3 期同事件的独立信源，并结合分数和 36 小时时间衰减选出最多 3 条；它不是归拢多条精选的「今日主线」。页内检索与普通时间轴采用相同归日和去重口径。
- 全部动态视图：按日期节点使用倒序单列时间轴，提供文本搜索、来源筛选、分类筛选和评分过滤。回填评分的日子默认只显示 `score >= min_score` 的条目，并提示已隐藏条数，可切换显示低分或未评分内容；条目同时展示来源、分类和分数。最新一天里已进精选的条目加「✓ 已进精选」徽标并淡化（补漏网时眼睛可直接跳过），旧日期不标——那时的「已进精选」你已记不得读没读过。该标记是渲染完成后的异步装饰，**整页渲染绝不等待日报文件**：全部动态页不依赖日报是否可用、是否够快。
- 报告视图：桌面端显示日/周切换与归档控制栏；移动端顶部栏横向排列周期、归档和前后日期控制。日报正文按 AI、互联网/科技、财经、社会、国际五类稳定分节并全部展开；今日主线后提供仅含非空类目的报告内跳转，隐藏或恢复精选时同步更新。日报和时间线卡片直出摘要，并仅在 `watch` 存在时追加短走向；旧日报中的新闻 `why` 也不显示。可信延续在日报卡片显示可聚焦的「第 N 天·延续」链接：优先跳到上一条精确详情，旧历史缺少 `item_ref` 时降级到对应日期的日报。来龙／起因、现状、详情走向和 claims 只在详情页展开：`context` 一个槽位按来源分栏名，可信延续显示「来龙」，新事件显示「起因」；若可信延续的 `context` 以格式完整的「走向回对」收尾，详情页把它独立显示并保留文字状态，其他形状原样降级。「追踪中」紧跟新闻分节，深读、论文、舆论观察和更多资讯依次置后。刊头按 300 字/分钟显示当前可见核心日报估时，口径为导语、最多 3 条今日主线以及未隐藏精选的标题、摘要和启用中的短走向；不读取顶层 `read_minutes`，也不含详情页字段。追踪、深读导读、论文、舆论和更多资讯合并显示附栏导读估时，深读标题仍单独汇总入选原文估时。30 分钟只是通读日报并选择性阅读深读的软目标，不据此裁剪内容。有效个人会话可在刊头下补记遗漏，表单明确提示记录会进入公开仓库；周报增加所选自然周近 7 天遗漏清单与原因汇总，普通访客不加载或显示该状态。
- 档案视图（所有访客可见，URL 仍为 `/news/?view=topics`，路由键不改以免破坏既有链接）：定位是历史检索工具，不是每日通读的一部分。首屏是「题材地图」，紧凑自适应网格陈列受控标签、精选条数与该题材最新一条精选的日期；**按总量排序而非活跃度**——检索靠位置稳定的肌肉记忆，按活跃度排会让卡片每天换位。点击进入对应 `tag:` 时间线。下方「事件线」把 📌 追踪中置顶，其余不分进行中/归档、按最新日期倒序排成一列（检索时并不知道目标是哪种状态，分组等于要在两组里各找一遍），已归档只在卡上给灰色小标。卡面直出最新一条进展和「起止日期 · 跨 N 天」，展开才看全链；有效个人会话下可追踪或取消追踪。
- 全站历史搜索在桌面端常驻内容工具栏；移动端由顶部搜索按钮打开全屏覆盖层，支持关闭按钮与 `Escape` 返回触发按钮。
- 页面视觉采用暖纸色上的报刊编辑风，亮/暗跟随博客：初始化读 Fluid 写入的 `localStorage["Fluid_Color_Scheme"]` 决定亮暗，未设置则跟随系统。阅读型日报、周报、时间线和详情页统一使用 780px 阅读栏；正文条目以栏线分隔，今日主线、深读和结论使用双线特稿框。日报刊头的导语是页面唯一 `h1`，日期使用 `<time datetime>`，装饰印章不进入无障碍树；期号按日报日期的年内日序生成 `YYYY · 第DDD期`，不依赖 manifest 数量。supplementary 栏目通过内部 `data-kind` 区分版式，仅在正文容器达到 740px 时让追踪、论文和更多资讯启用双栏，深读和舆论观察始终单栏。五类颜色仅用于分类文字和栏目题花，事实状态继续使用独立语义色。新增装饰统一使用 `--ink`、`--vermilion`、`--rule` 等 token，暗色模式只覆盖 token。耦合点：博客若更换主题或改这个存储键，日报页暗色会静默失效。
- 视觉回归基准位于 `docs/visual-baselines/news-editorial/`，覆盖时间线、日报、周报、详情、全部动态、档案和收藏七种状态，各保留 1440px 亮色与 390px 暗色截图。它们用于人工对比版式，不参与运行时加载。其中 `topics-*.png` 拍摄于档案页改版之前（仍是三段分组 + 底部题材地图的旧版式），下次改动该页时一并重拍。

#### 新闻页衬线字体

- `source/news/fonts/noto-serif-sc-700/` 是 Noto Serif SC Bold 2.003 的**全覆盖分片**，325 个 WOFF2，只用于刊头、标题、栏目名和数字。`news-serif-sc.txt` 是**首屏热区**（语料中出现过的全部汉字 + ASCII + 常用标点），决定第一批分片装什么；热区外的字形由 `subsetRemainChars` 保留在尾部分片，按 `unicode-range` 命中才下载。覆盖 30929 个码位，**没有任何字会回退到系统宋体**——因此热区清单不影响正确性，语料增长时无需重新生成。目录总字节数（约 13 MB）不是任何人会下载的量，别拿它当预算。源字体来自 Noto Serif CJK 官方 `Serif2.003/14_NotoSerifSC.zip` 的 `SubsetOTF/SC/NotoSerifSC-Bold.otf`，SHA-256 为 `24693D48BDB9152F0A06B02AF625638A1097ABD6DE4010EBBA027F6E82710527`。OTF 不入库，分发目录保留 `OFL.txt`。
- **冷传输预算是两维加一道合计，别合成一个数**（2026-08-07 修正，原先单卡 1.4 MB 被顶穿）：`test_news_frontend.mjs` 分开卡**结构性地板 ≤ 1_050_000 字节**（刊头/栏目名/导航等常量文案加数字本身就要 29 片 / 991580 字节，35 天实测恒定，防的是分片变碎）、**每日增量 ≤ 700_000 字节**（标题里每个不与常量文案共片的字整拉一片，35 天实测 179664–539868 字节）和**合计 ≤ 1_700_000 字节**（实测最大 1531448，兜"各自不超、加起来失控"）。三条界都做过变异测试。**切分基准是测试里硬编码的 `SERIF_CHROME` 常量文案，绝不能改用 `news-serif-sc.txt`**——那份字表能独立于字体重新生成（实测重生成会让热区从 38 片涨到 72 片），拿它当基准会让护栏在字体没有任何变化时凭空失败。**每日增量波动是内容驱动的正常现象，不是缺陷**；原先"最大 1198 KB 留 17% 余量"之所以站不住，是因为热区字表就是从那批语料生成的，那个最大值是样本内拟合残差。测试失败时先看它报的触发字：中频字（孤、赤、劝、菌）说明热区该换频率表，真生僻字（昇、镕）属预期成本。依据与被否方案见 `docs/adr/0013-serif-font-full-coverage-chunking.md`。
- **受阻未验：热区换 GB2312 频率表。** 实测 20 个触发字（含孤、赤、劝、菌等中频字）全部落在 GB2312 内，35 天里仅 2 天各有 1 个字落在其外；当前热区 2476 汉字中 2330 个已是 GB2312 子集，缺的正是中频字——热区边界是 2026-08-02 语料快照的偶然产物，不是频率。换表能把尾部波动压到近零，代价是热区冷加载从 1050 KB 微升到约 1081 KB（ADR 表已实测）。**卡在取不到源 OTF**（2026-08-07 实测）：`github.com` 能解析且返回 200，但拉 release 资产时连接被重置或降速到约 1.8 KB/s（19 分钟只拿到约 12 MB 压缩包中的 208 KB）；`@fontsource/noto-serif-sc` 只分发 woff2，不能替代 OTF；而上文钉死的 SHA-256 排除了换镜像或换字体版本的取巧办法。与晚点 LatePost 的 TLS 阻塞同类，属外部阻塞而非待排期工作，换网络环境或找到可校验的 OTF 获取途径后再按下条再生成。**不影响正确性**：全覆盖分片已保证没有任何字回退到系统宋体，换表只是压缩尾部分片的每日波动。
- **只托管 700 一个字面。**`--serif` 的每一处用法都必须显式写 `font-weight:700`，漏写会静默回退到系统宋体（合成假粗，与真粗体混排极难看）。常规字重的辅助文本一律用正文无衬线栈，不要试图补 `font-weight:400`。这条不变量由测试「每一处衬线字体用法都显式声明 700 字重」扫描 `news.css` 钉住。取舍全过程与被否掉的 8 种分片配置见 `docs/adr/0013-serif-font-full-coverage-chunking.md`。
- 再生成时先在固定仓库状态运行 `node tools/font-subsets/build-news-serif-chars.cjs`，再在临时目录安装固定版本 `cn-font-split@7.4.3`，把其 `node_modules` 放入 `NODE_PATH`，然后运行 `node tools/generate-news-font.cjs <NotoSerifSC-Bold.otf> tools/font-subsets/news-serif-sc.txt source/news/fonts/noto-serif-sc-700`。生成前先清空目录里的旧 WOFF2（分片文件名按内容哈希，不清会残留孤儿文件）；生成后复制官方 `LICENSE` 为输出目录的 `OFL.txt`，并删除工具生成的 `index.proto`。该版本 CLI 的重复 `--subsets` 参数在 Windows 上存在解析问题，因此使用同版本 Node API；脚本显式结束一次性进程以避开生成完成后的 FFI 清理崩溃。
- **统一详情页**与各列表视图共用同一套导航、搜索、主题切换和稍后读外壳，路由使用 `/news/?date=YYYY-MM-DD&type=news|deep|paper&item=<id>`，旧式无 `type` 链接仍按 news 兼容。新闻详情在标题下先给一行元信息（北京时间发布时刻 + 分类）和一条置顶「阅读原文」（取首个事实源、显示域名），接着把摘要作为无标题导语直出（与深读/论文同形），正文区再按**事实先行**的「来龙／起因 → 现状 → 走向」组织，缺失段落静默省略；走向优先显示 `watch_detail`，缺失时回退到 `watch`，历史新闻 `why` 与 `significance` 无条件忽略。来龙／起因、现状和走向按空行拆成自然段，逐段 HTML 转义并过滤空段。摘要不占章节标题但必须始终显示——搜索视图、周报「本周值得读」和卡片「第 N 天·延续」这三条入口进详情页时读者没见过卡片，且「更多资讯」条目只有摘要没有正文，去掉就是纯丢信息。之后呈现证据概览、claims，末尾用「相关链接」区块逐行列出全部来源（来源名 + 类型标记 + 域名，事实源排在分析源和舆论源之前），再接操作区；深读呈现推荐理由、核心观点、关键点和适合读者；论文呈现阅读理由、研究结论、贡献、证据与局限。缺少新字段的历史数据按现有字段静默降级，有效个人会话下保留稍后读、收藏与新闻反馈操作；「更多资讯」同时提供原文与站内详情入口。RSS 继续读取短走向 `watch` 并以「走向」标注。
- 浏览器通过不可由 JavaScript 读取的签名会话判断是否显示个人操作；普通访客看到的仍是纯阅读页。高权限后台口令不会持久化，也不会发送给日报接口。
- 反馈包括不感兴趣、更多类似、来源质量低、追踪/取消追踪。个人新闻卡直接展示不感兴趣与收藏，稍后读、更多类似、追踪和来源反馈收进原生溢出菜单；深读与论文直接展示收藏、把稍后读收进溢出菜单。日报、时间线、详情和收藏复用同一操作布局，来源质量低仍会在后续管线运行中按近 90 天反馈自然日机械降权，不修改 `sources.yaml`。
- 卡片上的稍后读、更多类似、追踪都是可撤销开关，再点一次即撤回对应记录；操作移入菜单不改变 API、localStorage 键或同步语义。个人操作先做乐观展示，服务端写入失败时会同时回滚内存、localStorage 与卡片状态；取消追踪保留显式的 `false` 覆盖，使当前报告的「追踪中」区立即移除该事件，不能因日报静态数据仍为真而反弹。
- ⭐ 收藏（仅个人会话）：独立于稍后读的永久精华库——稍后读是待读队列（读完沉底），收藏是"觉得最有价值就存"。精选、深度阅读、今日论文三类卡片上都有 ⭐ 按钮（再点取消）；收藏页按收藏时间倒序使用单列阅读流，并提供全部、新闻、深读、论文类型筛选。条目凭 `date + item_id` 引用从对应 daily 文件懒加载并重渲染完整卡片，跨天引用沿用 `日期:id` 复合键；服务端列表会并入本地高亮缓存（`news_fav`，永久不清理），换设备后卡片 ★ 状态一致。
- 追踪事件即使不进精选，也会出现在页面的追踪区；管线会用"更多资讯"补匹配，尽量防止断档。
- 深度阅读频道独立于新闻主管线，源来自 `sources.yaml` 的 `deep_sources`，每个源归入 `ai_engineering`、`tech_business`、`society_finance` 三栏（旧配置名 `zh_society_finance` 仍可读，新数据只写新名）。前三席优先从三栏各取一篇过线文章，空栏名额按总分释放；第四席取剩余最高分，最多 4 篇且不降低 7 分门槛。深读不另建 `voices` 栏，体裁由可选的内容类型标签表达。`deep_sources.type` 可切换专用适配器；综合评论源可用 `topic_filter: finance` 仅保留宏观、商业、市场、劳动和公共经济政策文章：候选必须同时通过模型 `topic_fit` 判断，并在标题或摘要中命中确定性财经证据，孤立的 `commercial`、`expensive`、`policy` 等泛词不构成准入依据。深读失败只丢当天深读推荐，不影响新闻日报产出。
- 今日论文频道同样独立于新闻主管线：抓 **Hugging Face Daily Papers**（社区精选 + 点赞，公开接口无需 key），LLM 按 `interest_profile.md` 的学习坐标（前端/全栈/AI 应用/自动化）从当天几十篇里挑 3-4 篇，产出中文标题、"该读什么/该补什么概念"，带点赞数与"是否有开源代码"标记。写进 daily js 的 `papers` 字段，前端日视图「今日论文」板块渲染（紫色左边框区别于深读）。论文不是新闻——不进精选评分、不占五类名额。参数在 `config.yaml` 的 `papers` 段（`enabled`/`lookback_days`/`max_candidates`/`pick_threshold`/`pick_max`/`seen_keep_days`），失败只记日志、不阻断每日产出。
- 舆论观察：微博/B站热榜（`sources.yaml` 的 `pulse_sources`，直连公开接口）只作两个用途，热榜词条本身永不成为新闻条目——①`opinion_pulse` 用 LLM 挑 2-3 个值得说的传播现象，讲"为何热/群体情绪/平台机制"（滤纯明星八卦），写 daily js 的 `opinion` 字段，前端「舆论观察」板块渲染（琥珀色左边框）；②co-occurrence 暗排序：热榜词条与真新闻事件文本重合（4 字连片或二元组覆盖 ≥0.5）时，该事件最终分乘 `opinion.cooccur_bonus`（默认 1.08）。参数在 `config.yaml` 的 `opinion` 段；热榜抓取或 LLM 失败只丢当天舆论板块，不阻断日报。
- 周综述按周一至周日的自然周生成：主管线每次公开日报运行都会幂等检查最近一个已结束周，覆盖至少 **5/7** 天且报告尚不存在时才合成，低于门槛则保持 `pending`；报告会列出覆盖期数与缺失日期。新版静态数据为兼容型 v2，包含周主线、数字盘点、3-6 个动态主题、代表报道复合引用（`date:item_id`）、上周判断回收、下周信号，以及单列的深读/论文引用。模型生成的主题、代表报道和回收引用只能来自最多 100 条有界证据，但数字盘点与深读/论文引用仍基于完整自然周。候选在写文件前自动初审；失败时定向修复并复审，最终通过才进入周归档。生成或审修失败不阻断日报，由 `weekly-health.json` 最多跨 3 个自然日自动重试，耗尽后本周停止调用；审计合同指纹变化会自动重置失败预算。shadow 不重新生成或审计周综述，旧周报也不改写，低于 5/7 的旧报告不进入新版归档。

### 验证与移除

- 文章页与后台回归：`npm run test:post`（`tests/test_post_reading.mjs` + `tests/test_admin_editor.mjs` + `tests/test_admin_comments.mjs`，同样用 Node 内置测试器与 jsdom）。三者分别覆盖文章阅读交互与样式不变量、后台编辑器与草稿恢复，以及评论 path 映射、本地已读状态、有效页码回退和安全 DOM 编排。改 `source/js/`、`source/css/`、`source/admin/` 或 `scripts/` 后必跑。
- 完整 Python 回归：`py -3.12 -m pytest news-pipeline/tests -q`，其中包含跨批同日归并、发布事务、轨迹夹具和全部历史日报引用完整性检查。测试不调 LLM、不联网；改评分、聚类、可信度审计、健康度、事件登记、偏好学习、深读、周综述、RSS 或搜索索引逻辑后必跑完整回归。`news-pipeline/tests/test_pipeline.py` 是历史独立脚本，不再作为交付验收入口。
- 客观性回归：`py -3.12 news-pipeline/tests/test_objectivity_audit.py`（证据合同、审计/修复/降级、夹具完整性、删除字段分项守恒、次级回退摘要判定与序列化/审计投影一致性）与 `py -3.12 news-pipeline/tests/test_shadow_rollout.py`（shadow 快照隔离与环境还原）。两者同样不调 LLM、不联网，静默通过、失败非零退出；改客观性审计、证据结构或 shadow 流程后必跑。
- API 与鉴权回归（`npm run test:news` 内的 `news-pipeline/tests/test_admin_api.mjs` 与 `test_admin_comments_api.mjs`）：**改 `api/` 下任何文件后必跑，两份测试共同守住后台信任边界**。除会话、Bearer、请求体、GitHub 写入、上传与 CSP 外，评论测试覆盖字段脱敏、只搜公开字段、Twikoo 总超时与业务码、重定向禁用、全量分页一致性、操作白名单、回复置顶限制和带回复顶层评论的删除保护。
- 新闻页回归：`npm run test:news`。测试使用 Node 内置测试器与 jsdom，覆盖新旧路由、DOM 渲染、个人操作 API 合同、无障碍状态和空数据降级；修改 `source/news/index.html`、`source/news/news.css`、`source/news/js/` 或 `source/news/fonts/`（含 `tools/font-subsets/` 的字符清单）后必跑。该套件还含衬线字体的覆盖断言与三条冷传输界，字体资产和清单的改动只有这里能拦住。渲染层的两条安全不变式也在这里：进入 HTML 的插值一律过 `escapeHtml`（判据是解析后的 DOM，不是原始字符串），以及 `safeUrl` 自己拒控制字符和协议相对 `//`、不依赖管线上游已过滤。
- Node 依赖或 `package-lock.json` 变更后运行 `npm ci` 和 `npm audit --omit=dev`，确认锁文件可重建且生产依赖没有已知漏洞；安全升级仍需执行受影响的功能回归，审计归零不能替代测试与构建。
- 依赖安全 override 回归（`npm run test:news` 内，`test_admin_api.mjs`）：`package.json` 的 `overrides` 把 `brace-expansion` 钉到 `5.0.9` 修 GHSA-rgw5-rvv9-x895，但 `minimatch@^3` 必须单独钉 `1.1.18`。**原因是 5.x 改了导出形状而不是能不能 require**：`1.1.18` 直接 `module.exports = expand`（`require()` 拿到函数），`5.0.9` 虽然仍带 CommonJS 构建，导出的却是 `{ expand, EXPANSION_MAX, ... }` 对象；而 `minimatch@3`（`glob@7` → `hexo-renderer-stylus` 那条链）写的是 `var expand = require('brace-expansion')` 后直接 `expand(pattern)`，拿到对象就会在运行时报 `expand is not a function`。**只比对锁文件版本号抓不到这种导出形状误配**，所以除版本断言外还有一条真实调用路径断言，跑 `stylus → glob → minimatch → brace-expansion` 展开 `{main,highlight}` 并要求解析出两个分支。**该测试用 `require.resolve("stylus")` 定位依赖，不要"简化"成 `new URL("../../node_modules/...")` 或 cwd 相对的 glob 模式**：git worktree 没有自己的 `node_modules`，只有 `require()` 解析会向上找到主仓库，改回相对路径会让它在每个 worktree 里都误报失败（2026-08-07 修）。
- 完整交付前运行 `npm run build`，确认 Hexo 能把新闻页 ES Modules、样式、字体和静态数据原样输出到 `_config.yml` 指定的 `dist/news/`，并确认 `dist/admin/` 仍存在。
- 移除方式：删除 `source/news/`、`news-pipeline/`、`.github/workflows/daily-news.yml`、`_config.yml` 中的 `- news/**`、`_config.fluid.yml` 菜单中的 `news` 项即可完全剥离。
- 历史沿革：管线原为独立项目 `D:\每日新闻网站`，已在 2026-07-04 迁入本仓库并退役。
