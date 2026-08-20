import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


ROOT = Path(__file__).resolve().parents[2]
DAILY_DIR = ROOT / "source" / "news" / "data" / "daily"
DATA_DIR = DAILY_DIR.parent

REPAIRED_TITLES = {
    ("2026-07-23", "pick-61"): "OpenAI模型逃逸沙盒并入侵Hugging Face生产环境",
    ("2026-07-23", "pick-24"): "美财政部威胁制裁，称月之暗面蒸馏Anthropic模型",
    ("2026-07-23", "pick-54"): "NTT DATA用ChatGPT和Codex将事件分析缩短至30分钟",
    ("2026-07-24", "pick-120"): "AMD发布Helios AI服务器，预测2030年AI加速器市场达1.4万亿美元",
    ("2026-07-24", "pick-29"): "Google Gemini月活接近10亿，市场份额升至27.7%",
    ("2026-07-24", "pick-18"): "Anthropic扩展Claude语音模式至Opus、Sonnet和Haiku",
    ("2026-07-24", "pick-66"): "北京智能体新政首次写入Harness Engineering",
    ("2026-07-24", "pick-60"): "OpenAI Workspace Agents曝AgentForger漏洞",
    ("2026-07-24", "pick-44"): "美国国会提出AI Kill Switch法案，授权关闭失控AI系统",
    ("2026-07-24", "pick-4"): "GitHub Mobile支持用Copilot修复失败的Actions检查",
    ("2026-07-25", "pick-2"): "Anthropic发布Claude Opus 5，性能接近Fable 5",
    ("2026-07-25", "pick-97"): "美国指控月之暗面蒸馏Anthropic模型开发Kimi K3",
    ("2026-07-25", "pick-7"): "Anthropic发布Drone-Bench评估AI操控无人机",
    ("2026-07-25", "pick-5"): "Anthropic为Claude 5代模型精简超80%系统提示词",
}


def _load_daily(path):
    raw = path.read_text(encoding="utf-8")
    match = re.search(r"window\.NEWS_DATA\[[^\]]+\] = (\{.*\});\s*$", raw, re.S)
    assert match, f"{path} has an invalid wrapper"
    return json.loads(match.group(1))


def test_legacy_quality_accepts_missing_same_day_duplicate_fields():
    payload = {
        "date": "2026-07-22",
        "quality": {
            "audited_events": 1,
            "split_events": 0,
            "removed_fields": 0,
            "degraded": False,
        },
        "items": [],
    }

    assert dn.validate_daily_payload(payload) == []
    payload["quality"]["enrichment_audited_events"] = -1
    assert any(
        "enrichment_audited_events" in error
        for error in dn.validate_daily_payload(payload))


def test_fetch_failure_logs_never_carry_the_rsshub_secret(monkeypatch):
    """resolve_rsshub_sources 把 ACCESS_KEY 拼进 query，抓取失败时异常会带上整条 URL。

    公开仓库的 Actions 日志里，唯一的防线是 GitHub 的 secret 自动打码——一旦值被
    转义或截断就失效。日志脱敏必须在我们自己这一侧。
    """
    monkeypatch.setenv("RSSHUB_BASE", "https://rsshub.example.internal")
    monkeypatch.setenv("RSSHUB_KEY", "s3cr3t-key-value")

    samples = [
        "HTTPSConnectionPool(host='rsshub.example.internal', port=443): "
        "Max retries exceeded with url: /twitter/user/x?key=s3cr3t-key-value",
        "HTTPError for https://rsshub.example.internal/x?limit=5&key=s3cr3t-key-value",
    ]
    for sample in samples:
        redacted = dn.redact(sample)
        assert "s3cr3t-key-value" not in redacted, sample
        assert "rsshub.example.internal" not in redacted, sample
        assert "[redacted]" in redacted


def test_a_base_without_a_scheme_is_skipped_like_an_unset_one(monkeypatch):
    """守卫只判空会漏掉「配错了」——而运维现场产生的正是错值，不是空值。

    2026-08-20 迁仓重配 secret 时 RSSHUB_BASE 漏了 https://，占位符替换出
    `rsshub.example.internal/cls/depth`，requests 报 "No scheme supplied"。
    未配置时有跳过分支，配错时却把非法 URL 直接喂进抓取，于是错误以「抓取失败」
    而不是「跳过」的面目出现，排查方向差了一截；当天六个自建源全灭。
    """
    sources = [{"id": "cls-depth", "name": "cls", "url": "{rsshub}/cls/depth"}]
    monkeypatch.setenv("RSSHUB_KEY", "")

    for bad in ("rsshub.example.internal", "//rsshub.example.internal",
                "ftp://rsshub.example.internal", "  "):
        monkeypatch.setenv("RSSHUB_BASE", bad)
        assert dn.resolve_rsshub_sources(sources) == [], bad

    for good in ("https://rsshub.example.internal",
                 "http://rsshub.example.internal/"):
        monkeypatch.setenv("RSSHUB_BASE", good)
        resolved = dn.resolve_rsshub_sources(sources)
        assert len(resolved) == 1, good
        assert resolved[0]["url"] == good.rstrip("/") + "/cls/depth"


