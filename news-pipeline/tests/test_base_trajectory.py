import json
import inspect
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


def test_default_watch_limit_is_90_characters():
    assert dn.OBJECTIVITY_FIELD_LIMITS["watch"] == 90
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["watch"] == 90
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["watch_detail"] == 260
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["context"] == 240
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["detail"] == 1200


class EnrichLLM:
    def __init__(self, response):
        self.response = response
        self.system = ""

    def json_call(self, system, _user):
        self.system = system
        return [dict(self.response)]


class RejectWatchAuditLLM:
    def __init__(self):
        self.system = ""

    def json_call(self, _system, _user):
        self.system = _system
        return {
            "fields": {
                "why": True,
                "context": True,
                "watch": False,
                "watch_detail": False,
            },
            "supported_claim_indexes": [],
        }


def _source_item():
    return {
        "title": "Factory begins pilot production",
        "desc": "The pilot starts this month and full production depends on yield tests.",
        "source": "Example Wire",
        "source_id": "example-wire",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "url": "https://example.test/factory",
        "time": "2026-07-21T01:00:00+00:00",
        "evidence_text": "The pilot starts this month and full production depends on yield tests.",
        "evidence_basis": "fulltext",
    }


def _event():
    return {
        "ids": [0],
        "category": "tech",
        "title": "Factory pilot",
        "score": 90,
        "tier": "T1",
    }


@pytest.mark.parametrize("mode", ["shadow", "active"])
def test_fulltext_enrich_uses_deep_reader_limits_without_significance(
        mode, monkeypatch):
    monkeypatch.setitem(dn.OBJECTIVITY_FIELD_LIMITS, "context", 11)
    monkeypatch.setitem(dn.OBJECTIVITY_FIELD_LIMITS, "watch", 17)
    monkeypatch.setitem(dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS, "context", 41)
    monkeypatch.setitem(dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS, "watch", 17)
    monkeypatch.setitem(dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS, "watch_detail", 61)
    response = {
        "idx": 0,
        "title": "Factory pilot expands",
        "summary": "Pilot production has begun.",
        "why": "The result affects the production timetable.",
        "context": "c" * 40,
        "context_evidence": [{
            "source_index": 0,
            "quote": "full production depends on yield tests",
        }],
        "watch": "w" * 120,
        "watch_detail": "d" * 60,
        "claims": [],
        "status": "发展中",
        "tags": [],
    }
    llm = EnrichLLM(response)
    event = _event()

    dn.enrich(llm, [event], [_source_item()], {
        "_objectivity_runtime_mode": mode,
        "topic_tags": [],
        "detail": {"enabled": False},
    })

    assert len(event["context"]) == 40
    assert "significance" not in event
    assert "significance" not in llm.system
    assert "why" not in event
    assert "- why:" not in llm.system
    assert "读者兴趣画像" not in llm.system
    assert "watch" not in event
    assert "watch_detail" not in event
    assert "≤17字" in llm.system
    assert "watch_detail" in llm.system
    assert "普通条目约 250-600 字" not in llm.system  # detail disabled in this fixture


def test_interim_enrich_keeps_short_contract_and_omits_watch_detail():
    llm = EnrichLLM({
        "idx": 0,
        "title": "Factory pilot expands",
        "summary": "Pilot production has begun.",
        "why": "The result affects the production timetable.",
        "context": "",
        "context_evidence": [],
        "watch": "Watch the next yield report.",
        "watch_detail": "This field must be ignored in interim mode.",
        "claims": [],
        "status": "发展中",
        "tags": [],
    })
    event = _event()

    dn.enrich(llm, [event], [_source_item()], {
        "_objectivity_runtime_mode": "interim",
        "topic_tags": [],
        "detail": {"enabled": False},
    })

    assert event["watch"] == "Watch the next yield report."
    assert "why" not in event
    assert "watch_detail" not in event
    assert "watch_detail" not in llm.system


def _snippet_source_item():
    """A source whose article body was never fetched — the RSS blurb is all there is."""
    item = _source_item()
    item.pop("evidence_text", None)
    item["evidence_basis"] = "snippet"
    return item


