import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import yaml
import pytest


ROOT = Path(__file__).resolve().parents[2]


def ledger():
    path = ROOT / "news-pipeline" / "issue_ledger.py"
    spec = importlib.util.spec_from_file_location("issue_ledger_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def attempt(run_id, run_attempt, *, publication="success", selection="pass",
            trajectory="pass", runtime="a", trajectory_ui="b",
            enrich="pass", objectivity_shadow="pass", source_metrics="pass"):
    return {
        "run_id": str(run_id),
        "run_attempt": int(run_attempt),
        "sha": "0123456789abcdef0123456789abcdef01234567",
        "publication": publication,
        "selection": {"status": selection, "reasons": []},
        "trajectory": {"status": trajectory, "reasons": []},
        "enrich": {"status": enrich, "reasons": []},
        "objectivity_shadow": {"status": objectivity_shadow, "reasons": []},
        "source_metrics": {"status": source_metrics, "reasons": []},
        "judge": {"pass": 1, "fail": 0, "needs_review": 0, "watch_ratio": 1.0},
        "fingerprints": {
            "runtime": runtime * 64 if runtime else "",
            "trajectory_ui": trajectory_ui * 64 if trajectory_ui else "",
        },
    }


def streaks(selection=0, trajectory=0, enrich=0, objectivity_shadow=0,
            source_metrics=0):
    return {
        "selection": selection,
        "trajectory": trajectory,
        "enrich": enrich,
        "objectivity_shadow": objectivity_shadow,
        "source_metrics": source_metrics,
    }


def state(date, attempts):
    return ledger().build_daily_state(date, attempts)


def test_publication_failure_is_permanent_across_same_day_reruns():
    il = ledger()
    failed = attempt(10, 1, publication="failure",
                     selection="needs_review", trajectory="needs_review")
    passed = attempt(10, 2)

    daily = il.build_daily_state("2026-07-22", [failed, passed])

    assert len(daily["attempts"]) == 2
    assert daily["aggregate"] == {
        "publication": "failure", "selection": "fail", "trajectory": "fail",
        "enrich": "fail", "objectivity_shadow": "fail", "source_metrics": "fail",
    }


def test_merging_same_run_attempt_is_idempotent_but_preserves_reruns():
    il = ledger()
    first = attempt(10, 1, selection="needs_review")
    replacement = attempt(10, 1, selection="pass")
    rerun = attempt(10, 2)

    merged = il.merge_attempts([first], replacement)
    merged = il.merge_attempts(merged, replacement)
    merged = il.merge_attempts(merged, rerun)

    assert [(row["run_id"], row["run_attempt"]) for row in merged] == [
        ("10", 1), ("10", 2)
    ]
    assert merged[0]["selection"]["status"] == "pass"


def test_distinct_workflow_run_ids_are_ordered_numerically():
    il = ledger()
    older = attempt(99, 1, selection="fail")
    newer = attempt(100, 1, selection="pass")

    daily = il.build_daily_state("2026-07-22", [newer, older])

    assert [row["run_id"] for row in daily["attempts"]] == ["99", "100"]
    assert daily["aggregate"]["selection"] == "pass"


def test_gate_streaks_follow_independent_fail_and_neutral_semantics():
    il = ledger()
    states = [
        state("2026-07-18", [attempt(1, 1)]),
        state("2026-07-19", [attempt(2, 1, selection="neutral", trajectory="pass")]),
        state("2026-07-20", [attempt(3, 1, selection="fail", trajectory="neutral")]),
        state("2026-07-21", [attempt(4, 1, selection="pass", trajectory="fail")]),
        state("2026-07-22", [attempt(5, 1, selection="needs_review",
                                      trajectory="needs_review")]),
    ]

    assert il.compute_streaks(states) == streaks(
        selection=1, trajectory=0, enrich=5, objectivity_shadow=5,
        source_metrics=5)


def test_cumulative_gates_bank_valid_days_while_consecutive_gates_reset():
    """A bad day must not erase banked enrich and source-metric observations."""
    il = ledger()
    states = [
        state("2026-07-20", [attempt(1, 1)]),
        state("2026-07-21", [attempt(2, 1)]),
        state("2026-07-22", [attempt(3, 1, enrich="fail", objectivity_shadow="fail",
                                     source_metrics="fail")]),
        state("2026-07-23", [attempt(4, 1)]),
    ]

    assert il.compute_streaks(states) == streaks(
        selection=4, trajectory=4, enrich=3, objectivity_shadow=1,
        source_metrics=3)


def test_manual_review_can_only_replace_needs_review_for_the_same_run():
    il = ledger()
    daily = state(
        "2026-07-25",
        [attempt(10, 1, selection="pass", trajectory="needs_review")],
    )

    reviewed = il.apply_manual_review(
        daily, gate="trajectory", status="pass",
        run_id="10", run_attempt=1,
    )

    assert reviewed["aggregate"]["trajectory"] == "pass"
    assert reviewed["manual_reviews"]["trajectory"]["run_id"] == "10"
    assert reviewed["manual_reviews"]["trajectory"]["run_attempt"] == 1

    preserved = il.build_daily_state(
        "2026-07-25",
        [attempt(10, 1, selection="pass", trajectory="needs_review")],
        manual_reviews=reviewed["manual_reviews"],
    )
    assert preserved["aggregate"]["trajectory"] == "pass"

    superseded = il.build_daily_state(
        "2026-07-25",
        [attempt(10, 2, selection="pass", trajectory="needs_review")],
        manual_reviews=reviewed["manual_reviews"],
    )
    assert superseded["aggregate"]["trajectory"] == "needs_review"


def test_manual_review_rejects_automatic_failures():
    il = ledger()
    daily = state(
        "2026-07-25",
        [attempt(10, 1, selection="pass", trajectory="fail")],
    )

    with pytest.raises(ValueError, match="needs_review"):
        il.apply_manual_review(
            daily, gate="trajectory", status="pass",
            run_id="10", run_attempt=1,
        )


def test_publication_failure_resets_every_consecutive_streak():
    il = ledger()
    states = [
        state("2026-07-20", [attempt(1, 1)]),
        state("2026-07-21", [attempt(2, 1)]),
        state("2026-07-22", [attempt(3, 1, publication="failure")]),
    ]

    assert il.compute_streaks(states) == streaks(
        selection=0, trajectory=0, enrich=2, objectivity_shadow=0,
        source_metrics=2)


def test_runtime_fingerprint_change_restarts_every_gate_clock():
    """A shared runtime change moves the sample, so no clock may carry over."""
    il = ledger()
    states = [
        state("2026-07-21", [attempt(1, 1, runtime="a", trajectory_ui="b")]),
        state("2026-07-22", [attempt(2, 1, runtime="c", trajectory_ui="b")]),
    ]

    assert il.compute_streaks(states) == streaks(
        selection=1, trajectory=1, enrich=1, objectivity_shadow=1,
        source_metrics=1)


def test_trajectory_ui_fingerprint_change_resets_only_trajectory():
    il = ledger()
    states = [
        state("2026-07-21", [attempt(1, 1, runtime="a", trajectory_ui="b")]),
        state("2026-07-22", [attempt(2, 1, runtime="a", trajectory_ui="c")]),
    ]

    assert il.compute_streaks(states) == streaks(
        selection=2, trajectory=1, enrich=2, objectivity_shadow=2,
        source_metrics=2)


def test_unrelated_fingerprint_fields_do_not_reset_streaks():
    il = ledger()
    prior = state("2026-07-21", [attempt(1, 1)])
    current = state("2026-07-22", [attempt(2, 1)])
    prior["fingerprints"]["articles"] = "x" * 64
    current["fingerprints"]["articles"] = "y" * 64

    assert il.compute_streaks([prior, current]) == streaks(
        selection=2, trajectory=2, enrich=2, objectivity_shadow=2,
        source_metrics=2)


