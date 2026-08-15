# 后台写接口改收带 scope 的会话 cookie，明文主口令不再常驻页面

在这条决策之前，后台的两套认证是分开的：`api/adminSession.js` 签发一个 8 小时、`HttpOnly + Secure + SameSite=Strict` 的签名会话 cookie，只有 `api/newsState.js` 认它；而 `adminArticles.js`、`adminSettings.js`、`adminUpload.js`、`vocab.js` 走 `requireAdmin()`，要求请求头里带裸的 `Authorization: Bearer <ADMIN_TOKEN>`。这个分离是刻意的，并且写成了测试断言：**签名 cookie 不得换来发文章的权限**。它防的是「日报页出现 XSS → 顺着自动携带的 cookie 去发文章」。

代价藏在前端。`source/admin/index.html` 为了持续发出 Bearer 请求，必须把用户输入的 ADMIN_TOKEN 存进 `state.token` 并保留整场会话。于是 `/admin/` 上任何一处 XSS、任何一个恶意浏览器扩展，拿走的不是一张 8 小时后自然过期、JS 读不到的凭据，而是**永久有效、可读、没有轮换路径的主口令**——它同时还是日报个人会话的换取凭据。附带的体验缺陷是刷新后台就得重输口令，尽管 cookie 还在有效期内。

两害相权，取的是后者。会话载荷从 `expires.signature` 改成 `expires.scope.signature`，**scope 参与 HMAC**，所以篡改 scope 必然签名失配；`scope` 只允许 `personal` 与 `admin`。写接口统一走 `requireAdminWrite()`：请求带 `Authorization` 头时走受限流的 Bearer（保留给脚本和 CLI），否则认 `scope=admin` 的 cookie。后台页因此彻底不再持有明文口令——它只在登录那一次请求里出现，换到会话后即从内存清除。

这条决策**放宽了前述不变式**：由于目前只有 `/admin/` 登录会签发会话、签发的都是 `admin` scope，一张有效会话 cookie 现在确实能发文章了。接受它的理由是原不变式的防护面比看上去窄——`/admin/` 与 `/news/` 同源，cookie 又是 `Path=/api`，站内任何一处 XSS 本来就能带着 cookie 打 `/api/*`；它真正拦住的只有「攻击者能执行脚本、但拿不到 admin 会话」这一种窄情形，而它换来的是主口令永久暴露在页面内存里。`personal` scope 保留在代码里不是摆设：将来若出现「只登日报、不进后台」的入口，写接口的拒绝路径已经就位并有测试守着。

## Considered Options

- **维持原样，只补限流**。同一轮修复发现 `requireAdmin()` 完全没有失败锁定，锁定只加在 cookie 登录那条路上——两条路验的是同一个口令，等于没锁。补限流是必须做的，也确实做了（`api/_loginGuard.js` 由两条路共用），但它只提高猜口令的成本，对「口令已经被页面内的脚本读走」这个主要威胁没有任何作用。所以补限流是前提，不是替代。
- **给主口令加过期与轮换**。能根治「永久有效」，但 ADMIN_TOKEN 是 Vercel 环境变量，轮换要手工改配置并重新部署，而且它同时是日报会话的换取凭据，轮换一次所有会话失效。为一个单人后台建一套凭据轮换机制，复杂度远超收益。
- **把主口令换成 sessionStorage 而不是内存变量**。完全没有改善：能执行脚本就能读 sessionStorage，反而多了一份跨标签页留存的副本。
- **保留 Bearer 且不做任何改动**。等于接受「后台页面上任何一处脚本注入 = 永久丢失主口令」。后台页自己就有一个把 Markdown 拼成 HTML 再 `innerHTML` 的预览函数，这个风险不是理论上的。

## Consequences

- **`test_admin_api.mjs` 里那条不变式的含义变了**，不是被删掉。它现在断言的是「**personal scope** 的 cookie 不得通过 `requireAdminScope`」，另加 admin scope 能通过、scope 被篡改则签名失配两条。看到这条测试与本 ADR 之前的直觉冲突时，读这一节，不要「修复」回去。
- **升级会踢掉所有在途会话**。旧的两段格式 `expires.signature` 解出的 scope 不在白名单里，一律判无效。会话本来就只有 8 小时寿命，重登一次即可，没有做兼容期。
- **Bearer 这条路必须一直留着**。它是脚本、CLI 和排障时唯一不依赖浏览器 cookie 的入口；删掉它等于把后台锁死在浏览器里。它现在受同一份失败锁定保护。
- **`requireAdminWrite` 用「有没有 Authorization 头」来选路，不是「先试 cookie 再试 Bearer」**。这是刻意的：串行回退会让一次没带凭据的请求在两条路上各记一次失败，未认证的探测就能把管理员自己锁在门外。同理，`requireAdmin` 对完全缺失的 `Authorization` 头直接返回 401 而不计入锁定——缺失凭证不是猜测。
- **新增 scope 时要同时想清楚两件事**：它能过 `requireAdminSession`（任意 scope 即可）吗，能过 `requireAdminScope`（只认 admin）吗。两个判定分别对应「日报个人状态」和「后台高权限写操作（包括 GitHub 与 Twikoo）」，不要合并成一个。
