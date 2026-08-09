import copy
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


PIPELINE_DIR = Path(__file__).resolve().parents[1]
ROOT = PIPELINE_DIR.parent


def load_module(name, path):
    assert path.exists(), f"missing production module: {path.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dn = load_module("daily_news_rollout_validation_test", PIPELINE_DIR / "daily_news.py")


def rollout():
    return load_module("rollout_validation_test", PIPELINE_DIR / "rollout_validation.py")


def valid_metrics(**overrides):
    metrics = {
        "threshold": 70,
        "quality_floor": 62,
        "picked_count": 2,
        "category_counts": {category: 0 for category in dn.CATEGORIES},
        "qualified_supply": {category: 0 for category in dn.CATEGORIES},
        "reserved_count": 0,
        "below_threshold_reserved": 0,
        "over_threshold_secondary": 0,
        "threshold_source": "dynamic",
        "history_days": 7,
        "selected_below_quality_floor": 0,
        "selected_opinion_only": 0,
        "category_reservation_violations": 0,
        "threshold_clamp": [66, 82],
        "threshold_clamp_valid": True,
        "threshold_in_clamp": True,
    }
    metrics.update(overrides)
    if "category_counts" not in overrides:
        metrics["category_counts"][dn.CATEGORIES[0]] = metrics["picked_count"]
    return metrics


def valid_health(**overrides):
    health = {
        "candidate_matches": 1,
        "continuity_accepted": 1,
        "continuity_rejected": 0,
        "filtered_history_rows": 0,
        "generation_fallbacks": 0,
        "audit_fallbacks": 0,
        "final_watch_count": 1,
        "final_trusted_continuation_count": 1,
        "selected_count": 1,
        "final_watch_coverage": 1.0,
    }
    health.update(overrides)
    return health


def valid_case(idx=0, *, trusted=True, watch="Watch adoption and observe the next report."):
    public = {
        "id": f"pick-{idx}",
        "title": "Current update",
        "summary": "A current verified update.",
        "watch": watch,
        "watch_detail": "Adoption depends on budget approval and integration results. Observe the next audited report and the next procurement notice.",
        "claims": [{"text": "Verified claim", "kind": "fact", "sources": ["Wire"]}],
    }
    history = []
    if trusted:
        public.update({
            "trusted_continuation": True,
            "day_count": 2,
            "history": [{
                "date": "2026-07-21",
                "summary": "Earlier verified update.",
                "item_ref": "2026-07-21:pick-3",
            }],
        })
        history = [{
            "date": "2026-07-21",
            "title": "Earlier update",
            "summary": "Earlier verified update.",
            "watch": "Watch adoption.",
            "item_ref": "2026-07-21:pick-3",
        }]
    return {
        "idx": idx,
        "picked_index": idx,
        "public": public,
        "sources": [{"source": "Wire", "title": "Source title", "snippet": "Source snippet"}],
        "verified_history": history,
    }


def valid_enrich_case(idx=0):
    case = valid_case(idx, trusted=False, watch="")
    case.pop("idx")
    case.pop("picked_index")
    case["public"].pop("watch")
    case["public"].pop("watch_detail")
    case["public"]["detail"] = "Detailed current status supported by the source."
    return case


def valid_evidence(cases=None, enrich_cases=None, **overrides):
    evidence = {
        "version": "rollout-evidence-v2",
        "date": "2026-07-22",
        "run": {"status": "success", "mode": "shadow", "runtime_seconds": 12.5},
        "selection": valid_metrics(),
        "trajectory": valid_health(),
        "fingerprints": {"runtime": "a" * 64, "trajectory_ui": "b" * 64},
        "review_cases": list(cases if cases is not None else [valid_case()]),
        "enrich_sample": {"ai": ["pick-0"]},
        "enrich_review_cases": list(
            enrich_cases if enrich_cases is not None else [valid_enrich_case()]),
    }
    evidence.update(overrides)
    return evidence


class Judge:
    def __init__(self, rows=None, error=None):
        self.rows = rows if rows is not None else [{
            "idx": 0,
            "continuity": "pass",
            "history_support": "pass",
            "watch_has_variable": True,
            "watch_has_landmark": True,
            "decision": "pass",
            "certainty": "certain",
            "reason_code": "supported",
            "reason": "The continuation and watch are supported.",
        }]
        self.error = error
        self.calls = []

    def json_call(self, system, user):
        self.calls.append((system, json.loads(user)))
        if self.error:
            raise self.error
        return {"rows": copy.deepcopy(self.rows)}


def passing_rows(cases):
    return [{
        "idx": case["idx"],
        "continuity": ("pass" if case["public"].get("trusted_continuation") is True
                       else "not_applicable"),
        "history_support": ("pass" if case["public"].get("trusted_continuation") is True
                            else "not_applicable"),
        "watch_has_variable": True,
        "watch_has_landmark": True,
        "decision": "pass",
        "certainty": "certain",
        "reason_code": "supported",
        "reason": "The available evidence supports this verdict.",
    } for case in cases]


def test_selection_gate_metrics_are_deterministic_and_complete():
    assert hasattr(dn, "finalize_selection_gate_metrics")
    picked = [
        {"score": 61, "opinion_only": False, "category": dn.CATEGORIES[0]},
        {"score": 75, "opinion_only": True, "category": dn.CATEGORIES[1]},
    ]
    stats = {
        "threshold": 70,
        "quality_floor": 62,
        "qualified_supply": {category: (2 if category == dn.CATEGORIES[0] else 0)
                             for category in dn.CATEGORIES},
    }
    cfg = {
        "min_per_category": 2,
        "max_per_category": {},
        "pick_dynamic": {"clamp": [66, 82]},
    }

    result = dn.finalize_selection_gate_metrics(stats, picked, cfg)

    assert result is stats
    assert stats["picked_count"] == 2
    assert stats["selected_below_quality_floor"] == 1
    assert stats["selected_opinion_only"] == 1
    assert stats["category_reservation_violations"] == 1
    assert stats["threshold_clamp"] == [66, 82]
    assert stats["threshold_clamp_valid"] is True
    assert stats["threshold_in_clamp"] is True