def test_publication_gate_rejects_non_http_source_urls():
    """前端 safeUrl 挡住了页面，但 feed.xml 的 <item><link> 是原样输出的。

    协议校验必须在发布闸门上 fail-closed，而不是靠每个消费端各自兜底。
    """
    def payload_with(url):
        return {
            "date": "2026-07-22",
            "quality": {
                "audited_events": 1,
                "split_events": 0,
                "removed_fields": 0,
                "degraded": False,
            },
            "items": [{
                "id": "pick-1",
                "title": "标题",
                "sources": [{"name": "来源", "url": url}],
            }],
        }

    for url in (
            "javascript:alert(1)", "data:text/html,x", "//example.com", "ftp://x/y", "",
            "https://", "https://not a url", "https://example.com:bad/path"):
        assert any(
            "source URL must be http(s)" in error
            for error in dn.validate_daily_payload(payload_with(url))
        ), url

    assert dn.validate_daily_payload(payload_with("https://example.com/a")) == []


def test_publication_gate_rejects_invalid_deep_urls():
    payload = {
        "date": "2026-07-22",
        "quality": {
            "audited_events": 1,
            "split_events": 0,
            "removed_fields": 0,
            "degraded": False,
        },
        "items": [],
        "deep": [{
            "id": "deep-1",
            "title": "Deep read",
            "url": "javascript:alert(1)",
        }],
    }

    assert any(
        "deep deep-1 URL must be http(s)" in error
        for error in dn.validate_daily_payload(payload))


def test_feed_falls_back_for_invalid_urls_in_legacy_daily_files(tmp_path):
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    payload = {
        "date": "2026-07-22",
        "generated_at": "2026-07-22T05:00:00+00:00",
        "items": [{
            "id": "pick-1",
            "tier": "pick",
            "category": "tech",
            "title": "Item",
            "summary": "Summary",
            "sources": [{"name": "Source", "url": "javascript:alert(1)"}],
        }],
        "deep": [{
            "id": "deep-1",
            "title": "Deep read",
            "url": "https://",
        }],
    }
    (daily_dir / "2026-07-22.js").write_text(
        'window.NEWS_DATA["2026-07-22"] = '
        f'{json.dumps(payload, ensure_ascii=False)};\n',
        encoding="utf-8")

    dn.write_feed(tmp_path, "2026-07-22", {
        "feed_days": 7,
        "site_url": "https://example.com",
    })

    feed = ET.parse(tmp_path / "feed.xml")
    assert [
        item.findtext("link") for item in feed.findall("./channel/item")
    ] == ["https://example.com/news/", "https://example.com/news/"]
    assert "javascript:" not in (tmp_path / "feed.xml").read_text(encoding="utf-8")


def test_quality_health_backfills_enrichment_audits_from_daily_pick_count(tmp_path):
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    (daily_dir / "2026-07-23.js").write_text(
        'window.NEWS_DATA["2026-07-23"] = not-json;\n',
        encoding="utf-8")
    (daily_dir / "2026-07-24.js").write_text(
        'window.NEWS_DATA["2026-07-24"] = '
        '{"date":"2026-07-24","stats":{"pick_count":36}};\n',
        encoding="utf-8")
    (tmp_path / "quality-health.json").write_text(json.dumps({
        "version": 1,
        "records": [
            {"date": "2026-07-23", "audited_events": 40, "removed_fields": 50},
            {"date": "2026-07-24", "audited_events": 42, "removed_fields": 69},
        ],
    }), encoding="utf-8")

    health = dn.update_quality_health(
        tmp_path, "2026-07-25",
        {**dn.new_quality_stats(), "enrichment_audited_events": 34})
    records = {row["date"]: row for row in health["records"]}

    assert "enrichment_audited_events" not in records["2026-07-23"]
    assert records["2026-07-24"]["enrichment_audited_events"] == 36
    assert records["2026-07-25"]["enrichment_audited_events"] == 34


