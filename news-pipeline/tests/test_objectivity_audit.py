# -*- coding: utf-8 -*-
import inspect
import json
import sys
import threading
import time
from pathlib import Path

import yaml
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


def test_enrich_ignores_non_object_rows_in_model_response():
    class NestedListLLM:
        def json_call(self, _system, _user):
            return [[{"idx": 0, "title": "unsafe nested row"}]]

    events = [{"ids": [0], "category": "world", "title": "Original title"}]
    items = [{
        "title": "Source title",
        "desc": "Source summary",
        "source": "Synthetic Wire",
        "source_id": "synthetic-wire",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "url": "https://example.com/report",
        "time": "2026-07-22T00:00:00+00:00",
    }]

    result = dn.enrich(
        NestedListLLM(),
        events,
        items,
        {"topic_tags": [], "detail": {"enabled": True},
         "objectivity": {"mode": "interim"}},
    )

    assert result == [{
        "ids": [0], "category": "world", "title": "Original title",
    }]


def test_enrich_rejects_boolean_event_indexes():
    class BooleanIndexLLM:
        def json_call(self, _system, _user):
            return [{"idx": True, "title": "Wrong event"}]

    events = [
        {"ids": [0], "category": "world", "title": "Event zero"},
        {"ids": [1], "category": "world", "title": "Event one"},
    ]
    items = [
        {
            "title": f"Source {index}",
            "desc": "Source summary",
            "source": "Synthetic Wire",
            "source_id": f"synthetic-{index}",
            "source_type": "fact",
            "tier": "T1",
            "credibility": 9,
            "url": f"https://example.com/report-{index}",
            "time": "2026-07-22T00:00:00+00:00",
        }
        for index in range(2)
    ]

    result = dn.enrich(
        BooleanIndexLLM(),
        events,
        items,
        {"topic_tags": [], "detail": {"enabled": False},
         "objectivity": {"mode": "interim"}},
    )

    assert [event["title"] for event in result] == ["Event zero", "Event one"]


def test_model_boolean_indexes_are_never_treated_as_integer_positions():
    items = [
        {
            "title": f"Source {index}",
            "desc": "Source summary",
            "source": f"Wire {index}",
            "source_id": f"wire-{index}",
            "source_type": "fact",
            "tier": "T1",
            "credibility": 9,
            "url": f"https://example.com/report-{index}",
            "time": "2026-07-22T00:00:00+00:00",
        }
        for index in range(2)
    ]

    class PrefilterLLM:
        def json_call(self, _system, _user):
            return {"drop": [True], "soft": [False]}

    assert dn.prefilter(PrefilterLLM(), [dict(item) for item in items]) == items

    class TriageLLM:
        def json_call(self, _system, _user):
            return [{
                "ids": [True],
                "category": "world",
                "dims": {dimension: 5 for dimension in dn.DIMS},
                "title": "Boolean event",
            }]

    # 布尔 ids 被拒后这一批一个事件都没落地，按 ADR-0012 降级为单条事件而不是
    # 让条目凭空消失。要守的不变式是「布尔永远不当下标」：降级出来的 ids 必须
    # 是货真价实的整数位置，且 True 没有被当成 1。
    boolean_triaged = dn.triage(TriageLLM(), [dict(item) for item in items])
    assert [event["ids"] for event in boolean_triaged] == [[0], [1]]
    assert all(type(i) is int for event in boolean_triaged for i in event["ids"])
    assert [event["title"] for event in boolean_triaged] == ["Source 0", "Source 1"]

    class NonFiniteTriageLLM:
        def json_call(self, _system, _user):
            return [{
                "ids": [0],
                "category": "world",
                "dims": {
                    **{dimension: 5 for dimension in dn.DIMS},
                    "impact": "NaN",
                },
                "title": "Non-finite score",
            }]

    triaged = dn.triage(NonFiniteTriageLLM(), [dict(item) for item in items])
    assert triaged[0]["dims"]["impact"] == 3.0

    class MergeLLM:
        def json_call(self, _system, _user):
            return [[True, 0]]

    events = [
        {"ids": [0], "category": "world", "title": "Zero"},
        {"ids": [1], "category": "world", "title": "One"},
    ]
    assert len(dn.merge_events(MergeLLM(), events, items)) == 2
    assert dn._serialized_source_ids({"ids": [True, 0]}, items) == [0]
    assert dn.sanitize_claims(
        [{"text": "Claim", "kind": "fact", "source_indexes": [True]}],
        ["Wire 0", "Wire 1"],
    ) == [{"text": "Claim", "kind": "fact", "sources": []}]

    class MatchLLM:
        def json_call(self, _system, _user):
            return {"matches": [
                {"today": "0", "registry": 0},
                {"today": True, "registry": 0},
            ]}

    active = [{
        "event_id": "evt-0",
        "title": "Active",
        "category": "world",
        "last_seen": "2026-07-21",
        "history": [{"date": "2026-07-21", "summary": "Earlier"}],
    }]
    picked = [{"title": "Today", "summary": "Update", "category": "world"}]
    assert dn.match_events_llm(MatchLLM(), active, picked) == []

    class FitLLM:
        def json_call(self, _system, _user):
            return {"fits": [
                {"idx": 0, "fit": "NaN"},
                {"idx": True, "fit": 10},
            ]}

    fitted = [{"title": "Today", "category": "world"}]
    dn.interest_fit(FitLLM(), "## 更关注\n- 主题", fitted)
    assert "interest_mult" not in fitted[0]

    class OpinionLLM:
        def json_call(self, _system, _user):
            return [{"idx": "0", "title": "String index"},
                    {"idx": True, "title": "Boolean index"}]

    pulse = [{"platform": "微博", "word": "主题", "url": "https://example.com"}]
    assert dn.opinion_pulse(
        OpinionLLM(), {"opinion": {"enabled": True}}, pulse) == []


def _triage_items(count):
    return [
        {
            "title": f"Source {index}",
            "desc": "Source summary",
            "source": f"Wire {index}",
            "source_id": f"wire-{index}",
            "source_type": "fact",
            "tier": "T1",
            "credibility": 9,
            "url": f"https://example.com/report-{index}",
            "time": "2026-07-22T00:00:00+00:00",
        }
        for index in range(count)
    ]


def _triage_event(index):
    return {
        "ids": [index],
        "category": "world",
        "dims": {dimension: 5 for dimension in dn.DIMS},
        "title": f"Event {index}",
    }


def test_model_rows_reads_the_wrapped_contract():
    payload = {"events": [{"a": 1}, {"b": 2}]}
    assert dn._model_rows(payload, "events") == [{"a": 1}, {"b": 2}]
    assert dn._model_rows({"events": []}, "events") == []


def test_model_rows_accepts_a_drifted_wrapper_key():
    """模型把 events 写成别的键：整个对象只有这一个键才认，靠字段数区分
    包裹对象和裸行对象。"""
    assert dn._model_rows({"event_list": [{"a": 1}]}, "events") == [{"a": 1}]


def test_model_rows_never_mistakes_a_row_field_for_the_row_list():
    """裸行对象自己带 ids / claims / context_evidence 这类列表字段。
    早期用「唯一的列表值」做判据会把 ids 当成行列表，正好在本次故障的形状上判错。"""
    row = {"ids": [0], "category": "world", "title": "Bare row"}
    assert dn._model_rows(row, "events") == [row]

    enriched = {"idx": 0, "title": "Bare enrich row",
                "claims": [{"text": "c"}], "context_evidence": []}
    assert dn._model_rows(enriched, "items") == [enriched]


def test_model_rows_keeps_bare_array_compatibility_and_rejects_scalars():
    assert dn._model_rows([{"a": 1}], "events") == [{"a": 1}]
    assert dn._model_rows([], "events") == []
    assert dn._model_rows("标量", "events") is None
    assert dn._model_rows(42, "events") is None
    assert dn._model_rows(None, "events") is None


def test_batch_spans_folds_a_short_tail_into_the_previous_batch():
    """2026-08-01 崩在只有 2 条的尾批上。历史尾批都 ≥ 13，阈值 10 让常规
    日子的分批边界完全不变。"""
    assert dn.batch_spans(302, 50) == [
        (0, 50), (50, 100), (100, 150), (150, 200), (200, 250), (250, 302)]
    # 尾批 13 条：历史常见值，边界不得改变
    assert dn.batch_spans(313, 50)[-2:] == [(250, 300), (300, 313)]
    # 单批不足阈值时不能被折叠掉
    assert dn.batch_spans(3, 50) == [(0, 3)]
    assert dn.batch_spans(0, 50) == []


def test_triage_reads_the_wrapped_event_contract():
    items = _triage_items(2)
    quality = dn.new_quality_stats()

    class WrappedLLM:
        def json_call(self, _system, _user):
            return {"events": [_triage_event(0), _triage_event(1)]}

    events = dn.triage(WrappedLLM(), [dict(item) for item in items], quality)

    # 只断言阶段A 自己的计数器：两个事件会触发后续的同日归并，那一步拿到的是
    # 阶段A 的载荷、走自己的降级路径，degraded 由它置位，与本用例无关。
    assert sorted(event["ids"][0] for event in events) == [0, 1]
    assert quality["triage_invalid_rows"] == 0
    assert quality["triage_fallback_batches"] == 0