def bot_comment(comment_id, daily_state, *, login="github-actions[bot]",
                user_type="Bot"):
    il = ledger()
    return {
        "id": comment_id,
        "user": {"login": login, "type": user_type},
        "body": il.render_comment(daily_state),
    }


def test_daily_comment_selection_ignores_untrusted_and_is_stable():
    il = ledger()
    daily = state("2026-07-22", [attempt(10, 1)])
    comments = [
        bot_comment(1, daily, login="attacker", user_type="User"),
        bot_comment(99, daily),
        bot_comment(42, daily),
        {"id": 2, "user": {"login": "github-actions[bot]", "type": "Bot"},
         "body": il.marker_for_date("2026-07-22") + "\n<!-- malformed -->"},
    ]

    selected = il.find_daily_comment(comments, "2026-07-22")

    assert selected["id"] == 2
    assert il.parse_machine_state(comments[0]) is None
    assert il.parse_machine_state(selected) is None
    assert il.parse_machine_state(comments[2])["date"] == "2026-07-22"


def test_rendered_comment_has_stable_marker_compact_state_and_human_summary():
    il = ledger()
    daily = state("2026-07-22", [attempt(10, 2)])
    daily["streaks"] = streaks(selection=7, trajectory=5, enrich=5,
                               objectivity_shadow=7, source_metrics=14)

    body = il.render_comment(daily, content_ratio=0.9, content_counts=(18, 20))

    assert body.count(il.marker_for_date("2026-07-22")) == 1
    assert "2026-07-22" in body
    assert "10 / attempt 2" in body
    assert "0123456" in body
    assert "Selection 7" in body
    assert "Source metrics 14" in body
    assert "18/20 passed" in body
    assert il.parse_machine_state({
        "user": {"login": "github-actions[bot]", "type": "Bot"}, "body": body,
    }) == daily


def test_rendered_comment_reports_observed_days_without_unlock_language():
    """ADR 0016 retired the unlock semantics; the comment is a dashboard.

    Reaching what used to be every target must not produce a final-confirmation
    verdict, an unmet-gate list, or an "N/target" ratio -- those would read as a
    countdown toward enabling `objectivity active`, which no longer exists.
    """
    il = ledger()
    daily = state("2026-07-22", [attempt(10, 2)])
    daily["streaks"] = streaks(selection=7, trajectory=5, enrich=5,
                               objectivity_shadow=7, source_metrics=14)

    at_former_targets = il.render_comment(
        daily, content_ratio=0.9, content_counts=(18, 20))
    short_source = il.render_comment(
        daily | {"streaks": {**daily["streaks"], "source_metrics": 13}},
        content_ratio=0.9, content_counts=(18, 20))
    weak_content = il.render_comment(
        daily, content_ratio=0.5, content_counts=(10, 20))
    unreviewed = il.render_comment(daily)

    for body in (at_former_targets, short_source, weak_content, unreviewed):
        assert "待人工最终确认" not in body
        assert "未达标门" not in body
        assert "Current progress" not in body
        assert "/7" not in body and "/14" not in body
        assert "Observed days: " in body

    assert "Source metrics 13" in short_source
    # The safety ratio is still reported, just no longer judged against a target.
    assert "10/20 passed" in weak_content
    assert "target" not in weak_content


def test_attempt_projection_does_not_copy_evidence_or_credentials():
    il = ledger()
    report = {
        "date": "2026-07-22",
        "selection": {
            "status": "pass",
            "reasons": ["ok TOKEN=top-secret ghp_ABC123secret"],
        },
        "trajectory": {
            "status": "needs_review",
            "reasons": ["judge at https://user:top-secret@example.test/v1 failed"],
            "watch_ratio": 0.75,
            "verdicts": [
                {"decision": "pass", "reason": "source body must not be copied"},
                {"decision": "needs_review", "reason": "full article text"},
            ],
        },
        "fingerprints": {"runtime": "a" * 64, "trajectory_ui": "b" * 64},
        "review_cases": [{"article": "private source body"}],
        "token": "top-secret",
    }

    projected = il.build_attempt(
        report=report, publication="success", publication_reason="",
        run_id="10", run_attempt=2,
        sha="0123456789abcdef0123456789abcdef01234567")
    body = json.dumps(projected, ensure_ascii=False)

    assert projected["judge"] == {
        "pass": 1, "fail": 0, "needs_review": 1, "watch_ratio": 0.75
    }
    assert "top-secret" not in body
    assert "ghp_ABC123secret" not in body
    assert "private source body" not in body
    assert "full article text" not in body


# Verbatim machine state from the three v1 comments already on Issue #15.
LIVE_V1_STATES = [
    '{"aggregate":{"publication":"success","selection":"fail","trajectory":"pass"},'
    '"attempts":[{"fingerprints":{"runtime":"f7871f8554ac4eab02e02635748953172723acc'
    'bfa4e8a263e56691abe84a56d","trajectory_ui":"43d5b4241deba846d6aab5dab9c54d5f8c3'
    '88917cf9f34e1ef9d6c167cce8286"},"judge":{"fail":0,"needs_review":0,"pass":10,"w'
    'atch_ratio":1.0},"publication":"success","run_attempt":1,"run_id":"29967591427"'
    ',"selection":{"reasons":["shadow outcome was not successful"],"status":"fail"},'
    '"sha":"07651ea232628fe8427b2165d190d35153598564","trajectory":{"reasons":[],"st'
    'atus":"pass"}}],"date":"2026-07-23","fingerprints":{"runtime":"f7871f8554ac4eab'
    '02e02635748953172723accbfa4e8a263e56691abe84a56d","trajectory_ui":"43d5b4241deb'
    'a846d6aab5dab9c54d5f8c388917cf9f34e1ef9d6c167cce8286"},"streaks":{"selection":0'
    ',"trajectory":1},"version":"issue-ledger-v1"}',
    '{"aggregate":{"publication":"success","selection":"pass","trajectory":"pass"},'
    '"attempts":[{"fingerprints":{"runtime":"9b2b7942291eb3f48aef7244c394737b38d4e5e'
    '021f5fa9f1d09dc293121202d","trajectory_ui":"2c9a0721e9241140a9b9c83cb14e70b6702'
    '5131e0f6065d4c5b8632cdb66fad3"},"judge":{"fail":0,"needs_review":0,"pass":17,"w'
    'atch_ratio":0.8235},"publication":"success","run_attempt":1,"run_id":"300545680'
    '36","selection":{"reasons":[],"status":"pass"},"sha":"36edb6983816216a0dfa63f1d'
    '3dc5139898c0346","trajectory":{"reasons":[],"status":"pass"}}],"date":"2026-07-'
    '24","fingerprints":{"runtime":"9b2b7942291eb3f48aef7244c394737b38d4e5e021f5fa9f'
    '1d09dc293121202d","trajectory_ui":"2c9a0721e9241140a9b9c83cb14e70b67025131e0f60'
    '65d4c5b8632cdb66fad3"},"streaks":{"selection":1,"trajectory":1},"version":"issu'
    'e-ledger-v1"}',
]


def live_v1_comment(comment_id, raw):
    il = ledger()
    date = json.loads(raw)["date"]
    return {
        "id": comment_id,
        "user": {"login": "github-actions[bot]", "type": "Bot"},
        "body": (f"{il.marker_for_date(date)}\n"
                 f"{il.STATE_PREFIX}{raw}{il.STATE_SUFFIX}\n"
                 f"## 日报验收 · {date}\n"),
    }


