# Hexo + Fluid 迁移记录

> 历史快照：本文记录 2026-06-18 的迁移过程，不描述当前全部功能。当前运行状态见根目录 `readme.md` 与 `docs/blog-maintenance.md`。

## 背景

旧博客采用 `Astro + Vercel Serverless API + MongoDB + public/admin.html`：

- 前台通过 `/api/getArticles` 和 `/api/getCategories` 动态读取 MongoDB。
- 后台通过 `public/admin.html` 在线发布文章。
- 评论使用 Twikoo。

本次迁移目标是改为更符合博客写作习惯的静态站：`Hexo + Fluid`。

## 关键决策

- 内容源改为 Markdown 文件。
- 使用 Fluid 主题。
- 继续部署到 Vercel。
- 只迁移公开 API 能返回的 19 篇文章，不迁移草稿。
- 保留测试文章。
- 图片统一放入 `/images/`。
- 文章 URL 使用日期加标题 slug。
- 保留 `/articles.html#article_id` 兼容跳转页。
- Twikoo 评论沿用旧 `article_id` 作为 path。
- 当时的 `public/admin.html` 旧后台不作为新站功能保留；当前 `/admin/` 是迁移后重新建设的后台。

## 迁移方式

迁移工具为 `tools/export-articles-to-hexo.mjs`（该脚本已于 2026-07-28 删除，现行兼容约束见 `docs/blog-maintenance.md`；下面记录的是当时的迁移方式，需要脚本本身请翻 git 历史）：

1. 调用 `https://aoiblog.top/api/getArticles?view=list` 获取公开文章列表。
2. 逐篇调用 detail 接口获取正文。
3. 使用 `pinyin-pro` 为中文标题生成稳定 slug。
4. 生成 `source/_posts/*.md`。
5. 生成 `source/articles.html` 作为旧链接兼容页。
6. 生成 About、Friends、Guestbook 三个独立页面。

## 运行变化

- `npm run dev` 改为 `hexo server`。
- `npm run build` 改为 `hexo clean && hexo generate`。
- 构建输出目录为 `dist/`。
- 当时的 MongoDB API、Astro `src/` 和 `public/admin.html` 不再参与运行；当前仓库的 `api/` 是迁移后重新建设的 Vercel 接口。

## 注意事项

- 如果以后需要迁移草稿，不能依赖公开 API，需要 MongoDB 导出或手动补充 Markdown。
- 如果修改旧文章的 `old_id` 或 `twikooPath`，旧评论关联可能断开。
- 如果调整文章 slug，需要同步更新 `source/articles.html` 的旧链接映射。