def _enrich_response(**overrides):
    return {
        "idx": 0,
        "title": "Factory pilot expands",
        "summary": "Pilot production has begun.",
        "why": "The result affects the production timetable.",
        "context": "",
        "context_evidence": [],
        "watch": "Watch the next yield report.",
        "detail": "The factory has started pilot production.",
        "claims": [],
        "status": "发展中",
        "tags": [],
        **overrides,
    }


def _interim_cfg():
    return {
        "_objectivity_runtime_mode": "interim",
        "topic_tags": [],
        "detail": {"enabled": True, "max_chars": 1000},
    }


def test_snippet_tier_prompt_does_not_use_fulltext_depth_contract():
    """写作目标跟着材料走：只有 RSS 摘要时不得下达全文档的深度目标（ADR 0020）。"""
    llm = EnrichLLM(_enrich_response())

    dn.enrich(llm, [_event()], [_snippet_source_item()], _interim_cfg())

    assert "现状短叙述" in llm.system
    assert "普通条目约 250-600 字" not in llm.system
    assert "利益相关方变化和未决事实" not in llm.system


def test_interim_event_with_fetched_fulltext_earns_the_depth_contract():
    """材料等级决定合同，发布模式不决定。

    ADR 0016 把 `objectivity.mode` 永久钉在 interim，此前这让 ADR 0015 的证据分级
    成为永不执行的死代码。分层之后，interim 里抓到正文的条目照样拿全文材料档合同。
    """
    llm = EnrichLLM(_enrich_response())

    dn.enrich(llm, [_event()], [_source_item()], _interim_cfg())

    assert "利益相关方变化和未决事实" in llm.system
    assert "现状短叙述" not in llm.system


def test_snippet_tier_neither_asks_for_nor_keeps_a_watch():
    """摘要材料里几乎没有可观察路标，模板句是通过审计的形状而不是内容（ADR 0020）。"""
    llm = EnrichLLM(_enrich_response())
    event = _event()

    dn.enrich(llm, [event], [_snippet_source_item()], _interim_cfg())

    assert "watch" not in llm.system
    assert "watch" not in event


def test_material_tier_is_per_event_within_one_interim_run():
    """同一次运行里两档并存，各用各的提示词，批次下标仍指向真实的 picked 位置。"""
    systems = []

    class RecordingLLM:
        def json_call(self, system, user):
            systems.append((system, user))
            return []

    picked = [{**_event(), "ids": [0]}, {**_event(), "ids": [1]}]
    dn.enrich(RecordingLLM(), picked,
              [_source_item(), _snippet_source_item()], _interim_cfg())

    assert len(systems) == 2
    rich_system, rich_user = systems[0]
    snippet_system, snippet_user = systems[1]
    assert "利益相关方变化和未决事实" in rich_system
    assert "现状短叙述" in snippet_system
    assert "事件[0]" in rich_user
    assert "事件[1]" in snippet_user


def test_fulltext_tier_still_asks_for_and_keeps_a_watch():
    """停走向只针对摘要材料档；抓到正文的条目仍然要给出可观察路标（ADR 0020）。"""
    llm = EnrichLLM(_enrich_response())
    event = _event()

    dn.enrich(llm, [event], [_source_item()], _interim_cfg())

    assert "- watch: 走向" in llm.system
    assert event["watch"] == "Watch the next yield report."


class _ArticleResponse:
    def __init__(self, body=b"<html>ok</html>"):
        self.body = body
        self.status_code = 200
        self.headers = {"Content-Type": "text/html; charset=utf-8",
                        "Content-Length": str(len(body))}

    def iter_content(self, chunk_size=65536):
        for pos in range(0, len(self.body), chunk_size):
            yield self.body[pos:pos + chunk_size]

    def close(self):
        pass


def _public_dns(_host, *_args, **_kwargs):
    return [(2, 1, 6, "", ("93.184.216.34", 0))]


def test_only_the_nominated_picks_reach_the_fulltext_tier():
    """接线测试：候选 → 抓取 → 档位判定这条链，而不只是候选函数本身。

    只有被提名的那几条应该拿到 evidence_text；其余即使分数不低也必须留在摘要材料档。
    """
    items = [{**_snippet_source_item(),
              "source_id": f"src-{index}", "source": f"Src {index}",
              "url": f"https://example.test/{index}"}
             for index in range(3)]
    picked = [{**_event(), "ids": [index], "title": f"E{index}",
               "score": score}
              for index, score in enumerate((60, 99, 80))]

    targets = dn.fulltext_fetch_candidates(picked, {"detail": {"fulltext_top_n": 1}})
    assert [event["title"] for event in targets] == ["E1"]

    dn.acquire_event_evidence(
        targets, items, dn.new_quality_stats(),
        request_get=lambda *_a, **_k: _ArticleResponse(),
        extractor=lambda _html: "抓来的正文。" * 60,
        resolver=_public_dns)

    tiers = [dn.event_has_fulltext_evidence(event, items) for event in picked]
    assert tiers == [False, True, False]


