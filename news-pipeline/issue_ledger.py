"""Issue #15 rollout ledger with pure aggregation and a thin REST boundary."""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import math
import os
import re
import urllib.request
from pathlib import Path


GATE_STATUSES = {"pass", "fail", "neutral", "needs_review"}

# Selection and trajectory are judged from the rollout report; the remaining
# three gates are judged from committed health data plus the shadow summary.
GATES = ("selection", "trajectory", "enrich", "objectivity_shadow",
         "source_metrics")
# Consecutive gates reset to zero on a failed day; cumulative gates only count
# valid days, so a day without usable data never erases banked observations.
# That exemption covers missing data only -- a runtime-fingerprint change still
# zeroes both kinds (see RUNTIME_RESET_GATES below).
CONSECUTIVE_GATES = ("selection", "trajectory", "objectivity_shadow")
# ADR 0016 retired the unlock semantics: these streaks are a quality dashboard,
# not a countdown toward enabling `objectivity active` or authorizing new
# sources. There are deliberately no per-gate targets to reach -- the former
# targets were unreachable in practice, because the reset below fires on any
# change to the four fingerprinted pipeline files.
# A shared runtime change restarts every clock: the sample composition moved, so
# pre-change and post-change evidence must never be mixed. A trajectory-UI-only
# change restarts trajectory alone.
RUNTIME_RESET_GATES = GATES
TRAJECTORY_UI_RESET_GATES = ("trajectory",)
ENRICH_SAFETY_MULTIPLIER = 1.2
ENRICH_BASELINE_DAYS = 3

STATE_VERSION = "issue-ledger-v2"
LEGACY_STATE_VERSIONS = ("issue-ledger-v1",)

TRUSTED_BOT = "github-actions[bot]"
MARKER_TEMPLATE = "<!-- daily-news-rollout:{date} -->"
STATE_PREFIX = "<!-- daily-news-rollout-state:"
STATE_SUFFIX = " -->"
_STATE_RE = re.compile(r"<!-- daily-news-rollout-state:(\{.*\}) -->")
_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret)\s*[=:]\s*[^\s,;]+")
_TOKEN_VALUE_RE = re.compile(
    r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{8,}|bearer\s+\S+)")
_URL_RE = re.compile(r"https?://[^\s]+", re.I)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _attempt_key(attempt):
    run_id = str(attempt.get("run_id") or "")
    ordered_id = (0, int(run_id)) if run_id.isdigit() else (1, run_id)
    return ordered_id, int(attempt.get("run_attempt") or 0)


def merge_attempts(existing, incoming):
    """Upsert one workflow attempt without collapsing distinct reruns."""
    merged = [copy.deepcopy(row) for row in existing]
    key = _attempt_key(incoming)
    for index, row in enumerate(merged):
        if _attempt_key(row) == key:
            merged[index] = copy.deepcopy(incoming)
            break
    else:
        merged.append(copy.deepcopy(incoming))
    return sorted(merged, key=_attempt_key)


def _gate_status(attempt, gate):
    value = attempt.get(gate)
    status = value.get("status") if isinstance(value, dict) else None
    return status if status in GATE_STATUSES else "needs_review"


def _latest_fingerprints(attempts):
    result = {"runtime": "", "trajectory_ui": ""}
    for attempt in attempts:
        fingerprints = attempt.get("fingerprints")
        if not isinstance(fingerprints, dict):
            continue
        for name in result:
            value = fingerprints.get(name)
            if isinstance(value, str) and value:
                result[name] = value
    return result


def _valid_manual_review(gate, review, latest):
    return (
        gate in GATES
        and isinstance(review, dict)
        and review.get("status") in {"pass", "fail", "neutral"}
        and review.get("reason_code") == "artifact_reviewed"
        and str(review.get("run_id") or "") == str(latest.get("run_id") or "")
        and int(review.get("run_attempt") or 0)
        == int(latest.get("run_attempt") or 0)
    )


def _enrich_samples(attempt):
    """Read the deterministic sample counts recorded for the enrich gate."""
    source = attempt.get("enrich") if isinstance(attempt, dict) else None
    source = source if isinstance(source, dict) else {}
    sample = source.get("sample")
    return sample if isinstance(sample, dict) else {}


def build_daily_state(date, attempts, manual_reviews=None):
    """Aggregate all attempts for one Beijing date."""
    ordered = sorted((copy.deepcopy(row) for row in attempts), key=_attempt_key)
    latest = ordered[-1] if ordered else {}
    publication_failed = any(
        row.get("publication") == "failure" for row in ordered)
    aggregate = {"publication": "failure" if publication_failed else "success"}
    for gate in GATES:
        aggregate[gate] = ("fail" if publication_failed
                           else _gate_status(latest, gate))
    state = {
        "version": STATE_VERSION,
        "date": str(date),
        "attempts": ordered,
        "aggregate": aggregate,
        "fingerprints": _latest_fingerprints(ordered),
        "streaks": {gate: 0 for gate in GATES},
        "enrich_sample": _enrich_samples(latest),
    }
    reviews = manual_reviews if isinstance(manual_reviews, dict) else {}
    applied = {}
    for gate in GATES:
        review = reviews.get(gate)
        if (aggregate[gate] == "needs_review"
                and _valid_manual_review(gate, review, latest)):
            applied[gate] = copy.deepcopy(review)
            aggregate[gate] = review["status"]
    if applied:
        state["manual_reviews"] = applied
    return state