def test_live_v1_comments_migrate_without_inventing_gate_evidence():
    il = ledger()
    parsed = [il.parse_machine_state(live_v1_comment(index, raw))
              for index, raw in enumerate(LIVE_V1_STATES, start=1)]

    assert [row["date"] for row in parsed] == ["2026-07-23", "2026-07-24"]
    assert all(row["version"] == il.STATE_VERSION for row in parsed)
    # Selection and trajectory verdicts survive verbatim.
    assert parsed[0]["aggregate"]["selection"] == "fail"
    assert parsed[1]["aggregate"]["trajectory"] == "pass"
    # The three gates that did not exist yet must freeze, never credit a day.
    for row in parsed:
        for gate in ("enrich", "objectivity_shadow", "source_metrics"):
            assert row["aggregate"][gate] == "neutral"
    # 07-24 carries a different shared runtime fingerprint, so both clocks
    # restart there — reproducing the streaks the live 07-24 comment shows.
    assert il.compute_streaks(parsed) == streaks(
        selection=1, trajectory=1, enrich=0, objectivity_shadow=0,
        source_metrics=0)


def test_migration_is_idempotent_and_leaves_current_states_untouched():
    il = ledger()
    current = state("2026-07-26", [attempt(1, 1)])

    assert il.migrate_state(current) == current
    assert il.migrate_state(il.migrate_state(current)) == current


def test_enrich_baseline_uses_the_median_of_pre_window_output_days():
    il = ledger()
    health = {"records": [
        {"date": "2026-07-20", "enrichment_audited_events": 10, "removed_fields": 30},
        {"date": "2026-07-21", "enrichment_audited_events": 10, "removed_fields": 10},
        {"date": "2026-07-22", "enrichment_audited_events": 10, "removed_fields": 20},
        {"date": "2026-07-23", "enrichment_audited_events": 10, "removed_fields": 99},
    ]}

    assert il.enrich_baseline(health, "2026-07-23") == 2.0


def test_enrich_baseline_requires_three_valid_new_denominators():
    il = ledger()
    health = {"records": [
        {"date": "2026-07-19", "enrichment_audited_events": 10, "removed_fields": 10},
        {"date": "2026-07-20", "audited_events": 1000, "removed_fields": 1},
        {"date": "2026-07-21", "enrichment_audited_events": 10, "removed_fields": 20},
    ]}

    assert il.enrich_baseline(health, "2026-07-22") is None
    assert il._quality_ratio(health["records"][1]) is None


def test_enrich_fails_only_when_the_safety_ratio_exceeds_the_limit():
    il = ledger()
    records = [
        {"date": "2026-07-20", "enrichment_audited_events": 10, "removed_fields": 20},
        {"date": "2026-07-21", "enrichment_audited_events": 10, "removed_fields": 20},
        {"date": "2026-07-22", "enrichment_audited_events": 10, "removed_fields": 20},
    ]

    within = il.evaluate_enrich(
        {"records": records + [
            {"date": "2026-07-23", "enrichment_audited_events": 10,
             "removed_fields": 24}]},
        date="2026-07-23", window_start="2026-07-23")
    breached = il.evaluate_enrich(
        {"records": records + [
            {"date": "2026-07-23", "enrichment_audited_events": 10,
             "removed_fields": 25}]},
        date="2026-07-23", window_start="2026-07-23")
    absent = il.evaluate_enrich(
        {"records": records}, date="2026-07-23", window_start="2026-07-23")

    # 2.0 baseline * 1.2 = 2.4; a clean safety metric still awaits human review.
    assert within["status"] == "needs_review"
    assert within["metrics"] == {"ratio": 2.4, "baseline": 2.0, "limit": 2.4}
    assert breached["status"] == "fail"
    assert absent["status"] == "needs_review"


def test_enrich_replay_uses_selected_content_audits_not_cohesion_audits():
    il = ledger()
    health = {"records": [
        {"date": "2026-07-24", "audited_events": 42,
         "enrichment_audited_events": 36, "removed_fields": 69},
        {"date": "2026-07-25", "audited_events": 178,
         "enrichment_audited_events": 34, "removed_fields": 79},
        {"date": "2026-07-26", "audited_events": 24,
         "enrichment_audited_events": 28, "removed_fields": 87},
        {"date": "2026-07-28", "audited_events": 33,
         "enrichment_audited_events": 36, "removed_fields": 98},
    ]}

    result = il.evaluate_enrich(
        health, date="2026-07-28", window_start="2026-07-27")

    assert result["status"] == "needs_review"
    assert result["metrics"] == {
        "ratio": 2.7222, "baseline": 2.3235, "limit": 2.7882}


def test_objectivity_shadow_never_infers_a_pass_from_missing_metrics():
    il = ledger()
    complete = {
        "selected_before_audit": 36, "selected_after_audit": 35,
        "audited_candidate_count": 12, "demoted_from_selected": 1,
        "source_reference_concentration": [],
    }

    assert il.evaluate_objectivity_shadow(
        complete, shadow_outcome="success")["status"] == "pass"
    assert il.evaluate_objectivity_shadow(
        complete, shadow_outcome="failure")["status"] == "fail"
    assert il.evaluate_objectivity_shadow(
        None, shadow_outcome="success")["status"] == "needs_review"
    assert il.evaluate_objectivity_shadow(
        {k: v for k, v in complete.items() if k != "demoted_from_selected"},
        shadow_outcome="success")["status"] == "needs_review"
    assert il.evaluate_objectivity_shadow(
        {**complete, "selected_before_audit": "36"},
        shadow_outcome="success")["status"] == "needs_review"
    assert il.evaluate_objectivity_shadow(
        {**complete, "selected_after_audit": 37},
        shadow_outcome="success")["status"] == "needs_review"


def test_source_metrics_day_is_neutral_until_both_inputs_are_complete():
    il = ledger()
    health = {"days": {"2026-07-26": {
        "mit-tr": {"count": 2, "error": False, "scored_events": 1,
                   "selected_events": 1},
        "openai": {"count": 0, "error": True, "scored_events": 0,
                   "selected_events": 0},
    }}}
    shadow = {
        "high_risk_single_source_rate": 0.25,
        "independent_chain_distribution": {"1": 3},
        "source_reference_concentration": [],
    }

    complete = il.evaluate_source_metrics(health, shadow, date="2026-07-26")
    no_shadow = il.evaluate_source_metrics(health, None, date="2026-07-26")
    no_health = il.evaluate_source_metrics({}, shadow, date="2026-07-26")

    assert complete["status"] == "pass"
    assert complete["metrics"] == {"sources": 2, "errored": 1, "zero_update": 1}
    assert no_shadow["status"] == "neutral"
    assert no_health["status"] == "neutral"
    assert il.evaluate_source_metrics(
        {"days": {"2026-07-26": {"broken": {"count": "many", "error": False}}}},
        shadow, date="2026-07-26")["status"] == "neutral"
    assert il.evaluate_source_metrics(
        health, {**shadow, "high_risk_single_source_rate": float("nan")},
        date="2026-07-26")["status"] == "neutral"


def test_manual_review_records_enrich_sample_counts_only_for_enrich():
    il = ledger()
    daily = state("2026-07-26", [attempt(10, 1, enrich="needs_review")])
    daily["enrich_sample"] = {
        "ai": ["pick-1"], "finance": ["pick-2"],
        "society": ["pick-3"], "tech": ["pick-4"], "world": ["pick-5"],
    }

    reviewed = il.apply_manual_review(
        daily, gate="enrich", status="pass", run_id="10", run_attempt=1,
        samples_passed=4, samples_total=5)

    assert reviewed["manual_reviews"]["enrich"]["samples"] == {
        "passed": 4, "total": 5}
    assert il.enrich_content_ratio([reviewed]) == (0.8, 4, 5)

    trajectory = state("2026-07-26", [attempt(11, 1, trajectory="needs_review")])
    with pytest.raises(ValueError, match="enrich gate"):
        il.apply_manual_review(
            trajectory, gate="trajectory", status="pass", run_id="11",
            run_attempt=1, samples_passed=1, samples_total=1)
    with pytest.raises(ValueError, match="between 0"):
        il.apply_manual_review(
            daily, gate="enrich", status="pass", run_id="10", run_attempt=1,
            samples_passed=6, samples_total=5)