def test_triage_normalizes_single_object_response():
    """2026-08-01 线上故障：模型只返回一个对象而不是对象数组，
    迭代得到字符串 key，整条管线 AttributeError 退出。"""
    items = _triage_items(1)
    quality = dn.new_quality_stats()

    class SingleObjectLLM:
        def json_call(self, _system, _user):
            return _triage_event(0)

    events = dn.triage(SingleObjectLLM(), [dict(item) for item in items], quality)

    assert [event["ids"] for event in events] == [[0]]
    assert events[0]["title"] == "Event 0"
    assert quality["triage_invalid_rows"] == 0
    assert quality["triage_fallback_batches"] == 0
    assert quality["degraded"] is False


def test_triage_skips_non_object_rows_and_keeps_the_rest():
    items = _triage_items(2)
    quality = dn.new_quality_stats()

    class MixedRowsLLM:
        def json_call(self, _system, _user):
            return [_triage_event(0), "不是对象", _triage_event(1)]

    events = dn.triage(MixedRowsLLM(), [dict(item) for item in items], quality)

    assert sorted(event["ids"][0] for event in events) == [0, 1]
    assert quality["triage_invalid_rows"] == 1
    assert quality["triage_fallback_batches"] == 0
    assert quality["degraded"] is True


@pytest.mark.parametrize("payload", [
    ["纯字符串数组"],
    "标量",
    42,
])
def test_triage_unusable_response_degrades_to_one_event_per_item(payload):
    """整批不可用时每条各自成事件——阶段A 跳过一批等于这些条目彻底不进
    事件层，是内容损失且日报表面看不出来。"""
    items = _triage_items(2)
    quality = dn.new_quality_stats()

    class UnusableLLM:
        def json_call(self, _system, _user):
            return payload

    events = dn.triage(UnusableLLM(), [dict(item) for item in items], quality)

    assert sorted(event["ids"][0] for event in events) == [0, 1]
    assert [event["title"] for event in events] == ["Source 0", "Source 1"]
    assert all(event["dims"] == {dimension: 3.0 for dimension in dn.DIMS}
               for event in events)
    assert quality["triage_fallback_batches"] == 1
    assert quality["degraded"] is True


@pytest.mark.parametrize("payload", [
    # 模型用了批内相对编号：行是合法对象，但编号全落在本批窗口外
    {"events": [{"ids": [900], "category": "world",
                 "dims": {d: 5 for d in dn.DIMS}, "title": "越界"}]},
    # 退化成一个空对象
    {},
])
def test_triage_degrades_when_rows_land_no_events(payload):
    """行是对象但一个事件都没落地时也必须降级。只看「元素是不是 dict」会漏掉
    这条路径，让整批条目静默消失——和形状崩坏后果相同，只是没人看得见。"""
    items = _triage_items(2)
    quality = dn.new_quality_stats()

    class NoLandingLLM:
        def json_call(self, _system, _user):
            return payload

    events = dn.triage(NoLandingLLM(), [dict(item) for item in items], quality)

    assert sorted(event["ids"][0] for event in events) == [0, 1]
    assert quality["triage_fallback_batches"] == 1
    assert quality["degraded"] is True


def test_triage_keeps_an_explicit_empty_answer_empty():
    """{"events": []} 是合法回答（该批全是垃圾），不得触发降级——否则模型
    每次正当地清空一批，都会被塞回一堆单条事件。"""
    items = _triage_items(2)
    quality = dn.new_quality_stats()

    class EmptyLLM:
        def json_call(self, _system, _user):
            return {"events": []}

    assert dn.triage(EmptyLLM(), [dict(item) for item in items], quality) == []
    assert quality["triage_fallback_batches"] == 0
    assert quality["degraded"] is False


def test_triage_call_failure_degrades_to_one_event_per_item():
    items = _triage_items(2)
    quality = dn.new_quality_stats()

    class RaisingLLM:
        def json_call(self, _system, _user):
            raise RuntimeError("LLM 调用重试均失败")

    events = dn.triage(RaisingLLM(), [dict(item) for item in items], quality)

    assert sorted(event["ids"][0] for event in events) == [0, 1]
    assert quality["triage_fallback_batches"] == 1
    assert quality["degraded"] is True


def test_triage_tolerates_non_list_ids_and_non_dict_dims():
    items = _triage_items(1)
    quality = dn.new_quality_stats()

    class MalformedFieldsLLM:
        def json_call(self, _system, _user):
            return [{"ids": 0, "category": "world", "dims": "high", "title": "Bad"},
                    {"ids": [0], "category": "world", "dims": None, "title": "Good"}]

    events = dn.triage(MalformedFieldsLLM(), [dict(item) for item in items], quality)

    assert [event["title"] for event in events] == ["Good"]
    assert events[0]["dims"] == {dimension: 3.0 for dimension in dn.DIMS}


def test_enrich_reads_the_wrapped_item_contract():
    class WrappedLLM:
        def json_call(self, _system, _user):
            return {"items": [{"idx": 0, "title": "加工后标题",
                               "summary": "事实增量", "status": "已确认"}]}

    events = [{"ids": [0], "category": "world", "title": "Original title"}]
    items = [{
        "title": "Source title",
        "desc": "Source summary",
        "source": "Synthetic Wire",
        "source_id": "synthetic-wire",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "url": "https://example.com/report",
        "time": "2026-07-22T00:00:00+00:00",
    }]

    result = dn.enrich(
        WrappedLLM(), events, items,
        {"topic_tags": [], "detail": {"enabled": True},
         "objectivity": {"mode": "interim"}},
    )

    assert result[0]["title"] == "加工后标题"


def test_enrich_counts_an_unusable_response_and_keeps_base_content():
    class ScalarLLM:
        def json_call(self, _system, _user):
            return "阶段B 跑偏了"

    events = [{"ids": [0], "category": "world", "title": "Original title"}]
    items = [{
        "title": "Source title",
        "desc": "Source summary",
        "source": "Synthetic Wire",
        "source_id": "synthetic-wire",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "url": "https://example.com/report",
        "time": "2026-07-22T00:00:00+00:00",
    }]
    quality = dn.new_quality_stats()

    result = dn.enrich(
        ScalarLLM(), events, items,
        {"topic_tags": [], "detail": {"enabled": True},
         "objectivity": {"mode": "interim"}},
        quality,
    )

    assert result[0]["title"] == "Original title"
    assert quality["model_unusable_responses"] == 1
    assert quality["degraded"] is True


@pytest.mark.parametrize("payload,expected", [
    ({"picks": [{"idx": 0, "title": "话题", "why_hot": "原因",
                 "emotion": "情绪", "mechanism": "机制"}]}, 1),
    ([{"idx": 0, "title": "话题", "why_hot": "原因",
       "emotion": "情绪", "mechanism": "机制"}], 1),
    ({"idx": 0, "title": "话题", "why_hot": "原因",
      "emotion": "情绪", "mechanism": "机制"}, 1),
    ("跑偏了", 0),
])
def test_opinion_pulse_accepts_wrapped_bare_and_single_object(payload, expected):
    """舆论观察此前收到裸对象会静默变空，且一行日志都没有。"""
    class ShapeLLM:
        def json_call(self, _system, _user):
            return payload

    pulse = [{"platform": "微博", "word": "主题", "url": "https://example.com"}]
    picks = dn.opinion_pulse(ShapeLLM(), {"opinion": {"enabled": True}}, pulse)
    assert len(picks) == expected