def _review_sample_counts(gate, samples_passed, samples_total):
    """Validate the optional per-day enrich sample tally supplied by a human."""
    if samples_passed is None and samples_total is None:
        return None
    if gate != "enrich":
        raise ValueError("sample counts apply only to the enrich gate")
    passed = int(samples_passed or 0)
    total = int(samples_total or 0)
    if total <= 0:
        raise ValueError("samples_total must be positive")
    if not 0 <= passed <= total:
        raise ValueError("samples_passed must be between 0 and samples_total")
    return {"passed": passed, "total": total}


def apply_manual_review(state, *, gate, status, run_id, run_attempt,
                        samples_passed=None, samples_total=None):
    """Replace only one needs-review result with an evidenced human verdict."""
    if gate not in GATES:
        raise ValueError(f"manual review gate must be one of {', '.join(GATES)}")
    if status not in {"pass", "fail", "neutral"}:
        raise ValueError("manual review status must be pass, fail, or neutral")
    counts = _review_sample_counts(gate, samples_passed, samples_total)
    updated = copy.deepcopy(state)
    if gate == "enrich":
        sample = updated.get("enrich_sample")
        sample = sample if isinstance(sample, dict) else {}
        expected_total = sum(
            len(ids) for ids in sample.values() if isinstance(ids, list))
        if status == "neutral":
            if counts is not None:
                raise ValueError("neutral enrich review cannot include sample counts")
        else:
            if counts is None:
                raise ValueError("enrich verdict requires sample counts")
            if counts["total"] != expected_total:
                raise ValueError("enrich verdict must review all sampled items")
    aggregate = updated.get("aggregate")
    aggregate = aggregate if isinstance(aggregate, dict) else {}
    if aggregate.get("publication") != "success":
        raise ValueError("manual review cannot override a publication failure")
    if aggregate.get(gate) != "needs_review":
        raise ValueError("manual review can only replace needs_review")
    attempts = updated.get("attempts") or []
    latest = attempts[-1] if attempts else {}
    if str(latest.get("run_id") or "") != str(run_id or ""):
        raise ValueError("manual review run_id must match the latest attempt")
    if int(latest.get("run_attempt") or 0) != int(run_attempt or 0):
        raise ValueError(
            "manual review run_attempt must match the latest attempt")
    reviews = updated.get("manual_reviews")
    reviews = copy.deepcopy(reviews) if isinstance(reviews, dict) else {}
    reviews[gate] = {
        "status": status,
        "reason_code": "artifact_reviewed",
        "run_id": str(run_id),
        "run_attempt": int(run_attempt),
    }
    if counts is not None:
        reviews[gate]["samples"] = counts
    updated["manual_reviews"] = reviews
    updated["aggregate"][gate] = status
    return updated


def _apply_gate(streak, status, gate):
    if status == "pass":
        return streak + 1
    if status == "fail" and gate in CONSECUTIVE_GATES:
        return 0
    return streak


def _reset(streaks, gates):
    for gate in gates:
        streaks[gate] = 0


def compute_streaks(states):
    """Compute independent gate streaks over chronological daily states."""
    streaks = {gate: 0 for gate in GATES}
    previous = {"runtime": "", "trajectory_ui": ""}
    for state in sorted(states, key=lambda row: str(row.get("date") or "")):
        fingerprints = state.get("fingerprints")
        fingerprints = fingerprints if isinstance(fingerprints, dict) else {}
        runtime = fingerprints.get("runtime")
        trajectory_ui = fingerprints.get("trajectory_ui")
        if previous["runtime"] and runtime and runtime != previous["runtime"]:
            _reset(streaks, RUNTIME_RESET_GATES)
        elif (previous["trajectory_ui"] and trajectory_ui
              and trajectory_ui != previous["trajectory_ui"]):
            _reset(streaks, TRAJECTORY_UI_RESET_GATES)

        aggregate = state.get("aggregate")
        aggregate = aggregate if isinstance(aggregate, dict) else {}
        if aggregate.get("publication") == "failure":
            _reset(streaks, CONSECUTIVE_GATES)
        else:
            for gate in GATES:
                streaks[gate] = _apply_gate(
                    streaks[gate], aggregate.get(gate), gate)

        if runtime:
            previous["runtime"] = runtime
        if trajectory_ui:
            previous["trajectory_ui"] = trajectory_ui
    return streaks


def enrich_content_ratio(states):
    """Aggregate the human-recorded enrich sample tally across the window."""
    passed = total = 0
    for state in states:
        reviews = state.get("manual_reviews")
        reviews = reviews if isinstance(reviews, dict) else {}
        samples = reviews.get("enrich", {}).get("samples")
        if not isinstance(samples, dict):
            continue
        passed += int(samples.get("passed") or 0)
        total += int(samples.get("total") or 0)
    if total <= 0:
        return None, 0, 0
    return round(passed / total, 4), passed, total


def marker_for_date(date):
    return MARKER_TEMPLATE.format(date=str(date))