def test_enrich_manual_review_requires_complete_counts_for_a_verdict():
    il = ledger()
    daily = state("2026-07-26", [attempt(10, 1, enrich="needs_review")])
    daily["enrich_sample"] = {
        "ai": ["pick-1"],
        "finance": ["pick-2"],
    }

    with pytest.raises(ValueError, match="all sampled items"):
        il.apply_manual_review(
            daily, gate="enrich", status="pass", run_id="10", run_attempt=1,
            samples_passed=1, samples_total=1)
    with pytest.raises(ValueError, match="sample counts"):
        il.apply_manual_review(
            daily, gate="enrich", status="pass", run_id="10", run_attempt=1)

    reviewed = il.apply_manual_review(
        daily, gate="enrich", status="pass", run_id="10", run_attempt=1,
        samples_passed=1, samples_total=2)
    assert reviewed["manual_reviews"]["enrich"]["samples"] == {
        "passed": 1, "total": 2}


def test_neutral_enrich_review_rejects_sample_counts():
    il = ledger()
    daily = state("2026-07-26", [attempt(10, 1, enrich="needs_review")])
    daily["enrich_sample"] = {"ai": ["pick-1"]}

    with pytest.raises(ValueError, match="neutral.*sample counts"):
        il.apply_manual_review(
            daily, gate="enrich", status="neutral", run_id="10",
            run_attempt=1, samples_passed=0, samples_total=1)

    reviewed = il.apply_manual_review(
        daily, gate="enrich", status="neutral", run_id="10", run_attempt=1)
    assert "samples" not in reviewed["manual_reviews"]["enrich"]


def test_window_start_tracks_the_latest_shared_runtime_change():
    il = ledger()
    states = [
        state("2026-07-21", [attempt(1, 1, runtime="a")]),
        state("2026-07-22", [attempt(2, 1, runtime="a")]),
        state("2026-07-23", [attempt(3, 1, runtime="c")]),
        state("2026-07-24", [attempt(4, 1, runtime="c")]),
    ]

    assert il.window_start(states, "2026-07-24") == "2026-07-23"
    assert il.window_start(states, "2026-07-22") == "2026-07-21"


def test_gate_projection_keeps_metrics_numeric_and_drops_free_text():
    il = ledger()
    projected = il.build_attempt(
        report={"selection": {"status": "pass", "reasons": []},
                "trajectory": {"status": "pass", "reasons": []}},
        publication="success", publication_reason="", run_id="10",
        run_attempt=1, sha="0123456789abcdef0123456789abcdef01234567",
        enrich={"status": "needs_review", "reasons": ["ok"],
                "metrics": {"ratio": 1.5, "note": "secret article body"}},
        objectivity_shadow={"status": "pass", "reasons": []},
        source_metrics={"status": "pass", "reasons": []},
        enrich_sample={"ai": ["evt-1"], "world": ["evt-2", "secret body"]})
    body = json.dumps(projected, ensure_ascii=False)

    assert projected["enrich"]["metrics"] == {"ratio": 1.5}
    assert "secret article body" not in body
    assert projected["enrich"]["sample"]["ai"] == ["evt-1"]


def test_gate_projection_drops_nonfinite_numeric_metrics():
    il = ledger()
    projected = il.build_attempt(
        report={"selection": {"status": "pass", "reasons": []},
                "trajectory": {"status": "pass", "reasons": []}},
        publication="success", publication_reason="", run_id="10",
        run_attempt=1, sha="0123456789abcdef0123456789abcdef01234567",
        enrich={"status": "needs_review", "reasons": ["ok"],
                "metrics": {
                    "finite": 1.25,
                    "nan": float("nan"),
                    "positive_infinity": float("inf"),
                    "negative_infinity": float("-inf"),
                }},
        objectivity_shadow={"status": "pass", "reasons": []},
        source_metrics={"status": "pass", "reasons": []})

    assert projected["enrich"]["metrics"] == {"finite": 1.25}
    assert "NaN" not in json.dumps(projected)
    assert "Infinity" not in json.dumps(projected)


def test_publication_failure_marks_every_gate_failed_in_the_attempt():
    il = ledger()
    projected = il.build_attempt(
        report=None, publication="failure",
        publication_reason="generate job failure", run_id="10", run_attempt=1,
        sha="0123456789abcdef0123456789abcdef01234567",
        enrich={"status": "pass", "reasons": []},
        objectivity_shadow={"status": "pass", "reasons": []},
        source_metrics={"status": "pass", "reasons": []})

    for gate in il.GATES:
        assert projected[gate]["status"] == "fail"
        assert projected[gate]["reasons"] == ["generate job failure"]


class FakeClient:
    def __init__(self, *, issue_state="open", comments=None):
        self.issue_state = issue_state
        self.comments = list(comments or [])
        self.calls = []

    def get_issue(self, issue_number):
        self.calls.append(("get_issue", issue_number))
        return {"number": issue_number, "state": self.issue_state}

    def list_comments(self, issue_number):
        self.calls.append(("list_comments", issue_number))
        return list(self.comments)

    def create_comment(self, issue_number, body):
        self.calls.append(("create_comment", issue_number, body))
        return {"id": 500, "body": body}

    def update_comment(self, comment_id, body):
        self.calls.append(("update_comment", comment_id, body))
        return {"id": comment_id, "body": body}


def test_closed_issue_is_clean_no_op_before_comment_access():
    il = ledger()
    client = FakeClient(issue_state="closed")

    result = il.sync_issue(
        client, issue_number=15, date="2026-07-22", incoming=attempt(10, 1))

    assert result == {"status": "closed", "comment_id": None}
    assert client.calls == [("get_issue", 15)]


def test_shadow_status_is_capped_so_auto_runs_never_pay_for_shadow_again():
    """ADR 0016: shadow is capped, so `auto` must always resolve to accepted.

    The retired rule compared streaks against a 7/14-day target. Because a
    runtime-fingerprint change zeroes every clock, those targets were
    unreachable and `auto` would have run a second full pipeline every day
    forever. `shadow_mode:force` remains the way to sample.
    """
    il = ledger()
    comments = []
    for day in range(1, 15):
        daily = state(
            f"2026-07-{day:02d}",
            [attempt(day, 1, runtime="a", trajectory_ui="b")],
        )
        comments.append(bot_comment(day, daily))
    client = FakeClient(comments=comments)

    result = il.shadow_status(client, issue_number=15)

    assert result["needed"] is False
    assert result["accepted"] is True
    assert result["status"] == "accepted"


def test_shadow_status_never_touches_the_network_so_it_cannot_fail_open():
    """The verdict is a constant, so any API call is pure downside risk.

    The workflow treats a non-zero exit from `shadow-status` as "status
    unknown" and fail-opens into a paid shadow run. While this returned real
    streak data that trade-off was right; now that the answer is fixed, one
    rate-limited or 502'd request would buy a full extra pipeline for a verdict
    that was never in doubt. So it must not perform I/O at all.
    """
    il = ledger()

    class Exploding:
        def get_issue(self, issue_number):
            raise AssertionError("shadow_status must not call the API")

        def list_comments(self, issue_number):
            raise AssertionError("shadow_status must not call the API")

    for args, kwargs in (((), {}), ((Exploding(),), {"issue_number": 15})):
        result = il.shadow_status(*args, **kwargs)
        assert result["accepted"] is True
        assert result["needed"] is False
        assert result["streaks"] == {gate: 0 for gate in il.GATES}