def test_transaction_exposes_allow_listed_review_cases_without_persisting_them():
    fixture = json.loads(
        (PIPELINE_DIR / "fixtures" / "trajectory_rollout.json").read_text(encoding="utf-8"))
    fixture["items"][0]["fulltext"] = "FULLTEXT_SENTINEL"
    fixture["items"][0]["content"] = "CONTENT_SENTINEL"
    fixture["registry"]["events"][0]["history"][1]["summary"] = (
        "REJECTED_HISTORY_SENTINEL")

    class FixtureLLM:
        def json_call(self, system, _user):
            if system == dn.CONTINUITY_GATE_SYSTEM:
                stage = "continuity"
            elif system == dn.TRAJECTORY_GENERATION_SYSTEM:
                stage = "generation"
            elif system == dn.TRAJECTORY_AUDIT_SYSTEM:
                stage = "audit"
            else:
                stage = "matches"
            return copy.deepcopy(fixture["responses"][stage])

    picked = copy.deepcopy(fixture["picked"])
    review_cases = []
    prepared = dn.prepare_registry_transaction(
        FixtureLLM(), fixture["registry"], picked, fixture["date"],
        {"events": {}, "trajectory": {"enabled": True}},
        items=fixture["items"], trajectory_review_cases=review_cases)

    assert len(review_cases) == 1
    case = review_cases[0]
    assert case["idx"] == 0
    assert case["public"]["trusted_continuation"] is True
    assert case["public"]["watch"] == picked[0]["watch"]
    assert case["sources"]
    assert case["verified_history"]
    serialized = json.dumps(review_cases, ensure_ascii=False)
    assert "The model launched." in serialized
    assert "Initial enterprise adoption figures arrived." in serialized
    assert "FULLTEXT_SENTINEL" not in serialized
    assert "CONTENT_SENTINEL" not in serialized
    assert "REJECTED_HISTORY_SENTINEL" not in serialized
    serialized = serialized.lower()
    for forbidden in ("fulltext", "content", "article_body", "api_key", "environment"):
        assert forbidden not in serialized
    assert "review_cases" not in json.dumps(prepared, ensure_ascii=False)


def test_transaction_counts_and_projects_multiple_final_trusted_continuations():
    fixture = json.loads(
        (PIPELINE_DIR / "fixtures" / "trajectory_rollout.json").read_text(encoding="utf-8"))
    second_registry = copy.deepcopy(fixture["registry"]["events"][0])
    second_registry["event_id"] = "evt-model-launch-2"
    second_registry["title"] = "Second model launch"
    fixture["registry"]["events"].append(second_registry)
    second_pick = copy.deepcopy(fixture["picked"][0])
    second_pick.update({"ids": [1], "title": "Second model follow-up"})
    fixture["picked"].append(second_pick)
    second_item = copy.deepcopy(fixture["items"][0])
    second_item.update({"title": "Second model follow-up",
                        "source_id": "example-news-2"})
    fixture["items"].append(second_item)
    fixture["responses"]["matches"]["matches"].append(
        {"today": 1, "registry": 1})
    second_validation = copy.deepcopy(
        fixture["responses"]["continuity"]["validations"][0])
    second_validation["candidate"] = 1
    fixture["responses"]["continuity"]["validations"].append(second_validation)
    second_generation = copy.deepcopy(
        fixture["responses"]["generation"]["trajectories"][0])
    second_generation["idx"] = 1
    fixture["responses"]["generation"]["trajectories"].append(second_generation)
    second_audit = copy.deepcopy(fixture["responses"]["audit"]["audits"][0])
    second_audit["idx"] = 1
    fixture["responses"]["audit"]["audits"].append(second_audit)

    class FixtureLLM:
        def json_call(self, system, _user):
            if system == dn.CONTINUITY_GATE_SYSTEM:
                stage = "continuity"
            elif system == dn.TRAJECTORY_GENERATION_SYSTEM:
                stage = "generation"
            elif system == dn.TRAJECTORY_AUDIT_SYSTEM:
                stage = "audit"
            else:
                stage = "matches"
            return copy.deepcopy(fixture["responses"][stage])

    health = dn.new_trajectory_health()
    review_cases = []
    dn.prepare_registry_transaction(
        FixtureLLM(), fixture["registry"], copy.deepcopy(fixture["picked"]),
        fixture["date"], {"events": {}, "trajectory": {"enabled": True}},
        items=fixture["items"], trajectory_health=health,
        trajectory_review_cases=review_cases)

    assert health["final_trusted_continuation_count"] == 2
    assert len(review_cases) == 2
    assert all(case["public"]["trusted_continuation"] is True
               for case in review_cases)


def test_enrich_review_cases_cover_sampled_items_without_trajectory_fields():
    fixture = json.loads(
        (PIPELINE_DIR / "fixtures" / "trajectory_rollout.json").read_text(
            encoding="utf-8"))
    picked = copy.deepcopy(fixture["picked"])
    one_off = {
        "ids": [1],
        "category": "world",
        "title": "One-off verified event",
        "summary": "A one-off event with no trajectory fields.",
        "detail": "The retained detail explains the supported current status.",
        "status": "confirmed",
        "score": 80,
        "tier": "T1",
        "tags": [],
    }
    picked.append(one_off)
    items = copy.deepcopy(fixture["items"])
    items.append({
        "title": "One-off source title",
        "desc": "The source supports the one-off event and its current status.",
        "url": "https://example.test/one-off",
        "source": "Second News",
        "source_id": "second-news",
        "source_type": "fact",
        "tier": "T1",
        "credibility": 9,
        "time": "2026-07-21T02:00:00+00:00",
    })
    sample = dn.build_enrich_sample(picked, fixture["date"])

    builder = getattr(dn, "build_enrich_review_cases", None)
    assert callable(builder), "enrich evidence builder is required"
    cases = builder(picked, items, {"trajectory": {"enabled": True}}, sample)

    expected_ids = {
        item_id for ids in sample.values() for item_id in ids
    }
    assert {case["public"]["id"] for case in cases} == expected_ids
    one_off_case = next(
        case for case in cases if case["public"]["id"] == "pick-1")
    assert one_off_case["public"]["detail"] == one_off["detail"]
    assert "watch" not in one_off_case["public"]
    assert one_off_case["sources"][0]["snippet"].startswith("The source supports")

    trajectory_cases = dn._build_trajectory_review_cases(
        picked, items, {"trajectory": {"enabled": True}})
    assert "pick-1" not in {
        case["public"]["id"] for case in trajectory_cases
    }


def test_enrich_review_case_mapping_is_stable_for_same_day_reruns():
    fixture = json.loads(
        (PIPELINE_DIR / "fixtures" / "trajectory_rollout.json").read_text(
            encoding="utf-8"))
    picked = copy.deepcopy(fixture["picked"])
    sample = dn.build_enrich_sample(picked, fixture["date"])
    builder = getattr(dn, "build_enrich_review_cases", None)
    assert callable(builder), "enrich evidence builder is required"

    first = builder(
        picked, fixture["items"], {"trajectory": {"enabled": True}}, sample)
    second = builder(
        list(reversed(picked)), fixture["items"],
        {"trajectory": {"enabled": True}}, sample)

    assert first == second


