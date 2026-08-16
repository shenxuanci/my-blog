import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml


PIPELINE_DIR = Path(__file__).resolve().parents[1]
ROOT = PIPELINE_DIR.parent
spec = importlib.util.spec_from_file_location("daily_news_shadow_test", PIPELINE_DIR / "daily_news.py")
dn = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dn
spec.loader.exec_module(dn)


def _load_eval_module():
    path = PIPELINE_DIR / "objectivity_eval.py"
    assert path.exists(), "objectivity evaluation harness is missing"
    module_spec = importlib.util.spec_from_file_location("objectivity_eval_test", path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def test_objectivity_acceptance_workflow_is_manual_read_only_and_publishes_report():
    workflow_path = ROOT / ".github" / "workflows" / "objectivity-acceptance.yml"
    assert workflow_path.exists(), "manual objectivity acceptance workflow is missing"

    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"evaluate"}

    evaluate = workflow["jobs"]["evaluate"]
    assert evaluate["if"] == "github.ref == 'refs/heads/main'"
    assert evaluate["permissions"] == {"contents": "read"}

    steps = evaluate["steps"]
    acceptance = next(
        step for step in steps
        if step.get("name") == "Evaluate fixed objectivity corpus"
    )
    assert acceptance["env"]["STEPFUN_API_KEY"] == "${{ secrets.STEPFUN_API_KEY }}"
    assert acceptance["env"]["DEEPSEEK_API_KEY"] == "${{ secrets.DEEPSEEK_API_KEY }}"
    assert "LLM_API_KEY" not in acceptance["env"]
    assert steps[0]["with"]["ref"] == "main"
    run_scripts = "\n".join(step.get("run", "") for step in steps)
    assert "python news-pipeline/objectivity_eval.py" in run_scripts
    assert "git show HEAD^:news-pipeline/daily_news.py" in run_scripts
    assert "--pipeline-path" in run_scripts
    assert "--cost-baseline" in run_scripts
    assert "git commit" not in run_scripts
    assert "git push" not in run_scripts

    upload = next(
        step for step in steps
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert upload["if"] == "${{ always() }}"
    assert upload["with"]["path"] == "${{ runner.temp }}/objectivity-acceptance.json"


def test_rollout_workflows_pin_runner_python_and_runtime_epoch():
    workflow_names = (
        "daily-news.yml",
        "objectivity-acceptance.yml",
        "rollout-heartbeat.yml",
        "rollout-manual-review.yml",
    )
    for name in workflow_names:
        workflow = yaml.load(
            (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )
        assert all(
            job["runs-on"] == "ubuntu-24.04"
            for job in workflow["jobs"].values()
        ), name
        setup_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if step.get("uses", "").startswith("actions/setup-python@")
        ]
        assert setup_steps, name
        assert all(
            step["with"]["python-version"] == "3.12.13"
            for step in setup_steps
        ), name

    daily = yaml.load(
        (ROOT / ".github" / "workflows" / "daily-news.yml").read_text(
            encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    assert daily["env"]["RUNTIME_ENVIRONMENT_EPOCH"] == "1"


def test_objectivity_judge_prompt_separates_evidence_category_from_candidate_failures():
    evaluator = _load_eval_module()

    for category in evaluator.CATEGORIES:
        assert f"- {category}:" in evaluator.JUDGE_SYSTEM
    assert "exactly one evidence-risk label" in evaluator.JUDGE_SYSTEM
    assert "even when the candidate safely removes" in evaluator.JUDGE_SYSTEM
    assert "redlines describe only violations that remain in the final candidate" in evaluator.JUDGE_SYSTEM
    assert "omitted risky claim is not an attribution failure" in evaluator.JUDGE_SYSTEM


def test_mode_defaults_to_interim_and_shadow_overrides_active():
    default_args = dn.parse_cli_args([])
    default = dn.resolve_run_policy({}, default_args)
    active = dn.resolve_run_policy(
        {"objectivity": {"mode": "active"}}, dn.parse_cli_args([]))
    shadow = dn.resolve_run_policy(
        {"objectivity": {"mode": "active"}},
        dn.parse_cli_args(["--objectivity-shadow"]),
    )

    assert default == {
        "mode": "interim",
        "full_objectivity": False,
        "writes_public_data": True,
    }
    assert active == {
        "mode": "active",
        "full_objectivity": True,
        "writes_public_data": True,
    }
    assert shadow == {
        "mode": "shadow",
        "full_objectivity": True,
        "writes_public_data": False,
    }


def test_date_argument_accepts_only_real_iso_calendar_dates():
    assert dn.parse_cli_args(["--date", "2026-07-22"]).date == "2026-07-22"

    for value in ("../../outside", "2026-02-30", "2026-7-2"):
        with pytest.raises(SystemExit):
            dn.parse_cli_args(["--date", value])


def test_invalid_configured_mode_is_rejected():
    with pytest.raises(ValueError, match="objectivity.mode"):
        dn.resolve_run_policy(
            {"objectivity": {"mode": "surprise"}}, dn.parse_cli_args([]))


def test_shadow_snapshots_existing_data_dir_while_public_uses_configured_path(tmp_path):
    public_dir = tmp_path / "public-data"
    (public_dir / "weekly").mkdir(parents=True)
    marker = public_dir / "daily.js"
    marker.write_text("public", encoding="utf-8")
    (public_dir / "feedback.json").write_text('{"keep":true}', encoding="utf-8")
    (public_dir / "profile.json").write_text('{"reader":"existing"}', encoding="utf-8")
    (public_dir / "events.json").write_text('{"events":[]}', encoding="utf-8")
    (public_dir / "weekly" / "2026-W28.js").write_text("weekly", encoding="utf-8")
    environ = {"DATA_DIR": str(public_dir)}

    shadow_dir, shadow_owner = dn.prepare_run_data_dir(
        {"writes_public_data": False}, environ)
    public_result, public_owner = dn.prepare_run_data_dir(
        {"writes_public_data": True}, environ)
    try:
        assert shadow_owner is not None
        assert shadow_dir != public_dir
        assert (shadow_dir / "daily.js").read_text(encoding="utf-8") == "public"
        assert (shadow_dir / "feedback.json").exists()
        assert (shadow_dir / "profile.json").exists()
        assert (shadow_dir / "events.json").exists()
        assert (shadow_dir / "weekly" / "2026-W28.js").exists()
        (shadow_dir / "daily.js").write_text("shadow", encoding="utf-8")
        assert public_result == public_dir
        assert public_owner is None
    finally:
        shadow_owner.cleanup()

    assert marker.read_text(encoding="utf-8") == "public"


@pytest.mark.parametrize("exit_kind", ["return", "exception", "validation_failure"])
def test_shadow_data_dir_lifecycle_never_mutates_source_on_any_exit(
        tmp_path, exit_kind):
    public_dir = tmp_path / "public-data"
    public_dir.mkdir()
    marker = public_dir / "marker.txt"
    marker.write_text("public", encoding="utf-8")
    environ = {"DATA_DIR": str(public_dir)}
    captured = []

    def run():
        with dn.managed_run_data_dir(
                {"writes_public_data": False}, environ) as shadow_dir:
            captured.append(shadow_dir)
            assert environ["DATA_DIR"] == str(shadow_dir)
            assert (shadow_dir / "marker.txt").read_text(encoding="utf-8") == "public"
            (shadow_dir / "marker.txt").write_text("shadow", encoding="utf-8")
            (shadow_dir / "generated.tmp").write_text("temporary", encoding="utf-8")
            if exit_kind == "return":
                return
            if exit_kind == "validation_failure":
                raise ValueError("daily payload validation failed")
            raise RuntimeError("pipeline failed")

    if exit_kind == "return":
        run()
    else:
        expected = ValueError if exit_kind == "validation_failure" else RuntimeError
        with pytest.raises(expected):
            run()

    assert environ["DATA_DIR"] == str(public_dir)
    assert marker.read_text(encoding="utf-8") == "public"
    assert captured and not captured[0].exists()


def test_shadow_data_dir_lifecycle_supports_empty_snapshot(tmp_path):
    public_dir = tmp_path / "empty-public-data"
    public_dir.mkdir()
    environ = {"DATA_DIR": str(public_dir)}

    with dn.managed_run_data_dir(
            {"writes_public_data": False}, environ) as shadow_dir:
        assert list(shadow_dir.iterdir()) == []
        (shadow_dir / "generated.js").write_text("shadow", encoding="utf-8")

    assert list(public_dir.iterdir()) == []


def test_objectivity_stage_dispatches_interim_support_only_and_full_audit():
    items = [
        {"title": "Source one", "desc": "Fact one", "source": "Wire A",
         "source_type": "fact", "credibility": 9, "url": "https://a.example"},
        {"title": "Source two", "desc": "Fact two", "source": "Wire B",
         "source_type": "fact", "credibility": 9, "url": "https://b.example"},
    ]

    class InterimStub:
        def __init__(self):
            self.systems = []

        def json_call(self, system, _user):
            self.systems.append(system)
            return {"fields": {"why": True}, "supported_claim_indexes": [0]}

    interim_event = {
        "ids": [0], "title": "Edited", "summary": "Summary", "why": "Why",
        "claims": [{"text": "Fact", "kind": "fact", "sources": ["Wire A"]}],
    }
    interim_secondary = {"ids": [1], "title": "Secondary", "summary": "Other"}
    interim_quality = dn.new_quality_stats()
    interim_stub = InterimStub()
    dn.run_objectivity_stage(
        {"full_objectivity": False}, interim_stub, [interim_event],
        [interim_secondary], items, interim_quality)

    assert interim_stub.systems == [dn.SUPPORT_AUDIT_SYSTEM]
    assert interim_quality["objectivity_audited"] == 0
    assert interim_secondary == {"ids": [1], "title": "Secondary", "summary": "Other"}

    class FullStub:
        def __init__(self):
            self.systems = []

        def json_call(self, system, _user):
            self.systems.append(system)
            return {"fields": {"title": True, "summary": True}, "claims": []}

    picked = [{"ids": [0], "title": "Edited", "summary": "Summary"}]
    secondary = [{"ids": [1], "title": "Secondary", "summary": "Other"}]
    full_quality = dn.new_quality_stats()
    full_stub = FullStub()
    dn.run_objectivity_stage(
        {"full_objectivity": True}, full_stub, picked, secondary, items, full_quality)

    assert full_stub.systems == [dn.OBJECTIVITY_AUDIT_SYSTEM, dn.OBJECTIVITY_AUDIT_SYSTEM]
    assert full_quality["objectivity_audited"] == 2


def test_public_serialization_strips_rollout_fields_in_interim_and_keeps_active(
        tmp_path, monkeypatch):
    item = {
        "title": "Source title", "desc": "Source description",
        "source": "Wire A", "source_id": "wire-a", "source_type": "fact",
        "tier": "T1", "credibility": 9, "url": "https://a.example/item",
        "time": "2026-07-18T00:00:00+00:00", "evidence_basis": "fulltext",
        "source_family": "wire-a", "provenance": "original",
    }
    event = {
        "ids": [0], "category": "ai", "title": "Edited", "summary": "Summary",
        "status": "已确认", "score": 90, "tier": "T1", "tags": [],
        "evidence": {
            "basis": "fulltext", "publisher_count": 1,
            "independent_chain_count": 1, "degraded": False,
        },
    }
    quality = dn.new_quality_stats()
    quality["objectivity_audited"] = 1
    quality["article_fetch_attempts"] = 1

    interim_dir = tmp_path / "interim"
    monkeypatch.setenv("DATA_DIR", str(interim_dir))
    interim = dn.write_output(
        "2026-07-18", "brief", [event], [], [item],
        {"objectivity": {"mode": "interim"}}, quality=quality)

    assert "evidence" not in interim["items"][0]
    assert "evidence_basis" not in interim["items"][0]["sources"][0]
    assert "objectivity_audited" not in interim["quality"]
    assert "article_fetch_attempts" not in interim["quality"]

    active_dir = tmp_path / "active"
    monkeypatch.setenv("DATA_DIR", str(active_dir))
    active = dn.write_output(
        "2026-07-18", "brief", [event], [], [item],
        {"objectivity": {"mode": "active"}}, quality=quality)

    assert active["items"][0]["evidence"]["basis"] == "fulltext"
    assert active["items"][0]["sources"][0]["evidence_basis"] == "fulltext"
    assert active["quality"]["objectivity_audited"] == 1
    assert active["quality"]["article_fetch_attempts"] == 1


def test_config_declares_interim_default():
    config = yaml.safe_load((PIPELINE_DIR / "config.yaml").read_text(encoding="utf-8"))
    assert config["objectivity"]["mode"] == "interim"
    assert config["cost_guard"] == {
        "same_day_reconcile_max_calls": 20,
        "same_day_min_shared_keys": 4,
        "cross_source_novelty_batch_size": 20,
        "cross_source_novelty_max_calls": 8,
        # 分层材料等级把日成本从 $0.055 抬到约 $0.079，告警随之上移（ADR 0020）。
        # 预算口径 ¥1/天 ≈ $0.14，告警仍在其下。
        "generate_warn_usd": 0.12,
        "shadow_warn_usd": 0.09,
    }
    assert config["detail"]["fulltext_top_n"] == 8


def test_shadow_summary_has_stable_shape_and_excludes_content_and_secrets():
    selected_before = [
        {
            "ids": [0],
            "risk_flags": {"allegation_legal": True},
            "evidence": {
                "basis": "fulltext",
                "publisher_count": 1,
                "independent_chain_count": 1,
                "degraded": False,
            },
            "detail": "ARTICLE_SENTINEL",
        },
        {
            "ids": [1, 2],
            "risk_flags": {},
            "evidence": {
                "basis": "mixed",
                "publisher_count": 2,
                "independent_chain_count": 0,
                "degraded": True,
            },
        },
    ]
    selected_after = [selected_before[1]]
    items = [
        {"source": "Wire A", "evidence_text": "ARTICLE_SENTINEL"},
        {"source": "Outlet B"},
        {"source": "Outlet C", "api_key": "SECRET_SENTINEL"},
    ]
    quality = {
        "article_fetch_attempts": 3,
        "article_fetch_successes": 2,
        "article_fetch_retries": 1,
        "objectivity_audited": 2,
        "objectivity_repaired": 1,
        "objectivity_degraded": 1,
        "high_risk_demoted": 1,
    }

    usage = {
        "llm_calls": 20,
        "llm_input_tokens": 1000,
        "llm_cached_input_tokens": 100,
        "llm_output_tokens": 200,
        "llm_cost_usd": 0.08,
        "llm_cost_known": True,
    }
    summary = dn.build_shadow_summary(
        selected_before, selected_after, items, quality,
        runtime_seconds=12.3456, usage=usage)

    assert set(summary) == {
        "mode", "runtime_seconds", "selected_before_audit",
        "selected_after_audit", "audited_candidate_count",
        "demoted_from_selected", "high_risk_selected_before_audit",
        "single_source_selected_before_audit", "high_risk_single_source_count",
        "high_risk_single_source_rate", "evidence_basis", "fetch",
        "objectivity", "detail_quality", "independent_chain_distribution",
        "source_reference_concentration", "llm_usage",
    }
    assert summary["runtime_seconds"] == 12.346
    assert summary["selected_before_audit"] == 2
    assert summary["selected_after_audit"] == 1
    assert summary["audited_candidate_count"] == 2
    assert summary["demoted_from_selected"] == 1
    assert summary["high_risk_single_source_count"] == 1
    assert summary["high_risk_single_source_rate"] == 1.0
    assert summary["evidence_basis"] == {"fulltext": 1, "mixed": 1, "snippet": 0}
    assert summary["fetch"] == {"attempts": 3, "successes": 2, "retries": 1}
    assert summary["objectivity"] == {
        "repaired": 1, "degraded": 1,
    }
    assert summary["detail_quality"] == {
        "evidence_rich": 0, "evidence_limited": 0,
        "evidence_snippet": 0, "final_median_chars": 0,
        "rich_target_met": 0, "rich_target_rate": 0.0,
    }
    assert summary["independent_chain_distribution"] == {"0": 1, "1": 1}
    assert summary["llm_usage"] == usage
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "ARTICLE_SENTINEL" not in encoded
    assert "SECRET_SENTINEL" not in encoded


def test_github_summary_appends_compact_markdown(tmp_path):
    target = tmp_path / "step-summary.md"
    summary = {
        "mode": "shadow",
        "runtime_seconds": 2.5,
        "selected_before_audit": 5,
        "selected_after_audit": 4,
        "audited_candidate_count": 7,
        "demoted_from_selected": 1,
        "high_risk_selected_before_audit": 1,
        "single_source_selected_before_audit": 1,
        "high_risk_single_source_count": 1,
        "high_risk_single_source_rate": 1.0,
        "evidence_basis": {"fulltext": 2, "mixed": 1, "snippet": 1},
        "fetch": {"attempts": 5, "successes": 4, "retries": 1},
        "objectivity": {"repaired": 1, "degraded": 0},
        "independent_chain_distribution": {"0": 1, "1": 3},
        "source_reference_concentration": [
            {"source": "Wire A", "reference_count": 2, "reference_share": 0.5}
        ],
    }

    assert dn.append_github_shadow_summary(summary, {"GITHUB_STEP_SUMMARY": str(target)})
    text = target.read_text(encoding="utf-8")
    assert "Objectivity shadow" in text
    assert "2.500s" in text
    assert "selected before/after audit: 5/4" in text
    assert "audited candidates/demoted from selected: 7/1" in text
    assert "source reference concentration" in text
    assert "fulltext/mixed/snippet: 2/1/1" in text
    assert "high-risk single-source: 1 (100.0%)" in text
    assert "ARTICLE_SENTINEL" not in text


def test_selection_summary_appends_threshold_and_composition_without_content(tmp_path):
    target = tmp_path / "step-summary.md"
    summary = {
        "threshold": 74,
        "threshold_source": "dynamic_history",
        "history_days": 7,
        "quality_floor": 66,
        "picked_count": 24,
        "category_counts": {"ai": 8, "tech": 4, "finance": 4, "society": 4, "world": 4},
        "qualified_supply": {"ai": 20, "tech": 6, "finance": 5, "society": 4, "world": 7},
        "reserved_count": 15,
        "below_threshold_reserved": 3,
        "over_threshold_secondary": 2,
        "detail": "ARTICLE_SENTINEL",
    }

    assert dn.append_github_selection_summary(
        summary, {"GITHUB_STEP_SUMMARY": str(target)})
    text = target.read_text(encoding="utf-8")
    assert "News selection" in text
    assert "threshold: 74 (dynamic_history; 7 history days)" in text
    assert "quality floor: 66" in text
    assert "reserved/below-threshold reserved: 15/3" in text
    assert "over-threshold secondary: 2" in text
    assert "ARTICLE_SENTINEL" not in text


def test_article_fetch_reports_transient_retry_count():
    calls = []

    class Response:
        status_code = 200
        headers = {"Content-Type": "text/html"}

        def iter_content(self, chunk_size):
            yield b"<html>ok</html>"

        def close(self):
            return None

    def request_get(*_args, **_kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise TimeoutError("transient")
        return Response()

    result = dn.fetch_article_evidence(
        {"url": "https://news.example/item", "title": "t", "desc": "d"},
        request_get=request_get,
        extractor=lambda _html: "safe evidence " * 30,
        resolver=lambda *_args, **_kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
        sleep=lambda _seconds: None,
    )

    assert result["evidence_basis"] == "fulltext"
    assert result["attempts"] == 2
    assert result["retries"] == 1


def test_fixture_corpus_has_required_count_categories_and_schema():
    evaluator = _load_eval_module()
    fixtures = evaluator.load_checked_in_corpus()
    errors = evaluator.validate_fixture_schema(fixtures)

    assert errors == []
    assert len(fixtures) == 45
    assert {fixture["category"] for fixture in fixtures} == {
        "waic_framing",
        "legal_procedure",
        "armed_conflict",
        "company_claim",
        "magnitude_without_baseline",
        "motive_causal_inference",
        "sensitive_single_source",
        "shared_evidence",
        "forbidden_fabricated_balance",
    }
    assert {
        category: sum(fixture["category"] == category for fixture in fixtures)
        for category in evaluator.CATEGORIES
    } == {category: 5 for category in evaluator.CATEGORIES}


def test_fixture_schema_rejects_unknown_keys_and_long_excerpts():
    evaluator = _load_eval_module()
    fixture = {
        "id": "bad-01",
        "category": "company_claim",
        "source": "Synthetic Wire",
        "excerpt": "x" * 281,
        "expected": {
            "labels": ["company_claim"],
            "accepted_labels": ["company_claim"],
            "attribution_required": True,
            "redlines": [],
        },
        "unexpected": True,
    }

    errors = evaluator.validate_fixture_schema([fixture])

    assert any("unexpected" in error for error in errors)
    assert any("excerpt" in error for error in errors)


def test_fixture_schema_enforces_size_categories_vocab_and_consistency():
    evaluator = _load_eval_module()
    fixtures = evaluator.load_checked_in_corpus()

    undersized_errors = evaluator.validate_fixture_schema(fixtures[:8])
    assert any("exactly 45" in error for error in undersized_errors)
    assert any("all 9 categories" in error for error in undersized_errors)

    oversized_errors = evaluator.validate_fixture_schema(fixtures + [fixtures[0]])
    assert any("exactly 45" in error for error in oversized_errors)

    imbalanced = json.loads(json.dumps(fixtures))
    imbalanced[0]["category"] = "legal_procedure"
    imbalanced[0]["expected"]["labels"] = ["legal_procedure"]
    imbalanced_errors = evaluator.validate_fixture_schema(imbalanced)
    assert any("exactly 5 fixtures" in error for error in imbalanced_errors)

    bad = json.loads(json.dumps(fixtures))
    bad[0]["expected"]["labels"] = ["legal_procedure"]
    bad[1]["expected"]["redlines"] = ["not_in_the_allowed_vocabulary"]
    bad[2]["id"] = bad[3]["id"]
    errors = evaluator.validate_fixture_schema(bad)
    assert any("must exactly match category" in error for error in errors)
    assert any("redline" in error and "allowed" in error for error in errors)
    assert any("duplicated" in error for error in errors)


def test_fixture_corpus_is_fixed_to_checked_in_path_and_hash():
    evaluator = _load_eval_module()
    raw = evaluator.CORPUS_PATH.read_bytes()
    lf_raw = raw.replace(b"\r\n", b"\n")
    crlf_raw = lf_raw.replace(b"\n", b"\r\n")
    canonical_digest = "10a2966f887e975b43f673bf81e0f1c9ee3f5040d389cb243ce2fc04b56c58b2"

    assert evaluator.CORPUS_PATH == PIPELINE_DIR / "fixtures" / "objectivity_evidence.json"
    assert evaluator.CORPUS_SHA256 == canonical_digest
    assert evaluator.canonical_corpus_sha256(lf_raw) == canonical_digest
    assert evaluator.canonical_corpus_sha256(crlf_raw) == canonical_digest
    assert evaluator.load_checked_in_corpus() == json.loads(raw.decode("utf-8"))
    with pytest.raises(SystemExit):
        evaluator.main(["--fixtures", str(PIPELINE_DIR / "fixtures" / "tiny.json")])


def test_three_run_worst_case_aggregation_and_thresholds():
    evaluator = _load_eval_module()
    fixtures = evaluator.load_checked_in_corpus()
    required_indexes = [
        index for index, fixture in enumerate(fixtures)
        if fixture["expected"]["attribution_required"]
    ]
    wrong_index = required_indexes[0]
    calls = []

    def stub_runner(_fixtures, run_number):
        calls.append(run_number)
        wrong = {wrong_index} if run_number == 2 else set()
        return [
            {
                "id": fixture["id"],
                "labels": [fixture["category"]],
                "attribution_ok": index not in wrong,
                "redlines": [],
            }
            for index, fixture in enumerate(_fixtures)
        ]

    report = evaluator.evaluate_three_runs(fixtures, stub_runner)

    assert calls == [1, 2, 3]
    assert report["worst"] == {
        "redline_count": 0,
        "label_agreement": 1.0,
        "attribution_accuracy": round(
            (len(required_indexes) - 1) / len(required_indexes), 4),
        "structure_validity": 1.0,
    }
    assert report["accepted"] is True

    def run(redline=0, label=1.0, attribution=1.0, structure=1.0):
        return {"redline_count": redline, "label_agreement": label,
                "attribution_accuracy": attribution,
                "structure_validity": structure}

    failed = evaluator.acceptance_result([
        run(redline=1), run(attribution=0.949), run(structure=0.999)])
    assert failed["accepted"] is False
    assert failed["worst"] == {
        "redline_count": 1,
        "label_agreement": 1.0,
        "attribution_accuracy": 0.949,
        "structure_validity": 0.999,
    }

    # Each gate must be able to fail the run on its own.
    for single in (run(redline=1), run(label=0.899),
                   run(attribution=0.949), run(structure=0.999)):
        assert evaluator.acceptance_result(
            [run(), single, run()])["accepted"] is False
    # Label agreement is a real gate, but it is not required to be perfect:
    # genuinely ambiguous cases may still divide a well-calibrated judge.
    assert evaluator.acceptance_result(
        [run(), run(label=0.9), run()])["accepted"] is True


def test_score_run_reports_aggregate_failure_breakdown():
    evaluator = _load_eval_module()
    fixtures = [
        {
            "id": "case-1",
            "category": "company_claim",
            "source": "Synthetic Wire",
            "excerpt": "A company reported a benchmark result.",
            "expected": {
                "labels": ["company_claim"],
                "accepted_labels": ["company_claim"],
                "attribution_required": True,
                "redlines": ["internal_benchmark_as_independent"],
            },
        },
        {
            "id": "case-2",
            "category": "legal_procedure",
            "source": "Synthetic Wire",
            "excerpt": "Prosecutors filed an allegation.",
            "expected": {
                "labels": ["legal_procedure"],
                "accepted_labels": ["legal_procedure"],
                "attribution_required": True,
                "redlines": ["allegation_as_conviction"],
            },
        },
        {
            "id": "case-3",
            "category": "waic_framing",
            "source": "Synthetic Wire",
            "excerpt": "An organizer described a product as leading.",
            "expected": {
                "labels": ["waic_framing"],
                "accepted_labels": ["waic_framing"],
                "attribution_required": True,
                "redlines": ["marketing_as_fact"],
            },
        },
    ]
    rows = [
        {
            "id": "case-1",
            "labels": ["company_claim"],
            "attribution_ok": True,
            "redlines": [],
        },
        {
            "id": "case-2",
            "labels": ["company_claim"],
            "attribution_ok": False,
            "redlines": ["allegation_as_conviction"],
        },
        {"judge_batch_invalid": True},
    ]

    score = evaluator.score_run(fixtures, rows)

    assert score["diagnostics"] == {
        "invalid_case_count": 1,
        "label_mismatch_count": 1,
        "label_scored_count": 2,
        "reported_redline_count": 1,
        "attribution_correct_count": 1,
        # case-3 is structurally invalid, so it is charged to the structure
        # gate only and never enters the attribution or label denominators.
        "attribution_required_count": 2,
    }
    assert score["redline_count"] == 1
    assert score["label_agreement"] == 0.5
    # The aggregate counters above cannot say *which* case to go fix; these can.
    assert score["case_findings"] == [
        {"id": "case-2", "issue": "attribution_missed"},
        {"id": "case-2", "issue": "label_mismatch",
         "accepted_labels": ["legal_procedure"],
         "actual_labels": ["company_claim"]},
        {"id": "case-2", "issue": "residual_redline",
         "redlines": ["allegation_as_conviction"]},
        {"id": "case-3", "issue": "invalid_structure"},
    ]


def test_redline_count_ignores_taxonomy_disagreement():
    """A judge that mislabels a clean candidate is a calibration problem,
    not a safety violation, and must not be reported as a redline."""
    evaluator = _load_eval_module()
    fixtures = [{
        "id": "case-1",
        "category": "waic_framing",
        "source": "Synthetic Wire",
        "excerpt": "An organizer called a demo industry-leading.",
        "expected": {
            "labels": ["waic_framing"],
            "accepted_labels": ["waic_framing"],
            "attribution_required": True,
            "redlines": ["marketing_as_fact"],
        },
    }]
    rows = [{"id": "case-1", "labels": ["company_claim"],
             "attribution_ok": True, "redlines": []}]

    score = evaluator.score_run(fixtures, rows)

    assert score["redline_count"] == 0
    assert score["label_agreement"] == 0.0
    assert score["attribution_accuracy"] == 1.0


def test_accepted_label_set_admits_every_defensible_reading():
    evaluator = _load_eval_module()
    fixtures = [{
        "id": "waic-05",
        "category": "waic_framing",
        "source": "Synthetic Wire",
        "excerpt": "A lab handout called its robot fully autonomous.",
        "expected": {
            "labels": ["waic_framing"],
            "accepted_labels": ["waic_framing", "company_claim"],
            "attribution_required": True,
            "redlines": ["autonomy_overclaim"],
        },
    }]

    def agreement(label):
        rows = [{"id": "waic-05", "labels": [label],
                 "attribution_ok": True, "redlines": []}]
        return evaluator.score_run(fixtures, rows)["label_agreement"]

    assert agreement("waic_framing") == 1.0
    assert agreement("company_claim") == 1.0
    assert agreement("legal_procedure") == 0.0


def test_case_findings_stay_empty_when_every_case_passes():
    evaluator = _load_eval_module()
    fixtures = [{
        "id": "case-1",
        "category": "company_claim",
        "source": "Synthetic Wire",
        "excerpt": "A company reported a benchmark result.",
        "expected": {
            "labels": ["company_claim"],
            "accepted_labels": ["company_claim"],
            "attribution_required": True,
            "redlines": ["internal_benchmark_as_independent"],
        },
    }]
    rows = [{"id": "case-1", "labels": ["company_claim"],
             "attribution_ok": True, "redlines": []}]

    score = evaluator.score_run(fixtures, rows)

    assert score["case_findings"] == []
    assert score["redline_count"] == 0
    assert score["structure_validity"] == 1.0


def test_case_findings_account_for_extra_rows_that_dock_structure_validity():
    """A findings list that under-reports its own invalid_case_count misleads."""
    evaluator = _load_eval_module()
    fixtures = [{
        "id": "case-1",
        "category": "company_claim",
        "source": "Synthetic Wire",
        "excerpt": "A company reported a benchmark result.",
        "expected": {
            "labels": ["company_claim"],
            "accepted_labels": ["company_claim"],
            "attribution_required": True,
            "redlines": ["internal_benchmark_as_independent"],
        },
    }]
    rows = [
        {"id": "case-1", "labels": ["company_claim"],
         "attribution_ok": True, "redlines": []},
        {"id": "ghost-1", "labels": ["waic_framing"],
         "attribution_ok": True, "redlines": []},
    ]

    score = evaluator.score_run(fixtures, rows)

    assert score["diagnostics"]["invalid_case_count"] == 1
    assert score["case_findings"] == [
        {"issue": "extra_judge_rows", "count": 1}]


def test_case_findings_reach_the_uploaded_acceptance_report():
    """The findings are only useful if they survive into the artifact."""
    evaluator = _load_eval_module()
    run = {
        "redline_count": 1, "attribution_accuracy": 1.0,
        "structure_validity": 1.0,
        "diagnostics": {},
        "case_findings": [
            {"id": "single-04", "issue": "label_mismatch",
             "expected_labels": ["sensitive_single_source"],
             "actual_labels": ["legal_procedure"]}],
    }

    report = evaluator.acceptance_result([run, run, run])
    serialized = json.loads(json.dumps(report, ensure_ascii=False))

    assert serialized["accepted"] is False
    assert [row["case_findings"] for row in serialized["runs"]] == [
        run["case_findings"]] * 3


def test_structure_validity_rejects_extra_model_rows():
    evaluator = _load_eval_module()
    fixtures = [{
        "id": "case-1",
        "category": "company_claim",
        "source": "Synthetic Wire",
        "excerpt": "A company said a lab metric improved.",
        "expected": {
            "labels": ["company_claim"],
            "accepted_labels": ["company_claim"],
            "attribution_required": True,
            "redlines": [],
        },
    }]
    rows = [{
        "id": "case-1",
        "labels": ["company_claim"],
        "attribution_ok": True,
        "redlines": [],
    }, {
        "id": "invented-case",
        "labels": ["company_claim"],
        "attribution_ok": True,
        "redlines": [],
    }]

    assert evaluator.score_run(fixtures, rows)["structure_validity"] == 0.0


def test_production_harness_uses_real_pipeline_without_metadata_leaks_or_self_judging():
    evaluator = _load_eval_module()
    fixture = next(
        row for row in evaluator.load_checked_in_corpus()
        if row["category"] == "company_claim"
    )
    calls = {"candidate": [], "audit": [], "judge": []}

    class CandidateLLM:
        def json_call(self, system, user):
            calls["candidate"].append((system, user))
            return [{
                "idx": 0,
                "title": "The company described a prototype result",
                "summary": "The company said a prototype improved a lab metric.",
                "why": "The statement describes a test result.",
                "context": "The evidence is a company statement.",
                "significance": "The result has not been independently verified.",
                "watch": "Watch for independent verification.",
                "detail": "The company reported a result from a lab test.",
                "claims": [],
                "labels": [],
                "redlines": [],
            }]

    class AuditLLM:
        def json_call(self, system, user):
            calls["audit"].append((system, user))
            content = json.loads(user)["content"]
            return {
                "fields": {key: True for key in dn.OBJECTIVITY_FIELDS if key in content},
                "claims": [True for _ in content.get("claims", [])],
            }

    class JudgeLLM:
        def json_call(self, system, user):
            calls["judge"].append((system, user))
            return {"cases": [{
                "case_index": 0,
                "labels": ["company_claim"],
                "attribution_ok": True,
                "redlines": [fixture["expected"]["redlines"][0]],
            }]}

    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), AuditLLM(), JudgeLLM(),
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
        batch_size=10,
    )
    assert runner.config["_objectivity_runtime_mode"] == "shadow"
    rows = runner([fixture], run_number=1)

    assert len(calls["candidate"]) == 1
    assert len(calls["audit"]) == 1
    assert len(calls["judge"]) == 1
    assert calls["audit"][0][0] == dn.OBJECTIVITY_AUDIT_SYSTEM
    forbidden = (
        fixture["id"], fixture["category"], fixture["expected"]["redlines"][0],
        "expected", "threshold", "0.95", "95%", "100%",
    )
    for _system, user in (
            calls["candidate"] + calls["audit"] + calls["judge"]):
        assert all(value not in user for value in forbidden)

    judge_payload = json.loads(calls["judge"][0][1])
    assert set(judge_payload) == {"cases"}
    assert len(judge_payload["cases"]) == 1
    assert set(judge_payload["cases"][0]) == {"evidence", "candidate"}
    assert rows == [{
        "id": fixture["id"],
        "labels": ["company_claim"],
        "attribution_ok": True,
        "redlines": [fixture["expected"]["redlines"][0]],
    }]
    assert evaluator.score_run([fixture], rows)["redline_count"] == 1


def test_paired_cost_gate_fails_closed_on_increase_or_invalid_evidence():
    evaluator = _load_eval_module()

    def report(*, calls=30, cost=0.01234567, weighted_cost=None,
               known=True, runs=3,
               truncations=0, terminal_errors=0, billing_errors=0,
               signature=None):
        return {
            "runs": [{"structure_validity": 1.0} for _ in range(runs)],
            "content_usage": {
                "llm_calls": calls,
                "llm_input_tokens": 1000,
                "llm_cached_input_tokens": 100,
                "llm_output_tokens": 200,
                "llm_cost_usd": cost if known else None,
                "llm_weighted_token_cost_usd": (
                    cost if weighted_cost is None else weighted_cost),
                "llm_cost_known": known,
                "truncated_responses": truncations,
                "terminal_errors": terminal_errors,
                "billing_errors": billing_errors,
                "billing_signature": signature or [{
                    "provider": "deepseek", "model": "deepseek-v4-flash",
                    "price_usd_per_mtok": {
                        "input_miss": 0.14, "input_hit": 0.0028,
                        "output": 0.28,
                    },
                }],
            },
        }

    baseline = report()
    assert evaluator.evaluate_paired_cost_gate(baseline, report())["accepted"] is True
    assert evaluator.evaluate_paired_cost_gate(
        baseline, report(calls=31))["accepted"] is False
    assert evaluator.evaluate_paired_cost_gate(
        baseline, report(cost=0.01234568))["accepted"] is False
    assert evaluator.evaluate_paired_cost_gate(
        baseline, report(cost=0.01, weighted_cost=0.01234568))["accepted"] is False
    for invalid in (
            report(known=False), report(runs=2), report(truncations=1),
            report(terminal_errors=1), report(billing_errors=1),
            report(signature=[{
                "provider": "deepseek", "model": "deepseek-v4-flash",
                "price_usd_per_mtok": {},
            }]),
            report(signature=[{"provider": "other", "model": "other",
                               "price_usd_per_mtok": {}}])):
        assert evaluator.evaluate_paired_cost_gate(
            baseline, invalid)["accepted"] is False
    invalid_pricing = report(signature=[{
        "provider": "deepseek", "model": "deepseek-v4-flash",
        "price_usd_per_mtok": {},
    }])
    assert evaluator.evaluate_paired_cost_gate(
        invalid_pricing, invalid_pricing)["accepted"] is False


def test_production_harness_keeps_fail_closed_fallback_candidate_for_judging():
    evaluator = _load_eval_module()
    fixture = evaluator.load_checked_in_corpus()[0]
    systems = []

    class CandidateLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "Unsafe candidate", "summary": "Unsafe summary",
                "why": "Unsafe why", "context": "Unsafe context",
                "significance": "Unsafe significance", "watch": "Unsafe watch",
                "detail": "Unsafe detail", "claims": [],
            }]

    class FailClosedAudit:
        def json_call(self, system, user):
            systems.append(system)
            if system == dn.OBJECTIVITY_REPAIR_SYSTEM:
                return {
                    "fields": {field: "Still unsafe" for field in dn.OBJECTIVITY_FIELDS},
                    "claims": [],
                }
            content = json.loads(user)["content"]
            return {
                "fields": {key: False for key in dn.OBJECTIVITY_FIELDS if key in content},
                "claims": [False for _ in content.get("claims", [])],
            }

    class JudgeLLM:
        def json_call(self, _system, user):
            candidate = json.loads(user)["cases"][0]["candidate"]
            assert candidate["title"].startswith(fixture["source"][:10])
            return {"cases": [{
                "case_index": 0, "labels": [fixture["category"]],
                "attribution_ok": True, "redlines": [],
            }]}

    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), FailClosedAudit(), JudgeLLM(),
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
    )

    rows = runner([fixture], run_number=1)

    assert systems == [
        dn.OBJECTIVITY_AUDIT_SYSTEM,
        dn.OBJECTIVITY_REPAIR_SYSTEM,
        dn.OBJECTIVITY_AUDIT_SYSTEM,
    ]
    assert len(rows) == 1


