# -*- coding: utf-8 -*-
"""起因原文核对闸：起因必须能逐字回溯到来源正文，否则整条丢弃。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


ARTICLE = (
    "最高法院于2月20日裁定，特朗普此前依据《国际紧急经济权力法》加征的全球关税违法。"
    "白宫随即改用第301条重新加征，并选在旧关税到期当天生效。"
)


def _items(evidence_text=ARTICLE):
    return [{
        "title": "新关税生效数小时后即遭起诉",
        # 摘要里也带上那句原文，好让 interim 与全文两条路径共用同一批用例
        "desc": "新关税遭到起诉。白宫随即改用第301条重新加征，并选在旧关税到期当天生效。",
        "evidence_text": evidence_text,
        "source": "Synthetic Wire",
        "source_id": "synthetic-wire",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "url": "https://example.com/report",
        "time": "2026-07-26T00:00:00+00:00",
    }]


def _event(cause, span):
    return {
        "ids": [0], "category": "world", "title": "关税遭起诉",
        "context": cause, "context_evidence": span,
    }


def test_verbatim_span_keeps_the_cause():
    event = _event(
        "最高法院裁定旧关税违法，白宫改用第301条并在旧关税到期当天生效。",
        [{"source_index": 0, "quote": "白宫随即改用第301条重新加征，并选在旧关税到期当天生效。"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality, rich=True) is True
    assert event["context"].startswith("最高法院裁定")
    assert quality["cause_evidence_rejected"] == 0
    # 内部字段不得泄漏到后续阶段
    assert "context_evidence" not in event


def test_span_absent_from_sources_drops_the_cause():
    event = _event(
        "白宫意在向北京施压。",
        [{"source_index": 0, "quote": "白宫官员表示此举意在向北京施压。"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality, rich=True) is False
    assert "context" not in event
    assert "context_evidence" not in event
    assert quality["cause_evidence_rejected"] == 1


def test_paraphrased_span_is_rejected():
    """改写过的引文不算逐字回溯——这正是要拦住的推断路径。"""
    event = _event(
        "最高法院裁定关税违法后白宫换了法律依据。",
        [{"source_index": 0, "quote": "由于最高法院作出了不利裁决，白宫方面决定更换加征关税所依据的法律条文。"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality, rich=True) is False
    assert "context" not in event
    assert quality["cause_evidence_rejected"] == 1


def test_trivially_short_span_cannot_vouch_for_a_cause():
    event = _event("白宫改用第301条。", [{"source_index": 0, "quote": "白宫"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality, rich=True) is False
    assert quality["cause_evidence_rejected"] == 1


def test_empty_cause_needs_no_span_and_is_not_counted_as_rejected():
    event = _event("", [])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality, rich=True) is False
    # 空起因保持 enrich 的空串约定，不是被闸门拒绝
    assert event["context"] == ""
    assert "context_evidence" not in event
    assert quality["cause_evidence_rejected"] == 0


def test_punctuation_and_width_differences_still_match():
    event = _event(
        "白宫改用第301条并在旧关税到期当天生效。",
        [{"source_index": 0, "quote": "白宫随即改用第３０１条重新加征，并选在旧关税到期当天生效"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality, rich=True) is True
    assert quality["cause_evidence_rejected"] == 0


def test_span_matched_against_rss_summary_when_no_fulltext():
    """interim 模式只有 200 字摘要，闸门照样按同一份材料核对。"""
    items = _items(evidence_text="")
    items[0]["desc"] = "新关税遭到起诉，原因是旧关税已被最高法院裁定违法。"
    event = _event(
        "旧关税已被最高法院裁定违法。",
        [{"source_index": 0, "quote": "原因是旧关税已被最高法院裁定违法"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, items, quality) is True


def test_enrich_drops_unbacked_cause_end_to_end():
    class InventedCauseLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "关税遭起诉", "summary": "新关税遭起诉。",
                "why": "影响进口商。",
                "context": "白宫意在向北京施压。",
                "context_evidence": [{"source_index": 0, "quote": "白宫官员表示此举意在向北京施压。"}],
                "watch": "", "watch_detail": "", "claims": [],
                "status": "已确认", "tags": [],
            }]

    events = [{"ids": [0], "category": "world", "title": "关税遭起诉"}]
    quality = dn.new_quality_stats()

    dn.enrich(InventedCauseLLM(), events, _items(),
              {"topic_tags": [], "detail": {"enabled": False},
               "objectivity": {"mode": "interim"}}, quality=quality)

    assert "context" not in events[0]
    assert "context_evidence" not in events[0]
    assert quality["cause_evidence_rejected"] == 1


def test_enrich_keeps_backed_cause_end_to_end():
    class GroundedCauseLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "关税遭起诉", "summary": "新关税遭起诉。",
                "why": "影响进口商。",
                "context": "最高法院裁定旧关税违法，白宫改用第301条。",
                "context_evidence": [{"source_index": 0, "quote": "白宫随即改用第301条重新加征，并选在旧关税到期当天生效。"}],
                "watch": "", "watch_detail": "", "claims": [],
                "status": "已确认", "tags": [],
            }]

    events = [{"ids": [0], "category": "world", "title": "关税遭起诉"}]
    quality = dn.new_quality_stats()

    dn.enrich(GroundedCauseLLM(), events, _items(),
              {"topic_tags": [], "detail": {"enabled": False},
               "objectivity": {"mode": "interim"}}, quality=quality)

    assert events[0]["context"].startswith("最高法院裁定")
    assert "context_evidence" not in events[0]
    assert quality["cause_evidence_rejected"] == 0


SPECULATION_ARTICLE = (
    "ARC-AGI-3的格式和任务类型在Opus 5开发前已公开。"
    "Anthropic发言人称公司未针对该基准做专门训练。"
)


def _speculation_items():
    items = _items(SPECULATION_ARTICLE)
    items[0]["title"] = "Opus 5 在 ARC-AGI-3 创纪录"
    return items


def test_unattributed_speculation_is_dropped_even_with_a_real_span():
    """探针第三轮的真实产出：引文属实，但从它推出的动机是模型加的。"""
    event = _event(
        "ARC-AGI-3的格式和任务类型在Opus 5开发前已公开，"
        "Anthropic可能针对性地进行了数据标注和强化学习训练。",
        [{"source_index": 0, "quote": "ARC-AGI-3的格式和任务类型在Opus 5开发前已公开。"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _speculation_items(), quality, rich=True) is False
    assert "context" not in event
    assert quality["cause_speculation_rejected"] == 1
    # 片段本身是能对上的，拦下它的是未归因推测这一条
    assert quality["cause_evidence_rejected"] == 0


def test_attributed_speculation_survives():
    event = _event(
        "Anthropic发言人称公司未针对该基准做专门训练。",
        [{"source_index": 0, "quote": "Anthropic发言人称公司未针对该基准做专门训练。"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _speculation_items(), quality, rich=True) is True
    assert quality["cause_speculation_rejected"] == 0


def test_compound_words_containing_cheng_do_not_count_as_attribution():
    """名称/简称/职称/对称 里的"称"不是引述，不得放行未归因推测。"""
    for cause in (
        "该基准的名称在发布前已公开，厂商可能针对性地做了优化。",
        "两家公司的简称相同，收购可能意在整合品牌。",
        "监管机构的职称评定改革，可能旨在留住人才。",
        "这套系统的对称结构使其可能更易受攻击。",
    ):
        assert dn.CAUSE_SPECULATION_RE.search(cause), cause
        assert not dn.CAUSE_ATTRIBUTION_RE.search(cause), cause


def test_real_attribution_forms_are_still_recognised():
    for cause in (
        "路透社报道称此举可能意在向北京施压。",
        "官员称新规可能推迟生效。",
        "公司声称此次调整旨在优化成本。",
        "发言人回应称停产可能持续一个季度。",
    ):
        assert dn.CAUSE_ATTRIBUTION_RE.search(cause), cause


def test_plain_factual_cause_is_untouched_by_the_speculation_guard():
    event = _event(
        "最高法院裁定旧关税违法，白宫改用第301条。",
        [{"source_index": 0, "quote": "白宫随即改用第301条重新加征，并选在旧关税到期当天生效。"}])
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, _items(), quality, rich=True) is True
    assert quality["cause_speculation_rejected"] == 0


def test_prompt_requires_a_verbatim_span():
    class CapturingLLM:
        system = ""

        def json_call(self, system, _user):
            CapturingLLM.system = system
            return []

    dn.enrich(CapturingLLM(), [{"ids": [0], "category": "world", "title": "T"}],
              _items(), {"topic_tags": [], "detail": {"enabled": False},
                         "objectivity": {"mode": "interim"}})

    assert "context_evidence" in CapturingLLM.system
    assert "逐字复制" in CapturingLLM.system


def test_multiple_spans_must_each_match_the_declared_source():
    items = _items()
    items.append({
        **_items("监管机构宣布将同步复核相关许可。")[0],
        "source": "Second Wire",
        "source_id": "zzz-second-wire",
        "url": "https://example.com/second",
    })
    event = {
        "ids": [0, 1],
        "category": "world",
        "title": "关税与许可同步调整",
        "context": "法院裁决促使白宫更换法律依据，监管机构随后启动许可复核。",
        "context_evidence": [
            {"source_index": 0, "quote": "白宫随即改用第301条重新加征，并选在旧关税到期当天生效。"},
            {"source_index": 1, "quote": "监管机构宣布将同步复核相关许可。"},
        ],
    }
    quality = dn.new_quality_stats()

    assert dn.verify_cause_evidence(event, items, quality, rich=True) is True
    assert "context_evidence" not in event

    event["context_evidence"] = [
        {"source_index": 0, "quote": "监管机构宣布将同步复核相关许可。"},
    ]
    assert dn.verify_cause_evidence(event, items, quality, rich=True) is False
    assert quality["cause_evidence_rejected"] == 1


def test_empty_source_keeps_later_declared_source_index_stable():
    items = _items()
    items[0]["desc"] = ""
    items[0]["evidence_text"] = ""
    items.append({
        **_items("监管机构宣布将同步复核相关许可。")[0],
        "source": "Second Wire",
        "source_id": "zzz-second-wire",
        "url": "https://example.com/second",
    })
    event = {
        "ids": [0, 1],
        "category": "world",
        "title": "许可复核",
        "context": "监管机构启动许可复核。",
        "context_evidence": [{
            "source_index": 1,
            "quote": "监管机构宣布将同步复核相关许可。",
        }],
    }

    assert dn.verify_cause_evidence(
        event, items, dn.new_quality_stats(), rich=True) is True