def _sanitize_text(value, limit=240):
    text = " ".join(str(value or "").split())
    text = _SECRET_RE.sub(lambda match: f"{match.group(1)}=[redacted]", text)
    text = _TOKEN_VALUE_RE.sub("[redacted]", text)
    text = _URL_RE.sub("[url]", text)
    text = text.replace("--", "—")
    return text[:limit]


def _project_reasons(value):
    if not isinstance(value, list):
        return []
    return [reason for reason in (_sanitize_text(row) for row in value[:5]) if reason]


def _project_gate(report, gate):
    source = report.get(gate) if isinstance(report, dict) else None
    source = source if isinstance(source, dict) else {}
    status = source.get("status")
    return {
        "status": status if status in GATE_STATUSES else "needs_review",
        "reasons": _project_reasons(source.get("reasons")),
    }


def _project_metrics(value):
    """Copy only finite numeric metrics; free text never reaches the ledger."""
    if not isinstance(value, dict):
        return {}
    projected = {}
    for name, metric in list(value.items())[:8]:
        if isinstance(metric, bool) or not isinstance(metric, (int, float)):
            continue
        numeric = float(metric)
        if not math.isfinite(numeric):
            continue
        projected[_sanitize_text(name, limit=40)] = round(numeric, 4)
    return projected


def _project_evaluation(evaluation):
    """Project a health-data evaluation into the compact ledger gate schema."""
    source = evaluation if isinstance(evaluation, dict) else {}
    status = source.get("status")
    projected = {
        "status": status if status in GATE_STATUSES else "needs_review",
        "reasons": _project_reasons(source.get("reasons")),
    }
    if not isinstance(evaluation, dict):
        projected["reasons"] = ["gate evaluation unavailable"]
    metrics = _project_metrics(source.get("metrics"))
    if metrics:
        projected["metrics"] = metrics
    return projected


def _project_enrich_sample(sample):
    """Record which items a human must review, by identifier only."""
    if not isinstance(sample, dict):
        return {}
    projected = {}
    for category, ids in list(sample.items())[:12]:
        if not isinstance(ids, list):
            continue
        cleaned = [_sanitize_text(row, limit=64) for row in ids[:4]]
        cleaned = [row for row in cleaned if row]
        if cleaned:
            projected[_sanitize_text(category, limit=32)] = cleaned
    return projected


def _project_fingerprints(report):
    source = report.get("fingerprints") if isinstance(report, dict) else None
    source = source if isinstance(source, dict) else {}
    return {
        name: value if isinstance(value := source.get(name), str)
        and _SHA256_RE.fullmatch(value) else ""
        for name in ("runtime", "trajectory_ui")
    }


def _judge_summary(report):
    trajectory = report.get("trajectory") if isinstance(report, dict) else None
    trajectory = trajectory if isinstance(trajectory, dict) else {}
    counts = {"pass": 0, "fail": 0, "needs_review": 0}
    verdicts = trajectory.get("verdicts")
    if isinstance(verdicts, list):
        for verdict in verdicts:
            decision = verdict.get("decision") if isinstance(verdict, dict) else None
            if decision in counts:
                counts[decision] += 1
    ratio = trajectory.get("watch_ratio")
    counts["watch_ratio"] = (
        round(float(ratio), 4)
        if isinstance(ratio, (int, float)) and not isinstance(ratio, bool)
        and 0 <= float(ratio) <= 1 else None)
    return counts


SHADOW_REQUIRED_FIELDS = (
    "selected_before_audit", "selected_after_audit", "audited_candidate_count",
    "demoted_from_selected", "source_reference_concentration")
SOURCE_REQUIRED_FIELDS = (
    "high_risk_single_source_rate", "independent_chain_distribution",
    "source_reference_concentration")


def _median(values):
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _quality_ratio(record):
    audited = record.get("enrichment_audited_events")
    removed = record.get("removed_fields")
    if (not isinstance(audited, int) or isinstance(audited, bool)
            or not isinstance(removed, int) or isinstance(removed, bool)
            or audited <= 0 or removed < 0):
        return None
    return removed / audited


def _is_nonnegative_int(value):
    return type(value) is int and value >= 0


def _valid_source_concentration(value):
    if not isinstance(value, list):
        return False
    for row in value:
        if not isinstance(row, dict):
            return False
        source = row.get("source")
        count = row.get("reference_count")
        share = row.get("reference_share")
        if (not isinstance(source, str) or not source.strip()
                or not _is_nonnegative_int(count)
                or isinstance(share, bool) or not isinstance(share, (int, float))
                or not math.isfinite(float(share)) or not 0 <= float(share) <= 1):
            return False
    return True


def _valid_chain_distribution(value):
    return (
        isinstance(value, dict)
        and all(isinstance(key, str) and key.isdigit()
                and _is_nonnegative_int(count)
                for key, count in value.items())
    )