@pytest.mark.parametrize("raw_judge", [
    {
        "cases": [{
            "case_index": 0, "labels": ["company_claim"],
            "attribution_ok": True, "redlines": [],
        }],
        "unexpected": True,
    },
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [], "unexpected": True,
    }]},
    {"cases": []},
    {"cases": [
        {
            "case_index": 0, "labels": ["company_claim"],
            "attribution_ok": True, "redlines": [],
        },
        {
            "case_index": 0, "labels": ["company_claim"],
            "attribution_ok": True, "redlines": [],
        },
    ]},
    {"cases": [{
        "case_index": 1, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": "0", "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["not_allowed"],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": [{}],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": [[]],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": [7],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": [None],
        "attribution_ok": True, "redlines": [],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [{}],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [[]],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [7],
    }]},
    {"cases": [{
        "case_index": 0, "labels": ["company_claim"],
        "attribution_ok": True, "redlines": [None],
    }]},
])
def test_production_harness_does_not_launder_invalid_raw_judge_batches(raw_judge):
    evaluator = _load_eval_module()
    fixture = next(
        row for row in evaluator.load_checked_in_corpus()
        if row["category"] == "company_claim"
    )

    class CandidateLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "Safe candidate", "summary": "Safe summary.",
                "why": "", "context": "", "significance": "", "watch": "",
                "detail": "", "claims": [],
            }]

    class AuditLLM:
        def json_call(self, _system, user):
            content = json.loads(user)["content"]
            return {
                "fields": {key: True for key in content if key != "claims"},
                "claims": [],
            }

    class JudgeLLM:
        def json_call(self, _system, _user):
            return raw_judge

    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), AuditLLM(), JudgeLLM(),
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
    )

    rows = runner([fixture], run_number=1)
    score = evaluator.score_run([fixture], rows)

    assert score["structure_validity"] < 1.0