def test_fulltext_fetch_candidates_take_the_highest_scores_and_honour_the_knob():
    picked = [{**_event(), "title": f"E{index}", "score": score}
              for index, score in enumerate((70, 95, 80, 95))]

    chosen = dn.fulltext_fetch_candidates(picked, {"detail": {"fulltext_top_n": 2}})

    assert [event["score"] for event in chosen] == [95, 95]
    # 同分按标题定序：同一批输入必须产生同一个抓取集合，否则成本和产出都不可复现。
    assert [event["title"] for event in chosen] == ["E1", "E3"]
    # 0 表示一条正文都不抓、全部落摘要材料档；这不等于回到分层之前，摘要材料档仍不生成走向。
    assert dn.fulltext_fetch_candidates(picked, {"detail": {"fulltext_top_n": 0}}) == []
    assert dn.fulltext_fetch_candidates(picked, {}) == []


def test_failed_fetch_leaves_the_event_in_the_snippet_tier():
    """抓取失败不升档，所以分层成本是上界而不是估算（ADR 0020）。"""
    failed = _source_item()
    failed["evidence_basis"] = "snippet"
    failed["evidence_text"] = "长正文" * 500

    assert dn.event_has_fulltext_evidence(_event(), [failed]) is False
    assert dn.event_has_fulltext_evidence(_event(), [_source_item()]) is True


def test_one_off_enrichment_outputs_an_evidence_constrained_trajectory():
    watch = "量产取决于良率测试；可观察下月披露的合格率与正式投产日期。"
    llm = EnrichLLM({
        "idx": 0,
        "title": "工厂启动试产",
        "summary": "工厂本月启动试产。",
        "why": "结果会影响后续产能安排。",
        "context": "",
        "watch": watch,
        "claims": [],
        "status": "发展中",
        "tags": [],
    })
    event = _event()

    dn.enrich(llm, [event], [_source_item()], {
        "_objectivity_runtime_mode": "interim",
        "topic_tags": [],
        "detail": {"enabled": False},
    })

    assert event["context"] == ""
    assert event["watch"] == watch
    assert "关键变量" in llm.system
    assert "可观察路标" in llm.system
    assert "具体概率" in llm.system
    assert "无条件断言" in llm.system
    assert "来源外类比" in llm.system


def test_support_audit_removed_watch_stays_absent_without_placeholder():
    event = {
        **_event(),
        "why": "重要性",
        "context": "",
        "watch": "没有来源支撑的走向",
        "watch_detail": "没有来源支撑的详情走向",
        "claims": [],
    }

    audit_llm = RejectWatchAuditLLM()
    dn.audit_enrichment_support_interim(audit_llm, [event], [_source_item()])

    assert "watch" not in event
    assert "watch_detail" not in event
    for rule in ("关键变量", "可观察路标", "具体概率", "无条件断言", "来源外类比"):
        assert rule in audit_llm.system


def test_full_objectivity_audit_enforces_the_same_watch_contract():
    for rule in ("关键变量", "可观察路标", "具体概率", "无条件断言", "来源外类比"):
        assert rule in dn.OBJECTIVITY_AUDIT_SYSTEM


def test_public_item_emits_watch_detail_but_never_significance():
    event = {
        **_event(),
        "watch": "Short watch.",
        "watch_detail": "Detailed watch.",
        "significance": "Legacy private advice.",
    }

    item = dn.event_to_item(event, [_source_item()], "pick")

    assert item["watch"] == "Short watch."
    assert item["watch_detail"] == "Detailed watch."
    assert "significance" not in item


def test_public_item_never_emits_watch_detail_without_short_watch():
    item = dn.event_to_item(
        {**_event(), "watch_detail": "Orphan detail watch."},
        [_source_item()],
        "pick",
    )

    assert "watch" not in item
    assert "watch_detail" not in item