def test_article_blocking_read_obeys_wall_clock_deadline_and_closes_response():
    class BlockingResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self):
            self.closed = False
            self.read_started = threading.Event()
            self.release_read = threading.Event()

        def iter_content(self, chunk_size):
            self.read_started.set()
            self.release_read.wait(5)
            if not self.closed:
                yield b"article body" * 100

        def close(self):
            self.closed = True
            self.release_read.set()

    response = BlockingResponse()
    started = time.perf_counter()
    result = dn.fetch_article_evidence(
        {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
        request_get=lambda *_args, **_kwargs: response,
        extractor=lambda _html: "正文" * 200,
        resolver=lambda *_args, **_kwargs: [
            (None, None, None, None, ("93.184.216.34", 443))],
        sleep=lambda _seconds: None,
        attempt_timeout=0.05,
        max_attempts=1,
    )
    elapsed = time.perf_counter() - started

    assert response.read_started.is_set()
    assert result["evidence_basis"] == "snippet"
    assert elapsed < 0.25
    assert response.closed is True


def test_native_article_extractor_abort_is_contained_and_reaped(tmp_path):
    abort_worker = tmp_path / "abort_worker.py"
    abort_worker.write_text(
        "import os\nimport sys\nsys.stdin.buffer.read()\n"
        "if sys.platform != 'win32':\n"
        " import resource\n resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
        "os._exit(134) if sys.platform == 'win32' else os.abort()\n",
        encoding="utf-8",
    )
    html = (Path(__file__).with_name("fixtures") / "article-extractor-minimal.html").read_text(
        encoding="utf-8")

    for _ in range(5):
        with pytest.raises(dn.ArticleEvidenceError, match="subprocess exited"):
            dn._extract_static_article(
                html,
                timeout=1.0,
                command=[sys.executable, str(abort_worker)],
            )

    # A crashed native parser must not poison the parent heap or prevent a later task.
    assert "Synthetic evidence report" in dn._extract_static_article(
        html, timeout=5.0)


def test_native_article_extractor_timeout_terminates_child(tmp_path):
    blocking_worker = tmp_path / "blocking_worker.py"
    blocking_worker.write_text(
        "import sys\nimport time\nsys.stdin.buffer.read()\ntime.sleep(30)\n",
        encoding="utf-8",
    )

    started = time.perf_counter()
    with pytest.raises(dn.ArticleEvidenceError, match="timed out"):
        dn._extract_static_article(
            "<article>fixture</article>",
            timeout=0.05,
            command=[sys.executable, str(blocking_worker)],
        )
    assert time.perf_counter() - started < 1.0


def test_article_timeout_never_waits_for_blocking_response_close():
    class BlockingCloseResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self):
            self.close_started = threading.Event()
            self.release_read = threading.Event()

        def iter_content(self, chunk_size):
            self.release_read.wait(5)
            return
            yield  # pragma: no cover - keeps this a generator

        def close(self):
            self.close_started.set()
            time.sleep(0.4)
            self.release_read.set()

    response = BlockingCloseResponse()
    started = time.perf_counter()
    result = dn.fetch_article_evidence(
        {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
        request_get=lambda *_args, **_kwargs: response,
        extractor=lambda _html: "正文" * 200,
        resolver=lambda *_args, **_kwargs: [
            (None, None, None, None, ("93.184.216.34", 443))],
        sleep=lambda _seconds: None,
        attempt_timeout=0.03,
        max_attempts=1,
    )
    elapsed = time.perf_counter() - started

    assert result["evidence_basis"] == "snippet"
    assert response.close_started.wait(0.1)
    assert elapsed < 0.15


def test_article_timeout_swallows_raising_response_close():
    class RaisingCloseResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self):
            self.close_called = threading.Event()
            self.release_read = threading.Event()

        def iter_content(self, chunk_size):
            self.release_read.wait(5)
            return
            yield  # pragma: no cover - keeps this a generator

        def close(self):
            self.close_called.set()
            raise RuntimeError("cleanup failed")

    response = RaisingCloseResponse()
    started = time.perf_counter()
    try:
        result = dn.fetch_article_evidence(
            {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
            request_get=lambda *_args, **_kwargs: response,
            extractor=lambda _html: "正文" * 200,
            resolver=lambda *_args, **_kwargs: [
                (None, None, None, None, ("93.184.216.34", 443))],
            sleep=lambda _seconds: None,
            attempt_timeout=0.03,
            max_attempts=1,
        )
        elapsed = time.perf_counter() - started

        assert result["evidence_basis"] == "snippet"
        assert response.close_called.wait(0.1)
        assert elapsed < 0.15
    finally:
        response.release_read.set()


def test_article_queue_wait_uses_only_budget_remaining_after_worker_setup():
    class SetupClock:
        def __init__(self):
            self.calls = 0

        def __call__(self):
            self.calls += 1
            return 0.0 if self.calls == 1 else 0.04

    release_resolver = threading.Event()

    def blocking_resolver(*_args, **_kwargs):
        release_resolver.wait(5)
        return [(None, None, None, None, ("93.184.216.34", 443))]

    started = time.perf_counter()
    try:
        result = dn.fetch_article_evidence(
            {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
            request_get=lambda *_args, **_kwargs: None,
            extractor=lambda _html: "正文" * 200,
            resolver=blocking_resolver,
            sleep=lambda _seconds: None,
            clock=SetupClock(),
            attempt_timeout=0.05,
            max_attempts=1,
        )
        elapsed = time.perf_counter() - started

        assert result["evidence_basis"] == "snippet"
        assert elapsed < 0.035
    finally:
        release_resolver.set()


def test_article_blocking_extractor_obeys_wall_clock_deadline_and_closes_response():
    class Response:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self):
            self.closed = False

        def iter_content(self, chunk_size):
            yield b"<html><body>article</body></html>"

        def close(self):
            self.closed = True

    response = Response()
    extractor_started = threading.Event()
    release_extractor = threading.Event()

    def blocking_extractor(_html):
        extractor_started.set()
        release_extractor.wait(5)
        return "正文" * 200

    started = time.perf_counter()
    try:
        result = dn.fetch_article_evidence(
            {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
            request_get=lambda *_args, **_kwargs: response,
            extractor=blocking_extractor,
            resolver=lambda *_args, **_kwargs: [
                (None, None, None, None, ("93.184.216.34", 443))],
            sleep=lambda _seconds: None,
            attempt_timeout=0.05,
            max_attempts=1,
        )
        elapsed = time.perf_counter() - started

        assert extractor_started.is_set()
        assert result["evidence_basis"] == "snippet"
        assert elapsed < 0.25
        assert response.closed is True
    finally:
        release_extractor.set()


def test_repeated_blocking_extractors_keep_attempt_workers_bounded():
    class Response:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self):
            self.closed = False

        def iter_content(self, chunk_size):
            yield b"<html><body>article</body></html>"

        def close(self):
            self.closed = True

    release_extractors = threading.Event()
    counter_lock = threading.Lock()
    entered = 0
    finished = 0
    responses = []

    def request_get(*_args, **_kwargs):
        response = Response()
        responses.append(response)
        return response

    def blocking_extractor(_html):
        nonlocal entered, finished
        with counter_lock:
            entered += 1
        try:
            release_extractors.wait(5)
            return "正文" * 200
        finally:
            with counter_lock:
                finished += 1

    started = time.perf_counter()
    try:
        for _ in range(12):
            result = dn.fetch_article_evidence(
                {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
                request_get=request_get,
                extractor=blocking_extractor,
                resolver=lambda *_args, **_kwargs: [
                    (None, None, None, None, ("93.184.216.34", 443))],
                sleep=lambda _seconds: None,
                attempt_timeout=0.02,
                max_attempts=1,
            )
            assert result["evidence_basis"] == "snippet"

        assert time.perf_counter() - started < 0.75
        assert 1 <= entered <= 6
        assert len(responses) == entered
        assert all(response.closed for response in responses)
    finally:
        release_extractors.set()
        cleanup_deadline = time.perf_counter() + 1
        while finished < entered and time.perf_counter() < cleanup_deadline:
            time.sleep(0.01)
        time.sleep(0.02)


class QueueLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def json_call(self, system, user):
        self.calls.append((system, user))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def source_item(title="OpenAI 发布模型", desc="OpenAI 发布模型并公布评测。",
                source="OpenAI", source_id="openai"):
    return {
        "title": title, "desc": desc, "source": source, "source_id": source_id,
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": f"https://example.com/{source_id}",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_basis": "snippet", "evidence_text": desc,
    }


def test_reader_title_keeps_complete_generated_title_above_soft_target():
    title = "T" * 31

    assert dn.select_reader_title(title, "Source title") == title


def test_reader_title_accepts_generated_title_at_hard_boundary():
    title = "T" * 120

    assert dn.select_reader_title(title, "Source title") == title


@pytest.mark.parametrize("candidate", ["", "T" * 121])
def test_reader_title_falls_back_to_complete_source_title(candidate):
    source_title = "S" * 300

    assert dn.select_reader_title(candidate, source_title) == source_title


def enriched_event(item_id=0, title="OpenAI 发布模型"):
    return {
        "ids": [item_id], "category": "ai", "title": title,
        "summary": "OpenAI 发布模型并公布评测。", "why": "影响开发者。",
        "context": "这是一次产品发布。", "significance": "可测试新 API。",
        "watch": "关注 API 开放时间。", "detail": "OpenAI 公布了模型与评测。",
        "claims": [{"text": "OpenAI 公布评测", "kind": "fact", "sources": ["OpenAI"]}],
        "status": "已确认", "tags": [], "score": 80, "tier": "T1",
        "evidence": {"basis": "snippet", "publisher_count": 1,
                     "independent_chain_count": 0, "degraded": True},
    }


def all_pass(event):
    return {
        "fields": {field: True for field in dn.OBJECTIVITY_FIELDS if field in event},
        "claims": [True for _ in event.get("claims", [])],
    }


def test_audit_llm_config_inherits_core_and_allows_independent_extra_body_override():
    cfg = {"llm": {
        "base_url": "https://main.example/v1", "api_key": "main-key", "model": "main-model",
        "temperature": 0.3, "max_retries": 3,
        "extra_body": {"thinking": {"type": "disabled"}},
    }, "audit_llm": {"base_url": "", "api_key": "", "model": ""}}
    inherited = dn.resolve_llm_config(cfg, "audit_llm")
    assert inherited == cfg["llm"]

    cfg["audit_llm"] = {
        "base_url": "", "api_key": "audit-key", "model": "audit-model",
        "extra_body": {"response_format": {"type": "json_object"}},
    }
    overridden = dn.resolve_llm_config(cfg, "audit_llm")
    assert overridden["base_url"] == cfg["llm"]["base_url"]
    assert overridden["api_key"] == "audit-key"
    assert overridden["model"] == "audit-model"
    assert overridden["extra_body"] == {"response_format": {"type": "json_object"}}


def test_normal_event_uses_one_audit_call_and_updates_counter():
    items = [source_item()]
    event = enriched_event()
    audit = QueueLLM([all_pass(event)])
    quality = dn.new_quality_stats()

    dn.audit_enrichment_support(audit, [event], items, quality, secondary=[])

    assert len(audit.calls) == 1
    assert quality["enrichment_audited_events"] == 1
    assert quality["objectivity_audited"] == 1
    assert quality["objectivity_repaired"] == 0
    assert quality["objectivity_degraded"] == 0


def test_failed_fields_are_repaired_once_reaudited_and_valid_fields_preserved():
    items = [source_item()]
    event = enriched_event()
    original_title = event["title"]
    original_context = event["context"]
    first = all_pass(event)
    first["fields"]["summary"] = False
    first["claims"][0] = False
    repaired_claim = {"text": "OpenAI 称其公布了评测", "kind": "fact", "sources": ["OpenAI"]}
    repaired = {
        "fields": {"summary": "OpenAI 发布模型，并公布其评测结果。"},
        "claims": [{"index": 0, **repaired_claim}],
    }
    after = all_pass(event)
    audit = QueueLLM([first, repaired, after])
    quality = dn.new_quality_stats()

    dn.audit_enrichment_support(audit, [event], items, quality, secondary=[])

    assert len(audit.calls) == 3
    assert event["summary"] == repaired["fields"]["summary"]
    assert event["claims"] == [repaired_claim]
    assert event["title"] == original_title
    assert event["context"] == original_context
    assert quality["objectivity_repaired"] == 1
    repair_payload = json.loads(audit.calls[1][1])
    assert set(repair_payload["failed_fields"]) == {"summary"}
    assert repair_payload["failed_claim_indexes"] == [0]


def test_failed_reaudit_degrades_and_demotes_only_high_risk_event():
    items = [source_item(title="检方提交起诉书", desc="Reuters 报道检方提交了起诉书。", source="Reuters", source_id="reuters")]
    event = enriched_event(title="被告已经犯罪")
    event["risk_flags"] = {"allegation_legal": True}
    picked, secondary = [event], []
    first = all_pass(event)
    first["fields"]["title"] = False
    again = all_pass(event)
    again["fields"]["title"] = False
    audit = QueueLLM([first, {"fields": {"title": "检方提交起诉书"}, "claims": []}, again])
    quality = dn.new_quality_stats()

    dn.audit_enrichment_support(audit, picked, items, quality, secondary=secondary)

    assert picked == [] and secondary == [event]
    assert event["title"] == "Reuters：检方提交起诉书"
    assert event["summary"] == "Reuters 报道：Reuters 报道检方提交了起诉书。"
    assert all(field not in event for field in dn.QUALITY_EXTENSION_FIELDS)
    assert event["evidence"]["degraded"] is True
    assert quality["objectivity_degraded"] == 1
    assert quality["high_risk_demoted"] == 1


def test_ordinary_failed_reaudit_remains_picked_and_failure_is_isolated():
    items = [source_item(), source_item("Meta 发布工具", "Meta 发布一款工具。", "Meta", "meta")]
    bad = enriched_event()
    good = enriched_event(1, "Meta 发布工具")
    good["summary"] = "Meta 发布一款工具。"
    good["claims"] = [{"text": "Meta 发布工具", "kind": "fact", "sources": ["Meta"]}]
    first_bad = all_pass(bad)
    first_bad["fields"]["detail"] = False
    second_bad = all_pass(bad)
    second_bad["fields"]["detail"] = False
    audit = QueueLLM([
        first_bad, RuntimeError("repair unavailable"), second_bad,
        all_pass(good),
    ])
    picked, secondary = [bad, good], []
    quality = dn.new_quality_stats()

    dn.audit_enrichment_support(audit, picked, items, quality, secondary=secondary)

    assert picked == [bad, good] and secondary == []
    assert bad["title"] == "OpenAI：OpenAI 发布模型"
    assert good["title"] == "Meta 发布工具"
    assert quality["objectivity_audited"] == 2
    assert quality["objectivity_degraded"] == 1


def test_downstream_consumers_run_after_objectivity_audit():
    source = inspect.getsource(dn.main)
    audit_pos = source.index("audit_enrichment_support")
    assert audit_pos < source.index("track_events")
    assert audit_pos < source.index("write_brief")
    assert audit_pos < source.index("write_output")
    assert audit_pos < source.index("write_weekly")


def test_brief_members_from_picked_and_secondary_are_both_audited():
    items = [source_item(), source_item("Meta 发布工具", "Meta 发布一款工具。", "Meta", "meta")]
    picked = [enriched_event()]
    secondary = [enriched_event(1, "Meta 发布工具")]
    secondary[0]["claims"] = [
        {"text": "Meta 发布工具", "kind": "fact", "sources": ["Meta"]}]
    audit = QueueLLM([all_pass(picked[0]), all_pass(secondary[0])])
    quality = dn.new_quality_stats()

    dn.audit_enrichment_support(audit, picked, items, quality, secondary=secondary)

    assert len(audit.calls) == 2
    assert quality["objectivity_audited"] == 2


def test_brief_repairs_failed_fields_drops_still_unsafe_theme_and_omits_unsafe_synthesis():
    picked = [enriched_event()]
    secondary = [enriched_event(1, "Meta 发布工具")]
    generator = QueueLLM([{
        "synthesis": "两家公司意在垄断市场",
        "themes": [
            {"title": "模型竞争", "one_liner": "两家公司意在垄断", "member_ids": ["pick-0", "more-1"]},
            {"title": "产品发布", "one_liner": "两家公司发布产品", "member_ids": ["pick-0", "more-1"]},
        ],
    }])
    first = {"synthesis": False, "themes": [
        {"index": 0, "title": True, "one_liner": False},
        {"index": 1, "title": True, "one_liner": True},
    ]}
    repair = {"synthesis": "两家公司发布产品", "themes": [
        {"index": 0, "one_liner": "两家公司发布产品"},
    ]}
    second = {"synthesis": False, "themes": [
        {"index": 0, "title": True, "one_liner": False},
        {"index": 1, "title": True, "one_liner": True},
    ]}
    audit = QueueLLM([first, repair, second])

    synthesis, themes = dn.write_brief(generator, picked, secondary, audit_llm=audit)

    assert synthesis == ""
    assert [theme["title"] for theme in themes] == ["产品发布"]
    assert len(audit.calls) == 3


def _write_week_days(data_dir):
    daily = data_dir / "daily"
    daily.mkdir(parents=True)
    for day in (6, 7, 8, 9, 10):
        date = f"2026-07-{day:02d}"
        payload = {"date": date, "items": [{
            "id": "pick-0", "tier": "pick", "category": "ai",
            "title": f"事件 {day}", "summary": f"来源确认事件 {day}",
            "why": "", "sources": [{"name": "Wire", "url": "https://example.com"}],
        }]}
        (daily / f"{date}.js").write_text(
            f'window.NEWS_DATA["{date}"] = {json.dumps(payload, ensure_ascii=False)};\n',
            encoding="utf-8")


def test_weekly_reaudit_failure_skips_writing_report(tmp_path):
    _write_week_days(tmp_path)
    refs = [f"2026-07-{day:02d}:pick-0" for day in (6, 7, 8)]
    generator = QueueLLM([{
        "lead": {"title": "本周主线", "summary": "无依据总述"},
        "threads": [{
            "title": f"主题 {i}", "one_liner": "事实", "direction": "推进", "detail": "事实",
            "member_refs": [ref], "representative_refs": [ref],
        } for i, ref in enumerate(refs)],
        "watch_recap": [], "outlook": ["无依据预测"],
    }])
    first = {"lead": False, "threads": [True, True, True],
             "watch_recap": [], "outlook": [False]}
    repair = {"lead": {"summary": "来源支持的总述"},
              "threads": [], "watch_recap": [], "outlook": [{"index": 0, "text": "观察后续"}]}
    second = {"lead": True, "threads": [True, True, True],
              "watch_recap": [], "outlook": [False]}
    audit = QueueLLM([first, repair, second])

    result = dn.write_weekly(
        generator, "2026-07-15",
        {"weekly": {"enabled": True, "min_daily_count": 5, "keep_weeks": 26}},
        tmp_path, audit_llm=audit)

    assert result is None
    assert not (tmp_path / "weekly" / "2026-W28.js").exists()
    assert len(audit.calls) == 3


def test_quality_counters_and_structural_evidence_validation_are_json_safe():
    quality = dn.new_quality_stats()
    for name in ("objectivity_audited", "objectivity_repaired",
                 "objectivity_degraded", "high_risk_demoted"):
        assert quality[name] == 0
    json.dumps(quality)
    payload = {
        "quality": quality,
        "items": [{
            "id": "pick-0", "sources": [{"name": "OpenAI", "url": "https://example.com",
                                             "evidence_basis": "snippet"}],
            "evidence": {"basis": "snippet", "publisher_count": 2,
                         "independent_chain_count": 0, "degraded": True},
        }],
    }
    assert any("evidence" in error for error in dn.validate_daily_payload(payload))


def test_legal_wording_distinguishes_procedural_filing_from_allegations_and_conviction():
    assert "程序性事实" in dn.ENRICH_SYSTEM
    assert "不等于定罪" in dn.ENRICH_SYSTEM
    assert "程序性事实" in dn.OBJECTIVITY_AUDIT_SYSTEM


# ---------------------------------------------------------------------------
# Task 2 review fixes
# ---------------------------------------------------------------------------


def test_triage_shaped_secondary_materializes_reader_summary_before_audit():
    desc = "Meta 发布一款开发工具，并公布了开放时间。" * 8
    items = [source_item("Meta 发布工具", desc, "Meta", "meta")]
    secondary = [{
        "ids": [0], "category": "ai", "title": "Meta 发布工具",
        "dims": {name: 7 for name in dn.DIMS}, "score": 65, "tier": "T1",
    }]
    audit = QueueLLM([{
        "fields": {"title": True, "summary": True}, "claims": [],
    }])

    dn.audit_enrichment_support(
        audit, [], items, dn.new_quality_stats(), secondary=secondary)

    audited_payload = json.loads(audit.calls[0][1])
    assert audited_payload["content"]["summary"] == desc[:100]
    assert secondary[0]["summary"] == desc[:100]
    assert dn.event_to_item(secondary[0], items, "more")["summary"] == desc[:100]


def test_high_risk_demotion_reaches_brief_and_serialization_as_audited_more_item():
    items = [source_item(
        "检方提交起诉书", "检方提交起诉书，文件指控被告实施违法行为。", "Reuters", "reuters")]
    event = {
        "ids": [0], "category": "world", "title": "被告已经犯罪",
        "summary": "被告已经犯罪。", "score": 80, "tier": "T1", "tags": [],
        "risk_flags": {"allegation_legal": True},
        "evidence": {"basis": "snippet", "publisher_count": 1,
                     "independent_chain_count": 0, "degraded": True},
    }
    first = {"fields": {"title": False, "summary": False}, "claims": []}
    repair = {"fields": {"title": "检方提交起诉书", "summary": "检方指控被告违法。"},
              "claims": []}
    second = {"fields": {"title": False, "summary": False}, "claims": []}
    audit = QueueLLM([first, repair, second])
    picked, secondary = [event], []

    dn.audit_enrichment_support(
        audit, picked, items, dn.new_quality_stats(), secondary=secondary)
    brief_llm = QueueLLM([{"synthesis": "", "themes": []}])
    dn.write_brief(brief_llm, picked, secondary)
    serialized = dn.event_to_item(
        secondary[0], items, "more", full_objectivity=True, source_limit=4)

    assert picked == [] and secondary == [event]
    assert "[more-0]" in brief_llm.calls[0][1]
    assert "Reuters：检方提交起诉书" in brief_llm.calls[0][1]
    assert serialized["tier"] == "more"
    assert serialized["title"] == "Reuters：检方提交起诉书"
    assert serialized["summary"].startswith("Reuters 报道：")
    assert serialized["evidence"]["degraded"] is True


def weekly_payload_for_audit():
    return {
        "lead": {"title": "一周主线", "summary": "整周变化"},
        "threads": [
            {"title": "主题 A", "one_liner": "A 推进", "detail": "A 详情",
             "direction": "推进", "member_refs": ["2026-07-06:pick-a"],
             "representative_refs": ["2026-07-06:pick-a"]},
            {"title": "主题 B", "one_liner": "B 推进", "detail": "B 详情",
             "direction": "推进", "member_refs": ["2026-07-07:pick-b"],
             "representative_refs": ["2026-07-07:pick-b"]},
        ],
        "watch_recap": [
            {"prior": "观察 A", "status": "兑现", "note": "A 已发生",
             "evidence_refs": ["2026-07-06:pick-a"]},
        ],
        "outlook": ["观察下一周"],
    }


def weekly_refs_for_audit():
    return {
        "2026-07-06:pick-a": ("item", {"title": "A", "summary": "A 事实"}),
        "2026-07-07:pick-b": ("item", {"title": "B", "summary": "B 事实"}),
        "2026-07-08:pick-unrelated": (
            "item", {"title": "无关事件", "summary": "不得支撑 A 或 B"}),
    }


def test_weekly_audit_maps_local_evidence_by_explicit_refs_only():
    payload = weekly_payload_for_audit()
    audit = QueueLLM([{
        "lead": True, "threads": [True, True],
        "watch_recap": [True], "outlook": [True],
    }])

    assert dn._audit_weekly(audit, payload, weekly_refs_for_audit()) is True

    request = json.loads(audit.calls[0][1])
    assert set(request["whole_week_evidence"]) == {
        "2026-07-06:pick-a", "2026-07-07:pick-b", "2026-07-08:pick-unrelated"}
    assert request["thread_evidence"] == [
        {"index": 0, "refs": ["2026-07-06:pick-a"],
         "items": {"2026-07-06:pick-a": {"title": "A", "summary": "A 事实"}}},
        {"index": 1, "refs": ["2026-07-07:pick-b"],
         "items": {"2026-07-07:pick-b": {"title": "B", "summary": "B 事实"}}},
    ]
    assert request["watch_recap_evidence"] == [
        {"index": 0, "refs": ["2026-07-06:pick-a"],
         "items": {"2026-07-06:pick-a": {"title": "A", "summary": "A 事实"}}},
    ]


def test_weekly_targeted_repair_succeeds_without_changing_refs_or_valid_rows():
    payload = weekly_payload_for_audit()
    before_refs = {
        "threads": [(row["member_refs"], row["representative_refs"])
                    for row in payload["threads"]],
        "watch": [row["evidence_refs"] for row in payload["watch_recap"]],
    }
    valid_thread = dict(payload["threads"][1])
    audit = QueueLLM([
        {"lead": True, "threads": [False, True],
         "watch_recap": [False], "outlook": [True]},
        {"threads": [{"index": 0, "title": "修复 A",
                       "member_refs": ["2026-07-08:pick-unrelated"],
                       "representative_refs": ["2026-07-08:pick-unrelated"]}],
         "watch_recap": [{"index": 0, "note": "A 来源确认",
                           "evidence_refs": ["2026-07-08:pick-unrelated"]}]},
        {"lead": True, "threads": [True, True],
         "watch_recap": [True], "outlook": [True]},
    ])

    assert dn._audit_weekly(audit, payload, weekly_refs_for_audit()) is True

    after_refs = {
        "threads": [(row["member_refs"], row["representative_refs"])
                    for row in payload["threads"]],
        "watch": [row["evidence_refs"] for row in payload["watch_recap"]],
    }
    assert after_refs == before_refs
    assert payload["threads"][0]["title"] == "修复 A"
    assert payload["threads"][1] == valid_thread
    assert payload["watch_recap"][0]["note"] == "A 来源确认"
    repair_request = json.loads(audit.calls[1][1])
    assert repair_request["failed"] == {
        "lead": False, "threads": [0], "watch_recap": [0], "outlook": []}


def test_weekly_clean_audit_succeeds_with_one_call():
    payload = weekly_payload_for_audit()
    audit = QueueLLM([{
        "lead": True, "threads": [True, True],
        "watch_recap": [True], "outlook": [True],
    }])
    assert dn._audit_weekly(audit, payload, weekly_refs_for_audit()) is True
    assert len(audit.calls) == 1


def evidence_payload(sources, basis, publisher_count, chain_count=0):
    return {
        "quality": dn.new_quality_stats(),
        "items": [{
            "id": "pick-0", "title": "Reader title", "sources": sources,
            "evidence": {"basis": basis, "publisher_count": publisher_count,
                         "independent_chain_count": chain_count, "degraded": True},
        }],
    }


def test_evidence_validation_derives_exact_publisher_count_and_basis():
    snippet = {"name": "Wire", "url": "https://example.com/a",
               "evidence_basis": "snippet"}
    fulltext = {"name": "Other", "url": "https://example.com/b",
                "evidence_basis": "fulltext"}

    assert any("publisher" in error for error in dn.validate_daily_payload(
        evidence_payload([snippet], "snippet", 0)))
    assert any("basis" in error for error in dn.validate_daily_payload(
        evidence_payload([snippet], "fulltext", 1)))
    assert dn.validate_daily_payload(
        evidence_payload([snippet, fulltext], "mixed", 2)) == []


def test_evidence_validation_rejects_duplicate_publisher_inflation():
    sources = [
        {"name": "Wire", "url": "https://example.com/a", "evidence_basis": "snippet"},
        {"name": "Wire", "url": "https://example.com/b", "evidence_basis": "snippet"},
    ]
    errors = dn.validate_daily_payload(evidence_payload(sources, "snippet", 2))
    assert any("publisher" in error for error in errors)
    errors = dn.validate_daily_payload(evidence_payload(sources, "snippet", 1))
    assert any("sources are not unique" in error for error in errors)


def test_evidence_validation_explicitly_rejects_chain_count_above_publishers():
    sources = [{
        "name": "Wire", "url": "https://example.com/a",
        "evidence_basis": "snippet", "evidence_chain": "wire-chain",
    }]
    errors = dn.validate_daily_payload(
        evidence_payload(sources, "snippet", 1, chain_count=2))
    assert any("cannot exceed publisher_count" in error for error in errors)


def test_stable_source_selection_deduplicates_publishers_before_contract_and_output():
    items = [
        source_item("Wire update one", "one", "Wire", "wire-one"),
        source_item("Wire update two", "two", "Wire", "wire-two"),
        source_item("Other report", "other", "Other", "other"),
    ]
    for index, item in enumerate(items):
        item.update({
            "url": f"https://example.com/{index}",
            "source_family": item["source_id"], "provenance": "original",
        })
    event = {
        "ids": [1, 0, 2], "category": "ai", "title": "event", "summary": "summary",
        "score": 80, "tier": "T1", "tags": [],
    }

    dn.apply_evidence_contract(event, items)
    serialized = dn.event_to_item(
        event, items, "pick", full_objectivity=True, source_limit=4)

    assert [source["name"] for source in serialized["sources"]] == ["Other", "Wire"]
    assert serialized["evidence"]["publisher_count"] == 2
    assert dn.validate_daily_payload({
        "quality": dn.new_quality_stats(), "items": [serialized],
    }) == []


def test_serialized_chain_identity_makes_independent_count_verifiable():
    item = source_item()
    item.update({"source_family": "openai-primary", "provenance": "official"})
    event = enriched_event()
    event["evidence"] = {"basis": "snippet", "publisher_count": 1,
                         "independent_chain_count": 1, "degraded": True}

    serialized = dn.event_to_item(
        event, [item], "pick", full_objectivity=True, source_limit=4)

    assert serialized["sources"][0]["evidence_chain"] == "openai-primary"
    valid = {"quality": dn.new_quality_stats(), "items": [serialized]}
    assert dn.validate_daily_payload(valid) == []
    serialized["evidence"]["independent_chain_count"] = 0
    assert any("chain" in error for error in dn.validate_daily_payload(valid))


def test_audit_llm_config_block_shows_all_supported_override_fields():
    block = (Path(dn.ROOT) / "config.yaml").read_text(encoding="utf-8").split(
        "audit_llm:", 1)[1].split("prefilter:", 1)[0]
    for field in ("base_url", "api_key", "model", "temperature", "max_retries", "extra_body"):
        assert f"{field}:" in block


def test_legal_procedural_fact_repair_preserves_attributed_filing_claim():
    items = [source_item(
        "检方提交起诉书", "检方提交起诉书，文件指控被告实施违法行为。", "Reuters", "reuters")]
    event = enriched_event(title="被告已经犯罪")
    event["summary"] = "检方提交起诉书。"
    event["claims"] = [{"text": "检方提交起诉书", "kind": "fact", "sources": ["Reuters"]}]
    first = all_pass(event)
    first["fields"]["title"] = False
    audit = QueueLLM([
        first,
        {"fields": {"title": "Reuters 报道检方提交起诉书，文件指控被告违法"},
         "claims": []},
        all_pass(event),
    ])

    dn.audit_enrichment_support(audit, [event], items, dn.new_quality_stats(), secondary=[])

    assert event["title"] == "Reuters 报道检方提交起诉书，文件指控被告违法"
    assert event["claims"] == [
        {"text": "检方提交起诉书", "kind": "fact", "sources": ["Reuters"]}]


def test_reordered_event_uses_one_stable_top_four_for_generation_audit_repair_and_output():
    specs = [
        ("C", "c", 8), ("E", "e", 7), ("B", "b", 9),
        ("A", "a", 9), ("D", "d", 8),
    ]
    items = []
    for name, source_id, credibility in specs:
        item = source_item(
            f"{name} 标题", f"{name} 证据说明。", name, source_id)
        item.update({
            "credibility": credibility,
            "source_family": f"family-{source_id}",
            "provenance": "original",
        })
        items.append(item)
    event = {
        "ids": [0, 4, 1, 2, 3], "category": "ai", "title": "聚合事件",
        "score": 80, "tier": "T1", "tags": [],
    }
    dn.apply_evidence_contract(event, items)
    generator = QueueLLM([[{
        "idx": 0, "title": "四源事件", "summary": "四源共同信息",
        "why": "影响开发者", "context": "发布背景", "significance": "可测试",
        "watch": "关注后续", "status": "已确认", "tags": [],
        "claims": [{"text": "A 提供首要证据", "kind": "fact", "source_indexes": [0]}],
    }]])

    dn.enrich(generator, [event], items, {
        "topic_tags": [], "detail": {"enabled": False},
        "_objectivity_runtime_mode": "active",
    })

    generation_prompt = generator.calls[0][1]
    assert [generation_prompt.index(f"[{name}|") for name in ("A", "B", "C", "D")] == sorted(
        generation_prompt.index(f"[{name}|") for name in ("A", "B", "C", "D"))
    assert "[E|" not in generation_prompt
    assert event["claims"][0]["sources"] == ["A"]

    first = all_pass(event)
    first["fields"]["summary"] = False
    audit = QueueLLM([
        first,
        {"fields": {"summary": "A 与 B 报道共同信息"}, "claims": []},
        all_pass(event),
    ])
    dn.audit_enrichment_support(
        audit, [event], items, dn.new_quality_stats(), secondary=[])

    audit_payload = json.loads(audit.calls[0][1])
    assert [report["source"] for report in audit_payload["reports"]] == ["A", "B", "C", "D"]
    repair_payload = json.loads(audit.calls[1][1])
    assert [report["source"] for report in repair_payload["reports"]] == ["A", "B", "C", "D"]
    serialized = dn.event_to_item(
        event, items, "pick", full_objectivity=True, source_limit=4)
    assert [source["name"] for source in serialized["sources"]] == ["A", "B", "C", "D"]
    assert serialized["evidence"] == {
        "basis": "snippet", "publisher_count": 4,
        "independent_chain_count": 4, "degraded": True,
    }


@pytest.mark.parametrize("runtime_mode", ["active", "shadow"])
def test_full_secondary_serialization_explicitly_uses_stable_top_four(
        tmp_path, monkeypatch, runtime_mode):
    specs = [
        ("C", "c", 8), ("E", "e", 7), ("B", "b", 9),
        ("A", "a", 9), ("D", "d", 8),
    ]
    items = []
    for name, source_id, credibility in specs:
        item = source_item(
            f"{name} 标题", f"{name} 摘要", name, source_id)
        item.update({
            "credibility": credibility,
            "source_family": f"family-{source_id}",
            "provenance": "original",
        })
        items.append(item)
    secondary = [{
        "ids": [0, 4, 1, 2, 3], "category": "ai", "title": "聚合事件",
        "summary": "四源摘要", "score": 65, "tier": "T1", "tags": [],
    }]
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    payload = dn.write_output(
        "2026-07-18", "brief", [], secondary, items,
        {
            "objectivity": {"mode": "active" if runtime_mode == "active" else "interim"},
            "_objectivity_runtime_mode": runtime_mode,
        },
        quality=dn.new_quality_stats())

    serialized = payload["items"][0]
    assert serialized["tier"] == "more"
    assert [source["name"] for source in serialized["sources"]] == ["A", "B", "C", "D"]
    assert serialized["evidence"] == {
        "basis": "snippet", "publisher_count": 4,
        "independent_chain_count": 4, "degraded": True,
    }
    assert dn.validate_daily_payload(payload) == []

    interim_dir = tmp_path / "interim"
    monkeypatch.setenv("DATA_DIR", str(interim_dir))
    interim_secondary = [{
        "ids": [0, 4, 1, 2, 3], "category": "ai", "title": "聚合事件",
        "summary": "五源摘要", "score": 65, "tier": "T1", "tags": [],
    }]
    interim_payload = dn.write_output(
        "2026-07-18", "brief", [], interim_secondary, items,
        {"objectivity": {"mode": "interim"}}, quality=dn.new_quality_stats())
    interim_item = interim_payload["items"][0]
    assert [source["name"] for source in interim_item["sources"]] == [
        "A", "B", "C", "D", "E"]
    assert "evidence" not in interim_item
    assert all("evidence_basis" not in source for source in interim_item["sources"])


def test_full_audit_rejects_legacy_support_only_reply_and_repairs_before_accepting():
    items = [source_item()]
    event = enriched_event()
    legacy = {
        "fields": {
            "why": True, "context": True, "significance": True,
            "watch": True, "detail": True,
        },
        "supported_claim_indexes": [0],
    }
    audit = QueueLLM([
        legacy,
        {
            "fields": {
                "title": "OpenAI 发布模型", "summary": "OpenAI 公布模型与评测。",
                "why": "影响开发者", "context": "产品发布", "significance": "可测试 API",
                "watch": "关注开放时间", "detail": "OpenAI 公布模型与评测。",
            },
            "claims": [{
                "index": 0, "text": "OpenAI 公布评测", "kind": "fact",
                "sources": ["OpenAI"],
            }],
        },
        all_pass(event),
    ])
    quality = dn.new_quality_stats()

    dn.audit_enrichment_support(audit, [event], items, quality, secondary=[])

    assert len(audit.calls) == 3
    assert audit.calls[1][0] == dn.OBJECTIVITY_REPAIR_SYSTEM
    assert quality["objectivity_repaired"] == 1


def test_interim_support_audit_keeps_legacy_reply_compatibility():
    items = [source_item()]
    event = enriched_event()
    audit = QueueLLM([{
        "fields": {
            "why": True, "context": True, "significance": True,
            "watch": True, "detail": True,
        },
        "supported_claim_indexes": [0],
    }])

    quality = dn.new_quality_stats()
    dn.audit_enrichment_support_interim(audit, [event], items, quality)

    assert len(audit.calls) == 1
    assert quality["enrichment_audited_events"] == 1
    assert event["claims"] == [{
        "text": "OpenAI 公布评测", "kind": "fact", "sources": ["OpenAI"]}]


def test_full_audit_counts_selected_and_secondary_reader_events():
    items = [
        source_item(),
        source_item("Meta 发布工具", "Meta 发布一款工具。", "Meta", "meta"),
    ]
    picked = [enriched_event()]
    secondary = [enriched_event(1, "Meta 发布工具")]
    secondary[0]["summary"] = "Meta 发布一款工具。"
    secondary[0]["claims"] = []
    audit = QueueLLM([all_pass(picked[0]), all_pass(secondary[0])])
    quality = dn.new_quality_stats()

    dn.audit_enrichment_support(
        audit, picked, items, quality, secondary=secondary)

    assert quality["enrichment_audited_events"] == 2


def test_daily_brief_scopes_synthesis_to_whole_day_and_theme_to_member_ids_only():
    picked = [enriched_event()]
    secondary = [enriched_event(1, "无关公司发布工具")]
    secondary[0]["summary"] = "无关公司发布另一款工具。"
    generator = QueueLLM([{
        "synthesis": "今日有两项发布",
        "themes": [{
            "title": "模型发布", "one_liner": "OpenAI 公布模型",
            "member_ids": ["pick-0"],
        }],
    }])
    audit = QueueLLM([
        {"synthesis": True, "themes": [
            {"index": 0, "title": False, "one_liner": True},
        ]},
        {"themes": [{
            "index": 0, "title": "OpenAI 模型",
            "member_ids": ["more-1"],
        }]},
        {"synthesis": True, "themes": [
            {"index": 0, "title": True, "one_liner": True},
        ]},
    ])

    synthesis, themes = dn.write_brief(
        generator, picked, secondary, audit_llm=audit)

    initial_payload = json.loads(audit.calls[0][1])
    assert set(initial_payload["whole_day_evidence"]) == {"pick-0", "more-1"}
    assert initial_payload["theme_evidence"] == [{
        "index": 0,
        "member_ids": ["pick-0"],
        "items": {"pick-0": initial_payload["whole_day_evidence"]["pick-0"]},
    }]
    assert "more-1" not in initial_payload["theme_evidence"][0]["items"]
    repair_payload = json.loads(audit.calls[1][1])
    assert repair_payload["theme_evidence"] == initial_payload["theme_evidence"]
    assert synthesis == "今日有两项发布"
    assert themes[0]["title"] == "OpenAI 模型"
    assert themes[0]["member_ids"] == ["pick-0"]


def test_shadow_weekly_force_regenerates_and_audits_existing_snapshot_file(tmp_path):
    _write_week_days(tmp_path)
    weekly_dir = tmp_path / "weekly"
    weekly_dir.mkdir()
    target = weekly_dir / "2026-W28.js"
    target.write_text(
        'window.WEEKLY_DATA["2026-W28"] = {"version":1,"week":"2026-W28"};\n',
        encoding="utf-8",
    )
    before = target.read_bytes()
    refs = [f"2026-07-{day:02d}:pick-0" for day in (6, 7, 8)]
    generator = QueueLLM([{
        "lead": {"title": "本周主线", "summary": "来源支持的整周总述"},
        "threads": [{
            "title": f"主题 {index}", "one_liner": "来源支持的事实",
            "direction": "推进", "detail": "来源支持的详情",
            "member_refs": [ref], "representative_refs": [ref],
        } for index, ref in enumerate(refs)],
        "watch_recap": [], "outlook": [],
    }])
    audit = QueueLLM([{
        "lead": True, "threads": [True, True, True],
        "watch_recap": [], "outlook": [],
    }])

    result = dn.write_weekly(
        generator, "2026-07-15",
        {"weekly": {"enabled": True, "min_daily_count": 5, "keep_weeks": 26}},
        tmp_path, audit_llm=audit, force=True)

    assert result["version"] == 2
    assert target.read_bytes() != before
    assert len(generator.calls) == 1
    assert len(audit.calls) == 1


def test_production_sources_declare_explicit_provenance_and_yield_trusted_chains():
    config = yaml.safe_load(
        (Path(dn.ROOT) / "sources.yaml").read_text(encoding="utf-8"))
    sources = config["sources"]
    assert sources
    assert all(str(source.get("source_family") or "").strip() for source in sources)
    assert all(str(source.get("provenance") or "").strip() for source in sources)
    trusted = [
        source for source in sources
        if source["provenance"] in {"original", "official", "first_party"}
    ]
    assert trusted

    items = []
    for source in trusted[:4]:
        item = source_item(source=source["name"], source_id=source["id"])
        item.update({
            "source_family": source["source_family"],
            "provenance": source["provenance"],
        })
        items.append(item)
    event = {"ids": list(range(len(items)))}
    evidence = dn.apply_evidence_contract(event, items)
    assert evidence["independent_chain_count"] > 0


def test_raw_pool_corroboration_accepts_only_different_explicit_trusted_chain():
    selected = source_item(
        "检方调查公司", "检方调查公司。", "Origin Wire", "origin-wire")
    selected.update({
        "source_family": "wire-family", "provenance": "original",
        "credibility": 9,
    })
    event = {"ids": [0], "category": "world", "title": "检方调查公司"}

    def candidate(source, source_id, family, provenance):
        row = source_item(
            "检方调查公司", "检方调查公司。", source, source_id)
        row.update({
            "source_family": family, "provenance": provenance,
            "credibility": 8,
        })
        return row

    raw_pool = [
        candidate("Sister Desk", "sister", "wire-family", "original"),
        candidate("Unknown Desk", "unknown", "unknown-family", "unclear"),
        candidate("Independent Desk", "independent", "independent-family", "original"),
    ]
    items = [selected]
    quality = dn.new_quality_stats()

    dn.corroborate_high_risk_events([event], items, raw_pool, quality)

    assert [items[index]["source"] for index in event["ids"]] == [
        "Origin Wire", "Independent Desk"]
    assert quality["corroboration_matches"] == 1


def test_corroboration_need_uses_distinct_trusted_chains_not_source_ids():
    first = source_item(
        "Bridge collapse kills 12", "Bridge collapse kills 12.",
        "Desk One", "desk-one")
    second = source_item(
        "Bridge collapse kills 12", "Bridge collapse kills 12.",
        "Desk Two", "desk-two")
    for item in (first, second):
        item.update({
            "source_family": "shared-wire", "provenance": "original",
            "credibility": 9,
        })
    candidate = source_item(
        "Bridge collapse kills 12", "Bridge collapse kills 12.",
        "Independent", "independent")
    candidate.update({
        "source_family": "independent-chain", "provenance": "original",
        "credibility": 8,
    })
    event = {
        "ids": [0, 1], "category": "society",
        "title": "Bridge collapse kills 12", "status": "发展中",
    }
    items = [first, second]
    quality = dn.new_quality_stats()

    dn.corroborate_high_risk_events([event], items, [candidate], quality)

    assert [items[index]["source"] for index in event["ids"]] == [
        "Desk One", "Desk Two", "Independent"]
    assert quality["high_risk_single_publisher"] == 1
    assert quality["corroboration_matches"] == 1


def test_ranked_corroboration_rechecks_updated_chain_before_each_append():
    selected = source_item(
        "Bridge collapse kills 12", "Bridge collapse kills 12.",
        "Origin", "origin")
    selected.update({
        "source_family": "origin-chain", "provenance": "original",
        "credibility": 9,
    })

    def candidate(source, source_id, url):
        item = source_item(
            "Bridge collapse kills 12", "Bridge collapse kills 12.",
            source, source_id)
        item.update({
            "url": url, "source_family": "same-new-chain",
            "provenance": "original", "credibility": 8,
        })
        return item

    candidates = [
        candidate("Candidate One", "candidate-one", "https://one.example/story"),
        candidate("Candidate Two", "candidate-two", "https://two.example/story"),
    ]
    event = {
        "ids": [0], "category": "society",
        "title": "Bridge collapse kills 12", "status": "发展中",
    }
    items = [selected]

    dn.corroborate_high_risk_events(
        [event], items, candidates, dn.new_quality_stats())

    assert len(event["ids"]) == 2
    assert items[event["ids"][1]]["source"] == "Candidate One"


def test_article_stream_enforces_monotonic_total_deadline_and_closes_each_attempt():
    class Clock:
        def __init__(self):
            self.value = 0.0

        def __call__(self):
            return self.value

    class SlowResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self, clock):
            self.clock = clock
            self.closed = False

        def iter_content(self, chunk_size):
            yield b"<html><body>"
            self.clock.value += 10.1
            yield b"slow chunk" * 100

        def close(self):
            self.closed = True

    clock = Clock()
    responses = []
    timeouts = []

    def request_get(*_args, **kwargs):
        timeouts.append(kwargs["timeout"])
        response = SlowResponse(clock)
        responses.append(response)
        return response

    result = dn.fetch_article_evidence(
        {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
        request_get=request_get,
        extractor=lambda _html: "不应完成提取" * 100,
        resolver=lambda *_args, **_kwargs: [
            (None, None, None, None, ("93.184.216.34", 443))],
        sleep=lambda _seconds: None,
        clock=clock,
    )

    assert result["evidence_basis"] == "snippet"
    assert result["attempts"] == 3
    assert result["retries"] == 2
    assert len(responses) == 3
    assert all(response.closed for response in responses)
    assert [timeout.total for timeout in timeouts] == pytest.approx([10.0, 10.0, 10.0])
    assert all(timeout.read_timeout <= 1.0 for timeout in timeouts)


def test_slow_response_headers_fail_closed_with_each_retry_getting_new_budget():
    class Clock:
        def __init__(self):
            self.value = 0.0

        def __call__(self):
            return self.value

    class Response:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    clock = Clock()
    timeouts = []
    responses = []

    def request_get(*_args, **kwargs):
        timeout = kwargs["timeout"]
        timeouts.append(timeout)
        response = Response()
        responses.append(response)
        clock.value += timeout.total + 0.01
        return response

    result = dn.fetch_article_evidence(
        {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
        request_get=request_get,
        extractor=lambda _html: "不应执行",
        resolver=lambda *_args, **_kwargs: [
            (None, None, None, None, ("93.184.216.34", 443))],
        sleep=lambda _seconds: None,
        clock=clock,
    )

    assert result["evidence_basis"] == "snippet"
    assert result["attempts"] == 3
    assert result["retries"] == 2
    assert [timeout.total for timeout in timeouts] == pytest.approx([10.0, 10.0, 10.0])
    assert all(timeout.connect_timeout <= 3.0 for timeout in timeouts)
    assert all(timeout.read_timeout <= 1.0 for timeout in timeouts)
    assert all(response.closed for response in responses)


def test_article_redirect_receives_only_remaining_attempt_budget():
    class Clock:
        value = 0.0

        def __call__(self):
            return self.value

    class Response:
        def __init__(self, status=200, location=""):
            self.status_code = status
            self.headers = {"Content-Type": "text/html"}
            if location:
                self.headers["Location"] = location

        def iter_content(self, chunk_size):
            yield b"<html>ok</html>"

        def close(self):
            pass

    clock = Clock()
    timeouts = []

    def request_get(*_args, **kwargs):
        timeouts.append(kwargs["timeout"])
        if len(timeouts) == 1:
            clock.value += 9.0
            return Response(302, "https://next.example/story")
        return Response()

    result = dn.fetch_article_evidence(
        {"url": "https://news.example/item", "title": "标题", "desc": "摘要"},
        request_get=request_get,
        extractor=lambda _html: "有效正文" * 100,
        resolver=lambda *_args, **_kwargs: [
            (None, None, None, None, ("93.184.216.34", 443))],
        sleep=lambda _seconds: None,
        clock=clock,
    )

    assert result["evidence_basis"] == "fulltext"
    assert len(timeouts) == 2
    assert timeouts[1].total <= 1.0


def test_modes_share_reader_field_caps_while_full_mode_uses_fulltext_evidence():
    # 起因片段同时放进摘要与正文：interim 只核对摘要前 200 字，全文模式核对正文
    item = source_item(desc="正文证据正文证据正文证据" + "旧摘要" * 80)
    item["evidence_text"] = "FULLTEXT_ONLY_MARKER " + ("正文证据" * 200)
    long_values = {
        "title": "题" * 45,
        "summary": "摘" * 150,
        "why": "因" * 120,
        "context": "背景事实。" * 30,
        "watch": "看" * 80,
        "watch_detail": "详细走向。" * 30,
        "detail": "现状事实。" * 180,
    }

    def reply():
        return [[{
            "idx": 0, **long_values,
            "context_evidence": [{
                "source_index": 0,
                "quote": "正文证据正文证据正文证据",
            }],
            "claims": [], "status": "已确认", "tags": [],
        }]]

    interim_event = {
        "ids": [0], "category": "ai", "title": "原题",
        "score": 80, "tier": "T1", "tags": [],
    }
    interim_llm = QueueLLM(reply())
    dn.enrich(interim_llm, [interim_event], [dict(item)], {
        "topic_tags": [], "detail": {"enabled": True, "max_chars": 600},
        "_objectivity_runtime_mode": "interim",
    })

    assert "FULLTEXT_ONLY_MARKER" not in interim_llm.calls[0][1]
    assert "watch_detail" not in interim_event
    assert {field: len(interim_event[field]) for field in
            ("title", "summary", "context", "watch", "detail")} == {
        "title": len(long_values["title"]), "summary": 100,
        "context": 80, "watch": 80, "detail": 800,
    }
    interim_output_item = dict(item)
    interim_output_item.pop("evidence_text", None)
    interim_output_item["evidence_basis"] = "snippet"
    serialized_interim = dn.event_to_item(
        interim_event, [interim_output_item], "pick")
    assert serialized_interim["title"] == long_values["title"]
    assert len(serialized_interim["summary"]) == 100
    assert "why" not in serialized_interim
    assert len(serialized_interim["watch"]) == 80

    active_event = {
        "ids": [0], "category": "ai", "title": "原题",
        "score": 80, "tier": "T1", "tags": [],
        "evidence": {"basis": "fulltext", "publisher_count": 1,
                     "independent_chain_count": 0, "degraded": False},
    }
    active_llm = QueueLLM(reply())
    dn.enrich(active_llm, [active_event], [dict(item)], {
        "topic_tags": [], "detail": {"enabled": True, "max_chars": 600},
        "_objectivity_runtime_mode": "active",
    })

    assert "FULLTEXT_ONLY_MARKER" in active_llm.calls[0][1]
    assert "significance" not in active_event
    assert len(active_event["context"]) <= 240
    assert len(active_event["watch"]) == 80
    assert len(active_event["watch_detail"]) <= 260
    assert len(active_event["detail"]) <= 1200


def _breakdown_invariant(quality):
    """removed_fields 必须同时等于两个分项各自的和。"""
    total = quality["removed_fields"]
    return (sum(quality["removed_field_counts"].values()) == total
            and sum(quality["removed_field_reasons"].values()) == total)


def test_removed_field_breakdown_attributes_audit_removals_by_field_and_reason():
    items = [source_item(title="检方提交起诉书", desc="Reuters 报道检方提交了起诉书。",
                         source="Reuters", source_id="reuters")]
    event = enriched_event(title="被告已经犯罪")
    event["watch_detail"] = "详情走向会继续观察司法程序与公开文件。"
    event["risk_flags"] = {"allegation_legal": True}
    first = all_pass(event)
    first["fields"]["title"] = False
    again = all_pass(event)
    again["fields"]["title"] = False
    audit = QueueLLM([first, {"fields": {"title": "检方提交起诉书"}, "claims": []}, again])
    quality = dn.new_quality_stats()

    dn.audit_enrichment_support(audit, [event], items, quality, secondary=[])

    # 降级会剥掉全部扩展字段，分项必须逐个记到字段名上，原因全是审计判不支持。
    assert all(field not in event for field in dn.QUALITY_EXTENSION_FIELDS)
    assert quality["removed_field_counts"] == {field: 1 for field in dn.QUALITY_EXTENSION_FIELDS}
    assert quality["removed_field_reasons"]["audit_unsupported"] == quality["removed_fields"]
    assert _breakdown_invariant(quality)


def test_removed_field_breakdown_separates_evidence_copies_from_audit_removals():
    # 直抄判定对 detail 要求 80、claims 要求 60 个规范化字符，证据必须够长。
    body = "OpenAI 今日发布了新一代模型并同步公布了完整评测结果" * 5
    item = source_item(desc=body)
    item["evidence_basis"] = "fulltext"  # 直抄检测只对全文证据生效
    event = enriched_event()
    # 让 detail 与 claim 逐字照抄证据原文，触发直抄剥离而不是审计判定。
    event["detail"] = body
    event["claims"] = [{"text": body, "kind": "fact", "sources": ["OpenAI"]}]
    quality = dn.new_quality_stats()

    dn.sanitize_objectivity_event(event, [item], quality)

    assert "detail" not in event and "claims" not in event
    assert quality["removed_field_reasons"] == {
        "evidence_copy": quality["removed_fields"], "audit_unsupported": 0,
        "claim_unsupported": 0, "generation_invalid": 0}
    assert quality["removed_field_counts"]["detail"] == 1
    assert quality["removed_field_counts"]["claims"] == 1
    assert _breakdown_invariant(quality)


def test_evidence_copy_removal_cannot_leave_an_orphan_watch_detail():
    copied_watch = "未来走向取决于监管审批时间表和公开听证会是否按期举行" * 3
    item = source_item(desc=copied_watch)
    item["evidence_basis"] = "fulltext"
    event = enriched_event()
    event["watch"] = copied_watch
    event["watch_detail"] = (
        "详情走向将继续观察审批时间表，并以公开听证会日期为路标。")
    quality = dn.new_quality_stats()

    dn.sanitize_objectivity_event(event, [item], quality)

    assert "watch" not in event
    assert "watch_detail" not in event
    assert quality["removed_field_counts"]["watch"] == 1
    assert quality["removed_field_counts"]["watch_detail"] == 1
    assert quality["removed_field_reasons"]["evidence_copy"] == 2
    assert _breakdown_invariant(quality)


ENGLISH_DESC = "A new field report shows how scientists use AI coding agents to modernize legacy code."
CHINESE_DESC = "微软开源 4B 参数的 Mage-VL 与 Mage-Flow 模型，分别用于图像理解和图像编辑。"


@pytest.mark.parametrize("desc,kept", [
    (ENGLISH_DESC, False),
    (CHINESE_DESC, True),
    ("", False),
    ("   ", False),
])
def test_fallback_summary_only_survives_when_the_source_blurb_reads_as_chinese(desc, kept):
    assert bool(dn.readable_fallback_summary(desc)) is kept


def test_secondary_item_drops_untranslated_blurb_instead_of_passing_it_off_as_a_summary():
    items = [source_item("英文源条目", ENGLISH_DESC, "Guardian", "guardian")]
    event = {"ids": [0], "category": "world", "title": "中文标题已由阶段 A 生成",
             "dims": {name: 7 for name in dn.DIMS}, "score": 60, "tier": "T1"}

    serialized = dn.event_to_item(event, items, "more")

    # 次级不跑 enrich，摘要位只能回退到来源原文；英文原句不是我们写的摘要，宁可留空。
    assert "summary" not in serialized
    assert serialized["title"] == "中文标题已由阶段 A 生成"


def test_secondary_item_keeps_a_chinese_source_blurb():
    items = [source_item("中文源条目", CHINESE_DESC, "IT之家", "ithome")]
    event = {"ids": [0], "category": "ai", "title": "微软开源 Mage 模型",
             "dims": {name: 7 for name in dn.DIMS}, "score": 60, "tier": "T1"}

    assert dn.event_to_item(event, items, "more")["summary"] == CHINESE_DESC[:100]


@pytest.mark.parametrize("desc", [ENGLISH_DESC, CHINESE_DESC])
def test_audit_projection_and_serialization_agree_on_the_fallback_summary(desc):
    # _materialize_reader_projection 的契约就是「和 event_to_item 暴露的默认值完全一致」，
    # 两边各改一处就会让审计去审一段永远不会发布的文字。
    items = [source_item("条目", desc, "Source", "source")]
    base = {"ids": [0], "category": "world", "title": "中文标题",
            "dims": {name: 7 for name in dn.DIMS}, "score": 60, "tier": "T1"}
    audited, serialized = dict(base), dict(base)

    dn._materialize_reader_projection(audited, items)

    assert audited.get("summary") == dn.event_to_item(serialized, items, "more").get("summary")