def test_shadow_status_cli_survives_a_missing_token_without_forcing_a_run(tmp_path):
    """Constructing GitHubClient raises without a token; that must not fail open.

    Same blast radius as the test above, one layer out: if `main` built a client
    before answering shadow-status, a missing GITHUB_TOKEN or malformed
    GITHUB_REPOSITORY would exit non-zero and the workflow would pay for a
    shadow run because of an unset environment variable.
    """
    il = ledger()
    output = tmp_path / "gh_output"

    def unusable_factory(repository, token):
        raise AssertionError("no client may be built for shadow-status")

    result = il.main(
        ["shadow-status", "--issue", "15"],
        environ={"GITHUB_OUTPUT": str(output)},
        client_factory=unusable_factory)

    assert result["accepted"] is True
    written = output.read_text(encoding="utf-8")
    assert "accepted=true" in written
    assert "needed=false" in written


def test_shadow_status_reports_zeroed_streaks_rather_than_faked_targets():
    il = ledger()

    result = il.shadow_status()

    assert result["accepted"] is True
    assert result["needed"] is False
    # The retired implementation fabricated target-sized streaks for a closed
    # issue. Report nothing banked instead of inventing observations.
    assert result["streaks"]["objectivity_shadow"] == 0
    assert result["streaks"]["source_metrics"] == 0


def test_accepted_shadow_outcome_freezes_shadow_and_source_gates():
    """The freeze reason must not claim an acceptance that never happened.

    ADR 0016 retired the acceptance rather than completing it, so the ledger's
    own reason strings have to say "capped", not "already complete" -- the whole
    point of the change was to stop surfaces implying the gates were passed.
    """
    il = ledger()

    assert il.evaluate_objectivity_shadow(
        None, shadow_outcome="accepted") == {
            "status": "neutral",
            "reasons": ["shadow capped; sample on demand with force"],
        }
    assert il.evaluate_source_metrics(
        None, None, date="2026-07-28",
        shadow_outcome="accepted") == {
            "status": "neutral",
            "reasons": ["shadow capped; sample on demand with force"],
        }


def test_sync_updates_same_daily_comment_idempotently():
    il = ledger()
    existing = state("2026-07-22", [attempt(10, 1, selection="needs_review")])
    client = FakeClient(comments=[bot_comment(88, existing)])

    result = il.sync_issue(
        client, issue_number=15, date="2026-07-22", incoming=attempt(10, 1))

    write_calls = [call for call in client.calls
                   if call[0] in {"create_comment", "update_comment"}]
    assert result == {"status": "updated", "comment_id": 88}
    assert len(write_calls) == 1
    assert write_calls[0][0:2] == ("update_comment", 88)
    parsed = il.parse_machine_state({
        "user": {"login": "github-actions[bot]", "type": "Bot"},
        "body": write_calls[0][2],
    })
    assert len(parsed["attempts"]) == 1
    assert parsed["attempts"][0]["selection"]["status"] == "pass"


def test_sync_preserves_manual_review_for_an_unchanged_workflow_run():
    il = ledger()
    existing = state(
        "2026-07-25",
        [attempt(10, 1, selection="pass", trajectory="needs_review")],
    )
    existing = il.apply_manual_review(
        existing, gate="trajectory", status="pass",
        run_id="10", run_attempt=1,
    )
    client = FakeClient(comments=[bot_comment(88, existing)])

    il.sync_issue(
        client, issue_number=15, date="2026-07-25",
        incoming=attempt(10, 1, selection="pass", trajectory="needs_review"),
    )

    updated = next(call[2] for call in client.calls if call[0] == "update_comment")
    parsed = il.parse_machine_state({
        "user": {"login": "github-actions[bot]", "type": "Bot"},
        "body": updated,
    })
    assert parsed["aggregate"]["trajectory"] == "pass"
    assert parsed["manual_reviews"]["trajectory"]["run_id"] == "10"


def test_manual_review_issue_updates_the_trusted_comment_and_streaks():
    il = ledger()
    prior = state("2026-07-24", [attempt(9, 1)])
    current = state(
        "2026-07-25",
        [attempt(10, 1, selection="pass", trajectory="needs_review")],
    )
    client = FakeClient(comments=[
        bot_comment(80, prior),
        bot_comment(88, current),
    ])

    result = il.manual_review_issue(
        client, issue_number=15, date="2026-07-25",
        gate="trajectory", status="pass",
        run_id="10", run_attempt=1,
    )

    assert result == {"status": "updated", "comment_id": 88}
    updated = next(call[2] for call in client.calls if call[0] == "update_comment")
    parsed = il.parse_machine_state({
        "user": {"login": "github-actions[bot]", "type": "Bot"},
        "body": updated,
    })
    assert parsed["aggregate"]["trajectory"] == "pass"
    assert parsed["streaks"] == streaks(
        selection=2, trajectory=2, enrich=2, objectivity_shadow=2,
        source_metrics=2)


def test_sync_cli_scores_all_five_gates_against_the_repo_health_files(tmp_path):
    """Exercise the exact production CLI path against committed health data."""
    il = ledger()
    data_dir = ROOT / "source" / "news" / "data"
    source_health = json.loads(
        (data_dir / "source_health.json").read_text(encoding="utf-8"))
    target_date = max(source_health["days"])

    report = tmp_path / "rollout-report.json"
    report.write_text(json.dumps({
        "selection": {"status": "pass", "reasons": []},
        "trajectory": {"status": "pass", "reasons": []},
        "fingerprints": {"runtime": "a" * 64, "trajectory_ui": "b" * 64},
        "enrich_sample": {"ai": ["top-1"], "world": ["more-2"]},
    }), encoding="utf-8")
    shadow = tmp_path / "shadow-summary.json"
    shadow.write_text(json.dumps({
        "selected_before_audit": 36, "selected_after_audit": 35,
        "audited_candidate_count": 12, "demoted_from_selected": 1,
        "high_risk_single_source_rate": 0.25,
        "independent_chain_distribution": {"1": 3},
        "source_reference_concentration": [],
    }), encoding="utf-8")

    client = FakeClient()
    il.main([
        "sync", "--issue", "15", "--date", target_date,
        "--publication", "success", "--report", str(report),
        "--shadow-summary", str(shadow), "--shadow-outcome", "success",
        "--quality-health", str(data_dir / "quality-health.json"),
        "--source-health", str(data_dir / "source_health.json"),
        "--run-id", "999", "--run-attempt", "1", "--sha", "a" * 40,
    ], environ={"GITHUB_REPOSITORY": "owner/repo", "GITHUB_TOKEN": "t"},
        client_factory=lambda _repo, _token: client)

    body = next(call[2] for call in client.calls if call[0] == "create_comment")
    parsed = il.parse_machine_state({
        "user": {"login": "github-actions[bot]", "type": "Bot"}, "body": body})
    aggregate = parsed["aggregate"]

    assert aggregate["selection"] == "pass"
    assert aggregate["objectivity_shadow"] == "pass"
    assert aggregate["source_metrics"] == "pass"
    # Legacy committed health data has not passed through the next generate
    # migration yet, so it must remain unknown rather than reuse audited_events.
    # After migration the metric may be measurable, but it still cannot pass
    # automatically because the three per-item checks are human-only.
    assert aggregate["enrich"] in {"needs_review", "fail"}
    metrics = parsed["attempts"][0]["enrich"].get("metrics")
    if metrics:
        assert metrics["baseline"] > 0
    else:
        assert aggregate["enrich"] == "needs_review"
    assert parsed["enrich_sample"] == {"ai": ["top-1"], "world": ["more-2"]}
    assert "待人工最终确认" not in body