def test_public_item_never_emits_watch_detail_with_an_invalid_short_watch():
    item = dn.event_to_item(
        {
            **_event(),
            "watch": "x" * (dn.OBJECTIVITY_FIELD_LIMITS["watch"] + 1),
            "watch_detail": "Detailed watch.",
        },
        [_source_item()],
        "pick",
    )

    assert "watch" not in item
    assert "watch_detail" not in item


def test_quality_stats_use_v3_extension_field_contract():
    quality = dn.new_quality_stats()

    assert quality["removed_field_counts_version"] == 3
    assert set(quality["removed_field_counts"]) == {
        "context", "watch", "watch_detail", "detail", "claims",
    }
    assert not {"why", "significance"}.intersection(quality["removed_field_counts"])


def test_news_item_never_serializes_legacy_why():
    item = dn.event_to_item(
        {**_event(), "summary": "Pilot begins.", "why": "Legacy impact."},
        [_source_item()],
        "pick",
    )

    assert "why" not in item


def test_detail_evidence_tiers_are_deterministic():
    rich_single = {**_source_item(), "evidence_text": "甲" * 2000}
    rich_a = {**_source_item(), "source_id": "a", "evidence_text": "甲" * 800}
    rich_b = {**_source_item(), "source_id": "b", "source": "Second Wire",
              "url": "https://example.com/b",
              "evidence_text": "乙" * 800}
    limited = {**_source_item(), "evidence_text": "甲" * 1999}
    snippet = {**_source_item(), "evidence_basis": "snippet", "evidence_text": "甲" * 4000}

    assert dn.detail_evidence_tier({"ids": [0]}, [rich_single]) == "rich"
    assert dn.detail_evidence_tier({"ids": [0, 1]}, [rich_a, rich_b]) == "rich"
    assert dn.detail_evidence_tier({"ids": [0]}, [limited]) == "limited"
    assert dn.detail_evidence_tier({"ids": [0]}, [snippet]) == "snippet"


def test_detail_evidence_tier_does_not_count_repeated_reports_twice():
    repeated = "同一段事实" * 200
    rows = [
        {**_source_item(), "source_id": "a", "evidence_text": repeated},
        {**_source_item(), "source_id": "b", "source": "Second Wire",
         "url": "https://example.com/b", "evidence_text": repeated},
    ]

    assert dn.detail_evidence_tier({"ids": [0, 1]}, rows) == "limited"
    assert "SequenceMatcher" not in inspect.getsource(dn.detail_evidence_tier)


def test_detail_quality_metrics_use_final_audited_text():
    quality = dn.new_quality_stats()
    items = [
        {**_source_item(), "evidence_text": "甲" * 2000},
        {**_source_item(), "evidence_basis": "fulltext", "evidence_text": "乙" * 1000},
        {**_source_item(), "evidence_basis": "snippet", "evidence_text": "丙" * 4000},
    ]
    picked = [
        {**_event(), "ids": [0], "detail": "甲" * 150 + "\n\n" + "乙" * 150},
        {**_event(), "ids": [1], "detail": "短现状。"},
        {**_event(), "ids": [2]},
    ]

    dn.finalize_detail_quality_metrics(picked, items, quality)

    assert quality["detail_evidence_rich"] == 1
    assert quality["detail_evidence_limited"] == 1
    assert quality["detail_evidence_snippet"] == 1
    assert quality["detail_rich_target_met"] == 1
    assert quality["detail_rich_target_rate"] == 1.0
    assert quality["detail_final_median_chars"] == 153


def test_unrepairable_overlong_objectivity_field_is_deleted_and_counted():
    event = {**_event(), "watch": "原走向。"}
    quality = dn.new_quality_stats()

    dn._apply_objectivity_repair(
        event,
        {"fields": {"watch": "x" * 200}, "claims": []},
        ["watch"],
        [],
        {"Example Wire"},
        quality=quality,
    )

    assert "watch" not in event
    assert quality["removed_field_counts"]["watch"] == 1
    assert quality["removed_field_reasons"]["generation_invalid"] == 1