def enrich_baseline(quality_health, before_date):
    """Median removed-field ratio over the output days preceding the window."""
    records = (quality_health or {}).get("records")
    records = records if isinstance(records, list) else []
    prior = [row for row in records
             if isinstance(row, dict) and str(row.get("date") or "") < str(before_date)]
    prior.sort(key=lambda row: str(row.get("date") or ""))
    ratios = [ratio for ratio in
              (_quality_ratio(row) for row in prior)
              if ratio is not None]
    recent = ratios[-ENRICH_BASELINE_DAYS:]
    if len(recent) != ENRICH_BASELINE_DAYS:
        return None
    return _median(recent)


def evaluate_enrich(quality_health, *, date, window_start):
    """Judge only the mechanical enrich safety metric.

    Content quality is deliberately left at `needs_review`: the three per-item
    checks require human judgement, and an unreviewed day must never be
    credited as a pass.
    """
    records = (quality_health or {}).get("records")
    records = records if isinstance(records, list) else []
    today = next((row for row in records
                  if isinstance(row, dict) and str(row.get("date") or "") == str(date)),
                 None)
    if today is None:
        return {"status": "needs_review", "reasons": ["no enrich quality record for the date"]}
    ratio = _quality_ratio(today)
    if ratio is None:
        return {"status": "needs_review", "reasons": ["no audited events to measure"]}
    baseline = enrich_baseline(quality_health, window_start)
    if baseline is None:
        return {"status": "needs_review",
                "reasons": ["no pre-window baseline to compare against"],
                "metrics": {"ratio": round(ratio, 4)}}
    limit = baseline * ENRICH_SAFETY_MULTIPLIER
    metrics = {"ratio": round(ratio, 4), "baseline": round(baseline, 4),
               "limit": round(limit, 4)}
    if ratio > limit:
        return {"status": "fail",
                "reasons": [f"removed-field ratio {ratio:.3f} exceeds limit {limit:.3f}"],
                "metrics": metrics}
    return {"status": "needs_review",
            "reasons": ["safety metric within limit; content sampling awaits human review"],
            "metrics": metrics}


def evaluate_objectivity_shadow(shadow_summary, *, shadow_outcome):
    """Judge the daily objectivity shadow observation."""
    if shadow_outcome == "accepted":
        return {"status": "neutral",
                "reasons": ["shadow capped; sample on demand with force"]}
    if shadow_outcome != "success":
        return {"status": "fail", "reasons": ["objectivity shadow run did not succeed"]}
    if not isinstance(shadow_summary, dict):
        return {"status": "needs_review", "reasons": ["shadow summary unavailable"]}
    missing = [name for name in SHADOW_REQUIRED_FIELDS
               if shadow_summary.get(name) is None]
    if missing:
        return {"status": "needs_review",
                "reasons": [f"shadow summary missing {', '.join(sorted(missing))}"]}
    before = shadow_summary["selected_before_audit"]
    after = shadow_summary["selected_after_audit"]
    audited = shadow_summary["audited_candidate_count"]
    demoted = shadow_summary["demoted_from_selected"]
    if (any(not _is_nonnegative_int(value)
            for value in (before, after, audited, demoted))
            or after > before or demoted > before
            or before - after != demoted
            or not _valid_source_concentration(
                shadow_summary["source_reference_concentration"])):
        return {"status": "needs_review",
                "reasons": ["shadow summary metrics are malformed or inconsistent"]}
    return {"status": "pass", "reasons": [],
            "metrics": {name: shadow_summary.get(name)
                        for name in ("selected_before_audit", "selected_after_audit",
                                     "demoted_from_selected")}}


def evaluate_source_metrics(
        source_health, shadow_summary, *, date, shadow_outcome="success"):
    """Judge whether one day contributes a complete source-metric observation."""
    if shadow_outcome == "accepted":
        return {"status": "neutral",
                "reasons": ["shadow capped; sample on demand with force"]}
    days = (source_health or {}).get("days")
    rows = days.get(str(date)) if isinstance(days, dict) else None
    if not isinstance(rows, dict) or not rows:
        return {"status": "neutral", "reasons": ["no source health record for the date"]}
    if not isinstance(shadow_summary, dict):
        return {"status": "neutral", "reasons": ["shadow metrics unavailable for the date"]}
    missing = [name for name in SOURCE_REQUIRED_FIELDS
               if shadow_summary.get(name) is None]
    if missing:
        return {"status": "neutral",
                "reasons": [f"shadow metrics missing {', '.join(sorted(missing))}"]}
    rate = shadow_summary["high_risk_single_source_rate"]
    if (isinstance(rate, bool) or not isinstance(rate, (int, float))
            or not math.isfinite(float(rate)) or not 0 <= float(rate) <= 1
            or not _valid_chain_distribution(
                shadow_summary["independent_chain_distribution"])
            or not _valid_source_concentration(
                shadow_summary["source_reference_concentration"])):
        return {"status": "neutral",
                "reasons": ["shadow source metrics are malformed"]}
    if any(not isinstance(row, dict)
           or not _is_nonnegative_int(row.get("count"))
           or type(row.get("error")) is not bool
           for row in rows.values()):
        return {"status": "neutral",
                "reasons": ["source health metrics are malformed"]}
    errored = sum(1 for row in rows.values()
                  if row["error"])
    empty = sum(1 for row in rows.values()
                if row["count"] == 0)
    return {"status": "pass", "reasons": [],
            "metrics": {"sources": len(rows), "errored": errored, "zero_update": empty}}