@pytest.mark.parametrize("record", [
    {"enrichment_audited_events": "bad", "removed_fields": 1},
    {"enrichment_audited_events": 2, "removed_fields": "bad"},
    {"enrichment_audited_events": True, "removed_fields": 1},
    {"enrichment_audited_events": -1, "removed_fields": 1},
    {"enrichment_audited_events": 2, "removed_fields": -1},
])
def test_enrich_quality_ratio_treats_invalid_persisted_fields_as_unknown(record):
    il = ledger()

    assert il._quality_ratio(record) is None


@pytest.mark.parametrize("command", ["sync", "manual-review", "heartbeat"])
def test_cli_rejects_dates_that_could_forge_a_trusted_ledger_comment(command):
    """The date lands inside the HTML comment marker of a bot-authored entry.

    A crafted value closes that comment early and injects arbitrary content —
    including a second state block — into the record the acceptance gates
    read back, so every entry point must reject non-dates.
    """
    il = ledger()
    extra = {
        "sync": ["--publication", "success", "--run-id", "1",
                 "--run-attempt", "1", "--sha", "a" * 40],
        "manual-review": ["--gate", "selection", "--status", "pass",
                          "--run-id", "1", "--run-attempt", "1"],
        "heartbeat": [],
    }[command]

    for hostile in (
        "2026-01-01 --><!-- daily-news-rollout-state:{} -->",
        "2026-01-01\nfoo=bar",
        "2026-13-01",
        "2026-02-30",
        "2026-1-1",
        "",
    ):
        with pytest.raises(SystemExit):
            il.parse_cli_args([command, "--date", hostile, *extra])

    assert il.parse_cli_args(
        [command, "--date", "2026-07-26", *extra]).date == "2026-07-26"


def test_heartbeat_is_a_no_op_when_the_date_already_has_a_ledger_entry():
    il = ledger()
    existing = state("2026-07-26", [attempt(10, 1)])
    client = FakeClient(comments=[bot_comment(88, existing)])

    result = il.heartbeat_issue(client, issue_number=15, date="2026-07-26")

    assert result["status"] == "present"
    assert result["comment_id"] == 88
    assert not [call for call in client.calls
                if call[0] in {"create_comment", "update_comment"}]


def test_heartbeat_gap_freezes_every_clock_instead_of_resetting_it():
    il = ledger()
    prior = [
        state("2026-07-24", [attempt(1, 1)]),
        state("2026-07-25", [attempt(2, 1)]),
    ]
    client = FakeClient(comments=[
        bot_comment(80, prior[0]), bot_comment(81, prior[1])])

    result = il.heartbeat_issue(client, issue_number=15, date="2026-07-26")

    assert result["status"] == "gap_recorded"
    body = next(call[2] for call in client.calls if call[0] == "create_comment")
    parsed = il.parse_machine_state({
        "user": {"login": "github-actions[bot]", "type": "Bot"}, "body": body})
    assert parsed["aggregate"]["publication"] == "neutral"
    assert all(parsed["aggregate"][gate] == "neutral" for gate in il.GATES)
    # The two banked days survive the gap untouched.
    assert parsed["streaks"] == streaks(
        selection=2, trajectory=2, enrich=2, objectivity_shadow=2,
        source_metrics=2)
    assert "所有门冻结" in body


def test_heartbeat_gap_then_a_real_day_keeps_counting_from_the_banked_total():
    il = ledger()
    states = [
        state("2026-07-24", [attempt(1, 1)]),
        il.build_gap_state("2026-07-25"),
        state("2026-07-26", [attempt(2, 1)]),
    ]

    assert il.compute_streaks(states) == streaks(
        selection=2, trajectory=2, enrich=2, objectivity_shadow=2,
        source_metrics=2)


def test_heartbeat_workflow_is_read_only_and_shares_the_ledger_concurrency():
    doc = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "rollout-heartbeat.yml").read_text(
            encoding="utf-8"))
    job = doc["jobs"]["heartbeat"]

    assert doc["permissions"] == {"contents": "read", "issues": "write"}
    assert doc["concurrency"] == {
        "group": "daily-news-rollout-ledger", "cancel-in-progress": False}
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["env"]["TZ"] == "Asia/Shanghai"
    assert job["steps"][0]["with"]["ref"] == "main"
    # A gap detector must never call the LLM or hold write access to contents.
    text = (ROOT / ".github" / "workflows" / "rollout-heartbeat.yml").read_text(
        encoding="utf-8")
    assert "LLM_API_KEY" not in text
    assert "contents: write" not in text
    assert "heartbeat" in step_named(job, "Record heartbeat")["run"]
    assert "steps.issue.outputs.open == 'true'" in step_named(
        job, "Record heartbeat")["if"]


def test_daily_ledger_sync_receives_every_gate_input():
    sync = step_named(workflow()["jobs"]["rollout-review"],
                      "Update rollout issue ledger")

    for flag in ("--report", "--shadow-summary", "--shadow-outcome",
                 "--quality-health", "--source-health"):
        assert flag in sync["run"]
    assert sync["env"]["SHADOW_OUTCOME"] == (
        "${{ steps.prepare.outputs.shadow_outcome }}")
    assert sync["env"]["QUALITY_HEALTH"].endswith(
        "source/news/data/quality-health.json")
    assert sync["env"]["SOURCE_HEALTH"].endswith(
        "source/news/data/source_health.json")
    assert "${{ inputs." not in sync["run"]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_rest_boundary_uses_bearer_token_and_expected_issue_endpoints():
    il = ledger()
    requests = []
    responses = iter([
        {"number": 15, "state": "open"},
        [],
        {"id": 12},
        {"id": 12},
    ])

    def opener(request, timeout):
        requests.append((request, timeout))
        return FakeResponse(next(responses))

    client = il.GitHubClient("owner/repo", "test-token", opener=opener)
    assert client.get_issue(15)["state"] == "open"
    assert client.list_comments(15) == []
    client.create_comment(15, "body")
    client.update_comment(12, "updated")

    assert [request.get_method() for request, _ in requests] == [
        "GET", "GET", "POST", "PATCH"
    ]
    assert [request.full_url for request, _ in requests] == [
        "https://api.github.com/repos/owner/repo/issues/15",
        "https://api.github.com/repos/owner/repo/issues/15/comments?per_page=100&page=1",
        "https://api.github.com/repos/owner/repo/issues/15/comments",
        "https://api.github.com/repos/owner/repo/issues/comments/12",
    ]
    assert all(request.get_header("Authorization") == "Bearer test-token"
               for request, _ in requests)


def test_check_open_cli_writes_closed_output_without_comment_calls(tmp_path):
    il = ledger()
    output = tmp_path / "github-output"
    client = FakeClient(issue_state="closed")

    result = il.main(
        ["check-open", "--issue", "15"],
        environ={
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_TOKEN": "test-token",
            "GITHUB_OUTPUT": str(output),
        },
        client_factory=lambda _repo, _token: client,
    )

    assert result == {"status": "closed", "open": False}
    assert output.read_text(encoding="utf-8") == "open=false\n"
    assert client.calls == [("get_issue", 15)]


def workflow():
    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / "daily-news.yml").read_text(
            encoding="utf-8"))


def manual_review_workflow():
    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / "rollout-manual-review.yml").read_text(
            encoding="utf-8"))


def step_named(job, name):
    return next(step for step in job["steps"] if step.get("name") == name)


def deploy_check_job():
    return workflow()["jobs"]["deploy-check"]


def deploy_check_script():
    return step_named(
        deploy_check_job(), "Wait for the briefing to go live")["run"]