def test_quality_validation_accepts_legacy_v1_v2_and_current_v3_breakdowns():
    current = dn.new_quality_stats()
    assert dn.validate_daily_payload({"quality": current, "items": []}) == []

    legacy = dict(current)
    legacy.pop("removed_field_counts_version")
    legacy["removed_field_counts"] = {
        field: 0 for field in dn.QUALITY_EXTENSION_FIELDS_V1
    }
    legacy["removed_field_reasons"] = {
        reason: 0 for reason in dn.REMOVAL_REASONS_V1
    }
    assert dn.validate_daily_payload({"quality": legacy, "items": []}) == []

    v2 = dict(current)
    v2["removed_field_counts_version"] = 2
    v2["removed_field_counts"] = {
        field: 0 for field in dn.QUALITY_EXTENSION_FIELDS_V2
    }
    assert dn.validate_daily_payload({"quality": v2, "items": []}) == []

    invalid = dict(current)
    invalid["removed_field_counts_version"] = 3.0
    assert any(
        "removed_field_counts_version" in error
        for error in dn.validate_daily_payload({"quality": invalid, "items": []})
    )

    orphan_payload = {
        "quality": current,
        "items": [{
            "id": "pick-1",
            "title": "Factory pilot",
            "watch_detail": "Detail without its short contract.",
        }],
    }
    assert any(
        "requires a valid short watch" in error
        for error in dn.validate_daily_payload(orphan_payload)
    )


def test_fulltext_enrich_batches_at_three_events_while_interim_keeps_six():
    items = [_source_item()]
    picked = [{**_event(), "ids": [0]} for _ in range(7)]

    indexes = list(range(7))

    assert dn._enrich_batches(picked, items, indexes, False) == [
        [0, 1, 2, 3, 4, 5], [6],
    ]
    assert dn._enrich_batches(picked, items, indexes, True) == [
        [0, 1, 2], [3, 4, 5], [6],
    ]
    # 两档并存时批次不再连续，携带的必须是真实的 picked 下标。
    assert dn._enrich_batches(picked, items, [1, 4, 6], True) == [[1, 4, 6]]
    assert dn._enrich_batches(picked, items, [0, 2, 4, 6], False) == [[0, 2, 4, 6]]


def test_zero_increment_cost_contract_stays_within_previous_reader_budget():
    picked = [{**_event(), "ids": [0]} for _ in range(45)]
    items = [_source_item()]
    fulltext_batches = dn._enrich_batches(picked, items, list(range(45)), True)

    assert len(fulltext_batches) == 15
    assert all(len(batch) <= 3 for batch in fulltext_batches)
    assert dn.ARTICLE_MAX_CHARS == 4000
    assert dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS["detail"] == 1200
    config = dn.yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "config.yaml").read_text(
            encoding="utf-8"))
    assert config["detail"]["max_chars"] == 1000
    active_provider = config["llm"]["active_provider"]
    assert config["llm"]["providers"][active_provider]["max_retries"] == 3
    current_reader_budget = sum(
        dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS[field]
        for field in dn.OBJECTIVITY_FIELDS
    )
    previous_reader_budget = 2090
    assert current_reader_budget == 2010
    assert current_reader_budget <= previous_reader_budget
    assert 3 * 4 * dn.ARTICLE_MAX_CHARS == 48_000

    pipeline_source = inspect.getsource(dn._run_pipeline)
    assert pipeline_source.count("enrich(llm, picked, items, cfg") == 1
    assert pipeline_source.count("run_audit_enrichment_support_stage(") == 1
    enrich_source = inspect.getsource(dn.enrich)
    audit_source = inspect.getsource(dn.audit_enrichment_support)
    assert "_serialized_source_ids(ev, items, limit=4)" in enrich_source
    assert "_serialized_source_ids(event, items, limit=4)" in audit_source


