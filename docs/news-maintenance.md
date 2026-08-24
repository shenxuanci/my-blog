# 日报维护手册

本文记录每日新闻日报的现行运行、数据、页面、字体和验证方式。领域用词以 [日报术语表](../CONTEXT.md) 为准；架构取舍以 [ADR](adr/) 为准。

## 系统概览

- `news-pipeline/` 负责抓取、筛选、事件归并、评分、内容生成、审计和发布数据。
- `source/news/` 是独立静态应用；Hexo 通过 `skip_render: news/**` 原样复制到 `dist/news/`。
- `.github/workflows/daily-news.yml` 每日生成数据并在 `main` 上自动提交 `source/news/data/`，这是仓库自动 push 的唯一例外。
- `api/newsState.js` 负责反馈、收藏、稍后读和漏读写回；公开访客仍只读取静态页面与静态数据。

日报是个人化信号筛选器，不是新闻流。内容结构、事件线和客观性术语不要脱离 `CONTEXT.md` 自创新同义词。

## 配置入口

| 目标 | 文件 |
| --- | --- |
| 新闻源、深读源、热榜源 | `news-pipeline/sources.yaml` |
| 评分、阈值、标签、轨迹、生成、成本与保留窗口 | `news-pipeline/config.yaml` |
| 兴趣画像 | `source/news/data/interest_profile.md` |
| 主管线 | `news-pipeline/daily_news.py` |
| 页面骨架与样式 | `source/news/index.html`、`source/news/news.css` |
| 前端行为 | `source/news/js/` |
| 自动运行 | `.github/workflows/daily-news.yml` |

新增信源先验证 GitHub Actions 出口可达性和近期更新，再用 `source_health.json`、入选结构与漏读记录证明供给缺口。信源终局结论保存在 `sources.yaml` 尾部注释；尚未完成的评估见 [日报信源待办](news_source_roadmap.md)。不得通过关闭 TLS 校验、提交私有信任锚或把密钥写入 URL 配置绕过抓取问题。

## 自动运行与部署

定时工作流每天 UTC 23:00 左右运行。`publish` 模式校验成功后只允许在 `main` 提交并显式 push `source/news/data/`；手动 workflow 默认执行只读 `validate`，不会提交或更新线上数据。

仓库配置：

| 类型 | 名称 | 用途 |
| --- | --- | --- |
| Secret | `STEPFUN_API_KEY`、`DEEPSEEK_API_KEY` | LLM provider 凭证 |
| Secret | `RSSHUB_BASE`、`RSSHUB_KEY` | 可选的自建 RSSHub 源 |
| Secret | `VERCEL_DEPLOY_HOOK` | 生产 manifest 未更新时触发自愈部署 |
| Variable | `LEDGER_ISSUE` | 质量台账 Issue 号 |

`RSSHUB_BASE` 必须包含 `http://` 或 `https://`，其地址和 key 都视为秘密。日志必须通过现有脱敏路径输出，不依赖 GitHub 自动打码。

部署检查直接请求规范主域 `https://www.aoiblog.top`，核对线上 `manifest.js` 是否包含本次发布日期。部署探测与质量台账是不同故障域：Vercel 抖动不能被记成日报内容发布失败。

## 本地运行

安装锁定依赖：

```powershell
py -3.12 -m pip install --require-hashes -r news-pipeline/requirements.txt
```

只抓取、不调用 LLM：

```powershell
py -3.12 news-pipeline/daily_news.py --dry-run
```

完整手动生成前，按 `config.yaml` 的活动 provider 设置 `STEPFUN_API_KEY` 或 `DEEPSEEK_API_KEY`，需要 RSSHub 时再设置对应变量：

```powershell
$env:DATA_DIR = "<repository-outside-temp-directory>"
py -3.12 news-pipeline/daily_news.py
```

默认输出到已忽略的 `news-pipeline/data/`；验收时应把 `DATA_DIR` 指向仓库外临时目录，禁止直接写 `source/news/data/`。客观性 shadow 使用 `--objectivity-shadow`，只在明确需要采样时运行；它会复制数据树到临时快照，不应改动生产数据。

## 数据与隐私边界

`source/news/data/` 主要由管线或页面 API 生成。除 `interest_profile.md` 的偏好要点外，不要手工维护生成数据。

| 数据 | 职责 |
| --- | --- |
| `daily/`、`manifest.js` | 每日日报数据与日期索引 |
| `all/`、`search_index.js`、`feed.xml` | 全部动态、搜索与 RSS 派生产物 |
| `events.json` | 跨天事件登记表 |
| `score_history.json` | 动态精选线账本 |
| `quality-health.json`、`source_health.json`、`deep_health.json` | 质量与信源诊断 |
| `weekly/`、`weekly-health.json` | 周综述与重试状态 |
| `feedback.json`、`read_later.json`、`favorites.json`、`misses.json` | 个人状态 |
| `interest_profile.md` | 可人工维护的兴趣画像 |

