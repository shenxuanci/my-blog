import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import daily_news as dn


FINANCE_SOURCE = {"topic_filter": "finance"}
MODEL_ACCEPTS = {"topic_fit": True}


def test_ai_peer_review_experiment_is_not_finance_even_when_the_model_accepts_it():
    candidate = {
        "title": "How well does AI peer review work?",
        "desc": (
            "Claude and I planted 100 known errors into psychology papers and ran "
            "them through frontier models and two commercial AI review tools. The "
            "best system caught 71 errors, and the most useful tool was expensive."
        ),
    }

    assert not dn.deep_topic_matches(FINANCE_SOURCE, MODEL_ACCEPTS, candidate)


@pytest.mark.parametrize(
    ("title", "desc"),
    [
        (
            "Most policy is also industrial policy",
            "Government support for strategic industries reshapes manufacturing capacity.",
        ),
        (
            "Why did South Korean stocks just crash?",
            "Chip earnings and investor expectations drove the stock-market selloff.",
        ),
        (
            "Banning data centers would blow up the U.S. economy",
            "The investment shock would reduce productivity and economic growth.",
        ),
        (
            "Retail automation is changing entry-level work",
            "The analysis traces automation into employment, wages, and labor demand.",
        ),
    ],
)
def test_model_accepted_articles_with_explicit_finance_mechanisms_pass(title, desc):
    assert dn.deep_topic_matches(
        FINANCE_SOURCE,
        MODEL_ACCEPTS,
        {"title": title, "desc": desc},
    )


def test_finance_filter_still_requires_the_model_to_accept_the_article():
    candidate = {
        "title": "Why did South Korean stocks just crash?",
        "desc": "The article analyzes equity valuations and investor expectations.",
    }

    assert not dn.deep_topic_matches(
        FINANCE_SOURCE,
        {"topic_fit": False},
        candidate,
    )


@pytest.mark.parametrize("candidate", [None, {}, {"title": "", "desc": ""}])
def test_finance_filter_fails_closed_without_candidate_text(candidate):
    assert not dn.deep_topic_matches(FINANCE_SOURCE, MODEL_ACCEPTS, candidate)


def test_generic_commercial_language_is_not_deterministic_finance_evidence():
    candidate = {
        "title": "A commercial AI tool is expensive",
        "desc": "The policy review compares several commercial products and their accuracy.",
    }

    assert not dn.deep_topic_matches(FINANCE_SOURCE, MODEL_ACCEPTS, candidate)


def test_sources_without_a_filter_and_unknown_filters_keep_their_existing_behavior():
    empty_candidate = {"title": "", "desc": ""}

    assert dn.deep_topic_matches({}, {"topic_fit": False}, empty_candidate)
    assert dn.deep_topic_matches(
        {"topic_filter": "future-filter"},
        {"topic_fit": True},
        empty_candidate,
    )
    assert not dn.deep_topic_matches(
        {"topic_filter": "future-filter"},
        {"topic_fit": False},
        empty_candidate,
    )


def test_deep_channel_passes_candidate_text_into_the_finance_gate(
    monkeypatch,
    tmp_path,
):
    (tmp_path / "sources.yaml").write_text(
        """deep_sources:
  - id: finance-source
    name: Finance Source
    type: rss
    url: https://example.test/feed
    lang: en
    channel: society_finance
    topic_filter: finance
    enabled: true
""",
        encoding="utf-8",
    )
    candidate = {
        "title": "Why did South Korean stocks just crash?",
        "url": "https://example.test/korean-stocks",
        "desc": "Chip earnings and investor expectations drove the stock-market selloff.",
        "time": "2026-08-23T00:00:00+00:00",
        "content_words": 1100,
    }
    monkeypatch.setattr(dn, "ROOT", tmp_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(dn, "fetch_rss", lambda source, window, limit: ([candidate], False))

    class AcceptingModel:
        def json_call(self, system, user):
            return {
                "picks": [
                    {
                        "idx": 0,
                        "score": 8,
                        "title_zh": "韩国股市为何下跌",
                        "brief": "分析韩国股市下跌机制",
                        "why": "包含盈利与投资者预期分析",
                        "topic_fit": True,
                    }
                ]
            }

    deep = dn.deep_channel(
        AcceptingModel(),
        {"deep": {"enabled": True, "pick_threshold": 7, "pick_max": 3}},
        "2026-08-23",
    )

    assert [item["url"] for item in deep] == [candidate["url"]]