def test_production_harness_splits_invalid_judge_batches_until_rows_are_valid():
    evaluator = _load_eval_module()
    fixtures = evaluator.load_checked_in_corpus()[:2]

    class CandidateLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": index, "title": f"Safe candidate {index}",
                "summary": "Safe summary.", "why": "", "context": "",
                "significance": "", "watch": "", "detail": "", "claims": [],
            } for index in range(2)]

    class AuditLLM:
        def json_call(self, _system, user):
            content = json.loads(user)["content"]
            return {
                "fields": {key: True for key in content if key != "claims"},
                "claims": [],
            }

    class SplitJudge:
        def __init__(self):
            self.batch_sizes = []

        def json_call(self, _system, user):
            cases = json.loads(user)["cases"]
            self.batch_sizes.append(len(cases))
            if len(cases) > 1:
                return {"cases": []}
            return {"cases": [{
                "case_index": 0,
                "labels": [fixtures[0]["category"]],
                "attribution_ok": True,
                "redlines": [],
            }]}

    judge = SplitJudge()
    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), AuditLLM(), judge,
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
        batch_size=2,
    )
    rows = runner(fixtures, run_number=1)

    assert judge.batch_sizes == [2, 1, 1]
    assert [row["id"] for row in rows] == [
        fixtures[0]["id"], fixtures[1]["id"]
    ]