def test_fulltext_trajectory_generates_and_audits_short_and_detail_watch():
    short_watch = "量产取决于良率测试；观察下月合格率。"
    detail_watch = (
        "量产仍取决于良率测试，首个路标是下月披露的合格率。"
        "还需观察正式投产日期是否随测试结果确定。"
    )

    class TrajectoryLLM:
        def __init__(self):
            self.calls = []

        def json_call(self, system, user):
            self.calls.append((system, json.loads(user)))
            if system == dn.TRAJECTORY_GENERATION_SYSTEM:
                return {"trajectories": [{
                    "idx": 0,
                    "context": "工厂此前公布试产计划，今天已开始试产。",
                    "watch": short_watch,
                    "watch_detail": detail_watch,
                    "claims": [],
                }]}
            return {"audits": [{
                "idx": 0,
                "fields": {
                    "context": True,
                    "watch": True,
                    "watch_detail": True,
                },
                "claims": [],
            }]}

    llm = TrajectoryLLM()
    event = _event()
    succeeded = dn.run_trajectory_stage(
        llm,
        [event],
        [(0, 0)],
        {0: [{
            "date": "2026-07-20",
            "title": "工厂公布试产计划",
            "summary": "工厂计划本月试产。",
            "watch": "观察是否按期开始试产。",
        }]},
        [_source_item()],
        audit_llm=llm,
        include_watch_detail=True,
    )

    assert succeeded == {0}
    assert event["watch"] == short_watch
    assert event["watch_detail"] == detail_watch
    assert llm.calls[0][1]["items"][0]["include_watch_detail"] is True
    assert llm.calls[1][1]["items"][0]["trajectory"]["watch_detail"] == detail_watch


def test_fulltext_trajectory_missing_detail_watch_is_not_audited_as_success():
    class MissingDetailLLM:
        calls = 0

        def json_call(self, system, _user):
            self.calls += 1
            assert system == dn.TRAJECTORY_GENERATION_SYSTEM
            return {"trajectories": [{
                "idx": 0,
                "context": "工厂此前公布试产计划，今天已开始试产。",
                "watch": "量产取决于良率测试；观察下月合格率。",
                "claims": [],
            }]}

    llm = MissingDetailLLM()
    event = _event()
    succeeded = dn.run_trajectory_stage(
        llm,
        [event],
        [(0, 0)],
        {0: [{"date": "2026-07-20", "watch": "观察是否按期开始试产。"}]},
        [_source_item()],
        audit_llm=llm,
        include_watch_detail=True,
    )

    assert succeeded == set()
    assert llm.calls == 1


def test_fulltext_trajectory_restores_both_watches_if_either_fails_audit():
    class MixedAuditLLM:
        def json_call(self, system, _user):
            if system == dn.TRAJECTORY_GENERATION_SYSTEM:
                return {"trajectories": [{
                    "idx": 0,
                    "context": "工厂此前公布试产计划，今天已开始试产。",
                    "watch": "新短走向；观察新路标。",
                    "watch_detail": "新详情走向完整包含新短走向与新路标。",
                    "claims": [],
                }]}
            return {"audits": [{
                "idx": 0,
                "fields": {
                    "context": True,
                    "watch": True,
                    "watch_detail": False,
                },
                "claims": [],
            }]}

    event = {
        **_event(),
        "watch": "原短走向。",
        "watch_detail": "原详情走向。",
    }
    health = dn.new_trajectory_health()
    succeeded = dn.run_trajectory_stage(
        MixedAuditLLM(),
        [event],
        [(0, 0)],
        {0: [{"date": "2026-07-20", "watch": "观察是否按期开始试产。"}]},
        [_source_item()],
        include_watch_detail=True,
        health=health,
    )

    assert succeeded == {0}
    assert event["watch"] == "原短走向。"
    assert event["watch_detail"] == "原详情走向。"
    assert health["audit_fallbacks"] == 2


def test_feed_labels_existing_watch_field_as_trajectory(tmp_path):
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    payload = {
        "date": "2026-07-21",
        "generated_at": "2026-07-21T05:00:00+00:00",
        "items": [{
            "id": "pick-1",
            "tier": "pick",
            "category": "tech",
            "title": "工厂启动试产",
            "summary": "工厂本月启动试产。",
            "watch": "量产取决于良率测试。",
            "time": "2026-07-21T01:00:00+00:00",
            "sources": [{"name": "Example Wire", "url": "https://example.test/factory"}],
        }],
    }
    (daily_dir / "2026-07-21.js").write_text(
        'window.NEWS_DATA = window.NEWS_DATA || {};\n'
        f'window.NEWS_DATA["2026-07-21"] = {json.dumps(payload, ensure_ascii=False)};\n',
        encoding="utf-8",
    )

    dn.write_feed(tmp_path, "2026-07-21", {
        "feed_days": 7,
        "site_url": "https://example.test",
    })

    feed = (tmp_path / "feed.xml").read_text(encoding="utf-8")
    assert "<b>走向：</b>" in feed
    assert "后续关注" not in feed
