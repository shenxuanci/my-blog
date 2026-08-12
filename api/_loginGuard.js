// 后台口令的失败锁定。
//
// 必须是所有认证路径共用的一份计数：cookie 登录（adminSession）和 Bearer 直连
// （requireAdmin）验的是同一个 ADMIN_TOKEN，只给其中一条接限流等于没限流——
// 攻击者换一条路就能无限次猜。
//
// 计数是模块级 Map，Vercel 每个 lambda 实例一份，所以这是尽力而为的减速带，
// 不是分布式配额；真正的强度来自口令熵。
const MAX_FAILED_ATTEMPTS = 5;
const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const MAX_TRACKED_CLIENTS = 1000;
const loginAttempts = new Map();

function clientAddress(req) {
  const forwarded = req.headers?.['x-vercel-forwarded-for']
    || req.headers?.['x-forwarded-for'];
  const raw = Array.isArray(forwarded) ? forwarded[0] : forwarded;
  return String(raw || req.socket?.remoteAddress || 'unknown')
    .split(',')[0].trim().slice(0, 128) || 'unknown';
}

function pruneLoginAttempts(now) {
  for (const [key, row] of loginAttempts) {
    if (now - row.startedAt >= LOGIN_WINDOW_MS) loginAttempts.delete(key);
  }
}

function retryAfterSeconds(req, now = Date.now()) {
  pruneLoginAttempts(now);
  const row = loginAttempts.get(clientAddress(req));
  if (!row || row.failures < MAX_FAILED_ATTEMPTS) return 0;
  return Math.max(1, Math.ceil((LOGIN_WINDOW_MS - (now - row.startedAt)) / 1000));
}

function recordFailedLogin(req, now = Date.now()) {
  pruneLoginAttempts(now);
  const key = clientAddress(req);
  const row = loginAttempts.get(key);
  if (row) {
    row.failures += 1;
  } else {
    while (loginAttempts.size >= MAX_TRACKED_CLIENTS) {
      loginAttempts.delete(loginAttempts.keys().next().value);
    }
    loginAttempts.set(key, { failures: 1, startedAt: now });
  }
}

function clearLoginAttempts(req) {
  loginAttempts.delete(clientAddress(req));
}

module.exports = {
  MAX_FAILED_ATTEMPTS,
  LOGIN_WINDOW_MS,
  MAX_TRACKED_CLIENTS,
  clientAddress,
  retryAfterSeconds,
  recordFailedLogin,
  clearLoginAttempts,
  resetLoginAttempts: () => loginAttempts.clear()
};