def test_production_harness_stops_at_the_judge_call_budget():
    evaluator = _load_eval_module()
    fixtures = evaluator.load_checked_in_corpus()[:4]

    class CandidateLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": index, "title": f"Safe candidate {index}",
                "summary": "Safe summary.", "why": "", "context": "",
                "significance": "", "watch": "", "detail": "", "claims": [],
            } for index in range(4)]

    class AuditLLM:
        def json_call(self, _system, user):
            content = json.loads(user)["content"]
            return {
                "fields": {key: True for key in content if key != "claims"},
                "claims": [],
            }

    class InvalidJudge:
        def __init__(self):
            self.calls = 0

        def json_call(self, _system, _user):
            self.calls += 1
            return {"cases": []}

    judge = InvalidJudge()
    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), AuditLLM(), judge,
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
        batch_size=4,
        max_judge_calls=3,
    )

    rows = runner(fixtures, run_number=1)

    assert judge.calls == 3
    assert len(rows) == len(fixtures)
    assert evaluator.score_run(fixtures, rows)["structure_validity"] < 1.0


def test_production_harness_marks_validator_exceptions_as_invalid(monkeypatch):
    evaluator = _load_eval_module()
    fixture = next(
        row for row in evaluator.load_checked_in_corpus()
        if row["category"] == "company_claim"
    )

    class CandidateLLM:
        def json_call(self, _system, _user):
            return [{
                "idx": 0, "title": "Safe candidate", "summary": "Safe summary.",
                "why": "", "context": "", "significance": "", "watch": "",
                "detail": "", "claims": [],
            }]

    class AuditLLM:
        def json_call(self, _system, user):
            content = json.loads(user)["content"]
            return {
                "fields": {key: True for key in content if key != "claims"},
                "claims": [],
            }

    class JudgeLLM:
        def json_call(self, _system, _user):
            return {"cases": [{
                "case_index": 0, "labels": ["company_claim"],
                "attribution_ok": True, "redlines": [],
            }]}

    def raise_validator_error(_raw, _expected_count):
        raise RuntimeError("validator failed")

    monkeypatch.setattr(
        evaluator, "_validated_judge_batch", raise_validator_error)
    runner = evaluator.ProductionHarnessRunner(
        dn, CandidateLLM(), AuditLLM(), JudgeLLM(),
        config={"topic_tags": [], "detail": {"enabled": True, "max_chars": 600}},
    )

    rows = runner([fixture], run_number=1)

    assert evaluator.score_run([fixture], rows)["structure_validity"] < 1.0