def build_attempt(*, report, publication, publication_reason, run_id,
                  run_attempt, sha, enrich=None, objectivity_shadow=None,
                  source_metrics=None, enrich_sample=None):
    """Project a report into the compact, non-sensitive ledger schema."""
    publication = "success" if publication == "success" else "failure"
    selection = _project_gate(report, "selection")
    trajectory = _project_gate(report, "trajectory")
    gates = {
        "enrich": _project_evaluation(enrich),
        "objectivity_shadow": _project_evaluation(objectivity_shadow),
        "source_metrics": _project_evaluation(source_metrics),
    }
    reason = _sanitize_text(publication_reason)
    if publication == "failure":
        failed = {"status": "fail", "reasons": [reason or "publication failed"]}
        selection = copy.deepcopy(failed)
        trajectory = copy.deepcopy(failed)
        gates = {gate: copy.deepcopy(failed) for gate in gates}
    elif not isinstance(report, dict):
        selection = trajectory = {
            "status": "needs_review", "reasons": ["rollout report unavailable"]}
    sample = _project_enrich_sample(enrich_sample)
    if sample:
        gates["enrich"]["sample"] = sample
    return {
        "run_id": str(run_id),
        "run_attempt": int(run_attempt),
        "sha": str(sha)[:40],
        "publication": publication,
        "selection": selection,
        "trajectory": trajectory,
        **gates,
        "judge": _judge_summary(report),
        "fingerprints": _project_fingerprints(report),
    }


def _trusted_bot_comment(comment):
    user = comment.get("user") if isinstance(comment, dict) else None
    return (isinstance(user, dict) and user.get("login") == TRUSTED_BOT
            and user.get("type") == "Bot")


def _valid_machine_state(state):
    return (isinstance(state, dict)
            and state.get("version") in (STATE_VERSION, *LEGACY_STATE_VERSIONS)
            and isinstance(state.get("date"), str)
            and isinstance(state.get("attempts"), list)
            and isinstance(state.get("aggregate"), dict)
            and isinstance(state.get("fingerprints"), dict)
            and isinstance(state.get("streaks"), dict))


def migrate_state(state):
    """Lift a legacy state to the current schema without inventing evidence.

    Days recorded before the three extra gates existed carry no enrich,
    objectivity-shadow or source-metric measurement, so those gates become
    `neutral`: they freeze their clock instead of crediting an unobserved day.
    """
    if state.get("version") == STATE_VERSION:
        return state
    migrated = copy.deepcopy(state)
    migrated["version"] = STATE_VERSION
    aggregate = migrated.get("aggregate")
    aggregate = aggregate if isinstance(aggregate, dict) else {}
    streaks = migrated.get("streaks")
    streaks = streaks if isinstance(streaks, dict) else {}
    for gate in GATES:
        aggregate.setdefault(gate, "neutral")
        streaks.setdefault(gate, 0)
    migrated["aggregate"] = aggregate
    migrated["streaks"] = streaks
    migrated.setdefault("enrich_sample", {})
    return migrated


def parse_machine_state(comment):
    """Parse only comments authored by the workflow's trusted bot identity."""
    if not _trusted_bot_comment(comment):
        return None
    body = comment.get("body")
    if not isinstance(body, str):
        return None
    match = _STATE_RE.search(body)
    if not match:
        return None
    try:
        state = json.loads(match.group(1))
    except (TypeError, ValueError):
        return None
    if (not _valid_machine_state(state)
            or marker_for_date(state["date"]) not in body):
        return None
    return migrate_state(state)


def find_daily_comment(comments, date):
    marker = marker_for_date(date)
    candidates = [
        comment for comment in comments
        if _trusted_bot_comment(comment)
        and marker in str(comment.get("body") or "")
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda row: int(row.get("id") or 0))


def _gate_reasons(state, gate):
    attempts = state.get("attempts") or []
    if (state.get("aggregate", {}).get("publication") == "failure"
            and any(row.get("publication") == "failure" for row in attempts)):
        return ["at least one publication attempt failed"]
    latest = attempts[-1] if attempts else {}
    projected = latest.get(gate) if isinstance(latest, dict) else None
    return projected.get("reasons") if isinstance(projected, dict) else []


GATE_LABELS = {
    "selection": "Selection",
    "trajectory": "Trajectory",
    "enrich": "Enrich",
    "objectivity_shadow": "Objectivity shadow",
    "source_metrics": "Source metrics",
}