def test_evidence_is_allow_listed_fingerprinted_and_written_only_to_explicit_temp_path(
        tmp_path, monkeypatch):
    rv = rollout()
    runtime_file = tmp_path / "runtime.py"
    ui_file = tmp_path / "reports.js"
    runtime_file.write_text("runtime", encoding="utf-8")
    ui_file.write_text("ui", encoding="utf-8")
    data_dir = tmp_path / "public-data"
    data_dir.mkdir()
    output = tmp_path / "runner-temp" / "evidence.json"
    picked = [{"score": 70, "category": dn.CATEGORIES[0], "opinion_only": False}]
    stats = valid_metrics(picked_count=1)

    evidence = rv.build_rollout_evidence(
        date_str="2026-07-22", mode="shadow", runtime_seconds=1.25,
        selection=stats, trajectory=valid_health(), review_cases=[valid_case()],
        enrich_sample={"ai": ["pick-0"]},
        enrich_review_cases=[valid_enrich_case()],
        runtime_paths=[runtime_file], trajectory_ui_paths=[ui_file], config={})

    assert evidence["version"] == "rollout-evidence-v2"
    assert evidence["run"] == {"status": "success", "mode": "shadow", "runtime_seconds": 1.25}
    assert len(evidence["fingerprints"]["runtime"]) == 64
    assert len(evidence["fingerprints"]["trajectory_ui"]) == 64
    assert rv.write_rollout_evidence(evidence, data_dir=data_dir, environ={}) is False
    assert rv.write_rollout_evidence(
        evidence, data_dir=data_dir,
        environ={"ROLLOUT_EVIDENCE_PATH": str(output)}) is True
    assert json.loads(output.read_text(encoding="utf-8")) == evidence
    leaky = copy.deepcopy(evidence)
    leaky["review_cases"][0]["article"] = "full article secret"
    with pytest.raises(ValueError, match="evidence"):
        rv.write_rollout_evidence(
            leaky, data_dir=data_dir,
            environ={"ROLLOUT_EVIDENCE_PATH": str(tmp_path / "leaky.json")})
    with pytest.raises(ValueError, match="DATA_DIR"):
        rv.write_rollout_evidence(
            evidence, data_dir=data_dir,
            environ={"ROLLOUT_EVIDENCE_PATH": str(data_dir / "evidence.json")})
    fake_module = tmp_path / "repo" / "news-pipeline" / "rollout_validation.py"
    fake_module.parent.mkdir(parents=True)
    fake_module.write_text("", encoding="utf-8")
    repository_data = tmp_path / "repo" / "source" / "news" / "data"
    monkeypatch.setattr(rv, "__file__", str(fake_module))
    with pytest.raises(ValueError, match="source/news/data"):
        rv.write_rollout_evidence(
            evidence, data_dir=data_dir,
            environ={"ROLLOUT_EVIDENCE_PATH": str(repository_data / "evidence.json")})


def test_rollout_allowlist_accepts_detail_watch_and_240_character_context(tmp_path):
    rv = rollout()
    case = valid_case()
    case["public"]["context"] = "来" * 240
    case["public"]["watch_detail"] = "走" * 260
    evidence = valid_evidence([case])
    output = tmp_path / "evidence.json"

    assert rv.write_rollout_evidence(
        evidence,
        data_dir=tmp_path / "data",
        environ={"ROLLOUT_EVIDENCE_PATH": str(output)},
    ) is True


def test_rollout_allowlist_rejects_detail_watch_without_short_watch(tmp_path):
    rv = rollout()
    case = valid_case()
    case["public"].pop("watch")

    with pytest.raises(ValueError, match="allow-list"):
        rv.write_rollout_evidence(
            valid_evidence([case]),
            data_dir=tmp_path / "data",
            environ={
                "ROLLOUT_EVIDENCE_PATH": str(tmp_path / "evidence.json"),
            },
        )


@pytest.mark.parametrize("mutate", [
    lambda evidence: evidence["enrich_review_cases"].clear(),
    lambda evidence: evidence["enrich_review_cases"].append(
        copy.deepcopy(evidence["enrich_review_cases"][0])),
    lambda evidence: evidence["enrich_review_cases"][0]["public"].update(
        {"id": "pick-99"}),
    lambda evidence: evidence["enrich_review_cases"][0]["public"].update(
        {"detail": "x" * 1201}),
    lambda evidence: evidence["enrich_review_cases"][0].update(
        {"unexpected": "value"}),
])
def test_enrich_review_cases_must_exactly_cover_the_sample(tmp_path, mutate):
    rv = rollout()
    evidence = valid_evidence()
    mutate(evidence)

    with pytest.raises(ValueError, match="allow-list"):
        rv.write_rollout_evidence(
            evidence,
            data_dir=tmp_path / "data",
            environ={
                "ROLLOUT_EVIDENCE_PATH": str(tmp_path / "evidence.json"),
            },
        )


def test_enrich_review_case_title_uses_the_public_source_fallback_limit(tmp_path):
    rv = rollout()
    evidence = valid_evidence()
    evidence["enrich_review_cases"][0]["public"]["title"] = "x" * 300

    assert rv.write_rollout_evidence(
        evidence,
        data_dir=tmp_path / "data",
        environ={"ROLLOUT_EVIDENCE_PATH": str(tmp_path / "evidence.json")},
    ) is True

    evidence["enrich_review_cases"][0]["public"]["title"] = "x" * 301
    with pytest.raises(ValueError, match="allow-list"):
        rv.write_rollout_evidence(
            evidence,
            data_dir=tmp_path / "data",
            environ={"ROLLOUT_EVIDENCE_PATH": str(tmp_path / "evidence.json")},
        )


def test_v1_rollout_evidence_is_not_rewritten_as_current_evidence(tmp_path):
    rv = rollout()
    evidence = valid_evidence()
    evidence["version"] = "rollout-evidence-v1"

    with pytest.raises(ValueError, match="version"):
        rv.write_rollout_evidence(
            evidence,
            data_dir=tmp_path / "data",
            environ={
                "ROLLOUT_EVIDENCE_PATH": str(tmp_path / "evidence.json"),
            },
        )