def test_objectivity_field_caps_apply_to_enrichment_repair_and_serialization():
    limits = dn.FULLTEXT_OBJECTIVITY_FIELD_LIMITS
    oversized = "oversized text " * 200
    event = {"ids": [0], **{field: "safe" for field in dn.OBJECTIVITY_FIELDS}}

    dn._apply_objectivity_repair(
        event,
        {"fields": {field: oversized for field in dn.OBJECTIVITY_FIELDS}},
        list(dn.OBJECTIVITY_FIELDS),
        [],
        {"Synthetic Wire"},
        source_title="Safe source title",
    )

    assert event["title"] == "Safe source title"
    assert all(
        len(event[field]) <= limits[field]
        for field in dn.OBJECTIVITY_FIELDS
        if field != "title" and field in event)

    evidence_text = "FULLTEXT_SENTINEL_DO_NOT_PERSIST_" + ("z" * 900)
    item = {
        "title": "Safe source title", "desc": "Safe public description",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/item",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": evidence_text, "evidence_basis": "fulltext",
        "source_family": "synthetic-wire", "provenance": "original",
    }
    leaky = {
        "ids": [0], "category": "ai", "score": 90, "tier": "T1",
        "status": "发展中", "tags": [],
        **{field: evidence_text for field in dn.OBJECTIVITY_FIELDS},
    }

    serialized = dn.event_to_item(
        leaky, [item], "pick", full_objectivity=True, source_limit=4)

    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        serialized, ensure_ascii=False)
    assert all(
        len(serialized[field]) <= limits[field]
        for field in dn.OBJECTIVITY_FIELDS
        if field in serialized
    )