def render_comment(state, *, content_ratio=None, content_counts=(0, 0)):
    """Render one readable daily comment plus compact hidden machine state."""
    machine = json.dumps(state, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    attempts = state.get("attempts") or []
    latest = attempts[-1] if attempts else {}
    aggregate = state.get("aggregate") or {}
    streaks = state.get("streaks") or {}
    fingerprints = state.get("fingerprints") or {}
    judge = latest.get("judge") if isinstance(latest, dict) else {}
    judge = judge if isinstance(judge, dict) else {}
    manual_reviews = state.get("manual_reviews")
    manual_reviews = manual_reviews if isinstance(manual_reviews, dict) else {}

    def reasons_for(gate):
        reasons = _gate_reasons(state, gate)
        return "; ".join(reasons) if reasons else "none"

    lines = [
        marker_for_date(state.get("date", "")),
        f"{STATE_PREFIX}{machine}{STATE_SUFFIX}",
        f"## 日报验收 · {state.get('date', '')}",
        "",
    ]
    if state.get("gap"):
        lines.append(
            "- Run: 无（当日没有任何日报台账记录，所有门冻结、不计入也不清零）")
    else:
        lines.append(
            f"- Run: {latest.get('run_id', '')} / attempt "
            f"{latest.get('run_attempt', '')} · `{str(latest.get('sha', ''))[:7]}`")
    lines.append(
        f"- Publication: **{aggregate.get('publication', 'needs_review')}**")
    lines.extend(
        f"- {GATE_LABELS[gate]}: **{aggregate.get(gate, 'needs_review')}** — "
        f"{reasons_for(gate)}"
        for gate in GATES)
    lines.extend([
        (f"- Judge: pass={judge.get('pass', 0)}, fail={judge.get('fail', 0)}, "
         f"needs_review={judge.get('needs_review', 0)}, "
         f"watch_ratio={judge.get('watch_ratio') if judge.get('watch_ratio') is not None else 'n/a'}"),
        (f"- Fingerprints: runtime=`{str(fingerprints.get('runtime') or '')[:12]}`, "
         f"trajectory_ui=`{str(fingerprints.get('trajectory_ui') or '')[:12]}`"),
        "- Observed days: " + ", ".join(
            f"{GATE_LABELS[gate]} {int(streaks.get(gate) or 0)}"
            for gate in GATES),
    ])
    sample = state.get("enrich_sample")
    if isinstance(sample, dict) and sample:
        lines.append("- Enrich sample awaiting review: " + ", ".join(
            f"{category}={'/'.join(ids)}"
            for category, ids in sorted(sample.items())))
    passed, total = content_counts
    if total:
        lines.append(
            f"- Enrich content samples: {passed}/{total} passed "
            f"({content_ratio:.1%})")
    for gate in GATES:
        review = manual_reviews.get(gate)
        if isinstance(review, dict):
            lines.append(
                f"- Manual {gate} review: **{review.get('status')}** — "
                "reviewed against the retained rollout artifact")
    return "\n".join(lines) + "\n"


def _states_by_date(comments):
    """Index the earliest trusted state per date, oldest comment winning."""
    states = {}
    for comment in sorted(comments, key=lambda row: int(row.get("id") or 0)):
        parsed = parse_machine_state(comment)
        if parsed is not None and parsed["date"] not in states:
            states[parsed["date"]] = parsed
    return states


def window_start(states, date):
    """First date of the observation window the given date belongs to.

    The window restarts whenever the shared runtime fingerprint changes, which
    is exactly when pre-change and post-change evidence must not be mixed.
    """
    ordered = sorted(states, key=lambda row: str(row.get("date") or ""))
    start = str(date)
    previous = ""
    for state in ordered:
        current_date = str(state.get("date") or "")
        if current_date > str(date):
            break
        fingerprints = state.get("fingerprints")
        fingerprints = fingerprints if isinstance(fingerprints, dict) else {}
        runtime = fingerprints.get("runtime") or ""
        if not previous or (runtime and runtime != previous):
            start = current_date
        if runtime:
            previous = runtime
    return start


def _window_states(states, date):
    start = window_start(states, date)
    return [state for state in states
            if start <= str(state.get("date") or "") <= str(date)]


def _finalize(states_by_date, date, updated):
    """Recompute streaks over the whole ledger and render the daily comment."""
    states_by_date[str(date)] = updated
    values = list(states_by_date.values())
    updated["streaks"] = compute_streaks(values)
    ratio, passed, total = enrich_content_ratio(_window_states(values, date))
    return render_comment(updated, content_ratio=ratio,
                          content_counts=(passed, total))


def shadow_status(client=None, *, issue_number=None):
    """Report shadow as capped: auto runs stop, manual `force` still works.

    Retired with ADR 0016. The accumulated sample is treated as sufficient, so
    this no longer compares streaks against unlock targets -- under the former
    rule a runtime-fingerprint change zeroed every clock, the targets were
    therefore unreachable, and `shadow_mode:auto` would have run a second full
    pipeline every single day with no terminating condition.

    Deliberately does no network I/O. The verdict is now a constant, so reading
    the issue could only change whether this call *fails*: the workflow treats a
    non-zero exit as "status unknown" and fail-opens into a paid shadow run, so
    one rate-limited API call would buy a full extra pipeline for a verdict that
    was never in doubt. `client` and `issue_number` are accepted and ignored to
    keep the call signature stable.
    """
    return {
        "status": "accepted",
        "needed": False,
        "accepted": True,
        "streaks": {gate: 0 for gate in GATES},
    }


def sync_issue(client, *, issue_number, date, incoming=None, attempt_builder=None):
    """Idempotently create or update the trusted comment for one date."""
    issue = client.get_issue(issue_number)
    if str(issue.get("state") or "").lower() != "open":
        return {"status": "closed", "comment_id": None}

    comments = client.list_comments(issue_number)
    current_comment = find_daily_comment(comments, date)
    current_state = (parse_machine_state(current_comment)
                     if current_comment is not None else None)
    states_by_date = _states_by_date(comments)
    if incoming is None:
        if attempt_builder is None:
            raise ValueError("sync_issue needs incoming or attempt_builder")
        prior = [state for name, state in states_by_date.items() if name != str(date)]
        incoming = attempt_builder(window_start(prior + [{"date": str(date)}], date))
    attempts = merge_attempts(
        current_state.get("attempts", []) if current_state else [], incoming)
    updated = build_daily_state(
        date, attempts,
        manual_reviews=(current_state or {}).get("manual_reviews"))
    body = _finalize(states_by_date, date, updated)

    if current_comment is None:
        response = client.create_comment(issue_number, body)
        return {"status": "created", "comment_id": response.get("id")}
    response = client.update_comment(current_comment["id"], body)
    return {"status": "updated", "comment_id": response.get("id")}


def build_gap_state(date):
    """State for a Beijing date whose daily run never reached the ledger.

    A day with no output is not a failed day: every gate freezes rather than
    resetting, and no publication verdict is claimed for work that never ran.
    """
    return {
        "version": STATE_VERSION,
        "date": str(date),
        "attempts": [],
        "aggregate": {"publication": "neutral",
                      **{gate: "neutral" for gate in GATES}},
        "fingerprints": {"runtime": "", "trajectory_ui": ""},
        "streaks": {gate: 0 for gate in GATES},
        "enrich_sample": {},
        "gap": True,
    }


def heartbeat_issue(client, *, issue_number, date):
    """Record a neutral gap row when a date produced no daily ledger comment."""
    issue = client.get_issue(issue_number)
    if str(issue.get("state") or "").lower() != "open":
        return {"status": "closed", "comment_id": None}

    comments = client.list_comments(issue_number)
    existing = find_daily_comment(comments, date)
    states_by_date = _states_by_date(comments)
    if existing is not None:
        streaks = compute_streaks(list(states_by_date.values()))
        return {"status": "present", "comment_id": existing.get("id"),
                "streaks": streaks}

    updated = build_gap_state(date)
    body = _finalize(states_by_date, date, updated)
    response = client.create_comment(issue_number, body)
    return {"status": "gap_recorded", "comment_id": response.get("id"),
            "streaks": updated["streaks"]}


def manual_review_issue(client, *, issue_number, date, gate, status,
                        run_id, run_attempt, samples_passed=None,
                        samples_total=None):
    """Apply an evidenced manual verdict through the trusted bot comment."""
    issue = client.get_issue(issue_number)
    if str(issue.get("state") or "").lower() != "open":
        return {"status": "closed", "comment_id": None}

    comments = client.list_comments(issue_number)
    current_comment = find_daily_comment(comments, date)
    current_state = (parse_machine_state(current_comment)
                     if current_comment is not None else None)
    if current_comment is None or current_state is None:
        raise ValueError(f"no trusted rollout state exists for {date}")
    updated = apply_manual_review(
        current_state, gate=gate, status=status,
        run_id=run_id, run_attempt=run_attempt,
        samples_passed=samples_passed, samples_total=samples_total)
    body = _finalize(_states_by_date(comments), date, updated)
    response = client.update_comment(current_comment["id"], body)
    return {"status": "updated", "comment_id": response.get("id")}


class GitHubClient:
    """Small GitHub Issues REST client; aggregation remains independently testable."""

    def __init__(self, repository, token, *, opener=None):
        if not re.fullmatch(r"[^/\s]+/[^/\s]+", str(repository or "")):
            raise ValueError("GITHUB_REPOSITORY must be owner/repo")
        if not str(token or "").strip():
            raise ValueError("GITHUB_TOKEN is required")
        self.base_url = f"https://api.github.com/repos/{repository}"
        self.token = str(token).strip()
        self.opener = opener or urllib.request.urlopen

    def _request(self, method, endpoint, payload=None):
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/{endpoint}", data=data, method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "daily-news-rollout-ledger",
                "X-GitHub-Api-Version": "2022-11-28",
            })
        with self.opener(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_issue(self, issue_number):
        return self._request("GET", f"issues/{int(issue_number)}")

    def list_comments(self, issue_number):
        comments = []
        page = 1
        while True:
            rows = self._request(
                "GET", f"issues/{int(issue_number)}/comments?per_page=100&page={page}")
            if not isinstance(rows, list):
                raise ValueError("GitHub comments response must be a list")
            comments.extend(rows)
            if len(rows) < 100:
                return comments
            page += 1

    def create_comment(self, issue_number, body):
        return self._request(
            "POST", f"issues/{int(issue_number)}/comments", {"body": body})

    def update_comment(self, comment_id, body):
        return self._request(
            "PATCH", f"issues/comments/{int(comment_id)}", {"body": body})


def beijing_date(value):
    """Reject anything that is not a real YYYY-MM-DD date.

    The date is interpolated into the HTML comment marker of a ledger entry
    written under the workflow bot's identity. Without this check a crafted
    `--date` closes the comment early and injects arbitrary content — or a
    second state block — into the audit record the acceptance gates trust.
    Workflow inputs reach this argument directly, so validate at the boundary.
    """
    text = str(value or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise argparse.ArgumentTypeError(
            "date must be a real calendar date in YYYY-MM-DD format")
    try:
        datetime.date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "date must be a real calendar date in YYYY-MM-DD format") from exc
    return text


def parse_cli_args(argv=None):
    parser = argparse.ArgumentParser(description="Update the rollout Issue ledger")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check-open")
    check.add_argument("--issue", type=int, default=15)
    shadow = subparsers.add_parser("shadow-status")
    shadow.add_argument("--issue", type=int, default=15)
    heartbeat = subparsers.add_parser("heartbeat")
    heartbeat.add_argument("--issue", type=int, default=15)
    heartbeat.add_argument("--date", required=True, type=beijing_date)
    sync = subparsers.add_parser("sync")
    sync.add_argument("--issue", type=int, default=15)
    sync.add_argument("--date", required=True, type=beijing_date)
    sync.add_argument("--publication", required=True, choices=("success", "failure"))
    sync.add_argument("--publication-reason", default="")
    sync.add_argument("--report", default="")
    sync.add_argument("--shadow-summary", default="")
    sync.add_argument("--shadow-outcome", default="failure",
                      choices=("success", "failure", "accepted"))
    sync.add_argument("--quality-health", default="")
    sync.add_argument("--source-health", default="")
    sync.add_argument("--run-id", required=True)
    sync.add_argument("--run-attempt", required=True, type=int)
    sync.add_argument("--sha", required=True)
    manual = subparsers.add_parser("manual-review")
    manual.add_argument("--issue", type=int, default=15)
    manual.add_argument("--date", required=True, type=beijing_date)
    manual.add_argument("--gate", required=True, choices=GATES)
    manual.add_argument(
        "--status", required=True, choices=("pass", "fail", "neutral"))
    manual.add_argument("--run-id", required=True)
    manual.add_argument("--run-attempt", required=True, type=int)
    manual.add_argument("--samples-passed", type=int, default=None)
    manual.add_argument("--samples-total", type=int, default=None)
    return parser.parse_args(argv)


def _write_output(environ, name, value):
    target = str(environ.get("GITHUB_OUTPUT") or "").strip()
    if target:
        with Path(target).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def _load_report(path):
    if not str(path or "").strip():
        return None
    target = Path(path)
    if not target.is_file():
        return None
    try:
        report = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    return report if isinstance(report, dict) else None


def main(argv=None, *, environ=None, client_factory=GitHubClient):
    environ = os.environ if environ is None else environ
    args = parse_cli_args(argv)
    # shadow-status is answered without a client on purpose: it needs no network
    # I/O since ADR 0016, and constructing GitHubClient raises when the token or
    # GITHUB_REPOSITORY is absent. Any raise exits non-zero, which the workflow
    # reads as "status unknown" and fail-opens into a paid shadow run -- so a
    # missing env var must not be able to trigger one.
    if args.command == "shadow-status":
        result = shadow_status()
        _write_output(environ, "needed", str(result["needed"]).lower())
        _write_output(environ, "accepted", str(result["accepted"]).lower())
        _write_output(
            environ, "objectivity_shadow",
            result["streaks"]["objectivity_shadow"])
        _write_output(
            environ, "source_metrics",
            result["streaks"]["source_metrics"])
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return result
    client = client_factory(
        environ.get("GITHUB_REPOSITORY", ""), environ.get("GITHUB_TOKEN", ""))
    if args.command == "check-open":
        issue = client.get_issue(args.issue)
        is_open = str(issue.get("state") or "").lower() == "open"
        _write_output(environ, "open", str(is_open).lower())
        result = {"status": "open" if is_open else "closed", "open": is_open}
    elif args.command == "heartbeat":
        result = heartbeat_issue(
            client, issue_number=args.issue, date=args.date)
        if result["status"] == "gap_recorded":
            print(f"::warning::No daily ledger entry for {args.date}; "
                  "recorded a neutral gap row.")
    elif args.command == "sync":
        report = _load_report(args.report)
        shadow_summary = _load_report(args.shadow_summary)
        quality_health = _load_report(args.quality_health)
        source_health = _load_report(args.source_health)
        enrich_sample = (report or {}).get("enrich_sample")

        def attempt_builder(start):
            return build_attempt(
                report=report, publication=args.publication,
                publication_reason=args.publication_reason, run_id=args.run_id,
                run_attempt=args.run_attempt, sha=args.sha,
                enrich=evaluate_enrich(
                    quality_health, date=args.date, window_start=start),
                objectivity_shadow=evaluate_objectivity_shadow(
                    shadow_summary, shadow_outcome=args.shadow_outcome),
                source_metrics=evaluate_source_metrics(
                    source_health, shadow_summary, date=args.date,
                    shadow_outcome=args.shadow_outcome),
                enrich_sample=enrich_sample)

        result = sync_issue(
            client, issue_number=args.issue, date=args.date,
            attempt_builder=attempt_builder)
    else:
        result = manual_review_issue(
            client, issue_number=args.issue, date=args.date,
            gate=args.gate, status=args.status,
            run_id=args.run_id, run_attempt=args.run_attempt,
            samples_passed=args.samples_passed,
            samples_total=args.samples_total)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