def deploy_hook_metadata_parser():
    script = deploy_check_script()
    marker = 'python3 - "$hook_response_file" <<\'PY\'\n'
    start = script.index(marker) + len(marker)
    return script[start:script.index("\nPY\n", start)]


def run_deploy_hook_metadata_parser(tmp_path, payload):
    response = tmp_path / "hook-response.json"
    response.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-c", deploy_hook_metadata_parser(), str(response)],
        text=True,
        capture_output=True,
    )


def bash_executable():
    bash = shutil.which("bash")
    if bash is not None:
        return bash
    git = shutil.which("git")
    if git is None:
        return None
    candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe"
    return str(candidate) if candidate.is_file() else None


def run_prepare_rollout_review(tmp_path, shadow_text=None):
    prepare = step_named(workflow()["jobs"]["rollout-review"],
                         "Prepare rollout review")
    script = prepare["run"]
    marker = "python - <<'PY'\n"
    assert script.startswith(marker) and script.endswith("\nPY\n")
    code = script[len(marker):-4]

    review_dir = tmp_path / "daily-news-rollout-review"
    evidence = review_dir / "rollout-evidence" / "rollout-evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    shadow = review_dir / "shadow-status" / "daily-news-shadow-status.json"
    configured_shadow = Path(
        prepare["env"]["SHADOW_STATUS_PATH"].replace(
            "${{ env.REVIEW_DIR }}", str(review_dir)))
    if shadow_text is not None:
        shadow.parent.mkdir(parents=True)
        shadow.write_text(shadow_text, encoding="utf-8")
    output = tmp_path / "github-output"
    env = {
        **os.environ,
        "GENERATE_RESULT": "success",
        "EVIDENCE_PATH": str(evidence),
        "SHADOW_STATUS_PATH": str(configured_shadow),
        "GITHUB_OUTPUT": str(output),
    }
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
    return dict(
        line.split("=", 1)
        for line in output.read_text(encoding="utf-8").splitlines())


def test_workflow_permissions_are_minimal_and_publication_stage_is_unchanged():
    jobs = workflow()["jobs"]

    assert jobs["generate"]["permissions"] == {"contents": "write"}
    assert jobs["shadow"]["permissions"] == {"contents": "read"}
    assert jobs["rollout-review"]["permissions"] == {
        "contents": "read", "issues": "write"
    }
    commit = step_named(jobs["generate"], "Commit and push")["run"]
    assert "git add source/news/data" in commit
    assert "git add ." not in commit
    assert "git add -A" not in commit


def test_publish_date_extraction_cannot_abort_after_push_under_pipefail():
    commit = step_named(workflow()["jobs"]["generate"], "Commit and push")["run"]

    assert "published_date=" in commit
    assert "source/news/data/manifest.js" in commit
    assert not re.search(
        r"^\s*grep\b[^\n]*(?:\n\s*[^#\n][^\n]*)*?\|\s*head\b",
        commit,
        re.MULTILINE,
    )
    assert commit.index("published_date=") < commit.index("git push origin HEAD:main")


def test_deploy_check_probes_the_canonical_host_without_redirects_or_cache_bust():
    deploy = deploy_check_job()
    script = deploy_check_script()

    assert deploy["env"]["SITE_MANIFEST"] == (
        "https://www.aoiblog.top/news/data/manifest.js")
    assert (
        'curl -fsS --max-time 20 --max-filesize "$MAX_RESPONSE_BYTES" '
        '"$SITE_MANIFEST"' in script
    )
    assert "?cb=" not in script
    assert "--max-redirs" not in script
    assert not re.search(r"(?:^|\s)-L(?:\s|$)", script)


def test_deploy_check_live_probe_cannot_false_fail_from_grep_closing_the_pipe():
    script = deploy_check_script()

    assert "local manifest_body" in script
    assert (
        'grep -Fq "window.NEWS_MANIFEST = [\\\"${PUBLISHED_DATE}\\\"" '
        '<<< "$manifest_body"' in script
    )
    assert not re.search(r"curl [^\n]+\n\s*\| grep -q", script)


def test_deploy_check_matches_the_manifest_contract_not_a_bare_date():
    script = deploy_check_script()

    assert (
        'grep -Fq "window.NEWS_MANIFEST = [\\\"${PUBLISHED_DATE}\\\""'
        in script
    )


def test_deploy_check_records_bounded_deploy_hook_metadata_without_logging_secret():
    script = deploy_check_script()

    assert "hook_response_file" in script
    assert 'job["id"]' in script
    assert 'job["state"]' in script
    assert 'job["createdAt"]' in script
    log_lines = [
        line for line in script.splitlines()
        if re.search(r"\b(?:echo|printf)\b", line)
    ]
    assert all(
        "$DEPLOY_HOOK" not in line and "${DEPLOY_HOOK}" not in line
        for line in log_lines
    )


def test_deploy_hook_metadata_rejects_boolean_timestamp(tmp_path):
    result = run_deploy_hook_metadata_parser(tmp_path, {
        "job": {"id": "job_123", "state": "PENDING", "createdAt": True},
    })

    assert result.returncode != 0


def test_deploy_hook_metadata_rejects_oversized_job_id(tmp_path):
    result = run_deploy_hook_metadata_parser(tmp_path, {
        "job": {
            "id": "a" * 129,
            "state": "PENDING",
            "createdAt": 1785661733449,
        },
    })

    assert result.returncode != 0


def test_deploy_hook_metadata_accepts_the_documented_shape(tmp_path):
    result = run_deploy_hook_metadata_parser(tmp_path, {
        "job": {
            "id": "job_123",
            "state": "PENDING",
            "createdAt": 1785661733449,
        },
    })

    assert result.returncode == 0
    assert result.stdout.strip() == (
        "id=job_123 state=PENDING createdAt=1785661733449")


def test_deploy_check_failure_diagnostic_is_bounded_and_failure_tolerant():
    script = deploy_check_script()

    for expected in (
            "diagnostic_headers", "diagnostic_body", "curl_exit",
            "http_code=%{http_code}", "url_effective=%{url_effective}",
            "num_redirects=%{num_redirects}", "Location", "X-Vercel-Cache",
            "Age", "ETag", "Last-Modified", "head -c 200"):
        assert expected in script
    assert "trap " in script
    assert script.rstrip().endswith("exit 1")


def test_deploy_check_bounds_every_downloaded_response():
    script = deploy_check_script()

    assert "MAX_RESPONSE_BYTES=65536" in script
    assert script.count('--max-filesize "$MAX_RESPONSE_BYTES"') == 3


def test_deploy_check_missing_inputs_are_safe_under_nounset():
    script = deploy_check_script()

    assert '[ -z "${PUBLISHED_DATE:-}" ]' in script
    assert '[ -z "${DEPLOY_HOOK:-}" ]' in script


def test_deploy_check_shell_syntax_is_valid_when_bash_is_available():
    bash = bash_executable()
    if bash is None:
        pytest.skip("bash is unavailable")

    subprocess.run(
        [bash, "--noprofile", "--norc", "-n"],
        input=deploy_check_script(),
        text=True,
        check=True,
    )