def test_conservative_fallback_never_uses_fulltext_when_public_desc_is_empty():
    sentinel = "FULLTEXT_SENTINEL_DO_NOT_PERSIST_" + ("e" * 400)
    item = {
        "title": "Safe source title", "desc": "", "source": "Synthetic Wire",
        "source_type": "fact", "evidence_text": sentinel,
    }
    event = {
        "ids": [0], "title": sentinel, "summary": sentinel,
        "why": sentinel, "evidence": {"degraded": False},
    }

    dn._conservative_event_fallback(event, [item], dn.new_quality_stats())

    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        event, ensure_ascii=False)


def test_final_serialization_strips_substantial_fulltext_copy_with_attribution_prefix():
    copied = (
        "The filing says the laboratory result was measured under a private internal "
        "benchmark and has not been independently reproduced by another organization."
    )
    item = {
        "title": "Safe filing title", "desc": "A short public RSS description.",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/filing",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": copied, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "category": "finance", "score": 90, "tier": "T1",
        "title": "Safe edited title", "summary": "Safe edited summary.",
        "detail": f"According to Synthetic Wire: {copied}",
        "status": "发展中", "tags": [],
    }

    serialized = dn.event_to_item(
        event, [item], "pick", full_objectivity=True, source_limit=4)

    assert "detail" not in serialized


def test_missing_title_and_summary_defaults_never_persist_fulltext(
        tmp_path, monkeypatch):
    sentinel = "DEFAULT_PROJECTION_FULLTEXT_SENTINEL_" + ("q" * 180)
    item = {
        "title": sentinel, "desc": sentinel,
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/default-projection",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": sentinel, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "category": "ai", "score": 90, "tier": "T1",
        "status": "developing", "tags": [],
    }

    serialized = dn.event_to_item(
        dict(event), [item], "pick", full_objectivity=True, source_limit=4)

    assert "DEFAULT_PROJECTION_FULLTEXT_SENTINEL" not in json.dumps(
        serialized, ensure_ascii=False)

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    payload = dn.write_output(
        "2026-07-18", "safe brief", [dict(event)], [], [item],
        {"objectivity": {"mode": "active"}}, quality=dn.new_quality_stats(),
    )

    assert "DEFAULT_PROJECTION_FULLTEXT_SENTINEL" not in json.dumps(
        payload, ensure_ascii=False)
    persisted = (tmp_path / "daily" / "2026-07-18.js").read_text(encoding="utf-8")
    assert "DEFAULT_PROJECTION_FULLTEXT_SENTINEL" not in persisted


@pytest.mark.parametrize("variant", ["suffix", "punctuation_whitespace"])
def test_persistence_strips_substantial_fulltext_copy_variants(
        tmp_path, monkeypatch, variant):
    evidence = (
        "The regulator recorded 128 transactions; the filing says they were reviewed "
        "under an internal process, but no independent audit was included."
    )
    if variant == "suffix":
        copied = evidence + " — according to Synthetic Wire."
    else:
        copied = (
            "The regulator recorded 128 transactions ... the filing says\n"
            "they were reviewed under an internal process — but no independent\t"
            "audit was included!"
        )
    item = {
        "title": "Safe filing title", "desc": "A short public RSS description.",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/filing",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": evidence, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "category": "finance", "score": 90, "tier": "T1",
        "title": "Safe edited title", "summary": "Safe edited summary.",
        "detail": copied, "status": "发展中", "tags": [],
    }
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    payload = dn.write_output(
        "2026-07-18", "safe brief", [event], [], [item],
        {"objectivity": {"mode": "active"}}, quality=dn.new_quality_stats(),
    )

    assert "detail" not in payload["items"][0]
    persisted = (tmp_path / "daily" / "2026-07-18.js").read_text(encoding="utf-8")
    assert copied not in persisted