def test_quality_health_writes_allowlisted_usage_deterministically(tmp_path):
    usage = {
        "date": "overwritten",
        "llm_output_tokens": 30,
        "llm_calls": 4,
        "llm_cost_known": True,
        "llm_cost_usd": 0.0123,
        "llm_cached_input_tokens": 20,
        "llm_input_tokens": 100,
        "private_detail": "must not persist",
    }
    quality = {**dn.new_quality_stats(), "audited_events": 2}

    first = dn.update_quality_health(
        tmp_path, "2026-07-25", quality, usage=usage)
    first_bytes = (tmp_path / "quality-health.json").read_bytes()
    second = dn.update_quality_health(
        tmp_path, "2026-07-25", quality, usage=dict(reversed(usage.items())))
    second_bytes = (tmp_path / "quality-health.json").read_bytes()

    assert first == second
    assert first_bytes == second_bytes
    row = second["records"][0]
    assert row["date"] == "2026-07-25"
    assert {
        key: row[key] for key in (
            "llm_calls", "llm_input_tokens", "llm_cached_input_tokens",
            "llm_output_tokens", "llm_cost_usd", "llm_cost_known",
        )
    } == {
        "llm_calls": 4,
        "llm_input_tokens": 100,
        "llm_cached_input_tokens": 20,
        "llm_output_tokens": 30,
        "llm_cost_usd": 0.0123,
        "llm_cost_known": True,
    }
    assert "private_detail" not in row


def test_all_daily_claims_and_themes_reference_published_rows():
    failures = []
    for path in sorted(DAILY_DIR.glob("*.js")):
        payload = _load_daily(path)
        rows = payload.get("items") or []
        item_ids = [row.get("id") for row in rows if isinstance(row, dict)]
        if len(item_ids) != len(set(item_ids)):
            failures.append(f"{path.name}: duplicate item ids")
        valid_ids = set(item_ids)
        for row in rows:
            names = {
                source.get("name") for source in (row.get("sources") or [])
                if isinstance(source, dict)
            }
            for claim in row.get("claims") or []:
                unknown = [
                    source for source in claim.get("sources") or []
                    if source not in names
                ]
                if unknown:
                    failures.append(
                        f"{path.name}:{row.get('id')} unknown claim sources {unknown}")
        for theme in payload.get("themes") or []:
            unknown = [
                item_id for item_id in theme.get("member_ids") or []
                if item_id not in valid_ids
            ]
            if unknown:
                failures.append(
                    f"{path.name}: unknown theme members {unknown}")

    assert failures == []


def test_repaired_titles_match_daily_registry_feed_and_search_index():
    daily_titles = {}
    for date in {date for date, _item_id in REPAIRED_TITLES}:
        payload = _load_daily(DAILY_DIR / f"{date}.js")
        daily_titles.update({
            (date, item["id"]): item["title"]
            for item in payload.get("items") or []
        })
    assert {
        key: daily_titles.get(key) for key in REPAIRED_TITLES
    } == REPAIRED_TITLES

    registry = json.loads(
        (DATA_DIR / "events.json").read_text(encoding="utf-8"))
    registered = {}
    # An event's own title tracks its newest update, so it only has to match a
    # repaired row while that row is still the line's latest one.
    latest_registered = {}
    for event in registry.get("events") or []:
        history = event.get("history") or []
        latest_ref = max(
            history, key=lambda row: str(row.get("date") or ""),
            default={}).get("item_ref", "")
        for row in history:
            item_ref = row.get("item_ref", "")
            if ":" not in item_ref:
                continue
            date, item_id = item_ref.split(":", 1)
            key = (date, item_id)
            if key in REPAIRED_TITLES:
                registered[key] = row.get("title")
                if item_ref == latest_ref:
                    latest_registered[key] = event.get("title")
    assert registered == REPAIRED_TITLES
    assert latest_registered == {
        key: REPAIRED_TITLES[key] for key in latest_registered
    }

    index_raw = (DATA_DIR / "search_index.js").read_text(encoding="utf-8")
    index_match = re.fullmatch(
        r"window\.NEWS_INDEX = (\[.*\]);\s*", index_raw, re.S)
    assert index_match
    index_titles = {
        (row[0], row[1]): row[4]
        for row in json.loads(index_match.group(1))
        if len(row) >= 5
    }
    assert {
        key: index_titles.get(key) for key in REPAIRED_TITLES
    } == REPAIRED_TITLES

    feed = ET.parse(DATA_DIR / "feed.xml")
    feed_titles = {
        tuple(item.findtext("guid").split(":", 1)): item.findtext("title")
        for item in feed.findall("./channel/item")
        if ":" in (item.findtext("guid") or "")
    }
    feed_dates = {date for date, _item_id in feed_titles}
    repaired_titles_in_feed_window = {
        key: title for key, title in REPAIRED_TITLES.items()
        if key[0] in feed_dates
    }
    assert all(
        feed_titles[key].endswith(title)
        for key, title in repaired_titles_in_feed_window.items()
    )
