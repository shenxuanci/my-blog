window.NEWS_DATA = window.NEWS_DATA || {};
window.NEWS_DATA["2026-08-12"] = {
 "date": "2026-08-12",
 "generated_at": "2026-08-11T23:39:18.842017+00:00",
 "brief": "今日全球聚焦AI产业爆发与安全争议、中东地缘冲突升级、极端天气与自然灾害并行。",
 "stats": {
  "sources_count": 41,
  "raw_count": 272,
  "pick_count": 36,
  "more_count": 8
 },
 "quality": {
  "audited_events": 29,
  "split_events": 3,
  "removed_fields": 39,
  "triage_invalid_rows": 0,
  "triage_fallback_batches": 0,
  "model_unusable_responses": 0,
  "enrichment_audited_events": 36,
  "duplicate_audited_events": 330,
  "same_day_duplicates_merged": 33,
  "duplicate_audit_failures": 0,
  "same_day_candidate_pairs": 523,
  "same_day_bridge_batches": 16,
  "same_day_reconcile_calls": 20,
  "same_day_deferred_batches": 7,
  "same_day_budget_exhausted": true,
  "event_lines_audited": 13,
  "event_lines_merged": 0,
  "event_line_audit_failures": 0,
  "cross_day_duplicates": 7,
  "material_updates": 0,
  "update_judge_failures": 0,
  "enrich_out_of_batch_idx": 0,
  "removed_field_counts_version": 3,
  "removed_field_counts": {
   "context": 12,
   "watch": 23,
   "watch_detail": 0,
   "detail": 0,
   "claims": 4
  },
  "removed_field_reasons": {
   "evidence_copy": 0,
   "audit_unsupported": 35,
   "claim_unsupported": 4,
   "generation_invalid": 0
  },
  "degraded": true
 },
 "trajectory_enabled": true,
 "items": [
  {
   "id": "pick-126",
   "tier": "pick",
   "category": "world",
   "title": "叙利亚法院缺席判处前总统阿萨德死刑",
   "summary": "叙利亚一法院缺席判处前总统阿萨德及其兄弟死刑，罪名是内战期间犯下战争罪和危害人类罪。",
   "status": "已确认",
   "tags": [
    "诉讼纠纷",
    "地缘冲突"
   ],
   "detail": "叙利亚一家法院缺席判处前总统巴沙尔·阿萨德及其兄弟死刑，罪名是内战期间犯下战争罪和危害人类罪。这场持续14年的冲突导致约50万人死亡。判决公布后，部分叙利亚民众聚集庆祝，称“正义终于到来”。阿萨德目前流亡海外，判决实际执行存在障碍。",
   "score": 88,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T14:50:10+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/ce34dkpnyg7o?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    },
    {
     "name": "NPR",
     "url": "https://www.npr.org/2026/08/11/g-s1-138166/syria-assad-sentenced-to-death",
     "type": "事实源"
    },
    {
     "name": "Al Jazeera",
     "url": "https://www.aljazeera.com/video/newsfeed/2026/8/11/justice-at-last-syrians-react-to-assad-death-sentence?traffic_source=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-a86767"
  },
  {
   "id": "pick-40",
   "tier": "pick",
   "category": "tech",
   "title": "Cloudflare报告2026上半年DDoS攻击激增519%",
   "summary": "Cloudflare报告称，2026年上半年其网络检测到超大规模DDoS攻击激增519%，主要由DNS和CLDAP反射向量驱动。",
   "status": "已确认",
   "tags": [
    "安全隐私"
   ],
   "watch": "后续取决于地缘政治紧张局势是否持续，以及攻击向量是否演变。可观察路标：Cloudflare是否发布新报告显示攻击频率或规模变化，或出现新的反射向量。",
   "context": "报告指出攻击激增与地缘政治紧张局势相关。",
   "detail": "Cloudflare在2026年上半年检测到其网络上的超大规模DDoS攻击数量激增519%。这些攻击主要由DNS和CLDAP反射向量驱动，攻击规模可达1 Tbps。报告将攻击激增与地缘政治紧张局势联系起来。",
   "score": 85,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T13:00:00+00:00",
   "sources": [
    {
     "name": "Cloudflare Blog",
     "url": "https://blog.cloudflare.com/ddos-threat-report-2026-h1/",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-70a1d1"
  },
  {
   "id": "pick-115",
   "tier": "pick",
   "category": "world",
   "title": "哥伦比亚7.4级强震致逾180人死亡救援持续",
   "summary": "哥伦比亚西部7.4级强震已致188人死亡、1677人受伤，救援工作持续进行。",
   "status": "发展中",
   "tags": [
    "灾害事故"
   ],
   "watch": "后续取决于余震情况和救援进展。可观察路标：死亡人数是否继续上升，以及救援人员能否找到更多幸存者。",
   "context": "哥伦比亚7.4级强震发生后，死亡人数从最初报告的111人持续上升，截至今日已升至188人，受伤人数达1677人。救援工作仍在进行中，余震不断。",
   "detail": "哥伦比亚西部发生7.4级强震，震中位于太平洋沿岸乔科省，但数百公里外的城市也有震感。截至11日，地震已造成188人死亡、1677人受伤。救援人员继续在废墟中搜寻幸存者，周二发生多次余震。这是该国本世纪最强地震。",
   "score": 85,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T03:43:53+00:00",
   "sources": [
    {
     "name": "BBC中文",
     "url": "https://www.bbc.com/zhongwen/articles/cy9w1n5vgljo/trad?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    },
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/c20dqd9qwq4o?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    },
    {
     "name": "Al Jazeera",
     "url": "https://www.aljazeera.com/video/newsfeed/2026/8/11/search-for-survivors-underway-in-colombias-earthquake-aftermath?traffic_source=rss",
     "type": "事实源"
    },
    {
     "name": "澎湃新闻·热门",
     "url": "https://m.thepaper.cn/detail/33765462",
     "type": "事实源"
    },
    {
     "name": "纽约时报中文网",
     "url": "https://cn.nytimes.com/world/20260811/earthquake-colombia-cali/?utm_source=RSS",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260811-1a7a69",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-08-11",
     "summary": "哥伦比亚西部发生7.4级地震，已致111人死亡、87人受伤，1575栋房屋受损，政府宣布进入国家灾难状态。",
     "item_ref": "2026-08-11:pick-109"
    }
   ]
  },
  {
   "id": "pick-32",
   "tier": "pick",
   "category": "ai",
   "title": "谷歌Gemini月活用户突破10亿",
   "summary": "谷歌CEO皮查伊宣布，Gemini应用月活跃用户达10亿，成为谷歌有史以来增长最快的产品，也是第14款突破10亿用户的产品。",
   "status": "已确认",
   "tags": [
    "产品发布"
   ],
   "watch": "后续取决于Gemini能否保持增长势头，以及商业化进展。可观察路标：谷歌是否公布Gemini的付费用户数或收入数据，或推出新的变现功能。",
   "context": "谷歌Gemini应用月活跃用户从6月的9亿增长至今日的10亿，成为谷歌第14款突破10亿用户的产品，也是增长最快的产品。",
   "detail": "谷歌CEO桑达尔·皮查伊宣布，Gemini应用月活跃用户达到10亿，成为谷歌有史以来增长最快的产品，也是该公司第14款跨越十亿用户大关的产品。此前6月，Gemini月活已超过9亿。据TechCrunch报道，63%的Gemini用户使用语音功能，Gemini每月生成超过1.5亿张图片。",
   "score": 84,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T18:49:12+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/11/googles-gemini-app-surges-to-one-billion-users/",
     "type": "事实源"
    },
    {
     "name": "The Verge",
     "url": "https://www.theverge.com/ai-artificial-intelligence/978113/chatgpt-gemini-1-billion-users",
     "type": "事实源"
    },
    {
     "name": "IT之家",
     "url": "https://www.ithome.com/0/988/552.htm",
     "type": "事实源"
    },
    {
     "name": "AI HOT · X：Sundar Pichai (@sundarpichai)",
     "url": "https://x.com/sundarpichai/status/2087222656819241292",
     "type": "舆论源"
    },
    {
     "name": "Ars Technica",
     "url": "https://arstechnica.com/ai/2026/08/google-says-gemini-has-reached-1b-users-faster-than-any-other-google-product/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260724-a4fbe5",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-07-24",
     "summary": "Google在Q2财报中宣布Gemini月活用户超9.5亿，较去年增长三倍，AI搜索模式用户超10亿，市场份额升至27.7%。",
     "item_ref": "2026-07-24:pick-29"
    }
   ]
  },
  {
   "id": "pick-28",
   "tier": "pick",
   "category": "ai",
   "title": "OpenAI开始在ChatGPT中测试广告",
   "summary": "OpenAI宣布开始在ChatGPT中测试广告，以支持免费访问，并承诺明确标注、答案独立性、隐私保护和用户控制。",
   "status": "发展中",
   "tags": [
    "产品发布"
   ],
   "watch": "后续取决于广告测试的用户反馈和效果。可观察路标：OpenAI是否扩大广告测试范围，或公布广告收入数据。",
   "context": "OpenAI为支持免费访问而测试广告。",
   "detail": "OpenAI宣布开始在ChatGPT中测试广告，目的是支持免费访问。公司承诺广告会有明确标注，不影响答案独立性，并加强隐私保护和用户控制。目前测试范围有限。",
   "score": 84,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T10:00:00+00:00",
   "sources": [
    {
     "name": "OpenAI News",
     "url": "https://openai.com/index/testing-ads-in-chatgpt",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-88f4af"
  },
  {
   "id": "pick-73",
   "tier": "pick",
   "category": "ai",
   "title": "研究人员发现可读取ChatGPT等模型加密推理的API漏洞",
   "summary": "Alexander Panfilov团队发现OpenAI、Anthropic、Google等AI提供商API存在漏洞，可读取推理模型的加密思考过程，并泄露API密钥等敏感信息。",
   "status": "已确认",
   "tags": [
    "安全隐私"
   ],
   "watch": "后续取决于提供商是否修复漏洞以及漏洞被利用的程度。可观察路标：OpenAI、Anthropic、Google是否发布安全公告或补丁。",
   "context": "漏洞源于API设计缺陷，允许提取加密推理轨迹。",
   "detail": "Alexander Panfilov团队发现OpenAI、Anthropic、Google等主要AI提供商的API存在漏洞，可读取推理模型的加密思考过程。扫描约7000条公开会话，发现62个API密钥、33个邮箱和33个密码。通过越狱，Anthropic的Haiku 4.5可逐字转写Opus 4.8的原始推理。解码10000条推理轨迹的API成本约720美元。",
   "claims": [
    {
     "text": "该漏洞可能影响AI模型推理过程的机密性，但实际利用需要特定技术能力。",
     "kind": "analysis",
     "sources": [
      "AI HOT · The Decoder：AI News（RSS）",
      "The Decoder"
     ]
    }
   ],
   "score": 84,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T17:38:49.000Z",
   "sources": [
    {
     "name": "AI HOT · The Decoder：AI News（RSS）",
     "url": "https://the-decoder.com/but-marinade-and-leaked-passwords-are-what-researchers-found-in-chatgpts-hidden-reasoning",
     "type": "事实源"
    },
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/but-marinade-and-leaked-passwords-are-what-researchers-found-in-chatgpts-hidden-reasoning/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-5b5003"
  },
  {
   "id": "pick-80",
   "tier": "pick",
   "category": "ai",
   "title": "NVIDIA发布开源模型Nemotron 3.5 Lightning，SGLang Day-0支持",
   "summary": "NVIDIA发布开源30B MoE模型Nemotron 3.5 Lightning，SGLang宣布Day-0支持，支持1M上下文和多种投机解码技术。",
   "status": "已确认",
   "tags": [
    "模型发布"
   ],
   "detail": "NVIDIA发布的Nemotron 3.5 Lightning是一款开源混合专家模型，总参数30B，激活参数3B，支持最长1M token上下文。模型可从Hugging Face下载BF16和NVFP4权重，支持MTP、DFlash、DSpark三种投机解码技术，并可通过OpenAI兼容API接入智能体工作流。SGLang宣布Day-0支持该模型。模型采用开放权重，支持用户微调，可在RTX PC、DGX Spark及Jetson等设备上运行。",
   "score": 82,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T13:51:45.827Z",
   "sources": [
    {
     "name": "AI HOT · LMSYS：Blog（Chatbot Arena 团队）",
     "url": "https://www.lmsys.org/blog/2026-08-11-nemotron-3-5-lightning",
     "type": "事实源"
    },
    {
     "name": "AI HOT · NVIDIA Blog（RSS）",
     "url": "https://blogs.nvidia.com/blog/local-ai-open-source-models-agents-nemotron",
     "type": "事实源"
    },
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/nvidias-open-weight-nemotron-3-5-lightning-prioritizes-speed-over-maximum-intelligence/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-dcda8f"
  },
  {
   "id": "pick-8",
   "tier": "pick",
   "category": "tech",
   "title": "GitHub Copilot推出MAI-Code-1.1-Flash模型，旧版弃用计划公布",
   "summary": "GitHub Copilot推出微软最新小规模编码模型MAI-Code-1.1-Flash，新增原生视觉支持，并宣布旧版弃用计划。",
   "status": "发展中",
   "tags": [
    "产品发布"
   ],
   "detail": "MAI-Code-1.1-Flash是微软最新的小规模编码模型，正在GitHub Copilot中逐步推出。该模型基于MAI-Code-1-Flash构建，新增了原生视觉支持，用于图像理解。GitHub同时宣布了旧版模型的弃用计划，但具体时间表和影响范围未在摘要中说明。",
   "score": 81,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T18:13:56+00:00",
   "sources": [
    {
     "name": "GitHub Changelog",
     "url": "https://github.blog/changelog/2026-08-11-mai-code-1-1-flash-available-in-github-copilot",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-968abf"
  },
  {
   "id": "pick-164",
   "tier": "pick",
   "category": "tech",
   "title": "JCB Hydromax氢动力车创653公里/小时陆地速度新纪录",
   "summary": "英国车手Andy Green驾驶氢动力车JCB Hydromax在美国邦纳维尔盐滩创下412.135英里/小时（约653公里/小时）的FIA世界陆地速度纪录。",
   "status": "已确认",
   "tags": [
    "汽车出行"
   ],
   "watch": "后续取决于JCB是否继续挑战更高速度，以及该纪录能否获得FIA正式认证。可观察路标：FIA官方公告、JCB后续测试计划。",
   "context": "此前该车已以368.347英里/小时的速度创造纪录，数天后再次冲击并刷新纪录。",
   "detail": "英国车手Andy Green驾驶由两台氢内燃机驱动的JCB Hydromax汽车，在美国邦纳维尔盐滩创下新的FIA世界陆地速度纪录。该车首次出场跑出400.623英里/小时（644.740公里/小时）的平均速度，随后反向行驶跑出412.135英里/小时（约653公里/小时）的速度，最终刷新纪录。Andy Green是唯一一位在汽车中突破音障的人。",
   "score": 81,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T17:48:25+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/us-news/2026/aug/11/driver-sound-barrier-land-speed-record",
     "type": "事实源"
    },
    {
     "name": "IT之家",
     "url": "https://www.ithome.com/0/988/557.htm",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-d86bad"
  },
  {
   "id": "pick-200",
   "tier": "pick",
   "category": "society",
   "title": "台风“白海豚”致中国东部超百万人疏散，北上影响华北",
   "summary": "台风“白海豚”导致中国东部沿海超100万人被疏散，上海上千航班取消，其残余涡旋北上影响华北，可能引发北京等地暴雨。",
   "status": "已确认",
   "tags": [
    "灾害事故"
   ],
   "watch": "后续取决于“白海豚”残余涡旋的移动路径和强度变化。可观察路标：中央气象台发布的暴雨预警、华北地区降雨实况。",
   "context": "台风“白海豚”走势反常，接连两次登陆浙江后北上，其残余涡旋影响华北。",
   "detail": "台风“白海豚”导致中国东部沿海超过100万人被疏散，上海上千个航班被取消。风暴还加剧了菲律宾的季风降雨，扰乱海上交通，导致部分地区洪灾。台风“白海豚”登陆减弱后形成“白海豚残余涡旋”，北上影响华北，可能引发北京等地暴雨。",
   "score": 81,
   "src_tier": "T1",
   "source_type": "分析源",
   "time": "2026-08-10T23:58:21+00:00",
   "sources": [
    {
     "name": "纽约时报中文网",
     "url": "https://cn.nytimes.com/china/20260811/typhoon-dolphin-china-evacuations/?utm_source=RSS",
     "type": "分析源"
    },
    {
     "name": "果壳·科学人",
     "url": "https://www.guokr.com/article/469898/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-cbfb2d"
  },
  {
   "id": "pick-104",
   "tier": "pick",
   "category": "world",
   "title": "伊朗称不满足条件不开放霍尔木兹海峡，国际油价上涨",
   "summary": "伊朗高级官员表示，除非美国满足条件，否则霍尔木兹海峡不会重新开放，国际油价短线冲高，WTI涨至83美元上方。",
   "status": "发展中",
   "tags": [
    "地缘冲突",
    "市场行情"
   ],
   "watch": "后续取决于美伊双方能否就条件达成妥协，以及美军对涉伊船只的行动是否升级。可观察路标：伊朗官方后续声明、美军中央司令部通报、霍尔木兹海峡通航情况。",
   "detail": "伊朗最高领袖顾问穆赫贝尔表示，在伊方条件满足前霍尔木兹海峡不会开放。伊朗最高国家安全委员会秘书雷扎伊称，美国必须接受伊方条件才能换取海峡开放。当天稍早，美官员称美军向一艘与伊朗有关的船只开火，该船试图突破美国对伊朗港口的封锁，一架美国军用直升机向该船船舵开火。受此消息影响，国际油价短线冲高，美国WTI原油期货上涨1.4%报83.27美元/桶，布伦特原油期货上涨1.3%报88.85美元/桶。",
   "score": 80,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T19:11:58+00:00",
   "sources": [
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/11/oil-prices-today-us-crude-84.html",
     "type": "事实源"
    },
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779209",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2451716",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260809-ef4cda",
   "trusted_continuation": true,
   "day_count": 4,
   "history": [
    {
     "date": "2026-08-11",
     "summary": "伊朗和阿曼表示，关于重新开放霍尔木兹海峡的谈判进展积极，伊朗已向美国提出一系列要求。",
     "item_ref": "2026-08-11:pick-106"
    },
    {
     "date": "2026-08-10",
     "summary": "伊朗否认与美国直接谈判，但通过中间人交换信息，并就霍尔木兹海峡问题提出六项条件。",
     "item_ref": "2026-08-10:pick-26"
    },
    {
     "date": "2026-08-09",
     "summary": "伊朗就重开霍尔木兹海峡提出强硬条件，要求美国“纠正行为”，谈判虽称积极但突破仍不明朗。",
     "item_ref": "2026-08-09:pick-30"
    }
   ]
  },
  {
   "id": "pick-110",
   "tier": "pick",
   "category": "ai",
   "title": "CME与Silicon Data合作推出AI算力期货合约，10月5日上线",
   "summary": "CME集团与Silicon Data宣布计划于10月5日推出追踪H100和B200租赁成本的算力期货合约，待监管审批。",
   "status": "发展中",
   "tags": [
    "市场行情"
   ],
   "watch": "后续取决于监管审批结果，以及市场对算力期货的接受度。可观察路标：CFTC审批公告、合约上线后的交易量。",
   "context": "CME此前在5月已宣布将在年内推出首创的算力期货市场，此次为具体产品落地。",
   "detail": "CME集团与GPU市场数据公司Silicon Data宣布，计划于10月5日推出两份算力期货合约，目前有待监管审批。两份合约分别为Silicon Data H100 Rental Index Futures和Silicon Data B200 Rental Index Futures，追踪H100和B200的租赁成本。芝商所表示，这些工具将为希望管理算力成本的企业提供对冲和投资工具。",
   "score": 80,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T18:09:08+00:00",
   "sources": [
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/11/ai-computing-power-becomes-a-tradable-asset-class-as-cme-starts-futures.html",
     "type": "事实源"
    },
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779217",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2451730",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-491675"
  },
  {
   "id": "pick-205",
   "tier": "pick",
   "category": "ai",
   "title": "DeepSeek流量超谷歌，每token成本降13.6%",
   "summary": "AI Gateway数据显示，DeepSeek流量超越谷歌，每token成本下降13.6%。",
   "status": "已确认",
   "tags": [
    "模型发布"
   ],
   "context": "AI Gateway月度路由数万亿token，反映生产环境AI使用情况。",
   "detail": "根据Vercel的AI Gateway Production Index，DeepSeek在流量上超过谷歌，每token成本下降13.6%。该指数基于AI Gateway每月路由的数万亿token数据，反映生产环境中的AI使用情况。",
   "score": 80,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T04:00:00+00:00",
   "sources": [
    {
     "name": "Vercel Blog",
     "url": "https://vercel.com/blog/deepseek-overtakes-google-on-volume-cost-per-token-falls",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-e5bd4d"
  },
  {
   "id": "pick-192",
   "tier": "pick",
   "category": "finance",
   "title": "CoreWeave Q2营收增112%，积压订单1040亿美元",
   "summary": "CoreWeave二季度营收25.75亿美元，同比增长112%，积压订单达1040亿美元。",
   "status": "已确认",
   "tags": [
    "财报"
   ],
   "context": "企业和AI公司持续扩大算力投入，推动AI基础设施需求增长。",
   "detail": "CoreWeave发布2026财年第二季度财报，营收同比增长约112%至25.75亿美元，高于市场预期。净亏损6.26亿美元，每股亏损1.14美元，亏损幅度好于预期。积压订单达1040亿美元，较上季度末的994亿美元增加。",
   "score": 79,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T21:30:37+00:00",
   "sources": [
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779221",
     "type": "事实源"
    },
    {
     "name": "IT之家",
     "url": "https://www.ithome.com/0/988/544.htm",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-b1d931"
  },
  {
   "id": "pick-85",
   "tier": "pick",
   "category": "ai",
   "title": "Anthropic计划9月或10月初IPO，估值9650亿美元",
   "summary": "Anthropic目标9月或10月初上市，估值9650亿美元，年化收入超470亿美元。",
   "status": "仅传言",
   "tags": [
    "融资并购"
   ],
   "context": "公司正与潜在投资者接触，淡化AI模型竞争等挑战。",
   "detail": "Anthropic计划最快9月上市，估值9650亿美元，年化收入超470亿美元。公司正与潜在投资者会面，安抚对近期进展的担忧。预测市场Kalshi上相关押注出现异动。公司计划拓展AI在医疗和生物学领域的应用，但尚未公布具体IPO定价方案。",
   "claims": [
    {
     "text": "Anthropic淡化中国AI企业竞争影响，但投资者可能仍担忧竞争压力。",
     "kind": "analysis",
     "sources": [
      "AI HOT · IT之家（RSS）",
      "The Decoder"
     ]
    }
   ],
   "score": 79,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T03:57:53.000Z",
   "sources": [
    {
     "name": "AI HOT · IT之家（RSS）",
     "url": "https://www.ithome.com/0/988/239.htm",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2451667",
     "type": "分析源"
    },
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/anthropics-planned-mega-ipo-faces-investor-skepticism-over-chinese-rivals-and-political-headwinds/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-c560b1"
  },
  {
   "id": "pick-191",
   "tier": "pick",
   "category": "finance",
   "title": "Lumentum Q4营收翻倍，债务重组致巨额亏损",
   "summary": "Lumentum第四财季营收10.1亿美元同比增逾一倍，但债务重组致超70亿亏损。",
   "status": "已确认",
   "tags": [
    "财报"
   ],
   "detail": "Lumentum第四财季净营收同比增长逾一倍至10.1亿美元，高于预期。非GAAP调整后EPS为3.23美元，同比增267%。但债务重组导致巨额亏损，2026财年归母亏损69.35亿美元，同比由盈转亏。",
   "score": 77,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T21:25:06+00:00",
   "sources": [
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779219",
     "type": "事实源"
    },
    {
     "name": "IT之家",
     "url": "https://www.ithome.com/0/988/545.htm",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-f1a804"
  },
  {
   "id": "pick-116",
   "tier": "pick",
   "category": "world",
   "title": "美军直升机向试图突破伊朗封锁的货船开火",
   "summary": "美军中央司令部称直升机击中巴拿马旗货船机舱，该船试图突破伊朗封锁。",
   "status": "已确认",
   "tags": [
    "地缘冲突"
   ],
   "watch": "关注美伊外交进展及类似事件是否再次发生。",
   "context": "美伊外交陷入僵局，美军对试图突破封锁的船只采取行动。",
   "detail": "美军中央司令部表示，一架直升机在阿曼湾击中一艘巴拿马旗货船Vela Nova的机舱，该船试图突破伊朗封锁。美伊外交仍处于停滞状态。",
   "score": 77,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T21:14:56+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/cvg8lyyyjedo?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    },
    {
     "name": "Al Jazeera",
     "url": "https://www.aljazeera.com/news/2026/8/11/us-military-fires-on-cargo-vessel-it-said-sought-to-break-iran-blockade?traffic_source=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-01074c"
  },
  {
   "id": "pick-20",
   "tier": "pick",
   "category": "ai",
   "title": "Anthropic未发布模型在黎曼猜想上取得进展",
   "summary": "Anthropic未发布模型在黎曼猜想上取得进展，但未解决该问题。",
   "status": "仅传言",
   "tags": [
    "研究论文"
   ],
   "watch": "后续取决于该模型是否正式发布以及数学界对其成果的验证。可观察路标：Anthropic是否发布相关论文或模型，以及独立数学家是否复现或认可该结果。",
   "context": "Anthropic未发布的研究版Claude在黎曼猜想上取得进展，将满足猜想的zeta函数零点比例下界从41.6%提升至67.2%，但未解决该问题。",
   "detail": "TechCrunch报道，Anthropic的一个未发布模型在黎曼猜想上取得了进展，但并未解决该问题。黎曼猜想是数学界150多年未解的重大问题。",
   "score": 77,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T16:25:20+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/11/an-unreleased-anthropic-model-made-progress-on-one-of-maths-biggest-unsolved-problems/",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260811-9ada4c",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-08-11",
     "summary": "Anthropic未发布的研究版Claude将满足黎曼猜想的zeta函数零点比例下界从41.6%提升至67.2%。",
     "item_ref": "2026-08-11:pick-38"
    }
   ]
  },
  {
   "id": "pick-29",
   "tier": "pick",
   "category": "ai",
   "title": "OpenAI Daybreak模型上线AWS Bedrock",
   "summary": "OpenAI的Daybreak网络安全模型现已在AWS Bedrock上可用，支持企业安全工作流。",
   "status": "已确认",
   "tags": [
    "产品发布"
   ],
   "watch": "后续取决于Daybreak Red的采用情况以及GPT-5.6-Cyber在真实漏洞发现中的表现。可观察路标：是否有更多安全厂商或研究机构宣布使用该模型。",
   "detail": "OpenAI与AWS合作，将Daybreak网络安全能力通过Amazon Bedrock提供给企业，以支持企业安全工作流。具体功能细节未披露。",
   "score": 77,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T10:00:00+00:00",
   "sources": [
    {
     "name": "OpenAI News",
     "url": "https://openai.com/index/daybreak-models-are-now-available-on-aws",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260811-b3fb19",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-08-11",
     "summary": "OpenAI发布网络安全专用模型GPT-5.6-Cyber，通过Daybreak Red向授权研究人员开放，用于漏洞研究、利用验证和安全测试。",
     "item_ref": "2026-08-11:pick-10"
    }
   ]
  },
  {
   "id": "pick-121",
   "tier": "pick",
   "category": "world",
   "title": "泽连斯基称俄用朝鲜导弹袭击乌克兰",
   "summary": "泽连斯基称俄罗斯使用朝鲜提供的弹道导弹袭击扎波罗热，造成7人死亡。",
   "status": "有争议",
   "tags": [
    "地缘冲突"
   ],
   "detail": "乌克兰总统泽连斯基表示，俄罗斯在扎波罗热的袭击中使用了来自其盟友朝鲜的弹道导弹，该袭击导致7人死亡。此说法尚未得到独立证实。",
   "score": 77,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T16:19:44+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/c151dpzwnvxo?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-3b7ca2"
  },
  {
   "id": "pick-202",
   "tier": "pick",
   "category": "tech",
   "title": "Vercel企业托管用户功能正式可用",
   "summary": "Vercel的Enterprise Managed Users功能正式全面可用，提供对账户的完全控制。",
   "status": "已确认",
   "tags": [
    "产品发布"
   ],
   "watch": "取决于企业客户的采用速度和与现有身份管理系统的集成。可观察路标：后续是否有大型企业部署案例。",
   "detail": "Vercel宣布Enterprise Managed Users (EMU)正式全面可用。该功能使组织能够完全控制与其验证域名关联的Vercel账户，并将组织的身份提供商作为认证的唯一来源。",
   "score": 76,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T20:38:00+00:00",
   "sources": [
    {
     "name": "Vercel Blog",
     "url": "https://vercel.com/changelog/enterprise-managed-users",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-bde95f"
  },
  {
   "id": "pick-60",
   "tier": "pick",
   "category": "tech",
   "title": "Chrome采用设备绑定会话凭证增强账户保护",
   "summary": "Chrome采用设备绑定会话凭证，以应对日益常见的账户接管攻击。",
   "status": "已确认",
   "tags": [
    "安全隐私"
   ],
   "detail": "Chrome浏览器采用了设备绑定会话凭证，这是一种新型的账户保护机制，旨在防止账户被接管。该技术通过将会话与特定设备绑定，增加了攻击者窃取凭证的难度。",
   "score": 75,
   "src_tier": "T1.5",
   "source_type": "分析源",
   "time": "2026-08-11T20:59:52+00:00",
   "sources": [
    {
     "name": "Ars Technica",
     "url": "https://arstechnica.com/security/2026/08/chrome-adopts-what-may-be-the-best-protection-yet-against-account-takeovers/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-ee167f"
  },
  {
   "id": "pick-78",
   "tier": "pick",
   "category": "ai",
   "title": "英伟达开发万亿参数开源模型Nemotron 4",
   "summary": "英伟达正在开发开源AI模型Nemotron 4，最大规模预计超1万亿参数，目标挑战全球顶级开源模型。",
   "status": "仅传言",
   "tags": [
    "模型发布",
    "开源"
   ],
   "detail": "据媒体报道，英伟达正在开发新一代开源AI模型系列Nemotron 4，规模最大的模型预计至少拥有1万亿个参数，旨在与全球最先进的开源模型竞争。英伟达尚未确定发布日期，最终训练也未完成，员工认为该模型最早可能在今年秋末准备就绪。此举意在通过开放模型生态扩大AI应用范围，并推动市场对其GPU算力的需求。",
   "score": 75,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T14:54:16.000Z",
   "sources": [
    {
     "name": "AI HOT · IT之家（RSS）",
     "url": "https://www.ithome.com/0/988/524.htm",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2451691",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-f37f93"
  },
  {
   "id": "pick-94",
   "tier": "pick",
   "category": "finance",
   "title": "英伟达推动5000亿美元AI基础设施融资计划",
   "summary": "英伟达联合多家机构推动5000亿美元AI基础设施融资，黄仁勋澄清细节后信用风险回落。",
   "status": "发展中",
   "tags": [
    "融资并购",
    "芯片算力"
   ],
   "watch": "后续取决于投资者对芯片残值风险的接受度。可观察路标：债券利差和CDS价格是否持续收窄。",
   "detail": "英伟达联合Apollo、BlackRock、Blackstone、Brookfield、Goldman Sachs和KKR等机构，计划动员超过5000亿美元用于AI基础设施融资。为赢得投资者，英伟达承诺保证其芯片的残值。黄仁勋在X平台澄清了具体条款，随后英伟达的信用风险指标回落，2056年到期的债券利差收窄至113个基点，5年期CDS价格收窄至72.11个基点。",
   "claims": [
    {
     "text": "英伟达通过担保芯片价值来吸引投资者，这一策略可能面临芯片快速贬值的风险。",
     "kind": "analysis",
     "sources": [
      "CNBC",
      "The Decoder"
     ]
    }
   ],
   "score": 74,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T21:01:13+00:00",
   "sources": [
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/11/nvidia-ai-funding-jensen-huang-china-risk.html",
     "type": "事实源"
    },
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779211",
     "type": "事实源"
    },
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/nvidia-guarantees-its-own-chips-value-to-unlock-500-billion-in-ai-infrastructure-financing/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260811-d79376",
   "trusted_continuation": true,
   "day_count": 2,
   "history": [
    {
     "date": "2026-08-11",
     "summary": "英伟达正与Apollo、黑石、贝莱德等六大金融机构磋商，筹集高达5000亿美元资金用于AI基础设施建设，最早可能今日宣布。",
     "item_ref": "2026-08-11:pick-37"
    }
   ]
  },
  {
   "id": "pick-5",
   "tier": "pick",
   "category": "tech",
   "title": "GitHub Copilot for JetBrains新增记忆与Ollama支持",
   "summary": "GitHub Copilot for JetBrains更新，新增持久记忆、本地模型访问及更多企业控制功能。",
   "status": "已确认",
   "tags": [
    "产品发布"
   ],
   "detail": "本次更新为GitHub Copilot for JetBrains带来了持久记忆功能，允许模型在会话间记住用户偏好。同时新增了对Ollama的支持，使用户能够访问本地模型。此外，更新还增强了企业控制选项，并改善了日常聊天工作流，解决了跨多个方面的可靠性问题。",
   "score": 74,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T20:15:55+00:00",
   "sources": [
    {
     "name": "GitHub Changelog",
     "url": "https://github.blog/changelog/2026-08-11-copilot-memory-and-ollama-in-github-copilot-for-jetbrains",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-67402a"
  },
  {
   "id": "pick-123",
   "tier": "pick",
   "category": "world",
   "title": "特朗普因伊朗威胁秘密换乘飞机引发质疑",
   "summary": "美媒报道称特朗普因伊朗威胁秘密换乘，记者等被允许乘坐总统专机，引发对‘诱饵’乘客的质疑。",
   "status": "发展中",
   "tags": [
    "地缘冲突"
   ],
   "context": "美国媒体报道称，总统因伊朗对其生命的威胁而秘密离开。",
   "detail": "据美国媒体报道，特朗普总统因伊朗威胁而秘密离开空军一号，据称是通过一辆餐饮卡车。与此同时，记者和其他人员被允许乘坐总统专机，这一做法被民主党人批评为使用‘诱饵’乘客，并引发了对安全措施和透明度的质疑。",
   "claims": [
    {
     "text": "报道称特朗普秘密换乘是为躲避伊朗威胁，但具体细节和动机仍需官方证实。",
     "kind": "uncertain",
     "sources": [
      "BBC World",
      "The Guardian"
     ]
    }
   ],
   "score": 74,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T15:53:53+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/videos/cj3672ljgzro?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    },
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/us-news/2026/aug/11/trump-air-force-one-deception-democrats",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-c53af1"
  },
  {
   "id": "pick-88",
   "tier": "pick",
   "category": "ai",
   "title": "OpenAI完成70亿美元员工股票回购",
   "summary": "OpenAI完成约70亿美元二级市场要约收购，允许员工在8520亿美元估值下变现持股，为IPO前流动性安排。",
   "status": "已确认",
   "tags": [
    "融资并购"
   ],
   "context": "该要约收购早在今年3月OpenAI完成1220亿美元融资时便已筹划。",
   "detail": "OpenAI完成了一轮约70亿美元的二级市场要约收购，允许现任及前任员工在8520亿美元估值下变现部分持股。此次交易未引入外部投资者，而是直接从员工手中回购股份。该交易为员工提供了IPO前的退出渠道，并缓解了估值攀升带来的股权流动性需求。",
   "score": 73,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T16:52:41+00:00",
   "sources": [
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779208",
     "type": "事实源"
    },
    {
     "name": "财联社·深度",
     "url": "https://www.cls.cn/detail/2451668",
     "type": "分析源"
    },
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/openai-lets-employees-cash-out-another-7-billion-in-stock/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-0b0793"
  },
  {
   "id": "pick-224",
   "tier": "pick",
   "category": "ai",
   "title": "美参议员桑德斯致信AI巨头要求暂停开发否则国会介入",
   "summary": "桑德斯致信OpenAI、Anthropic和Meta CEO，要求暂停AI开发，警告否则国会将强制介入。",
   "status": "发展中",
   "tags": [
    "监管政策"
   ],
   "context": "桑德斯援引这些公司关于风险过高时暂停开发的声明，认为风险阈值已到。",
   "detail": "美国参议员伯尼·桑德斯于8月10日致信OpenAI、Anthropic和Meta的首席执行官，要求暂停AI开发，并警告若企业不采取行动，国会将强制介入。他在信中援引这些公司关于风险过高时暂停开发的声明，认为该风险阈值最近已经达到，并直接点名三位CEO。",
   "claims": [
    {
     "text": "桑德斯认为风险阈值已达到，但这一判断基于其个人观点，并非公司共识。",
     "kind": "analysis",
     "sources": [
      "华尔街见闻"
     ]
    }
   ],
   "score": 73,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T20:31:48+00:00",
   "sources": [
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779220",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-5d9eba"
  },
  {
   "id": "pick-93",
   "tier": "pick",
   "category": "ai",
   "title": "Anthropic与比特币矿商Riot签署91亿美元数据中心协议",
   "summary": "Anthropic与Riot Platforms签署91亿美元、20年计算协议，租用德州Rockdale站点191兆瓦容量。",
   "status": "已确认",
   "tags": [
    "融资并购"
   ],
   "detail": "比特币矿商Riot Platforms与Anthropic达成一项价值91亿美元、为期20年的计算协议。根据协议，Anthropic将租用Riot位于德克萨斯州Rockdale站点的191兆瓦数据中心容量，并可能扩展。该交易标志着比特币矿商进一步向AI基础设施领域拓展。",
   "score": 72,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T19:08:16+00:00",
   "sources": [
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/11/riot-platforms-signs-anthropic-deal-as-miners-shift-to-ai-infrastructure-.html",
     "type": "事实源"
    },
    {
     "name": "The Decoder",
     "url": "https://the-decoder.com/anthropic-signs-9-1-billion-data-center-deal-with-bitcoin-miner-riot-platforms/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-9e221c"
  },
  {
   "id": "pick-124",
   "tier": "pick",
   "category": "world",
   "title": "黎巴嫩议会投票废除死刑成为中东首例",
   "summary": "黎巴嫩议会投票废除死刑，新法律待内阁批准，若通过将成为中东首个废除死刑的国家。",
   "status": "发展中",
   "tags": [
    "选举政治"
   ],
   "detail": "黎巴嫩议会投票通过废除死刑的法律，该法律下一步将提交内阁批准。如果最终通过，黎巴嫩将成为中东地区首个废除死刑的国家。",
   "score": 72,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T15:24:07+00:00",
   "sources": [
    {
     "name": "BBC World",
     "url": "https://www.bbc.co.uk/news/articles/c8enj8p1xwgo?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-ff0a28"
  },
  {
   "id": "pick-96",
   "tier": "pick",
   "category": "world",
   "title": "明尼苏达与威斯康星初选：进步派再受考验",
   "summary": "明尼苏达州和威斯康星州举行初选，进步派与温和派民主党人竞争，检验进步派候选人能否在11月获胜。",
   "status": "发展中",
   "tags": [
    "选举政治"
   ],
   "detail": "在明尼苏达州，进步派副州长Peggy Flanagan与温和派众议员Angie Craig竞争，以接替即将退休的参议员Tina Smith。威斯康星州也有竞争性初选。这些初选结果将影响11月中期选举的格局。",
   "score": 71,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T09:00:00+00:00",
   "sources": [
    {
     "name": "NPR",
     "url": "https://www.npr.org/2026/08/11/nx-s1-5927455/minnesota-wisconsin-primaries-hong-dsa-crowley-lindell-craig-flanagan-trump",
     "type": "事实源"
    },
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/11/minnesota-wisconsin-primaries-hong-flanagan-craig-run-in-key-races.html",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-777cca"
  },
  {
   "id": "pick-134",
   "tier": "pick",
   "category": "ai",
   "title": "科技业员工称AI未减工时反增至每周90小时",
   "summary": "科技公司员工表示，AI并未减少工作时间，反而每周工时高达90小时，与AI带来闲暇的承诺相悖。",
   "status": "已确认",
   "tags": [
    "劳动就业"
   ],
   "detail": "BBC中文报道指出，科技公司并未以自身实践证明AI能为人们带来更多闲暇时间。员工反映每周工作时间高达90小时，暗示AI可能增加了工作强度而非减少工时。",
   "claims": [
    {
     "text": "科技公司宣称AI能减少工作时间，但员工实际工时反而增加，表明技术承诺与现实存在差距。",
     "kind": "analysis",
     "sources": [
      "BBC中文"
     ]
    }
   ],
   "score": 71,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T08:37:49+00:00",
   "sources": [
    {
     "name": "BBC中文",
     "url": "https://www.bbc.com/zhongwen/articles/clyxr681dn7o/trad?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-b2d377"
  },
  {
   "id": "pick-135",
   "tier": "pick",
   "category": "society",
   "title": "中国单身男性陷闪婚骗局，反映人口结构危机",
   "summary": "中国单身男性陷入“闪婚”诈骗，BBC称此现象反映长期人口结构危机已走向极端。",
   "status": "已确认",
   "tags": [],
   "detail": "BBC中文报道称，“闪婚”诈骗现象反映出中国长期累积的人口结构危机已走向极端。单身男性在孤独与婚姻焦虑中成为受害者，但报道未提供具体案例细节。",
   "score": 68,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T07:58:58+00:00",
   "sources": [
    {
     "name": "BBC中文",
     "url": "https://www.bbc.com/zhongwen/articles/c0rdx0qd11eo/trad?at_medium=RSS&at_campaign=rss",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-35ebd2"
  },
  {
   "id": "pick-209",
   "tier": "pick",
   "category": "society",
   "title": "西班牙迎百年首次日全食，叠加英仙座流星雨",
   "summary": "西班牙大陆迎来121年来首次日全食，恰逢英仙座流星雨极大期，可能观测到流星划过日全食的奇景。",
   "status": "已确认",
   "tags": [
    "气候环境"
   ],
   "watch": "取决于天气状况和观测条件。可观察路标：日食带内的云量预报和流星雨观测报告。",
   "context": "日全食是西班牙大陆自1904年以来首次出现，英仙座流星雨每年在8月中旬达到极大。",
   "detail": "西班牙大陆将于8月12-13日迎来日全食，这是121年来的首次。与此同时，英仙座流星雨达到极大期，在日食带内可能看到流星划过日全食的罕见景象。果壳直播团队已赴西班牙全食带核心观测区进行直播。",
   "score": 64,
   "src_tier": "T1.5",
   "source_type": "分析源",
   "time": "2026-08-11T11:00:00+00:00",
   "sources": [
    {
     "name": "The Atlantic",
     "url": "https://www.theatlantic.com/science/2026/08/spain-eclipse/688243/?utm_source=feed",
     "type": "分析源"
    },
    {
     "name": "果壳·科学人",
     "url": "https://www.guokr.com/article/469899/",
     "type": "分析源"
    }
   ],
   "event_id": "evt-20260812-87bafa"
  },
  {
   "id": "pick-13",
   "tier": "pick",
   "category": "society",
   "title": "FBI警告：网络罪犯入侵账户窃取私密照片",
   "summary": "FBI发布警报，称网络罪犯正入侵受害者在线账户，窃取私密照片用于勒索活动。",
   "status": "已确认",
   "tags": [
    "安全隐私"
   ],
   "detail": "FBI在最新警报中表示，网络罪犯正针对成人和未成年人，试图窃取其个人和私密照片用于勒索活动。具体作案手法和规模未在摘要中详述。",
   "score": 63,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T19:38:23+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/11/fbi-says-cybercriminals-are-hacking-into-victims-online-accounts-to-steal-their-intimate-pictures/",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-83f4a0"
  },
  {
   "id": "pick-219",
   "tier": "pick",
   "category": "finance",
   "title": "英特尔200亿美元增发获美商务部支持，政府不认购",
   "summary": "英特尔宣布200亿美元股票增发，获美国商务部支持，但政府不参与认购，为AI扩张提供资金。",
   "status": "已确认",
   "tags": [
    "融资并购",
    "芯片算力"
   ],
   "context": "英特尔CEO Lip-Bu Tan在宣布增发前致电商务部长Howard Lutnick寻求背书，Lutnick表示认可。",
   "detail": "英特尔宣布200亿美元股票增发，规模从最初的150亿美元扩大。据Semafor援引知情人士，CEO Lip-Bu Tan在宣布前致电商务部长Howard Lutnick寻求支持，Lutnick认可但政府不参与认购。此次增发为英特尔AI扩张提供资金，也验证了Tan主导的战略转型获市场认可。",
   "score": 62,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T22:34:44+00:00",
   "sources": [
    {
     "name": "华尔街见闻",
     "url": "https://wallstreetcn.com/articles/3779218",
     "type": "事实源"
    }
   ],
   "event_id": "evt-20260812-8d36b9"
  },
  {
   "id": "more-6",
   "tier": "more",
   "category": "tech",
   "title": "GitHub支持自动迁移分支保护规则到规则集",
   "status": "",
   "tags": [],
   "score": 70,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T19:03:57+00:00",
   "sources": [
    {
     "name": "GitHub Changelog",
     "url": "https://github.blog/changelog/2026-08-11-automatically-migrate-branch-protection-rules-to-repository-rulesets",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-201",
   "tier": "more",
   "category": "tech",
   "title": "Vercel Connect新增可观测性支持",
   "status": "",
   "tags": [],
   "score": 70,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T22:00:00+00:00",
   "sources": [
    {
     "name": "Vercel Blog",
     "url": "https://vercel.com/changelog/vercel-connect-adds-observability-support",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-18",
   "tier": "more",
   "category": "ai",
   "title": "OpenAI长期高管Brad Lightcap宣布离职创业",
   "status": "",
   "tags": [],
   "score": 69,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T19:41:17+00:00",
   "sources": [
    {
     "name": "CNBC",
     "url": "https://www.cnbc.com/2026/08/11/longtime-openai-executive-brad-lightcap-leaves-as-shakeup-at-ai-lab-continues.html",
     "type": "事实源"
    },
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/11/brad-lightcap-openais-longtime-coo-is-leaving-to-start-something-new/",
     "type": "事实源"
    },
    {
     "name": "The Verge",
     "url": "https://www.theverge.com/ai-artificial-intelligence/978048/brad-lightcap-openai-executive-departure",
     "type": "事实源"
    },
    {
     "name": "IT之家",
     "url": "https://www.ithome.com/0/988/556.htm",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-19",
   "tier": "more",
   "category": "ai",
   "title": "General Catalyst领投River AI 11亿美元融资",
   "status": "",
   "tags": [],
   "score": 68,
   "src_tier": "T1.5",
   "source_type": "事实源",
   "time": "2026-08-11T17:41:22+00:00",
   "sources": [
    {
     "name": "TechCrunch",
     "url": "https://techcrunch.com/2026/08/11/general-catalyst-leads-1-1b-round-into-2-month-old-river-ai/",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-2",
   "tier": "more",
   "category": "ai",
   "title": "Hugging Face博客提出用更少令牌实现ACE",
   "status": "",
   "tags": [],
   "score": 68,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T13:37:10+00:00",
   "sources": [
    {
     "name": "Hugging Face Blog",
     "url": "https://huggingface.co/blog/ibm-research/altk-evolve-sldd",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-161",
   "tier": "more",
   "category": "world",
   "title": "联邦法官扩大禁令，阻止美国邮政执行特朗普限制邮寄投票的行政令",
   "status": "",
   "tags": [],
   "score": 68,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T21:39:55+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/us-news/2026/aug/11/judge-blocks-trump-mail-in-voting-usps",
     "type": "事实源"
    },
    {
     "name": "NPR",
     "url": "https://www.npr.org/2026/08/11/nx-s1-5928383/trump-mail-in-voting-executive-order-usps",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-167",
   "tier": "more",
   "category": "world",
   "title": "人权组织起诉特朗普政府‘严厉’国际刑事法院制裁",
   "status": "",
   "tags": [],
   "score": 67,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T15:10:16+00:00",
   "sources": [
    {
     "name": "The Guardian",
     "url": "https://www.theguardian.com/us-news/2026/aug/11/human-rights-groups-trump-lawsuit-icc-sanctions",
     "type": "事实源"
    }
   ]
  },
  {
   "id": "more-204",
   "tier": "more",
   "category": "ai",
   "title": "Vercel报告称AI模型网络攻击能力显著增强",
   "status": "",
   "tags": [],
   "score": 67,
   "src_tier": "T1",
   "source_type": "事实源",
   "time": "2026-08-11T07:00:00+00:00",
   "sources": [
    {
     "name": "Vercel Blog",
     "url": "https://vercel.com/blog/everything-hackable-will-get-hacked",
     "type": "事实源"
    }
   ]
  }
 ],
 "themes": [
  {
   "title": "AI产业狂飙与争议",
   "one_liner": "AI巨头融资、模型发布与商业化加速，同时引发安全、监管与工作负荷争议。",
   "member_ids": [
    "pick-32",
    "pick-28",
    "pick-73",
    "pick-80",
    "pick-8",
    "pick-110",
    "pick-205",
    "pick-192"
   ]
  },
  {
   "title": "中东地缘冲突升级",
   "one_liner": "叙利亚、伊朗、美军行动与特朗普安全事件交织，地区紧张加剧。",
   "member_ids": [
    "pick-126",
    "pick-104",
    "pick-116",
    "pick-123",
    "pick-121"
   ]
  },
  {
   "title": "极端天气与自然灾害",
   "one_liner": "哥伦比亚强震与台风白海豚造成重大伤亡和疏散，全球灾害频发。",
   "member_ids": [
    "pick-115",
    "pick-200"
   ]
  }
 ],
 "deep": [
  {
   "id": "deep-a2a745e3",
   "title": "Stealing Reasoning Traces from Proprietary LLM APIs",
   "title_zh": "从专有LLM API窃取推理痕迹",
   "url": "https://simonwillison.net/2026/Aug/11/stealing-reasoning-traces/#atom-everything",
   "source": "Simon Willison",
   "channel": "ai_engineering",
   "lang": "en",
   "brief": "论文揭示Anthropic、OpenAI、Google返回加密思维链块，存在被窃取风险。",
   "why": "涉及AI安全与隐私核心议题，对理解闭源模型内部机制和风险有实质增量。",
   "key_points": [
    "闭源LLM API返回加密思维链，但可被攻击者窃取。",
    "该漏洞影响Anthropic、OpenAI、Google等主流服务。",
    "论文提供具体技术细节，对AI安全研究有参考价值。"
   ],
   "audience": "AI开发者、安全研究者、关注模型隐私的技术人员。",
   "takeaway": "闭源模型的思维链并非绝对安全，需警惕推理过程泄露风险。",
   "score": 8,
   "read_minutes": 3,
   "content_type": "analysis"
  },
  {
   "id": "deep-bc5a2869",
   "title": "Nvidia’s Risky Business",
   "title_zh": "英伟达的风险生意",
   "url": "https://stratechery.com/2026/nvidias-risky-business/",
   "source": "Stratechery",
   "channel": "tech_business",
   "lang": "en",
   "brief": "英伟达帮助客户融资，扩大AI建设风险。",
   "why": "深入分析AI基础设施融资模式，对理解产业泡沫和风险有独到洞察。",
   "key_points": [
    "英伟达通过新方式帮助客户筹集资金。",
    "此举显著扩大AI建设整体风险。",
    "对AI投资可持续性提出质疑。"
   ],
   "audience": "关注AI产业经济、投资风险的分析师和从业者。",
   "takeaway": "AI建设热潮中，融资创新可能放大系统性风险。",
   "score": 8,
   "read_minutes": 17,
   "content_type": "analysis"
  },
  {
   "id": "deep-4284a72c",
   "title": "How well does AI peer review work?",
   "title_zh": "AI同行评审效果如何？",
   "url": "https://marginalrevolution.com/marginalrevolution/2026/08/how-well-does-ai-peer-review-work.html?utm_source=rss&utm_medium=rss&utm_campaign=how-well-does-ai-peer-review-work",
   "source": "Marginal Revolution",
   "channel": "society_finance",
   "lang": "en",
   "brief": "实验将100个已知错误植入论文，测试AI评审工具检出率。",
   "why": "提供AI评审能力的实证数据，对学术工具应用有参考价值。",
   "key_points": [
    "最佳AI系统检出71个错误。",
    "实验设计严谨，覆盖前沿模型和商业工具。",
    "结果对AI辅助学术评审有实际意义。"
   ],
   "audience": "学术研究者、AI工具开发者。",
   "takeaway": "AI评审能有效发现错误，但非完美，需结合人工。",
   "score": 8,
   "read_minutes": 3,
   "content_type": "analysis"
  },
  {
   "id": "deep-8aaf1cb2",
   "title": "Introducing Muse Glimmer",
   "title_zh": "Meta发布开源模型Muse Glimmer",
   "url": "https://simonwillison.net/2026/Aug/10/introducing-muse-glimmer/#atom-everything",
   "source": "Simon Willison",
   "channel": "ai_engineering",
   "lang": "en",
   "brief": "Meta推出30B参数开源模型Muse Glimmer，采用Apache 2.0许可。",
   "why": "开源模型新进展，对AI工具应用和学习路线有直接影响，值得关注。",
   "key_points": [
    "Muse Glimmer为30B参数，Apache 2.0许可。",
    "相比Llama许可更宽松，利于商业使用。",
    "可在单张RTX 3090上运行，降低硬件门槛。"
   ],
   "audience": "AI开发者、开源爱好者、全栈工程师。",
   "takeaway": "开源模型许可和硬件要求是实际应用的关键考量。",
   "score": 7,
   "read_minutes": 3,
   "content_type": "reporting"
  }
 ],
 "papers": [
  {
   "id": "paper-2608.09802",
   "title": "SWE-Bench ProMax: Benchmarking Agents on Large-Scale Multilingual Code Refactoring",
   "title_zh": "SWE-Bench ProMax：大规模多语言代码重构基准",
   "url": "https://huggingface.co/papers/2608.09802",
   "arxiv_id": "2608.09802",
   "brief": "构建多语言大规模代码重构基准，评估AI编码智能体能力。",
   "why": "直接关联前端/全栈工程，了解AI编码工具的实际边界，指导工具选型。",
   "contribution": "提供严格筛选的多语言重构基准，揭示当前AI编码智能体在大规模重构任务上的未解难题。",
   "evidence": "基于SWE-Bench扩展，包含多语言任务，实验显示现有智能体性能显著不足。",
   "limitations": "基准任务可能偏重特定重构场景，不代表所有编码任务。",
   "takeaway": "AI编码工具在复杂重构上仍有限，工程中应合理预期并保留人工审查。",
   "score": 8,
   "upvotes": 116,
   "has_code": false
  },
  {
   "id": "paper-2608.08311",
   "title": "Ouroboros: A Self-Developing Frontier Coding Agent with Reviewed Core Evolution",
   "title_zh": "Ouroboros：自进化编码智能体",
   "url": "https://huggingface.co/papers/2608.08311",
   "arxiv_id": "2608.08311",
   "brief": "提出自进化编码智能体，通过审查提交改进自身工具与核心。",
   "why": "展示AI工具自我改进的潜力，对自动化管线设计有启发。",
   "contribution": "实现智能体核心代码通过审查提交持续进化，形成运行时闭环。",
   "evidence": "开源代码，实验显示在编码任务上性能随进化提升。",
   "limitations": "自进化可能引入不稳定，需谨慎控制审查质量。",
   "takeaway": "可探索让AI工具自我迭代，但需建立可靠审查机制。",
   "score": 8,
   "upvotes": 66,
   "has_code": true
  },
  {
   "id": "paper-2608.07169",
   "title": "Agent Memory Distillation: Empowering Small LLM Agents with Hierarchical Teacher Memory",
   "title_zh": "Agent记忆蒸馏：小模型工具调用增强",
   "url": "https://huggingface.co/papers/2608.07169",
   "arxiv_id": "2608.07169",
   "brief": "将大模型教师的分层记忆蒸馏给小模型，无需额外训练。",
   "why": "对资源受限的前端项目有用，可提升小模型工具使用能力。",
   "contribution": "提出分层记忆蒸馏方法，显著提升小LLM智能体工具调用性能。",
   "evidence": "开源代码，实验显示在多个工具使用基准上性能提升。",
   "limitations": "依赖教师模型质量，记忆结构可能不通用。",
   "takeaway": "可借鉴记忆蒸馏思路，在轻量级应用中增强小模型能力。",
   "score": 7,
   "upvotes": 31,
   "has_code": true
  },
  {
   "id": "paper-2608.08097",
   "title": "OasisKV: Scaling In-Decode KV Cache Beyond HBM with Lookahead Sparse Prefetching",
   "title_zh": "OasisKV：KV缓存外置与预取优化",
   "url": "https://huggingface.co/papers/2608.08097",
   "arxiv_id": "2608.08097",
   "brief": "将KV缓存存于低层内存，通过预取提升LLM推理吞吐。",
   "why": "理解LLM推理优化，对部署高效AI服务有直接价值。",
   "contribution": "提出前瞻稀疏预取方法，突破HBM限制，提升推理吞吐。",
   "evidence": "实验显示在长上下文场景下吞吐显著提升。",
   "limitations": "依赖预测准确性，预取失败可能影响性能。",
   "takeaway": "关注KV缓存优化技术，可降低LLM服务成本。",
   "score": 7,
   "upvotes": 16,
   "has_code": false
  }
 ],
 "opinion": [
  {
   "id": "op-c138cf72",
   "platform": "微博",
   "word": "桑德斯要求三大AI公司暂停开发",
   "title": "桑德斯要求三大AI公司暂停开发",
   "why_hot": "美国参议员桑德斯公开要求OpenAI等三大AI公司暂停开发，引发关于AI安全与监管的公共辩论，涉及科技巨头与政策博弈。",
   "emotion": "公众对AI失控风险的焦虑，以及对科技巨头权力扩张的警惕。",
   "mechanism": "政治人物言论经社交媒体放大，触发科技圈与政策圈联动讨论，算法助推争议性议题扩散。",
   "url": "https://s.weibo.com/weibo?q=%23%E6%A1%91%E5%BE%B7%E6%96%AF%E8%A6%81%E6%B1%82%E4%B8%89%E5%A4%A7AI%E5%85%AC%E5%8F%B8%E6%9A%82%E5%81%9C%E5%BC%80%E5%8F%91%23"
  },
  {
   "id": "op-815173dc",
   "platform": "微博",
   "word": "高考444分考生回应被殡葬专业录取",
   "title": "高考444分考生回应被殡葬专业录取",
   "why_hot": "高考生以444分被殡葬专业录取并公开回应，触及青年就业选择、冷门专业价值与社会偏见，引发关于教育与职业路径的讨论。",
   "emotion": "对传统职业观念的反思，青年对多元就业的探索与认同，以及社会对冷门专业的重新审视。",
   "mechanism": "个人故事经微博话题运营推上热榜，引发教育类KOL与普通用户互动，形成情感共鸣与观点交锋。",
   "url": "https://s.weibo.com/weibo?q=%23%E9%AB%98%E8%80%83444%E5%88%86%E8%80%83%E7%94%9F%E5%9B%9E%E5%BA%94%E8%A2%AB%E6%AE%A1%E8%91%AC%E4%B8%93%E4%B8%9A%E5%BD%95%E5%8F%96%23"
  },
  {
   "id": "op-7fd67a45",
   "platform": "微博",
   "word": "日本篡改历史被反噬了",
   "title": "日本篡改历史被反噬了",
   "why_hot": "日本历史篡改事件引发国际舆论反弹，涉及历史认知、民族情绪与地缘政治，具有公共讨论价值。",
   "emotion": "对历史正义的坚持，民族情感被触动，以及对日本右翼行为的愤怒与警惕。",
   "mechanism": "国际新闻经微博话题聚合，结合历史记忆与民族情绪，算法推荐至热榜，形成跨平台讨论。",
   "url": "https://s.weibo.com/weibo?q=%23%E6%97%A5%E6%9C%AC%E7%AF%A1%E6%94%B9%E5%8E%86%E5%8F%B2%E8%A2%AB%E5%8F%8D%E5%99%AC%E4%BA%86%23"
  }
 ]
};