def test_fulltext_overlap_guard_preserves_paraphrase_and_ordinary_short_fact():
    evidence = (
        "The company said its internal benchmark improved by twelve percent during a "
        "private laboratory run, and no outside organization reproduced the result."
    )
    item = {
        "title": "Safe company title", "desc": "A short public RSS description.",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/company",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": evidence, "evidence_basis": "fulltext",
    }
    paraphrase = (
        "The reported improvement came from the firm's own test and still lacks "
        "replication by an external organization."
    )
    short_fact = "The company reported a result."
    event = {
        "ids": [0], "category": "finance", "score": 90, "tier": "T1",
        "title": "Safe edited title", "summary": short_fact,
        "detail": paraphrase, "status": "发展中", "tags": [],
    }

    serialized = dn.event_to_item(
        event, [item], "pick", full_objectivity=True, source_limit=4)

    assert serialized["summary"] == short_fact
    assert serialized["detail"] == paraphrase


def test_repair_strips_attributed_fulltext_copy_before_reaudit():
    evidence = (
        "The filing describes an internal benchmark measured during a private test and "
        "states that no independent organization reproduced the reported result."
    )
    item = {
        "title": "Safe title", "desc": "Short RSS description.",
        "source": "Synthetic Wire", "source_type": "fact",
        "evidence_text": evidence, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "title": "Safe title", "summary": "Safe summary.",
        "detail": "Unsafe initial detail.", "category": "finance",
    }

    class RepairAudit:
        def __init__(self):
            self.audit_calls = 0

        def json_call(self, system, user):
            if system == dn.OBJECTIVITY_REPAIR_SYSTEM:
                return {
                    "fields": {"detail": f"Synthetic Wire reported: {evidence}"},
                    "claims": [],
                }
            content = json.loads(user)["content"]
            self.audit_calls += 1
            if self.audit_calls == 1:
                return {
                    "fields": {key: key != "detail" for key in content if key != "claims"},
                    "claims": [],
                }
            assert "detail" not in content
            return {
                "fields": {key: True for key in content if key != "claims"},
                "claims": [],
            }

    dn.audit_enrichment_support(
        RepairAudit(), [event], [item], dn.new_quality_stats(), secondary=[])

    assert "detail" not in event


def test_fail_closed_fallback_does_not_reintroduce_fulltext_via_desc_overlap():
    evidence = (
        "The filing describes an internal benchmark measured during a private test and "
        "states that no independent organization reproduced the reported result."
    )
    item = {
        "title": "Safe title", "desc": evidence,
        "source": "Synthetic Wire", "source_type": "fact",
        "evidence_text": evidence, "evidence_basis": "fulltext",
    }
    event = {
        "ids": [0], "title": "Unsafe title", "summary": "Unsafe summary.",
        "detail": "Unsafe detail.", "category": "finance",
    }

    class AlwaysFailAudit:
        def json_call(self, system, user):
            if system == dn.OBJECTIVITY_REPAIR_SYSTEM:
                return {"fields": {}, "claims": []}
            content = json.loads(user)["content"]
            return {
                "fields": {key: False for key in content if key != "claims"},
                "claims": [],
            }

    dn.audit_enrichment_support(
        AlwaysFailAudit(), [event], [item], dn.new_quality_stats(), secondary=[])

    assert evidence not in event["summary"]
    assert len(event["summary"]) < 80


def test_fulltext_sentinel_never_survives_repair_fallback_or_persistent_consumers(
        tmp_path, monkeypatch):
    sentinel = "FULLTEXT_SENTINEL_DO_NOT_PERSIST_" + ("q" * 900)
    item = {
        "title": "Safe source title", "desc": "Safe public description",
        "source": "Synthetic Wire", "source_id": "synthetic-wire",
        "source_type": "fact", "tier": "T1", "credibility": 9,
        "url": "https://example.test/item",
        "time": "2026-07-18T00:00:00+00:00",
        "evidence_text": sentinel, "evidence_basis": "fulltext",
        "source_family": "synthetic-wire", "provenance": "original",
    }
    event = {
        "ids": [0], "category": "ai", "title": "Initial safe title",
        "summary": "Initial safe summary", "why": "Initial safe why",
        "context": "Initial safe context", "significance": "Initial safe significance",
        "watch": "Initial safe watch", "detail": "Initial safe detail",
        "claims": [], "score": 90, "tier": "T1", "status": "发展中",
        "tags": [], "risk_flags": {"allegation_legal": True},
        "evidence": {
            "basis": "fulltext", "publisher_count": 1,
            "independent_chain_count": 1, "degraded": False,
        },
    }

    class FailClosedAudit:
        def json_call(self, system, user):
            if system == dn.OBJECTIVITY_REPAIR_SYSTEM:
                return {
                    "fields": {field: sentinel for field in dn.OBJECTIVITY_FIELDS},
                    "claims": [],
                }
            content = json.loads(user)["content"]
            return {
                "fields": {key: False for key in dn.OBJECTIVITY_FIELDS if key in content},
                "claims": [False for _ in content.get("claims", [])],
            }

    quality = dn.new_quality_stats()
    picked = [event]
    secondary = []
    dn.audit_enrichment_support(
        FailClosedAudit(), picked, [item], quality, secondary=secondary)

    assert picked == []
    assert secondary == [event]
    assert event["title"].startswith("Synthetic Wire")
    assert event["summary"].endswith("Safe public description")
    assert not any(field in event for field in dn.QUALITY_EXTENSION_FIELDS)
    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        event, ensure_ascii=False)

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    registry = dn.track_events(
        None, [event], "2026-07-18", {"events": {}}, secondary=[])
    payload = dn.write_output(
        "2026-07-18", "safe brief", [event], [], [item],
        {"objectivity": {"mode": "active"}}, registry=registry, quality=quality,
    )
    dn.write_feed(
        tmp_path, "2026-07-18",
        {"feed_days": 7, "site_url": "https://example.test"},
    )
    weekly_material = dn.weekly_pick_material([payload])

    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        registry, ensure_ascii=False)
    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in json.dumps(
        payload, ensure_ascii=False)
    assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in "\n".join(weekly_material)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert "FULLTEXT_SENTINEL_DO_NOT_PERSIST" not in path.read_text(
                encoding="utf-8")


