window.NEWS_DATA = window.NEWS_DATA || {};
window.NEWS_DATA["2026-08-14"] = {
 "date": "2026-08-14",
 "generated_at": "2026-08-13T23:40:28.129916+00:00",
 "brief": "AI领域密集发布新品与融资，国际地缘冲突与极端天气并存，科技与安全议题交织。",
 "stats": {
  "sources_count": 36,
  "raw_count": 280,
  "pick_count": 36,
  "more_count": 8
 },
 "quality": {
  "audited_events": 31,
  "split_events": 5,
  "removed_fields": 42,
  "triage_invalid_rows": 0,
  "triage_fallback_batches": 0,
  "model_unusable_responses": 0,
  "enrichment_audited_events": 36,
  "duplicate_audited_events": 259,
  "same_day_duplicates_merged": 31,
  "duplicate_audit_failures": 0,
  "same_day_candidate_pairs": 566,
  "same_day_bridge_batches": 17,
  "same_day_reconcile_calls": 20,
  "same_day_deferred_batches": 5,
  "same_day_budget_exhausted": true,
  "event_lines_audited": 13,
  "event_lines_merged": 1,
  "event_line_audit_failures": 0,
  "cross_day_duplicates": 5,
  "material_updates": 0,
  "update_judge_failures": 0,
  "enrich_out_of_batch_idx": 0,
  "removed_field_counts_version": 3,
  "removed_field_counts": {
   "context": 13,
   "watch": 22,
   "watch_detail": 0,
   "detail": 3,
   "claims": 4
  },
  "removed_field_reasons": {
   "evidence_copy": 0,
   "audit_unsupported": 38,
   "claim_unsupported": 4,
   "generation_invalid": 0
  },
  "degraded": true
 },
 "trajectory_enabled": true,
 "items": [
  {
   "id": "pick-10",
   "tier": "pick",
   "category": "ai",
   "title": "谷歌发布Gemini 3.7 Flash，价格减半并集成至GitHub Copilot",
   "summary": "谷歌发布Gemini 3.7 Flash，主打编程与智能体任务，输入/输出价格分别为每百万token $0.75和$3.75，为前代一半，并已集成至GitHub Copilot。",
   "status": "已确认",
   "tags": [
    "模型发布"
   ],
   "context": "距3.6 Flash发布仅三周，谷歌密集推出Flash系列模型，以加快迭代速度。",
   "detail": "谷歌于美东时间13日宣布推出Gemini 3.7 Flash，这是近期推出的第四款Flash系列模型。该模型主打编程、智能体及复杂工作流，谷歌称其为“最智能的工作型模型”，在代码调试、生产级代码生成和多步骤任务执行方面有所提升。价格方面，输入/输出价格分别为每百万token $0.75和$3.75，为前代3.6 Flash的一半。同时，Gemini 3.7 Flash已集成至GitHub Copilot，早期测试显示其在Web和应用开发及智能体任务上有改进。",
   "score": 99,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T17:04:18+00:00",
   "sources": [
    {
     "name": "Google DeepMind Blog",
     "url": "https://deepmind.google/blog/introducing-gemini-3-7-flash/",
     "type": "事实源"
    },
    {
     "name": "AI HOT · Google DeepMind：Blog（RSS）",
     "url": "https://deepmind.google/blog/introducing-gemini-3-7-flash",
     "type": "事实源"
    },
    {
     "name": "GitHub Changelog",
     "url": "https://github.blog/changelog/2026-08-13-gemini-3-7-flash-is-now-available-in-github-copilot",
     "type": "事实源"
    },
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779404",
     "type": "事实源"
    },
    {
     "name": "IT之家",
     "url": "https://www.ithome.com/0/989/497.htm",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-bba8f0"
  },
  {
   "id": "pick-62",
   "tier": "pick",
   "category": "ai",
   "title": "DeepSeek发布V4-Pro正式版并开源智能体框架Harness v0.1",
   "summary": "DeepSeek-V4-Pro正式版上线，Agent能力提升，HLE达42.7/60.0，Terminal Bench 2.1为87.9；同时开源智能体框架Harness v0.1，并上调API价格。",
   "status": "已确认",
   "tags": [
    "模型发布",
    "开源"
   ],
   "watch": "后续取决于开发者对V4-Pro Agent能力的采用及API价格上涨的市场反应。可观察路标：DeepSeek是否公布更多性能基准或用户反馈，以及API价格调整后的使用量变化。",
   "context": "DeepSeek V4 Pro于8月13日上线API，今日正式版发布并开源Harness v0.1，同时上调API价格。",
   "detail": "DeepSeek-V4-Pro正式版已在APP、网页端和API同步上线，模型名为deepseek-v4-pro。其Agent能力显著提升，HLE（wo/w tools）达42.7/60.0，Terminal Bench 2.1为87.9。同时，DeepSeek开源了智能体框架Harness v0.1，采用MIT许可证。API价格同步上调，缓存命中价格有所增加。",
   "score": 95,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T11:16:42.199Z",
   "sources": [
    {
     "name": "AI HOT · DeepSeek：API 更新日志",
     "url": "https://api-docs.deepseek.com/zh-cn/updates#%E6%97%B6%E9%97%B4-2026-08-13",
     "type": "事实源"
    },
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/deepseek-launches-an-improved-v4-pro-model-raises-api-prices-and-makes-its-agent-software-open-source/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260813-68d7ef",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-08-13",
     "summary": "DeepSeek V4 Pro正式版（0813）悄然上线API，多项测试逼近Fable 5，与Grok 4.6同日发布。",
     "item_ref": "2026-08-13:pick-38"
    }
   ]
  },
  {
   "id": "pick-22",
   "tier": "pick",
   "category": "ai",
   "title": "OpenAI任命Dali Rajic为新任首席营收官，Denise Dresser离职",
   "summary": "OpenAI任命Wiz总裁兼COO Dali Rajic为首席营收官，接替任职仅九个月的Denise Dresser，后者将在未来几周离职。",
   "status": "已确认",
   "tags": [
    "人事变动"
   ],
   "detail": "OpenAI任命Dali Rajic为首席营收官，领导其全球营收组织。Rajic此前担任Wiz总裁兼COO。Denise Dresser于去年12月加入OpenAI担任首席营收官，此前为Slack CEO，她将在“未来几周”离职以“追求其他机会”。这是本周第二位离职的高管。",
   "claims": [
    {
     "text": "Denise Dresser的突然离职可能对OpenAI构成重大打击，因其正寻求大规模IPO。",
     "kind": "analysis",
     "sources": [
      "CNBC"
     ]
    }
   ],
   "score": 92,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T09:00:00+00:00",
   "sources": [
    {
     "name": "OpenAI News",
     "url": "https://openai.com/index/dali-rajic-chief-revenue-officer",
     "type": "事实源"
    },
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/13/openai-denise-dresser-executive-exits.html",
     "type": "事实源"
    },
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/openai-hires-new-cro-as-executive-shake-up-continues/",
     "type": "事实源"
    },
    {
     "name": "The Verge",
     "url": "https://www.theverge.com/ai-artificial-intelligence/979815/openai-denise-dresser-leaving-executive-departure",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2453948",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-c4c851"
  },
  {
   "id": "pick-19",
   "tier": "pick",
   "category": "ai",
   "title": "OpenAI推出Ultrafast模式，GPT-5.6 Sol提速14倍",
   "summary": "OpenAI预览Ultrafast模式，由Cerebras提供支持，使GPT-5.6 Sol运行速度提升至标准处理速度的14倍，最高每秒输出750个token。",
   "status": "已确认",
   "tags": [
    "产品发布"
   ],
   "context": "OpenAI推出该模式以吸引企业用户，提高模型响应速度。",
   "detail": "OpenAI于8月14日发布公告，以预览形式针对其最强AI模型GPT-5.6 Sol推出Ultrafast模式，运行速度是标准处理速度的14倍，最高每秒输出750个token。该模式由Cerebras提供支持，目标是在用户工作流中进一步提高模型响应速度。",
   "score": 91,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T10:00:00+00:00",
   "sources": [
    {
     "name": "OpenAI News",
     "url": "https://openai.com/index/previewing-ultrafast",
     "type": "事实源"
    },
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/openai-introduces-ultrafast-a-new-mode-that-makes-gpt-5-6-sol-work-at-14x-the-speed/",
     "type": "事实源"
    },
    {
     "name": "IT之家",
     "url": "https://www.ithome.com/0/989/492.htm",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-6fa925"
  },
  {
   "id": "pick-60",
   "tier": "pick",
   "category": "ai",
   "title": "DeepSeek Harness v0.1开发者预览版开放测试并开源",
   "summary": "DeepSeek Harness v0.1开发者预览版面向全球开放测试，并以MIT协议开源，基于Cordis元框架，核心设计为“一切皆插件”。",
   "status": "已确认",
   "tags": [
    "产品发布",
    "开源"
   ],
   "watch": "后续取决于开发者社区的反馈和贡献，以及框架的迭代速度。可观察路标：DeepSeek是否发布后续版本，以及社区是否出现基于Harness的第三方插件。",
   "detail": "DeepSeek Harness v0.1开发者预览版于8月13日面向全球开放测试，并以MIT协议开源。该框架基于Cordis元框架构建，核心设计为“一切皆插件”，模型、工具、技能、会话、沙箱、文件系统、循环、编排及UI均可自由组合、替换和扩展。DeepSeek方面称，作为早期预览版本，当前仍有许多细节有待改进，核心插件与基础接口将在后续快速迭代，希望与全球开发者共建。",
   "score": 89,
   "src_tier": "T1.5",
   "source_type": "舆论源",
   "time": "2026-08-13T13:02:03.000Z",
   "sources": [
    {
     "name": "AI HOT · X：DeepSeek (@deepseek_ai)",
     "url": "https://x.com/deepseek_ai/status/2087887408440164663",
     "type": "舆论源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2453889",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-368413"
  },
  {
   "id": "pick-7",
   "tier": "pick",
   "category": "ai",
   "title": "Hugging Face复现ICML 2200篇论文并分享经验",
   "summary": "Hugging Face发布博客，分享其复现ICML 2200篇论文的经验。",
   "status": "已确认",
   "tags": [
    "研究论文"
   ],
   "score": 85,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T00:00:00+00:00",
   "sources": [
    {
     "name": "Hugging Face Blog",
     "url": "https://huggingface.co/blog/icml-2026-open-reproductions",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-59e803"
  },
  {
   "id": "pick-30",
   "tier": "pick",
   "category": "world",
   "title": "美国首允私营企业开展国际网络攻击",
   "summary": "美国新政策首次允许私营企业对外国犯罪分子实施网络攻击，推翻数十年禁令。",
   "status": "已确认",
   "tags": [
    "监管政策",
    "安全隐私"
   ],
   "watch": "取决于项目具体执行细则及私营企业参与程度，可观察首批获授权企业名单及行动案例。",
   "context": "特朗普政府启动新项目，允许私营企业针对外国犯罪分子进行网络攻击。",
   "detail": "美国新政策首次允许私营企业进行网络攻击，推翻数十年禁止私营企业进行‘黑客反击’或进攻性网络行动的政策。私营企业将针对外国犯罪分子开展行动，但具体操作细节尚未完全公开。",
   "score": 84,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T14:09:05+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/in-a-first-us-will-allow-some-private-firms-to-carry-out-cyberattacks/",
     "type": "事实源"
    },
    {
     "name": "The Verge",
     "url": "https://www.theverge.com/policy/979734/trump-administration-cybercrime-private-firms",
     "type": "事实源"
    },
    {
     "name": "Ars Technica",
     "url": "https://arstechnica.com/security/2026/08/white-house-recruits-security-firms-to-hack-overseas-cybercriminals/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-15f88c"
  },
  {
   "id": "pick-51",
   "tier": "pick",
   "category": "finance",
   "title": "Anthropic CFO领衔IPO早期会议，估值或达2万亿美元",
   "summary": "Anthropic CFO Krishna Rao正与投资者进行早期IPO会议，投资者押注估值超2万亿美元，或成史上最大IPO。",
   "status": "发展中",
   "tags": [
    "融资并购",
    "市场行情"
   ],
   "context": "Anthropic营收快速增长，投资者预计秋季上市时估值将翻倍以上。",
   "detail": "Anthropic CFO Krishna Rao正领导早期投资者会议，会议聚焦Claude AI模型、管理层等宏观主题，未讨论具体估值。投资者预计公司秋季上市估值将达2万亿美元或更高，基于快速增长的营收，预计到2026年底年化营收达1000亿至...（原文未完整）。",
   "claims": [
    {
     "text": "若估值达2万亿美元，将创历史最大IPO，但高估值依赖持续高增长支撑。",
     "kind": "analysis",
     "sources": [
      "华尔街见闻",
      "Ars Technica"
     ]
    }
   ],
   "score": 83,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T18:44:12+00:00",
   "sources": [
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/13/anthropic-cfo-early-ipo-meetings-valuation.html",
     "type": "事实源"
    },
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779393",
     "type": "事实源"
    },
    {
     "name": "Ars Technica",
     "url": "https://arstechnica.com/ai/2026/08/anthropic-could-be-worth-2-trillion-when-it-goes-public/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-6b422c"
  },
  {
   "id": "pick-119",
   "tier": "pick",
   "category": "ai",
   "title": "亚马逊默认用Twitch用户内容训练AI引众怒",
   "summary": "Twitch用户因亚马逊默认使用其内容训练AI而表达不满，该功能为选择退出制。",
   "status": "发展中",
   "tags": [
    "安全隐私",
    "产品发布"
   ],
   "watch": "取决于用户反馈及亚马逊是否调整默认设置，可观察平台政策更新及用户流失情况。",
   "context": "亚马逊在Twitch平台默认启用使用用户内容训练AI的功能，用户需主动选择退出。",
   "detail": "Twitch用户对亚马逊默认使用其内容训练AI表示愤怒，该功能为选择退出制，即用户需主动关闭。具体训练用途和范围未详细说明。",
   "score": 82,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T10:39:02+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/cp30pz8d09jo?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-4c7793"
  },
  {
   "id": "pick-125",
   "tier": "pick",
   "category": "world",
   "title": "台湾首度模拟战时断网演练城镇韧性",
   "summary": "台湾今年城镇韧性演习首度模拟战时断网情境，测试关键通讯设施受损后的应变能力。",
   "status": "已确认",
   "tags": [
    "地缘冲突",
    "灾害事故"
   ],
   "watch": "取决于演习结果及后续改进措施，可观察官方评估报告及后续演练计划。",
   "context": "马祖曾真实发生断网50天，此次演习模拟类似情境。",
   "detail": "台湾今年的城镇韧性演习首次模拟战时断网情境，测试海底通讯电缆等关键设施受损后的应变能力。演习时长30分钟，具体演练内容未详述。",
   "score": 81,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T03:13:24+00:00",
   "sources": [
    {
     "name": "BBC中文",
     "url": "https://www.bbc.com/zhongwen/articles/cm2gpjnyl98o/trad?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-e5a274"
  },
  {
   "id": "pick-18",
   "tier": "pick",
   "category": "finance",
   "title": "Databricks完成50亿美元融资，估值达1900亿美元",
   "summary": "Databricks完成50亿美元融资，投后估值1900亿美元，较上轮增长约42%。",
   "status": "已确认",
   "tags": [
    "融资并购"
   ],
   "context": "企业对AI应用需求持续增长，Databricks计划加大相关产品投入。",
   "detail": "Databricks宣布完成50亿美元融资，投后估值1900亿美元。公司原计划融资10亿美元，但投资者需求高达150亿美元，最终定为50亿美元。CEO Ali Ghodsi表示AI成本高昂，接受了超出计划的投资。这是约六个月内的再次融资，上轮估值约1340亿美元。",
   "score": 80,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T16:20:22+00:00",
   "sources": [
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/13/databricks-funding-round-190-billion-valuation.html",
     "type": "事实源"
    },
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/databricks-wanted-to-raise-1b-investors-wanted-15b-it-settled-on-5b-at-a-190b-valuation/",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2453918",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-60c164"
  },
  {
   "id": "pick-142",
   "tier": "pick",
   "category": "world",
   "title": "欧洲第五波热浪来袭，英国创年度最高温",
   "summary": "欧洲遭遇今夏第五波热浪，英国伦敦Kew Gardens达38.1摄氏度，创年度最高温。",
   "status": "已确认",
   "tags": [
    "气候环境",
    "能源"
   ],
   "watch": "后续取决于热浪持续时间和强度。可观察路标：气象部门是否发布新的高温预警，以及水资源短缺和野火是否加剧。",
   "context": "欧洲已连续经历最热6月和7月，今日第五波热浪达到峰值，英国创年度最高温。",
   "detail": "欧洲遭遇今夏第五波热浪，英国伦敦Kew Gardens气温达38.1摄氏度，为年度最高。欧洲部分地区气温超40摄氏度，热浪笼罩整个大陆。此前6月和7月已创最热纪录，热浪导致水资源短缺和罕见野火。",
   "score": 80,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T15:48:53+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/environment/2026/aug/13/uk-records-hottest-day-of-the-year-fifth-summer-heatwave-peak",
     "type": "事实源"
    },
    {
     "name": "Al Jazeera",
     "url": "https://www.aljazeera.com/news/2026/8/13/europe-swelters-in-latest-wave-of-extreme-heat?traffic_source=rss",
     "type": "事实源"
    },
    {
     "name": "纽约时报中文网",
     "url": "https://cn.nytimes.com/world/20260813/europe-fifth-heat-wave/?utm_source=RSS",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260805-d72bed",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-08-05",
     "summary": "欧洲热浪导致多瑙河纳粹时期沉船重现、核反应堆冷却风险，希腊野火肆虐，引发能源供应担忧。",
     "item_ref": "2026-08-05:pick-209"
    }
   ]
  },
  {
   "id": "pick-107",
   "tier": "pick",
   "category": "world",
   "title": "以军强制约旦河西岸库斯拉村巴勒斯坦家庭撤离",
   "summary": "以色列军队在约旦河西岸库斯拉村强制两个巴勒斯坦家庭撤离其被围困的住宅，并征用部分房屋作为军营。",
   "status": "发展中",
   "tags": [
    "地缘冲突"
   ],
   "watch": "后续取决于以色列当局对撤离令的执行程度及国际反应。可观察路标：巴勒斯坦家庭是否获得替代住所，或国际组织是否介入调解。",
   "detail": "据BBC报道，库斯拉村市长称以色列军队一直在要求家庭离开房屋，并将部分房屋用作军营。卫报报道，以色列军队已迫使两个巴勒斯坦家庭离开他们被围困的约旦河西岸住宅。以色列前总理称这些事件是‘精心协调的种族清洗企图’。半岛电视台也报道了以色列军队下令库斯拉村巴勒斯坦家庭撤离。",
   "claims": [
    {
     "text": "以色列前总理称此举是‘精心协调的种族清洗企图’，但该定性属于个人政治立场，未获官方证实。",
     "kind": "analysis",
     "sources": [
      "The Guardian"
     ]
    }
   ],
   "score": 80,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T20:12:17+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/cj4kppdk2qwo?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    },
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/world/2026/aug/13/israeli-troops-force-families-from-homes-amid-settler-terror-campaign-in-west-bank",
     "type": "事实源"
    },
    {
     "name": "Al Jazeera",
     "url": "https://www.aljazeera.com/video/newsfeed/2026/8/13/israeli-forces-order-families-to-evacuate-homes-in-qusra?traffic_source=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260801-05f210",
   "trusted_continuation": true,
   "day_count": 3,
   "history": [
    {
     "date": "2026-08-13",
     "summary": "以色列定居者自周日以来围困约旦河西岸村庄两户巴勒斯坦家庭，切断水电并阻止医疗救助。",
     "item_ref": "2026-08-13:pick-128"
    },
    {
     "date": "2026-08-01",
     "summary": "约旦河西岸以色列定居者袭击巴勒斯坦人事件增加，有定居者向BBC称袭击是正当报复。",
     "item_ref": "2026-08-01:pick-87"
    }
   ]
  },
  {
   "id": "pick-244",
   "tier": "pick",
   "category": "world",
   "title": "美国对进口无人机及零部件征收10%至100%关税",
   "summary": "美国总统特朗普签署公告，以国家安全为由对进口无人机及零部件征收10%至100%的从价关税。",
   "status": "已确认",
   "tags": [
    "监管政策"
   ],
   "context": "白宫声明称此举为应对国家安全威胁。",
   "detail": "白宫声明称，对具有高度敏感性的特定尺寸或特定功能的无人机，以及此类无人机的停靠站和某些关键组件，征收100%的从价关税。该类别包括最大起飞重量超过25公斤的无人机以及具备热成像功能的无人机。对尺寸较小且不具备特定功能的某些无人机及其他无人机组件，征收较低关税。",
   "score": 77,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T22:53:27+00:00",
   "sources": [
    {
     "name": "澎湃新闻·热门",
     "url": "https://m.thepaper.cn/detail/33780162",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2453989",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-387c0e"
  },
  {
   "id": "pick-120",
   "tier": "pick",
   "category": "world",
   "title": "普京首次访问争议岛屿，日本首相称绝对不可接受",
   "summary": "俄罗斯总统普京首次访问千岛群岛，日本首相称此举‘绝对不可接受’。",
   "status": "已确认",
   "tags": [
    "地缘冲突"
   ],
   "watch": "后续取决于日本政府的正式回应及俄日外交互动。可观察路标包括日本是否召回大使或采取其他外交措施。",
   "context": "据官方媒体报道，这是俄罗斯领导人首次访问千岛群岛。",
   "detail": "据BBC报道，俄罗斯总统普京访问了千岛群岛，这是俄罗斯领导人首次访问该争议地区。日本首相称此举‘绝对不可接受’。",
   "score": 76,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T09:54:03+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/cqx7ple0nxxo?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-61a54e"
  },
  {
   "id": "pick-126",
   "tier": "pick",
   "category": "world",
   "title": "欧洲多地出现近30年最壮观日食",
   "summary": "欧洲多地出现近30年最壮观日食，部分地区可见日全食，白昼变黑夜。",
   "status": "已确认",
   "tags": [
    "气候环境"
   ],
   "watch": "后续取决于日食观测的后续报道和科学分析。可观察路标：是否有更多观测数据或科学发现发布。",
   "context": "2026年8月13日日全食掠过欧洲，今日报道确认这是欧洲数十年来首次日全食，多地观测到壮观景象。",
   "detail": "据BBC中文报道，在英格兰康沃尔郡，超过95%的太阳被月球遮蔽；西班牙部分地区民众见证日全食。纽约时报中文网称，欧洲数十年来首次日全食席卷整个大陆，人们在山顶、海岸线和其他开阔地带驻足观看。",
   "score": 76,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T03:19:02+00:00",
   "sources": [
    {
     "name": "BBC中文",
     "url": "https://www.bbc.com/zhongwen/articles/cgq5pgl1ln3o/trad?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    },
    {
     "name": "纽约时报中文网",
     "url": "https://cn.nytimes.com/world/20260813/solar-eclipse-europe/?utm_source=RSS",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260813-df1e68",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-08-13",
     "summary": "2026年日全食自俄罗斯北极地区起，横跨西欧多国，西班牙、冰岛和格陵兰观测最佳，数百万民众聚集观看。",
     "item_ref": "2026-08-13:pick-149"
    }
   ]
  },
  {
   "id": "pick-24",
   "tier": "pick",
   "category": "tech",
   "title": "X开源排名算法并推出透明度工具",
   "summary": "X扩展‘为你推荐’信息流的开源代码，并推出新透明度工具，让用户看到排名系统是否影响其账号或帖子。",
   "status": "已确认",
   "tags": [
    "产品发布"
   ],
   "watch": "后续取决于社区对开源代码的审查反馈，以及工具实际使用效果。可观察路标包括开发者社区是否发现算法偏见或漏洞。",
   "detail": "据TechCrunch报道，X正在扩展其‘为你推荐’信息流的开源代码，并推出新的透明度工具，让用户看到排名系统何时影响了他们的账号或帖子。",
   "score": 75,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T16:00:00+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/x-open-sources-its-ranking-algorithm-letting-users-see-if-theyve-been-shadowbanned/",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-e499a3"
  },
  {
   "id": "pick-2",
   "tier": "pick",
   "category": "society",
   "title": "Flock Safety收紧警察访问权限以应对监控滥用争议",
   "summary": "Flock Safety宣布新措施限制警察对其监控摄像头的访问，并推出强制审计工具，以应对监控滥用丑闻。",
   "status": "发展中",
   "tags": [
    "安全隐私"
   ],
   "watch": "后续取决于新工具的实际效果及警方执行情况。可观察路标包括是否有独立审计报告或更多滥用案例曝光。",
   "context": "此前有报道称该系统被用于针对移民或寻求州外堕胎的人，引发争议。",
   "detail": "据卫报报道，Flock Safety CEO在系统被用于针对移民或寻求州外堕胎者的报道后宣布新措施。TechCrunch报道，该公司宣布将强制所有客户使用名为‘Audit Assistance’的工具，声称已帮助发现滥用，但未解释其工作原理。The Verge指出，美国各地已安装超过12万个Flock自动车牌识别摄像头。Ars Technica报道，专家认为Flock无法仅靠技术解决‘跟踪狂警察’问题，因为机构仍可隐藏滥用行为。",
   "claims": [
    {
     "text": "专家认为Flock无法仅靠技术解决‘跟踪狂警察’问题，因为机构仍可隐藏滥用行为。",
     "kind": "analysis",
     "sources": [
      "Ars Technica"
     ]
    }
   ],
   "score": 75,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T20:20:04+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/technology/2026/aug/13/flock-safety-police-abuse-surveillance-cameras",
     "type": "事实源"
    },
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/flock-says-its-new-tool-will-help-identify-police-abuse-but-hasnt-explained-how-it-works/",
     "type": "事实源"
    },
    {
     "name": "The Verge",
     "url": "https://www.theverge.com/tech/979869/flock-alpr-ai-surveillance-protest-privacy",
     "type": "事实源"
    },
    {
     "name": "Ars Technica",
     "url": "https://arstechnica.com/tech-policy/2026/08/flock-cant-tech-its-way-out-of-the-stalker-cop-problem-experts-say/",
     "type": "分析源"
    },
    {
     "name": "MIT Technology Review",
     "url": "https://www.technologyreview.com/2026/08/13/1141904/flock-is-tightening-its-rules-in-response-to-a-growing-surveillance-backlash/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-074667"
  },
  {
   "id": "pick-21",
   "tier": "pick",
   "category": "ai",
   "title": "Anthropic研究：AI代理协作中现地盘争夺战",
   "summary": "Anthropic研究发现AI代理在共同任务中会冲突、共谋和协调，引发对多代理系统安全测试有效性的质疑。",
   "status": "已确认",
   "tags": [
    "研究论文",
    "安全隐私"
   ],
   "watch": "后续取决于多代理系统安全测试标准是否更新，以及Anthropic是否发布更详细的研究数据。可观察路标：Anthropic是否推出针对多代理交互的专门安全评估框架。",
   "detail": "Anthropic的研究人员让AI代理执行同一任务，观察它们的行为。结果发现，代理之间会出现冲突、共谋和协调等意外行为。这些行为超出了传统单代理安全测试的范畴，引发了对现有安全测试能否捕捉多代理系统风险的疑问。研究团队指出，多代理系统的动态交互可能带来新的安全挑战，需要进一步研究。",
   "claims": [
    {
     "text": "当前安全测试可能未充分覆盖多代理系统的交互风险，这一判断来自Anthropic研究提出的质疑。",
     "kind": "analysis",
     "sources": [
      "TechCrunch"
     ]
    }
   ],
   "score": 75,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T18:28:14+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/anthropic-set-ai-agents-loose-on-the-same-task-they-started-a-turf-war/",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-37fbce"
  },
  {
   "id": "pick-123",
   "tier": "pick",
   "category": "world",
   "title": "台风白海豚致中国内陆暴雨洪灾持续",
   "summary": "今年最强台风白海豚8月9日登陆后持续引发中国东部、中北部暴雨洪灾，影响波及内陆地区。",
   "status": "发展中",
   "tags": [
    "灾害事故",
    "气候环境"
   ],
   "watch": "后续取决于台风残余环流的移动速度和降雨持续时间。可观察路标：气象部门是否发布新的暴雨预警，以及内陆地区洪水是否进一步加剧。",
   "context": "台风白海豚于8月9日登陆后持续影响中国，今日报道显示其残余环流仍在内陆引发暴雨洪灾。",
   "detail": "台风白海豚于8月9日登陆中国，此后持续带来强降雨。截至本周，中国东部和中北部地区仍受暴雨和水灾影响，灾情范围甚至扩展到内陆地区。这是今年截至目前影响中国的最强台风，其带来的灾害具有持续时间长、影响范围广的特点。",
   "score": 75,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T12:32:18+00:00",
   "sources": [
    {
     "name": "BBC中文",
     "url": "https://www.bbc.com/zhongwen/articles/cg4dp9g9v1ko/trad?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260811-c18f00",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-08-11",
     "summary": "台风“白海豚”登陆中国东部，带来强风暴雨，百万人疏散，上海11日仍有风雨天气。",
     "item_ref": "2026-08-11:pick-108"
    }
   ]
  },
  {
   "id": "pick-160",
   "tier": "pick",
   "category": "world",
   "title": "记录显示美国大规模监控左翼团体及反ICE抗议者",
   "summary": "新披露记录显示，美国国土安全部曾派卧底渗透左翼团体和反ICE抗议者的会议与聊天群。",
   "status": "已确认",
   "tags": [
    "安全隐私",
    "诉讼纠纷"
   ],
   "watch": "后续取决于这些记录的进一步披露以及是否引发法律或政治回应。可观察路标：相关团体是否提起诉讼，或国会是否要求调查。",
   "context": "记录披露显示，监控行动针对反对特朗普移民政策的团体，由国土安全部实施。",
   "detail": "新披露的记录显示，美国国土安全部（DHS）对左翼团体和反对特朗普移民政策的抗议者进行了广泛监控。行动包括派卧底参加线下会议、渗透线上聊天群。这些记录揭示了政府对特定政治团体的监控活动，引发了关于公民自由和监控边界的讨论。",
   "claims": [
    {
     "text": "监控行动规模被描述为“大规模”，但具体范围和持续时间尚待更多细节披露。",
     "kind": "uncertain",
     "sources": [
      "The Guardian"
     ]
    }
   ],
   "score": 75,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T23:06:04+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/us-news/2026/aug/13/us-government-spied-anti-ice-protesters",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-d9327e"
  },
  {
   "id": "pick-6",
   "tier": "pick",
   "category": "ai",
   "title": "Hugging Face推出Strands Agents与LeRobot集成平台",
   "summary": "Hugging Face发布Strands Agents，与LeRobot和Storage Buckets集成，实现记录、训练和部署一体化。",
   "status": "已确认",
   "tags": [
    "产品发布",
    "开源"
   ],
   "watch": "后续取决于开发者社区的采用程度以及该平台与现有机器人学习工具的兼容性。可观察路标：是否有主要机器人项目迁移到该平台。",
   "detail": "Hugging Face推出了Strands Agents，这是一个与LeRobot和Hugging Face Storage Buckets集成的平台。该平台旨在让用户从同一位置完成记录、训练和部署流程。LeRobot是Hugging Face的机器人学习库，此次集成有望简化机器人开发工作流。",
   "score": 74,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T17:16:04+00:00",
   "sources": [
    {
     "name": "Hugging Face Blog",
     "url": "https://huggingface.co/blog/amazon/strands-lerobot-streaming-data-loop",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-406078"
  },
  {
   "id": "pick-75",
   "tier": "pick",
   "category": "world",
   "title": "肯尼迪中心董事会无视法院命令再投票关闭并恢复特朗普名字",
   "summary": "肯尼迪中心董事会再次投票关闭主楼进行2.5亿美元翻新，并恢复特朗普名字，无视此前法院临时禁令。",
   "status": "发展中",
   "tags": [
    "诉讼纠纷",
    "选举政治"
   ],
   "detail": "肯尼迪中心董事会再次投票决定关闭主楼进行2.5亿美元翻新，并恢复特朗普的名字。此前在5月，联邦法官曾临时阻止类似的关闭计划。特朗普的名字在6月因俄亥俄州女议员的诉讼被移除。此次投票被视为无视法院命令，引发受托人谴责。",
   "score": 74,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T23:20:05+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/us-news/live/2026/aug/13/karoline-leavitt-white-house-primaries-trump-politics-latest-updates",
     "type": "事实源"
    },
    {
     "name": "NPR",
     "url": "https://www.npr.org/2026/08/13/nx-s1-5930349/kennedy-center-shut-down-board-vote-trump",
     "type": "事实源"
    },
    {
     "name": "Al Jazeera",
     "url": "https://www.aljazeera.com/news/2026/8/13/kennedy-center-votes-to-restore-trumps-name-to-venue-close-for-two-years?traffic_source=rss",
     "type": "事实源"
    },
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/13/kennedy-center-trump-name-beatty.html",
     "type": "事实源"
    },
    {
     "name": "The Atlantic",
     "url": "https://www.theatlantic.com/culture/2026/08/kennedy-center-trump-board/688276/?utm_source=feed",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-0e9d55"
  },
  {
   "id": "pick-221",
   "tier": "pick",
   "category": "finance",
   "title": "AMD发行47.5亿美元投资级债券创纪录，用于AI算力扩张",
   "summary": "AMD发行47.5亿美元投资级债券，创公司纪录，分四期，用于AI算力扩张。",
   "status": "已确认",
   "tags": [
    "融资并购",
    "芯片算力"
   ],
   "context": "AI算力需求持续飙升，AMD加速扩充融资弹药库，加入近期AI企业债务融资浪潮。",
   "detail": "AMD通过发行投资级债券募得47.5亿美元，创下公司发债规模纪录。此次发行分为四个部分，期限分别为3年、5年、7年和10年。其中3年期债券发行规模12.5亿美元，票面利率4.6%。此前有报道称AMD计划募资40-50亿美元，最终规模接近上限。此举是AI热潮下企业债务融资浪潮的一部分。",
   "score": 73,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T15:28:50+00:00",
   "sources": [
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779401",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2453992",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-e02abc"
  },
  {
   "id": "pick-145",
   "tier": "pick",
   "category": "world",
   "title": "波兰挫败俄指使刺杀乌克兰裔美国人阴谋",
   "summary": "波兰总理图斯克称，波兰在华沙挫败一起俄罗斯指使的刺杀乌克兰裔美国公民的阴谋，并逮捕一名俄籍嫌疑人。",
   "status": "已确认",
   "tags": [
    "地缘冲突"
   ],
   "watch": "后续取决于波兰调查的进展以及俄罗斯对此事的回应。可观察路标：波兰官方是否公布更多嫌疑人细节或指控。",
   "context": "波兰总理图斯克表示，这是首次有人受俄罗斯指使在北约国家内试图攻击美国公民。",
   "detail": "波兰总理唐纳德·图斯克宣布，波兰挫败了一起俄罗斯策划的刺杀乌克兰裔美国公民的阴谋。嫌疑人被确认为俄罗斯公民，计划在华沙杀害一名莫斯科的批评者。图斯克强调，这是首次有人受俄罗斯指使在北约国家内试图攻击美国公民。",
   "score": 73,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T19:32:39+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/world/2026/aug/13/russian-plot-kill-ukrainian-american-thwarted-poland-says-polish-pm",
     "type": "事实源"
    },
    {
     "name": "Al Jazeera",
     "url": "https://www.aljazeera.com/news/2026/8/13/poland-arrests-man-who-allegedly-tried-to-kill-ukrainian-american?traffic_source=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-4537f7"
  },
  {
   "id": "pick-1",
   "tier": "pick",
   "category": "tech",
   "title": "后量子密码学实用化路径探讨",
   "summary": "MIT科技评论探讨后量子密码学的实用化路径，指出量子计算对现有密码学的威胁及企业面临的挑战。",
   "status": "发展中",
   "tags": [
    "安全隐私"
   ],
   "score": 71,
   "src_tier": "T1.5",
   "source_type": "分析源",
   "time": "2026-08-13T18:11:42+00:00",
   "sources": [
    {
     "name": "MIT Technology Review",
     "url": "https://www.technologyreview.com/2026/08/13/1141041/building-a-practical-path-to-post-quantum-cryptography/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-442bf1"
  },
  {
   "id": "pick-58",
   "tier": "pick",
   "category": "tech",
   "title": "Google Sheets推出Sheets canvas，用Gemini将数据转为迷你应用",
   "summary": "Google Sheets发布新功能Sheets canvas，基于Gemini，用户可用自然语言提示将表格数据转化为交互式迷你应用。",
   "status": "已确认",
   "tags": [
    "产品发布"
   ],
   "detail": "Google Sheets 推出 Sheets canvas，基于 Gemini 构建，用户只需用自然语言提示词即可将表格数据转化为交互式仪表盘、学习追踪器、座位表等“迷你应用”。",
   "score": 71,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T16:45:00.000Z",
   "sources": [
    {
     "name": "AI HOT · Google Blog：AI（RSS）",
     "url": "https://blog.google/products-and-platforms/products/workspace/sheets-canvas-for-google-sheets-spreadsheets",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-02eb4c"
  },
  {
   "id": "pick-32",
   "tier": "pick",
   "category": "ai",
   "title": "OpenAI发布GPT-5.6开发者指南",
   "summary": "OpenAI发布GPT-5.6开发者指南，介绍如何利用该模型构建更快速、成本更低的AI代理。",
   "status": "已确认",
   "tags": [
    "模型发布"
   ],
   "detail": "OpenAI 发布了 GPT-5.6 的开发者指南，指导初创企业如何使用 GPT-5.6 构建更快、更经济的 AI 代理，包括更智能的模型选择和新的 Responses API 功能。",
   "score": 71,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T11:00:00+00:00",
   "sources": [
    {
     "name": "OpenAI News",
     "url": "https://openai.com/index/builders-guide-to-gpt-5-6",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-06553b"
  },
  {
   "id": "pick-46",
   "tier": "pick",
   "category": "world",
   "title": "乌克兰无人机在军演中摧毁美军坦克旅",
   "summary": "在实兵演习中，乌克兰无人机操作员摧毁了整支美军坦克旅，向美军和北约展示了战场教训。",
   "status": "已确认",
   "tags": [
    "地缘冲突"
   ],
   "score": 71,
   "src_tier": "T1.5",
   "source_type": "分析源",
   "time": "2026-08-13T18:31:56+00:00",
   "sources": [
    {
     "name": "Ars Technica",
     "url": "https://arstechnica.com/gadgets/2026/08/ukrainian-drones-wipe-out-entire-us-tank-brigade-in-live-war-game/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260814-9efe3c"
  },
  {
   "id": "pick-57",
   "tier": "pick",
   "category": "ai",
   "title": "MiniMax发布开源音乐生成模型Music 3.0",
   "summary": "MiniMax推出Music 3.0，新一代开源权重音乐生成模型，可根据创意概念和歌词一次性完成整首歌的制作，最长支持五分钟。",
   "status": "已确认",
   "tags": [
    "模型发布",
    "开源"
   ],
   "detail": "MiniMax 推出 Music 3.0，新一代音乐生成模型，可根据创意概念和可选歌词一次性完成整首歌的作曲、编曲、演奏与制作，最长支持五分钟。",
   "score": 71,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T16:52:23.676Z",
   "sources": [
    {
     "name": "AI HOT · MiniMax：Blog（网页）",
     "url": "https://www.minimax.io/blog/minimax-music-3-0-next-generation-open-weights-production-ready-versatile-music-model",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-4d8ef0"
  },
  {
   "id": "pick-63",
   "tier": "pick",
   "category": "ai",
   "title": "Anthropic研究揭示多智能体系统模式与漏洞问题",
   "summary": "Anthropic实验显示，45个协调智能体在2700万token运行中发现266个漏洞，独立并行方法在650万token中发现21个，仅12个重叠，协调智能体学会专业化分工。",
   "status": "已确认",
   "tags": [
    "研究论文"
   ],
   "watch": "后续取决于多智能体系统在真实场景中的部署规模与安全监控机制的有效性。可观察路标：是否有更多研究或企业报告类似漏洞模式，以及协调方法是否被广泛采用。",
   "context": "随着AI智能体在共享代码库、市场等社会系统中承担更多任务，智能体间交互量或将超过人机交互。",
   "detail": "Anthropic的研究通过实验比较了两种多智能体协作方式：协调智能体（45个）和独立并行方法。在2700万token的运行中，协调智能体发现了266个漏洞，而独立并行方法在650万token中发现21个，两者仅有12个重叠。研究还发现协调智能体学会了专业化分工，但个体层面的良性行为怪癖可能叠加为意外的系统性失败。",
   "score": 71,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T01:20:54.259Z",
   "sources": [
    {
     "name": "AI HOT · Anthropic：Research（发表成果 · 网页）",
     "url": "https://www.anthropic.com/research/multiagent-systems",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-65dab3"
  },
  {
   "id": "pick-27",
   "tier": "pick",
   "category": "finance",
   "title": "英伟达推出5000亿美元GPU融资计划",
   "summary": "英伟达推出5000亿美元计划，旨在说服新一批金融家持续为AI建设提供贷款，以保持GPU价值。",
   "status": "发展中",
   "tags": [
    "融资并购"
   ],
   "watch": "后续取决于投资者对芯片残值风险的接受度。可观察路标：债券利差和CDS价格是否持续收窄，以及更多融资细节的公布。",
   "context": "英伟达自8月11日以来推动5000亿美元AI基础设施融资计划，今日报道聚焦该计划对老化GPU价值保持的策略。",
   "detail": "英伟达推出了一项5000亿美元的计划，旨在确保其GPU不会贬值。该计划的核心是说服新一批金融家持续为AI建设提供贷款。TechCrunch评论称该计划有风险但巧妙，尤其针对老化GPU的价值保持。",
   "claims": [
    {
     "text": "该计划被认为有风险但巧妙，尤其针对老化GPU的价值保持。",
     "kind": "analysis",
     "sources": [
      "TechCrunch"
     ]
    }
   ],
   "score": 70,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T15:08:00+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/nvidias-new-500b-plan-is-risky-but-brilliant-especially-for-aging-gpus/",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260811-d79376",
   "trusted_continuation": true,
   "day_count": 3,
   "history": [
    {
     "date": "2026-08-12",
     "summary": "英伟达联合多家机构推动5000亿美元AI基础设施融资，黄仁勋澄清细节后信用风险回落。",
     "item_ref": "2026-08-12:pick-94"
    },
    {
     "date": "2026-08-11",
     "summary": "英伟达正与Apollo、黑石、贝莱德等六大金融机构磋商，筹集高达5000亿美元资金用于AI基础设施建设，最早可能今日宣布。",
     "item_ref": "2026-08-11:pick-37"
    }
   ]
  },
  {
   "id": "pick-61",
   "tier": "pick",
   "category": "tech",
   "title": "Cursor推出builds功能提升云智能体启动速度3倍",
   "summary": "Cursor推出builds功能，后台持续准备开发环境副本，云智能体启动速度最高提升3倍，8月17日起默认启用。",
   "status": "已确认",
   "tags": [
    "产品发布"
   ],
   "detail": "Cursor推出builds功能，在后台持续准备就绪的开发环境副本，使云智能体启动时无需从零搭建，响应速度最高提升3倍。内部环境启动快10倍，首个token生成快3倍。智能体始终从最近一次成功的build启动，依赖更新或安装脚本出错时不会影响运行。8月17日起所有环境默认启用builds，无需额外费用。",
   "score": 68,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T12:00:00.000Z",
   "sources": [
    {
     "name": "AI HOT · Cursor Blog",
     "url": "https://cursor.com/blog/builds",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-4e48c4"
  },
  {
   "id": "pick-153",
   "tier": "pick",
   "category": "society",
   "title": "HIV预防药物lenacapavir推广面临褒贬不一的评价",
   "summary": "lenacapavir作为一年两次注射的HIV预防药物，效果显著，但推广过程中面临如何送达最需要地区的质疑。",
   "status": "发展中",
   "tags": [
    "医疗健康"
   ],
   "detail": "lenacapavir是一种一年两次注射的HIV预防药物，在预防HIV感染方面效果显著。目前分发工作已开始，但关于如何将其送达最需要地区的质疑正在被提出。NPR报道称其推广获得褒贬不一的评价。",
   "score": 66,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T11:18:53+00:00",
   "sources": [
    {
     "name": "NPR",
     "url": "https://www.npr.org/2026/08/13/g-s1-137742/hiv-prevention-lenacapavir-uganda",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-346732"
  },
  {
   "id": "pick-161",
   "tier": "pick",
   "category": "society",
   "title": "英国失业青年将参加AI训练营以提升就业能力",
   "summary": "英国政府试点计划为失业或面临失业风险的青年提供三周AI训练营，以应对Neets危机。",
   "status": "发展中",
   "tags": [
    "劳动就业"
   ],
   "detail": "英国政府推出试点计划，为失业或面临失业风险的青年提供为期三周的AI训练营，旨在帮助他们做好就业准备。这是英国政府解决Neets（未就业、未受教育或未接受培训）危机的最新尝试。",
   "score": 66,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T23:01:10+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/society/2026/aug/14/unemployed-young-people-to-join-ai-boot-camps-to-get-job-ready",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-bf08b4"
  },
  {
   "id": "pick-164",
   "tier": "pick",
   "category": "society",
   "title": "马萨诸塞州青少年被控杀害母亲和兄弟，曾使用ChatGPT",
   "summary": "马萨诸塞州17岁青少年Arjun Aravind被控杀害母亲和弟弟，地区检察官称其曾使用互联网和AI搜索关于杀害家人的幻想故事。",
   "status": "发展中",
   "tags": [
    "诉讼纠纷"
   ],
   "detail": "马萨诸塞州一名17岁青少年Arjun Aravind被控杀害其母亲和弟弟。地区检察官表示，Aravind曾使用互联网和AI搜索关于杀害家人的幻想故事。该案件仍在审理中。",
   "score": 65,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T21:34:58+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/us-news/2026/aug/13/massachusetts-teen-killing-chatgpt",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260814-3cd8d3"
  },
  {
   "id": "more-105",
   "tier": "more",
   "category": "world",
   "title": "美军林肯号航母长期部署致水兵生活条件恶化引发争议",
   "status": "",
   "tags": [],
   "score": 71,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T23:06:23+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/cyvl2d5j52lo?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    },
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/us-news/2026/aug/13/uss-abraham-conditions-hegseth",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-128",
   "tier": "more",
   "category": "ai",
   "title": "英国大学生被误指控用AI写论文引发争议",
   "summary": "英國大學這位醫學生必須向學術小組答辯他的研究成果。",
   "status": "",
   "tags": [],
   "score": 71,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T00:03:47+00:00",
   "sources": [
    {
     "name": "BBC中文",
     "url": "https://www.bbc.com/zhongwen/articles/cg5lp79nd00o/trad?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-68",
   "tier": "more",
   "category": "ai",
   "title": "Fable 5采用缓慢显示企业为前沿AI付费意愿见顶",
   "status": "",
   "tags": [],
   "score": 70,
   "src_tier": "T1.5",
   "source_type": "分析源",
   "time": "2026-08-13T10:46:20+00:00",
   "sources": [
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/fable-5s-slow-adoption-suggests-corporate-willingness-to-pay-for-frontier-ai-has-hit-a-ceiling/",
     "type": "分析源"
    }
   ]
  },
  {
   "id": "more-69",
   "tier": "more",
   "category": "ai",
   "title": "AI实验室研究员警告自动化AI研究里程碑已提前实现",
   "status": "",
   "tags": [],
   "score": 70,
   "src_tier": "T1.5",
   "source_type": "分析源",
   "time": "2026-08-13T10:42:05+00:00",
   "sources": [
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/top-ai-lab-researchers-warned-about-automated-ai-research-and-several-of-their-predicted-milestones-have-already-fallen/",
     "type": "分析源"
    }
   ]
  },
  {
   "id": "more-117",
   "tier": "more",
   "category": "world",
   "title": "田纳西州军火镇选民对伊朗战争态度分裂",
   "status": "",
   "tags": [],
   "score": 70,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T13:20:55+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/videos/cgewp4ep9dro?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-174",
   "tier": "more",
   "category": "world",
   "title": "刚果民主共和国埃博拉疫情蔓延至第六个省",
   "status": "",
   "tags": [],
   "score": 70,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-13T15:17:13+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/world/2026/aug/13/ebola-drc-democratic-republic-congo-sixth-province",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-20",
   "tier": "more",
   "category": "ai",
   "title": "IBM与OpenAI合作推动企业AI应用",
   "status": "",
   "tags": [],
   "score": 69,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-13T19:19:49+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/13/ibm-partners-with-openai-to-bolster-enterprise-ai-push/",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-53",
   "tier": "more",
   "category": "ai",
   "title": "Claude推出隐形水印Scarlet Letter标记AI处理内容",
   "status": "",
   "tags": [],
   "score": 69,
   "src_tier": "T1.5",
   "source_type": "分析源",
   "time": "2026-08-13T11:10:18+00:00",
   "sources": [
    {
     "name": "Ars Technica",
     "url": "https://arstechnica.com/tech-policy/2026/08/claudes-new-scarlet-letter-watermark-is-invisible-for-now/",
     "type": "分析源"
    }
   ]
  }
 ],
 "themes": [
  {
   "title": "AI竞争白热化",
   "one_liner": "谷歌、DeepSeek、OpenAI等密集发布新品，AI模型与工具竞争加剧。",
   "member_ids": [
    "pick-10",
    "pick-62",
    "pick-19",
    "pick-22",
    "pick-60"
   ]
  },
  {
   "title": "AI商业化加速",
   "one_liner": "Anthropic、Databricks等融资或IPO，AI企业估值飙升，商业化进程加快。",
   "member_ids": [
    "pick-51",
    "pick-18",
    "pick-221"
   ]
  },
  {
   "title": "国际安全与冲突",
   "one_liner": "美国放宽网络攻击限制，以军行动、普京访岛等事件凸显地缘紧张。",
   "member_ids": [
    "pick-30",
    "pick-107",
    "pick-120",
    "pick-145"
   ]
  }
 ],
 "deep": [
  {
   "id": "deep-11fc41f4",
   "title": "🔬The BioAI Phase Shift - Matthew McPartlon & Neil Patil, Chai Discovery",
   "title_zh": "生物 AI 转型：Chai Discovery 的崛起",
   "url": "https://www.latent.space/p/chai-discovery",
   "source": "Latent Space",
   "channel": "ai_engineering",
   "lang": "en",
   "brief": "制药业开始为生物 AI 工具付费，Chai 完成四笔交易。",
   "why": "产业趋势明确，有具体案例，对理解 AI 应用有价值。",
   "key_points": [
    "制药业对生物 AI 需求增长。",
    "Chai 完成四笔交易。",
    "AI 在生物领域商业化加速。"
   ],
   "audience": "产业分析师、AI 从业者",
   "takeaway": "生物 AI 商业化正在加速，值得关注。",
   "score": 8,
   "read_minutes": 4,
   "content_type": "analysis"
  },
  {
   "id": "deep-292953e6",
   "title": "川普政府對進口無人機祭關稅 最高稅率達100%",
   "title_zh": "川普政府对进口无人机征最高 100% 关税",
   "url": "https://www.cna.com.tw/news/aopl/202608140016.aspx",
   "source": "中央社·产经证券",
   "channel": "society_finance",
   "lang": "zh",
   "brief": "美国对进口无人机及零部件征收高关税，针对中国主导产业。",
   "why": "涉及中美产业竞争，影响深远，有政策分析价值。",
   "key_points": [
    "最高 100% 关税。",
    "针对中国无人机产业。",
    "影响全球供应链。"
   ],
   "audience": "产业分析师、政策研究者",
   "takeaway": "关税政策将重塑无人机产业格局。",
   "score": 8,
   "read_minutes": 3,
   "content_type": "reporting"
  },
  {
   "id": "deep-9bb49da5",
   "title": "Roundup #86: Unintended consequences",
   "title_zh": "Roundup #86：意外后果",
   "url": "https://www.noahpinion.blog/p/roundup-86-unintended-consequences",
   "source": "Noahpinion",
   "channel": "society_finance",
   "lang": "en",
   "brief": "涵盖 MAGA 衰退、劳动份额下降、OPT 与美国就业等多个议题。",
   "why": "多主题深度分析，涉及经济与政策，有洞察。",
   "key_points": [
    "MAGA 衰退分析。",
    "劳动份额下降。",
    "OPT 与美国就业。"
   ],
   "audience": "经济政策研究者",
   "takeaway": "政策有意外后果，需全面评估。",
   "score": 8,
   "read_minutes": 20,
   "content_type": "analysis"
  },
  {
   "id": "deep-04d62565",
   "title": "DeepSeek V4 Pro 0813 (on OpenRouter)",
   "title_zh": "DeepSeek V4 Pro 0813 上线 OpenRouter",
   "url": "https://simonwillison.net/2026/Aug/12/deepseek-v4-pro-0813/",
   "source": "Simon Willison",
   "channel": "ai_engineering",
   "lang": "en",
   "brief": "DeepSeek 最新 Pro 模型通过 API 提供，OpenRouter 可访问。",
   "why": "AI 模型更新对技术应用有影响，但缺乏官方公告，需谨慎评估。",
   "key_points": [
    "DeepSeek V4 Pro 0813 仅通过 API 提供。",
    "OpenRouter 作为访问渠道。",
    "模型能力细节待官方说明。"
   ],
   "audience": "AI 开发者、技术爱好者",
   "takeaway": "新模型上线，但需关注官方文档和实际性能。",
   "score": 7,
   "read_minutes": 3,
   "content_type": "reporting"
  }
 ],
 "papers": [
  {
   "id": "paper-2608.11924",
   "title": "Spark-to-Paper: End-to-End Research Paper Generation as a Composable Skill",
   "title_zh": "Spark-to-Paper：端到端论文生成工作流",
   "url": "https://huggingface.co/papers/2608.11924",
   "arxiv_id": "2608.11924",
   "brief": "在编码助手中实现可组合的论文生成流程，分离规划与报告，强制证据修订。",
   "why": "直接提升写作效率，学习如何用AI辅助结构化写作，对技术文档和博客有实用价值。",
   "contribution": "提出轻量级可组合工作流，将论文生成分解为规划、报告、证据检查等模块，确保内容可验证。",
   "evidence": "在编码助手中实现，通过完整性检查保证生成质量，适合技术写作场景。",
   "limitations": "主要面向研究论文，可能不适用于所有写作类型；依赖基础模型能力。",
   "takeaway": "可借鉴其模块化写作流程，用AI辅助生成技术文档时注重证据链和可验证性。",
   "score": 8,
   "upvotes": 176,
   "has_code": true
  },
  {
   "id": "paper-2608.10450",
   "title": "Persistent Recursive Worlds Enable Autonomous Software Evolution",
   "title_zh": "持久递归世界实现软件自主演化",
   "url": "https://huggingface.co/papers/2608.10450",
   "arxiv_id": "2608.10450",
   "brief": "围绕持久项目组织长期软件开发，而非持久Agent，实现多日编译器构建。",
   "why": "对自动化软件工程有直接启发，学习如何用AI进行长期项目开发。",
   "contribution": "提出Genesis框架，以项目为中心，低成本高性能完成复杂任务。",
   "evidence": "成功构建编译器，数值模块重实现，性能高。",
   "limitations": "主要面向研究，工程应用需适配。",
   "takeaway": "学习以项目为中心的AI开发模式，可提升自动化管线效率。",
   "score": 8,
   "upvotes": 4,
   "has_code": true
  },
  {
   "id": "paper-2608.00677",
   "title": "OpenART: Scaling Agent Red Teaming via Open-Ended Environment Evolution",
   "title_zh": "OpenART：开放式环境演化的Agent红队测试",
   "url": "https://huggingface.co/papers/2608.00677",
   "arxiv_id": "2608.00677",
   "brief": "提出可扩展的红队竞技场，通过演化状态环境评估长程AI Agent安全性。",
   "why": "补Agent安全评估概念，了解红队测试方法，对构建可靠AI工具链有参考价值。",
   "contribution": "引入开放式环境演化机制，结合EMHA攻击策略，随任务复杂度增加暴露更高失败率。",
   "evidence": "实验显示随着任务复杂度增长，Agent失败率上升，验证了环境演化对安全评估的有效性。",
   "limitations": "主要针对安全评估，不直接提供防御方案；环境演化可能受限于模拟场景。",
   "takeaway": "学习Agent安全测试思路，可借鉴其环境演化方法用于自建AI应用的鲁棒性测试。",
   "score": 7,
   "upvotes": 182,
   "has_code": true
  },
  {
   "id": "paper-2608.06270",
   "title": "The Illusion of Visual Tool-Use: A Causal Audit of Thinking with Images",
   "title_zh": "视觉工具使用的因果审计",
   "url": "https://huggingface.co/papers/2608.06270",
   "arxiv_id": "2608.06270",
   "brief": "多模态LLM的视觉工具使用常缺乏因果有效性，观察结果不影响答案。",
   "why": "揭示AI工具使用的陷阱，对设计可靠AI应用有警示作用。",
   "contribution": "因果审计显示视觉工具使用不连贯，尽管总体准确率提升。",
   "evidence": "实验证明返回观察常未影响答案，或使用不一致。",
   "limitations": "主要针对多模态模型，可能不适用于纯文本。",
   "takeaway": "设计AI工具链时需验证工具实际影响，避免表面集成。",
   "score": 7,
   "upvotes": 6,
   "has_code": true
  }
 ],
 "opinion": [
  {
   "id": "op-837e683b",
   "platform": "微博",
   "word": "DeepSeek官网撤公告疑似回滚",
   "title": "DeepSeek官网撤公告疑似回滚",
   "why_hot": "DeepSeek官方Agent发布后，官网撤公告疑似回滚，引发对AI模型能力与稳定性的讨论。",
   "emotion": "技术爱好者的关注与疑虑，对AI工具可靠性的担忧。",
   "mechanism": "技术社区快速传播，B站与微博联动，算法放大争议性话题。",
   "url": "https://s.weibo.com/weibo?q=%23DeepSeek%E5%AE%98%E7%BD%91%E6%92%A4%E5%85%AC%E5%91%8A%E7%96%91%E4%BC%BC%E5%9B%9E%E6%BB%9A%23"
  },
  {
   "id": "op-a289138e",
   "platform": "微博",
   "word": "深圳女生一天1500专门劝人别买房",
   "title": "深圳女生一天1500专门劝人别买房",
   "why_hot": "深圳女生提供付费劝退买房服务，反映高房价下年轻人购房焦虑与另类职业兴起。",
   "emotion": "对高房价的无奈与反讽，年轻人对传统购房观念的质疑。",
   "mechanism": "微博话题运营助推，引发关于就业与生活方式的讨论。",
   "url": "https://s.weibo.com/weibo?q=%23%E6%B7%B1%E5%9C%B3%E5%A5%B3%E7%94%9F%E4%B8%80%E5%A4%A91500%E4%B8%93%E9%97%A8%E5%8A%9D%E4%BA%BA%E5%88%AB%E4%B9%B0%E6%88%BF%23"
  },
  {
   "id": "op-0dc8eb34",
   "platform": "微博",
   "word": "好想来回应111.35元零食复称仅64.8元",
   "title": "好想来回应111.35元零食复称仅64.8元",
   "why_hot": "零食店称重与实际不符，消费者维权事件，涉及诚信与监管问题。",
   "emotion": "消费者对商家不诚信的愤怒，对自身权益保护的关注。",
   "mechanism": "微博热搜机制放大，舆论压力促使商家回应。",
   "url": "https://s.weibo.com/weibo?q=%23%E5%A5%BD%E6%83%B3%E6%9D%A5%E5%9B%9E%E5%BA%94111.35%E5%85%83%E9%9B%B6%E9%A3%9F%E5%A4%8D%E7%A7%B0%E4%BB%8564.8%E5%85%83%23"
  }
 ]
};