个人状态文件通过 Hexo `exclude` 和 `.vercelignore` 排除在静态部署之外，但仍以公开 Git 仓库为存储后端。任何状态文件都不得写入秘密、隐私正文或可识别个人身份的信息；需要真正私密的数据时必须迁移到私有存储并处理既有 Git 历史。

状态写入统一走 `api/newsState.js`，单次 payload、条数、日期、URL 和原因枚举均由接口校验。损坏或结构错误的数据必须显式失败，不能静默当空列表覆盖。单词本已停用，`api/vocab.js` 已删除；`vocab-book.json` 与 `vocab/` 只保留恢复材料。

日报发布把 `daily/YYYY-MM-DD.js`、`manifest.js` 和 `events.json` 视为同一可回滚事务。不要绕过管线分别替换这些文件，也不要手工修补评分或事件登记历史。

## 页面与兼容合同

- 页面路由继续使用 `/news/?view=...`；详情路由为 `/news/?date=YYYY-MM-DD&type=news|deep|paper&item=<id>`，旧式无 `type` 链接按新闻兼容。
- 日报、周报、时间线、详情、全部动态、档案、收藏和搜索共用同一静态外壳与主题状态。
- 历史数据缺少新字段时静默降级；新代码不得要求回填全部旧日报才能加载。
- 新闻详情按“来龙／起因 → 现状 → 走向”组织，材料不足时省略缺失段落；旧新闻 `why` 与 `significance` 不再显示。
- 所有进入 HTML 的文本必须转义；所有外链必须由渲染端自身执行 HTTP(S)、控制字符和协议相对 URL 校验，不能只依赖管线上游。
- 普通访客不加载个人状态；有效签名会话才显示反馈、收藏、稍后读、追踪和漏读入口。
- 视觉基准位于 [日报视觉基准](visual-baselines/news-editorial/)，用于人工对照，不参与运行时加载。

详细字段取舍和兼容理由见对应 ADR，尤其是事件线、跨源复述、次级摘要、客观性、材料等级和周综述相关记录；维护手册不复制算法阈值和模型 wire contract。

## 字体维护

`source/news/fonts/noto-serif-sc-700/` 托管 Noto Serif SC Bold 的全覆盖 WOFF2 分片，只用于刊头、标题、栏目名和数字。项目只托管 `700` 字重；每处 `--serif` 用法必须显式声明 `font-weight: 700`。

`tools/font-subsets/news-serif-sc.txt` 是首屏热区，不是字符覆盖合同。语料增长无需重生成；只有重新调优首屏传输时才同时更新字符清单和字体分片。再生成流程：

1. 在固定仓库状态运行 `node tools/font-subsets/build-news-serif-chars.cjs`。
2. 在仓库外临时目录安装固定版本 `cn-font-split@7.4.3`，通过 `NODE_PATH` 提供依赖。
3. 清空目标目录旧 WOFF2 后运行 `node tools/generate-news-font.cjs <NotoSerifSC-Bold.otf> tools/font-subsets/news-serif-sc.txt source/news/fonts/noto-serif-sc-700`。
4. 保留生成的 WOFF2、`result.css` 与 `OFL.txt`，删除 `index.proto` 和临时依赖；OTF 不入库。
5. 运行 `npm run test:news`，检查结构性、每日增量与合计三条冷传输预算。

字体版本、覆盖策略和预算理由见 [ADR 0013](adr/0013-serif-font-full-coverage-chunking.md)。

## 验证

| 改动 | 验证 |
| --- | --- |
| 日报前端、静态路由、个人操作或字体 | `npm run test:news` |
| `api/` | `npm run test:news` |
| 管线、评分、聚类、轨迹、审计、健康度、深读、周报、RSS 或索引 | `py -3.12 -m pytest news-pipeline/tests -q` |
| 客观性审计 | `py -3.12 news-pipeline/tests/test_objectivity_audit.py` |
| shadow 隔离 | `py -3.12 news-pipeline/tests/test_shadow_rollout.py` |
| 完整交付 | `npm run build` |

Python 回归不调用 LLM、不联网。`news-pipeline/tests/test_pipeline.py` 是历史独立脚本，不作为交付验收入口。修改依赖后还需运行锁文件重建检查和 `pip install --dry-run --require-hashes`；修改 Node 依赖后运行 `npm ci`、`npm audit --omit=dev` 及受影响功能回归。

构建后确认 `dist/news/` 原样包含 ES Modules、样式、字体和静态数据，并确认 `dist/admin/` 仍存在。测试或预览结束后删除仓库内临时数据和工具目录。

## 移除

完整移除日报需要同步删除 `source/news/`、`news-pipeline/`、`.github/workflows/daily-news.yml`，并移除 `_config.yml` 中的 `news/**` 跳过规则和 `_config.fluid.yml` 的日报导航项。执行前先确认个人状态与历史日报是否需要归档。