def test_workflow_supports_non_publishing_validation_and_explicit_publish():
    path = ROOT / ".github" / "workflows" / "daily-news.yml"
    text = path.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    dispatch = workflow["on"]["workflow_dispatch"]
    mode = dispatch["inputs"]["mode"]
    assert mode["default"] == "validate"
    assert mode["options"] == ["validate", "publish"]
    shadow_mode = dispatch["inputs"]["shadow_mode"]
    assert shadow_mode["default"] == "auto"
    assert shadow_mode["options"] == ["auto", "force", "skip"]

    generate = workflow["jobs"]["generate"]
    assert generate["timeout-minutes"] == "60"
    assert generate["env"]["RUN_MODE"] == (
        "${{ github.event_name == 'schedule' && 'publish' || inputs.mode }}")
    assert "LLM_API_KEY" not in generate["env"]
    generate_run = next(step for step in generate["steps"]
                        if step.get("name") == "Generate daily briefing")
    assert generate_run["env"]["STEPFUN_API_KEY"] == (
        "${{ secrets.STEPFUN_API_KEY }}")
    assert generate_run["env"]["DEEPSEEK_API_KEY"] == (
        "${{ secrets.DEEPSEEK_API_KEY }}")
    prepare = next(step for step in generate["steps"]
                   if step.get("name") == "Prepare run data")
    assert "runner.temp" in prepare["env"]["VALIDATION_DATA_DIR"]
    assert 'cp -a source/news/data/. "$VALIDATION_DATA_DIR/"' in prepare["run"]
    commit = next(step for step in generate["steps"]
                  if step.get("name") == "Commit and push")
    # 自动 push 是 CLAUDE.md「严禁自动 push」的唯一例外，例外的边界要在代码里画死：
    # 只在 main 上跑、只提交 source/news/data、只推 main。少任何一条，从别的分支
    # 手动 dispatch 一次 publish 就会把数据推到那条分支上。
    assert commit["if"] == (
        "${{ env.RUN_MODE == 'publish' && github.ref == 'refs/heads/main' }}")
    assert "git add source/news/data" in commit["run"]
    assert "git push origin HEAD:main" in commit["run"]

    upload = next(step for step in generate["steps"]
                  if step.get("name") == "Upload generated data")
    assert upload["with"]["path"] == "${{ steps.run_data.outputs.data_dir }}"
    assert upload["with"]["retention-days"] == "1"

    policy = workflow["jobs"]["shadow-policy"]
    # ADR 0016: the gate step reads no issue state, so it must not hold
    # `issues: read` or a token. Both would only add a way for the step to fail,
    # and a failed lookup fail-opens into a paid shadow run.
    assert "issues" not in policy["permissions"]
    gate = next(step for step in policy["steps"]
                if step.get("name") == "Read shadow gate status")
    assert "env" not in gate
    decision = next(step for step in policy["steps"]
                    if step.get("name") == "Decide shadow policy")
    assert "inputs.shadow_mode" in decision["env"]["SHADOW_MODE"]
    assert "validate" in decision["run"]
    assert "force" in decision["run"]
    assert "skip" in decision["run"]

    shadow = workflow["jobs"]["shadow"]
    assert shadow["timeout-minutes"] == "60"
    assert set(shadow["needs"]) == {"generate", "shadow-policy"}
    assert "needs.shadow-policy.outputs.run_shadow == 'true'" in shadow["if"]
    assert shadow["continue-on-error"] == (
        "${{ github.event_name == 'schedule' || inputs.mode == 'publish' }}")
    download = next(step for step in shadow["steps"]
                    if step.get("name") == "Download generated data")
    assert download["with"]["name"] == "generated-news-data"
    run = next(step for step in shadow["steps"]
               if step.get("name") == "Run objectivity shadow")
    assert run["env"]["STEPFUN_API_KEY"] == "${{ secrets.STEPFUN_API_KEY }}"
    assert run["env"]["DEEPSEEK_API_KEY"] == "${{ secrets.DEEPSEEK_API_KEY }}"
    assert run["env"]["DATA_DIR"] == "${{ runner.temp }}/generated-news-data"
    assert run["continue-on-error"] == (
        "${{ github.event_name == 'schedule' || inputs.mode == 'publish' }}")

    review = workflow["jobs"]["rollout-review"]
    assert "inputs.mode == 'publish'" in review["if"]
    assert "github.event_name == 'schedule'" in review["if"]


def test_weekly_repair_prompt_names_actual_scoped_evidence_keys():
    assert "cited_items" not in dn.WEEKLY_REPAIR_SYSTEM
    for key in ("whole_week_evidence", "thread_evidence", "watch_recap_evidence"):
        assert key in dn.WEEKLY_REPAIR_SYSTEM


def test_rollout_docs_state_interim_is_terminal_and_gates_are_retired():
    """Guard the same thing as before: docs must not imply acceptance happened.

    ADR 0016 retired the five-gate unlock semantics, so the old "N-day gate"
    phrasing is gone -- but the underlying risk is unchanged. Nothing may read as
    though `objectivity active` was validated, and nothing may reintroduce a
    day-counting countdown toward enabling it.
    """
    roadmap = (ROOT / "docs" / "news_source_roadmap.md").read_text(encoding="utf-8")
    readme = (ROOT / "readme.md").read_text(encoding="utf-8")
    label_adr = (ROOT / "docs" / "adr" /
                 "0005-objectivity-label-accepted-sets.md").read_text(encoding="utf-8")
    cause_adr = (ROOT / "docs" / "adr" /
                 "0006-cause-is-extracted-not-inferred.md").read_text(encoding="utf-8")
    retire_adr = (ROOT / "docs" / "adr" /
                  "0016-retire-five-gate-rollout-acceptance.md").read_text(
                      encoding="utf-8")
    combined = "\n".join(
        (roadmap, readme, label_adr, cause_adr, retire_adr))

    for phrase in (
        "interim wording hotfix",
        "--objectivity-shadow",
        "45 条",
        "100%",
        "active mode is not enabled",
        "publisher_count",
        "independent_chain_count",
        "degraded",
        "付费墙",
    ):
        assert phrase in combined

    for stale_count in ("40+", "至少 40", "at least 40"):
        assert stale_count not in combined
    assert "九个风险标签" in combined
    assert "正文只是当次运行内存" in combined

    # The retirement itself must be recorded, and interim must read as terminal
    # rather than as a stage before an upcoming switch.
    for phrase in ("退役", "仪表盘", "interim"):
        assert phrase in retire_adr
    assert "ADR 0016" in readme
    assert "ADR 0016" in roadmap

    # No surface may promise that banking days unlocks anything. ADR 0016 is
    # exempt: it has to name the thing it removed.
    current_surfaces = "\n".join((roadmap, readme, label_adr, cause_adr))
    for revived in ("待人工最终确认", "攒满五门", "五门全部达标"):
        assert revived not in current_surfaces

    assert "live acceptance has not occurred" in combined
    for metric_name in (
        "selected_before_audit",
        "selected_after_audit",
        "audited_candidate_count",
        "demoted_from_selected",
        "source_reference_concentration",
    ):
        assert metric_name in combined


def test_shadow_summary_is_only_persisted_when_the_env_var_is_set(tmp_path):
    summary = {"mode": "shadow", "selected_before_audit": 36}
    target = tmp_path / "nested" / "shadow-summary.json"

    assert dn.write_shadow_summary(summary, environ={}) is False
    assert dn.write_shadow_summary(summary, environ={"SHADOW_SUMMARY_PATH": ""}) is False
    assert dn.write_shadow_summary(
        summary, environ={"SHADOW_SUMMARY_PATH": str(target)}) is True
    assert json.loads(target.read_text(encoding="utf-8")) == summary


def test_enrich_sample_picks_one_stable_item_per_non_empty_category():
    picked = [
        {"id": "top-1", "category": "ai"},
        {"id": "top-2", "category": "ai"},
        {"id": "top-3", "category": "ai"},
        {"id": "more-4", "category": "world"},
        {"id": "", "category": "tech"},
        {"id": "top-5", "category": "unknown-category"},
    ]

    sample = dn.build_enrich_sample(picked, "2026-07-26")

    # One item per category that actually has content, identifiers only.
    assert set(sample) == {"ai", "world"}
    assert sample["ai"][0] in {"top-1", "top-2", "top-3"}
    assert sample["world"] == ["more-4"]
    # A same-day rerun must name the same items; a new day may differ.
    assert dn.build_enrich_sample(picked, "2026-07-26") == sample
    assert dn.build_enrich_sample(list(reversed(picked)), "2026-07-26") == sample
    assert dn.build_enrich_sample([], "2026-07-26") == {}


def test_enrich_sample_names_raw_selected_events():
    # `main` samples the selected events, which only gain their public id later
    # in `event_to_item`; naming them must not wait for the daily payload.
    picked = [
        {"ids": [11, 4], "category": "ai"},
        {"ids": [7], "category": "finance"},
        {"ids": [], "category": "world"},
    ]

    sample = dn.build_enrich_sample(picked, "2026-07-26")

    assert set(sample) == {"ai", "finance"}
    assert sample["ai"] == ["pick-11"]
    assert sample["finance"] == ["pick-7"]
    # The named identifier is the one readers see on the published item.
    assert sample["ai"][0] == dn.public_item_id(picked[0], "pick")
    assert dn.build_enrich_sample(picked, "2026-07-26") == sample


def test_enrich_sample_is_allow_listed_and_rejects_smuggled_text():
    rv_path = PIPELINE_DIR / "rollout_validation.py"
    rv_spec = importlib.util.spec_from_file_location("rv_enrich_test", rv_path)
    rv = importlib.util.module_from_spec(rv_spec)
    sys.modules[rv_spec.name] = rv
    rv_spec.loader.exec_module(rv)

    rv._validate_enrich_sample({"ai": ["top-1"]})
    for bad in ({"ai": "top-1"}, {"ai": ["x" * 65]}, {"": ["top-1"]},
                {"ai": [""]}, {"ai": ["a", "b", "c", "d", "e"]}, []):
        with pytest.raises(ValueError):
            rv._validate_enrich_sample(bad)