def test_workflow_artifacts_are_temp_scoped_short_lived_and_sha_pinned():
    jobs = workflow()["jobs"]
    generate_step = step_named(jobs["generate"], "Generate daily briefing")
    assert generate_step["env"]["ROLLOUT_EVIDENCE_PATH"].startswith(
        "${{ runner.temp }}/")
    evidence_upload = step_named(jobs["generate"], "Upload rollout evidence")
    shadow_upload = step_named(jobs["shadow"], "Upload shadow status")
    summary_upload = step_named(jobs["shadow"], "Upload shadow summary")
    expected_upload = (
        "actions/upload-artifact@"
        "ea165f8d65b6e75b540449e92b4886f43607fa02")
    for upload in (evidence_upload, shadow_upload, summary_upload):
        assert upload["uses"] == expected_upload
        assert 1 <= upload["with"]["retention-days"] <= 7
        assert "source/news/data" not in upload["with"]["path"]
    assert jobs["shadow"]["env"]["SHADOW_SUMMARY_PATH"].startswith("/tmp/")
    assert summary_upload["if"] == "${{ always() }}"

    downloads = [step for step in jobs["rollout-review"]["steps"]
                 if str(step.get("uses", "")).startswith("actions/download-artifact@")]
    assert len(downloads) == 3
    assert all(step["uses"] == (
        "actions/download-artifact@"
        "d3f86a106a0bac45b974a628896c90dbdf5c8093") for step in downloads)

    review_prepare = step_named(jobs["rollout-review"], "Prepare rollout review")
    assert review_prepare["env"]["SHADOW_STATUS_PATH"] == (
        "${{ env.REVIEW_DIR }}/shadow-status/daily-news-shadow-status.json")


def test_prepare_review_reads_real_downloaded_shadow_status_and_fails_closed(
        tmp_path):
    success = run_prepare_rollout_review(
        tmp_path / "success", '{"outcome":"success"}\n')
    assert success["publication"] == "success"
    assert success["judge_ready"] == "true"
    assert success["shadow_outcome"] == "success"

    for name, payload in (
            ("missing", None),
            ("invalid", "not-json\n"),
            ("failed", '{"outcome":"failure"}\n')):
        result = run_prepare_rollout_review(tmp_path / name, payload)
        assert result["shadow_outcome"] == "failure"


def test_shadow_failure_is_observed_without_failing_the_job():
    jobs = workflow()["jobs"]
    shadow = jobs["shadow"]
    run_step = step_named(shadow, "Run objectivity shadow")
    status_step = step_named(shadow, "Record shadow status")

    assert run_step["id"] == "shadow_run"
    conditional_non_blocking = (
        "${{ github.event_name == 'schedule' || inputs.mode == 'publish' }}")
    assert run_step["continue-on-error"] == conditional_non_blocking
    assert shadow["continue-on-error"] == conditional_non_blocking
    assert status_step["if"] == "${{ always() }}"
    assert status_step["env"]["SHADOW_OUTCOME"] == (
        "${{ steps.shadow_run.outcome }}")
    assert shadow["env"]["SHADOW_STATUS_PATH"].startswith("/tmp/")
    assert "SHADOW_STATUS_PATH" not in jobs["generate"]["env"]


def test_review_checks_open_issue_before_dependencies_or_judge():
    review = workflow()["jobs"]["rollout-review"]
    names = [step.get("name") for step in review["steps"]]
    issue_index = names.index("Check rollout issue")
    install_index = names.index("Install review dependencies")
    judge_index = names.index("Evaluate rollout")

    assert review["needs"] == ["generate", "shadow-policy", "shadow"]
    assert review["if"] == (
        "${{ always() && github.ref == 'refs/heads/main' && "
        "(github.event_name == 'schedule' || inputs.mode == 'publish') }}")
    assert issue_index < install_index < judge_index
    assert step_named(review, "Check rollout issue")["id"] == "issue"
    assert "steps.issue.outputs.open == 'true'" in step_named(
        review, "Install review dependencies")["if"]
    judge_if = step_named(review, "Evaluate rollout")["if"]
    assert "steps.issue.outputs.open == 'true'" in judge_if
    assert "steps.prepare.outputs.judge_ready == 'true'" in judge_if


def test_generate_failure_or_missing_evidence_skips_judge_but_syncs_ledger():
    review = workflow()["jobs"]["rollout-review"]
    prepare = step_named(review, "Prepare rollout review")
    judge = step_named(review, "Evaluate rollout")
    sync = step_named(review, "Update rollout issue ledger")

    assert prepare["env"]["GENERATE_RESULT"] == "${{ needs.generate.result }}"
    assert "judge_ready" in prepare["run"]
    assert "steps.prepare.outputs.judge_ready == 'true'" in judge["if"]
    assert "steps.issue.outputs.open == 'true'" in sync["if"]
    assert "--publication" in sync["run"]
    assert "--report" in sync["run"]


def test_review_infrastructure_failures_warn_and_still_reach_ledger():
    review = workflow()["jobs"]["rollout-review"]
    issue = step_named(review, "Check rollout issue")
    setup = next(step for step in review["steps"]
                 if str(step.get("uses", "")).startswith("actions/setup-python@"))
    install = step_named(review, "Install review dependencies")
    sync = step_named(review, "Update rollout issue ledger")
    warning = step_named(review, "Warn on review failure")

    assert issue["continue-on-error"] is True
    assert setup["continue-on-error"] is True
    assert install["continue-on-error"] is True
    assert "always()" in sync["if"]
    assert "always()" in warning["if"]
    for step_id in ("issue", "setup", "install", "judge", "ledger"):
        assert f"steps.{step_id}.outcome == 'failure'" in warning["if"]


def test_needs_review_report_emits_a_workflow_warning():
    judge = step_named(
        workflow()["jobs"]["rollout-review"], "Evaluate rollout")

    assert "needs_review" in judge["run"]
    assert "::warning::" in judge["run"]


def test_rollout_review_uploads_the_complete_report_artifact():
    review = workflow()["jobs"]["rollout-review"]
    upload = step_named(review, "Upload rollout report")

    assert upload["if"] == "${{ always() && steps.issue.outputs.open == 'true' }}"
    assert upload["with"]["name"] == "rollout-report"
    assert upload["with"]["path"] == "${{ env.REVIEW_DIR }}/rollout-report.json"


def test_manual_review_workflow_uses_bot_identity_and_bounded_inputs():
    workflow_doc = manual_review_workflow()
    job = workflow_doc["jobs"]["review"]
    inputs = workflow_doc[True]["workflow_dispatch"]["inputs"]
    apply_step = step_named(job, "Apply manual review")

    assert workflow_doc["permissions"] == {"contents": "read", "issues": "write"}
    assert workflow_doc["concurrency"] == {
        "group": "daily-news-rollout-ledger",
        "cancel-in-progress": False,
    }
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert inputs["gate"]["options"] == [
        "selection", "trajectory", "enrich", "objectivity_shadow",
        "source_metrics"]
    assert inputs["status"]["options"] == ["pass", "fail", "neutral"]
    assert apply_step["env"]["GITHUB_TOKEN"] == "${{ github.token }}"
    assert apply_step["env"]["REVIEW_RUN_ID"] == "${{ inputs.run_id }}"
    assert apply_step["env"]["REVIEW_RUN_ATTEMPT"] == "${{ inputs.run_attempt }}"
    assert "reason" not in inputs
    assert "REVIEW_REASON" not in apply_step["env"]
    assert "${{ inputs." not in apply_step["run"]
    assert '--run-id "$REVIEW_RUN_ID"' in apply_step["run"]
    assert '--run-attempt "$REVIEW_RUN_ATTEMPT"' in apply_step["run"]
    assert "--reason" not in apply_step["run"]
    checkout = job["steps"][0]
    assert checkout["with"]["ref"] == "main"


def test_daily_and_manual_ledger_writes_share_one_concurrency_group():
    daily_review = workflow()["jobs"]["rollout-review"]

    assert daily_review["if"] == (
        "${{ always() && github.ref == 'refs/heads/main' && "
        "(github.event_name == 'schedule' || inputs.mode == 'publish') }}")
    assert daily_review["concurrency"] == {
        "group": "daily-news-rollout-ledger",
        "cancel-in-progress": False,
    }
    assert daily_review["steps"][0]["with"]["ref"] == "main"