def test_stage_fingerprints_only_change_for_their_allow_listed_scope(tmp_path):
    rv = rollout()
    builder = getattr(rv, "build_stage_fingerprints", None)
    assert callable(builder), "stage-scoped fingerprint builder is required"
    runtime_file = tmp_path / "runtime.py"
    reports_file = tmp_path / "reports.js"
    css_file = tmp_path / "news.css"
    runtime_file.write_text("runtime", encoding="utf-8")
    reports_file.write_text("reports", encoding="utf-8")
    css_file.write_text("css", encoding="utf-8")
    config = {
        "llm": {"base_url": "https://llm.example/v1", "api_key": "secret-a",
                "model": "model-a", "temperature": 0.3, "max_retries": 3,
                "extra_body": {"thinking": {"type": "disabled"}}},
        "audit_llm": {"base_url": "", "api_key": "secret-b", "model": ""},
        "prefilter": {"enabled": True, "model": "prefilter-a"},
        "objectivity": {"mode": "interim"},
        "pick_threshold": 68, "pick_min": 8, "pick_max": 32,
        "pick_dynamic": {"enabled": True, "window_days": 14,
                         "percentile": 75, "clamp": [66, 82],
                         "min_history_days": 5, "backfill_offset": 8},
        "scoring": {"dim_weights": {"impact": 0.3},
                    "tier_multipliers": {"T1": 1.0}, "fit_span": 0.3},
        "interest_weights": {"ai": 1.0},
        "min_per_category": 3, "max_per_category": {},
        "opinion": {"enabled": True, "cooccur_bonus": 1.08},
        "cost_guard": {
            "same_day_reconcile_max_calls": 20,
            "same_day_min_shared_keys": 4,
            "cross_source_novelty_batch_size": 20,
            "cross_source_novelty_max_calls": 8,
            "generate_warn_usd": 0.06,
            "shadow_warn_usd": 0.09,
        },
        "events": {"match_window_days": 14, "archive_days": 7,
                   "prune_archived_days": 60},
        "trajectory": {"enabled": True},
        "deep": {"enabled": True, "pick_threshold": 7},
        "feed_days": 7,
    }

    def fingerprints(candidate):
        return builder(
            config=candidate, runtime_paths=[runtime_file],
            trajectory_ui_paths=[reports_file, css_file])

    baseline = fingerprints(config)
    selection_change = copy.deepcopy(config)
    selection_change["pick_dynamic"]["clamp"] = [67, 83]
    selection_fingerprint = fingerprints(selection_change)
    assert selection_fingerprint["runtime"] != baseline["runtime"]
    assert selection_fingerprint["trajectory_ui"] == baseline["trajectory_ui"]

    shared_change = copy.deepcopy(config)
    shared_change["llm"]["model"] = "model-b"
    assert fingerprints(shared_change)["runtime"] != baseline["runtime"]

    endpoint_path_change = copy.deepcopy(config)
    endpoint_path_change["llm"]["base_url"] = "https://llm.example/v2"
    assert fingerprints(endpoint_path_change)["runtime"] != baseline["runtime"]

    same_day_guard_change = copy.deepcopy(config)
    same_day_guard_change["cost_guard"]["same_day_reconcile_max_calls"] = 12
    assert fingerprints(same_day_guard_change)["runtime"] != baseline["runtime"]

    novelty_guard_change = copy.deepcopy(config)
    novelty_guard_change["cost_guard"]["cross_source_novelty_max_calls"] = 4
    assert fingerprints(novelty_guard_change)["runtime"] != baseline["runtime"]

    cost_warning_change = copy.deepcopy(config)
    cost_warning_change["cost_guard"]["generate_warn_usd"] = 0.04
    assert fingerprints(cost_warning_change) == baseline

    trajectory_change = copy.deepcopy(config)
    trajectory_change["trajectory"]["enabled"] = False
    trajectory_fingerprint = fingerprints(trajectory_change)
    assert trajectory_fingerprint["runtime"] == baseline["runtime"]
    assert trajectory_fingerprint["trajectory_ui"] != baseline["trajectory_ui"]

    unrelated = copy.deepcopy(config)
    unrelated["llm"]["api_key"] = "rotated-secret"
    unrelated["deep"]["pick_threshold"] = 9
    unrelated["feed_days"] = 30
    assert fingerprints(unrelated) == baseline

    css_file.write_text("css changed", encoding="utf-8")
    css_change = fingerprints(config)
    assert css_change["runtime"] == baseline["runtime"]
    assert css_change["trajectory_ui"] != baseline["trajectory_ui"]


def test_runtime_fingerprint_tracks_dependencies_interpreter_runner_and_epoch(tmp_path):
    rv = rollout()
    runtime_file = tmp_path / "daily_news.py"
    requirements_file = tmp_path / "requirements.txt"
    ui_file = tmp_path / "reports.js"
    runtime_file.write_text("runtime-v1", encoding="utf-8")
    requirements_file.write_text("lxml==6.1.1", encoding="utf-8")
    ui_file.write_text("ui-v1", encoding="utf-8")
    environment = {
        "python_version": "3.12.13",
        "python_implementation": "CPython",
        "runner_os": "Linux",
        "runner_arch": "X64",
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        "epoch": "1",
    }

    def fingerprints(candidate_environment):
        return rv.build_stage_fingerprints(
            config={},
            runtime_paths=[runtime_file, requirements_file],
            trajectory_ui_paths=[ui_file],
            runtime_environment=candidate_environment,
        )

    baseline = fingerprints(environment)
    for key, value in (
        ("python_version", "3.12.14"),
        ("python_implementation", "PyPy"),
        ("runner_os", "Windows"),
        ("runner_arch", "ARM64"),
        ("epoch", "2"),
    ):
        changed = dict(environment)
        changed[key] = value
        result = fingerprints(changed)
        assert result["runtime"] != baseline["runtime"]
        assert result["trajectory_ui"] == baseline["trajectory_ui"]

    requirements_file.write_text("lxml==6.1.2", encoding="utf-8")
    dependency_change = fingerprints(environment)
    assert dependency_change["runtime"] != baseline["runtime"]
    assert dependency_change["trajectory_ui"] == baseline["trajectory_ui"]


def test_runtime_fingerprint_tracks_active_provider_protocol_and_limits_not_secrets(
        tmp_path):
    rv = rollout()
    runtime_file = tmp_path / "runtime.py"
    ui_file = tmp_path / "ui.js"
    runtime_file.write_text("runtime", encoding="utf-8")
    ui_file.write_text("ui", encoding="utf-8")
    config = {
        "llm": {
            "active_provider": "stepfun",
            "providers": {
                "stepfun": {
                    "protocol": "anthropic",
                    "base_url": "https://api.stepfun.com/v1",
                    "api_key_env": "STEPFUN_API_KEY",
                    "api_key": "secret-a",
                    "model": "step-explore",
                    "max_tokens": 16384,
                    "max_retries": 3,
                    "request_timeout": [10, 180],
                },
                "deepseek": {
                    "protocol": "openai",
                    "base_url": "https://api.deepseek.com/v1",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "api_key": "secret-b",
                    "model": "deepseek-v4-flash",
                    "temperature": 0.3,
                    "max_retries": 3,
                    "extra_body": {"thinking": {"type": "disabled"}},
                },
            },
        },
        "audit_llm": {},
        "prefilter": {"enabled": True},
        "objectivity": {"mode": "interim"},
    }

    def runtime(candidate):
        return rv.build_stage_fingerprints(
            config=candidate,
            runtime_paths=[runtime_file],
            trajectory_ui_paths=[ui_file],
        )["runtime"]

    baseline = runtime(config)
    secret_change = copy.deepcopy(config)
    secret_change["llm"]["providers"]["stepfun"]["api_key"] = "rotated"
    assert runtime(secret_change) == baseline

    for key, value in (
        ("protocol", "openai"),
        ("max_tokens", 8192),
        ("max_retries", 4),
        ("request_timeout", [10, 240]),
    ):
        changed = copy.deepcopy(config)
        changed["llm"]["providers"]["stepfun"][key] = value
        assert runtime(changed) != baseline

    fallback = copy.deepcopy(config)
    fallback["llm"]["active_provider"] = "deepseek"
    assert runtime(fallback) != baseline


def test_daily_pipeline_evidence_emitter_is_opt_in_and_import_context_safe(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    output = tmp_path / "runner-temp" / "evidence.json"
    args = (
        "2026-07-22", {"mode": "shadow"}, 2.0, valid_metrics(),
        valid_health(), [valid_case()], data_dir, {})

    assert dn.emit_rollout_evidence(*args, environ={}) is False
    assert dn.emit_rollout_evidence(
        *args, environ={"ROLLOUT_EVIDENCE_PATH": str(output)}) is True
    assert json.loads(output.read_text(encoding="utf-8"))["version"] == "rollout-evidence-v2"


def test_evaluator_batches_every_case_once_and_emits_versioned_pass_report():
    rv = rollout()
    cases = [valid_case(0), valid_case(1, trusted=False)]
    judge = Judge(rows=[
        {
            "idx": 0, "continuity": "pass", "history_support": "pass",
            "watch_has_variable": True, "watch_has_landmark": True,
            "decision": "pass", "certainty": "certain",
            "reason_code": "supported", "reason": "Supported continuation and watch.",
        },
        {
            "idx": 1, "continuity": "not_applicable",
            "history_support": "not_applicable", "watch_has_variable": True,
            "watch_has_landmark": True, "decision": "pass",
            "certainty": "certain", "reason_code": "supported",
            "reason": "The public watch has both required parts.",
        },
    ])
    evidence = valid_evidence(
        cases, trajectory=valid_health(final_watch_count=2, selected_count=2))

    report = rv.evaluate_rollout(evidence, shadow_success=True, judge_llm=judge)

    assert len(judge.calls) == 1
    assert judge.calls[0][1] == {"cases": cases}
    assert report["version"] == "rollout-report-v1"
    assert report["selection"]["status"] == "pass"
    assert report["trajectory"]["status"] == "pass"
    assert report["trajectory"]["watch_ratio"] == 1.0
    assert [row["idx"] for row in report["trajectory"]["verdicts"]] == [0, 1]
    assert report["fingerprints"] == evidence["fingerprints"]
    assert report["enrich_sample"] == evidence["enrich_sample"]


def test_evaluator_rejects_nested_forbidden_or_malformed_evidence_before_judge():
    rv = rollout()
    mutations = [
        lambda evidence: evidence["review_cases"][0]["public"].update(
            {"fulltext": "SECRET FULL BODY"}),
        lambda evidence: evidence["review_cases"][0].update(
            {"content": "SECRET CONTENT"}),
        lambda evidence: evidence["review_cases"][0]["sources"][0].update(
            {"snippet": "x" * 401}),
        lambda evidence: evidence["review_cases"][0]["public"].update(
            {"title": ["not", "text"]}),
    ]
    for mutate in mutations:
        evidence = valid_evidence()
        mutate(evidence)
        judge = Judge()

        report = rv.evaluate_rollout(
            evidence, shadow_success=True, judge_llm=judge)

        assert report["selection"]["status"] == "needs_review"
        assert report["trajectory"]["status"] == "needs_review"
        assert judge.calls == []


def test_evaluator_requires_exact_final_trusted_case_coverage():
    rv = rollout()
    evidence = valid_evidence(trajectory=valid_health(
        candidate_matches=2, continuity_accepted=2,
        final_trusted_continuation_count=2, selected_count=2,
        final_watch_coverage=0.5))
    judge = Judge()

    report = rv.evaluate_rollout(
        evidence, shadow_success=True, judge_llm=judge)

    assert report["trajectory"]["status"] == "needs_review"
    assert "trusted" in " ".join(report["trajectory"]["reasons"]).lower()


def test_evaluator_rejects_final_trusted_count_above_accepted_continuations():
    rv = rollout()
    cases = [valid_case(0), valid_case(1)]
    evidence = valid_evidence(cases, trajectory=valid_health(
        candidate_matches=2, continuity_accepted=1,
        final_watch_count=2, final_trusted_continuation_count=2,
        selected_count=2, final_watch_coverage=1.0))

    report = rv.evaluate_rollout(
        evidence, shadow_success=True,
        judge_llm=Judge(rows=passing_rows(cases)))

    assert report["trajectory"]["status"] == "needs_review"


@pytest.mark.parametrize(("item_ref", "expected"), [
    (None, "pass"),
    ("2026-07-21:pick-3", "pass"),
    ("2026-07-21:more-9", "pass"),
    ("1999-01-01:pick-3", "fail"),
    ("2026-07-21:deep-1", "fail"),
    ("2026-07-21:not-a-public-item", "fail"),
])
def test_continuation_link_validates_exact_public_item_ref_contract(item_ref, expected):
    rv = rollout()
    case = valid_case()
    if item_ref is None:
        case["public"]["history"][0].pop("item_ref")
    else:
        case["public"]["history"][0]["item_ref"] = item_ref
    report = rv.evaluate_rollout(
        valid_evidence([case]), shadow_success=True,
        judge_llm=Judge(rows=passing_rows([case])))
    assert report["trajectory"]["status"] == expected


@pytest.mark.parametrize("reason", [
    "Possibly supported; cannot verify independently.",
    "This may be supported, but it is not independently verified.",
    "It might be supported, but the evidence is inconclusive.",
    "It is unclear whether this continuation is supported.",
    "The relationship could be valid, but it remains unverified.",
    "The evidence could not confirm that the continuation is valid.",
    "The continuation may not be supported by the available evidence.",
    "Evidence verification remains inconclusive.",
    "There is insufficient evidence to confirm the continuation.",
    "The support remains unconfirmed and cannot be verified conclusively.",
    "The evidence is ambiguous.",
    "The support remains doubtful.",
    "可能支持，尚待确认。",
    "相关性无法核实。",
    "这次延续可能成立，但证据仍无定论。",
    "这次延续可能不成立。",
    "这次延续或许尚未获得支持。",
    "这段关系也许并不属实。",
    "目前尚不清楚这是否属于可信延续。",
    "这段关系仍未经核实，无法确认。",
    "此前已确认，但当前无法核实。",
    "先前已确认；目前证据无法核实这次延续。",
    "此前已确认；目前仍无法核实，需等待新文件。",
    "核验结果仍无定论。",
    "证据不足以确认这次延续关系。",
    "证据存疑。",
    "这次延续关系存在歧义。",
])
def test_explicit_multilingual_uncertainty_needs_review(reason):
    rv = rollout()
    row = passing_rows([valid_case()])[0]
    row["reason"] = reason
    report = rv.evaluate_rollout(
        valid_evidence(), shadow_success=True, judge_llm=Judge(rows=[row]))
    assert report["trajectory"]["status"] == "needs_review"


@pytest.mark.parametrize("reason", [
    "The watch names a possible adoption variable and a concrete quarterly report.",
    "Verification could affect adoption decisions, so watch the next audited report.",
    "The continuation is supported and independently verified by the filing.",
    "Earlier evidence was inconclusive, but the new filing conclusively verifies the continuation.",
    "走向把可能影响采用率的变量写清，并给出下一份季度报告作为路标。",
    "核验方式可能影响采用决策，因此应观察下一份审计报告。",
    "现有证据已核实这次延续关系，下一份季度报告是明确路标。",
    "此前证据不足，但新文件已确认并支持这次延续。",
    "此前无法确认，但今天的官方文件已核实延续。",
    "此前证据不足；现在新文件已确认并支持这次延续。",
    "The evidence was ambiguous, but the latest filing conclusively supports it.",
    "Support was doubtful; however, the latest filing now verifies it.",
    "此前证据存疑，但新文件现已确认并支持这次延续。",
    "原有歧义已由最新文件消除，目前证据明确支持延续。",
])
def test_uncertainty_detection_does_not_misread_quoted_watch_language(reason):
    rv = rollout()
    row = passing_rows([valid_case()])[0]
    row["reason"] = reason
    report = rv.evaluate_rollout(
        valid_evidence(), shadow_success=True, judge_llm=Judge(rows=[row]))
    assert report["trajectory"]["status"] == "pass"


def test_judge_pass_requires_certain_supported_structured_reason():
    rv = rollout()
    uncertain = passing_rows([valid_case()])[0]
    uncertain.update({"certainty": "uncertain", "reason_code": "ambiguous"})
    uncertain_report = rv.evaluate_rollout(
        valid_evidence(), shadow_success=True, judge_llm=Judge(rows=[uncertain]))
    assert uncertain_report["trajectory"]["status"] == "needs_review"

    supported = passing_rows([valid_case()])[0]
    supported.update({"certainty": "certain", "reason_code": "supported"})
    supported_report = rv.evaluate_rollout(
        valid_evidence(), shadow_success=True, judge_llm=Judge(rows=[supported]))
    assert supported_report["trajectory"]["status"] == "pass"


@pytest.mark.parametrize("rows", [
    [],
    [{"idx": 0, "continuity": "pass", "history_support": "pass",
      "watch_has_variable": True, "watch_has_landmark": True,
      "decision": "pass", "reason": "ok"}] * 2,
    [{"idx": 9, "continuity": "pass", "history_support": "pass",
      "watch_has_variable": True, "watch_has_landmark": True,
      "decision": "pass", "reason": "ok"}],
    [{"idx": 0, "continuity": "uncertain", "history_support": "pass",
      "watch_has_variable": True, "watch_has_landmark": True,
      "decision": "pass", "reason": "uncertain"}],
    [{"idx": 0, "continuity": "pass", "history_support": "pass",
      "watch_has_variable": True, "watch_has_landmark": True,
      "decision": "needs_review", "reason": "uncertain"}],
    [{"idx": 0, "continuity": "pass", "history_support": "pass",
      "watch_has_variable": True, "watch_has_landmark": True,
      "decision": "pass", "reason": "x" * 241}],
])
def test_malformed_missing_duplicate_or_uncertain_judge_rows_need_review(rows):
    rv = rollout()
    report = rv.evaluate_rollout(
        valid_evidence(), shadow_success=True, judge_llm=Judge(rows=rows))
    assert report["trajectory"]["status"] == "needs_review"
    assert report["trajectory"]["verdicts"][0]["decision"] == "needs_review"


def test_judge_infrastructure_failure_is_needs_review_not_fail():
    rv = rollout()
    report = rv.evaluate_rollout(
        valid_evidence(), shadow_success=True,
        judge_llm=Judge(error=RuntimeError("judge unavailable")))
    assert report["selection"]["status"] == "pass"
    assert report["trajectory"]["status"] == "needs_review"
    assert "judge" in " ".join(report["trajectory"]["reasons"]).lower()


def test_judge_retries_a_malformed_batch_before_returning_needs_review():
    rv = rollout()
    case = valid_case()
    valid_row = Judge().rows[0]

    class RetryJudge:
        def __init__(self):
            self.calls = 0

        def json_call(self, _system, _user):
            self.calls += 1
            if self.calls == 1:
                return {"rows": [{"idx": 0}]}
            return {"rows": [copy.deepcopy(valid_row)]}

    judge = RetryJudge()
    verdicts, error = rv._judge_verdicts([case], judge)

    assert error is None
    assert judge.calls == 2
    assert verdicts[0]["decision"] == "pass"


def test_judge_retries_a_response_with_extra_top_level_fields():
    rv = rollout()
    case = valid_case()
    valid_row = Judge().rows[0]

    class RetryJudge:
        def __init__(self):
            self.calls = 0

        def json_call(self, _system, _user):
            self.calls += 1
            response = {"rows": [copy.deepcopy(valid_row)]}
            if self.calls == 1:
                response["unexpected"] = True
            return response

    judge = RetryJudge()
    verdicts, error = rv._judge_verdicts([case], judge)

    assert error is None
    assert judge.calls == 2
    assert verdicts[0]["decision"] == "pass"


def test_judge_failure_report_does_not_persist_provider_exception_text():
    rv = rollout()
    report = rv.evaluate_rollout(
        valid_evidence(), shadow_success=True,
        judge_llm=Judge(error=RuntimeError("TOKEN=super-secret")))

    serialized = json.dumps(report, ensure_ascii=False)
    assert "super-secret" not in serialized
    assert report["trajectory"]["status"] == "needs_review"


def test_explicit_judge_failure_has_a_gate_reason():
    rv = rollout()
    rows = [{
        "idx": 0, "continuity": "fail", "history_support": "pass",
        "watch_has_variable": True, "watch_has_landmark": True,
        "decision": "fail", "certainty": "certain",
        "reason_code": "unsupported",
        "reason": "Today does not continue the mainline.",
    }]
    report = rv.evaluate_rollout(
        valid_evidence(), shadow_success=True, judge_llm=Judge(rows=rows))
    assert report["trajectory"]["status"] == "fail"
    assert report["trajectory"]["reasons"]


def test_explicit_judge_failure_dominates_another_uncertain_verdict():
    rv = rollout()
    cases = [
        valid_case(0),
        valid_case(1, trusted=False),
    ]
    rows = passing_rows(cases)
    rows[0].update({
        "continuity": "fail",
        "history_support": "pass",
        "decision": "fail",
        "certainty": "certain",
        "reason_code": "unsupported",
        "reason": "The continuation is contradicted by the evidence.",
    })
    rows[1].update({
        "decision": "needs_review",
        "certainty": "uncertain",
        "reason_code": "ambiguous",
        "reason": "The watch wording is ambiguous.",
    })
    evidence = valid_evidence(
        cases=cases,
        trajectory=valid_health(
            candidate_matches=2,
            continuity_accepted=1,
            continuity_rejected=1,
            final_watch_count=2,
            final_trusted_continuation_count=1,
            selected_count=2,
            final_watch_coverage=1.0,
        ),
    )

    report = rv.evaluate_rollout(
        evidence, shadow_success=True, judge_llm=Judge(rows=rows))

    assert report["trajectory"]["status"] == "fail"


def test_watch_gate_fails_when_uncertain_rows_cannot_reach_eighty_percent():
    rv = rollout()
    cases = [valid_case(index, trusted=False) for index in range(10)]
    rows = passing_rows(cases)
    for row in rows[6:9]:
        row["watch_has_variable"] = False
        row["watch_has_landmark"] = False
    rows[9].update({
        "watch_has_variable": False,
        "watch_has_landmark": False,
        "decision": "needs_review",
        "certainty": "uncertain",
        "reason_code": "ambiguous",
        "reason": "The watch wording is ambiguous.",
    })
    evidence = valid_evidence(
        cases=cases,
        trajectory=valid_health(
            candidate_matches=1,
            continuity_accepted=0,
            final_watch_count=10,
            final_trusted_continuation_count=0,
            selected_count=10,
            final_watch_coverage=1.0,
        ),
    )

    report = rv.evaluate_rollout(
        evidence, shadow_success=True, judge_llm=Judge(rows=rows))

    assert report["trajectory"]["watch_ratio"] == 0.6
    assert report["trajectory"]["status"] == "fail"


def test_incomplete_evidence_envelope_needs_review_for_both_gates():
    rv = rollout()
    evidence = valid_evidence()
    evidence.pop("fingerprints")
    report = rv.evaluate_rollout(evidence, shadow_success=True, judge_llm=Judge())
    assert report["selection"]["status"] == "needs_review"
    assert report["trajectory"]["status"] == "needs_review"


def test_internally_inconsistent_machine_metrics_need_review():
    rv = rollout()
    selection = valid_metrics(picked_count=2)
    selection["category_counts"][dn.CATEGORIES[0]] = 1
    selection_report = rv.evaluate_rollout(
        valid_evidence(selection=selection), shadow_success=True, judge_llm=Judge())
    assert selection_report["selection"]["status"] == "needs_review"

    trajectory = valid_health(selected_count=1, final_watch_count=2,
                              final_watch_coverage=2.0)
    trajectory_report = rv.evaluate_rollout(
        valid_evidence(trajectory=trajectory), shadow_success=True, judge_llm=Judge())
    assert trajectory_report["trajectory"]["status"] == "needs_review"


def test_duplicate_review_case_picked_index_needs_review():
    rv = rollout()
    cases = [valid_case(0), valid_case(1, trusted=False)]
    cases[1]["picked_index"] = 0
    evidence = valid_evidence(
        cases, trajectory=valid_health(final_watch_count=2, selected_count=2))
    rows = [
        {"idx": 0, "continuity": "pass", "history_support": "pass",
         "watch_has_variable": True, "watch_has_landmark": True,
         "decision": "pass", "certainty": "certain",
         "reason_code": "supported", "reason": "Supported."},
        {"idx": 1, "continuity": "not_applicable",
         "history_support": "not_applicable", "watch_has_variable": True,
         "watch_has_landmark": True, "decision": "pass",
         "certainty": "certain", "reason_code": "supported",
         "reason": "Supported."},
    ]
    report = rv.evaluate_rollout(
        evidence, shadow_success=True, judge_llm=Judge(rows=rows))
    assert report["trajectory"]["status"] == "needs_review"


def test_no_candidate_or_no_watch_is_neutral_without_judge_call():
    rv = rollout()
    judge = Judge()
    evidence = valid_evidence(
        cases=[], trajectory=valid_health(candidate_matches=0, continuity_accepted=0,
                                          final_watch_count=0,
                                          final_trusted_continuation_count=0,
                                          final_watch_coverage=0.0))
    report = rv.evaluate_rollout(evidence, shadow_success=True, judge_llm=judge)
    assert report["trajectory"]["status"] == "neutral"
    assert judge.calls == []


@pytest.mark.parametrize("case_field", ["review_cases", "enrich_review_cases"])
def test_evaluator_rejects_review_cases_with_too_many_sources_before_judge(case_field):
    evidence = valid_evidence()
    evidence[case_field][0]["sources"] = [
        {"source": f"Outlet {index}", "title": "Report", "snippet": "Evidence"}
        for index in range(6)
    ]
    judge = Judge()

    report = rollout().evaluate_rollout(
        evidence, shadow_success=True, judge_llm=judge)

    assert report["selection"]["status"] == "needs_review"
    assert report["trajectory"]["status"] == "needs_review"
    assert judge.calls == []


def test_first_day_and_same_day_rerun_both_remain_trajectory_neutral():
    class NoMatchLLM:
        def json_call(self, _system, _user):
            return {"matches": []}

    items = [{
        "title": "Launch", "desc": "The product launched.",
        "url": "https://example.test/launch", "source": "Wire",
        "source_id": "wire", "source_type": "fact", "tier": "T1",
        "credibility": 9, "time": "2026-07-22T01:00:00+00:00",
    }]

    def run_attempt(registry):
        picked = [{
            "ids": [0], "category": "ai", "title": "Launch",
            "summary": "The product launched.", "status": "confirmed",
            "watch": "Watch adoption and observe the next report.",
            "score": 90, "tier": "T1", "tags": [],
        }]
        health = dn.new_trajectory_health()
        cases = []
        prepared = dn.prepare_registry_transaction(
            NoMatchLLM(), registry, picked, "2026-07-22",
            {"events": {}, "trajectory": {"enabled": True}}, items=items,
            trajectory_health=health, trajectory_review_cases=cases)
        judge = Judge(rows=passing_rows(cases))
        report = rollout().evaluate_rollout(
            valid_evidence(cases, trajectory=health), shadow_success=True,
            judge_llm=judge)
        return prepared, health, report, judge

    first_registry, first_health, first_report, first_judge = run_attempt(
        {"version": 1, "events": []})
    _, rerun_health, rerun_report, rerun_judge = run_attempt(first_registry)

    assert first_health["candidate_matches"] == 0
    assert rerun_health["candidate_matches"] == 0
    assert first_report["trajectory"]["status"] == "neutral"
    assert rerun_report["trajectory"]["status"] == "neutral"
    assert first_judge.calls == []
    assert rerun_judge.calls == []


@pytest.mark.parametrize(("change", "reason_fragment"), [
    ({"shadow_success": False}, "shadow"),
    ({"selected_below_quality_floor": 1}, "quality floor"),
    ({"selected_opinion_only": 1}, "opinion"),
    ({"category_reservation_violations": 1}, "reservation"),
    ({"picked_count": 37}, "36"),
    ({"threshold_in_clamp": False}, "clamp"),
    ({"threshold": 90, "threshold_in_clamp": True}, "clamp"),
])
def test_selection_gate_rejects_each_automatic_pass_violation(change, reason_fragment):
    rv = rollout()
    shadow_success = change.pop("shadow_success", True)
    evidence = valid_evidence(selection=valid_metrics(**change))
    report = rv.evaluate_rollout(evidence, shadow_success=shadow_success, judge_llm=Judge())
    assert report["selection"]["status"] == "fail"
    assert reason_fragment in " ".join(report["selection"]["reasons"]).lower()


def test_selection_gate_accepts_new_capacity_boundary():
    rv = rollout()
    evidence = valid_evidence(selection=valid_metrics(picked_count=36))
    report = rv.evaluate_rollout(
        evidence, shadow_success=True, judge_llm=Judge())
    assert report["selection"]["status"] == "pass"


def test_cli_accepts_completed_shadow_gate_as_selection_evidence(tmp_path):
    rv = rollout()

    args = rv.parse_cli_args([
        "--evidence", str(tmp_path / "evidence.json"),
        "--shadow-outcome", "accepted",
    ])

    assert args.shadow_outcome == "accepted"
    assert rv.shadow_satisfies_selection(args.shadow_outcome) is True


def test_watch_ratio_and_continuation_link_are_deterministic_trajectory_gates():
    rv = rollout()
    cases = [valid_case(i, trusted=(i == 0)) for i in range(5)]
    cases[0]["public"]["history"][0]["item_ref"] = "1999-01-01:pick-3"
    rows = []
    for case in cases:
        rows.append({
            "idx": case["idx"],
            "continuity": "pass" if case["idx"] == 0 else "not_applicable",
            "history_support": "pass" if case["idx"] == 0 else "not_applicable",
            "watch_has_variable": case["idx"] != 4,
            "watch_has_landmark": case["idx"] != 4,
            "decision": "pass",
            "certainty": "certain",
            "reason_code": "supported",
            "reason": "Checked.",
        })
    report = rv.evaluate_rollout(
        valid_evidence(cases, trajectory=valid_health(
            final_watch_count=5, selected_count=5)),
        shadow_success=True, judge_llm=Judge(rows=rows))
    assert report["trajectory"]["watch_ratio"] == 0.8
    assert report["trajectory"]["status"] == "fail"
    assert any("link" in reason.lower() for reason in report["trajectory"]["reasons"])


def test_judge_config_reuses_audit_identity_but_forces_zero_temperature():
    rv = rollout()
    cfg = {
        "llm": {"base_url": "https://primary", "api_key": "secret", "model": "main",
                "temperature": 0.4, "max_retries": 3,
                "extra_body": {"thinking": {"type": "disabled"}}},
        "audit_llm": {"base_url": "https://audit", "model": "judge"},
    }
    resolved = rv.resolve_judge_llm_config(cfg)
    assert resolved["base_url"] == "https://audit"
    assert resolved["api_key"] == "secret"
    assert resolved["model"] == "judge"
    assert resolved["max_retries"] == 3
    assert resolved["extra_body"] == {"thinking": {"type": "disabled"}}
    assert resolved["temperature"] == 0.0


def test_cli_turns_judge_construction_failure_into_needs_review_report(
        tmp_path, monkeypatch):
    rv = rollout()
    evidence_path = tmp_path / "evidence.json"
    config_path = tmp_path / "config.yaml"
    report_path = tmp_path / "report.json"
    evidence_path.write_text(json.dumps(valid_evidence()), encoding="utf-8")
    config_path.write_text(json.dumps({
        "llm": {"base_url": "https://example.test", "api_key": "",
                "model": "judge"},
        "audit_llm": {},
    }), encoding="utf-8")

    class BrokenLLM:
        def __init__(self, _cfg):
            raise RuntimeError("missing credentials")

    monkeypatch.setitem(sys.modules, "daily_news", types.SimpleNamespace(LLM=BrokenLLM))
    try:
        rv.main([
            "--evidence", str(evidence_path), "--shadow-outcome", "success",
            "--config", str(config_path), "--output", str(report_path),
        ])
    except Exception as exc:
        pytest.fail(f"CLI leaked Judge construction failure: {exc}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["version"] == "rollout-report-v1"
    assert report["trajectory"]["status"] == "needs_review"


def test_cli_does_not_construct_judge_for_neutral_evidence(tmp_path, monkeypatch):
    rv = rollout()
    evidence = valid_evidence(
        cases=[], trajectory=valid_health(
            candidate_matches=0, continuity_accepted=0,
            final_watch_count=0, final_trusted_continuation_count=0,
            final_watch_coverage=0.0))
    evidence_path = tmp_path / "evidence.json"
    config_path = tmp_path / "config.yaml"
    report_path = tmp_path / "report.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    config_path.write_text(json.dumps({
        "llm": {"base_url": "https://example.test", "api_key": "",
                "model": "judge"},
    }), encoding="utf-8")
    constructions = []

    class CountingLLM:
        def __init__(self, _cfg):
            constructions.append(True)

    monkeypatch.setitem(sys.modules, "daily_news", types.SimpleNamespace(LLM=CountingLLM))
    rv.main([
        "--evidence", str(evidence_path), "--shadow-outcome", "success",
        "--config", str(config_path), "--output", str(report_path),
    ])

    assert constructions == []
    assert json.loads(report_path.read_text(encoding="utf-8"))[
        "trajectory"]["status"] == "neutral"
