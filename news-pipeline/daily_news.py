# -*- coding: utf-8 -*-
"""
每日新闻驾驶舱 - 聚合管线
用法:
    python daily_news.py              # 正常跑：抓取 -> LLM 处理 -> 生成当日数据
    python daily_news.py --dry-run    # 只抓取不调 LLM，检查各源是否正常
    python daily_news.py --date 2026-07-03   # 指定输出日期（默认今天）

流程:
    1. 抓取 sources.yaml 里所有启用的源（RSS + AI HOT API）
    2. 时间窗过滤、清洗、限量
    3. 预筛（便宜模型）：丢弃垃圾/无关条目，主模型只处理幸存者
    4. LLM 阶段A：去重聚类 + 分类 + 五维分项打分（影响面/新颖/实质/佐证/持续）
    5. 代码合成最终分：维度加权 + 来源可信度 + 信源层级乘数(T1/T1.5/T2) + 兴趣权重
       阈值制精选：过线才进精选（含上下限与五类保底），不硬凑固定条数
       硬约束：纯舆论源事件封顶在阈值之下，只能进"更多资讯"
    6. LLM 阶段B：对精选生成 一句话摘要 / 来龙或起因 / 现状 / 走向 / 状态标记
    7. 写入 data/daily/YYYY-MM-DD.js 和 data/manifest.js（前端直接读）
    8. 更新 data/source_health.json：滚动记录 14 天各源抓取状态，
       连续 3 天抓取失败的源发 GitHub Actions ::warning:: 注解
"""
import argparse
import concurrent.futures
import copy
from contextlib import contextmanager
import hashlib
import html
import importlib.util
import ipaddress
import json
import math
import queue
from email.utils import format_datetime
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from statistics import median
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import feedparser
import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util import Timeout

# Windows 控制台中文输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

CATEGORIES = ["ai", "tech", "finance", "society", "world"]
CAT_NAMES = {"ai": "AI", "tech": "互联网/科技", "finance": "财经",
             "society": "社会", "world": "国际"}
TYPE_NAMES = {"fact": "事实源", "analysis": "分析源", "opinion": "舆论源"}
STATUS_SET = {"已确认", "发展中", "有争议", "仅传言"}
TIER_ORDER = {"T1": 0, "T1.5": 1, "T2": 2}
DIMS = ["impact", "novelty", "substance", "evidence", "durability"]
QUALITY_NEUTRAL_EVIDENCE = 5.0
QUALITY_EXTENSION_FIELDS = ("context", "watch", "watch_detail", "detail", "claims")
QUALITY_EXTENSION_FIELDS_V2 = (
    "why", "context", "watch", "watch_detail", "detail", "claims",
)
QUALITY_EXTENSION_FIELDS_V1 = (
    "why", "context", "significance", "watch", "detail", "claims",
)
OBJECTIVITY_FIELDS = ("title", "summary", "context", "watch", "watch_detail", "detail")
REMOVED_FIELD_COUNTS_VERSION = 3
# 读者可见字段被删掉的四种原因。分项计数只为回答「详情页的空块是闸门删的还是
# 生成端没写」，不改任何判定。
REMOVAL_REASONS = (
    "evidence_copy", "audit_unsupported", "claim_unsupported",
    "generation_invalid",
)
REMOVAL_REASONS_V1 = (
    "evidence_copy", "audit_unsupported", "claim_unsupported",
)
GENERATED_TITLE_MAX_CHARS = 120
SOURCE_TITLE_MAX_CHARS = 300
OBJECTIVITY_FIELD_LIMITS = {
    "title": GENERATED_TITLE_MAX_CHARS,
    "summary": 100,
    "why": 80,
    "context": 80,
    "watch": 90,
    "detail": 800,
}
FULLTEXT_OBJECTIVITY_FIELD_LIMITS = {
    **OBJECTIVITY_FIELD_LIMITS,
    "context": 240,
    "watch": 90,
    "watch_detail": 260,
    "detail": 1200,
}
OBJECTIVITY_COPY_MIN_LENGTHS = {
    "title": 24,
    "summary": 48,
    "why": 48,
    "context": 48,
    "watch": 40,
    "watch_detail": 60,
    "detail": 80,
    "claims": 60,
}
TRAJECTORY_RECAP_STATUS = frozenset({"兑现", "部分兑现", "未兑现", "反转"})
EVIDENCE_RISK_FLAGS = (
    "politics_geopolitics", "armed_conflict", "allegation_legal",
    "public_safety_health", "high_impact_numbers",
)
TRUSTED_PROVENANCE = {"original", "official", "first_party"}
ARTICLE_MAX_BYTES = 2 * 1024 * 1024
ARTICLE_MAX_CHARS = 4000
ARTICLE_MIN_CHARS = 200
ARTICLE_ATTEMPT_TIMEOUT = 10.0
ARTICLE_ATTEMPT_WORKERS = 6
_ARTICLE_ATTEMPT_SLOTS = threading.BoundedSemaphore(ARTICLE_ATTEMPT_WORKERS)
_ARTICLE_CLEANUP_SLOTS = threading.BoundedSemaphore(ARTICLE_ATTEMPT_WORKERS)
# 单价（美元 / 百万 token），按模型名索引。step-explore 的 0 来自当前账号免费授权，
# 不是公开长期定价；未知模型必须保持 unknown，不能静默伪装成免费。
LLM_PRICE_USD_PER_MTOK = {
    "deepseek-v4-flash": {
        "input_miss": 0.14,
        "input_hit": 0.0028,
        "output": 0.28,
    },
    "step-explore": {
        "input_miss": 0.0,
        "input_hit": 0.0,
        "output": 0.0,
    },
}
LLM_USAGE_FIELDS = (
    "llm_calls",
    "llm_input_tokens",
    "llm_cached_input_tokens",
    "llm_output_tokens",
    "llm_cost_usd",
    "llm_cost_known",
)

CROSS_SOURCE_NOVELTY_FIELDS = (
    "cross_source_novelty_candidates",
    "cross_source_material_additions",
    "cross_source_restatements",
    "cross_source_novelty_failures",
    "cross_source_novelty_calls",
    "cross_source_novelty_deferred",
    "cross_source_novelty_budget_exhausted",
)
CROSS_SOURCE_NOVELTY_MAX_PROMPT_CHARS = 64_000

ROLLOUT_QUALITY_FIELDS = {
    "article_fetch_attempts", "article_fetch_successes", "article_fetch_retries",
    "article_http_requests", "evidence_fulltext_sources", "evidence_snippet_sources",
    "high_risk_single_publisher", "corroboration_candidates", "corroboration_matches",
    "objectivity_audited", "objectivity_repaired", "objectivity_degraded",
    "high_risk_demoted", "cause_evidence_rejected", "cause_speculation_rejected",
    "detail_evidence_rich", "detail_evidence_limited", "detail_evidence_snippet",
    "detail_rich_target_met", "detail_rich_target_rate",
    "detail_final_median_chars",
}


def new_quality_stats():
    """Create the stable, JSON-safe daily quality summary."""
    return {
        "audited_events": 0,
        "split_events": 0,
        "removed_fields": 0,
        # 模型返回形状的三个诊断维度：阶段A 跳过的单个非法元素、阶段A 整批降级
        # 次数、以及所有调用点上「整体不可用」的次数。只做留痕，不参与任何判定
        # 或验收门，见 docs/adr/0012。
        "triage_invalid_rows": 0,
        "triage_fallback_batches": 0,
        "model_unusable_responses": 0,
        "enrichment_audited_events": 0,
        "duplicate_audited_events": 0,
        "same_day_duplicates_merged": 0,
        "duplicate_audit_failures": 0,
        "same_day_candidate_pairs": 0,
        "same_day_bridge_batches": 0,
        "same_day_reconcile_calls": 0,
        "same_day_deferred_batches": 0,
        "same_day_budget_exhausted": False,
        "event_lines_audited": 0,
        "event_lines_merged": 0,
        "event_line_audit_failures": 0,
        "cross_day_duplicates": 0,
        "material_updates": 0,
        "update_judge_failures": 0,
        "article_fetch_attempts": 0,
        "article_fetch_successes": 0,
        "article_fetch_retries": 0,
        "article_http_requests": 0,
        "evidence_fulltext_sources": 0,
        "evidence_snippet_sources": 0,
        "high_risk_single_publisher": 0,
        "corroboration_candidates": 0,
        "corroboration_matches": 0,
        "objectivity_audited": 0,
        "objectivity_repaired": 0,
        "objectivity_degraded": 0,
        "high_risk_demoted": 0,
        "cause_evidence_rejected": 0,
        "cause_speculation_rejected": 0,
        "detail_evidence_rich": 0,
        "detail_evidence_limited": 0,
        "detail_evidence_snippet": 0,
        "detail_rich_target_met": 0,
        "detail_rich_target_rate": 0.0,
        "detail_final_median_chars": 0,
        "enrich_out_of_batch_idx": 0,
        # removed_fields 的两维分项：按字段名、按删除原因。总数仍以 removed_fields
        # 为准，两个分项之和必须与它相等——诊断用，不参与任何判定或验收门。
        "removed_field_counts_version": REMOVED_FIELD_COUNTS_VERSION,
        "removed_field_counts": {field: 0 for field in QUALITY_EXTENSION_FIELDS},
        "removed_field_reasons": {reason: 0 for reason in REMOVAL_REASONS},
        "degraded": False,
    }


def new_cross_source_novelty_stats():
    """Create operational metrics kept out of the reader-facing daily payload."""
    return {
        "cross_source_novelty_candidates": 0,
        "cross_source_material_additions": 0,
        "cross_source_restatements": 0,
        "cross_source_novelty_failures": 0,
        "cross_source_novelty_calls": 0,
        "cross_source_novelty_deferred": 0,
        "cross_source_novelty_budget_exhausted": False,
        "degraded": False,
    }


def count_removed_field(quality, field, reason):
    """Increment the removal total together with both breakdown dimensions.

    Going through one helper is what keeps ``removed_fields`` equal to the sum of
    either breakdown; incrementing the total by hand anywhere would break that.
    """
    quality["removed_fields"] = int(quality.get("removed_fields", 0)) + 1
    for key, bucket in (("removed_field_counts", field),
                        ("removed_field_reasons", reason)):
        counts = quality.get(key)
        if not isinstance(counts, dict):
            counts = {}
            quality[key] = counts
        counts[bucket] = int(counts.get(bucket, 0)) + 1


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _is_valid_http_url(value):
    """Return whether a reader-facing URL is a well-formed HTTP(S) URL."""
    raw = str(value or "")
    if not raw or raw != raw.strip() or re.search(r"\s", raw):
        return False
    try:
        parts = urlsplit(raw)
        parts.port
    except ValueError:
        return False
    return (
        parts.scheme.lower() in {"http", "https"}
        and bool(parts.hostname)
    )
_RSSHUB_KEY_RE = re.compile(r"(?i)([?&]key=)[^&\s]+")


def redact(text):
    """Strip the RSSHub access key (and instance host) out of anything logged.

    ``resolve_rsshub_sources`` puts RSSHUB_KEY in the query string, and requests
    exceptions embed the full URL. On a public repository the only thing standing
    between that and the Actions log is GitHub's secret masking — which stops
    working the moment the value is escaped or truncated. Redact at the source.
    """
    out = _RSSHUB_KEY_RE.sub(r"\1[redacted]", str(text))
    base = os.environ.get("RSSHUB_BASE", "").strip().rstrip("/")
    if base:
        # requests 的异常里出现的往往是裸主机名（HTTPSConnectionPool(host='...')），
        # 不是配置里那个带 scheme 的完整地址，两种形态都要盖掉。
        host = urlsplit(base if "//" in base else f"//{base}").hostname or ""
        for needle in sorted({base, host}, key=len, reverse=True):
            if needle:
                out = out.replace(needle, "[rsshub]")
    key = os.environ.get("RSSHUB_KEY", "").strip()
    if key:
        out = out.replace(key, "[redacted]")
    return out


def parse_iso_date(value):
    text = str(value or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD")
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be a real calendar date") from exc
    return text


def parse_cli_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只抓取，不调 LLM")
    parser.add_argument("--date", type=parse_iso_date, default=None,
                        help="输出日期 YYYY-MM-DD，默认今天")
    parser.add_argument(
        "--objectivity-shadow", action="store_true",
        help="运行完整证据/客观性路径，但不写入公开数据",
    )
    return parser.parse_args(argv)


def resolve_run_policy(cfg, args):
    """Resolve the explicit rollout gate without mutating configuration."""
    configured = str((cfg.get("objectivity") or {}).get("mode") or "interim").strip().lower()
    if configured not in {"interim", "active"}:
        raise ValueError("objectivity.mode must be interim or active")
    mode = "shadow" if bool(getattr(args, "objectivity_shadow", False)) else configured
    return {
        "mode": mode,
        "full_objectivity": mode in {"shadow", "active"},
        "writes_public_data": mode != "shadow",
    }


def prepare_run_data_dir(policy, environ=None):
    """Return the public directory or an owned snapshot directory for shadow."""
    environ = os.environ if environ is None else environ
    configured = str(environ.get("DATA_DIR") or "").strip()
    public_dir = Path(configured) if configured else ROOT / "data"
    if not policy["writes_public_data"]:
        owner = tempfile.TemporaryDirectory(prefix="news-objectivity-shadow-")
        shadow_dir = Path(owner.name)
        try:
            if public_dir.exists():
                shutil.copytree(public_dir, shadow_dir, dirs_exist_ok=True)
        except Exception:
            owner.cleanup()
            raise
        return shadow_dir, owner
    return public_dir, None


@contextmanager
def managed_run_data_dir(policy, environ=None):
    """Install a shadow snapshot for the whole run and always restore/clean it."""
    environ = os.environ if environ is None else environ
    run_dir, owner = prepare_run_data_dir(policy, environ)
    if owner is None:
        yield run_dir
        return
    existed = "DATA_DIR" in environ
    previous = environ.get("DATA_DIR")
    environ["DATA_DIR"] = str(run_dir)
    try:
        yield run_dir
    finally:
        if existed:
            environ["DATA_DIR"] = previous
        else:
            environ.pop("DATA_DIR", None)
        owner.cleanup()


def _rollout_output_enabled(cfg):
    mode = str(cfg.get("_objectivity_runtime_mode")
               or (cfg.get("objectivity") or {}).get("mode") or "interim").lower()
    return mode in {"shadow", "active"}


def _quality_for_output(quality, include_rollout):
    result = {**new_quality_stats(), **(quality or {})}
    if not include_rollout:
        for field in ROLLOUT_QUALITY_FIELDS:
            result.pop(field, None)
    return result


def _strip_rollout_item_fields(rows):
    for row in rows:
        row.pop("evidence", None)
        for source in row.get("sources") or []:
            if isinstance(source, dict):
                source.pop("evidence_basis", None)
                source.pop("evidence_chain", None)
    return rows


def build_shadow_summary(
        selected_before, selected_after, items, quality, runtime_seconds,
        usage=None):
    """Build an allow-listed aggregate; article text and configuration never enter it."""
    basis_counts = {"fulltext": 0, "mixed": 0, "snippet": 0}
    chain_counts = {}
    source_counts = {}
    high_risk = 0
    single_source = 0
    high_risk_single_source = 0
    for event in selected_before:
        is_high_risk = _event_is_high_risk(event)
        if is_high_risk:
            high_risk += 1
        evidence = event.get("evidence") if isinstance(event.get("evidence"), dict) else {}
        basis = evidence.get("basis") if evidence.get("basis") in basis_counts else "snippet"
        basis_counts[basis] += 1
        publishers = evidence.get("publisher_count", 0)
        if isinstance(publishers, int) and not isinstance(publishers, bool) and publishers <= 1:
            single_source += 1
            if is_high_risk:
                high_risk_single_source += 1
        chains = evidence.get("independent_chain_count", 0)
        if not isinstance(chains, int) or isinstance(chains, bool) or chains < 0:
            chains = 0
        chain_counts[str(chains)] = chain_counts.get(str(chains), 0) + 1
        for index in _serialized_source_ids(event, items, limit=4):
            source = str(items[index].get("source") or "unknown").strip() or "unknown"
            source_counts[source] = source_counts.get(source, 0) + 1
    total_sources = sum(source_counts.values())
    concentration = [
        {"source": source, "reference_count": count,
         "reference_share": round(count / total_sources, 4) if total_sources else 0.0}
        for source, count in sorted(source_counts.items(), key=lambda row: (-row[1], row[0]))[:10]
    ]
    selected_after_ids = {id(event) for event in selected_after}
    safe_usage = {
        key: usage[key] for key in LLM_USAGE_FIELDS
        if key in (usage or {})
    }
    return {
        "mode": "shadow",
        "runtime_seconds": round(float(runtime_seconds), 3),
        "selected_before_audit": len(selected_before),
        "selected_after_audit": len(selected_after),
        "audited_candidate_count": int(quality.get("objectivity_audited", 0)),
        "demoted_from_selected": sum(
            1 for event in selected_before if id(event) not in selected_after_ids),
        "high_risk_selected_before_audit": high_risk,
        "single_source_selected_before_audit": single_source,
        "high_risk_single_source_count": high_risk_single_source,
        "high_risk_single_source_rate": round(
            high_risk_single_source / high_risk, 4) if high_risk else 0.0,
        "evidence_basis": basis_counts,
        "fetch": {
            "attempts": int(quality.get("article_fetch_attempts", 0)),
            "successes": int(quality.get("article_fetch_successes", 0)),
            "retries": int(quality.get("article_fetch_retries", 0)),
        },
        "objectivity": {
            "repaired": int(quality.get("objectivity_repaired", 0)),
            "degraded": int(quality.get("objectivity_degraded", 0)),
        },
        "detail_quality": {
            "evidence_rich": int(quality.get("detail_evidence_rich", 0)),
            "evidence_limited": int(quality.get("detail_evidence_limited", 0)),
            "evidence_snippet": int(quality.get("detail_evidence_snippet", 0)),
            "final_median_chars": int(
                quality.get("detail_final_median_chars", 0)),
            "rich_target_met": int(quality.get("detail_rich_target_met", 0)),
            "rich_target_rate": float(
                quality.get("detail_rich_target_rate", 0.0)),
        },
        "independent_chain_distribution": dict(sorted(chain_counts.items(), key=lambda row: int(row[0]))),
        "source_reference_concentration": concentration,
        "llm_usage": safe_usage,
    }


def write_shadow_summary(summary, environ=None):
    """Persist the allow-listed shadow aggregate so the rollout ledger can read it.

    Mirrors ROLLOUT_EVIDENCE_PATH: without the env var nothing is written, so
    local runs stay unchanged. `build_shadow_summary` already restricts the
    payload to counts and rates, so no article text can reach this file.
    """
    environ = os.environ if environ is None else environ
    target = str(environ.get("SHADOW_SUMMARY_PATH") or "").strip()
    if not target:
        return False
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    return True


def public_item_id(event, tier):
    """The identifier `event_to_item` will publish for this event.

    Kept as the single source of the formula so the enrich sample can name
    items before the daily payload exists.
    """
    ids = event.get("ids") if isinstance(event, dict) else None
    if not isinstance(ids, list) or not ids:
        return ""
    return f"{tier}-{ids[0]}"


def build_enrich_sample(picked, date_str):
    """Choose one item per non-empty category as that day's enrich review list.

    The choice is derived from the date so a same-day rerun names the same
    items and the human review list never shifts underneath the ledger.
    Selected events arrive here as raw events, whose public identifier is only
    minted later in `event_to_item`, so derive the same `pick` identifier
    rather than reading an `id` the event never carries.
    """
    by_category = {}
    for item in picked or []:
        category = str(item.get("category") or "")
        item_id = str(item.get("id") or "") or public_item_id(item, "pick")
        if category in CATEGORIES and item_id:
            by_category.setdefault(category, []).append(item_id)
    sample = {}
    for category, ids in by_category.items():
        ordered = sorted(set(ids))
        digest = hashlib.sha1(
            f"{date_str}:{category}".encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        sample[category] = [ordered[int(digest, 16) % len(ordered)]]
    return dict(sorted(sample.items()))


def append_github_shadow_summary(summary, environ=None):
    environ = os.environ if environ is None else environ
    target = str(environ.get("GITHUB_STEP_SUMMARY") or "").strip()
    if not target:
        return False
    basis = summary["evidence_basis"]
    fetch = summary["fetch"]
    audit = summary["objectivity"]
    lines = [
        "## Objectivity shadow",
        "",
        f"- runtime: {summary['runtime_seconds']:.3f}s",
        (f"- selected before/after audit: {summary['selected_before_audit']}/"
         f"{summary['selected_after_audit']}"),
        (f"- audited candidates/demoted from selected: {summary['audited_candidate_count']}/"
         f"{summary['demoted_from_selected']}"),
        (f"- high-risk/single-source selected before audit: "
         f"{summary['high_risk_selected_before_audit']}/"
         f"{summary['single_source_selected_before_audit']}"),
        (f"- high-risk single-source: {summary['high_risk_single_source_count']} "
         f"({summary['high_risk_single_source_rate']:.1%})"),
        f"- fulltext/mixed/snippet: {basis['fulltext']}/{basis['mixed']}/{basis['snippet']}",
        f"- fetch attempts/successes/retries: {fetch['attempts']}/{fetch['successes']}/{fetch['retries']}",
        f"- repaired/degraded: {audit['repaired']}/{audit['degraded']}",
        "- independent chains: " + json.dumps(
            summary["independent_chain_distribution"], ensure_ascii=False, sort_keys=True),
        "- source reference concentration: " + ", ".join(
            f"{row['source']}={row['reference_count']} ({row['reference_share']:.1%})"
            for row in summary["source_reference_concentration"]),
        "",
    ]
    with Path(target).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return True


def append_github_selection_summary(summary, environ=None):
    """Append allow-listed selection metrics to a GitHub Actions step summary."""
    environ = os.environ if environ is None else environ
    target = str(environ.get("GITHUB_STEP_SUMMARY") or "").strip()
    if not target:
        return False
    category_counts = summary.get("category_counts") or {}
    qualified_supply = summary.get("qualified_supply") or {}
    lines = [
        "## News selection",
        "",
        (f"- threshold: {int(summary['threshold'])} "
         f"({summary['threshold_source']}; {int(summary['history_days'])} history days)"),
        f"- quality floor: {int(summary['quality_floor'])}",
        f"- picked: {int(summary['picked_count'])}",
        "- categories: " + ", ".join(
            f"{cat}={int(category_counts.get(cat, 0))}" for cat in CATEGORIES),
        "- qualified supply: " + ", ".join(
            f"{cat}={int(qualified_supply.get(cat, 0))}" for cat in CATEGORIES),
        (f"- reserved/below-threshold reserved: {int(summary['reserved_count'])}/"
         f"{int(summary['below_threshold_reserved'])}"),
        f"- over-threshold secondary: {int(summary['over_threshold_secondary'])}",
        "",
    ]
    with Path(target).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return True


def emit_rollout_evidence(date_str, policy, runtime_seconds, selection_stats,
                          trajectory_health, review_cases, data_dir,
                          config, enrich_sample=None, enrich_review_cases=None,
                          environ=None):
    """Write acceptance evidence without coupling it to publication output."""
    environ = os.environ if environ is None else environ
    if not str(environ.get("ROLLOUT_EVIDENCE_PATH") or "").strip():
        return False
    try:
        import rollout_validation
    except ModuleNotFoundError:
        module_path = ROOT / "rollout_validation.py"
        spec = importlib.util.spec_from_file_location(
            "daily_news_rollout_validation", module_path)
        rollout_validation = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = rollout_validation
        spec.loader.exec_module(rollout_validation)

    evidence = rollout_validation.build_rollout_evidence(
        date_str=date_str,
        mode=policy["mode"],
        runtime_seconds=runtime_seconds,
        selection=selection_stats,
        trajectory=trajectory_health,
        review_cases=review_cases,
        runtime_paths=[
            Path(__file__),
            Path(rollout_validation.__file__),
            ROOT / "article_extractor.py",
            ROOT / "requirements.txt",
        ],
        trajectory_ui_paths=[
            ROOT.parent / "source" / "news" / "js" / "reports.js",
            ROOT.parent / "source" / "news" / "news.css",
        ],
        config=config,
        enrich_sample=enrich_sample or {},
        enrich_review_cases=enrich_review_cases or [],
    )
    return rollout_validation.write_rollout_evidence(
        evidence, data_dir=data_dir, environ=environ)


# ----------------------------------------------------------------
# 1. 抓取
# ----------------------------------------------------------------

def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def http_get(url, timeout=20, retries=2, backoff=1.5):
    """带指数退避的 GET；全部尝试失败才抛。retries 指额外重试次数。
    治 AIHOT 连接重置这类偶发失败——单次 requests.get 一挂整源归零。"""
    last = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    raise last


def http_post(url, data=None, timeout=20, retries=2, backoff=1.5, headers=None):
    """带指数退避的 POST，仅用于读取公开数据端点。"""
    last = None
    req_headers = {"User-Agent": UA}
    req_headers.update(headers or {})
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, data=data, headers=req_headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    raise last


class ArticleEvidenceError(ValueError):
    """Permanent article validation/extraction failure; callers use RSS fallback."""


def _public_article_target(url, resolver=socket.getaddrinfo):
    """Return a normalized URL and a validated IP that the transport must pin."""
    parts = urlsplit(str(url or ""))
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ArticleEvidenceError("article URL must be public HTTP/HTTPS")
    try:
        addresses = [ipaddress.ip_address(parts.hostname)]
    except ValueError:
        try:
            rows = resolver(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80),
                            type=socket.SOCK_STREAM)
            addresses = [ipaddress.ip_address(row[4][0]) for row in rows]
        except Exception as exc:
            raise ArticleEvidenceError("article hostname did not resolve") from exc
    if not addresses or any(not addr.is_global for addr in addresses):
        raise ArticleEvidenceError("article target is not public")
    return urlunsplit(parts), str(addresses[0])


def _public_article_url(url, resolver=socket.getaddrinfo):
    """Compatibility helper for callers that only need URL validation."""
    return _public_article_target(url, resolver)[0]


def _schedule_article_cleanup(closer):
    """Schedule best-effort cleanup without ever blocking or raising to the caller."""
    if closer is None or not _ARTICLE_CLEANUP_SLOTS.acquire(blocking=False):
        return False

    def cleanup():
        try:
            closer()
        except BaseException:
            pass
        finally:
            _ARTICLE_CLEANUP_SLOTS.release()

    worker = threading.Thread(
        target=cleanup, name="article-evidence-cleanup", daemon=True)
    try:
        worker.start()
    except BaseException:
        _ARTICLE_CLEANUP_SLOTS.release()
        return False
    return True


class _ArticleAttemptControl:
    """Thread-safe cancellation and live transport cleanup for one attempt."""

    def __init__(self):
        self.cancelled = threading.Event()
        self._lock = threading.Lock()
        self._closer = None

    def register_closer(self, closer):
        close_now = False
        with self._lock:
            if self.cancelled.is_set():
                close_now = True
            else:
                self._closer = closer
        if close_now:
            _schedule_article_cleanup(closer)

    def cancel_and_schedule_close(self):
        self.cancelled.set()
        with self._lock:
            closer = self._closer
            self._closer = None
        _schedule_article_cleanup(closer)


class PinnedIPAdapter(HTTPAdapter):
    """Connect to a validated IP while authenticating the original HTTPS host."""

    def __init__(self, pinned_ip, original_hostname, *args, **kwargs):
        self.pinned_ip = str(pinned_ip)
        self.original_hostname = str(original_hostname)
        super().__init__(*args, **kwargs)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(
            request, verify, cert)
        host_params["host"] = self.pinned_ip
        if host_params.get("scheme") == "https":
            pool_kwargs["server_hostname"] = self.original_hostname
            pool_kwargs["assert_hostname"] = self.original_hostname
        return self.poolmanager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)


def _pinned_article_get(url, pinned_ip, attempt_control=None, **kwargs):
    """Issue one direct request through a pool connected only to ``pinned_ip``."""
    parts = urlsplit(url)
    hostname = parts.hostname or ""
    default_port = 443 if parts.scheme == "https" else 80
    host_header = hostname if not parts.port or parts.port == default_port else f"{hostname}:{parts.port}"
    headers = dict(kwargs.pop("headers", {}) or {})
    headers.setdefault("Host", host_header)
    session = requests.Session()
    session.trust_env = False
    session.mount(f"{parts.scheme}://", PinnedIPAdapter(pinned_ip, hostname))
    if attempt_control is not None:
        attempt_control.register_closer(session.close)
    try:
        response = session.get(url, headers=headers, **kwargs)
    except Exception:
        session.close()
        raise
    original_close = response.close

    def close():
        try:
            original_close()
        finally:
            session.close()

    response.close = close
    if attempt_control is not None:
        attempt_control.register_closer(response.close)
    return response


def _extract_static_article(page_html, timeout=ARTICLE_ATTEMPT_TIMEOUT, command=None):
    """Extract static HTML beyond a process boundary that contains native crashes."""
    worker_command = command or [
        sys.executable,
        "-I",
        str(ROOT / "article_extractor.py"),
    ]
    try:
        completed = subprocess.run(
            worker_command,
            input=str(page_html or "").encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=max(0.001, float(timeout)),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ArticleEvidenceError("article extractor subprocess timed out") from exc
    except (OSError, ValueError) as exc:
        raise ArticleEvidenceError("article extractor subprocess could not start") from exc
    if completed.returncode != 0:
        raise ArticleEvidenceError(
            f"article extractor subprocess exited with code {completed.returncode}")
    return completed.stdout.decode("utf-8", errors="replace")


def _rss_evidence(item):
    text = "\n".join(part for part in (
        str(item.get("title") or "").strip(), str(item.get("desc") or "").strip()) if part)
    return re.sub(r"\s+", " ", text).strip()[:ARTICLE_MAX_CHARS]


def fetch_article_evidence(item, request_get=None, extractor=None, resolver=None, sleep=None,
                           clock=None, attempt_timeout=ARTICLE_ATTEMPT_TIMEOUT,
                           max_attempts=3):
    """Fetch one public static-HTML article, returning transient bounded evidence text.

    Redirects are followed manually so every target is revalidated. Permanent safety,
    media-type and size failures immediately fall back; transient HTTP failures get
    two retries (three total attempts).
    """
    request_get = request_get or _pinned_article_get
    extractor = extractor or _extract_static_article
    resolver = resolver or socket.getaddrinfo
    sleep = sleep or time.sleep
    clock = clock or time.monotonic
    if isinstance(attempt_timeout, bool) or not isinstance(attempt_timeout, (int, float)):
        raise ValueError("attempt_timeout must be a positive number")
    attempt_timeout = float(attempt_timeout)
    if attempt_timeout <= 0:
        raise ValueError("attempt_timeout must be a positive number")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts <= 0:
        raise ValueError("max_attempts must be a positive integer")
    fallback = {"evidence_basis": "snippet", "evidence_text": _rss_evidence(item),
                "attempts": 0, "retries": 0}
    initial_url = str(item.get("url") or "")

    attempts = 0
    retries_used = 0
    for retry in range(max_attempts):
        deadline = clock() + attempt_timeout
        request_count = [0]
        control = _ArticleAttemptControl()

        def require_time_remaining():
            remaining = deadline - clock()
            if control.cancelled.is_set() or remaining <= 0:
                raise requests.Timeout("article attempt exceeded wall-clock deadline")
            return remaining

        def operation():
            current_url = initial_url
            response = None
            try:
                for _redirect in range(6):
                    require_time_remaining()
                    current_url, pinned_ip = _public_article_target(current_url, resolver)
                    remaining = require_time_remaining()
                    request_count[0] += 1
                    request_timeout = Timeout(
                        total=remaining,
                        connect=min(3.0, remaining),
                        read=min(1.0, remaining),
                    )
                    response = request_get(
                        current_url, headers={"User-Agent": UA},
                        timeout=request_timeout, stream=True,
                        allow_redirects=False, pinned_ip=pinned_ip,
                        attempt_control=control)
                    control.register_closer(response.close)
                    require_time_remaining()
                    status = int(getattr(response, "status_code", 200))
                    if status in (301, 302, 303, 307, 308):
                        location = (getattr(response, "headers", {}) or {}).get("Location")
                        if not location:
                            raise ArticleEvidenceError("redirect without Location")
                        current_url = urljoin(current_url, location)
                        response.close()
                        response = None
                        continue
                    if status >= 400:
                        raise requests.HTTPError(f"article HTTP {status}")
                    headers = getattr(response, "headers", {}) or {}
                    content_type = str(headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
                    if content_type not in ("text/html", "application/xhtml+xml"):
                        raise ArticleEvidenceError("article response is not HTML")
                    length = headers.get("Content-Length")
                    if length and int(length) > ARTICLE_MAX_BYTES:
                        raise ArticleEvidenceError("article response exceeds 2 MiB")
                    body = bytearray()
                    for chunk in response.iter_content(chunk_size=65536):
                        require_time_remaining()
                        if not chunk:
                            continue
                        body.extend(chunk)
                        if len(body) > ARTICLE_MAX_BYTES:
                            raise ArticleEvidenceError("article response exceeds 2 MiB")
                    page_html = bytes(body).decode("utf-8", errors="replace")
                    require_time_remaining()
                    if extractor is _extract_static_article:
                        extracted = extractor(
                            page_html, timeout=require_time_remaining())
                    else:
                        extracted = extractor(page_html)
                    text = re.sub(r"\s+", " ", str(extracted or "")).strip()
                    require_time_remaining()
                    if len(text) < ARTICLE_MIN_CHARS:
                        raise ArticleEvidenceError("article extraction was too short")
                    return {"evidence_basis": "fulltext",
                            "evidence_text": text[:ARTICLE_MAX_CHARS]}
                raise ArticleEvidenceError("too many article redirects")
            finally:
                if response is not None:
                    response.close()

        result_queue = queue.Queue(maxsize=1)
        acquired = _ARTICLE_ATTEMPT_SLOTS.acquire(blocking=False)
        if acquired:
            def run_attempt():
                try:
                    result_queue.put((True, operation()))
                except BaseException as exc:
                    result_queue.put((False, exc))
                finally:
                    _ARTICLE_ATTEMPT_SLOTS.release()

            worker = threading.Thread(
                target=run_attempt, name="article-evidence-attempt", daemon=True)
            worker.start()
            try:
                wait_timeout = max(0.0, deadline - clock())
                succeeded, result = result_queue.get(timeout=wait_timeout)
            except queue.Empty:
                control.cancel_and_schedule_close()
                succeeded, result = False, requests.Timeout(
                    "article attempt exceeded wall-clock deadline")
        else:
            succeeded, result = False, requests.Timeout(
                "article attempt worker capacity exhausted")

        attempts += request_count[0]
        if succeeded:
            return {**result, "attempts": attempts, "retries": retries_used}
        if isinstance(result, ArticleEvidenceError):
            fallback["attempts"] = attempts
            fallback["retries"] = retries_used
            return fallback
        if retry < max_attempts - 1:
            retries_used += 1
            sleep(retry + 1)
    fallback["attempts"] = attempts
    fallback["retries"] = retries_used
    return fallback


def fetch_rss(src, window_start, max_items):
    """返回 (items, fetch_error)。fetch_error=True 表示抓取本身失败，
    与"源正常但窗口内无新文章"（items 为空、error=False）区分开。"""
    try:
        resp = http_get(src["url"])
        feed = feedparser.parse(resp.content)
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({redact(e)})")
        return [], True
    items = []
    for e in feed.entries:
        pub = parse_time(e)
        if pub is None or pub < window_start:
            continue
        title = strip_html(e.get("title", ""))
        link = e.get("link", "")
        if not title or not link:
            continue
        # 全文长度指标（仅深读频道估算阅读时长用，不存全文本身）
        content = ""
        if e.get("content"):
            try:
                content = strip_html(e["content"][0].get("value", ""))
            except Exception:
                content = ""
        if not content:
            content = strip_html(e.get("summary", e.get("description", "")))
        items.append({
            "title": title,
            "url": link,
            "desc": strip_html(e.get("summary", e.get("description", "")))[:400],
            "content_chars": len(re.sub(r"\s", "", content)),
            "content_words": len(content.split()),
            "time": pub.isoformat(),
            "source": src["name"],
            "source_id": src["id"],
            "source_type": src["source_type"],
            "tier": src.get("tier", "T2"),
            "credibility": src["credibility"],
        })
    items.sort(key=lambda x: x["time"], reverse=True)
    return items[:max_items], False


# AI HOT 分类 → 主题标签提示：enrich 阶段优先采纳，保证论文/技巧观点不被大类淹没。
# 值必须在 config.yaml 的 topic_tags 词表里，否则会被过滤掉。
AIHOT_TAG_HINT = {
    "ai-models": "模型发布",
    "ai-products": "产品发布",
    "paper": "研究论文",
    "tip": "技巧观点",
}


def fetch_aihot(src, window_start, max_items):
    """AI HOT 公开 API 适配器（精选池）。返回 (items, fetch_error)。
    AIHOT 是最对味的中文 AI 源、已精选噪音低，是 AI 深度的独木——放宽单源取量
    （不受全局 max_per_source 压制），让它多供给。"""
    cap = max(max_items, 40)
    since = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{src['url']}?mode=selected&since={since}&take={min(cap * 2, 100)}"
    try:
        resp = http_get(url)
        data = resp.json()
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({redact(e)})")
        return [], True
    items = []
    for it in data.get("items", []):
        inner = it.get("source", "")
        # 按 AI HOT 的内部来源粗分类型：X 推文算舆论，公众号算分析，其余算事实
        if inner.startswith("X："):
            stype, tier = "opinion", "T2"
        elif inner.startswith("公众号"):
            stype, tier = "analysis", "T2"
        else:
            stype, tier = src["source_type"], src.get("tier", "T1.5")
        # source_id 透传 AIHOT 内部真实来源：多源加分/同源封顶按真实出处计数，
        # 统一记成 "aihot" 会把独立信源信号压扁（多家报道被当成同一来源）
        sid = f"{src['id']}:{re.sub(r'\s+', '', inner)}" if inner else src["id"]
        items.append({
            "title": it.get("title") or it.get("title_en") or "",
            "url": it.get("url", ""),
            "desc": (it.get("summary") or "")[:400],
            "time": it.get("publishedAt") or datetime.now(timezone.utc).isoformat(),
            "source": f"AI HOT · {inner}" if inner else src["name"],
            "source_id": sid,
            "source_type": stype,
            "tier": tier,
            "credibility": src["credibility"],
            "tag_hint": AIHOT_TAG_HINT.get(it.get("category") or ""),
        })
    return [x for x in items if x["title"] and x["url"]][:cap], False


def fetch_thepaper_list(src, window_start, max_items):
    """澎湃频道页适配器（AIHOT 式"网页内嵌数据"直连，无 RSSHub 依赖）。
    澎湃各频道 list_* 页同构：__NEXT_DATA__ -> props.pageProps.data.list，
    每条带 name / contId / pubTimeLong（epoch 毫秒，绝对时间戳）。"""
    try:
        resp = http_get(src["url"])
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                      resp.text, re.S)
        rows = json.loads(m.group(1))["props"]["pageProps"]["data"]["list"] if m else []
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({redact(e)})")
        return [], True
    items = []
    for it in rows:
        title = (it.get("name") or "").strip()
        cont_id = str(it.get("contId") or "")
        ts = it.get("pubTimeLong")
        if not title or not cont_id or not ts:
            continue
        try:
            pub = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            continue
        if pub < window_start:
            continue
        items.append({
            "title": title,
            "url": f"https://www.thepaper.cn/newsDetail_forward_{cont_id}",
            "desc": "",
            "time": pub.isoformat(),
            "source": src["name"],
            "source_id": src["id"],
            "source_type": src["source_type"],
            "tier": src.get("tier", "T2"),
            "credibility": src["credibility"],
        })
    items.sort(key=lambda x: x["time"], reverse=True)
    return items[:max_items], False


LATEPOST_TZ = timezone(timedelta(hours=8))


def parse_latepost_time(value, now=None):
    """解析晚点列表的中国时区日期。无法可靠推断年份时返回 None。"""
    text = str(value or "").strip()
    if not text:
        return None
    ref = now or datetime.now(timezone.utc)
    local_now = ref.astimezone(LATEPOST_TZ)
    if text == "昨天":
        target = local_now.date() - timedelta(days=1)
        return datetime(target.year, target.month, target.day, tzinfo=LATEPOST_TZ)
    full = re.fullmatch(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", text)
    short = re.fullmatch(r"(\d{1,2})月(\d{1,2})日", text)
    try:
        if full:
            return datetime(int(full.group(1)), int(full.group(2)), int(full.group(3)),
                            tzinfo=LATEPOST_TZ)
        if short:
            month, day = int(short.group(1)), int(short.group(2))
            candidate = datetime(local_now.year, month, day, tzinfo=LATEPOST_TZ)
            if candidate.date() <= local_now.date():
                return candidate
            # 跨年初可以可靠判定 11/12 月属于上一年；其他未来日期丢弃。
            if local_now.month == 1 and month >= 11:
                return datetime(local_now.year - 1, month, day, tzinfo=LATEPOST_TZ)
    except ValueError:
        return None
    return None


def extract_latepost_content(page_html):
    """从晚点详情页提取正文；选择器失效时不用全页导航充当正文。"""
    for class_hint in ("article-body", "detail-content", "detail-con",
                       "article-content", "news-content"):
        m = re.search(
            rf'<(?:div|article)[^>]*class=["\'][^"\']*{class_hint}[^"\']*["\'][^>]*>'
            r'(.*?)</(?:div|article)>', page_html or "", re.I | re.S)
        if m:
            return strip_html(m.group(1))
    return ""


def _same_origin_http_url(base, value):
    """Resolve one upstream link while refusing scheme, credential or origin changes."""
    try:
        base_parts = urlsplit(str(base or ""))
        resolved = urljoin(str(base or "").rstrip("/") + "/", str(value or "").strip())
        parts = urlsplit(resolved)
        if (base_parts.scheme not in ("http", "https")
                or parts.scheme not in ("http", "https")
                or not base_parts.hostname or not parts.hostname
                or parts.username is not None or parts.password is not None):
            return ""
        base_port = base_parts.port or (443 if base_parts.scheme == "https" else 80)
        resolved_port = parts.port or (443 if parts.scheme == "https" else 80)
        if (parts.scheme != base_parts.scheme
                or parts.hostname.lower() != base_parts.hostname.lower()
                or resolved_port != base_port):
            return ""
        return urlunsplit(parts)
    except (TypeError, ValueError):
        return ""


def fetch_latepost(src, window_start, max_items, now=None):
    """晚点长报道适配器：公开 JSON 列表 + 服务端详情页，无浏览器依赖。"""
    base = str(src.get("url") or "https://www.latepost.com").rstrip("/")
    endpoint = base + "/news/get-news-data"
    try:
        resp = http_post(
            endpoint,
            data={"page": 1, "limit": max(max_items * 2, 10), "programa": 4},
            headers={"Referer": base + "/news/index?proma=4"})
        payload = resp.json()
        rows = payload.get("data", []) if payload.get("code") == 1 else []
    except Exception as e:
        log(f"  ✗ {src['name']}: 抓取失败 ({redact(e)})")
        return [], True

    pending = []
    reference = now or datetime.now(timezone.utc)
    for row in rows:
        title = strip_html(row.get("title", ""))
        detail_url = str(row.get("detail_url") or "")
        pub = parse_latepost_time(row.get("release_time"), reference)
        if not title or not detail_url or pub is None or pub < window_start:
            continue
        url = _same_origin_http_url(base, detail_url)
        if not url:
            continue
        summary = strip_html(" ".join(str(row.get(k) or "")
                                      for k in ("intro", "abstract", "problem", "answer")))
        pending.append({"title": title, "url": url, "summary": summary, "pub": pub})

    pending.sort(key=lambda x: x["pub"], reverse=True)
    items = []
    for row in pending[:max_items]:
        title, url, summary, pub = (row["title"], row["url"], row["summary"], row["pub"])
        content = ""
        if len(summary) < 80:
            try:
                content = extract_latepost_content(http_get(url).text)
            except Exception as e:
                log(f"  ⚠ {src['name']}: 详情页读取失败 ({e})")
        if not content:
            content = summary
        desc = content[:400] if content and len(summary) < 80 else (summary or content[:400])
        items.append({
            "title": title,
            "url": url,
            "desc": desc[:400],
            "content_chars": len(re.sub(r"\s", "", content)),
            "content_words": len(content.split()),
            "time": pub.isoformat(),
            "source": src["name"],
            "source_id": src["id"],
            "source_type": src.get("source_type", "analysis"),
            "tier": src.get("tier", "T1.5"),
            "credibility": src.get("credibility", 8),
        })
    return items, False


# ----------------------------------------------------------------
# 1.1 舆论热榜适配器（直连公开接口，无 RSSHub / 无浏览器）
#   热榜词条只作两个用途，本身永不成为新闻条目：
#   ① opinion_pulse 舆论观察模块的 LLM 输入
#   ② co-occurrence 暗排序：与真新闻事件重合时加公众热度 bonus
# ----------------------------------------------------------------

def fetch_weibo_hot(limit=40):
    """微博热搜：genvisitor 两步握手拿访客 cookie（无需登录/浏览器），再取榜单。
    失败返回 []（独立故障域，只丢当天微博信号）。"""
    try:
        sess = requests.Session()
        sess.headers.update({"User-Agent": UA})
        r1 = sess.post("https://passport.weibo.com/visitor/genvisitor",
                       data={"cb": "gen_callback"}, timeout=15)
        m = re.search(r'"tid":"([^"]+)"', r1.text)
        if m:
            sess.get("https://passport.weibo.com/visitor/visitor",
                     params={"a": "incarnate", "t": m.group(1), "w": "2",
                             "c": "095", "cb": "cross_domain"}, timeout=15)
        r2 = sess.get("https://weibo.com/ajax/side/hotSearch",
                      headers={"Referer": "https://weibo.com/"}, timeout=15)
        rows = (r2.json().get("data") or {}).get("realtime") or []
        out = []
        for x in rows:
            w = (x.get("word") or "").strip()
            if not w or x.get("is_ad"):
                continue
            out.append({"platform": "微博", "word": w,
                        "hot": int(x.get("num") or 0),
                        "url": "https://s.weibo.com/weibo?q=" + quote(f"#{w}#")})
        return out[:limit]
    except Exception as e:
        log(f"  ✗ 微博热搜: {e}")
        return []


def fetch_bilibili_hot(limit=30):
    """B站热搜：公开 JSON 接口，无鉴权。失败返回 []（独立故障域）。"""
    try:
        resp = http_get("https://api.bilibili.com/x/web-interface/search/square?limit=30")
        rows = (((resp.json().get("data") or {}).get("trending") or {}).get("list")) or []
        out = []
        for x in rows:
            w = (x.get("keyword") or x.get("show_name") or "").strip()
            if not w:
                continue
            out.append({"platform": "B站", "word": w, "hot": 0,
                        "url": "https://search.bilibili.com/all?keyword=" + quote(w)})
        return out[:limit]
    except Exception as e:
        log(f"  ✗ B站热搜: {e}")
        return []


PULSE_FETCHERS = {"weibo_hot": fetch_weibo_hot, "bilibili_hot": fetch_bilibili_hot}


def fetch_pulse_all(src_cfg):
    """拉全部启用的舆论热榜源。单平台失败只丢该平台，永不抛异常。"""
    pulse = []
    for s in (src_cfg.get("pulse_sources") or []):
        if not s.get("enabled", True):
            continue
        fn = PULSE_FETCHERS.get(s.get("type"))
        if not fn:
            continue
        got = fn()
        if got:
            log(f"  ✓ {s.get('name', s['type'])}: {len(got)} 条热榜词")
        pulse += got
    return pulse


FETCHERS = {"aihot": fetch_aihot, "thepaper_list": fetch_thepaper_list,
            "latepost": fetch_latepost}


def fetch_all(sources, cfg):
    """返回 (items, fetch_stats)。fetch_stats 按源记录条数与抓取是否失败，
    供健康度记录使用。"""
    window_start = datetime.now(timezone.utc) - timedelta(hours=cfg["window_hours"])
    max_items = cfg["max_per_source"]
    results = []
    fetch_stats = {}
    log(f"开始抓取 {len(sources)} 个源（窗口 {cfg['window_hours']} 小时）...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = {}
        for src in sources:
            fn = FETCHERS.get(src["type"], fetch_rss)
            futs[pool.submit(fn, src, window_start, max_items)] = src
        for fut in concurrent.futures.as_completed(futs):
            src = futs[fut]
            try:
                items, err = fut.result()
            except Exception as e:
                log(f"  ✗ {src['name']}: {e}")
                items, err = [], True
            fetch_stats[src["id"]] = {"name": src["name"],
                                      "count": len(items), "error": err}
            for item in items:
                if src.get("source_family"):
                    item.setdefault("source_family", src["source_family"])
                if src.get("provenance"):
                    item.setdefault("provenance", src["provenance"])
            if items:
                log(f"  ✓ {src['name']}: {len(items)} 条")
            results.extend(items)
    # URL 级去重（同链接完全相同的）
    seen, deduped = set(), []
    for it in results:
        key = it["url"].split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    log(f"共抓取 {len(results)} 条，URL 去重后 {len(deduped)} 条")
    return deduped, fetch_stats


# ----------------------------------------------------------------
# 1.1 普通新闻跨日去重
# ----------------------------------------------------------------

NEWS_SEEN_DIR = "news-seen"
UPDATE_JUDGE_SYSTEM = """你是新闻更新审计员。比较同一 URL 上次与本次的标题和摘要。
只有事件结果、关键数字、影响范围、政策结论、正式更正，或首次官方确认/否认导致可信状态变化，material 才为 true。
措辞润色、翻译变化、标题改写、时间戳刷新和背景补充均为 false。
严格返回 JSON：{"updates":[{"index":0,"material":false}]}，每个输入 index 恰好一项。"""


def canonical_news_url(url):
    """URL 身份：保留路径，移除查询参数和片段。"""
    try:
        parts = urlsplit(str(url or "").strip())
        if not parts.scheme or not parts.netloc:
            return str(url or "").split("?", 1)[0].split("#", 1)[0]
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, "", ""))
    except ValueError:
        return str(url or "").split("?", 1)[0].split("#", 1)[0]


def _normalized_news_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def news_content_fingerprint(title, desc):
    raw = _normalized_news_text(title) + "\n" + _normalized_news_text(desc)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _read_all_payload(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
        match = re.search(r"window\.NEWS_ALL\[[^\]]+\] = (\{.*\});\s*$", raw, re.S)
        return json.loads(match.group(1)) if match else None
    except (OSError, ValueError):
        return None


def _bootstrap_news_seen(data_dir, cutoff, date_str):
    seen = {}
    for path in sorted((Path(data_dir) / "all").glob("*.js")):
        if path.stem == "manifest" or path.stem < cutoff or path.stem > date_str:
            continue
        payload = _read_all_payload(path)
        if not payload:
            continue
        report_date = str(payload.get("date") or path.stem)
        for row in payload.get("items") or []:
            url = canonical_news_url(row.get("u"))
            if not url:
                continue
            title = str(row.get("t") or "")
            old = seen.get(url)
            first_seen = min(old.get("first_seen", report_date), report_date) if old else report_date
            seen[url] = {
                "url": url, "first_seen": first_seen, "last_seen": report_date,
                "title": title, "desc": "",
                "fingerprint": news_content_fingerprint(title, ""), "legacy": True,
            }
    if seen:
        log(f"  新闻去重账本冷启动：从全部动态恢复 {len(seen)} 个 URL")
    return seen


def load_news_seen(data_dir, date_str, keep_days=90):
    data_dir = Path(data_dir)
    cutoff = (datetime.strptime(date_str, "%Y-%m-%d")
              - timedelta(days=int(keep_days))).strftime("%Y-%m-%d")
    # 历史 all 档是部署前底账；新分片补充摘要与指纹，不能因出现首个分片就丢掉旧历史。
    seen = _bootstrap_news_seen(data_dir, cutoff, date_str)
    shard_dir = data_dir / NEWS_SEEN_DIR
    paths = sorted(shard_dir.glob("*.json")) if shard_dir.exists() else []
    for path in paths:
        if path.stem < cutoff or path.stem > date_str:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("items") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                continue
        except (OSError, ValueError):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = canonical_news_url(row.get("url"))
            if not url:
                continue
            old = seen.get(url)
            if old and str(old.get("last_seen", "")) > str(row.get("last_seen", "")):
                continue
            merged = dict(row)
            merged["url"] = url
            if old:
                merged["first_seen"] = min(str(old.get("first_seen") or date_str),
                                           str(row.get("first_seen") or date_str))
            seen[url] = merged
    return seen


def filter_cross_day_news(llm, items, seen, date_str, quality=None):
    """过滤旧 URL；内容变化时才批量语义判断是否为重大更新。"""
    quality = quality if quality is not None else new_quality_stats()
    kept, changed = [], []
    for item in items:
        url = canonical_news_url(item.get("url"))
        prior = seen.get(url)
        if not prior or prior.get("last_seen") == date_str:
            kept.append(item)
            continue
        fingerprint = news_content_fingerprint(item.get("title"), item.get("desc"))
        legacy_same_title = (prior.get("legacy")
                             and _normalized_news_text(prior.get("title"))
                             == _normalized_news_text(item.get("title")))
        if prior.get("fingerprint") == fingerprint or legacy_same_title:
            quality["cross_day_duplicates"] += 1
            continue
        changed.append((item, prior))

    if not changed:
        return kept
    request_rows = [{
        "index": i,
        "previous": {"title": prior.get("title", ""), "summary": prior.get("desc", "")},
        "current": {"title": item.get("title", ""), "summary": item.get("desc", "")},
    } for i, (item, prior) in enumerate(changed)]
    decisions = {}
    try:
        raw = llm.json_call(UPDATE_JUDGE_SYSTEM,
                            json.dumps(request_rows, ensure_ascii=False))
        rows = raw.get("updates") if (isinstance(raw, dict)
                                        and set(raw) == {"updates"}) else None
        if not isinstance(rows, list):
            raise ValueError("updates must be a list")
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {"index", "material"}
                    or isinstance(row.get("index"), bool)
                    or not isinstance(row.get("index"), int)
                    or not isinstance(row.get("material"), bool)):
                raise ValueError("invalid update row")
            idx = row["index"]
            if not 0 <= idx < len(changed) or idx in decisions:
                raise ValueError("duplicate or out-of-range update index")
            decisions[idx] = row["material"]
        if set(decisions) != set(range(len(changed))):
            raise ValueError("updates must cover every input exactly once")
    except Exception as exc:
        decisions = {}
        log(f"  重大更新判定失败，候选保留: {exc}")
        quality["degraded"] = True

    for idx, (item, prior) in enumerate(changed):
        if decisions.get(idx) is True:
            item["is_update"] = True
            item["first_seen"] = prior.get("first_seen") or prior.get("last_seen")
            kept.append(item)
            quality["material_updates"] += 1
        elif idx in decisions:
            quality["cross_day_duplicates"] += 1
        else:
            kept.append(item)
            quality["update_judge_failures"] += 1
            quality["degraded"] = True
    return kept


def save_news_seen(data_dir, date_str, items, seen, keep_days=90):
    """成功生成日报后写当天分片；同日重跑覆盖，避免整本账本每日重写。"""
    data_dir = Path(data_dir)
    shard_dir = data_dir / NEWS_SEEN_DIR
    shard_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        url = canonical_news_url(item.get("url"))
        if not url:
            continue
        prior = seen.get(url) or {}
        rows.append({
            "url": url,
            "first_seen": item.get("first_seen") or prior.get("first_seen") or date_str,
            "last_seen": date_str,
            "title": str(item.get("title") or "")[:300],
            "desc": str(item.get("desc") or "")[:500],
            "fingerprint": news_content_fingerprint(item.get("title"), item.get("desc")),
        })
    rows.sort(key=lambda row: row["url"])
    payload = {"version": 1, "date": date_str, "items": rows}
    (shard_dir / f"{date_str}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cutoff = (datetime.strptime(date_str, "%Y-%m-%d")
              - timedelta(days=int(keep_days))).strftime("%Y-%m-%d")
    for path in shard_dir.glob("*.json"):
        if path.stem < cutoff:
            path.unlink()
    log(f"  新闻去重账本：写入 {len(rows)} 个 URL（保留 {keep_days} 天）")


# ----------------------------------------------------------------
# 2. LLM 客户端
# ----------------------------------------------------------------

def resolve_llm_config(cfg, section="llm", environ=None):
    """Resolve one role against the active named provider.

    The legacy flat ``llm`` shape remains readable for tests and local overrides.
    In the named shape, credentials come only from each provider's
    ``api_key_env``. Empty role identity fields inherit the active provider.
    """
    environ = os.environ if environ is None else environ
    llm_cfg = cfg.get("llm") or {}
    providers = llm_cfg.get("providers")
    override = {} if section == "llm" else (cfg.get(section) or {})

    if isinstance(providers, dict):
        active = str(override.get("provider") or llm_cfg.get("active_provider") or "").strip()
        if not active:
            raise ValueError("llm.active_provider is required")
        raw_provider = providers.get(active)
        if not isinstance(raw_provider, dict):
            raise ValueError(f"unknown LLM provider: {active}")
        primary = dict(raw_provider)
        primary["provider"] = active
        env_name = str(primary.get("api_key_env") or "").strip()
        if env_name and str(environ.get(env_name) or "").strip():
            primary["api_key"] = str(environ[env_name]).strip()
    else:
        primary = dict(llm_cfg)

    if section == "llm":
        return primary
    merged = dict(primary)
    for key, value in override.items():
        if key in ("provider", "base_url", "api_key", "model") and not str(value or "").strip():
            continue
        if key == "enabled":
            continue
        if value is not None:
            merged[key] = value
    return merged

_STAGE_PROMPT_INDEX = None
_FORMATTED_STAGE_PROMPTS = ("ENRICH_SYSTEM", "VOCAB_SYSTEM")


def stage_of_prompt(system):
    """Map a system prompt back to its module-level constant name.

    Stage labels stay zero-maintenance this way: adding a new ``*_SYSTEM``
    constant automatically gets its own accounting row, with no call-site edits.
    The two formatted templates are matched by their full literal prefix.
    Static prompts require exact equality, so an unrelated prompt cannot enter
    a known cost bucket merely by sharing its first characters.
    """
    global _STAGE_PROMPT_INDEX
    if _STAGE_PROMPT_INDEX is None:
        exact = {
            value: name for name, value in list(globals().items())
            if name.endswith("_SYSTEM") and isinstance(value, str) and value
        }
        formatted = []
        for name in _FORMATTED_STAGE_PROMPTS:
            template = globals().get(name)
            if isinstance(template, str) and "{" in template:
                formatted.append((template.split("{", 1)[0], name))
                exact.pop(template, None)
        _STAGE_PROMPT_INDEX = exact, tuple(formatted)
    prompt = str(system or "")
    exact, formatted = _STAGE_PROMPT_INDEX
    if prompt in exact:
        return exact[prompt]
    for prefix, name in formatted:
        if prompt.startswith(prefix):
            return name
    return "OTHER"


def new_usage_stats():
    return {"calls": 0, "input": 0, "input_cached": 0, "output": 0}


def usage_cost_usd(usage, price=None):
    """Convert a usage row to dollars. Cached input is billed at its own rate."""
    price = price if price is not None else usage.get("price_usd_per_mtok")
    if not isinstance(price, dict):
        return None
    try:
        input_miss_price = float(price["input_miss"])
        input_hit_price = float(price["input_hit"])
        output_price = float(price["output"])
    except (KeyError, TypeError, ValueError):
        return None
    if any(
            not math.isfinite(value) or value < 0
            for value in (
                input_miss_price, input_hit_price, output_price)):
        return None
    input_tokens = max(0, int(usage.get("input", 0)))
    cached_tokens = min(
        input_tokens, max(0, int(usage.get("input_cached", 0))))
    output_tokens = max(0, int(usage.get("output", 0)))
    miss = input_tokens - cached_tokens
    return (miss * input_miss_price
            + cached_tokens * input_hit_price
            + output_tokens * output_price) / 1e6


class LLMCallError(RuntimeError):
    def __init__(self, message, *, retryable=False, retry_after=None, usage=None):
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after
        self.usage = usage


class LLM:
    def __init__(self, cfg):
        self.provider = str(cfg.get("provider") or cfg.get("protocol") or "openai")
        self.protocol = str(cfg.get("protocol") or "openai").lower()
        if self.protocol not in {"openai", "anthropic"}:
            raise ValueError(f"unsupported LLM protocol: {self.protocol}")
        self.base_url = str(cfg["base_url"]).rstrip("/")
        self.api_key = str(cfg.get("api_key") or "")
        self.model = cfg["model"]
        self.temperature = cfg.get("temperature", 0.3)
        self.max_retries = max(1, int(cfg.get("max_retries", 3)))
        self.max_tokens = int(cfg.get("max_tokens", 16384))
        raw_timeout = cfg.get("request_timeout", (10, 180))
        if not isinstance(raw_timeout, (list, tuple)) or len(raw_timeout) != 2:
            raise ValueError("request_timeout must contain connect and read seconds")
        self.request_timeout = (float(raw_timeout[0]), float(raw_timeout[1]))
        # 供应商专有请求体字段（如 DeepSeek V4 的 thinking 开关），原样透传。
        # 不配置则完全不发，保持对任意 OpenAI 兼容接口的通用性。
        self.extra_body = cfg.get("extra_body") or None
        self.price_usd_per_mtok = (
            cfg.get("price_usd_per_mtok")
            if isinstance(cfg.get("price_usd_per_mtok"), dict)
            else LLM_PRICE_USD_PER_MTOK.get(self.model)
        )
        if self.protocol == "openai":
            from openai import OpenAI, Timeout
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                # Retries are owned by _call so one logical attempt cannot
                # silently expand into multiple paid SDK requests.
                max_retries=0,
                timeout=Timeout(
                    self.request_timeout[1],
                    connect=self.request_timeout[0],
                ),
            )
        else:
            self.client = None
        # 按阶段累计的 token 消耗。计量只读响应里的 usage，不参与任何管线决策。
        self.stage_usage = {}

    def record_usage(self, stage, usage):
        """Accumulate one billed response. Retries count too—they are billed."""
        row = self.stage_usage.setdefault(stage, new_usage_stats())
        row["calls"] += 1
        if usage is None:
            return
        row["input"] += int(usage.get("input", 0) or 0)
        row["input_cached"] += int(usage.get("input_cached", 0) or 0)
        row["output"] += int(usage.get("output", 0) or 0)

    @staticmethod
    def _openai_usage(usage):
        if usage is None:
            return None
        input_tokens = max(0, int(getattr(usage, "prompt_tokens", 0) or 0))
        details = getattr(usage, "prompt_tokens_details", None)
        cached_tokens = max(
            int(getattr(usage, "prompt_cache_hit_tokens", 0) or 0),
            int(getattr(details, "cached_tokens", 0) or 0),
        )
        return {
            "input": input_tokens,
            "input_cached": min(input_tokens, max(0, cached_tokens)),
            "output": max(
                0, int(getattr(usage, "completion_tokens", 0) or 0)),
        }

    @staticmethod
    def _anthropic_usage(usage):
        if not isinstance(usage, dict):
            return None
        cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
        cache_create = int(usage.get("cache_creation_input_tokens", 0) or 0)
        return {
            "input": int(usage.get("input_tokens", 0) or 0) + cache_read + cache_create,
            "input_cached": cache_read,
            "output": int(usage.get("output_tokens", 0) or 0),
        }

    @staticmethod
    def _retry_after(response):
        try:
            value = float((response.headers or {}).get("retry-after", ""))
            return min(30.0, max(0.0, value))
        except (TypeError, ValueError):
            return None

    def _complete(self, system, user, temperature=None):
        if self.protocol == "openai":
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature if temperature is None else temperature,
                max_tokens=self.max_tokens,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                extra_body=self.extra_body,
            )
            usage = self._openai_usage(getattr(resp, "usage", None))
            choice = resp.choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                raise LLMCallError(
                    "OpenAI response truncated", retryable=True, usage=usage)
            return choice.message.content.strip(), usage

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=headers,
                timeout=self.request_timeout,
            )
        except requests.RequestException as exc:
            raise LLMCallError(
                f"Anthropic transport error: {exc}", retryable=True) from exc
        if response.status_code != 200:
            retryable = response.status_code in {408, 429, 500, 503, 504}
            raise LLMCallError(
                f"Anthropic HTTP {response.status_code}: {str(response.text)[:300]}",
                retryable=retryable,
                retry_after=self._retry_after(response) if retryable else None,
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise LLMCallError("Anthropic response is not JSON") from exc
        usage = self._anthropic_usage(body.get("usage"))
        if body.get("stop_reason") == "max_tokens":
            raise LLMCallError(
                "Anthropic response truncated at max_tokens",
                retryable=True,
                usage=usage,
            )
        blocks = body.get("content")
        if not isinstance(blocks, list):
            raise LLMCallError("Anthropic response missing content blocks")
        text = "".join(
            str(block.get("text") or "")
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
        if not text:
            raise LLMCallError("Anthropic response contains no text")
        return text, usage

    def _call(self, system, user, parser, temperature=None):
        last_err = None
        stage = stage_of_prompt(system)
        # Same-day reconciliation already has a conservative deterministic
        # fallback and a whole-run request budget. Retrying one logical batch
        # would silently spend multiple slots, so this stage gets one request.
        max_attempts = 1 if stage == "SAME_DAY_RECONCILE_SYSTEM" else self.max_retries
        for attempt in range(max_attempts):
            try:
                text, usage = self._complete(
                    system, user, temperature=temperature)
                self.record_usage(stage, usage)
                return parser(text)
            except Exception as exc:
                last_err = exc
                usage = getattr(exc, "usage", None)
                if usage is not None:
                    self.record_usage(stage, usage)
                retryable = self._is_retryable_error(exc)
                log(f"  LLM 调用失败（第{attempt + 1}次）: {exc}")
                if not retryable or attempt + 1 >= max_attempts:
                    break
                delay = getattr(exc, "retry_after", None)
                time.sleep(delay if delay is not None else 2 ** attempt)
        raise RuntimeError(f"LLM 调用重试均失败: {last_err}")

    @staticmethod
    def _is_retryable_error(exc):
        if isinstance(exc, LLMCallError):
            return exc.retryable
        if isinstance(exc, requests.RequestException):
            return True
        status_code = getattr(exc, "status_code", None)
        if status_code is not None:
            return status_code in {408, 429, 500, 503, 504}
        return exc.__class__.__name__ in {"APIConnectionError", "APITimeoutError"}

    @staticmethod
    def _parse_json(text):
        # 提取 JSON（容忍 ```json 包裹）
        m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
        if m:
            text = m.group(1).strip()
        positions = [i for i in (text.find("["), text.find("{")) if i >= 0]
        if not positions:
            raise LLMCallError("LLM response contains no JSON object or array")
        try:
            return json.loads(text[min(positions):])
        except ValueError as exc:
            raise LLMCallError(
                f"LLM response JSON parse failed: {exc}",
            ) from exc

    def json_call(self, system, user):
        """调用并解析 JSON，自动重试"""
        return self._call(system, user, self._parse_json)

    def text_call(self, system, user, temperature=None):
        """调用并返回纯文本，复用协议、重试与计量。"""
        return self._call(system, user, lambda text: text, temperature=temperature)


def merge_usage(llms):
    """Merge usage without losing provider/model identity."""
    merged = {}
    for llm in llms:
        for stage, row in getattr(llm, "stage_usage", {}).items():
            identity = (
                str(getattr(llm, "provider", "unknown")),
                str(getattr(llm, "model", "unknown")),
                stage,
            )
            client_price = getattr(llm, "price_usd_per_mtok", None)
            if identity not in merged:
                merged[identity] = {
                    **new_usage_stats(),
                    "price_usd_per_mtok": client_price,
                }
            target = merged[identity]
            if target["price_usd_per_mtok"] != client_price:
                # One identity must not silently inherit whichever role happened
                # to be merged first. A conflicting override makes cost unknown.
                target["price_usd_per_mtok"] = None
            for key in new_usage_stats():
                target[key] += int(row.get(key, 0))
    return merged


def usage_totals(merged):
    total = new_usage_stats()
    for row in merged.values():
        for key in total:
            total[key] += int(row.get(key, 0))
    costs = [usage_cost_usd(row) for row in merged.values()]
    cost_known = all(cost is not None for cost in costs)
    return {
        "llm_calls": total["calls"],
        "llm_input_tokens": total["input"],
        "llm_cached_input_tokens": total["input_cached"],
        "llm_output_tokens": total["output"],
        "llm_cost_usd": (
            round(sum(costs), 4) if cost_known else None),
        "llm_cost_known": cost_known,
    }


def log_usage_report(llms):
    """Print the run's token bill, most expensive stage first."""
    merged = merge_usage(llms)
    totals = usage_totals(merged)
    if not totals["llm_calls"]:
        return totals
    log("LLM 用量结算（按阶段，成本降序）：")
    def sort_cost(item):
        cost = usage_cost_usd(item[1])
        return -(cost if cost is not None else -1)

    for (provider, model, stage), row in sorted(merged.items(), key=sort_cost):
        cost = usage_cost_usd(row)
        cost_text = f"${cost:.4f}" if cost is not None else "单价未知"
        log(f"  {provider}/{model} {stage:<34} {row['calls']:>4} 次  "
            f"入 {row['input'] / 1000:>8.1f}k（缓存 {row['input_cached'] / 1000:.1f}k）  "
            f"出 {row['output'] / 1000:>6.1f}k  {cost_text}")
    total_cost = (
        f"${totals['llm_cost_usd']:.4f}"
        if totals["llm_cost_known"] else "单价未知")
    log(f"  合计 {totals['llm_calls']} 次调用｜"
        f"入 {totals['llm_input_tokens'] / 1000:.1f}k（缓存 "
        f"{totals['llm_cached_input_tokens'] / 1000:.1f}k）｜"
        f"出 {totals['llm_output_tokens'] / 1000:.1f}k｜"
        f"{total_cost}")
    return totals


def warn_if_cost_exceeds(usage, cfg, policy):
    """Emit a non-blocking warning when a run crosses its configured soft cap."""
    if not usage.get("llm_cost_known"):
        return False
    guard = (cfg or {}).get("cost_guard") or {}
    is_shadow = str((policy or {}).get("mode") or "") == "shadow"
    key = "shadow_warn_usd" if is_shadow else "generate_warn_usd"
    try:
        limit = float(guard.get(key))
        cost = float(usage.get("llm_cost_usd"))
    except (TypeError, ValueError):
        return False
    if limit < 0 or cost <= limit:
        return False
    mode = "shadow" if is_shadow else "generate"
    print(
        f"::warning::LLM {mode} cost ${cost:.4f} exceeded "
        f"the configured ${limit:.4f} warning threshold.",
        flush=True,
    )
    return True


# ----------------------------------------------------------------
# 3. 预筛（便宜模型）：丢垃圾，主模型只处理幸存者
# ----------------------------------------------------------------


def _model_index(value, size):
    """Return a strict JSON integer index; booleans and numeric strings are invalid."""
    return value if type(value) is int and 0 <= value < size else None


def _model_number(value):
    """Return a finite JSON number, rejecting booleans, strings, NaN and infinity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _model_rows(raw, key):
    """把模型返回归一化成行列表；整体不可用时返回 None。

    本仓库的默认输出契约是对象包裹 `{key: [...]}`——裸数组契约在答案只有单个
    元素时会被模型丢掉外壳，退化成裸对象，见 docs/adr/0012。这里同时接住三种
    历史与退化形态，任一命中都不算故障。"""
    if isinstance(raw, dict):
        rows = raw.get(key)
        if isinstance(rows, list):
            return rows
        # 键名漂移（events 写成 event_list 之类）：判据是"整个对象只有这一个
        # 键"。包裹对象只有一个键，而丢了外壳的裸行对象总是带着 idx/title/dims
        # 等一堆字段——按字段数区分不可能误判。换成"唯一的列表值"就会误判：
        # 裸行自己就带 ids / claims / context_evidence 这类列表字段。
        if len(raw) == 1:
            only = next(iter(raw.values()))
            if isinstance(only, list):
                return only
        return [raw]
    if isinstance(raw, list):
        return raw
    return None


PREFILTER_SYSTEM = """你是新闻信息流的第一道过滤器。用户给你一批带编号的条目标题。
输出两类编号：
- drop（丢弃）：广告软文、纯营销、促销、招聘、菜谱/生活贴士、纯情绪帖、
  以及明显不属于（AI/互联网科技/财经/社会事件/国际时事）任何一类的内容。拿不准一律不丢。
- soft（软边角料）：本身是真实新闻、但对建立长期判断价值低的轻资讯——
  体育赛事结果/花絮、明星八卦与私生活、猎奇轶闻、纯日抛型热点。
  这类不丢弃（仍可留作长尾），只是打个标记。拿不准算不算边角料的，倾向不标。
只输出 JSON：{"drop": [编号...], "soft": [编号...]}，无对应项输出空数组。"""


def prefilter(llm, items):
    batch_size = 80
    drop, soft = set(), set()
    for bi in range(0, len(items), batch_size):
        batch = items[bi:bi + batch_size]
        lines = [f"[{bi + j}] ({it['source']}) {it['title']}"
                 for j, it in enumerate(batch)]
        try:
            result = llm.json_call(PREFILTER_SYSTEM, "\n".join(lines))
            for i in result.get("drop", []):
                if isinstance(i, int) and not isinstance(i, bool) and bi <= i < bi + len(batch):
                    drop.add(i)
            for i in result.get("soft", []):
                if isinstance(i, int) and not isinstance(i, bool) and bi <= i < bi + len(batch):
                    soft.add(i)
        except Exception as e:
            log(f"  预筛批次失败，该批全部保留: {e}")
    for i in soft:
        if i not in drop:
            items[i]["soft"] = True   # 标记随 item 传递到事件层，用于长尾过滤
    kept = [it for i, it in enumerate(items) if i not in drop]
    n_soft = sum(1 for it in kept if it.get("soft"))
    log(f"预筛：丢弃 {len(drop)} 条，保留 {len(kept)} 条（其中软边角料 {n_soft} 条）")
    return kept


# ----------------------------------------------------------------
# 4. 阶段A：去重聚类 + 分类 + 五维分项打分
# ----------------------------------------------------------------

TRIAGE_SYSTEM = """你是一个严格的新闻编辑，负责筛选每日高质量新闻。
用户会给你一批带编号的新闻条目（标题+简介+来源）。你的任务：
1. 把报道【同一事件】的条目合并成一个事件（去重）
   同一事件 = 同一主体 + 同一具体事实（同一次发布/同一起事故/同一项决定）。
   仅仅主题相同、领域相同、都和 AI 或同一家公司有关，【不算】同一事件，禁止合并。
   拿不准就不合并，宁可各自成事件也不要打包。
   事件标题必须只描述一件事，禁止"X与Y"式拼盘标题。
2. 给每个事件分类：ai(人工智能) / tech(互联网科技) / finance(财经) / society(社会事件) / world(国际政治与时事)
3. 给每个事件打 5 个维度的分项分（各 0-10，不要打总分）：
   - impact     影响面：波及多少人/多大市场/多少行业
   - novelty    新颖性：全新事件=高分；旧闻翻炒、周年回顾、老话题重提=低分
   - substance  实质性：有真实信息增量（数据/决策/事实）=高分；口水、软文、纯观点=低分
   - evidence   佐证强度：官方发布或多个独立来源交叉=高分；单一匿名爆料=低分
   - durability 持续重要性：一周后还重要=高分；日抛型花边=低分
   注意：大佬转发/名人鸡汤 substance 和 durability 必须低；论文没有实验验证时 impact 别打高。
4. 丢弃残余垃圾（广告、花边、无信息量的帖子）

只输出 JSON 对象：{"events":[事件...]}，每个事件：
{"ids": [条目编号列表，同一事件的都放进来], "category": "ai|tech|finance|society|world",
 "dims": {"impact": 0-10, "novelty": 0-10, "substance": 0-10, "evidence": 0-10, "durability": 0-10},
 "title": "该事件的一句话中文标题"}
只有一个事件时也必须放在 events 数组里。没有事件就输出 {"events":[]}。
被丢弃的条目不要出现在任何事件里。不要输出任何其他文字。"""


def cap_same_source(ids, items, limit=2):
    """一个事件里同一来源最多保留 limit 条——同源 3 条以上几乎必然是
    "快讯打包"式错误聚类，代码层直接拦住。"""
    kept, per_src = [], {}
    for i in ids:
        sid = items[i]["source_id"]
        per_src[sid] = per_src.get(sid, 0) + 1
        if per_src[sid] <= limit:
            kept.append(i)
    return kept


def _triage_rows(result, quality):
    """归一化阶段A 返回并逐元素过滤；整体不可用时返回 None。"""
    raw_rows = _model_rows(result, "events")
    if raw_rows is None:
        return None
    rows = [ev for ev in raw_rows if isinstance(ev, dict)]
    # 空数组是合法回答（该批全是垃圾）；非空但一个可用行都没有，说明模型
    # 整体跑偏，按整批不可用处理，否则这批条目会静默丢光。
    if raw_rows and not rows:
        return None
    invalid = len(raw_rows) - len(rows)
    if invalid and quality is not None:
        quality["triage_invalid_rows"] += invalid
        quality["degraded"] = True
    return rows


def batch_spans(total, batch_size, min_tail=10):
    """分批区间；尾批不足 min_tail 条时并入前一批。

    2026-08-01 崩在只有 2 条的尾批上：输入极少时模型很可能只产出单个元素，
    而单元素答案极易被丢掉数组外壳。历史尾批都在 13 条以上，阈值 10 让常规
    日子的分批边界完全不变，只吃掉这种离群值。"""
    spans = [(bi, min(bi + batch_size, total))
             for bi in range(0, total, batch_size)]
    if len(spans) > 1 and spans[-1][1] - spans[-1][0] < min_tail:
        tail = spans.pop()
        spans[-1] = (spans[-1][0], tail[1])
    return spans


def _triage_singleton_events(batch, bi):
    """整批降级：每条各自成事件。阶段A 是聚类步骤，跳过一批等于这些条目
    彻底不进事件层，是内容损失且表面看不出来；宁可不去重也不能丢内容。
    重复由后面的全量同日归并接住。"""
    return [{
        "ids": [bi + j],
        "category": "world",
        "dims": {dimension: 3.0 for dimension in DIMS},
        "title": it["title"],
    } for j, it in enumerate(batch)]


def triage(llm, items, quality=None):
    """分批聚类打分，返回事件列表"""
    events = []
    for batch_number, (bi, end) in enumerate(batch_spans(len(items), 50), start=1):
        batch = items[bi:end]
        lines = []
        for j, it in enumerate(batch):
            idx = bi + j
            lines.append(f"[{idx}] ({it['source']}|{TYPE_NAMES[it['source_type']]}|{it['tier']}) "
                         f"{it['title']} —— {it['desc'][:120]}")
        log(f"  阶段A 批次 {batch_number}: {len(batch)} 条")
        try:
            rows = _triage_rows(
                llm.json_call(TRIAGE_SYSTEM, "\n".join(lines)), quality)
            if rows is None:
                raise ValueError("triage response has no usable event rows")
        except Exception as exc:
            log(f"  阶段A 批次失败，该批每条降级为单条事件: {exc}")
            if quality is not None:
                quality["triage_fallback_batches"] += 1
                quality["model_unusable_responses"] += 1
                quality["degraded"] = True
            events.extend(_triage_singleton_events(batch, bi))
            continue
        produced = 0
        for ev in rows:
            # 编号必须落在本批次范围内——模型若返回批内相对编号，
            # 会静默指向其他批次的条目，造成标题与来源错配
            raw_ids = ev.get("ids", [])
            if not isinstance(raw_ids, (list, tuple)):
                raw_ids = []
            ids = [i for i in raw_ids
                   if isinstance(i, int) and not isinstance(i, bool)
                   and bi <= i < bi + len(batch)]
            ids = cap_same_source(ids, items)
            if not ids:
                continue
            raw_dims = ev.get("dims", {}) or {}
            if not isinstance(raw_dims, dict):
                raw_dims = {}
            dims = {}
            for dimension in DIMS:
                value = _model_number(raw_dims.get(dimension))
                dims[dimension] = max(0.0, min(10.0, value if value is not None else 3.0))
            events.append({
                "ids": ids,
                "category": ev.get("category") if ev.get("category") in CATEGORIES else "world",
                "dims": dims,
                "title": ev.get("title", items[ids[0]]["title"]),
            })
            produced += 1
        # 模型给了行、却一个事件都没落地，几乎只有一种成因：整批编号都不在本批
        # 窗口内（模型用了批内相对编号）。此时不降级就等于这批条目静默消失，
        # 和形状崩坏的后果一样，只是没人看得见。空数组是合法回答，不在此列。
        if rows and not produced:
            log(f"  阶段A 批次 {batch_number} 没有落地任何事件，该批每条降级为单条事件")
            if quality is not None:
                quality["triage_fallback_batches"] += 1
                quality["degraded"] = True
            events.extend(_triage_singleton_events(batch, bi))
    # 阶段A之后统一做证据归并：既覆盖跨批次漏项，也覆盖单批次模型漏项。
    if len(events) > 1:
        events = reconcile_same_day_events(llm, events, items, quality)
    return events


MERGE_SYSTEM = """下面是一批新闻事件标题（带编号）。有些编号可能描述的是同一事件（来自不同批次）。
只有当两个标题明显描述【同一具体事件】（同一主体+同一事实）时才算重复；
仅主题相近、领域相同不算，拿不准就不合并。
只输出 JSON 数组：需要合并的编号组，如 [[0,5],[2,9,11]]。没有可合并的就输出 []。不要输出其他文字。"""


def merge_events(llm, events, items):
    lines = [f"[{i}] {ev['title']}" for i, ev in enumerate(events)]
    try:
        groups = llm.json_call(MERGE_SYSTEM, "\n".join(lines))
    except Exception:
        return events
    merged_away = set()
    for group in groups:
        group = [g for g in group if isinstance(g, int) and not isinstance(g, bool)
                 and 0 <= g < len(events)]
        if len(group) < 2:
            continue
        primary = group[0]
        for g in group[1:]:
            if g in merged_away or g == primary:
                continue
            # 只吸收来源，维度分保留主事件的——避免错误合并抬高分数
            events[primary]["ids"].extend(events[g]["ids"])
            events[primary]["ids"] = cap_same_source(events[primary]["ids"], items)
            merged_away.add(g)
    result = [ev for i, ev in enumerate(events) if i not in merged_away]
    if merged_away:
        log(f"  跨批次合并了 {len(merged_away)} 个重复事件")
    return result


SAME_DAY_RECONCILE_BATCH_SIZE = 40
SAME_DAY_BLOCK_MAX_FREQUENCY = 12
SAME_DAY_RECONCILE_MAX_CALLS = 20
SAME_DAY_MIN_SHARED_KEYS = 4


def configure_same_day_cost_guard(llm, cfg):
    """Install one run-scoped reconciliation budget on the primary LLM."""
    guard = (cfg or {}).get("cost_guard") or {}
    state = {
        "max_calls": max(
            0, int(guard.get(
                "same_day_reconcile_max_calls",
                SAME_DAY_RECONCILE_MAX_CALLS))),
        "min_shared_keys": max(
            1, int(guard.get(
                "same_day_min_shared_keys",
                SAME_DAY_MIN_SHARED_KEYS))),
        "calls": 0,
    }
    setattr(llm, "_same_day_cost_guard", state)
    return state


def _same_day_cost_guard(llm):
    state = getattr(llm, "_same_day_cost_guard", None)
    return state if isinstance(state, dict) else configure_same_day_cost_guard(
        llm, {})


SAME_DAY_RECONCILE_SYSTEM = """你是日报的同日事件归并审计员。
输入是一批候选事件，每个事件带模型标题、分类和若干原始报道（标题、摘要、来源）。
同日事件 = 同一主体 + 同一具体发生事项（同一次发布、决定、事故、交易、财报或进展）。
事实报道与分析报道只要底层事项相同，必须归为一个事件；同一主体的不同事项、同一领域的相近主题不得合并。
同一持续事件在不同时间点出现的实质新进展也不得合并。
必须把每个输入事件编号恰好放入一个组，包括无需合并的单元素组。
只输出 JSON 对象：{"groups":[[0,3],[1],[2,4]]}。不要输出其他文字。"""


def _same_day_reconcile_payload(events, items, report_limit=None):
    payload = []
    for index, event in enumerate(events):
        reports = []
        for item_id in event.get("ids") or []:
            if not isinstance(item_id, int) or isinstance(item_id, bool):
                continue
            if not (0 <= item_id < len(items)):
                continue
            item = items[item_id]
            reports.append({
                "title": str(item.get("title") or "")[:180],
                "summary": str(item.get("desc") or "")[:240],
                "source": str(item.get("source") or "")[:100],
            })
            if report_limit is not None and len(reports) >= report_limit:
                break
        payload.append({
            "index": index,
            "title": str(event.get("title") or "")[:180],
            "category": event.get("category") if event.get("category") in CATEGORIES else "world",
            "reports": reports,
        })
    return payload


def _validated_same_day_groups(raw, event_count):
    if not isinstance(raw, dict) or not isinstance(raw.get("groups"), list):
        return None
    groups, seen = [], []
    for raw_group in raw["groups"]:
        if not isinstance(raw_group, list) or not raw_group:
            return None
        group = []
        for value in raw_group:
            if (not isinstance(value, int) or isinstance(value, bool)
                    or not 0 <= value < event_count or value in group):
                return None
            group.append(value)
        group.sort()
        groups.append(group)
        seen.extend(group)
    if len(seen) != event_count or len(set(seen)) != event_count \
            or set(seen) != set(range(event_count)):
        return None
    groups.sort(key=lambda group: group[0])
    return groups


def _deterministic_same_day_groups(events, items):
    """Return only identity-safe fallback groups that share an original item."""
    parents = list(range(len(events)))

    def find(value):
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    item_owners = {}
    for event_index, event in enumerate(events):
        for item_id in event.get("ids") or []:
            if not isinstance(item_id, int) or isinstance(item_id, bool):
                continue
            prior = item_owners.setdefault(item_id, event_index)
            union(prior, event_index)
    grouped = {}
    for index in range(len(events)):
        grouped.setdefault(find(index), []).append(index)
    return sorted(grouped.values(), key=lambda group: group[0])


def _same_day_block_keys(event, items):
    """Return recall-oriented keys used only to choose bounded model comparisons."""
    texts = [str(event.get("title") or "")]
    urls = set()
    for item_id in event.get("ids") or []:
        if not isinstance(item_id, int) or isinstance(item_id, bool):
            continue
        if not 0 <= item_id < len(items):
            continue
        item = items[item_id]
        texts.extend((str(item.get("title") or ""), str(item.get("desc") or "")))
        url = canonical_news_url(item.get("url"))
        if url:
            urls.add(f"url:{url}")

    text = unicodedata.normalize("NFKC", " ".join(texts)).casefold()
    keys = set(re.findall(r"[a-z][a-z0-9._-]{2,}", text))
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        keys.update(run[index:index + 2] for index in range(len(run) - 1))
    return keys | urls


def _same_day_reconcile_plan(
        events, items, batch_size=SAME_DAY_RECONCILE_BATCH_SIZE,
        min_shared_keys=SAME_DAY_MIN_SHARED_KEYS):
    """Build bounded base batches plus ranked, evidence-backed bridge batches."""
    batch_size = max(2, int(batch_size))
    min_shared_keys = max(1, int(min_shared_keys))
    base_batches = [
        list(range(start, min(start + batch_size, len(events))))
        for start in range(0, len(events), batch_size)
    ]
    key_owners = {}
    for event_index, event in enumerate(events):
        for key in _same_day_block_keys(event, items):
            key_owners.setdefault(key, set()).add(event_index)

    forced_pairs = set()
    lexical_counts = {}

    def add_pairs(owners, *, forced=False):
        ordered = sorted(owners)
        for left_pos, left in enumerate(ordered):
            for right in ordered[left_pos + 1:]:
                if left // batch_size == right // batch_size:
                    continue
                pair = (left, right)
                if forced:
                    forced_pairs.add(pair)
                else:
                    lexical_counts[pair] = lexical_counts.get(pair, 0) + 1

    for key, owners in key_owners.items():
        if key.startswith("url:"):
            if len(owners) >= 2:
                add_pairs(owners, forced=True)
            continue
        if not 2 <= len(owners) <= SAME_DAY_BLOCK_MAX_FREQUENCY:
            continue
        add_pairs(owners)

    item_owners = {}
    for event_index, event in enumerate(events):
        for item_id in event.get("ids") or []:
            if isinstance(item_id, int) and not isinstance(item_id, bool):
                item_owners.setdefault(item_id, set()).add(event_index)
    for owners in item_owners.values():
        if len(owners) >= 2:
            add_pairs(owners, forced=True)

    candidate_pairs = forced_pairs | {
        pair for pair, count in lexical_counts.items()
        if count >= min_shared_keys
    }
    ordered_pairs = sorted(
        candidate_pairs,
        key=lambda pair: (
            0 if pair in forced_pairs else 1,
            -lexical_counts.get(pair, 0),
            pair[0], pair[1],
        ))

    bridge_batches = []
    current_set = set()
    for left, right in ordered_pairs:
        additions = {left, right} - current_set
        if current_set and len(current_set) + len(additions) > batch_size:
            bridge_batches.append(sorted(current_set))
            current_set = set()
        for value in (left, right):
            current_set.add(value)
    if current_set:
        bridge_batches.append(sorted(current_set))

    seen = set()
    unique_bridges = []
    for batch in bridge_batches:
        marker = tuple(batch)
        if marker and marker not in seen:
            seen.add(marker)
            unique_bridges.append(batch)
    return {
        "base_batches": base_batches,
        "bridge_batches": unique_bridges,
        "candidate_pairs": len(candidate_pairs),
    }


def _same_day_reconcile_batches(
        events, items, batch_size=SAME_DAY_RECONCILE_BATCH_SIZE,
        min_shared_keys=SAME_DAY_MIN_SHARED_KEYS):
    plan = _same_day_reconcile_plan(
        events, items, batch_size=batch_size,
        min_shared_keys=min_shared_keys)
    return [*plan["base_batches"], *plan["bridge_batches"]]


def _merge_same_day_groups(events, groups, items, quality=None):
    quality = quality if quality is not None else new_quality_stats()
    merged_away = set()
    for group in groups:
        if len(group) < 2:
            continue
        primary = group[0]
        absorbed = 0
        for event_index in group[1:]:
            if event_index in merged_away:
                continue
            events[primary]["ids"].extend(events[event_index].get("ids") or [])
            events[primary]["ids"] = cap_same_source(events[primary]["ids"], items)
            merged_away.add(event_index)
            absorbed += 1
        if absorbed:
            events[primary]["same_day_reconciled"] = True
            quality["same_day_duplicates_merged"] += absorbed
    return [event for index, event in enumerate(events) if index not in merged_away]


def reconcile_same_day_events(llm, events, items, quality=None):
    """Merge duplicate same-day events using evidence, with identity-safe fallback."""
    quality = quality if quality is not None else new_quality_stats()
    if len(events) < 2:
        return events
    quality["duplicate_audited_events"] += len(events)
    guard = _same_day_cost_guard(llm)
    plan = _same_day_reconcile_plan(
        events, items,
        min_shared_keys=guard["min_shared_keys"])
    quality["same_day_candidate_pairs"] += plan["candidate_pairs"]
    quality["same_day_bridge_batches"] += len(plan["bridge_batches"])
    parents = list(range(len(events)))

    def find(value):
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    budget_warning_logged = False
    for batch in [*plan["base_batches"], *plan["bridge_batches"]]:
        batch_events = [events[index] for index in batch]
        payload = _same_day_reconcile_payload(batch_events, items)
        if guard["calls"] >= guard["max_calls"]:
            quality["same_day_budget_exhausted"] = True
            quality["same_day_deferred_batches"] += 1
            quality["degraded"] = True
            if not budget_warning_logged:
                log("  同日事件归并达到调用预算，剩余批次使用确定性降级")
                budget_warning_logged = True
            groups = _deterministic_same_day_groups(batch_events, items)
            for group in groups:
                global_group = [batch[index] for index in group]
                for event_index in global_group[1:]:
                    union(global_group[0], event_index)
            continue
        guard["calls"] += 1
        quality["same_day_reconcile_calls"] += 1
        try:
            groups = _validated_same_day_groups(
                llm.json_call(
                    SAME_DAY_RECONCILE_SYSTEM,
                    json.dumps(payload, ensure_ascii=False)),
                len(batch))
        except Exception as exc:
            log(f"  同日事件归并审计批次失败，使用确定性降级: {exc}")
            groups = None
        if groups is None:
            quality["duplicate_audit_failures"] += 1
            quality["degraded"] = True
            groups = _deterministic_same_day_groups(batch_events, items)
        for group in groups:
            global_group = [batch[index] for index in group]
            for event_index in global_group[1:]:
                union(global_group[0], event_index)

    grouped = {}
    for index in range(len(events)):
        grouped.setdefault(find(index), []).append(index)
    groups = sorted(grouped.values(), key=lambda group: group[0])
    before = len(events)
    result = _merge_same_day_groups(events, groups, items, quality)
    if len(result) < before:
        log(f"  同日事件归并了 {before - len(result)} 个重复事件")
    return result


CROSS_DAY_LINE_RECONCILE_SYSTEM = """你是日报的跨天事件线归并审计员。
输入是一批事件线，每条带事件线名、分类、日期区间和逐日进展摘要。
同一条事件线 = 同一件持续发展的具体事情。判据是"是不是同一件事"，不是"是不是同一个主体"。
同一主体的不同事情（例如同一国家的军事冲突与贸易谈判、同一公司的模型发布与人事变动）必须留成不同事件线。
只有当两条线记录的是同一件事在不同日子的进展、彼此重复或交错时才归并。
把握不准就不要合并：漏并只是留下两条线，误并会毁掉事件身份。
必须把每个输入编号恰好放入一个组，包括无需合并的单元素组。
只输出 JSON 对象：{"groups":[[0,3],[1],[2,4]]}。不要输出其他文字。"""

CROSS_DAY_LINE_BATCH_SIZE = 20
# 实测标定：真正的碎片线共享 28-46 个低频键，而符合「同类目+区间重叠」的噪声对
# 绝大多数只共享 0-3 个。取 8 兼顾两侧余量；共享一个键就配对会把整张登记表连成
# 一个巨型连通分量，"特朗普""美国"这类词会当桥。
CROSS_DAY_LINE_MIN_SHARED_KEYS = 8
_LINE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _event_line_span(event):
    """Return the (earliest, latest) dates this line covers, or ("", "")."""
    dates = [str(row.get("date") or "")
             for row in event.get("history") or [] if isinstance(row, dict)]
    dates.extend(str(event.get(key) or "") for key in ("first_seen", "last_seen"))
    dates = sorted(date for date in dates if _LINE_DATE.fullmatch(date))
    return (dates[0], dates[-1]) if dates else ("", "")


def _event_lines_may_merge(left, right):
    """Same category and overlapping spans — necessary, nowhere near sufficient."""
    if (left.get("category") or "") != (right.get("category") or ""):
        return False
    left_span, right_span = _event_line_span(left), _event_line_span(right)
    if not all([*left_span, *right_span]):
        return False
    return left_span[0] <= right_span[1] and right_span[0] <= left_span[1]


def _event_line_keys(event, progress_limit=6):
    """Recall keys used only to pick which lines are worth a model comparison."""
    texts = [str(event.get("title") or "")]
    for row in (event.get("history") or [])[-progress_limit:]:
        if isinstance(row, dict):
            texts.extend((str(row.get("title") or ""), str(row.get("summary") or "")))
    text = unicodedata.normalize("NFKC", " ".join(texts)).casefold()
    keys = set(re.findall(r"[a-z][a-z0-9._-]{2,}", text))
    for run in re.findall(r"[一-鿿]{2,}", text):
        keys.update(run[index:index + 2] for index in range(len(run) - 1))
    return keys


CROSS_SOURCE_NOVELTY_SYSTEM = """你负责执行日报的跨日实质新增门。输入 items 中每条都是今天的候选，
current 是今天来源明确写出的材料，registry 是同类别的既有精选事件线。只能使用输入证据，不得使用常识或联网信息。
逐条选择：different_event（不是同一具体事件）、material_addition（同一事件且有实质新增）、
restatement（同一事件、当前核心事实已被历史明确覆盖且无实质新增）、uncertain（证据不足）。
实质新增包括新结果、关键数字或影响范围变化、政策结论、正式更正，或首次官方确认/否认使可信状态变化。
新来源、新标题、背景或参数解释、评论分析、重复基准结果不算实质新增。
只有证据明确时才能选 restatement；拿不准必须选 uncertain。
只输出 JSON：{"items":[{"idx":0,"decision":"different_event|material_addition|restatement|uncertain",
"registry_index":0或null,"reason":"简短证据理由"}]}。每个 idx 必须恰好返回一次，不得增加字段。"""


def cross_source_event_key(event):
    """Stable within one run and changes whenever same-day reconciliation changes."""
    indexes = [index for index in (event.get("ids") or [])
               if type(index) is int]
    return tuple(sorted(set(indexes)))


def _cross_source_history_is_pick(row):
    return bool(re.fullmatch(
        r"\d{4}-\d{2}-\d{2}:pick-[A-Za-z0-9_-]+",
        str((row or {}).get("item_ref") or "")))


def _cross_source_days_since(date_str, prior):
    try:
        return (datetime.strptime(date_str, "%Y-%m-%d")
                - datetime.strptime(str(prior), "%Y-%m-%d")).days
    except (TypeError, ValueError):
        return 10 ** 6


def _cross_source_current_projection(event, items):
    reports = []
    for index in event.get("ids") or []:
        if type(index) is not int or not 0 <= index < len(items):
            continue
        item = items[index]
        reports.append({
            "title": str(item.get("title") or "")[:240],
            "summary": str(item.get("desc") or "")[:600],
            "source": str(item.get("source") or "")[:120],
        })
    return {
        "category": str(event.get("category") or ""),
        "title": str(event.get("title") or "")[:240],
        "summary": str(event.get("summary") or "")[:600],
        "reports": reports[:6],
    }


def _cross_source_relevant_history(line, current_keys, limit=7):
    rows = [row for row in (line.get("history") or [])
            if isinstance(row, dict) and _cross_source_history_is_pick(row)]
    if not rows:
        return []
    ranked = sorted(
        enumerate(rows),
        key=lambda pair: (
            -len(current_keys.intersection(_event_line_keys({
                "title": pair[1].get("title", ""), "history": [pair[1]]}))),
            pair[0],
        ))
    chosen = {0, len(rows) - 1}
    for index, _row in ranked:
        if len(chosen) >= limit:
            break
        chosen.add(index)
    return [rows[index] for index in sorted(chosen)[:limit]]


class CrossSourceNoveltyGate:
    """Fail-open reviewer for cross-source restatements of prior picks."""

    def __init__(self, llm, registry, data_dir, date_str, cfg, stats=None):
        self.llm = llm
        self.data_dir = Path(data_dir)
        self.date_str = date_str
        self.stats = stats if stats is not None else new_cross_source_novelty_stats()
        guard = (cfg or {}).get("cost_guard") or {}
        self.batch_size = max(1, int(
            guard.get("cross_source_novelty_batch_size", 20)))
        self.max_calls = max(0, int(
            guard.get("cross_source_novelty_max_calls", 8)))
        self.calls = 0
        self.decisions = {}
        self.daily_cache = {}
        self.lines = []
        for line in (registry or {}).get("events") or []:
            if not isinstance(line, dict):
                continue
            prior_history = [
                row for row in (line.get("history") or [])
                if isinstance(row, dict)
                and 0 < _cross_source_days_since(date_str, row.get("date")) < 10 ** 6
            ]
            if not prior_history:
                continue
            historical_line = {**line, "history": prior_history,
                               "last_seen": max(
                                   str(row.get("date") or "")
                                   for row in prior_history)}
            age = _cross_source_days_since(
                date_str, historical_line.get("last_seen"))
            if not 0 <= age <= 60:
                continue
            if not any(_cross_source_history_is_pick(row)
                       for row in prior_history):
                continue
            self.lines.append(historical_line)

    def _history_projection(self, row):
        projection = {
            "date": str(row.get("date") or ""),
            "title": str(row.get("title") or "")[:180],
            "summary": str(row.get("summary") or "")[:320],
            "status": str(row.get("news_status") or ""),
            "item_ref": str(row.get("item_ref") or ""),
        }
        match = re.fullmatch(
            r"(\d{4}-\d{2}-\d{2}):(pick-[A-Za-z0-9_-]+)",
            projection["item_ref"])
        if not match:
            return projection
        day, item_id = match.groups()
        if day not in self.daily_cache:
            self.daily_cache[day] = read_daily_payload(
                self.data_dir / "daily" / f"{day}.js") or {}
        prior = next((item for item in self.daily_cache[day].get("items") or []
                      if isinstance(item, dict) and item.get("id") == item_id), None)
        if not prior:
            return projection
        for field, limit in (("title", 180), ("summary", 320),
                             ("detail", 600), ("status", 80)):
            if prior.get(field):
                projection[field] = str(prior[field])[:limit]
        return projection

    def _shortlist(self, event, items):
        current = _cross_source_current_projection(event, items)
        key_event = {
            "title": " ".join([
                current["title"], current["summary"],
                *(report["title"] + " " + report["summary"]
                  for report in current["reports"]),
            ]),
            "history": [],
        }
        current_keys = _event_line_keys(key_event)
        candidates = []
        for line in self.lines:
            if line.get("category") != event.get("category"):
                continue
            overlap = len(current_keys.intersection(_event_line_keys(line)))
            if overlap <= 0:
                continue
            candidates.append((overlap, str(line.get("last_seen") or ""), line))
        candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)
        projected = []
        for _overlap, _last_seen, line in candidates[:6]:
            history = _cross_source_relevant_history(line, current_keys)
            projected.append({
                "event_id": str(line.get("event_id") or ""),
                "title": str(line.get("title") or "")[:240],
                "category": str(line.get("category") or ""),
                "history": [self._history_projection(row) for row in history],
            })
        return current, projected

    def _record_fail_open(self, keys, *, deferred=False):
        count = 0
        for key in keys:
            if key in self.decisions:
                continue
            self.decisions[key] = ("uncertain", None)
            count += 1
        if deferred:
            self.stats["cross_source_novelty_deferred"] += count
            self.stats["cross_source_novelty_budget_exhausted"] = True
        else:
            self.stats["cross_source_novelty_failures"] += count
        if count:
            self.stats["degraded"] = True

    def _validate(self, raw, expected, shortlist_sizes):
        if not isinstance(raw, dict) or set(raw) != {"items"}:
            return None
        rows = raw.get("items")
        if not isinstance(rows, list):
            return None
        by_index = {}
        allowed = {"different_event", "material_addition", "restatement", "uncertain"}
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                    "idx", "decision", "registry_index", "reason"}:
                return None
            index = row.get("idx")
            if type(index) is not int or not 0 <= index < expected or index in by_index:
                return None
            decision = row.get("decision")
            registry_index = row.get("registry_index")
            reason = row.get("reason")
            if (decision not in allowed or not isinstance(reason, str)
                    or not reason.strip() or len(reason.strip()) > 240):
                return None
            if decision in {"material_addition", "restatement"}:
                if (type(registry_index) is not int
                        or not 0 <= registry_index < shortlist_sizes[index]):
                    return None
            elif registry_index is not None and (
                    type(registry_index) is not int
                    or not 0 <= registry_index < shortlist_sizes[index]):
                return None
            by_index[index] = row
        return by_index if set(by_index) == set(range(expected)) else None

    def _review_batch(self, batch):
        keys = [entry[0] for entry in batch]
        payload = self._batch_payload(batch)
        validated = None
        attempts = 0
        while (attempts < 2 and self.calls < self.max_calls
               and validated is None):
            attempts += 1
            self.calls += 1
            self.stats["cross_source_novelty_calls"] += 1
            try:
                raw = self.llm.json_call(
                    CROSS_SOURCE_NOVELTY_SYSTEM,
                    json.dumps(payload, ensure_ascii=False))
                validated = self._validate(
                    raw, len(batch), [len(entry[2]) for entry in batch])
            except Exception as exc:
                log(f"  跨日实质新增门调用失败，候选保留: {exc}")
                self._record_fail_open(keys)
                return
            if validated is not None:
                break
            if attempts < 2 and self.calls < self.max_calls:
                log("  跨日实质新增门响应非法，重试一次")
                continue
            break
        if validated is None:
            if self.calls >= self.max_calls:
                self.stats["cross_source_novelty_budget_exhausted"] = True
            self._record_fail_open(keys)
            return
        for index, key in enumerate(keys):
            row = validated[index]
            decision = row["decision"]
            line = (batch[index][2][row["registry_index"]]
                    if type(row.get("registry_index")) is int else None)
            self.decisions[key] = (decision, line)
            if decision == "restatement":
                self.stats["cross_source_restatements"] += 1
            elif decision == "material_addition":
                self.stats["cross_source_material_additions"] += 1
            elif decision == "uncertain":
                self.stats["cross_source_novelty_failures"] += 1
                self.stats["degraded"] = True

    def review(self, events, items):
        pending = []
        event_by_key = {}
        for event in events:
            key = cross_source_event_key(event)
            event_by_key[key] = event
            if key in self.decisions:
                continue
            current, shortlist = self._shortlist(event, items)
            if not shortlist:
                self.decisions[key] = ("different_event", None)
                continue
            pending.append((key, current, shortlist))
        self.stats["cross_source_novelty_candidates"] += len(pending)

        batches = []
        batch = []
        for entry in pending:
            proposed = [*batch, entry]
            oversized = len(json.dumps(
                self._batch_payload(proposed), ensure_ascii=False)) \
                > CROSS_SOURCE_NOVELTY_MAX_PROMPT_CHARS
            if batch and (len(batch) >= self.batch_size or oversized):
                batches.append(batch)
                batch = []
                proposed = [entry]
            if len(json.dumps(
                    self._batch_payload(proposed), ensure_ascii=False)) \
                    > CROSS_SOURCE_NOVELTY_MAX_PROMPT_CHARS:
                log("  跨日实质新增门证据包过大，候选保留")
                self._record_fail_open([entry[0]])
                continue
            batch = proposed
        if batch:
            batches.append(batch)

        for batch in batches:
            if self.calls >= self.max_calls:
                self._record_fail_open([entry[0] for entry in batch], deferred=True)
                continue
            self._review_batch(batch)
        restatements = []
        hints = {}
        for key, event in event_by_key.items():
            decision, line = self.decisions.get(key, ("uncertain", None))
            if decision == "restatement":
                restatements.append(event)
            elif decision == "material_addition" and line and line.get("event_id"):
                hints[key] = line["event_id"]
        return {"restatements": restatements, "material_hints": hints}

    @staticmethod
    def _batch_payload(batch):
        return {"items": [
            {"idx": index, "current": current, "registry": registry}
            for index, (_key, current, registry) in enumerate(batch)
        ]}


def _cross_day_line_batches(events, batch_size=CROSS_DAY_LINE_BATCH_SIZE):
    """Pair only lines that share low-frequency vocabulary.

    Same category with an overlapping span describes almost every pair in a
    registry that spans a few weeks across five categories, so using that alone
    ships the whole registry to the auditor every single day. Mirror the
    same-day path: low-frequency title/summary keys choose the candidates, and
    the model still makes the actual call."""
    batch_size = max(2, int(batch_size))
    keys_by_index = {index: _event_line_keys(event)
                     for index, event in enumerate(events)}
    key_owners = {}
    for index, keys in keys_by_index.items():
        for key in keys:
            key_owners.setdefault(key, set()).add(index)

    shared_counts = {}
    for owners in key_owners.values():
        if not 2 <= len(owners) <= SAME_DAY_BLOCK_MAX_FREQUENCY:
            continue
        ordered = sorted(owners)
        for position, left in enumerate(ordered):
            for right in ordered[position + 1:]:
                shared_counts[(left, right)] = shared_counts.get((left, right), 0) + 1
    pairs = {pair for pair, count in shared_counts.items()
             if count >= CROSS_DAY_LINE_MIN_SHARED_KEYS
             and _event_lines_may_merge(events[pair[0]], events[pair[1]])}

    # 把配对连成连通分量，再按批次上限切分，避免同一组重复被拆到两批里。
    adjacency = {}
    for left, right in pairs:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
    batches, seen = [], set()
    for start in sorted(adjacency):
        if start in seen:
            continue
        component, queue = [], [start]
        seen.add(start)
        while queue:
            current = queue.pop()
            component.append(current)
            for neighbour in sorted(adjacency[current]):
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        component.sort()
        for offset in range(0, len(component), batch_size):
            batch = component[offset:offset + batch_size]
            if len(batch) >= 2:
                batches.append(batch)
    return batches


def _cross_day_line_payload(events, batch, progress_limit=6):
    payload = []
    for position, index in enumerate(batch):
        event = events[index]
        span = _event_line_span(event)
        history = [row for row in event.get("history") or [] if isinstance(row, dict)]
        payload.append({
            "index": position,
            "name": str(event.get("title") or "")[:180],
            "category": str(event.get("category") or ""),
            "span": {"from": span[0], "to": span[1]},
            "progress": [{
                "date": str(row.get("date") or ""),
                "title": str(row.get("title") or "")[:180],
                "summary": str(row.get("summary") or "")[:240],
            } for row in history[-progress_limit:]],
        })
    return payload


def _merge_event_lines(events, group):
    """Fold a group of lines into the one that started earliest; return its index."""
    ordered = sorted(group,
                     key=lambda index: (_event_line_span(events[index])[0], index))
    keeper = ordered[0]
    primary = events[keeper]
    rows_by_date = {}
    # 倒序遍历让 keeper 最后写入：同一天有两行时保留身份线自己的那行。
    for index in reversed(ordered):
        for row in events[index].get("history") or []:
            if isinstance(row, dict) and row.get("date"):
                rows_by_date[str(row["date"])] = row
    primary["history"] = [rows_by_date[date] for date in sorted(rows_by_date)]
    spans = [_event_line_span(events[index]) for index in ordered]
    starts = [span[0] for span in spans if span[0]]
    ends = [span[1] for span in spans if span[1]]
    if starts:
        primary["first_seen"] = min(starts)
    if ends:
        primary["last_seen"] = max(ends)
    if any(events[index].get("status") == "active" for index in ordered):
        primary["status"] = "active"
    if any(events[index].get("pinned") for index in ordered):
        primary["pinned"] = True
    primary["line_reconciled"] = True
    return keeper


def reconcile_registry_events(llm, events, quality=None):
    """Merge registry lines that track the same continuing thing across days.

    Audit failure never merges: a missed merge leaves two lines, a wrong merge
    destroys event identity."""
    quality = quality if quality is not None else new_quality_stats()
    if len(events) < 2:
        return events
    parents = list(range(len(events)))

    def find(value):
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for batch in _cross_day_line_batches(events):
        quality["event_lines_audited"] += len(batch)
        payload = _cross_day_line_payload(events, batch)
        try:
            groups = _validated_same_day_groups(
                llm.json_call(CROSS_DAY_LINE_RECONCILE_SYSTEM,
                              json.dumps(payload, ensure_ascii=False)),
                len(batch))
        except Exception as exc:
            log(f"  跨天事件线归并审计批次失败，本批不合并: {exc}")
            groups = None
        if groups is None:
            quality["event_line_audit_failures"] += 1
            quality["degraded"] = True
            continue
        for group in groups:
            global_group = [batch[position] for position in group]
            for index in global_group[1:]:
                union(global_group[0], index)

    grouped = {}
    for index in range(len(events)):
        grouped.setdefault(find(index), []).append(index)
    merged_away = set()
    for group in sorted(grouped.values(), key=lambda group: group[0]):
        if len(group) < 2:
            continue
        keeper = _merge_event_lines(events, group)
        merged_away.update(index for index in group if index != keeper)
        quality["event_lines_merged"] += len(group) - 1
    if merged_away:
        log(f"  跨天事件线归并了 {len(merged_away)} 条重复事件线")
    return [event for index, event in enumerate(events) if index not in merged_away]


def reconcile_stale_event_lines(llm, events, date_str, quality=None):
    """Reconcile only lines today did not write.

    Today's lines carry the event_id back-filled into the daily items and the
    continuity verdict from the continuity gate (ADR 0002). Merging them here
    would silently re-decide a verdict that was independently verified, so this
    pass is housekeeping over the historical registry only. A fragment created
    today merges on a later day, once it stops receiving picks."""
    touched, stale = [], []
    for event in events:
        rows = event.get("history") or []
        if any(isinstance(row, dict) and row.get("date") == date_str
               for row in rows):
            touched.append(event)
        else:
            stale.append(event)
    if len(stale) < 2:
        return events
    reconciled = reconcile_registry_events(llm, stale, quality)
    if len(reconciled) == len(stale):
        return events
    kept = {id(event) for event in reconciled} | {id(event) for event in touched}
    return [event for event in events if id(event) in kept]


def review_reader_facing_duplicates(llm, events, picked, secondary, items, quality=None):
    """Reconcile the bounded reader-facing shortlist and remove absorbed events."""
    shortlist, seen = [], set()
    for event in [*(picked or []), *(secondary or [])]:
        marker = id(event)
        if marker not in seen:
            seen.add(marker)
            shortlist.append(event)
    if len(shortlist) < 2:
        return events, 0
    before = list(shortlist)
    reviewed = reconcile_same_day_events(llm, shortlist, items, quality)
    retained = {id(event) for event in reviewed}
    removed = {id(event) for event in before if id(event) not in retained}
    return [event for event in events if id(event) not in removed], len(removed)


COHESION_AUDIT_SYSTEM = """你是新闻事件聚类质检员。给你一个已聚类事件及其中的原始报道。
逐条核对是否确实是同一主体、同一具体事实。主题相近、同属一家公司或同属一个地区都不能合并。
可把错误聚类拆成多个组，并校正每组标题、五类分类及五维评分。
只输出 JSON 对象：
{"groups":[{"ids":[原始条目编号],"category":"ai|tech|finance|society|world",
"dims":{"impact":0-10,"novelty":0-10,"substance":0-10,"evidence":0-10,"durability":0-10},
"title":"只描述一件事的中文标题"}]}
每个输入编号必须恰好出现一次，不得新增、遗漏或重复。"""


def _audit_singletons(event, items):
    """Conservative cohesion fallback: one raw report per event, neutral evidence."""
    out = []
    for item_id in event.get("ids", []):
        dims = {d: float((event.get("dims") or {}).get(d, 3.0)) for d in DIMS}
        dims["evidence"] = QUALITY_NEUTRAL_EVIDENCE
        out.append({
            "ids": [item_id],
            "category": event.get("category") if event.get("category") in CATEGORIES else "world",
            "dims": dims,
            "title": items[item_id].get("title") or event.get("title", ""),
            "cohesion_audit": "degraded",
        })
    return out


def _validated_audit_groups(raw, expected_ids):
    if not isinstance(raw, dict) or not isinstance(raw.get("groups"), list):
        return None
    groups, seen = [], []
    for group in raw["groups"]:
        if not isinstance(group, dict):
            return None
        ids = group.get("ids")
        if (not isinstance(ids, list) or not ids
                or any(not isinstance(i, int) or isinstance(i, bool) for i in ids)):
            return None
        category = group.get("category")
        title = str(group.get("title", "")).strip()
        raw_dims = group.get("dims")
        if category not in CATEGORIES or not title or not isinstance(raw_dims, dict):
            return None
        dims = {}
        for dim in DIMS:
            value = raw_dims.get(dim)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return None
            dims[dim] = max(0.0, min(10.0, float(value)))
        seen.extend(ids)
        groups.append({"ids": ids, "category": category, "dims": dims, "title": title,
                       "cohesion_audit": "passed"})
    if (len(expected_ids) != len(set(expected_ids))
            or len(seen) != len(expected_ids)
            or len(seen) != len(set(seen))
            or set(seen) != set(expected_ids)):
        return None
    order = {item_id: index for index, item_id in enumerate(expected_ids)}
    for group in groups:
        group["ids"].sort(key=order.__getitem__)
    groups.sort(key=lambda group: order[group["ids"][0]])
    return groups


def audit_event_cohesion(llm, events, items, quality=None):
    """Recheck every multi-report event after cross-batch clustering.

    An invalid result is not trusted partially: the affected event is split into
    singletons so it cannot retain a cross-source score bonus.
    """
    quality = quality if quality is not None else new_quality_stats()
    audited = []
    for event in events:
        ids = list(event.get("ids") or [])
        if len(ids) < 2:
            audited.append(event)
            continue
        quality["audited_events"] += 1
        reports = [{
            "id": i,
            "title": items[i].get("title", ""),
            "summary": items[i].get("desc", ""),
            "source": items[i].get("source", ""),
        } for i in ids]
        user = json.dumps({
            "event_title": event.get("title", ""),
            "event_category": event.get("category", ""),
            "reports": reports,
        }, ensure_ascii=False)
        try:
            groups = _validated_audit_groups(
                llm.json_call(COHESION_AUDIT_SYSTEM, user), ids)
        except Exception as exc:
            log(f"  事件凝聚度审计失败，拆回单条: {exc}")
            groups = None
        if groups is None:
            quality["split_events"] += 1
            quality["degraded"] = True
            audited.extend(_audit_singletons(event, items))
            continue
        if len(groups) > 1:
            quality["split_events"] += 1
        audited.extend(groups)
    return audited, quality


def detect_evidence_risks(event, event_items):
    """Return all fixed evidence-risk flags without an additional model call."""
    text = " ".join(str(value or "") for value in (
        event.get("title"), event.get("summary"), event.get("status"),
        *(it.get("title") for it in event_items), *(it.get("desc") for it in event_items),
    )).lower()

    def has(*terms):
        return any(term in text for term in terms)

    politics = event.get("category") == "world" or has(
        "政府", "总统", "首相", "选举", "制裁", "外交", "领土", "地缘", "政变",
        "government", "president", "election", "sanction", "diplomatic")
    conflict = has("战争", "冲突", "袭击", "空袭", "导弹", "军队", "武装", "停火",
                   "war", "armed conflict", "attack", "airstrike", "missile", "ceasefire")
    legal = event.get("status") in ("有争议", "仅传言") or has(
        "指控", "起诉", "检方", "涉嫌", "诉讼", "调查", "allegation", "accused",
        "charged", "lawsuit", "prosecutor", "investigation")
    safety = has("死亡", "受伤", "坍塌", "事故", "地震", "火灾", "疫情", "疾病", "药品",
                 "公共安全", "health", "killed", "death", "injured", "collapse", "earthquake",
                 "fire", "outbreak", "disease", "public safety")
    has_number = bool(re.search(
        r"(?<!\w)\d[\d,.]*(?:\s*%|\s*(?:亿|万|人|名|美元|元|billion|million))?", text))
    number = has_number and (safety or has(
        "%", "亿美元", "亿元", "万人", "营收", "市值", "损失", "影响", "占比",
        "billion", "million", "revenue", "gdp", "market value", "affected"))
    return dict(zip(EVIDENCE_RISK_FLAGS, (politics, conflict, legal, safety, number)))


def _event_is_high_risk(event):
    return any(bool((event.get("risk_flags") or {}).get(name))
               for name in EVIDENCE_RISK_FLAGS)


def _title_tokens(value):
    return set(re.findall(r"[a-z0-9]+|[\u3400-\u9fff]{2,}", str(value or "").lower()))


def _text_similarity(left_value, right_value):
    left = _title_tokens(left_value)
    right = _title_tokens(right_value)
    overlap = len(left & right) / max(len(left | right), 1)
    sequence = SequenceMatcher(None, str(left_value or "").lower(),
                               str(right_value or "").lower()).ratio()
    return max(overlap, sequence)


def _candidate_similarity(event, event_items, candidate):
    candidate_text = str(candidate.get("title") or "")
    selected_texts = [event.get("title", "")]
    selected_texts.extend(str(item.get("title") or "") for item in event_items)
    return max((_text_similarity(text, candidate_text) for text in selected_texts), default=0.0)


def _within_corroboration_window(event_items, candidate, hours=48):
    try:
        candidate_time = datetime.fromisoformat(str(candidate.get("time") or "").replace("Z", "+00:00"))
        known_times = [datetime.fromisoformat(str(it.get("time") or "").replace("Z", "+00:00"))
                       for it in event_items if it.get("time")]
        return not known_times or min(abs((candidate_time - known).total_seconds())
                                      for known in known_times) <= hours * 3600
    except (TypeError, ValueError):
        return False


def corroborate_high_risk_events(events, items, raw_pool, quality=None):
    """Merge deterministic, credible matches from the already-fetched prefilter pool."""
    quality = quality if quality is not None else new_quality_stats()
    for event in events:
        event_items = [items[i] for i in event.get("ids", []) if 0 <= i < len(items)]
        event["risk_flags"] = detect_evidence_risks(event, event_items)
        publishers = {it.get("source_id") for it in event_items if it.get("source_id")}
        known_chains = {
            chain for chain in (_trusted_evidence_chain(item) for item in event_items)
            if chain
        }
        if not _event_is_high_risk(event) or len(known_chains) != 1:
            continue
        quality["high_risk_single_publisher"] += 1
        known_urls = {canonical_news_url(it.get("url")) for it in event_items}
        known_source_ids = set(publishers)
        known_publishers = {
            str(item.get("source") or "").strip().casefold()
            for item in event_items if str(item.get("source") or "").strip()
        }
        ranked = []
        for position, candidate in enumerate(raw_pool):
            candidate_chain = _trusted_evidence_chain(candidate)
            candidate_publisher = str(candidate.get("source") or "").strip().casefold()
            if (not known_chains
                    or not candidate_chain
                    or candidate_chain in known_chains
                    or candidate.get("source_id") in known_source_ids
                    or not candidate_publisher
                    or candidate_publisher in known_publishers
                    or canonical_news_url(candidate.get("url")) in known_urls
                    or candidate.get("source_type") == "opinion"
                    or float(candidate.get("credibility", 0)) < 7
                    or not _within_corroboration_window(event_items, candidate)):
                continue
            quality["corroboration_candidates"] += 1
            similarity = _candidate_similarity(event, event_items, candidate)
            if similarity >= 0.58:
                ranked.append((-similarity, position, candidate))
        for _score, _position, candidate in sorted(ranked)[:3]:
            candidate_chain = _trusted_evidence_chain(candidate)
            candidate_source_id = candidate.get("source_id")
            candidate_publisher = str(candidate.get("source") or "").strip().casefold()
            candidate_url = canonical_news_url(candidate.get("url"))
            if (not candidate_chain
                    or candidate_chain in known_chains
                    or candidate_source_id in known_source_ids
                    or not candidate_publisher
                    or candidate_publisher in known_publishers
                    or candidate_url in known_urls):
                continue
            items.append(dict(candidate))
            event["ids"].append(len(items) - 1)
            known_source_ids.add(candidate_source_id)
            known_publishers.add(candidate_publisher)
            known_urls.add(candidate_url)
            known_chains.add(candidate_chain)
            quality["corroboration_matches"] += 1
            if len(event["ids"]) >= 4:
                break
    return events


def _serialized_source_ids(event, items, limit=5):
    """Return the exact stable source order shared by acquisition and output."""
    ids = [i for i in event.get("ids", [])
           if isinstance(i, int) and not isinstance(i, bool)
           and 0 <= i < len(items)]
    ids.sort(key=lambda i: (
        items[i].get("source_type") != "fact",
        -float(items[i].get("credibility", 0)),
        str(items[i].get("source_id") or "").strip().casefold(),
        canonical_news_url(items[i].get("url")),
        str(items[i].get("source") or "").strip().casefold(),
        i,
    ))
    selected, seen_urls, seen_publishers = [], set(), set()
    for index in ids:
        url = items[index].get("url", "")
        publisher = str(items[index].get("source") or "").strip().casefold()
        if not publisher or url in seen_urls or publisher in seen_publishers:
            continue
        seen_urls.add(url)
        seen_publishers.add(publisher)
        selected.append(index)
        if len(selected) >= limit:
            break
    return selected


def _trusted_evidence_chain(item):
    provenance = str(item.get("provenance") or "").strip().lower()
    family = str(item.get("source_family") or "").strip().casefold()
    return family if family and provenance in TRUSTED_PROVENANCE else None


def apply_evidence_contract(event, items):
    """Attach the public evidence summary while conservatively counting chains."""
    event_items = [items[i] for i in _serialized_source_ids(event, items, limit=4)]
    bases = [it.get("evidence_basis", "snippet") for it in event_items]
    if bases and all(basis == "fulltext" for basis in bases):
        basis = "fulltext"
    elif bases and any(value == "fulltext" for value in bases):
        basis = "mixed"
    else:
        basis = "snippet"
    publishers = {str(it.get("source") or "").strip().casefold() for it in event_items
                  if str(it.get("source") or "").strip()}
    independent = set()
    for item in event_items:
        chain = _trusted_evidence_chain(item)
        if chain:
            independent.add(chain)
    event["evidence"] = {
        "basis": basis,
        "publisher_count": len(publishers),
        "independent_chain_count": len(independent),
        "degraded": basis != "fulltext",
    }
    return event["evidence"]


def acquire_event_evidence(events, items, quality=None, request_get=None,
                           extractor=None, resolver=None):
    """Fetch at most four sources per event with a global concurrency ceiling of six."""
    quality = quality if quality is not None else new_quality_stats()
    source_ids = list(dict.fromkeys(
        i for event in events for i in _serialized_source_ids(event, items, limit=4)))

    def fetch(index):
        return index, fetch_article_evidence(
            items[index], request_get=request_get, extractor=extractor, resolver=resolver)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for index, result in pool.map(fetch, source_ids):
            items[index]["evidence_basis"] = result["evidence_basis"]
            items[index]["evidence_text"] = result["evidence_text"]
            quality["article_fetch_attempts"] += 1
            quality["article_http_requests"] += result["attempts"]
            quality["article_fetch_retries"] += result.get("retries", 0)
            if result["evidence_basis"] == "fulltext":
                quality["article_fetch_successes"] += 1
                quality["evidence_fulltext_sources"] += 1
            else:
                quality["evidence_snippet_sources"] += 1
    for event in events:
        apply_evidence_contract(event, items)
    return events, quality


# ----------------------------------------------------------------
# 5. 评分（代码合成最终分）+ 阈值制精选
# ----------------------------------------------------------------

SCORE_HISTORY_VERSION = 1
SCORE_HISTORY_KEEP_DAYS = 30


def _score_history_path(data_dir):
    return Path(data_dir) / "score_history.json"


def _nearest_rank_percentile(values, percentile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("percentile requires at least one value")
    rank = max(1, math.ceil((float(percentile) / 100.0) * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=str(path.parent),
                prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            json.dump(payload, handle, ensure_ascii=False, indent=1)
            handle.write("\n")
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)


def _atomic_replace_texts(artifacts):
    """Replace a set of UTF-8 files as one recoverable publication unit."""
    entries = []
    replaced = []
    try:
        for target, content in artifacts.items():
            target = Path(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            original = target.read_bytes() if target.exists() else None
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=str(target.parent),
                    prefix=f".{target.name}.", suffix=".tmp",
                    delete=False) as handle:
                handle.write(content)
                temp_path = Path(handle.name)
            entries.append((target, temp_path, original))

        for target, temp_path, original in entries:
            os.replace(temp_path, target)
            replaced.append((target, original))

    except Exception:
        for target, original in reversed(replaced):
            if original is None:
                target.unlink(missing_ok=True)
                continue
            rollback_path = None
            try:
                with tempfile.NamedTemporaryFile(
                        mode="wb", dir=str(target.parent),
                        prefix=f".{target.name}.rollback.", suffix=".tmp",
                        delete=False) as handle:
                    handle.write(original)
                    rollback_path = Path(handle.name)
                os.replace(rollback_path, target)
                rollback_path = None
            finally:
                if rollback_path is not None:
                    rollback_path.unlink(missing_ok=True)
        raise
    finally:
        for _target, temp_path, _original in entries:
            temp_path.unlink(missing_ok=True)


def _valid_history_scores(raw):
    if not isinstance(raw, list):
        return []
    scores = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if math.isfinite(float(value)):
            scores.append(float(value))
    return scores


def resolve_pick_threshold(cfg, data_dir, date_str):
    """Resolve today's threshold from prior production days only."""
    static_threshold = int(cfg.get("pick_threshold", 68))
    dynamic = cfg.get("pick_dynamic") or {}
    offset = max(0, int(dynamic.get("backfill_offset", 8)))
    base = {
        "threshold": static_threshold,
        "source": "static_disabled",
        "history_days": 0,
        "quality_floor": max(5, static_threshold - offset),
    }
    if not dynamic.get("enabled", False):
        return base

    history_file = _score_history_path(data_dir)
    history = {"version": SCORE_HISTORY_VERSION, "days": {}}
    invalid_history = False
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
            if (not isinstance(history, dict)
                    or history.get("version") != SCORE_HISTORY_VERSION
                    or not isinstance(history.get("days"), dict)):
                raise ValueError("unsupported score history schema")
        except Exception as exc:
            invalid_history = True
            print(f"::warning::score_history.json 读取失败，动态精选线回退静态值: {exc}",
                  flush=True)
            history = {"version": SCORE_HISTORY_VERSION, "days": {}}

    window_days = max(1, int(dynamic.get("window_days", 14)))
    percentile = max(1.0, min(100.0, float(dynamic.get("percentile", 75))))
    day_values = []
    prior_days = [day for day in sorted(history["days"]) if day < date_str]
    for day in prior_days[-window_days:]:
        record = history["days"].get(day)
        if not isinstance(record, dict):
            continue
        scores = _valid_history_scores(record.get("eligible_scores"))
        if scores:
            day_values.append(_nearest_rank_percentile(scores, percentile))

    base["history_days"] = len(day_values)
    minimum_days = max(1, int(dynamic.get("min_history_days", 5)))
    if invalid_history:
        base["source"] = "fallback_invalid_history"
        return base
    if len(day_values) < minimum_days:
        base["source"] = "fallback_insufficient_history"
        return base

    clamp = dynamic.get("clamp") or [66, 82]
    if not isinstance(clamp, (list, tuple)) or len(clamp) != 2:
        clamp = [66, 82]
    lower, upper = sorted((int(clamp[0]), int(clamp[1])))
    threshold = int(math.floor(float(median(day_values)) + 0.5))
    threshold = max(lower, min(upper, threshold))
    return {
        "threshold": threshold,
        "source": "dynamic_history",
        "history_days": len(day_values),
        "quality_floor": max(5, threshold - offset),
    }


def save_score_history(data_dir, date_str, events, keep_days=SCORE_HISTORY_KEEP_DAYS):
    """Persist eligible event scores idempotently; failures never block publishing."""
    history_file = _score_history_path(data_dir)
    history = {"version": SCORE_HISTORY_VERSION, "days": {}}
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
            if (not isinstance(history, dict)
                    or history.get("version") != SCORE_HISTORY_VERSION
                    or not isinstance(history.get("days"), dict)):
                raise ValueError("unsupported score history schema")
        except Exception as exc:
            print(f"::warning::score_history.json 读取失败，将从当天重建: {exc}", flush=True)
            history = {"version": SCORE_HISTORY_VERSION, "days": {}}
    scores = []
    for event in events:
        value = event.get("score")
        if event.get("opinion_only") or isinstance(value, bool) \
                or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            continue
        scores.append(int(round(float(value))))
    history["days"][date_str] = {"eligible_scores": scores}
    keep_days = max(1, int(keep_days))
    for old in sorted(history["days"])[:-keep_days]:
        del history["days"][old]
    try:
        _atomic_write_json(history_file, history)
        return True
    except Exception as exc:
        print(f"::warning::score_history.json 写入失败，当天选材将回退静态线: {exc}",
              flush=True)
        return False


def finalize_selection_gate_metrics(selection_stats, picked, cfg):
    """Add deterministic acceptance inputs to the existing selection metrics."""
    threshold = selection_stats.get("threshold")
    quality_floor = selection_stats.get("quality_floor")
    selection_stats["picked_count"] = len(picked)
    selection_stats["selected_below_quality_floor"] = sum(
        1 for event in picked
        if (isinstance(event.get("score"), (int, float))
            and not isinstance(event.get("score"), bool)
            and isinstance(quality_floor, (int, float))
            and not isinstance(quality_floor, bool)
            and event["score"] < quality_floor))
    selection_stats["selected_opinion_only"] = sum(
        1 for event in picked if event.get("opinion_only") is True)

    category_counts = {
        category: sum(1 for event in picked if event.get("category") == category)
        for category in CATEGORIES
    }
    selection_stats["category_counts"] = category_counts
    qualified_supply = selection_stats.get("qualified_supply") or {}
    min_per = max(0, int(cfg.get("min_per_category", 2)))
    max_per_category = cfg.get("max_per_category") or {}
    violations = 0
    for category in CATEGORIES:
        cap = max_per_category.get(category)
        reserve_limit = min_per if cap is None else min(min_per, max(0, int(cap)))
        available = qualified_supply.get(category, 0)
        available = available if type(available) is int and available >= 0 else 0
        required = min(reserve_limit, available)
        if category_counts[category] < required:
            violations += 1
    selection_stats["category_reservation_violations"] = violations

    clamp = (cfg.get("pick_dynamic") or {}).get("clamp")
    clamp_valid = (isinstance(clamp, (list, tuple)) and len(clamp) == 2
                   and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                           and math.isfinite(float(value)) for value in clamp)
                   and float(clamp[0]) <= float(clamp[1]))
    selection_stats["threshold_clamp"] = (
        [int(clamp[0]), int(clamp[1])] if clamp_valid else [])
    selection_stats["threshold_clamp_valid"] = bool(clamp_valid)
    selection_stats["threshold_in_clamp"] = bool(
        clamp_valid and isinstance(threshold, (int, float))
        and not isinstance(threshold, bool)
        and clamp[0] <= threshold <= clamp[1])
    return selection_stats


def score_and_select(events, items, cfg, effective_threshold=None, selection_stats=None):
    weights = cfg.get("interest_weights", {})
    scoring = cfg.get("scoring", {})
    dim_w = scoring.get("dim_weights", {})
    dim_w = {d: float(dim_w.get(d, 0.2)) for d in DIMS}
    tier_mult = scoring.get("tier_multipliers", {"T1": 1.0, "T1.5": 0.93, "T2": 0.83})
    threshold = int(effective_threshold if effective_threshold is not None
                    else cfg.get("pick_threshold", 68))

    for ev in events:
        # 事件层级 = 其所有来源中最高的层级（官方/一线优先）
        best_tier = min((items[i]["tier"] for i in ev["ids"]),
                        key=lambda t: TIER_ORDER.get(t, 2))
        ev["tier"] = best_tier
        # 五维加权 -> 重要性
        importance = sum(ev["dims"][d] * dim_w[d] for d in DIMS) / max(sum(dim_w.values()), 1e-6)
        ev["importance"] = importance
        cred = max(items[i]["credibility"] for i in ev["ids"])
        multi_bonus = min(len(set(items[i]["source_id"] for i in ev["ids"])) - 1, 2) * 0.4
        w = float(weights.get(ev["category"], 1.0))
        raw = (0.62 * importance + 0.30 * cred + multi_bonus) * 10 \
            * float(tier_mult.get(best_tier, 0.83)) * w \
            * float(ev.get("interest_mult", 1.0)) \
            * float(ev.get("pulse_mult", 1.0))
        ev["score"] = int(max(5, min(99, round(raw))))
        # 舆论源硬约束：事件的所有来源都是舆论源（无事实/分析源交叉）时，
        # 分数封顶在阈值之下——只能进"更多资讯"，不进精选、不参与保底补位
        ev["opinion_only"] = all(items[i]["source_type"] == "opinion"
                                 for i in ev["ids"])
        if ev["opinion_only"]:
            ev["score"] = min(ev["score"], threshold - 1)

    events.sort(key=lambda e: e["score"], reverse=True)
    pick_min = int(cfg.get("pick_min", 8))
    pick_max = int(cfg.get("pick_max", 24))
    min_per = max(0, int(cfg.get("min_per_category", 2)))
    offset = max(0, int((cfg.get("pick_dynamic") or {}).get("backfill_offset", 8)))
    quality_floor = max(5, threshold - offset)
    max_per_cat = cfg.get("max_per_category") or {}

    eligible = [e for e in events
                if e["score"] >= threshold and not e.get("opinion_only")]
    qualified = [e for e in events
                 if e["score"] >= quality_floor and not e.get("opinion_only")]
    below_threshold = [e for e in qualified if e["score"] < threshold]

    picked = []
    picked_ids = set()
    category_counts = {cat: 0 for cat in CATEGORIES}
    reserved_ids = set()
    below_threshold_reserved = 0

    def category_cap(cat):
        cap = max_per_cat.get(cat)
        return None if cap is None else max(0, int(cap))

    def can_add(event):
        if id(event) in picked_ids or len(picked) >= pick_max:
            return False
        cap = category_cap(event["category"])
        return cap is None or category_counts[event["category"]] < cap

    def add_pick(event, reserved=False):
        nonlocal below_threshold_reserved
        if not can_add(event):
            return False
        picked.append(event)
        picked_ids.add(id(event))
        category_counts[event["category"]] += 1
        if reserved:
            reserved_ids.add(id(event))
            if event["score"] < threshold:
                below_threshold_reserved += 1
        return True

    # 五类保留席：先取过线事件，再从质量线以上补位；后续不再截断。
    for cat in CATEGORIES:
        cap = category_cap(cat)
        reserve_limit = min_per if cap is None else min(min_per, cap)
        cat_pool = ([e for e in eligible if e["category"] == cat] +
                    [e for e in below_threshold if e["category"] == cat])
        for event in cat_pool:
            if category_counts[cat] >= reserve_limit:
                break
            add_pick(event, reserved=True)

    # 剩余槽位只由过线事件按分填入，并始终尊重单类上限。
    for e in eligible:
        add_pick(e)

    # 极端稀日尝试补到 pick_min，但仍不得突破统一质量下限。
    if len(picked) < pick_min:
        for e in qualified:
            if len(picked) >= pick_min:
                break
            add_pick(e)
    picked = sorted(picked, key=lambda e: e["score"], reverse=True)

    over = sum(1 for e in picked if e["score"] >= threshold)
    log(f"  阈值 {threshold} 分（补位线 {quality_floor}）：过线 {len(eligible)} 个事件，"
        f"精选 {len(picked)} 条（其中过线 {over}）")

    # 长尾过滤：整条事件的来源都被预筛标为软边角料时，不进"更多资讯"
    # （精选不受影响——上面已选完；软事件即便分高也只是被挡在长尾外）
    for ev in events:
        ev["soft"] = bool(ev["ids"]) and all(items[i].get("soft") for i in ev["ids"])
    remaining = [e for e in events if e not in picked and not e.get("soft")]
    n_soft = sum(1 for e in events if e.get("soft") and e not in picked)
    if n_soft:
        log(f"  长尾过滤：{n_soft} 个软边角料事件挡在更多资讯外")
    secondary = remaining[:cfg["secondary_count"]]
    if selection_stats is not None:
        selection_stats.update({
            "threshold": threshold,
            "quality_floor": quality_floor,
            "picked_count": len(picked),
            "category_counts": {
                cat: sum(1 for event in picked if event["category"] == cat)
                for cat in CATEGORIES
            },
            "qualified_supply": {
                cat: sum(1 for event in qualified if event["category"] == cat)
                for cat in CATEGORIES
            },
            "reserved_count": len(reserved_ids),
            "below_threshold_reserved": below_threshold_reserved,
            "over_threshold_secondary": sum(
                1 for event in secondary if event["score"] >= threshold),
        })
        finalize_selection_gate_metrics(selection_stats, picked, cfg)
    return picked, secondary


def select_and_record(events, items, cfg, data_dir, date_str):
    """Resolve the threshold, select events, and persist the score ledger.

    A ledger write failure reruns the deterministic selection with the static
    threshold so the published output never claims a dynamic line it could not record.
    """
    threshold_info = resolve_pick_threshold(cfg, data_dir, date_str)
    selection_stats = {}
    picked, secondary = score_and_select(
        events, items, cfg,
        effective_threshold=threshold_info["threshold"],
        selection_stats=selection_stats)
    if not save_score_history(data_dir, date_str, events):
        static_threshold = int(cfg.get("pick_threshold", 68))
        offset = max(0, int((cfg.get("pick_dynamic") or {}).get("backfill_offset", 8)))
        threshold_info = {
            "threshold": static_threshold,
            "source": "fallback_history_write",
            "history_days": threshold_info["history_days"],
            "quality_floor": max(5, static_threshold - offset),
        }
        selection_stats.clear()
        picked, secondary = score_and_select(
            events, items, cfg,
            effective_threshold=static_threshold,
            selection_stats=selection_stats)
    selection_stats.update({
        "threshold_source": threshold_info["source"],
        "history_days": threshold_info["history_days"],
    })
    finalize_selection_gate_metrics(selection_stats, picked, cfg)
    return picked, secondary, threshold_info, selection_stats


def _reaudit_reconciled_same_day_events(llm, events, items, quality):
    """Recheck only groups created by the reader-facing duplicate pass."""
    result = []
    for event in events:
        if not event.pop("same_day_reconciled", False):
            result.append(event)
            continue
        carried = {
            key: event[key] for key in ("interest_mult", "pulse_mult")
            if key in event
        }
        audited, _ = audit_event_cohesion(llm, [event], items, quality)
        for audited_event in audited:
            audited_event.update(carried)
        result.extend(audited)
    return result


def select_review_and_record(reconcile_llm, cohesion_llm, events, items, cfg,
                             data_dir, date_str, quality=None, *, novelty_llm=None,
                             registry=None, novelty_stats=None, novelty_hints=None):
    """Reach a stable reader-facing set, then persist only final scores."""
    quality = quality if quality is not None else new_quality_stats()
    if novelty_llm is not None:
        stats = (novelty_stats if novelty_stats is not None
                 else new_cross_source_novelty_stats())
        gate = CrossSourceNoveltyGate(
            novelty_llm, registry or {"version": 2, "events": []}, data_dir,
            date_str, cfg, stats)
        hints = novelty_hints if novelty_hints is not None else {}
        suppressed = set()
        all_events = list(events)
        threshold_info = resolve_pick_threshold(cfg, data_dir, date_str)

        def stabilize(threshold):
            nonlocal all_events
            max_passes = max(1, len(all_events) * 2)
            final_stats = {}
            for pass_index in range(max_passes):
                suppressed_events = [
                    event for event in all_events
                    if cross_source_event_key(event) in suppressed]
                eligible = [
                    event for event in all_events
                    if cross_source_event_key(event) not in suppressed]
                preliminary_picked, preliminary_secondary = score_and_select(
                    eligible, items, cfg, effective_threshold=threshold)
                reviewed, merged = review_reader_facing_duplicates(
                    reconcile_llm, eligible, preliminary_picked,
                    preliminary_secondary, items, quality)
                log(f"  发布前稳定复核第 {pass_index + 1}/{max_passes} 轮："
                    f"同日归并 {merged} 个")
                if merged:
                    reviewed = _reaudit_reconciled_same_day_events(
                        cohesion_llm, reviewed, items, quality)
                    all_events = suppressed_events + reviewed
                    continue

                novelty = gate.review(
                    [*preliminary_picked, *preliminary_secondary], items)
                hints.update(novelty["material_hints"])
                newly_suppressed = {
                    cross_source_event_key(event)
                    for event in novelty["restatements"]
                    if cross_source_event_key(event) not in suppressed
                }
                if stats.get("degraded"):
                    quality["degraded"] = True
                if newly_suppressed:
                    suppressed.update(newly_suppressed)
                    log(f"  跨源复述抑制 {len(newly_suppressed)} 个，重新选位")
                    continue

                final_stats.clear()
                picked, secondary = score_and_select(
                    eligible, items, cfg, effective_threshold=threshold,
                    selection_stats=final_stats)
                return eligible, picked, secondary, final_stats
            quality["duplicate_audit_failures"] += 1
            quality["degraded"] = True
            log("  发布前稳定复核未在有限轮次内稳定，保留当前候选")
            eligible = [event for event in all_events
                        if cross_source_event_key(event) not in suppressed]
            picked, secondary = score_and_select(
                eligible, items, cfg, effective_threshold=threshold,
                selection_stats=final_stats)
            return eligible, picked, secondary, final_stats

        eligible, picked, secondary, selection_stats = stabilize(
            threshold_info["threshold"])
        if not save_score_history(data_dir, date_str, eligible):
            static_threshold = int(cfg.get("pick_threshold", 68))
            offset = max(0, int(
                (cfg.get("pick_dynamic") or {}).get("backfill_offset", 8)))
            threshold_info = {
                "threshold": static_threshold,
                "source": "fallback_history_write",
                "history_days": threshold_info["history_days"],
                "quality_floor": max(5, static_threshold - offset),
            }
            eligible, picked, secondary, selection_stats = stabilize(
                static_threshold)
        selection_stats.update({
            "threshold_source": threshold_info["source"],
            "history_days": threshold_info["history_days"],
        })
        finalize_selection_gate_metrics(selection_stats, picked, cfg)
        log("  跨日实质新增门："
            f"候选 {stats['cross_source_novelty_candidates']}，"
            f"实质新增 {stats['cross_source_material_additions']}，"
            f"复述 {stats['cross_source_restatements']}，"
            f"失败 {stats['cross_source_novelty_failures']}，"
            f"调用 {stats['cross_source_novelty_calls']}，"
            f"延后 {stats['cross_source_novelty_deferred']}，"
            f"预算耗尽 {int(stats['cross_source_novelty_budget_exhausted'])}")
        return all_events, picked, secondary, threshold_info, selection_stats

    threshold_info = resolve_pick_threshold(cfg, data_dir, date_str)
    max_passes = max(1, len(events))
    for pass_index in range(max_passes):
        preliminary_picked, preliminary_secondary = score_and_select(
            events, items, cfg, effective_threshold=threshold_info["threshold"])
        events, merged = review_reader_facing_duplicates(
            reconcile_llm, events, preliminary_picked, preliminary_secondary,
            items, quality)
        # 每轮都要 log：这个循环上限是事件数（可达上百），失控时此前只能事后
        # 从 quality.duplicate_audited_events 反推，日志里完全静默。
        log(f"  发布前复核第 {pass_index + 1}/{max_passes} 轮：归并 {merged} 个")
        if not merged:
            break
        events = _reaudit_reconciled_same_day_events(
            cohesion_llm, events, items, quality)
    else:
        quality["duplicate_audit_failures"] += 1
        quality["degraded"] = True
        log("  同日事件发布前复核未在有限轮次内稳定，保留当前结果")
    picked, secondary, threshold_info, selection_stats = select_and_record(
        events, items, cfg, data_dir, date_str)
    return events, picked, secondary, threshold_info, selection_stats


# ----------------------------------------------------------------
# 5. 阶段B：精选深加工
# ----------------------------------------------------------------

ENRICH_SYSTEM = """你是资深新闻主编，为个人读者的"每日信息驾驶舱"加工精选新闻。
用户给你若干事件，每个事件附带一条或多条原始报道（标题+简介+来源）。
各字段职责唯一：除实体名和理解所需的最短指代外，不得在字段之间复述同一事实、背景或判断。
根据事件输入中的类目控制解释层次：非 AI 类面向聪明的外行，就地解释必要术语、机构和背景；AI 类不科普基础概念，直接写增量信息。
对每个事件输出：
- title: 精炼中文标题（建议≤30字，信息完整，不标题党；不得为满足长度截断语义）
- summary: 一句话事实增量（≤70字，只说发生了什么和新在哪里；不写影响、背景或行动建议）
- context: 事件为何此时发生（≤{context_limit}字）。{context_depth}只写原始报道中明确陈述或明确归因的直接诱因、触发点或既有机制；
  来源没有说明原因就留空，禁止用常识、行业背景或你已知的信息补写，禁止写名词解释。
  留空是正常输出，宁可留空也不要凑。以下四种一律不写，写了就是错：
  （1）任何推测性归因——出现"可能/或许/大概/据信"加动机或目的的表述；来源没明说动机就不写动机
  （2）复述 title/summary 已有的当日事实，或给它加"首个/最大/最强"之类的定性
  （3）后续走向、市场预期、风险提示——context 一律不写
  （4）与本事件无因果关系的并列背景或同类事件罗列
- context_evidence: 最多 3 条依据片段，每条形如 {{"source_index":来源编号,"quote":"逐字原文"}}。
  quote 必须从对应来源正文中**逐字复制**（12-160字，不要改写、拼接或翻译）。
  context 留空时输出空数组。每条都会由程序按来源编号精确比对，任一条对不上，context 会被整条丢弃；
  找不到足够证据时应留空，而不是编造
{watch_field}{watch_detail_field}
- claims: 0-4 条需要显式归因的分析或不确定判断，每条包含 text、kind 和 source_indexes。kind 只用 analysis 或 uncertain；source_indexes 对应输入来源前的编号。没有此类判断时允许空数组，不要把正文事实改写成 claim
{detail_field}- status: 事件状态，只能是这四个之一：
    已确认（官方发布或多个独立可信来源证实）
    发展中（事件仍在进行，信息还在更新）
    有争议（各方说法明显冲突）
    仅传言（单一来源爆料，未获证实）
- tags: 从下面的词表里选 1-2 个最贴切的主题标签，只能用词表里的词，不得自创：
    {tag_list}

客观性规范（适用于 title/summary/context/detail 全部文字字段）：
- 总纲：只陈述可追溯的事实，主张归属于提出者，争议和不确定性显式保留，不粉饰也不放大。
- 归因：来源媒体的定性判断、推断、立场性表述不得直接写成事实，必须显式归因（"X 报道称/X 评论认为"），地缘政治和涉及国家形象的定性尤其如此。检方提交起诉书/公诉文件是可报道的程序性事实；文件内指控仍须归因给检方或文件，起诉不等于定罪，不得写成已定罪事实。
- 跨源印证：事件有多个来源时，优先写各来源共同证实的事实；仅单一来源支撑的立场性内容必须归因到该来源。
- 逐项剥离或改写：情绪化煽动性形容词；未归属的价值判断；无来源依据的动机推断（"意在/旨在/企图"类措辞需原始报道有依据，否则归因或删除）；把相关性暗示成因果；数字缺分母或比较基准时不做程度渲染。
- 禁止为"平衡"补充原始报道中不存在的对立观点或说法；素材只有单一来源立场时，归因后照写即可，宁缺毋造。
- 立场性判断优先归入 claims（kind 用 analysis）并标 source_indexes，不要写进正文的叙述语气里。

只输出 JSON 对象：{{"items":[条目...]}}，每个条目：
{{"idx": 事件编号, "title": "...", "summary": "...", "context": "...", "context_evidence": [{{"source_index":0,"quote":"..."}}]{watch_json}{watch_detail_json}, "claims": [{{"text":"...","kind":"analysis","source_indexes":[0]}}]{detail_json}, "status": "...", "tags": ["..."]}}
只有一个条目时也必须放在 items 数组里。不要输出任何其他文字。"""


def sanitize_claims(raw_claims, source_names):
    """规范关键结论，把 LLM 的 source_indexes 立即解析为来源名。
    输出 sources 存名字而非索引：build_item 会对来源重排去重，
    索引出了 enrich 这一层就没有稳定含义，存名字才不会张冠李戴。"""
    if not isinstance(raw_claims, list):
        return []
    claims = []
    for raw in raw_claims[:4]:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text", "")).strip()[:120]
        if not text:
            continue
        kind = raw.get("kind")
        if kind not in {"fact", "analysis", "uncertain"}:
            kind = "uncertain"
        indexes = raw.get("source_indexes")
        if not isinstance(indexes, list):
            indexes = []
        names = list(dict.fromkeys(
            source_names[i] for i in indexes
            if isinstance(i, int) and not isinstance(i, bool)
            and 0 <= i < len(source_names)
        ))
        claims.append({"text": text, "kind": kind, "sources": names})
    return claims


CAUSE_EVIDENCE_MAX_CHARS = 160
CAUSE_EVIDENCE_MIN_CHARS = 12
# 起因只陈述事实。带推测或动机语气而不归属给任何一方的写法一律丢弃：
# 引文可以是真的，从它推出的动机却是模型加的，这正是客观性规范禁止的那一类。
CAUSE_SPECULATION_RE = re.compile(
    r"可能|或许|大概|据信|疑似|恐将|料将|意在|旨在|企图|似乎|理论上")
# "称" 单字不够：名称/简称/职称/对称 这类构词会把未归因推测放行，
# 所以排除这些前缀，并挡掉 称号/称呼/称赞 这类非引述用法。
CAUSE_ATTRIBUTION_RE = re.compile(
    r"(?<![名简全别昵俗代职尊对人通统并著相匀堪])称(?![号呼赞])"
    r"|表示|指出|认为|报道|披露|声明|通报|发言人|回应")


def _source_material(source, rich, *, snippet_limit=200):
    """The exact text one source contributes at this material tier.

    生成、引文核对与事实支撑审计必须看同一份材料。这个表达式原先在三处各写一遍，
    任何一处漂移都会造出「模型看得到、校验看不到」的字段并被整段删除（ADR 0020）。
    `snippet_limit=None` 只留给审计：它读完整 `desc` 是安全方向——材料更多，不会
    把有支撑的内容误判成无支撑；生成端受提示词长度约束只展示前 200 字。
    """
    if rich:
        return str(source.get("evidence_text")
                   or source.get("desc") or "")[:ARTICLE_MAX_CHARS]
    text = str(source.get("desc") or "")
    return text if snippet_limit is None else text[:snippet_limit]


def _event_evidence_texts(event, items, rich=False):
    """Return exactly the source texts enrich was shown, for verbatim checking.

    The slicing has to match the prompt in `enrich`: the snippet-tier prompt
    shows only the first 200 characters of the RSS summary, so verifying against
    the whole summary would accept a span the model could never have read.
    `rich` is therefore per event, not per run — an event written from fetched
    article text must be checked against that text.
    """
    texts = []
    for index in _serialized_source_ids(event, items, limit=4):
        source = items[index]
        raw = _source_material(source, rich)
        # Preserve empty entries: source_index is the ordinal shown in the
        # enrich prompt, so dropping an empty source would shift every later
        # index and validate a quote against the wrong report.
        texts.append(_normalized_copy_text(raw))
    return texts


def verify_cause_evidence(event, items, quality=None, rich=False):
    """Blank a cause unless every declared source quote matches verbatim.

    Quotes are indexed against the source order shown to enrich. Exact provenance
    does not prove entailment; the full objectivity audit separately checks that
    the resulting cause is actually supported by those reports.
    """
    cause = str(event.get("context") or "").strip()
    spans = event.pop("context_evidence", None)
    if not cause:
        # 空起因沿用 enrich 的既有约定留作空串，由后续清理阶段统一移除
        return False
    evidence_texts = _event_evidence_texts(event, items, rich)
    valid = isinstance(spans, list) and 1 <= len(spans) <= 3
    if valid:
        for span in spans:
            if not isinstance(span, dict) or set(span) != {"source_index", "quote"}:
                valid = False
                break
            source_index = span.get("source_index")
            if (not isinstance(source_index, int) or isinstance(source_index, bool)
                    or not 0 <= source_index < len(evidence_texts)):
                valid = False
                break
            quote = str(span.get("quote") or "").strip()
            if len(quote) > CAUSE_EVIDENCE_MAX_CHARS:
                valid = False
                break
            normalized_span = _normalized_copy_text(quote)
            evidence = evidence_texts[source_index]
            if len(normalized_span) < CAUSE_EVIDENCE_MIN_CHARS:
                valid = False
                break
            if normalized_span not in evidence:
                valid = False
                break
    if not valid:
        event.pop("context", None)
        if quality is not None:
            quality["cause_evidence_rejected"] += 1
        return False
    if (CAUSE_SPECULATION_RE.search(cause)
            and not CAUSE_ATTRIBUTION_RE.search(cause)):
        event.pop("context", None)
        if quality is not None:
            quality["cause_speculation_rejected"] += 1
        return False
    return True


def _field_limits(rich=False):
    """Pick the field-length table.

    `rich` is about the *material* behind the text, not the rollout mode: an
    interim event whose article text was fetched earns the same budget as a
    full-objectivity one, because the words are backed by the same evidence.
    """
    return (FULLTEXT_OBJECTIVITY_FIELD_LIMITS
            if rich else OBJECTIVITY_FIELD_LIMITS)


def _shorten_long_field(value, limit):
    """Shorten once at a sentence/paragraph boundary; never cut mid-sentence."""
    normalized = str(value or "").strip()
    if len(normalized) <= limit:
        return normalized
    prefix = normalized[:limit + 1]
    boundary = max(
        prefix.rfind(mark)
        for mark in ("\n\n", "。", "！", "？", ".", "!", "?")
    )
    if boundary < max(20, limit // 2):
        return ""
    if prefix[boundary:boundary + 2] == "\n\n":
        return prefix[:boundary].rstrip()
    return prefix[:boundary + 1].rstrip()


def _clip_objectivity_field(field, value, rich=False):
    normalized = str(value or "").strip()
    if field == "title":
        return normalized
    limit = _field_limits(rich)[field]
    if rich and field in {"context", "watch", "watch_detail", "detail"}:
        return _shorten_long_field(normalized, limit)
    return normalized[:limit]


def readable_fallback_summary(desc):
    """Return the source blurb only when it reads as Chinese, else nothing.

    次级条目不跑 enrich，摘要只能回退到来源原文。英文源的原文照抄放进摘要位，读
    起来像是我们写的中文摘要，实际是没翻译的外语原句——`CONTEXT.md` 的「次级」本
    就定义为只以标题形式呈现，宁可留空。实测 231 条次级摘要里中文最低占比 0.22、
    英文全为 0.00，0.1~0.2 之间没有样本，阈值取在这个空档正中。
    """
    text = str(desc or "").strip()[:100]
    if not text:
        return ""
    chinese = sum(1 for character in text if "一" <= character <= "鿿")
    return text if chinese / len(text) >= 0.15 else ""


def select_reader_title(candidate, source_title):
    """Keep complete generated titles and fall back instead of slicing them."""
    generated = str(candidate or "").strip()
    if generated and len(generated) <= GENERATED_TITLE_MAX_CHARS:
        return generated
    return str(source_title or "").strip()


def _normalized_copy_text(value):
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _is_direct_evidence_copy(field, value, evidence_texts):
    candidate = _normalized_copy_text(value)
    minimum = OBJECTIVITY_COPY_MIN_LENGTHS[field]
    if len(candidate) < minimum:
        return False
    for evidence in evidence_texts:
        if len(evidence) < minimum:
            continue
        if candidate in evidence:
            return True
        overlap = SequenceMatcher(
            None, candidate, evidence, autojunk=False).find_longest_match().size
        if overlap >= minimum and overlap / len(candidate) >= 0.65:
            return True
    return False


def sanitize_objectivity_event(event, items=None, quality=None):
    """Cap reader fields and fail closed on direct long full-text copies."""
    quality = quality if quality is not None else new_quality_stats()
    # ``why`` is a legacy news field.  Drop it before every audit/repair pass so
    # old fixtures and stale model responses cannot re-enter the public contract.
    event.pop("why", None)
    source_title = ""
    if items:
        source_ids = _serialized_source_ids(event, items, limit=1)
        if source_ids:
            source_title = items[source_ids[0]].get("title", "")
    for field in OBJECTIVITY_FIELDS:
        if field in event:
            raw_value = event[field]
            value = (
                select_reader_title(event[field], source_title)
                if field == "title"
                else _clip_objectivity_field(field, event[field], True)
            )
            if field != "title" and str(raw_value or "").strip() and not value:
                event.pop(field, None)
                count_removed_field(quality, field, "generation_invalid")
            else:
                event[field] = value
    _remove_orphan_watch_detail(event, quality)
    claims = []
    for claim in event.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("text") or "").strip()[:120]
        if text:
            claims.append({**claim, "text": text})
    if claims:
        event["claims"] = claims
    else:
        event.pop("claims", None)
    if not items:
        return event

    ids = _serialized_source_ids(event, items, limit=4)
    evidence_texts = [
        _normalized_copy_text(items[index].get("evidence_text"))
        for index in ids
        if (items[index].get("evidence_basis") == "fulltext"
            and items[index].get("evidence_text"))
    ]
    if not evidence_texts:
        return event

    primary = items[ids[0]] if ids else {}
    source_name = str(primary.get("source") or "Source").strip()
    source_title = str(primary.get("title") or "").strip()
    source_desc = str(primary.get("desc") or "").strip()
    safe_title = select_reader_title(
        f"{source_name}: {source_title}" if source_title else source_name,
        source_title)
    safe_summary = _clip_objectivity_field(
        "summary",
        (f"{source_name} reported: {source_desc}"
         if source_desc else f"{source_name} reported the item."),
    )
    if _is_direct_evidence_copy("title", safe_title, evidence_texts):
        safe_title = _clip_objectivity_field("title", source_name)
    if _is_direct_evidence_copy("summary", safe_summary, evidence_texts):
        safe_summary = _clip_objectivity_field(
            "summary", f"{source_name} reported the item.")
    if _is_direct_evidence_copy("title", event.get("title"), evidence_texts):
        event["title"] = safe_title
    if _is_direct_evidence_copy("summary", event.get("summary"), evidence_texts):
        event["summary"] = safe_summary
    for field in OBJECTIVITY_FIELDS[2:]:
        if field in event and _is_direct_evidence_copy(
                field, event.get(field), evidence_texts):
            event.pop(field, None)
            count_removed_field(quality, field, "evidence_copy")
    _remove_orphan_watch_detail(event, quality, reason="evidence_copy")
    kept_claims = []
    for claim in event.get("claims") or []:
        if _is_direct_evidence_copy("claims", claim.get("text"), evidence_texts):
            count_removed_field(quality, "claims", "evidence_copy")
            continue
        kept_claims.append(claim)
    if kept_claims:
        event["claims"] = kept_claims
    else:
        event.pop("claims", None)
    return event


def _substantially_duplicate_evidence(left, right, *, shingle_size=16):
    """Detect near-duplicate long evidence in linear time.

    Character shingles tolerate small insertions and reordered boilerplate while
    avoiding the quadratic worst case of sequence alignment on fetched pages.
    """
    if not left or not right:
        return False
    if len(left) < shingle_size or len(right) < shingle_size:
        return left == right
    left_shingles = {
        left[index:index + shingle_size]
        for index in range(len(left) - shingle_size + 1)
    }
    right_shingles = {
        right[index:index + shingle_size]
        for index in range(len(right) - shingle_size + 1)
    }
    denominator = min(len(left_shingles), len(right_shingles))
    if not denominator:
        return left == right
    return len(left_shingles & right_shingles) / denominator >= 0.85


def detail_evidence_tier(event, items):
    """Classify the evidence available to the existing enrich call.

    The classifier only inspects sources already selected by the unchanged
    four-source contract.  Two long reports count as rich evidence only when
    they come from different sources and are not substantially duplicative.
    """
    fulltexts = []
    for index in _serialized_source_ids(event, items, limit=4):
        item = items[index]
        if item.get("evidence_basis") != "fulltext":
            continue
        text = _normalized_copy_text(item.get("evidence_text"))
        if not text:
            continue
        identity = str(item.get("source_id") or item.get("source") or index).strip()
        fulltexts.append((identity, text))
    if any(len(text) >= 2000 for _, text in fulltexts):
        return "rich"
    long_reports = [(identity, text) for identity, text in fulltexts if len(text) >= 800]
    for left_index, (left_identity, left_text) in enumerate(long_reports):
        for right_identity, right_text in long_reports[left_index + 1:]:
            if left_identity == right_identity:
                continue
            if not _substantially_duplicate_evidence(left_text, right_text):
                return "rich"
    return "limited" if fulltexts else "snippet"


def _detail_tier_prompt(tier):
    return {
        "rich": "丰富材料；目标 350-600 字、2-4 段",
        "limited": "有限全文；目标 180-350 字、1-3 段",
        "snippet": "摘要材料；安全短写，不设最低字数",
    }[tier]


def finalize_detail_quality_metrics(picked, items, quality):
    """Record aggregate detail health from the final post-audit text only."""
    for tier in ("rich", "limited", "snippet"):
        quality[f"detail_evidence_{tier}"] = 0
    quality["detail_rich_target_met"] = 0
    lengths = []
    for event in picked or []:
        tier = detail_evidence_tier(event, items)
        quality[f"detail_evidence_{tier}"] += 1
        detail = str(event.get("detail") or "").strip()
        if detail:
            lengths.append(len(detail))
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", detail)
                      if part.strip()]
        if tier == "rich" and len(detail) >= 300 and len(paragraphs) >= 2:
            quality["detail_rich_target_met"] += 1
    rich = quality["detail_evidence_rich"]
    quality["detail_rich_target_rate"] = round(
        quality["detail_rich_target_met"] / rich, 4) if rich else 0.0
    quality["detail_final_median_chars"] = int(median(lengths)) if lengths else 0
    return quality


def fulltext_fetch_candidates(picked, cfg):
    """The highest-scoring picks nominated for an article fetch (ADR 0020).

    Nominated, not yet fetched: whether a candidate actually reaches the
    fulltext contract is answered later by `event_has_fulltext_evidence`, after
    the fetch either succeeded or quietly failed.

    Selection has to happen here, before enrich: `track_events` and the daily
    brief both run later, so 可信延续 and 今日主线 are not known yet and cannot
    serve as criteria.  Score is the ordering the reader already reads by.
    """
    top_n = int((cfg.get("detail") or {}).get("fulltext_top_n") or 0)
    if top_n <= 0:
        return []
    ranked = sorted(picked, key=lambda event: (
        -(event.get("score") or 0), str(event.get("title") or "")))
    return ranked[:top_n]


def event_has_fulltext_evidence(event, items):
    """True when this event's own sources carry fetched article text.

    The material tier is derived, never stored: a failed fetch leaves
    `evidence_basis` at snippet, so the event falls back to the snippet contract
    on its own and costs no extra tokens.  That is what makes the tiered budget
    an upper bound rather than an estimate.
    """
    return detail_evidence_tier(event, items) != "snippet"


def _enrich_batches(picked, items, indexes, rich):
    """Group indexes into prompt batches, fullest contract first.

    Batches carry explicit `picked` indexes rather than a (start, end) range:
    the two material tiers interleave inside `picked`, so a batch is no longer
    contiguous.  The index shown in the prompt stays the true `picked` index, so
    the out-of-batch guard in `enrich` still compares against real identities.
    """
    indexes = list(indexes)
    if not rich:
        return [indexes[start:start + 6] for start in range(0, len(indexes), 6)]
    batches = []
    start = 0
    while start < len(indexes):
        end = start
        evidence_chars = 0
        while end < len(indexes) and end - start < 3:
            event_chars = sum(
                len(str(items[index].get("evidence_text")
                        or items[index].get("desc") or "")[:ARTICLE_MAX_CHARS])
                for index in _serialized_source_ids(
                    picked[indexes[end]], items, limit=4)
            )
            if end > start and evidence_chars + event_chars > 48_000:
                break
            evidence_chars += event_chars
            end += 1
        end = max(start + 1, end)
        batches.append(indexes[start:end])
        start = end
    return batches


def _assign_generated_field(event, field, raw, rich, quality):
    value = _clip_objectivity_field(field, raw, rich)
    if str(raw or "").strip() and not value:
        event.pop(field, None)
        if quality is not None:
            count_removed_field(quality, field, "generation_invalid")
        return
    event[field] = value


def _remove_orphan_watch_detail(
        event, quality=None, reason="generation_invalid"):
    """A detail watch is invalid unless the short public contract also exists."""
    if event.get("watch_detail") and not event.get("watch"):
        event.pop("watch_detail", None)
        if quality is not None:
            count_removed_field(quality, "watch_detail", reason)


def _enrich_system_prompt(tag_vocab, detail_on, detail_chars, rich,
                          full_objectivity):
    """Build one system prompt per material tier.

    `rich` is the *material* contract — how much the model was shown, and
    therefore how much it may write.  `full_objectivity` stays the *rollout*
    contract and only decides whether `watch_detail` exists.  Keeping them apart
    is the point: one boolean standing for both is what left ADR 0015's evidence
    tiers unreachable for as long as `objectivity.mode` was `interim`.
    """
    if detail_on and rich:
        detail_field = (
            f"- detail: 现状叙述（软上限仍为 {detail_chars} 字，程序硬上限仍为 1200 字；严格服从每个事件标注的材料等级与目标；"
            "丰富材料目标 350-600 字、2-4 段，有限全文目标 180-350 字、1-3 段，摘要材料安全短写且不设最低字数；"
            "段间空行，不用小标题；串联来源已提供的事实过程和关键细节，不复述 summary/context/watch/watch_detail；"
            "来源材料能够支持时，从机制或传导链、带比较锚点的数字、利益相关方变化和未决事实中择最有价值的内容写入，不要求每条全部具备；"
            "不写公共影响或为何重要的判断；"
            "严格基于所给原始报道，不得编造原文没有的事实/数字/引语；"
            "来源媒体的立场性定性须显式归因（如\"BBC 称\"），不得写成客观事实；素材不足就写多少算多少，宁短毋凑）\n"
        )
    elif detail_on:
        detail_field = (
            f"- detail: 现状短叙述（约 {detail_chars} 字以内，需要分段时使用自然段和空行，不用小标题；"
            "摘要材料安全短写且不设最低字数；串联摘要材料已有的事件过程和关键细节，不复述 summary/context；"
            "不写公共影响或为何重要的判断；"
            "只写输入明确提供的内容，不得凭摘要补全机制、数字、引语或未决事实；素材不足就短写）\n"
        )
    else:
        detail_field = ""
    # 摘要材料档不生成走向：`CONTEXT.md` 说「没有路标的走向不成立」，而 200 字 RSS 摘要
    # 里几乎不可能有可观察路标，模型只能靠「取决于X／可观察Y／路标Z」的骨架把结构
    # 显式写出来换取审计放行——那是通过审计的形状，不是读者要的内容（ADR 0020）。
    watch_field = (
        f"- watch: 走向（≤{OBJECTIVITY_FIELD_LIMITS['watch']}字）：说明接下来取决于哪 1-2 个关键变量，并给出至少一个可观察路标。\n"
        "  仅在当前来源明确提供既有趋势或可比历史时使用类比；禁止具体概率数字、无条件断言和来源外类比\n"
        if rich else "")
    watch_json = ', "watch": "..."' if rich else ""
    watch_detail_field = (
        "- watch_detail: 详情走向（建议 120-220 字，最多 260 字）：完整包含 watch 的变量和路标语义，"
        "可补充第二个关键变量、判断依据和更多可观察路标；不得与 watch 矛盾，不得增加来源外判断\n"
        if full_objectivity else "")
    return ENRICH_SYSTEM.format(
        tag_list="、".join(tag_vocab) if tag_vocab else "（词表为空，tags 输出空数组）",
        detail_field=detail_field,
        detail_json=', "detail": "..."' if detail_on else "",
        context_limit=(240 if rich else 60),
        context_depth=("材料丰富时可写 80-180 字；" if rich else ""),
        watch_field=watch_field,
        watch_json=watch_json,
        watch_detail_field=watch_detail_field,
        watch_detail_json=', "watch_detail": "..."' if full_objectivity else "")


def enrich(llm, picked, items, cfg, quality=None):
    tag_vocab = [str(t) for t in (cfg.get("topic_tags") or [])]
    tag_set = set(tag_vocab)
    dcfg = cfg.get("detail") or {}
    detail_on = dcfg.get("enabled", True)
    full_objectivity = _rollout_output_enabled(cfg)
    configured_detail_chars = int(dcfg.get("max_chars", 600) or 600)
    # 两档各自的现状软目标。摘要材料档的这个值同时喂提示词和回填时的硬裁剪，
    # 必须只算一次——两处各写一遍 `min(..., 600)` 就是等着它们哪天分叉。
    detail_chars = {True: min(configured_detail_chars, 1000),
                    False: min(configured_detail_chars, 600)}
    # Full objectivity keeps its run-wide contract; in interim the tier is
    # per-event, so both prompts have to exist within one run.
    rich_flags = [full_objectivity or event_has_fulltext_evidence(event, items)
                  for event in picked]
    groups = [(True, [i for i, is_rich in enumerate(rich_flags) if is_rich]),
              (False, [i for i, is_rich in enumerate(rich_flags) if not is_rich])]
    prompts = {
        rich: _enrich_system_prompt(
            tag_vocab, detail_on, detail_chars[rich], rich, full_objectivity)
        for rich in (True, False)
    }
    batch_number = 0
    for rich, group_indexes in groups:
        if not group_indexes:
            continue
        system = prompts[rich]
        for batch_indexes in _enrich_batches(picked, items, group_indexes, rich):
            batch_number += 1
            batch = [picked[index] for index in batch_indexes]
            allowed_indexes = set(batch_indexes)
            blocks = []
            for index, ev in zip(batch_indexes, batch):
                ev.pop("why", None)
                srcs = []
                source_ids = _serialized_source_ids(ev, items, limit=4)
                for source_index, i in enumerate(source_ids):
                    it = items[i]
                    evidence_text = (
                        (it.get("evidence_text") or it.get("desc", ""))[:ARTICLE_MAX_CHARS]
                        if rich else str(it.get("desc") or "")[:200]
                    )
                    srcs.append(f"  - [{source_index}] [{it['source']}|{TYPE_NAMES[it['source_type']]}] "
                                f"{it['title']}：{evidence_text}")
                hints = list(dict.fromkeys(items[i].get("tag_hint") for i in ev["ids"]
                                           if items[i].get("tag_hint") in tag_set))
                hint_line = ("\n  （来源分类提示，若贴切请优先选为标签："
                             + "、".join(hints) + "）") if hints else ""
                detail_hint = (
                    f"\n  （现状材料等级：{_detail_tier_prompt(detail_evidence_tier(ev, items))}）"
                    if detail_on else "")
                blocks.append(
                    f"事件[{index}]（类目：{ev.get('category', 'world')}） {ev['title']}\n"
                    + "\n".join(srcs) + hint_line + detail_hint)
            log(f"  阶段B 批次 {batch_number}"
                f"（{'全文材料' if rich else '摘要材料'}）: {len(batch)} 个事件")
            result = _model_rows(
                llm.json_call(system, "【今日事件】\n" + "\n\n".join(blocks)), "items")
            if result is None:
                log("  阶段B 返回结构非法，本批保留基础内容")
                if quality is not None:
                    quality["model_unusable_responses"] += 1
                    quality["degraded"] = True
                continue
            invalid_rows = sum(not isinstance(row, dict) for row in result)
            if invalid_rows:
                log(f"  阶段B 忽略 {invalid_rows} 条非法返回，本批其余条目继续")
            out_of_batch = 0
            for r in result:
                if not isinstance(r, dict):
                    continue
                k = r.get("idx")
                if not isinstance(k, int) or isinstance(k, bool):
                    continue
                # 提示词里只展示了本批事件的 picked 下标，所以合法回填只可能落在本批
                # 这几个下标上。放行本批以外的 idx 意味着一条新闻的返回可以覆盖另一条
                # 已经算好的全部读者字段——模型写错下标是这样，抓来的正文用提示注入
                # 诱导它写错下标也是这样。下游 support 审计按事件自己的来源复核，
                # 覆盖的后果只会表现为 removed_fields 无故上涨，查不到源头，
                # 所以必须在这里挡住。批次不再连续，判据是集合成员而不是区间。
                if k not in allowed_indexes:
                    out_of_batch += 1
                    continue
                ev = picked[k]
                source_ids = _serialized_source_ids(ev, items, limit=1)
                source_title = items[source_ids[0]].get("title", "") if source_ids else ""
                ev["title"] = select_reader_title(r.get("title"), source_title)
                ev["summary"] = _clip_objectivity_field("summary", r.get("summary", ""))
                ev.pop("why", None)
                _assign_generated_field(
                    ev, "context", r.get("context", ""), rich, quality)
                ev["context_evidence"] = r.get("context_evidence", [])
                # 引文核对必须按本事件实际展示过的材料来，否则全文材料档引自正文的逐字片段
                # 会因为只比对 200 字摘要而全数判假，context 被整条丢掉。
                verify_cause_evidence(ev, items, quality, rich)
                if rich:
                    _assign_generated_field(
                        ev, "watch", r.get("watch", ""), rich, quality)
                if full_objectivity:
                    _assign_generated_field(
                        ev, "watch_detail", r.get("watch_detail", ""),
                        True, quality)
                    _remove_orphan_watch_detail(ev, quality)
                ev["claims"] = sanitize_claims(
                    r.get("claims"), [
                        items[i]["source"]
                        for i in _serialized_source_ids(ev, items, limit=4)
                    ])
                if detail_on:
                    if rich:
                        _assign_generated_field(
                            ev, "detail", r.get("detail", ""), True, quality)
                    else:
                        ev["detail"] = str(
                            r.get("detail", "")).strip()[
                                :detail_chars[False] + 200]
                ev["status"] = r.get("status") if r.get("status") in STATUS_SET else "发展中"
                raw_tags = r.get("tags") or []
                if not isinstance(raw_tags, list):
                    raw_tags = []
                tags = [t for t in raw_tags if t in tag_set]
                # 兜底：AI HOT 携带的分类提示（研究论文/技巧观点等）优先入选，防止被淹没
                for h in (items[i].get("tag_hint") for i in ev["ids"]):
                    if h in tag_set and h not in tags:
                        tags.insert(0, h)
                ev["tags"] = tags[:2]
                if full_objectivity:
                    sanitize_objectivity_event(ev, items)
            if out_of_batch:
                log(f"  阶段B 丢弃 {out_of_batch} 条越批次 idx"
                    f"（本批 {sorted(allowed_indexes)}）")
                if quality is not None:
                    quality["enrich_out_of_batch_idx"] = int(
                        quality.get("enrich_out_of_batch_idx", 0)) + out_of_batch
    return picked


OBJECTIVITY_AUDIT_SYSTEM = """你是新闻证据与客观性审计员。输入报道是唯一可用证据，不得用常识补证据。
逐项检查 title、summary、context、watch、watch_detail、detail 以及每条 claim：
1. 是否有来源支撑；2. fact/analysis/uncertain 类型是否正确；3. 主张、评价和指控是否正确归因；
4. 是否加入来源没有的动机或因果推断；5. 是否使用缺少基准的幅度/程度语言；
6. 是否为追求平衡而虚构反方观点或反诉。
对 watch 和 watch_detail 还必须检查：是否说明 1-2 个有来源支撑的关键变量并给出至少一个可观察路标；
是否含具体概率、无条件断言或来源外类比。watch_detail 还必须完整保留 watch 的变量和路标语义。
任一项不合规，对应字段必须为 false。
检方提交起诉书/公诉文件本身是可报道的程序性事实；其中指控仍须归因，起诉不等于定罪。
只输出 JSON 对象：
{"fields":{"title":true,"summary":true,"context":true,
"watch":true,"watch_detail":true,"detail":true},"claims":[true]}
fields 只列输入中存在的字段；claims 布尔数组必须与输入 claims 等长。任一检查不通过即为 false。"""

OBJECTIVITY_REPAIR_SYSTEM = """你是新闻客观性修复编辑。只能修改输入列出的 failed_fields 和
failed_claim_indexes，其他内容不得改动。严格依据 reports 修复；无法安全修复的字段给空字符串，
claim 可用 {"index":编号,"drop":true} 删除。只输出 JSON：
{"fields":{"字段":"修复后文字"},
"claims":[{"index":0,"text":"...","kind":"fact|analysis|uncertain","sources":["来源名"]}]}。
不得创造来源、事实、动机、因果、幅度或所谓平衡观点。"""

# Historical name kept for callers that import the prompt constant.
SUPPORT_AUDIT_SYSTEM = """你是新闻事实支撑质检员。原始报道是唯一可用证据。
检查编辑扩展字段是否只讨论当前事件且能由原始报道支撑；不要凭常识补证据。
对 watch 和 watch_detail 还必须检查：是否说明 1-2 个有来源支撑的关键变量并给出至少一个可观察路标；
是否含具体概率、无条件断言或来源外类比。watch_detail 还必须完整保留 watch 的变量和路标语义。
任一项不合规，对应字段必须为 false。
对 context/watch/watch_detail/detail 分别给出布尔值。逐条检查 claims，返回有支撑的 claim 编号。
只输出 JSON 对象：
{"fields":{"context":true,"watch":true,"watch_detail":true,"detail":true},
 "supported_claim_indexes":[0]}
受到别的事件污染、超出来源或无法确认的字段/claim 必须判为不支持。"""


def _remove_extension(event, field, quality):
    if field in event:
        event.pop(field, None)
        count_removed_field(quality, field, "audit_unsupported")


def _strip_extensions(event, quality):
    for field in QUALITY_EXTENSION_FIELDS:
        _remove_extension(event, field, quality)


def _validated_support_result(raw, event):
    if not isinstance(raw, dict) or not isinstance(raw.get("fields"), dict):
        return None
    fields = raw["fields"]
    for field in QUALITY_EXTENSION_FIELDS[:-1]:
        if field in event and not isinstance(fields.get(field), bool):
            return None
    indexes = raw.get("supported_claim_indexes")
    if (not isinstance(indexes, list)
            or any(not isinstance(i, int) or isinstance(i, bool) for i in indexes)):
        return None
    claims = event.get("claims") or []
    if len(indexes) != len(set(indexes)) or any(i < 0 or i >= len(claims) for i in indexes):
        return None
    return fields, indexes


def audit_enrichment_support_interim(llm, picked, items, quality=None):
    """Retain the pre-rollout support-only audit for interim public runs."""
    quality = quality if quality is not None else new_quality_stats()
    quality["enrichment_audited_events"] += len(picked)
    for event in picked:
        ids = event.get("ids") or []
        # 审计材料必须与生成材料同源。全文材料档的条目是照抓来的正文写的，若审计只拿到 RSS
        # 摘要，凡是引自正文的内容都会被判成「无来源支撑」并整段删除——那才是结构性
        # 误杀。摘要材料档两边都只有 desc，本来就对齐（ADR 0020）。
        rich = event_has_fulltext_evidence(event, items)
        reports = [{
            "id": i,
            "title": items[i].get("title", ""),
            "summary": (
                (items[i].get("evidence_text") or items[i].get("desc", ""))[:ARTICLE_MAX_CHARS]
                if rich else items[i].get("desc", "")),
            "source": items[i].get("source", ""),
        } for i in ids if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(items)]
        extension = {field: event.get(field) for field in QUALITY_EXTENSION_FIELDS
                     if field in event}
        try:
            checked = _validated_support_result(
                llm.json_call(SUPPORT_AUDIT_SYSTEM, json.dumps({
                    "event_title": event.get("title", ""),
                    "reports": reports,
                    "extension": extension,
                }, ensure_ascii=False)), event)
        except Exception as exc:
            log(f"  事实支撑审计失败，移除扩展字段: {exc}")
            checked = None
        if checked is None:
            quality["degraded"] = True
            _strip_extensions(event, quality)
            continue
        fields, supported_indexes = checked
        for field in QUALITY_EXTENSION_FIELDS[:-1]:
            if field in event and not fields.get(field, False):
                _remove_extension(event, field, quality)
        claims = event.get("claims") or []
        valid_sources = {items[i].get("source", "") for i in ids
                         if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(items)}
        kept = []
        for index, claim in enumerate(claims):
            claim_sources = claim.get("sources") if isinstance(claim, dict) else None
            if (index in supported_indexes and isinstance(claim_sources, list)
                    and claim_sources and set(claim_sources).issubset(valid_sources)):
                kept.append(claim)
            else:
                count_removed_field(quality, "claims", "claim_unsupported")
        if kept:
            event["claims"] = kept
        else:
            event.pop("claims", None)
    return picked


def _validated_objectivity_result(raw, event):
    if not isinstance(raw, dict) or not isinstance(raw.get("fields"), dict):
        return None
    fields = raw["fields"]
    for field in OBJECTIVITY_FIELDS:
        if field not in event:
            continue
        if not isinstance(fields.get(field), bool):
            return None
    claims = event.get("claims") or []
    claim_checks = raw.get("claims")
    if (not isinstance(claim_checks, list) or len(claim_checks) != len(claims)
            or any(not isinstance(value, bool) for value in claim_checks)):
        return None
    return fields, claim_checks


def _objectivity_failures(checked, event, valid_sources):
    if checked is None:
        return ([field for field in OBJECTIVITY_FIELDS if field in event],
                list(range(len(event.get("claims") or []))))
    fields, claim_checks = checked
    failed_fields = [field for field in OBJECTIVITY_FIELDS
                     if field in event and not fields.get(field, False)]
    failed_claims = []
    for index, claim in enumerate(event.get("claims") or []):
        sources = claim.get("sources") if isinstance(claim, dict) else None
        kind = claim.get("kind") if isinstance(claim, dict) else None
        if (not claim_checks[index] or kind not in {"fact", "analysis", "uncertain"}
                or not isinstance(sources, list) or not sources
                or not set(sources).issubset(valid_sources)):
            failed_claims.append(index)
    return failed_fields, failed_claims


def _apply_objectivity_repair(
        event, raw, failed_fields, failed_claims, valid_sources,
        source_title="", quality=None):
    if not isinstance(raw, dict):
        return
    field_repairs = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    for field in failed_fields:
        if field in field_repairs:
            if field == "title":
                event[field] = select_reader_title(
                    field_repairs[field], source_title)
            else:
                _assign_generated_field(
                    event, field, field_repairs[field], True, quality)
    claims = list(event.get("claims") or [])
    repairs = raw.get("claims") if isinstance(raw.get("claims"), list) else []
    for repair in repairs:
        if not isinstance(repair, dict):
            continue
        index = repair.get("index")
        if (not isinstance(index, int) or isinstance(index, bool)
                or index not in failed_claims or not 0 <= index < len(claims)):
            continue
        if repair.get("drop") is True:
            claims[index] = None
            continue
        sources = repair.get("sources")
        kind = repair.get("kind")
        text = str(repair.get("text") or "").strip()[:120]
        if (text and kind in {"fact", "analysis", "uncertain"}
                and isinstance(sources, list) and sources
                and set(sources).issubset(valid_sources)):
            claims[index] = {"text": text, "kind": kind,
                             "sources": list(dict.fromkeys(sources))}
    event["claims"] = [claim for claim in claims if claim is not None]
    if not event["claims"]:
        event.pop("claims", None)


def _conservative_event_fallback(event, items, quality):
    ids = _serialized_source_ids(event, items, limit=1)
    if not ids:
        raise ValueError("audited event has no valid source mapping")
    source = items[ids[0]]
    source_name = str(source.get("source") or "来源").strip()
    source_title = str(source.get("title") or "").strip()
    source_desc = str(source.get("desc") or "").strip()
    event["title"] = select_reader_title(
        f"{source_name}：{source_title}", source_title)
    event["summary"] = f"{source_name} 报道：{source_desc}"
    event["title"] = _clip_objectivity_field("title", event.get("title"))
    event["summary"] = _clip_objectivity_field("summary", event.get("summary"))
    _strip_extensions(event, quality)
    evidence = event.get("evidence") if isinstance(event.get("evidence"), dict) else {}
    event["evidence"] = {**evidence, "degraded": True}
    quality["degraded"] = True
    quality["objectivity_degraded"] += 1
    sanitize_objectivity_event(event, items, quality)


def _materialize_reader_projection(event, items):
    """Populate the exact title/summary defaults that ``event_to_item`` would expose."""
    ids = _serialized_source_ids(event, items, limit=1)
    if not ids:
        raise ValueError("audited event has no valid source mapping")
    primary = items[ids[0]]
    if "title" not in event:
        event["title"] = primary.get("title", "")
    if "summary" not in event:
        fallback = readable_fallback_summary(primary.get("desc"))
        if fallback:
            event["summary"] = fallback
    return event


def audit_enrichment_support(llm, picked, items, quality=None, secondary=None):
    """Audit every reader-facing event field, repairing once then failing closed."""
    quality = quality if quality is not None else new_quality_stats()
    demoted = []
    picked_ids = {id(event) for event in picked}
    candidates = list(picked)
    if secondary is not None:
        candidates.extend(event for event in secondary
                          if not any(event is existing for existing in candidates))
    quality["enrichment_audited_events"] += len(candidates)
    for event in candidates:
        _materialize_reader_projection(event, items)
        sanitize_objectivity_event(event, items, quality)
        quality["objectivity_audited"] += 1
        ids = _serialized_source_ids(event, items, limit=4)
        reports = [{
            "id": i,
            "title": items[i].get("title", ""),
            "summary": items[i].get("evidence_text") or items[i].get("desc", ""),
            "source": items[i].get("source", ""),
            "source_type": items[i].get("source_type", ""),
        } for i in ids if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(items)]
        valid_sources = {report["source"] for report in reports if report["source"]}
        content = {field: event.get(field) for field in OBJECTIVITY_FIELDS if field in event}
        content["claims"] = event.get("claims") or []
        audit_payload = {"reports": reports, "content": content}
        raw = None
        try:
            raw = llm.json_call(OBJECTIVITY_AUDIT_SYSTEM,
                                json.dumps(audit_payload, ensure_ascii=False))
            checked = _validated_objectivity_result(raw, event)
        except Exception as exc:
            log(f"  客观性初审失败，进入定向修复: {exc}")
            checked = None
            if secondary is None:
                quality["degraded"] = True
                _strip_extensions(event, quality)
                continue

        failed_fields, failed_claims = _objectivity_failures(
            checked, event, valid_sources)
        if not failed_fields and not failed_claims:
            continue

        repair_payload = {
            **audit_payload,
            "failed_fields": failed_fields,
            "failed_claim_indexes": failed_claims,
        }
        try:
            repaired = llm.json_call(OBJECTIVITY_REPAIR_SYSTEM,
                                     json.dumps(repair_payload, ensure_ascii=False))
            _apply_objectivity_repair(
                event, repaired, failed_fields, failed_claims, valid_sources,
                source_title=reports[0]["title"] if reports else "",
                quality=quality)
            sanitize_objectivity_event(event, items, quality)
        except Exception as exc:
            log(f"  客观性定向修复失败，继续复审并保守降级: {exc}")

        content = {field: event.get(field) for field in OBJECTIVITY_FIELDS if field in event}
        content["claims"] = event.get("claims") or []
        try:
            raw = llm.json_call(OBJECTIVITY_AUDIT_SYSTEM, json.dumps({
                "reports": reports, "content": content,
            }, ensure_ascii=False))
            checked = _validated_objectivity_result(raw, event)
        except Exception as exc:
            log(f"  客观性复审失败，使用来源保守降级: {exc}")
            checked = None
        failed_fields, failed_claims = _objectivity_failures(
            checked, event, valid_sources)
        if not failed_fields and not failed_claims:
            quality["objectivity_repaired"] += 1
            continue

        _conservative_event_fallback(event, items, quality)
        if id(event) in picked_ids and _event_is_high_risk(event):
            demoted.append(event)
            quality["high_risk_demoted"] += 1

    if secondary is not None and demoted:
        demoted_ids = {id(event) for event in demoted}
        picked[:] = [event for event in picked if id(event) not in demoted_ids]
        for event in demoted:
            if not any(existing is event for existing in secondary):
                secondary.append(event)
    return picked


def run_audit_enrichment_support_stage(
        policy, audit_llm, picked, secondary, items, quality):
    """Dispatch the rollout-gated audit while preserving interim behavior."""
    if policy["full_objectivity"]:
        return audit_enrichment_support(
            audit_llm, picked, items, quality, secondary=secondary)
    return audit_enrichment_support_interim(audit_llm, picked, items, quality)


# Concise compatibility name used by focused rollout tests and external callers.
run_objectivity_stage = run_audit_enrichment_support_stage


BRIEF_SYSTEM = """你是新闻主编。用户给你今天的条目列表（每条带 id、类目、标题、可能有要点）。
你的任务是替读者"拼主线"：把相关的条目归拢成今天的 2-3 条主线，让读者一眼看懂今天的世界在发生什么。
输出 JSON：
{"synthesis": "一句话总纲，≤60字，概括今天整体格局",
 "themes": [{"title": "主线名，≤12字", "one_liner": "这条主线的一句综合，≤50字",
             "member_ids": ["属于这条主线的条目 id，2个及以上"]}]}
规则：
- themes 最多 3 条，宁缺毋滥；每条主线必须有 ≥2 个成员 id（单个孤立事件不算主线，除非是压倒性头条可破例给 1 个）。
- member_ids 只能从用户给出的 id 里选，禁止自造 id；一条可以跨类目（如极端天气可同时含国际和社会的条目）。
- 措辞中性：synthesis 与 one_liner 只陈述事实，媒体的立场性定性不得写成事实——归因（"X 称"）或略去。
- 今天若确实没有能归拢的主线，themes 给空数组，synthesis 照常写。
只输出 JSON，不要其他文字。"""


BRIEF_AUDIT_SYSTEM = """你是日报导语客观性审计员。whole_day_evidence 是 synthesis 的唯一证据；
每条 theme 只能使用 theme_evidence 中同 index 的 items，不能使用当天其他条目。
检查 synthesis，以及每条 theme 的 title/one_liner：是否受对应范围事实支撑、归因正确，且没有
无依据动机/因果/幅度语言或虚构平衡说法。只输出：
{"synthesis":true,"themes":[{"index":0,"title":true,"one_liner":true}]}。
themes 必须逐条按 index 返回。"""

BRIEF_REPAIR_SYSTEM = """只修复 failed 中列出的日报导语字段；synthesis 严格依据 whole_day_evidence，
每条 theme 严格依据 theme_evidence 中同 index 的 items；
其他字段不得改。只输出 {"synthesis":"可选修复", "themes":[{"index":0,
"title":"可选修复","one_liner":"可选修复"}]}。"""


def _validated_brief_audit(raw, themes):
    if not isinstance(raw, dict) or not isinstance(raw.get("synthesis"), bool):
        return None
    rows = raw.get("themes")
    if not isinstance(rows, list) or len(rows) != len(themes):
        return None
    checked = {}
    for row in rows:
        if not isinstance(row, dict):
            return None
        index = row.get("index")
        if (not isinstance(index, int) or isinstance(index, bool) or index in checked
                or not 0 <= index < len(themes)
                or not isinstance(row.get("title"), bool)
                or not isinstance(row.get("one_liner"), bool)):
            return None
        checked[index] = (row["title"], row["one_liner"])
    if len(checked) != len(themes):
        return None
    return raw["synthesis"], checked


def _brief_failures(checked, themes):
    if checked is None:
        return False, {index: {"title", "one_liner"} for index in range(len(themes))}
    synthesis_ok, rows = checked
    failed = {}
    for index, (title_ok, one_liner_ok) in rows.items():
        names = set()
        if not title_ok:
            names.add("title")
        if not one_liner_ok:
            names.add("one_liner")
        if names:
            failed[index] = names
    return synthesis_ok, failed


def _audit_brief(audit_llm, synthesis, themes, member_items):
    whole_day_evidence = {
        str(item.get("id")): {
            key: value for key, value in item.items() if key != "id"
        }
        for item in member_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    theme_evidence = []
    for index, theme in enumerate(themes):
        member_ids = [
            member_id for member_id in (theme.get("member_ids") or [])
            if member_id in whole_day_evidence
        ]
        theme_evidence.append({
            "index": index,
            "member_ids": member_ids,
            "items": {
                member_id: whole_day_evidence[member_id]
                for member_id in member_ids
            },
        })
    payload = {
        "whole_day_evidence": whole_day_evidence,
        "theme_evidence": theme_evidence,
        "brief": {"synthesis": synthesis, "themes": themes},
    }
    try:
        checked = _validated_brief_audit(
            audit_llm.json_call(BRIEF_AUDIT_SYSTEM,
                                json.dumps(payload, ensure_ascii=False)), themes)
    except Exception as exc:
        log(f"  导语客观性初审失败，进入修复: {exc}")
        checked = None
    synthesis_ok, failed = _brief_failures(checked, themes)
    if synthesis_ok and not failed:
        return synthesis, themes

    failed_payload = {
        **payload,
        "failed": {"synthesis": not synthesis_ok,
                   "themes": [{"index": index, "fields": sorted(fields)}
                              for index, fields in failed.items()]},
    }
    try:
        repair = audit_llm.json_call(
            BRIEF_REPAIR_SYSTEM, json.dumps(failed_payload, ensure_ascii=False))
        if isinstance(repair, dict):
            if not synthesis_ok and "synthesis" in repair:
                synthesis = str(repair.get("synthesis") or "").strip()[:80]
            for row in repair.get("themes") or []:
                if not isinstance(row, dict):
                    continue
                index = row.get("index")
                if not isinstance(index, int) or isinstance(index, bool) or index not in failed:
                    continue
                for field in failed[index]:
                    if field in row:
                        themes[index][field] = str(row.get(field) or "").strip()[:60]
    except Exception as exc:
        log(f"  导语客观性修复失败，继续复审: {exc}")

    payload["brief"] = {"synthesis": synthesis, "themes": themes}
    try:
        checked = _validated_brief_audit(
            audit_llm.json_call(BRIEF_AUDIT_SYSTEM,
                                json.dumps(payload, ensure_ascii=False)), themes)
    except Exception as exc:
        log(f"  导语客观性复审失败，移除不安全内容: {exc}")
        checked = None
    synthesis_ok, failed = _brief_failures(checked, themes)
    if not synthesis_ok:
        synthesis = ""
    themes = [theme for index, theme in enumerate(themes) if index not in failed]
    return synthesis, themes


def write_brief(llm, picked, secondary=None, audit_llm=None):
    """产出结构化今日主线：返回 (synthesis, themes)。
    themes 里的 member_ids 用最终输出 id（pick-N/more-N），与 event_to_item 保持一致。"""
    entries = ([("pick", e) for e in picked] +
               [("more", e) for e in (secondary or [])])
    id_of = {}
    lines = []
    for tier, e in entries:
        _id = f"{tier}-{e['ids'][0]}"
        id_of[_id] = e
        lines.append(f"[{_id}] ({CAT_NAMES.get(e['category'], e['category'])}) {e['title']}")
    valid = set(id_of)
    try:
        result = llm.json_call(BRIEF_SYSTEM, "\n".join(lines))
        synthesis = str(result.get("synthesis", "")).strip()[:80] if isinstance(result, dict) else ""
        themes = []
        for t in (result.get("themes", []) if isinstance(result, dict) else []):
            if not isinstance(t, dict):
                continue
            members = [m for m in (t.get("member_ids") or []) if m in valid]
            members = list(dict.fromkeys(members))   # 去重保序
            if not members:
                continue
            themes.append({
                "title": str(t.get("title", "")).strip()[:14],
                "one_liner": str(t.get("one_liner", "")).strip()[:60],
                "member_ids": members[:8],
            })
            if len(themes) >= 3:
                break
        if audit_llm is not None:
            member_items = [{
                "id": item_id,
                **{field: event.get(field) for field in
                   ("title", "summary", "context", "claims") if event.get(field)},
            } for item_id, event in id_of.items()]
            synthesis, themes = _audit_brief(
                audit_llm, synthesis, themes, member_items)
        return synthesis, themes
    except Exception as e:
        log(f"  导语/主线生成失败: {e}")
        return "", []


# ----------------------------------------------------------------
# 5.5 跨天事件登记表：今日精选与历史活跃事件的延续性匹配
# ----------------------------------------------------------------

EVENT_MATCH_SYSTEM = """你负责维护跨天新闻事件登记表。输入两组条目：
【登记表】正在追踪的活跃事件（编号 R0、R1…，含最近一次进展摘要和日期）
【今日】今天的精选事件（编号 T0、T1…）
找出今日事件中哪些是登记表某事件的【后续进展】：
同一主体 + 同一条持续发展的具体事件线（同一场冲突的后续、同一起收购案的新进展、同一次发布的后续反应）。
仅主题相似、领域相同、或只是涉及同一家公司的不同事情，都【不算】。
类别(category)不同的禁止匹配。拿不准就不匹配。
只输出 JSON：{"matches":[{"today":数字,"registry":数字}]}；没有匹配输出 {"matches":[]}。
不要输出任何其他文字。"""

CONTINUITY_GATE_SYSTEM = """你负责执行新闻事件线的连续性门。每个候选包含登记事件主线、今天的进展和最近最多 7 条登记历史。
对每个候选必须同时判断：
1. 今天的进展是否属于登记标题指向的同一条具体事件主线；
2. 今天的进展是否延续最近一条可信进展；
3. 每条历史是否确实属于这条具体事件线。类别相同、主体相同但具体事情不同都必须拒绝。
只输出 JSON：{"validations":[{"candidate":数字,"matches_mainline":布尔值,"matches_latest":布尔值,"history":[{"row":数字,"relevant":布尔值}]}]}。
每个候选和每条历史必须恰好返回一次，索引必须与输入一致。拿不准就返回 false，不要输出其他文字。"""

TRAJECTORY_GENERATION_SYSTEM = """你负责批量执行可信新闻延续的轨迹生成。输入中的 history 已逐行验证，
reports 是今天该条新闻的原始报道；这两者是唯一可用材料，不得使用其他登记行、常识或联网信息。
对每条输入分别生成：
- context（来龙）：只解释已验证事件线怎样走到今天，不补写链外背景；
- watch（走向）：说明接下来取决于 1-2 个关键变量，并给出至少一个可观察路标；
- watch_detail（详情走向）：仅当输入 include_watch_detail 为 true 时生成；完整保留 watch 的变量和路标语义，
  并可补充第二个变量、判断依据和更多可观察路标；
- claims：只放独立的分析或不确定判断，kind 只能是 analysis 或 uncertain，sources 必须来自输入 evidence_sources。
若最近历史有最终 watch，且今天材料足以判断，可在 context 中追加一句
“走向回对（状态）：结论”，状态只能是 兑现、部分兑现、未兑现、反转；证据不足或旧 watch 缺失时不要回对，
也不要写占位语。watch 和 watch_detail 禁止具体概率、无条件断言和来源外类比。
只输出 JSON：{"trajectories":[{"idx":数字,"context":"...","watch":"...","watch_detail":"...",
"claims":[{"text":"...","kind":"analysis|uncertain","sources":["来源"]}]}]}。
每个 idx 最多一次；只允许 idx/context/watch/watch_detail/claims 五个键，不要输出其他文字。"""

TRAJECTORY_AUDIT_SYSTEM = """你负责批量执行独立轨迹审计。每条输入的 history 是逐行验证的历史投影，
reports 是今天的原始报道；它们是唯一证据，不得使用未验证登记行、模型常识或联网补证据。
只检查 trajectory 中实际出现的 context、watch、watch_detail、claims，不检查或修改其他字段，也不得改变精选层级。
context 只能叙述已验证来龙；若含走向回对，必须有旧版最终 watch 和今天证据，并且状态只能是
兑现、部分兑现、未兑现、反转。watch 和 watch_detail 必须有 1-2 个有依据的关键变量和至少一个可观察路标，
不得含具体概率、无条件断言或来源外类比；watch_detail 必须完整保留 watch 的变量和路标语义。
逐条检查 claim 的类型、内容与 sources 归属。
只输出 JSON：{"audits":[{"idx":数字,"fields":{"context":布尔值,"watch":布尔值,"watch_detail":布尔值},
"claims":[布尔值]}]}。fields 只列 trajectory 中存在的文字字段，claims 数组与输入 claims 等长；
每个 idx 最多一次，不要输出其他文字。"""


def _trajectory_enabled(cfg):
    return (cfg.get("trajectory") or {}).get("enabled", True) is not False


def new_trajectory_health():
    return {
        "candidate_matches": 0,
        "continuity_accepted": 0,
        "continuity_rejected": 0,
        "filtered_history_rows": 0,
        "generation_fallbacks": 0,
        "audit_fallbacks": 0,
        "final_watch_count": 0,
        "final_trusted_continuation_count": 0,
        "selected_count": 0,
        "final_watch_coverage": 0.0,
    }


def _trajectory_fallback_units(proposal):
    return sum(field in proposal for field in ("context", "watch", "watch_detail")) \
        + len(proposal.get("claims", []))


def load_registry(data_dir):
    """读 events.json；不存在或损坏时返回空登记表（冷启动）。"""
    f = data_dir / "events.json"
    if f.exists():
        try:
            reg = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(reg.get("events"), list):
                return reg
            log("  events.json 结构异常，重建")
        except Exception as e:
            log(f"  events.json 读取失败，重建: {e}")
    return {"version": 1, "events": []}


def match_events_llm(llm, active_events, picked):
    """LLM 匹配今日精选与活跃事件，返回 [(today_idx, registry_idx), ...]。
    任何异常返回 None，调用方视为"今日全部按新事件处理"。"""
    reg_lines = []
    for i, e in enumerate(active_events):
        last = e["history"][-1] if e.get("history") else {}
        reg_lines.append(f"[R{i}] ({e.get('category', '')}) {e.get('title', '')} ｜ "
                         f"最近进展 {e.get('last_seen', '')}: {str(last.get('summary', ''))[:100]}")
    today_lines = []
    for j, ev in enumerate(picked):
        today_lines.append(f"[T{j}] ({ev.get('category', '')}) {ev.get('title', '')} ｜ "
                           f"{str(ev.get('summary', ''))[:100]}")
    user = "【登记表】\n" + "\n".join(reg_lines) + "\n\n【今日】\n" + "\n".join(today_lines)
    try:
        result = llm.json_call(EVENT_MATCH_SYSTEM, user)
        matches = result.get("matches", []) if isinstance(result, dict) else []
        pairs, seen_today, seen_reg = [], set(), set()
        for m in matches:
            if not isinstance(m, dict):
                continue
            t = _model_index(m.get("today"), len(picked))
            r = _model_index(m.get("registry"), len(active_events))
            if t is None or r is None:
                continue
            if t in seen_today or r in seen_reg:
                continue
            # 同类目硬校验：LLM 违规跨类匹配直接丢弃
            if picked[t].get("category") != active_events[r].get("category"):
                continue
            seen_today.add(t)
            seen_reg.add(r)
            pairs.append((t, r))
        return pairs
    except Exception as e:
        log(f"  事件匹配调用失败，今日全部按新事件处理: {e}")
        return None


def validate_continuity_llm(llm, pairs, active_events, picked, date_str, health=None):
    """Validate candidate continuations and their recent history as one batch.

    Returns ``(trusted_pairs, verified_history_by_today)``. Any malformed or
    missing result rejects only its candidate.
    """
    candidates = []
    histories = []
    for candidate_index, (today_index, registry_index) in enumerate(pairs):
        if not (0 <= today_index < len(picked)
                and 0 <= registry_index < len(active_events)):
            continue
        registry_event = active_events[registry_index]
        history = [row for row in registry_event.get("history", [])
                   if row.get("date") != date_str][-7:]
        histories.append(history)
        history_lines = [
            f"  [H{row_index}] {row.get('date', '')} | "
            f"{row.get('title', '')} | {str(row.get('summary', ''))[:160]}"
            for row_index, row in enumerate(history)
        ]
        today = picked[today_index]
        candidates.append(
            f"[C{candidate_index}] 类别 {today.get('category', '')}\n"
            f"登记主线: {registry_event.get('title', '')}\n"
            f"今天: {today.get('title', '')} | {str(today.get('summary', ''))[:160]}\n"
            f"历史:\n" + ("\n".join(history_lines) or "  （无）"))

    if len(candidates) != len(pairs) or not candidates:
        if health is not None:
            health["filtered_history_rows"] += sum(map(len, histories))
        return [], {}
    try:
        result = llm.json_call(CONTINUITY_GATE_SYSTEM, "\n\n".join(candidates))
    except Exception as exc:
        log(f"  连续性门调用失败，受影响候选按新事件处理: {exc}")
        if health is not None:
            health["filtered_history_rows"] += sum(map(len, histories))
        return [], {}
    validations = result.get("validations") if isinstance(result, dict) else None
    if not isinstance(validations, list):
        if health is not None:
            health["filtered_history_rows"] += sum(map(len, histories))
        return [], {}

    by_candidate = {}
    duplicates = set()
    for validation in validations:
        if not isinstance(validation, dict):
            continue
        candidate_index = validation.get("candidate")
        if type(candidate_index) is not int or not 0 <= candidate_index < len(pairs):
            continue
        if candidate_index in by_candidate:
            duplicates.add(candidate_index)
        else:
            by_candidate[candidate_index] = validation

    trusted_pairs = []
    verified_history_by_today = {}
    for candidate_index, pair in enumerate(pairs):
        validation = by_candidate.get(candidate_index)
        history = histories[candidate_index]
        if candidate_index in duplicates or not isinstance(validation, dict):
            continue
        if (type(validation.get("matches_mainline")) is not bool
                or type(validation.get("matches_latest")) is not bool):
            continue
        row_results = validation.get("history")
        if not isinstance(row_results, list):
            continue
        by_row = {}
        invalid_rows = False
        for row_result in row_results:
            if not isinstance(row_result, dict):
                invalid_rows = True
                break
            row_index = row_result.get("row")
            relevant = row_result.get("relevant")
            if (type(row_index) is not int or not 0 <= row_index < len(history)
                    or type(relevant) is not bool or row_index in by_row):
                invalid_rows = True
                break
            by_row[row_index] = relevant
        if invalid_rows or set(by_row) != set(range(len(history))):
            continue
        verified = [row for row_index, row in enumerate(history) if by_row[row_index]]
        if (not validation["matches_mainline"]
                or not validation["matches_latest"] or not verified
                or not history or not by_row[len(history) - 1]):
            continue
        trusted_pairs.append(pair)
        verified_history_by_today[pair[0]] = verified
    if health is not None:
        health["filtered_history_rows"] += (
            sum(map(len, histories))
            - sum(map(len, verified_history_by_today.values())))
    return trusted_pairs, verified_history_by_today


def _trajectory_history_projection(rows):
    fields = ("date", "title", "summary", "news_status", "watch", "sources",
              "item_ref")
    return [{field: copy.deepcopy(row[field]) for field in fields if field in row}
            for row in rows if isinstance(row, dict)]


def _trajectory_reports(event, items, source_limit):
    reports = []
    for source_index in _serialized_source_ids(event, items, limit=source_limit):
        source = items[source_index]
        reports.append({
            "id": source_index,
            "title": source.get("title", ""),
            "summary": source.get("evidence_text") or source.get("desc", ""),
            "source": source.get("source", ""),
            "source_id": source.get("source_id", ""),
        })
    return reports


def _trajectory_claim_sources(reports):
    """Keep public claim attribution aligned with today's serialized source names."""
    return {report["source"] for report in reports
            if isinstance(report.get("source"), str) and report["source"].strip()}


def _valid_trajectory_context(value, history, *, full_objectivity=False):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if len(value) > _field_limits(full_objectivity)["context"]:
        return None
    if "走向回对" not in value:
        return value
    matches = re.findall(r"走向回对（([^）]+)）：", value)
    if (value.count("走向回对") != 1 or len(matches) != 1
            or matches[0] not in TRAJECTORY_RECAP_STATUS
            or not history or not history[-1].get("watch")):
        return None
    return value


def _valid_trajectory_watch(value, *, detail=False):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    field = "watch_detail" if detail else "watch"
    if len(value) > _field_limits(detail)[field]:
        return None
    return value


def _valid_trajectory_claims(value, evidence_sources):
    if not isinstance(value, list) or len(value) > 4:
        return None
    claims = []
    for claim in value:
        if not isinstance(claim, dict) or set(claim) != {"text", "kind", "sources"}:
            return None
        text = claim.get("text")
        kind = claim.get("kind")
        sources = claim.get("sources")
        if (not isinstance(text, str) or not text.strip() or len(text.strip()) > 120
                or kind not in {"analysis", "uncertain"}
                or not isinstance(sources, list) or not sources
                or any(not isinstance(source, str) or not source.strip()
                       for source in sources)
                or not set(sources).issubset(evidence_sources)):
            return None
        claims.append({"text": text.strip(), "kind": kind,
                       "sources": list(dict.fromkeys(sources))})
    return claims


def _indexed_batch_rows(raw, key, size):
    rows = raw.get(key) if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        return {}, set()
    by_index = {}
    duplicates = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        index = row.get("idx")
        if type(index) is not int or not 0 <= index < size:
            continue
        if index in by_index:
            duplicates.add(index)
        else:
            by_index[index] = row
    return by_index, duplicates


def _restore_trajectory_field(event, snapshot, field):
    if field in snapshot:
        event[field] = copy.deepcopy(snapshot[field])
    else:
        event.pop(field, None)


def run_trajectory_stage(llm, picked, trusted_pairs, verified_history_by_today,
                         items, audit_llm=None, source_limit=5, health=None,
                         include_watch_detail=False):
    """Generate and independently audit trusted trajectories as separate batches."""
    if not trusted_pairs:
        return set()
    audit_llm = audit_llm or llm
    batch = []
    snapshots = []
    today_indexes = []
    for today_index, _ in trusted_pairs:
        if not 0 <= today_index < len(picked):
            continue
        event = picked[today_index]
        history = _trajectory_history_projection(
            verified_history_by_today.get(today_index, []))
        reports = _trajectory_reports(event, items or [], source_limit)
        snapshot = {field: copy.deepcopy(event[field])
                    for field in ("watch", "watch_detail", "claims") if field in event}
        batch.append({
            "idx": len(batch),
            "event": {field: event.get(field) for field in
                      ("title", "summary", "context", "watch",
                       "watch_detail", "claims")
                      if event.get(field)},
            "include_watch_detail": include_watch_detail,
            "history": history,
            "reports": reports,
            "evidence_sources": sorted(_trajectory_claim_sources(reports)),
        })
        snapshots.append(snapshot)
        today_indexes.append(today_index)
        # Base enrich context is generic background, not verified history.  Keep
        # it in the generation input above, but never use it as a public
        # trajectory fallback.
        event.pop("context", None)
    if not batch:
        return set()

    try:
        raw = llm.json_call(
            TRAJECTORY_GENERATION_SYSTEM,
            json.dumps({"items": batch}, ensure_ascii=False))
    except Exception as exc:
        log(f"  轨迹生成失败，可信延续保留主精加工内容: {exc}")
        if health is not None:
            health["generation_fallbacks"] += len(batch)
        return set()
    generated, generation_duplicates = _indexed_batch_rows(
        raw, "trajectories", len(batch))
    proposals = {}
    audit_items = []
    generation_fallback_indexes = set()
    for batch_index, input_row in enumerate(batch):
        row = generated.get(batch_index)
        if (batch_index in generation_duplicates or not isinstance(row, dict)
                or not set(row).issubset(
                    {"idx", "context", "watch", "watch_detail", "claims"})):
            generation_fallback_indexes.add(batch_index)
            continue
        proposal = {}
        if "context" in row:
            context = _valid_trajectory_context(
                row["context"], input_row["history"],
                full_objectivity=include_watch_detail)
            if context is not None:
                proposal["context"] = context
        if "watch" in row:
            watch = _valid_trajectory_watch(row["watch"])
            if watch is not None:
                proposal["watch"] = watch
        if include_watch_detail and "watch_detail" in row:
            watch_detail = _valid_trajectory_watch(
                row["watch_detail"], detail=True)
            if watch_detail is not None:
                proposal["watch_detail"] = watch_detail
        if "claims" in row:
            claims = _valid_trajectory_claims(
                row["claims"], set(input_row["evidence_sources"]))
            if claims is not None:
                proposal["claims"] = claims
        expected_fields = {"context", "watch", "claims"}
        if include_watch_detail:
            expected_fields.add("watch_detail")
        if set(proposal) != expected_fields:
            generation_fallback_indexes.add(batch_index)
        if include_watch_detail and not {"watch", "watch_detail"}.issubset(proposal):
            # The long field is an expansion of the short public contract.
            # Auditing only one side cannot establish their semantic agreement.
            continue
        if not proposal:
            continue
        proposals[batch_index] = proposal
        audit_items.append({
            "idx": batch_index,
            "history": input_row["history"],
            "reports": input_row["reports"],
            "trajectory": proposal,
        })
    if health is not None:
        health["generation_fallbacks"] += len(generation_fallback_indexes)
    if not audit_items:
        return set()

    try:
        raw_audit = audit_llm.json_call(
            TRAJECTORY_AUDIT_SYSTEM,
            json.dumps({"items": audit_items}, ensure_ascii=False))
    except Exception as exc:
        log(f"  轨迹审计失败，受影响条目恢复主精加工内容: {exc}")
        if health is not None:
            health["audit_fallbacks"] += sum(
                _trajectory_fallback_units(proposal)
                for proposal in proposals.values())
        return set()
    audited, audit_duplicates = _indexed_batch_rows(raw_audit, "audits", len(batch))
    successful_today_indexes = set()
    for batch_index, proposal in proposals.items():
        event = picked[today_indexes[batch_index]]
        snapshot = snapshots[batch_index]
        audit = audited.get(batch_index)
        if (batch_index in audit_duplicates or not isinstance(audit, dict)
                or set(audit) != {"idx", "fields", "claims"}):
            if health is not None:
                health["audit_fallbacks"] += _trajectory_fallback_units(proposal)
            continue
        fields = audit.get("fields")
        if not isinstance(fields, dict):
            if health is not None:
                health["audit_fallbacks"] += _trajectory_fallback_units(proposal)
            continue
        text_fields = [field for field in ("context", "watch", "watch_detail")
                       if field in proposal]
        if (set(fields) != set(text_fields)
                or any(type(fields[field]) is not bool for field in text_fields)):
            if health is not None:
                health["audit_fallbacks"] += _trajectory_fallback_units(proposal)
            continue
        claim_checks = audit.get("claims")
        proposed_claims = proposal.get("claims", [])
        if (not isinstance(claim_checks, list)
                or len(claim_checks) != len(proposed_claims)
                or any(type(value) is not bool for value in claim_checks)):
            if health is not None:
                health["audit_fallbacks"] += _trajectory_fallback_units(proposal)
            continue
        coupled_watch_fields = (
            {"watch", "watch_detail"}
            if include_watch_detail
            and {"watch", "watch_detail"}.issubset(proposal)
            else set()
        )
        if coupled_watch_fields:
            if all(fields[field] for field in coupled_watch_fields):
                for field in coupled_watch_fields:
                    event[field] = proposal[field]
            else:
                for field in coupled_watch_fields:
                    _restore_trajectory_field(event, snapshot, field)
                if health is not None:
                    health["audit_fallbacks"] += len(coupled_watch_fields)
        for field in text_fields:
            if field in coupled_watch_fields:
                continue
            if fields[field]:
                event[field] = proposal[field]
            else:
                _restore_trajectory_field(event, snapshot, field)
                if health is not None:
                    health["audit_fallbacks"] += 1
        if "claims" in proposal:
            kept = [claim for claim, valid in zip(proposed_claims, claim_checks)
                     if valid]
            if health is not None:
                health["audit_fallbacks"] += claim_checks.count(False)
            if kept:
                event["claims"] = kept
            else:
                event.pop("claims", None)
        successful_today_indexes.add(today_indexes[batch_index])
    return successful_today_indexes


def _registry_history_entry(event, date_str, cfg, items, item_kind, summary):
    entry = {"date": date_str, "title": event.get("title", ""),
             "summary": summary, "news_status": event.get("status", "")}
    if event.get("watch"):
        entry["watch"] = event["watch"]
    if items:
        source_limit = 4 if _rollout_output_enabled(cfg) else 5
        source_ids = [items[i].get("source_id")
                      for i in _serialized_source_ids(event, items, limit=source_limit)
                      if items[i].get("source_id")]
        if source_ids:
            entry["sources"] = list(dict.fromkeys(source_ids))
    if event.get("ids"):
        entry["item_ref"] = _same_day_item_ref(event, date_str, item_kind)
    source_keys = _same_day_source_keys(event, items or [])
    if source_keys:
        entry["source_keys"] = source_keys
    event_identity = _same_day_event_identity(event, items or [])
    if event_identity:
        entry["event_identity"] = event_identity
    return entry


def _same_day_item_ref(event, date_str, item_kind="pick"):
    ids = event.get("ids") or []
    return f"{date_str}:{item_kind}-{ids[0]}" if ids else ""


def _same_day_source_key(source):
    canonical_url = canonical_news_url(source.get("url"))
    if canonical_url:
        seed = f"url:{canonical_url}"
    else:
        source_id = str(source.get("source_id") or "").strip().casefold()
        content = news_content_fingerprint(source.get("title"), source.get("desc"))
        seed = f"source:{source_id}|content:{content}"
    return "src-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _same_day_source_keys(event, items):
    source_indexes = _serialized_source_ids(
        event, items or [], limit=len(event.get("ids") or []))
    return sorted({_same_day_source_key(items[index]) for index in source_indexes})


def _same_day_event_content_signature(event):
    payload = {
        field: _normalized_news_text(event.get(field))
        for field in ("category", "status", "summary", "title")
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _same_day_event_identity(event, items):
    """Return the deterministic initial identity for a same-day event."""
    source_keys = _same_day_source_keys(event, items)
    payload = {
        "content": _same_day_event_content_signature(event),
        "source_keys": source_keys,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "set-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _allocate_same_day_event_ids(picked, entries, matched, reserved_ids, date_str):
    """Allocate new IDs from stable descriptors without reusing reserved IDs."""
    groups = {}
    for index, event in enumerate(picked):
        if index in matched:
            continue
        descriptor = json.dumps({
            "content": _same_day_event_content_signature(event),
            "event_identity": entries[index].get("event_identity", ""),
            "source_keys": entries[index].get("source_keys", []),
        }, sort_keys=True, separators=(",", ":"))
        groups.setdefault(descriptor, []).append(index)

    used_ids = {value for value in reserved_ids if value}
    allocated = {}
    date_token = date_str.replace("-", "")
    for descriptor in sorted(groups):
        indexes = groups[descriptor]
        for ordinal, index in enumerate(indexes, start=1):
            seed = descriptor if len(indexes) == 1 else \
                f"{descriptor}|duplicate:{ordinal}"
            digest = hashlib.sha1(
                seed.encode("utf-8"),
                usedforsecurity=False,
            ).hexdigest()[:6]
            event_id = f"evt-{date_token}-{digest}"
            collision = 0
            while event_id in used_ids:
                collision += 1
                digest = hashlib.sha256(
                    f"{seed}|collision:{collision}".encode("utf-8")
                ).hexdigest()[:12]
                event_id = f"evt-{date_token}-{digest}"
            allocated[index] = event_id
            used_ids.add(event_id)
    return allocated


def _inherit_same_day_identity(entry, prior_today):
    if not prior_today:
        return entry
    if prior_today.get("event_identity"):
        entry["event_identity"] = prior_today["event_identity"]
    source_keys = set(prior_today.get("source_keys") or [])
    if str(prior_today.get("event_identity") or "").startswith("src-"):
        source_keys.add(prior_today["event_identity"])
    source_keys.update(entry.get("source_keys") or [])
    if source_keys:
        entry["source_keys"] = sorted(source_keys)
    return entry


def _same_day_rerun_pairs(candidates, eligible, date_str, item_kind,
                          items=None, excluded_object_ids=None):
    excluded_object_ids = excluded_object_ids or set()
    pairs = []
    candidate_indexes = set()
    matched_object_ids = set()
    edges = []
    for candidate_index, event in enumerate(candidates or []):
        item_ref = _same_day_item_ref(event, date_str, item_kind)
        source_keys = set(_same_day_source_keys(event, items or []))
        event_identity = _same_day_event_identity(event, items or [])
        if not item_ref and not source_keys and not event_identity:
            continue
        matches = [registry_event for registry_event in eligible
                   if id(registry_event) not in excluded_object_ids
                   and any(
                        row.get("date") == date_str
                        and ((source_keys and source_keys.intersection(
                                set(row.get("source_keys") or [])
                                | ({row["event_identity"]}
                                   if str(row.get("event_identity") or "")
                                   .startswith("src-") else set())))
                             or (event_identity
                                 and row.get("event_identity") == event_identity)
                             or (not row.get("event_identity")
                                 and not row.get("source_keys")
                                 and item_ref and row.get("item_ref") == item_ref))
                        for row in registry_event.get("history", []))]
        edges.extend((candidate_index, target) for target in matches)
    candidate_counts = {}
    target_counts = {}
    for candidate_index, target in edges:
        candidate_counts[candidate_index] = candidate_counts.get(candidate_index, 0) + 1
        target_counts[id(target)] = target_counts.get(id(target), 0) + 1
    for candidate_index, target in edges:
        if (candidate_counts[candidate_index] != 1
                or target_counts[id(target)] != 1):
            continue
        pairs.append((candidate_index, target))
        candidate_indexes.add(candidate_index)
        matched_object_ids.add(id(target))
    return pairs, candidate_indexes, matched_object_ids


def update_registry(registry, picked, pairs, active_events, date_str, cfg, items=None,
                    verified_history_by_today=None):
    """纯函数：把今日精选写入登记表（续接或新建），归档与剪枝，
    并回填 picked 的 event_id / day_count / history_prev。
    pairs 为 None（LLM 失败）时全部按新事件处理。"""
    evcfg = cfg.get("events") or {}
    archive_days = int(evcfg.get("archive_days", 7))
    prune_days = int(evcfg.get("prune_archived_days", 60))
    today = datetime.strptime(date_str, "%Y-%m-%d")
    registry["version"] = 2
    events = registry.setdefault("events", [])

    matched = {}
    for t, r in (pairs or []):
        if 0 <= t < len(picked) and 0 <= r < len(active_events):
            matched[t] = active_events[r]

    entries = [
        _registry_history_entry(
            event, date_str, cfg, items, "pick",
            event.get("summary") or event.get("title", ""))
        for event in picked
    ]
    new_event_ids = _allocate_same_day_event_ids(
        picked, entries, matched,
        {event.get("event_id") for event in events}, date_str)

    # 同日重跑幂等：清掉本日旧进展；已由 item_ref 确认的目标即使清空也保留容器，
    # 随后写入最终行，避免第二次 LLM 漂移导致 event_id 改变或产生重复事件。
    matched_target_ids = {id(event) for event in matched.values()}
    prior_today_by_target = {
        id(event): next(
            (row for row in reversed(event.get("history", []))
             if row.get("date") == date_str), None)
        for event in matched.values()
    }
    for e in events:
        e["history"] = [h for h in e.get("history", []) if h.get("date") != date_str]
    events[:] = [e for e in events if e["history"] or id(e) in matched_target_ids]
    for e in events:
        if e["history"]:
            e["last_seen"] = e["history"][-1]["date"]

    for idx, ev in enumerate(picked):
        entry = entries[idx]
        tgt = matched.get(idx)
        if tgt is None:
            eid = new_event_ids[idx]
            tgt = {"event_id": eid, "title": ev.get("title", ""),
                   "category": ev.get("category", ""), "status": "active",
                   "pinned": False, "first_seen": date_str, "last_seen": date_str,
                   "history": [entry]}
            events.append(tgt)
        else:
            prior_today = prior_today_by_target.get(id(tgt))
            _inherit_same_day_identity(entry, prior_today)
            tgt["history"].append(entry)
            tgt["last_seen"] = date_str
            tgt["status"] = "active"
            # 事件线名是身份标识，取首次出现那天的展示标题；当天的标题只进 history 行。
            if not tgt.get("title"):
                tgt["title"] = ev.get("title", "")
        ev["event_id"] = tgt["event_id"]
        if verified_history_by_today is not None and idx in matched:
            verified = verified_history_by_today.get(idx, [])
            ev["day_count"] = len({h.get("date") for h in verified if h.get("date")}) + 1
            ev["history_prev"] = verified
            if verified:
                ev["trusted_continuation"] = True
        else:
            ev["day_count"] = len({h["date"] for h in tgt["history"]})
            ev["history_prev"] = [h for h in tgt["history"] if h["date"] != date_str][-7:]

    def days_since(d):
        try:
            return (today - datetime.strptime(d, "%Y-%m-%d")).days
        except Exception:
            return 10 ** 6

    for e in events:
        if e.get("status") == "active" and days_since(e.get("last_seen", "")) > archive_days:
            e["status"] = "archived"
    events[:] = [e for e in events
                 if not (e.get("status") == "archived"
                         and days_since(e.get("last_seen", "")) > prune_days)]
    return registry


def _build_trajectory_review_cases(picked, items, cfg):
    """Project only final public trajectory fields and verified evidence."""
    cases = []
    source_limit = 4 if _rollout_output_enabled(cfg) else 5
    for picked_index, event in enumerate(picked):
        public = event_to_item(
            event, items or [], "pick", source_limit=source_limit,
            trajectory_enabled=_trajectory_enabled(cfg))
        if public.get("trusted_continuation") is not True and not public.get("watch"):
            continue
        # Judge 只审轨迹：continuity/history_support 仅适用于可信延续，对新事件的
        # 起因没有判据。把起因投影进去会让整体 decision 因它失败，拖垮轨迹门。
        trajectory_context = public.get("trusted_continuation") is True
        public_projection = {
            field: copy.deepcopy(public[field])
            for field in (
                "id", "title", "summary", "context", "watch", "claims",
                "trusted_continuation", "day_count", "history")
            if field in public and (field != "context" or trajectory_context)
        }
        sources = []
        for source_index in _serialized_source_ids(
                event, items or [], limit=source_limit):
            source = items[source_index]
            sources.append({
                "source": str(source.get("source") or ""),
                "title": str(source.get("title") or ""),
                "snippet": str(source.get("desc") or "")[:400],
            })
        verified_history = []
        if public.get("trusted_continuation") is True:
            verified_history = [{
                field: copy.deepcopy(row[field])
                for field in ("date", "title", "summary", "watch", "item_ref")
                if field in row
            } for row in event.get("history_prev", []) if isinstance(row, dict)]
        cases.append({
            "idx": len(cases),
            "picked_index": picked_index,
            "public": public_projection,
            "sources": sources,
            "verified_history": verified_history,
        })
    return cases


def build_enrich_review_cases(picked, items, cfg, enrich_sample):
    """Retain bounded evidence for every item named by the enrich sample."""
    sampled_ids = [
        item_id
        for category in sorted(enrich_sample or {})
        for item_id in enrich_sample[category]
    ]
    source_limit = 4 if _rollout_output_enabled(cfg) else 5
    public_by_id = {}
    for event in picked or []:
        public = event_to_item(
            event, items or [], "pick", source_limit=source_limit,
            trajectory_enabled=_trajectory_enabled(cfg))
        item_id = str(public.get("id") or "")
        if item_id:
            public_by_id[item_id] = (event, public)

    cases = []
    for item_id in sampled_ids:
        pair = public_by_id.get(item_id)
        if pair is None:
            continue
        event, public = pair
        public_projection = {
            field: copy.deepcopy(public[field])
            for field in (
                "id", "title", "summary", "context", "detail", "watch",
                "watch_detail", "claims", "trusted_continuation", "day_count",
                "history")
            if field in public
        }
        sources = []
        for source_index in _serialized_source_ids(
                event, items or [], limit=source_limit):
            source = items[source_index]
            sources.append({
                "source": str(source.get("source") or ""),
                "title": str(source.get("title") or ""),
                "snippet": str(source.get("desc") or "")[:400],
            })
        verified_history = []
        if public.get("trusted_continuation") is True:
            verified_history = [{
                field: copy.deepcopy(row[field])
                for field in ("date", "title", "summary", "watch", "item_ref")
                if field in row
            } for row in event.get("history_prev", []) if isinstance(row, dict)]
        cases.append({
            "public": public_projection,
            "sources": sources,
            "verified_history": verified_history,
        })
    return cases


def prepare_registry_transaction(llm, registry, picked, date_str, cfg,
                                 secondary=None, feedback=None, items=None,
                                 trajectory_audit_llm=None, trajectory_health=None,
                                 trajectory_review_cases=None, quality=None,
                                 preferred_event_ids=None):
    """Prepare the complete registry update in memory without persisting it."""
    registry = copy.deepcopy(registry)
    quality = quality if quality is not None else new_quality_stats()
    health = trajectory_health if trajectory_health is not None else new_trajectory_health()
    pinned_changed = apply_pins(registry, feedback or [])
    if pinned_changed:
        log(f"  钉选状态更新：{pinned_changed} 个事件")
    evcfg = cfg.get("events") or {}
    window = int(evcfg.get("match_window_days", 14))
    today = datetime.strptime(date_str, "%Y-%m-%d")

    def days_since(d):
        try:
            return (today - datetime.strptime(d, "%Y-%m-%d")).days
        except Exception:
            return 10 ** 6

    eligible = [e for e in registry["events"]
                if e.get("status") == "active"
                and 0 <= days_since(e.get("last_seen", "")) <= window]
    rerun_pairs, rerun_today, rerun_event_object_ids = _same_day_rerun_pairs(
        picked, eligible, date_str, "pick", items=items)
    secondary_rerun_pairs, _, _ = \
        _same_day_rerun_pairs(
            secondary, [event for event in eligible if event.get("pinned")],
            date_str, "more", items=items,
            excluded_object_ids=rerun_event_object_ids)
    secondary_prior_today = {
        id(event): next(
            (row for row in reversed(event.get("history", []))
             if row.get("date") == date_str), None)
        for _, event in secondary_rerun_pairs
    }

    # LLM 只处理未由稳定 item_ref 认出的候选；今天之前没有历史的事件不进匹配池。
    llm_active = [event for event in eligible
                  if id(event) not in rerun_event_object_ids
                  and any(row.get("date") != date_str for row in event.get("history", []))]
    llm_picked_indexes = [index for index in range(len(picked)) if index not in rerun_today]
    llm_picked = [picked[index] for index in llm_picked_indexes]
    llm_pairs = match_events_llm(llm, llm_active, llm_picked) \
        if (llm_active and llm_picked) else []
    hinted_event_ids = {
        (preferred_event_ids or {}).get(cross_source_event_key(event))
        for event in llm_picked
    }
    hinted_event_ids.discard(None)
    active_object_ids = {id(event) for event in llm_active}
    prune_window = int(evcfg.get("prune_archived_days", 60))
    llm_active.extend(
        event for event in registry["events"]
        if event.get("event_id") in hinted_event_ids
        and id(event) not in active_object_ids
        and 0 <= days_since(event.get("last_seen", "")) <= prune_window
        and any(row.get("date") != date_str for row in event.get("history", [])))
    event_index_by_id = {
        event.get("event_id"): index for index, event in enumerate(llm_active)
        if event.get("event_id")
    }
    hinted_pairs = []
    for local_today, event in enumerate(llm_picked):
        event_id = (preferred_event_ids or {}).get(cross_source_event_key(event))
        registry_index = event_index_by_id.get(event_id)
        if registry_index is not None:
            hinted_pairs.append((local_today, registry_index))
    unique_llm_pairs = []
    seen_today, seen_registry = set(), set()
    for today_index, registry_index in [*hinted_pairs, *(llm_pairs or [])]:
        if today_index in seen_today or registry_index in seen_registry:
            continue
        if (not 0 <= today_index < len(llm_picked)
                or not 0 <= registry_index < len(llm_active)):
            continue
        if (llm_picked[today_index].get("category")
                != llm_active[registry_index].get("category")):
            continue
        seen_today.add(today_index)
        seen_registry.add(registry_index)
        unique_llm_pairs.append((today_index, registry_index))
    llm_pairs = unique_llm_pairs
    active = [event for _, event in rerun_pairs] + llm_active
    pairs = [(today_index, active_index)
             for active_index, (today_index, _) in enumerate(rerun_pairs)]
    pairs.extend((llm_picked_indexes[today_index], len(rerun_pairs) + registry_index)
                  for today_index, registry_index in (llm_pairs or []))
    picked_target_object_ids = {
        id(active[registry_index]) for _, registry_index in pairs
        if 0 <= registry_index < len(active)
    }
    secondary_rerun_pairs = [
        (index, event) for index, event in secondary_rerun_pairs
        if id(event) not in picked_target_object_ids
    ]
    secondary_rerun_indexes = {index for index, _ in secondary_rerun_pairs}
    secondary_rerun_event_object_ids = {
        id(event) for _, event in secondary_rerun_pairs
    }
    continuity_pairs = [
        pair for pair in pairs
        if any(row.get("date") != date_str
               for row in active[pair[1]].get("history", []))
    ]
    health["candidate_matches"] = len(continuity_pairs)
    trusted_pairs, verified_history_by_today = validate_continuity_llm(
        llm, continuity_pairs, active, picked, date_str,
        health=health) if continuity_pairs else ([], {})
    health["continuity_accepted"] = len(trusted_pairs)
    health["continuity_rejected"] = len(continuity_pairs) - len(trusted_pairs)
    trajectory_successes = set()
    if _trajectory_enabled(cfg):
        trajectory_successes = run_trajectory_stage(
            llm, picked, trusted_pairs, verified_history_by_today, items or [],
            audit_llm=trajectory_audit_llm,
            source_limit=4 if _rollout_output_enabled(cfg) else 5,
            health=health,
            include_watch_detail=_rollout_output_enabled(cfg))
    # context 承载两种前情：可信延续是轨迹生成的来龙，新事件是 enrich 抽取的起因。
    # 进过轨迹批次的事件已在 run_trajectory_stage 里丢掉 enrich 起因，生成失败就没有
    # 前情可展示；连续性门拒绝的事件按新事件处理，保留它的起因。
    failed_projection_today = {today_index for today_index, _ in pairs} - \
        trajectory_successes
    for today_index in failed_projection_today:
        for field in ("watch_recap", "recap", "trusted_continuation"):
            picked[today_index].pop(field, None)
    projected_history = {
        today_index: history
        for today_index, history in verified_history_by_today.items()
        if today_index in trajectory_successes
    }
    rerun_registry_pairs = [
        pair for pair in pairs if pair[0] in rerun_today
    ]
    registry_pairs = list(trusted_pairs)
    registry_pairs.extend(
        pair for pair in rerun_registry_pairs if pair not in registry_pairs)
    # Trajectory generation may have replaced fields after the pipeline's
    # initial cleanup. Sanitize once more before taking the registry snapshot;
    # write_output repeats the same idempotent cleanup for direct callers.
    prepare_events_for_output(picked, secondary or [], items or [], cfg)
    update_registry(
        registry, picked, registry_pairs, active, date_str, cfg, items=items,
        verified_history_by_today=projected_history)
    health["selected_count"] = len(picked)
    health["final_watch_count"] = (sum(1 for event in picked if event.get("watch"))
                                   if _trajectory_enabled(cfg) else 0)
    health["final_trusted_continuation_count"] = (
        sum(1 for event in picked if event.get("trusted_continuation") is True)
        if _trajectory_enabled(cfg) else 0)
    health["final_watch_coverage"] = (
        health["final_watch_count"] / len(picked) if picked else 0.0)
    if trajectory_review_cases is not None:
        trajectory_review_cases.clear()
        trajectory_review_cases.extend(
            _build_trajectory_review_cases(picked, items or [], cfg))

    # 钉选事件今天没进精选时，尝试与"更多资讯"补匹配续接进展，
    # 保证追踪中的事件不因分数不过线而断档
    if secondary:
        for secondary_index, target in secondary_rerun_pairs:
            if not any(target is event for event in registry["events"]):
                registry["events"].append(target)
            event = secondary[secondary_index]
            entry = _registry_history_entry(
                event, date_str, cfg, items, "more",
                event.get("summary") or event.get("title", ""))
            _inherit_same_day_identity(
                entry, secondary_prior_today.get(id(target)))
            target["history"].append(entry)
            target["last_seen"] = date_str
        pinned_stale = [e for e in registry["events"]
                        if e.get("pinned") and e.get("status") == "active"
                        and e.get("last_seen") != date_str
                        and id(e) not in secondary_rerun_event_object_ids
                        and any(h.get("date") != date_str for h in e.get("history", []))]
        unmatched_secondary_indexes = [index for index in range(len(secondary))
                                       if index not in secondary_rerun_indexes]
        unmatched_secondary = [secondary[index] for index in unmatched_secondary_indexes]
        if pinned_stale and unmatched_secondary:
            sec_pairs = match_events_llm(llm, pinned_stale, unmatched_secondary) or []
            for t, r in sec_pairs:
                sev, tgt = secondary[unmatched_secondary_indexes[t]], pinned_stale[r]
                tgt["history"].append(_registry_history_entry(
                    sev, date_str, cfg, items, "more",
                    sev.get("summary") or sev.get("title", "")))
                tgt["last_seen"] = date_str
            if sec_pairs:
                log(f"  钉选补匹配：{len(sec_pairs)} 个钉选事件从'更多资讯'续上进展")

    registry["events"] = reconcile_stale_event_lines(
        llm, registry["events"], date_str, quality)
    return registry


def track_events(llm, picked, date_str, cfg, secondary=None, feedback=None, items=None,
                 trajectory_audit_llm=None, trajectory_health=None,
                 trajectory_review_cases=None, persist=True, quality=None,
                 registry=None, preferred_event_ids=None):
    """Load and prepare one registry transaction, optionally persisting it."""
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    health = trajectory_health if trajectory_health is not None else new_trajectory_health()
    registry = prepare_registry_transaction(
        llm, registry if registry is not None else load_registry(data_dir),
        picked, date_str, cfg,
        secondary=secondary, feedback=feedback, items=items,
        trajectory_audit_llm=trajectory_audit_llm, trajectory_health=health,
        trajectory_review_cases=trajectory_review_cases, quality=quality,
        preferred_event_ids=preferred_event_ids)
    if persist:
        persist_registry(registry, data_dir)
    n_cont = sum(1 for ev in picked if ev.get("trusted_continuation"))
    n_active = sum(1 for event in registry["events"] if event.get("status") == "active")
    log(f"  事件登记表：活跃 {n_active}，续接 {n_cont}，登记总数 {len(registry['events'])}")
    log("  轨迹健康：候选匹配 {candidate_matches}，连续性通过/拒绝 "
        "{continuity_accepted}/{continuity_rejected}，过滤历史行 "
        "{filtered_history_rows}，生成回退 {generation_fallbacks}，审计回退 "
        "{audit_fallbacks}，最终走向 {final_watch_count}/{selected_count} "
        "({coverage:.1%})".format(coverage=health["final_watch_coverage"], **health))
    return registry


def persist_registry(registry, data_dir=None):
    """Atomically commit a fully prepared registry after daily output succeeds."""
    target_dir = Path(data_dir) if data_dir is not None else (
        Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data")
    target_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(target_dir / "events.json", registry)


# ----------------------------------------------------------------
# 5.6 偏好学习：消费 feedback.json / read_later.json
#   - track/untrack  -> events.json 钉选
#   - 来源质量低      -> 运行时降低该源条目可信度（不改 sources.yaml）
#   - 其余反馈+稍后读 -> LLM 蒸馏进 interest_profile.md（明文，可手改）
#   - 画像            -> 对当日事件打"兴趣契合分"，换算成分数乘数
# ----------------------------------------------------------------

PROFILE_MARKER_RE = re.compile(r"<!--\s*last_feedback_ts:\s*([^>]*?)\s*-->")
PROFILE_DEFAULT = """# 兴趣画像
<!-- last_feedback_ts: 1970-01-01T00:00:00Z -->

本文件由管线自动蒸馏页面反馈生成，也可以直接手改（增删行都会保留，
除非与后续反馈明确矛盾）。要点行以"- "开头，管线据此判断画像是否为空。

## 学习参考系
（暂无，可手写：长期学习方向 / 当前能力栈 / 希望积累的判断力 / 资讯转化偏好。此段蒸馏时受保护、不被自动改写）

## 更关注
（暂无）

## 不关注
（暂无）

## 来源印象
（暂无）
"""

PROFILE_SYSTEM = """你维护一份个人新闻"兴趣画像"文档（markdown）。
输入：当前画像全文 + 一批新的用户反馈（动作、条目标题、类目、理由、备注、来源）和新收藏的稍后读标题。
任务：把新反馈蒸馏进画像，输出更新后的画像全文。
规则：
- 保持三个小节：## 更关注 / ## 不关注 / ## 来源印象；每节内是要点行，每行以"- "开头（一行一个偏好，≤25字）
- 若输入含"## 学习参考系"段，原样保留、不要改写（那是用户手写的长期学习参考系）
- 若输入仍含旧"## 我的处境"段，也原样保留、不要改写
- 已有要点行是用户认可或手写的，除非与新反馈明确矛盾，否则原样保留
- 归纳到主题/领域层面（如"- 航天工程细节"），不要罗列具体新闻标题
- 同一偏好被反复印证时可在行尾标注 (xN) 表示强度
- 全文不超过 40 行；小节为空时写"（暂无）"
只输出画像 markdown 全文，不要解释，不要代码块包裹。"""

FIT_SYSTEM = """根据用户的兴趣画像，为每条新闻事件打"兴趣契合分"0-10：
10 = 画像明确表示高度关注的主题；5 = 画像未提及或中性；0 = 画像明确表示不关注。
画像没提到的一律给 5，不要引申猜测。
只输出 JSON：{"fits":[{"idx":编号,"fit":0-10}]}，不要其他文字。"""

FEEDBACK_ACT_NAMES = {"not_interested": "不感兴趣", "more_like_this": "更关注类似",
                      "low_quality_source": "来源质量低", "track": "继续追踪"}


def load_state_list(data_dir, filename, key):
    """读 feedback.json / read_later.json 里的列表；缺失或损坏一律返回 []。"""
    f = data_dir / filename
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        lst = data.get(key)
        return lst if isinstance(lst, list) else []
    except Exception as e:
        log(f"  {filename} 读取失败，忽略: {e}")
        return []


def source_penalties(feedback, date_str, window_days=90, step=0.1, floor=0.7):
    """"来源质量低"反馈 -> {来源名: 可信度乘数}。
    近 window_days 天内每个"有反馈的自然日"记一次，每次降 step，最低 floor。"""
    today = datetime.strptime(date_str, "%Y-%m-%d")
    strikes = {}
    for e in feedback:
        if e.get("action") != "low_quality_source" or not e.get("source"):
            continue
        day = str(e.get("ts", ""))[:10]
        try:
            if not (0 <= (today - datetime.strptime(day, "%Y-%m-%d")).days <= window_days):
                continue
        except ValueError:
            continue
        strikes.setdefault(str(e["source"]), set()).add(day)
    return {s: round(max(floor, 1 - step * len(days)), 2) for s, days in strikes.items()}


def apply_pins(registry, feedback):
    """track/untrack 反馈 -> 登记表事件 pinned 位（按时间取每个事件最后一次动作）。"""
    by_event = {}
    for e in feedback or []:
        if e.get("action") in ("track", "untrack") and e.get("event_id"):
            by_event.setdefault(e["event_id"], []).append((str(e.get("ts", "")), e["action"]))
    changed = 0
    for ev in registry.get("events", []):
        acts = by_event.get(ev.get("event_id"))
        if not acts:
            continue
        want = max(acts)[1] == "track"
        if bool(ev.get("pinned")) != want:
            ev["pinned"] = want
            changed += 1
    return changed


def profile_has_content(text):
    return any(line.strip().startswith("- ") for line in (text or "").splitlines())


def split_section(text, header):
    """按 '## <header>' 切出该段（含标题行，到下一个 '## ' 或 EOF）。
    返回 (去掉该段的文本, 该段块字符串或 '')。找不到则 (原文, '')。
    用于把用户手写的"学习参考系"等保护段摘出、绕过画像蒸馏 LLM，再原样贴回——
    否则 PROFILE_SYSTEM 全文重写会把它丢掉。"""
    lines = (text or "").splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip() == f"## {header}"), None)
    if start is None:
        return text, ""
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")),
               len(lines))
    block = "\n".join(lines[start:end]).rstrip()
    rest = "\n".join(lines[:start] + lines[end:])
    return rest, block


def update_profile(llm, data_dir, feedback, read_later):
    """把 marker 之后的新反馈蒸馏进 interest_profile.md。
    无新反馈不调 LLM；蒸馏失败保留旧画像、不推进 marker。返回画像全文。"""
    data_dir.mkdir(parents=True, exist_ok=True)  # 本函数早于 main 里其他 mkdir 执行
    pf = data_dir / "interest_profile.md"
    try:
        text = pf.read_text(encoding="utf-8") if pf.exists() else PROFILE_DEFAULT
    except Exception:
        text = PROFILE_DEFAULT
    m = PROFILE_MARKER_RE.search(text)
    marker = m.group(1).strip() if m else "1970-01-01T00:00:00Z"

    def newer(ts):
        return isinstance(ts, str) and ts > marker

    fb_new = [e for e in feedback
              if newer(e.get("ts")) and e.get("action") in FEEDBACK_ACT_NAMES
              and not (e.get("action") == "not_interested"
                       and "只是今天不想看" in (e.get("reasons") or [])
                       and not e.get("note"))]
    rl_new = [it for it in read_later if newer(it.get("ts"))]
    if not fb_new and not rl_new:
        if not pf.exists():
            pf.write_text(text, encoding="utf-8")  # 首次落盘默认画像，方便手改
        return text

    fb_lines = []
    for e in fb_new[-80:]:
        parts = [FEEDBACK_ACT_NAMES[e["action"]], f"[{e.get('category', '')}]",
                 str(e.get("title", ""))[:60]]
        if e.get("reasons"):
            parts.append("理由:" + "/".join(str(r) for r in e["reasons"]))
        if e.get("note"):
            parts.append("备注:" + str(e["note"])[:80])
        if e.get("source"):
            parts.append("来源:" + str(e["source"]))
        fb_lines.append(" ｜ ".join(parts))
    rl_lines = [f"[{it.get('category', '')}] {str(it.get('title', ''))[:60]}"
                for it in rl_new[-40:]]
    # 手写参考系段摘出、不进 LLM（LLM 只蒸馏兴趣），蒸馏完再原样贴回。
    # 同时兼容旧的"我的处境"段，避免老画像在全文重写时被冲掉。
    text_for_llm = text
    protected_blocks = []
    for header in ("学习参考系", "我的处境"):
        text_for_llm, block = split_section(text_for_llm, header)
        if block:
            protected_blocks.append(block)
    body = PROFILE_MARKER_RE.sub("", text_for_llm).strip()
    user = ("【当前画像】\n" + body +
            "\n\n【新反馈】\n" + ("\n".join(fb_lines) or "（无）") +
            "\n\n【新收藏的稍后读】\n" + ("\n".join(rl_lines) or "（无）"))
    new_marker = max([str(e.get("ts", "")) for e in fb_new] +
                     [str(it.get("ts", "")) for it in rl_new])
    try:
        out = llm.text_call(PROFILE_SYSTEM, user, temperature=0.2)
        out = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", out).strip()
        if "## 更关注" not in out or "## 不关注" not in out:
            raise ValueError("画像输出缺少必需小节")
        out = PROFILE_MARKER_RE.sub("", out).strip()
        for header in ("学习参考系", "我的处境"):
            out, _ = split_section(out, header)  # 去掉 LLM 可能误带的保护段，防重复
        lines = out.splitlines()
        insert_at = 1 if lines and lines[0].startswith("#") else 0
        lines.insert(insert_at, f"<!-- last_feedback_ts: {new_marker} -->")
        if protected_blocks:  # 保护段原样贴回：放在第一个 "## " 小节前（导语之后）
            pos = next((k for k, ln in enumerate(lines) if ln.startswith("## ")), len(lines))
            lines.insert(pos, "\n\n".join(protected_blocks) + "\n")
        new_text = "\n".join(lines).rstrip() + "\n"
        pf.write_text(new_text, encoding="utf-8")
        log(f"  画像已更新：吸收 {len(fb_new)} 条反馈、{len(rl_new)} 条稍后读")
        return new_text
    except Exception as e:
        log(f"  画像蒸馏失败，保留旧画像: {e}")
        return text


def interest_fit(llm, profile_text, events, span=0.30):
    """按画像给事件打契合分，写入 ev['interest_mult'] ∈ [1-span, 1+span]。
    span 由 config 的 scoring.fit_span 控制（默认 0.30，即 ±30%）。
    画像为空或调用失败时不写（默认 1.0）。中性 5 分恰好等于 1.0。"""
    if not events or not profile_has_content(profile_text):
        return
    span = max(0.0, min(0.6, float(span)))
    lines = [f"[{i}] ({CAT_NAMES.get(e.get('category', ''), e.get('category', ''))}) "
             f"{e.get('title', '')}" for i, e in enumerate(events)]
    user = "【兴趣画像】\n" + profile_text + "\n\n【今日事件】\n" + "\n".join(lines)
    try:
        result = llm.json_call(FIT_SYSTEM, user)
        fits = result.get("fits", []) if isinstance(result, dict) else []
        for f_ in fits:
            if not isinstance(f_, dict):
                continue
            i = _model_index(f_.get("idx"), len(events))
            fit = _model_number(f_.get("fit"))
            if i is not None and fit is not None:
                fit = max(0.0, min(10.0, fit))
                events[i]["interest_mult"] = round(
                    1.0 + (fit - 5.0) / 5.0 * span, 3)
        n = sum(1 for e in events if e.get("interest_mult", 1.0) != 1.0)
        log(f"  兴趣拟合：{n}/{len(events)} 个事件获得非中性乘数")
    except Exception as e:
        log(f"  兴趣拟合失败，保持中性: {e}")


# ----------------------------------------------------------------
# 5.7 深度阅读频道：独立于新闻管线的长文推荐（阈值制 0-4 篇）
# ----------------------------------------------------------------

DEEP_SYSTEM = """你为个人读者筛选"今天值得花时间深读的长文"。
输入若干候选文章（标题+摘要+来源），可能附带读者的兴趣画像。
给每篇打"深读价值分"0-10，标准：
- 实质密度：有真实信息增量、数据、一手经验，而非口水/热点复读
- 独到洞察：提供新框架、方法论或反直觉结论
- 持久价值：一周后再读仍有价值
显著契合兴趣画像可 +1，明确落在画像"不关注"里的 -2。宁缺毋滥，平庸的给低分。
候选行若标有 filter=finance，还要判断文章核心是否属于宏观经济、商业/产业、市场、
劳动就业或公共经济政策。普通 AI/科技/政治评论不算，除非经济或商业分析是主体。
对每篇输出：
{"idx": 编号, "score": 0-10, "title_zh": "中文标题（中文原题则原样保留，≤30字）",
 "brief": "一句话讲这篇是什么（≤40字）", "why": "为什么值得花时间读（≤60字）",
 "key_points": ["核心观点，最多3条，每条≤60字"], "audience": "适合谁读（≤50字）",
 "takeaway": "读完最该带走的一句话（≤80字）",
 "content_type": "reporting|analysis|opinion", "topic_fit": true|false}
content_type 分别表示报道、分析、观点；无法可靠判断时省略该字段。
未标 filter 的候选，topic_fit 一律输出 true。
只输出 JSON 对象：{"picks":[候选...]}。只有一个也必须放在 picks 数组里。不要其他文字。"""


def estimate_read_minutes(item, lang):
    """按 RSS 全文长度估算阅读分钟数（中文 400 字/分，英文 220 词/分），3-60 封顶。"""
    if lang == "zh":
        n = item.get("content_chars") or len(re.sub(r"\s", "", item.get("desc", "")))
        m = n / 400
    else:
        n = item.get("content_words") or len(item.get("desc", "").split())
        m = n / 220
    return max(3, min(60, int(m + 0.999)))


def normalize_deep_content_type(value):
    """只保留公开契约允许的深读内容类型；旧数据和非法值统一省略。"""
    return value if value in {"reporting", "analysis", "opinion"} else None


def load_deep_seen(data_dir, date_str, filename="deep_seen.json"):
    """已推荐 URL 滚动表；当日条目剔除（同日重跑幂等：重跑时重新评选）。
    filename 可切换到 papers_seen.json 等，供其他独立频道共用同一去重逻辑。"""
    f = data_dir / filename
    seen = {"version": 1, "urls": {}}
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data.get("urls"), dict):
                seen["urls"] = {u: d for u, d in data["urls"].items() if d != date_str}
        except Exception as e:
            log(f"  deep_seen.json 读取失败，重建: {e}")
    return seen


DEEP_CHANNELS = ("ai_engineering", "tech_business", "society_finance")

FINANCE_EVIDENCE_RE = re.compile(
    r"(?:"
    r"\b(?:economy|economies|economic|economics|macroeconomy|macroeconomic|gdp|"
    r"inflation|deflation|recession|fiscal|monetary)\b|"
    r"\bcentral banks?\b|\binterest rates?\b|\b(?:national|government) debt\b|"
    r"\b(?:stocks?|stock markets?|equities|equity valuations?|bonds?|treasury yields?|"
    r"market selloffs?|investors?|valuations?|ipos?|dividends?)\b|"
    r"\b(?:industrial policy|manufacturing|supply chains?|revenues?|profits?|earnings|"
    r"business models?|market shares?|capital expenditures?|capex|productivity|"
    r"economic growth)\b|"
    r"\b(?:employment|unemployment|wages?|jobs?|workforce|labor (?:market|demand|force)|"
    r"labour (?:market|demand|force))\b|"
    r"\b(?:taxes|taxation|tariffs?|subsid(?:y|ies)|budget deficits?|public spending|"
    r"public procurement|economic regulation|financial regulation)\b|"
    r"宏观经济|经济增长|经济衰退|国内生产总值|通货膨胀|通货紧缩|通胀|通缩|"
    r"货币政策|财政政策|中央银行|央行|利率|国债|政府债务|"
    r"股票市场|股市|股票|债券|收益率|投资者|估值|首次公开募股|分红|"
    r"产业政策|制造业|供应链|营业收入|营收|利润|盈利|财报|商业模式|市场份额|"
    r"资本支出|资本开支|生产率|劳动市场|劳动力|就业|失业|工资|薪资|"
    r"税收|税率|关税|补贴|预算赤字|公共支出|政府采购|经济监管|金融监管"
    r")",
    re.IGNORECASE,
)


def normalize_deep_channel(channel):
    """兼容旧配置名；新数据统一写 society_finance。"""
    return "society_finance" if channel == "zh_society_finance" else channel


def deep_source_channel(source):
    """旧配置兼容映射；新源应在 sources.yaml 显式声明 channel。"""
    configured = normalize_deep_channel(source.get("channel"))
    if configured in DEEP_CHANNELS:
        return configured
    if source.get("lang") == "zh":
        return "society_finance"
    if source.get("id") in {"stratechery", "pragmaticengineer"}:
        return "tech_business"
    return "ai_engineering"


def deep_fetcher(source):
    """深读源与主抓取线共用同一 type -> fetcher 协议。"""
    return FETCHERS.get(source.get("type", "rss"), fetch_rss)


def deep_topic_matches(source, result, candidate):
    """综合源须通过模型主题判断；finance 另须有确定性财经文本证据。"""
    topic_filter = source.get("topic_filter")
    if not topic_filter:
        return True
    if result.get("topic_fit") is not True:
        return False
    if topic_filter != "finance":
        return True
    if not isinstance(candidate, dict):
        return False
    text = unicodedata.normalize(
        "NFKC",
        f"{candidate.get('title') or ''}\n{candidate.get('desc') or ''}",
    ).casefold()
    return bool(text.strip() and FINANCE_EVIDENCE_RE.search(text))


def select_deep_soft_quota(scored, pick_max):
    """每栏优先一篇；空栏或剩余名额按总分回填，不降低既有质量门槛。"""
    ordered = sorted(scored, key=lambda t: -t[0])
    selected, used = [], set()
    for channel in DEEP_CHANNELS:
        hit = next((t for t in ordered
                    if t[1] not in used and t[2].get("channel") == channel), None)
        if hit and len(selected) < pick_max:
            selected.append(hit)
            used.add(hit[1])
    for row in ordered:
        if len(selected) >= pick_max:
            break
        if row[1] not in used:
            selected.append(row)
            used.add(row[1])
    return selected


def update_deep_health(data_dir, date_str, sources, fetch_stats, candidates,
                       score_stats, picked):
    """记录最近 14 天深读抓取、去重、评分、主题匹配与入选。"""
    path = data_dir / "deep_health.json"
    health = {"version": 2, "days": {}}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded.get("days"), dict):
                health["days"] = loaded["days"]
        except Exception as e:
            log(f"  deep_health.json 读取失败，重建: {e}")
    source_rows = {}
    source_by_id = {s["id"]: s for s in sources}
    for source in sources:
        stat = fetch_stats.get(source["id"], {})
        source_rows[source["id"]] = {
            "fetch_ok": not bool(stat.get("error", False)),
            "fetch_error": "fetch_failed" if stat.get("error", False) else "",
            "fetched": int(stat.get("count", 0)),
            "candidates": 0,
            "scored": 0,
            "topic_matched": 0,
            "above_threshold": 0,
            "picked": 0,
        }
    channel_rows = {c: {"candidates": 0, "scored": 0, "topic_matched": 0,
                        "above_threshold": 0, "picked": 0}
                    for c in DEEP_CHANNELS}
    for item in candidates:
        sid = item.get("source_id")
        channel = normalize_deep_channel(item.get("channel", "ai_engineering"))
        if sid in source_rows:
            source_rows[sid]["candidates"] += 1
        channel_rows[channel]["candidates"] += 1
    for sid, metrics in score_stats.items():
        if sid not in source_rows:
            continue
        channel = deep_source_channel(source_by_id[sid])
        for key in ("scored", "topic_matched", "above_threshold"):
            value = int(metrics.get(key, 0))
            source_rows[sid][key] = value
            channel_rows[channel][key] += value
    picked_urls = {item.get("url") for item in picked}
    for item in candidates:
        if item.get("url") not in picked_urls:
            continue
        sid = item.get("source_id")
        channel = normalize_deep_channel(item.get("channel", "ai_engineering"))
        if sid in source_rows:
            source_rows[sid]["picked"] += 1
        channel_rows[channel]["picked"] += 1
    health["days"][date_str] = {"sources": source_rows, "channels": channel_rows}
    cutoff = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=13)).strftime("%Y-%m-%d")
    health["days"] = {d: v for d, v in health["days"].items() if d >= cutoff}
    data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(health, ensure_ascii=False, indent=1), encoding="utf-8")


def deep_channel(llm, cfg, date_str, profile_text=""):
    """深读频道编排。独立故障域：任何异常只 log 并返回 []，绝不影响新闻主管线。"""
    try:
        dcfg = cfg.get("deep") or {}
        if not dcfg.get("enabled", False):
            return []
        src_cfg = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
        deep_sources = [s for s in (src_cfg.get("deep_sources") or [])
                        if s.get("enabled", True)]
        # deep 源同样支持 {rsshub} 占位符（未配 RSSHUB_BASE 时自动跳过该源）
        deep_sources = resolve_rsshub_sources(deep_sources)
        if not deep_sources:
            return []
        window_start = datetime.now(timezone.utc) - timedelta(
            hours=int(dcfg.get("window_hours", 78)))
        max_per = int(dcfg.get("max_per_source", 5))
        fetched_candidates = []
        fetch_stats = {}
        for s in deep_sources:
            src = dict(s, source_type="analysis", credibility=7)
            fetched, err = deep_fetcher(src)(src, window_start, max_per)
            fetch_stats[s["id"]] = {"count": len(fetched), "error": err}
            for it in fetched:
                it["source_id"] = s["id"]
                it["source"] = s["name"]
                it["lang"] = s.get("lang", "en")
                it["channel"] = deep_source_channel(s)
                it["topic_filter"] = s.get("topic_filter", "")
            fetched_candidates += fetched

        data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
        seen = load_deep_seen(data_dir, date_str)
        candidates = [c for c in fetched_candidates if c["url"] not in seen["urls"]]
        log(f"  深读候选：{len(candidates)} 篇（去重后）")
        if not candidates:
            update_deep_health(data_dir, date_str, deep_sources, fetch_stats,
                               candidates, {}, [])
            return []

        lines = [f"[{i}] ({c['source']}/{c['lang']}"
                 f"{'; filter=' + c['topic_filter'] if c.get('topic_filter') else ''}) "
                 f"{c['title']}\n    {c['desc'][:200]}"
                 for i, c in enumerate(candidates)]
        user = ""
        if profile_has_content(profile_text):
            user = "【兴趣画像】\n" + profile_text + "\n\n"
        user += "【候选文章】\n" + "\n".join(lines)
        try:
            result = llm.json_call(DEEP_SYSTEM, user)
        except Exception:
            update_deep_health(data_dir, date_str, deep_sources, fetch_stats,
                               candidates, {}, [])
            raise

        rows = _model_rows(result, "picks")
        if rows is None:
            log("  深读返回结构非法，本次不推荐")
            rows = []
        scored = []
        score_stats = {}
        source_by_id = {s["id"]: s for s in deep_sources}
        threshold = float(dcfg.get("pick_threshold", 7))
        for r in rows:
            if not isinstance(r, dict):
                continue
            i = _model_index(r.get("idx"), len(candidates))
            score = _model_number(r.get("score"))
            if i is not None and score is not None:
                sid = candidates[i].get("source_id")
                metrics = score_stats.setdefault(
                    sid, {"scored": 0, "topic_matched": 0, "above_threshold": 0})
                metrics["scored"] += 1
                if deep_topic_matches(source_by_id.get(sid, {}), r, candidates[i]):
                    metrics["topic_matched"] += 1
                    if score >= threshold:
                        metrics["above_threshold"] += 1
                else:
                    continue
                r["channel"] = candidates[i].get("channel", "ai_engineering")
                scored.append((max(0.0, min(10.0, score)), i, r))
        pick_max = int(dcfg.get("pick_max", 3))
        scored = select_deep_soft_quota([t for t in scored if t[0] >= threshold], pick_max)

        deep, used = [], set()
        for score, i, r in scored:
            if len(deep) >= pick_max:
                break
            if i in used:
                continue
            used.add(i)
            c = candidates[i]
            deep_item = {
                "id": "deep-" + hashlib.sha1(
                    c["url"].encode("utf-8"),
                    usedforsecurity=False,
                ).hexdigest()[:8],
                "title": c["title"],
                "title_zh": str(r.get("title_zh") or c["title"])[:40],
                "url": c["url"],
                "source": c["source"],
                "channel": c.get("channel", "ai_engineering"),
                "lang": c["lang"],
                "brief": str(r.get("brief", ""))[:60],
                "why": str(r.get("why", ""))[:90],
                "key_points": [str(x).strip()[:80] for x in (r.get("key_points") or [])
                               if str(x).strip()][:3],
                "audience": str(r.get("audience", "")).strip()[:70],
                "takeaway": str(r.get("takeaway", "")).strip()[:100],
                "score": int(score),
                "read_minutes": estimate_read_minutes(c, c["lang"]),
            }
            content_type = normalize_deep_content_type(r.get("content_type"))
            if content_type:
                deep_item["content_type"] = content_type
            deep.append(deep_item)

        for d in deep:
            seen["urls"][d["url"]] = date_str
        prune = int(dcfg.get("seen_keep_days", 60))
        today = datetime.strptime(date_str, "%Y-%m-%d")

        def _keep(dt):
            try:
                return (today - datetime.strptime(dt, "%Y-%m-%d")).days <= prune
            except ValueError:
                return False

        seen["urls"] = {u: dt for u, dt in seen["urls"].items() if _keep(dt)}
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "deep_seen.json").write_text(
            json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")
        try:
            update_deep_health(data_dir, date_str, deep_sources, fetch_stats,
                               candidates, score_stats, deep)
        except Exception as e:
            log(f"  深读健康统计写入失败: {e}")
        log(f"  深读推荐：{len(deep)} 篇（阈值 {threshold} 分）")
        return deep
    except Exception as e:
        log(f"  深读频道失败（不影响主管线）: {e}")
        return []


# ----------------------------------------------------------------
# 5.1 今日论文频道（Hugging Face Daily Papers）
#   独立于新闻管线：抓 HF 每日社区精选论文，LLM 按读者学习坐标挑 3-4 篇，
#   产出"该读什么/该补什么概念"。论文不是新闻——不进精选评分、自成一块。
#   与深读频道同为独立故障域：任何异常只 log 并返回 []。
# ----------------------------------------------------------------

HF_PAPERS_API = "https://huggingface.co/api/daily_papers"

PAPERS_SYSTEM = """你为一位**前端/全栈开发者**从每天的 arXiv 热门论文里挑"值得他花时间读的"。
读者不是研究员，学习坐标是：前端/全栈工程、AI 工具应用、数据与自动化管线、计算机基础。
他要的是：该补什么概念、能不能用得上、有没有可跑的代码/工具，而非纯理论推导。
输入若干候选论文（标题+摘要+点赞数+是否带开源代码），可能附带读者兴趣画像。
给每篇打"该读价值分"0-10，标准：
- 可落地：方法/工具能迁移到工程或学习实践，带开源代码/项目页的加分
- 认知增量：讲清一个值得掌握的概念、框架或反直觉结论，能转成学习路线
- 贴合坐标：越靠近读者学习方向越高；纯数学/理论且离工程很远的压低
社区点赞高只是线索、不是理由，平庸或过于窄众的仍给低分。宁缺毋滥。
对每篇输出：
{"idx": 编号, "score": 0-10, "title_zh": "中文标题（≤30字）",
 "brief": "一句话这篇做了什么（≤40字）",
 "why": "为什么值得读：该补什么概念/能不能用上（≤60字）",
 "contribution": "核心贡献（≤80字）", "evidence": "主要证据或实验（≤80字）",
 "limitations": "适用边界或局限（≤80字）", "takeaway": "对个人学习最有用的结论（≤80字）"}
只输出 JSON 对象：{"picks":[论文...]}。只有一篇也必须放在 picks 数组里。不要其他文字。"""


def fetch_hf_papers(date_str, days=2):
    """抓 HF Daily Papers（社区精选 + 点赞）。合并 date_str 及往前 days-1 天，
    按 arxiv id 去重，返回规范化候选 list。抓取失败该日跳过、不抛（独立故障域）。"""
    base = datetime.strptime(date_str, "%Y-%m-%d")
    merged = {}
    for d in range(max(1, days)):
        day = (base - timedelta(days=d)).strftime("%Y-%m-%d")
        try:
            resp = http_get(f"{HF_PAPERS_API}?date={day}", timeout=25)
            data = resp.json()
        except Exception as e:
            log(f"  HF Papers {day} 抓取失败: {e}")
            continue
        if not isinstance(data, list):
            continue
        for it in data:
            p = it.get("paper") or {}
            aid = p.get("id")
            if not aid or aid in merged:
                continue
            title = (it.get("title") or p.get("title") or "").strip()
            if not title:
                continue
            merged[aid] = {
                "title": title,
                "url": f"https://huggingface.co/papers/{aid}",
                "arxiv_id": aid,
                "summary": (p.get("ai_summary") or it.get("summary")
                            or p.get("summary") or "").strip(),
                "upvotes": int(p.get("upvotes") or 0),
                "comments": int(it.get("numComments") or 0),
                "has_code": bool(p.get("githubRepo")),
            }
    return list(merged.values())


def papers_channel(llm, cfg, date_str, profile_text=""):
    """今日论文频道编排。独立故障域：任何异常只 log 并返回 []，绝不影响主管线。"""
    try:
        pcfg = cfg.get("papers") or {}
        if not pcfg.get("enabled", False):
            return []
        candidates = fetch_hf_papers(date_str, days=int(pcfg.get("lookback_days", 2)))
        data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
        seen = load_deep_seen(data_dir, date_str, "papers_seen.json")
        candidates = [c for c in candidates if c["url"] not in seen["urls"]]
        # 点赞预排序 + 截断，控 token（候选本就是社区精选，40+ 篇取头部足够）
        candidates.sort(key=lambda c: (-c["upvotes"], -c["comments"]))
        candidates = candidates[:int(pcfg.get("max_candidates", 30))]
        log(f"  论文候选：{len(candidates)} 篇（去重 + 预排序后）")
        if not candidates:
            return []

        lines = []
        for i, c in enumerate(candidates):
            code = "，带开源代码" if c["has_code"] else ""
            lines.append(f"[{i}] (👍{c['upvotes']}{code}) {c['title']}\n    {c['summary'][:220]}")
        user = ""
        if profile_has_content(profile_text):
            user = "【兴趣画像】\n" + profile_text + "\n\n"
        user += "【候选论文】\n" + "\n".join(lines)
        rows = _model_rows(llm.json_call(PAPERS_SYSTEM, user), "picks")
        if rows is None:
            log("  论文返回结构非法，本次不推荐")
            rows = []

        scored = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            i = _model_index(r.get("idx"), len(candidates))
            score = _model_number(r.get("score"))
            if i is not None and score is not None:
                scored.append((max(0.0, min(10.0, score)), i, r))
        threshold = float(pcfg.get("pick_threshold", 7))
        pick_max = int(pcfg.get("pick_max", 4))
        scored = sorted([t for t in scored if t[0] >= threshold], key=lambda t: -t[0])

        papers, used = [], set()
        for score, i, r in scored:
            if len(papers) >= pick_max:
                break
            if i in used:
                continue
            used.add(i)
            c = candidates[i]
            papers.append({
                "id": "paper-" + c["arxiv_id"],
                "title": c["title"],
                "title_zh": str(r.get("title_zh") or c["title"])[:40],
                "url": c["url"],
                "arxiv_id": c["arxiv_id"],
                "brief": str(r.get("brief", ""))[:60],
                "why": str(r.get("why", ""))[:90],
                "contribution": str(r.get("contribution", "")).strip()[:100],
                "evidence": str(r.get("evidence", "")).strip()[:100],
                "limitations": str(r.get("limitations", "")).strip()[:100],
                "takeaway": str(r.get("takeaway", "")).strip()[:100],
                "score": int(score),
                "upvotes": c["upvotes"],
                "has_code": c["has_code"],
            })

        for p in papers:
            seen["urls"][p["url"]] = date_str
        prune = int(pcfg.get("seen_keep_days", 45))
        today = datetime.strptime(date_str, "%Y-%m-%d")

        def _keep(dt):
            try:
                return (today - datetime.strptime(dt, "%Y-%m-%d")).days <= prune
            except ValueError:
                return False

        seen["urls"] = {u: dt for u, dt in seen["urls"].items() if _keep(dt)}
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "papers_seen.json").write_text(
            json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"  今日论文：{len(papers)} 篇（阈值 {threshold} 分）")
        return papers
    except Exception as e:
        log(f"  今日论文频道失败（不影响主管线）: {e}")
        return []


# ----------------------------------------------------------------
# 5.2 舆论观察（微博/B站热榜 → 传播机制解读）+ co-occurrence 暗排序
#   热榜词条永不成为新闻条目：只作 LLM 输入与排序信号。
# ----------------------------------------------------------------

OPINION_SYSTEM = """你为一位关注"舆论机制"的读者做每日舆论观察。输入是今天微博/B站的热榜词条。
读者不想看热榜本身，想理解传播现象：一件事为什么热、映射什么群体情绪、什么平台机制在起作用。
从候选里挑 2-3 个真正值得说的（有公共意义/群体情绪/平台机制可讲的）：
- 纯明星八卦、综艺、剧集、体育赛果本身一律跳过，除非其传播方式本身反映平台机制
- 优先：社会公共事件、青年/教育/就业议题、科技产品争议、梗与亚文化破圈现象
对每个输出：
{"idx": 编号, "title": "话题的中性转述（≤24字）",
 "why_hot": "为什么热：事件是什么+传播动力（≤60字）",
 "emotion": "映射的群体情绪（≤40字）",
 "mechanism": "平台机制的作用（算法推流/话题运营/社群结构等，≤40字）"}
只输出 JSON 对象：{"picks":[话题...]}。只有一个也必须放在 picks 数组里。
拿不准的宁可少挑，一个都不值得说就输出 {"picks":[]}。不要其他文字。"""


def _cjk_norm(s):
    """匹配用归一化：只留中英数字，去掉标点/空白/emoji。"""
    return re.sub(r"[^0-9A-Za-z一-鿿]", "", s or "")


def _bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)}


def apply_pulse_bonus(events, items, pulse, cfg):
    """co-occurrence 暗排序：热榜词条与事件文本重合 -> 事件最终分乘公众热度 bonus。
    命中判据（宁松勿严，bonus 很温和）：热榜词的任意 4 字连片出现在事件文本里
    （实体名兜底，如"台风巴威"），或热榜词字符二元组被事件文本覆盖率 >= 0.5。
    每事件最多命中一次。返回命中数。"""
    bonus = float((cfg.get("opinion") or {}).get("cooccur_bonus", 1.08))
    if not pulse or bonus <= 1.0:
        return 0
    hits = 0
    for ev in events:
        text = _cjk_norm(ev.get("title", "") + " " + " ".join(
            items[i]["title"] for i in ev.get("ids", []) if 0 <= i < len(items)))
        tb = _bigrams(text)
        for p in pulse:
            wn = _cjk_norm(p["word"])
            if len(wn) < 2:
                continue
            wb = _bigrams(wn)
            if any(wn[i:i + 4] in text for i in range(max(len(wn) - 3, 0))) or \
               (wb and len(wb & tb) / len(wb) >= 0.5):
                ev["pulse_mult"] = bonus
                ev["pulse_word"] = p["word"]
                hits += 1
                break
    return hits


def opinion_pulse(llm, cfg, pulse, profile_text=""):
    """舆论观察编排。独立故障域：任何异常只 log 并返回 []，绝不影响主管线。"""
    try:
        ocfg = cfg.get("opinion") or {}
        if not ocfg.get("enabled", False) or not pulse:
            return []
        cand = pulse[:int(ocfg.get("max_candidates", 50))]
        lines = [f"[{i}] ({p['platform']}) {p['word']}" for i, p in enumerate(cand)]
        user = ""
        if profile_has_content(profile_text):
            user = "【读者兴趣画像】\n" + profile_text + "\n\n"
        user += "【今日热榜】\n" + "\n".join(lines)
        rows = _model_rows(llm.json_call(OPINION_SYSTEM, user), "picks")
        if rows is None:
            log("  舆论观察返回结构非法，本次留空")
            rows = []

        out, used = [], set()
        pick_max = int(ocfg.get("pick_max", 3))
        for r in rows:
            i = _model_index(r.get("idx"), len(cand)) if isinstance(r, dict) else None
            if i is None or i in used or len(out) >= pick_max:
                continue
            used.add(i)
            p = cand[i]
            out.append({
                "id": "op-" + hashlib.sha1(
                    (p["platform"] + p["word"]).encode("utf-8"),
                    usedforsecurity=False,
                ).hexdigest()[:8],
                "platform": p["platform"],
                "word": p["word"],
                "title": str(r.get("title") or p["word"])[:30],
                "why_hot": str(r.get("why_hot", ""))[:90],
                "emotion": str(r.get("emotion", ""))[:60],
                "mechanism": str(r.get("mechanism", ""))[:60],
                "url": p.get("url", ""),
            })
        log(f"  舆论观察：{len(out)} 条")
        return out
    except Exception as e:
        log(f"  舆论观察失败（不影响主管线）: {e}")
        return []


# ----------------------------------------------------------------
# 6. 输出
# ----------------------------------------------------------------

def event_to_item(ev, items, tier, *, full_objectivity=False, source_limit=5,
                  trajectory_enabled=True):
    ids = ev["ids"]
    # 主链接：可信度最高的事实源优先
    if (not isinstance(source_limit, int) or isinstance(source_limit, bool)
            or source_limit < 1):
        raise ValueError("source_limit must be a positive integer")
    sorted_ids = _serialized_source_ids(ev, items, limit=source_limit)
    primary = items[sorted_ids[0]]
    ev["title"] = select_reader_title(ev.get("title"), primary["title"])
    if "summary" not in ev:
        fallback = readable_fallback_summary(primary["desc"])
        if fallback:
            ev["summary"] = fallback
    if full_objectivity:
        sanitize_objectivity_event(ev, items)
    public_watch = (
        _valid_trajectory_watch(ev.get("watch"))
        if trajectory_enabled else None
    )
    public_watch_detail = (
        _valid_trajectory_watch(ev.get("watch_detail"), detail=True)
        if public_watch is not None else None
    )
    sources = []
    seen_urls = set()
    for i in sorted_ids:
        it = items[i]
        if it["url"] in seen_urls:
            continue
        seen_urls.add(it["url"])
        source = {"name": it["source"], "url": it["url"],
                  "type": TYPE_NAMES[it["source_type"]]}
        if full_objectivity:
            source["evidence_basis"] = (
                it.get("evidence_basis") if it.get("evidence_basis") in ("fulltext", "snippet")
                else "snippet")
            chain = _trusted_evidence_chain(it)
            if chain:
                source["evidence_chain"] = chain
        sources.append(source)
    item = {
        "id": public_item_id(ev, tier),
        "tier": tier,
        "category": ev["category"],
        "title": ev.get("title", primary["title"]),
        **({"summary": ev["summary"]} if ev.get("summary") else {}),
        "status": ev.get("status", ""),
        "tags": ev.get("tags", []),
        **({"watch": public_watch} if public_watch is not None else {}),
        **({"watch_detail": public_watch_detail}
           if public_watch_detail is not None else {}),
        **({"context": ev["context"]}
           if trajectory_enabled and ev.get("context") else {}),
        **({"detail": ev["detail"]} if ev.get("detail") else {}),
        **({"claims": ev["claims"]} if ev.get("claims") else {}),
        "score": ev["score"],
        "src_tier": ev.get("tier", ""),
        "source_type": TYPE_NAMES[primary["source_type"]],
        "time": primary["time"],
        "sources": sources,
    }
    if full_objectivity:
        evidence = ev.get("evidence") if isinstance(ev.get("evidence"), dict) else {}
        item["evidence"] = {
            "basis": evidence.get("basis", "snippet"),
            "publisher_count": int(evidence.get("publisher_count", 0)),
            "independent_chain_count": int(evidence.get("independent_chain_count", 0)),
            "degraded": bool(evidence.get("degraded", False)),
        }
    update_sources = [items[i] for i in ids if items[i].get("is_update")]
    if update_sources:
        item["is_update"] = True
        first_dates = [it.get("first_seen") for it in update_sources if it.get("first_seen")]
        if first_dates:
            item["first_seen"] = min(first_dates)
    # 精选恒带 event_id（前端"继续追踪"按钮需要）；
    # 跨天延续字段（第 2 天起）才带 day_count/history，文件保持干净
    if ev.get("event_id"):
        item["event_id"] = ev["event_id"]
    if (trajectory_enabled and ev.get("trusted_continuation") is True
            and ev.get("day_count", 0) >= 2 and ev.get("history_prev")):
        item["trusted_continuation"] = True
        item["day_count"] = ev["day_count"]
        item["history"] = [{
            "date": h.get("date", ""),
            "summary": h.get("summary", ""),
            **({"item_ref": h["item_ref"]} if h.get("item_ref") else {}),
        } for h in reversed(ev.get("history_prev", []))]
    return item


def build_tracking(registry, picked, date_str):
    """「追踪中」区数据：钉选且活跃、今天没进精选的事件。"""
    if not registry:
        return []
    picked_ids = {ev.get("event_id") for ev in picked if ev.get("event_id")}
    tracking = []
    for e in registry.get("events", []):
        if e.get("status") != "active" or not e.get("pinned"):
            continue
        if e.get("event_id") in picked_ids:
            continue
        hist = e.get("history", [])
        tracking.append({
            "event_id": e.get("event_id", ""),
            "title": e.get("title", ""),
            "category": e.get("category", ""),
            "day_count": len({h.get("date") for h in hist}),
            "last_seen": e.get("last_seen", ""),
            "updated_today": e.get("last_seen") == date_str,
            "history": [{"date": h.get("date", ""), "summary": h.get("summary", "")}
                        for h in reversed(hist[-7:])],
        })
    return tracking


# ----------------------------------------------------------------
# 6.1.5 英语单词本：从精选英文原文挑高价值词 + 补全手动加的裸词
#   功能自 2026-07-10 停用（config.yaml 的 vocab.enabled: false），build_vocab
#   直接 return，本节代码不再运行。写端点 api/vocab.js 已于 2026-08-16 删除，
#   见 docs/adr/0018-delete-dead-vocab-write-endpoint.md；恢复时需从 git 历史
#   一并找回接口、前端界面和接口里的 vocab-book.json 损坏校验。
#   原数据流：用户在页面收藏/加词 -> api/vocab.js 写回 vocab-book.json；
#   管线次日读它做全量去重、并把 pending 裸词补全成完整卡。
#   每日候选写 data/vocab/<date>.js（前端按日懒加载，无需 manifest）。
# ----------------------------------------------------------------

VOCAB_BOOK_FILE = "vocab-book.json"

VOCAB_SYSTEM = """你是英语词汇教练，为中文母语的英语学习者从今日英文新闻里挑"高价值单词"。
用户给你若干条今日精选新闻的英文标题与英文摘要（附中文事件标题和条目编号 [k]）。
请挑出 {n_min}-{n_max} 个最值得积累的高价值单词/短语，标准：
- 兼收两类：①通用进阶词汇（CEFR B2-C1，可迁移到写作/考试，如 scrutiny、resilience、unprecedented）
  ②时事高频术语（如 sanctions、tariff、ceasefire、inflation）
- 按"对中文母语学习者的学习价值"综合权衡，宁缺毋滥
排除：专有名词、地名、人名、机构名、太基础的词（四级以下）、以及只在该新闻里出现、迁移价值低的生僻词。
用户会给出【已收录、请跳过】的词元清单，清单里的词一律不要再挑。
对每个词输出一张精炼卡：
- word: 原词的词元 lemma（动词还原原形、名词还原单数、去掉时态/复数）
- phonetic: 音标（带斜杠，如 /ˈskruːtɪni/）
- pos: 词性缩写（n. / v. / adj. / adv. / phrase 等）
- sense_zh: 该新闻语境下的中文释义（≤20字，只给这个语境的义项）
- example_en: 一句包含该词的英文例句，优先直接取自给定的新闻标题/摘要原文
- item_id: 该词来自哪条新闻的编号（就是用户给的 [k] 里的 k，整数）
只输出 JSON 数组，每个元素：
{{"word":"...","phonetic":"...","pos":"...","sense_zh":"...","example_en":"...","item_id":k}}
不要输出任何其他文字。"""

VOCAB_ENRICH_SYSTEM = """你是英语词汇教练。用户给你若干英文单词/短语（可能带一句来源语境）。
为每个词生成精炼卡，供中文母语学习者积累：
- word: 词元原形
- phonetic: 音标（带斜杠）
- pos: 词性缩写（n. / v. / adj. / adv. / phrase 等）
- sense_zh: 最常用的中文释义（≤20字；若给了语境则取该语境义）
- example_en: 一句自然的英文例句（若给了来源语境句可直接采用）
按输入顺序输出 JSON 数组，每个元素：
{"word":"...","phonetic":"...","pos":"...","sense_zh":"...","example_en":"..."}
不要输出其他文字。"""


def normalize_word(w):
    """词元归一：小写、只留字母（run/Running/ran 各自的表面形按输入，去噪即可）。"""
    return re.sub(r"[^a-z]", "", str(w or "").strip().lower())


def load_vocab_book(data_dir):
    """读 vocab-book.json；缺失/损坏一律返回空册（结构补齐）。"""
    f = data_dir / VOCAB_BOOK_FILE
    if not f.exists():
        return {"version": 1, "words": [], "pending": []}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not a dict")
        data.setdefault("version", 1)
        if not isinstance(data.get("words"), list):
            data["words"] = []
        if not isinstance(data.get("pending"), list):
            data["pending"] = []
        return data
    except Exception as e:
        log(f"  {VOCAB_BOOK_FILE} 读取失败，重建空册: {e}")
        return {"version": 1, "words": [], "pending": []}


def collect_seen_lemmas(data_dir, book, skip_date=None):
    """已出现过的词元集合：单词本 words+pending ∪ 历史 vocab/<date>.js。
    skip_date 对应的当日文件不计入——同日重跑时才能重新生成、而非把自己去空。"""
    seen = set()
    for w in book.get("words", []):
        seen.add(w.get("lemma") or normalize_word(w.get("word")))
    for p in book.get("pending", []):
        seen.add(p.get("lemma") or normalize_word(p.get("word")))
    vdir = data_dir / "vocab"
    if vdir.exists():
        for p in sorted(vdir.glob("*.js")):
            if skip_date and p.stem == skip_date:
                continue
            try:
                src = p.read_text(encoding="utf-8")
                m = re.search(r"window\.VOCAB_DATA\[[^\]]+\] = (\{.*\});", src, re.S)
                if not m:
                    continue
                payload = json.loads(m.group(1))
                for w in payload.get("words", []):
                    seen.add(w.get("lemma") or normalize_word(w.get("word")))
            except Exception:
                continue
    seen.discard("")
    return seen


def extract_vocab(llm, picked, items, seen_lemmas, cfg):
    """从精选事件的英文标题+摘要挑高价值词，返回精炼卡列表（已按 seen_lemmas 去重）。"""
    vcfg = cfg.get("vocab") or {}
    n_min = int(vcfg.get("daily_min", 6))
    n_max = int(vcfg.get("daily_max", 10))
    if not picked:
        return []
    blocks = []
    idx_to_meta = {}
    for k, ev in enumerate(picked):
        ids = ev.get("ids") or []
        if not ids:
            continue
        # 主源排序与 event_to_item 一致：事实源优先、可信度高优先
        sorted_ids = sorted(ids, key=lambda i: (
            items[i]["source_type"] != "fact", -items[i]["credibility"]))
        en_parts = []
        for i in sorted_ids[:2]:
            it = items[i]
            en_parts.append(f"{it['title']}. {it.get('desc', '')[:300]}")
        en_text = " ".join(en_parts).strip()
        if not en_text:
            continue
        idx_to_meta[k] = {"item_id": f"pick-{ids[0]}", "item_title": ev.get("title", ""),
                          "category": ev.get("category", "")}
        blocks.append(f"[{k}]（{ev.get('title', '')}）\n{en_text}")
    if not blocks:
        return []
    skip_hint = ""
    if seen_lemmas:
        skip_hint = "\n\n【已收录、请跳过这些词元】\n" + ", ".join(sorted(seen_lemmas)[:200])
    system = VOCAB_SYSTEM.format(n_min=n_min, n_max=n_max)
    try:
        result = llm.json_call(system, "\n\n".join(blocks) + skip_hint)
    except Exception as e:
        log(f"  单词本挑词失败，今日跳过: {e}")
        return []
    cards = []
    used = set()
    for r in (result if isinstance(result, list) else []):
        word = str(r.get("word", "")).strip()
        lemma = normalize_word(word)
        if not lemma or lemma in seen_lemmas or lemma in used:
            continue
        k = r.get("item_id")
        meta = idx_to_meta.get(k) if isinstance(k, int) and not isinstance(k, bool) else None
        if meta is None:   # LLM 漏填或填错编号：退化到第一条精选，避免丢词
            meta = next(iter(idx_to_meta.values()),
                        {"item_id": "", "item_title": "", "category": ""})
        used.add(lemma)
        cards.append({
            "word": word,
            "lemma": lemma,
            "phonetic": str(r.get("phonetic", "")).strip(),
            "pos": str(r.get("pos", "")).strip(),
            "sense_zh": str(r.get("sense_zh", "")).strip()[:40],
            "example_en": str(r.get("example_en", "")).strip()[:400],
            "item_id": meta["item_id"],
            "item_title": meta["item_title"],
            "category": meta["category"],
        })
        if len(cards) >= n_max:
            break
    return cards


def enrich_pending(llm, book):
    """把 vocab-book.json 的 pending 裸词补全成完整卡并移入 words。返回补全条数；
    LLM 失败则原样保留 pending 下次再试。"""
    pending = book.get("pending") or []
    if not pending:
        return 0
    existing = {w.get("lemma") or normalize_word(w.get("word"))
                for w in book.get("words", [])}
    lines, valid = [], []
    for p in pending:
        word = str(p.get("word", "")).strip()
        if not word:
            continue
        ctx = str(p.get("context", "")).strip()
        lines.append(f"[{len(valid)}] {word}" + (f"  语境: {ctx}" if ctx else ""))
        valid.append(p)
    if not valid:
        book["pending"] = []
        return 0
    try:
        result = llm.json_call(VOCAB_ENRICH_SYSTEM, "\n".join(lines))
    except Exception as e:
        log(f"  手动词补全失败，保留 pending 下次再试: {e}")
        return 0
    result = result if isinstance(result, list) else []
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for i, p in enumerate(valid):
        r = result[i] if i < len(result) else {}
        word = str(r.get("word") or p.get("word") or "").strip()
        lemma = normalize_word(word)
        if not lemma or lemma in existing:
            continue
        existing.add(lemma)
        book.setdefault("words", []).append({
            "word": word,
            "lemma": lemma,
            "phonetic": str(r.get("phonetic", "")).strip(),
            "pos": str(r.get("pos", "")).strip(),
            "sense_zh": str(r.get("sense_zh", "")).strip()[:40],
            "example_en": str(r.get("example_en", "")).strip()[:400],
            "item_id": p.get("item_id", ""),
            "item_title": p.get("item_title", ""),
            "date": p.get("date", ""),
            "source": "manual",
            "collected_ts": now,
            "mastered": False,
        })
        n += 1
    book["pending"] = []   # 处理过的都清空：成功的入册，无效/重复的丢弃
    return n


def write_vocab(date_str, cards, data_dir):
    vdir = data_dir / "vocab"
    vdir.mkdir(parents=True, exist_ok=True)
    payload = {"date": date_str,
               "generated_at": datetime.now(timezone.utc).isoformat(),
               "words": cards}
    js = ("window.VOCAB_DATA = window.VOCAB_DATA || {};\n"
          f"window.VOCAB_DATA[{json.dumps(date_str)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    (vdir / f"{date_str}.js").write_text(js, encoding="utf-8")


def build_vocab(llm, picked, items, date_str, cfg):
    """单词本编排：补全手动裸词 -> 全量去重 -> 挑今日候选 -> 落盘。"""
    vcfg = cfg.get("vocab") or {}
    if not vcfg.get("enabled", True):
        return
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    book = load_vocab_book(data_dir)
    had_pending = bool(book.get("pending"))
    n_enriched = enrich_pending(llm, book)          # 先补全，纳入去重集
    seen = collect_seen_lemmas(data_dir, book, skip_date=date_str)
    cards = extract_vocab(llm, picked, items, seen, cfg)
    if cards:                                        # 空结果不落盘，避免覆盖前次好数据 / 产出空文件
        write_vocab(date_str, cards, data_dir)
    if had_pending or not (data_dir / VOCAB_BOOK_FILE).exists():
        (data_dir / VOCAB_BOOK_FILE).write_text(
            json.dumps(book, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"  英语单词本：新挑 {len(cards)} 词，补全手动词 {n_enriched} 个")


def write_all_archive(items, sources, date_str, keep_days=90, min_score=40):
    """全部动态轻档：窗口内全量抓取条目的轻字段落盘 data/all/<date>.js。
    不经 LLM、零 token；供前端「全部动态」板块按天懒加载，也是筛选器的
    可核查底账。滚动保留 keep_days 天防仓库膨胀（git 历史仍会增长，接受）。
    类别取来源配置的 category（条目级类别在此阶段尚不存在）；min_score 是
    前端默认展示阈值，评分由 backfill_all_scores 在评分阶段后回填。"""
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    adir = data_dir / "all"
    adir.mkdir(parents=True, exist_ok=True)
    cat_by_src = {s["id"]: s.get("category", "") for s in sources}
    rows = [{
        "t": it["title"],
        "u": it["url"],
        "s": it["source"],
        "c": cat_by_src.get(it["source_id"].split(":")[0], ""),
        "time": it["time"],
    } for it in items]
    rows.sort(key=lambda r: r["time"], reverse=True)
    payload = {"date": date_str, "min_score": min_score, "items": rows}
    js = ("window.NEWS_ALL = window.NEWS_ALL || {};\n"
          f"window.NEWS_ALL[{json.dumps(date_str)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    (adir / f"{date_str}.js").write_text(js, encoding="utf-8")
    # 滚动剪枝（ISO 日期字符串可直接比大小）+ manifest 倒序
    cutoff = (datetime.strptime(date_str, "%Y-%m-%d")
              - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    for p in adir.glob("*.js"):
        if p.stem != "manifest" and p.stem < cutoff:
            p.unlink()
    dates = sorted([p.stem for p in adir.glob("*.js") if p.stem != "manifest"],
                   reverse=True)
    (adir / "manifest.js").write_text(
        f"window.ALL_MANIFEST = {json.dumps(dates, ensure_ascii=False)};\n",
        encoding="utf-8")
    log(f"已写入 data/all/{date_str}.js（全量 {len(rows)} 条 · 保留 {keep_days} 天）")


def backfill_all_scores(events, items, date_str):
    """评分回填全量档：按 URL（去 query，与 fetch_all 去重同口径）把事件分
    写到当日 all 档匹配条目的 score 字段。被预筛砍掉的条目不参与评分、无分，
    前端默认隐藏、可切换显示。独立故障域，档缺失/格式异常只记日志。"""
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    f = data_dir / "all" / f"{date_str}.js"
    if not f.exists():
        return
    m = re.search(r"window\.NEWS_ALL\[[^\]]+\] = (\{.*\});",
                  f.read_text(encoding="utf-8"), re.S)
    if not m:
        log("  全量档格式异常，跳过评分回填")
        return
    payload = json.loads(m.group(1))
    url_score = {}
    for ev in events:
        sc = _model_number(ev.get("score"))
        if sc is None:
            continue
        for i in ev.get("ids", []):
            if type(i) is not int or not 0 <= i < len(items):
                continue
            item = items[i]
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").split("?")[0]
            if url:
                url_score[url] = round(sc)
    n = 0
    for r in payload.get("items", []):
        sc = url_score.get((r.get("u") or "").split("?")[0])
        if sc is not None:
            r["score"] = sc
            n += 1
    js = ("window.NEWS_ALL = window.NEWS_ALL || {};\n"
          f"window.NEWS_ALL[{json.dumps(date_str)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    f.write_text(js, encoding="utf-8")
    log(f"  全量档评分回填：{n}/{len(payload.get('items') or [])} 条带分")


def validate_daily_payload(payload):
    """Return structural/reference errors that must block publication."""
    errors = []
    quality = payload.get("quality")
    if not isinstance(quality, dict):
        errors.append("quality must be an object")
    else:
        for field in ("audited_events", "split_events", "removed_fields"):
            value = quality.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"quality.{field} must be a non-negative integer")
        value = quality.get("enrichment_audited_events")
        if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0):
            errors.append(
                "quality.enrichment_audited_events must be a non-negative integer")
        # 分项与总数对不上说明埋点漏了或重复计数，诊断数据不可用——阻断发布比事后
        # 发现一周的分项是错的便宜。缺失仍然合法：本次之前的日报没有这两个键。
        version = quality.get("removed_field_counts_version")
        if (version is not None
                and (type(version) is not int or version not in {2, 3})):
            errors.append(
                "quality.removed_field_counts_version must be 2 or 3 when present")
        if version == REMOVED_FIELD_COUNTS_VERSION:
            count_fields = QUALITY_EXTENSION_FIELDS
            reason_fields = REMOVAL_REASONS
        elif version == 2:
            count_fields = QUALITY_EXTENSION_FIELDS_V2
            reason_fields = REMOVAL_REASONS
        else:
            count_fields = QUALITY_EXTENSION_FIELDS_V1
            reason_fields = REMOVAL_REASONS_V1
        for field, allowed in (("removed_field_counts", count_fields),
                               ("removed_field_reasons", reason_fields)):
            counts = quality.get(field)
            if counts is None:
                continue
            if not isinstance(counts, dict) or set(counts) != set(allowed) or any(
                    not isinstance(value, int) or isinstance(value, bool) or value < 0
                    for value in counts.values()):
                errors.append(
                    f"quality.{field} must map {'/'.join(allowed)} to non-negative integers")
            elif sum(counts.values()) != quality.get("removed_fields"):
                errors.append(
                    f"quality.{field} must sum to quality.removed_fields")
        for field in (
                "duplicate_audited_events", "same_day_duplicates_merged",
                "duplicate_audit_failures", "same_day_candidate_pairs",
                "same_day_bridge_batches", "same_day_reconcile_calls",
                "same_day_deferred_batches"):
            value = quality.get(field)
            if value is not None and (
                    not isinstance(value, int) or isinstance(value, bool) or value < 0):
                errors.append(f"quality.{field} must be a non-negative integer")
        exhausted = quality.get("same_day_budget_exhausted")
        if exhausted is not None and not isinstance(exhausted, bool):
            errors.append("quality.same_day_budget_exhausted must be a boolean")
        for field in ("cross_day_duplicates", "material_updates", "update_judge_failures",
                      "triage_invalid_rows", "triage_fallback_batches",
                      "model_unusable_responses"):
            value = quality.get(field)
            if value is not None and (not isinstance(value, int)
                                      or isinstance(value, bool) or value < 0):
                errors.append(f"quality.{field} must be a non-negative integer")
        for field in ("objectivity_audited", "objectivity_repaired",
                      "objectivity_degraded", "high_risk_demoted"):
            value = quality.get(field)
            if value is not None and (not isinstance(value, int)
                                      or isinstance(value, bool) or value < 0):
                errors.append(f"quality.{field} must be a non-negative integer")
        if not isinstance(quality.get("degraded"), bool):
            errors.append("quality.degraded must be boolean")

    rows = payload.get("items")
    if not isinstance(rows, list):
        return errors + ["items must be an array"]
    item_ids = [row.get("id") for row in rows if isinstance(row, dict)]
    valid_ids = {item_id for item_id in item_ids if isinstance(item_id, str) and item_id}
    if len(item_ids) != len(rows) or len(valid_ids) != len(rows):
        errors.append("item ids must be present and unique")
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = row.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"item {row.get('id')} title must be non-empty")
        elif len(title) > SOURCE_TITLE_MAX_CHARS:
            errors.append(
                f"item {row.get('id')} title exceeds {SOURCE_TITLE_MAX_CHARS} characters")
        watch_detail = row.get("watch_detail")
        if watch_detail is not None:
            watch = row.get("watch")
            if (not isinstance(watch_detail, str) or not watch_detail.strip()
                    or len(watch_detail) > FULLTEXT_OBJECTIVITY_FIELD_LIMITS["watch_detail"]):
                errors.append(
                    f"item {row.get('id')} watch_detail must be non-empty and at most "
                    f"{FULLTEXT_OBJECTIVITY_FIELD_LIMITS['watch_detail']} characters")
            if (not isinstance(watch, str) or not watch.strip()
                    or len(watch) > OBJECTIVITY_FIELD_LIMITS["watch"]):
                errors.append(
                    f"item {row.get('id')} watch_detail requires a valid short watch")
        source_names = {source.get("name") for source in (row.get("sources") or [])
                        if isinstance(source, dict) and source.get("name")}
        # 前端 safeUrl 只放行 http(s)，但 feed.xml 的 <item><link> 是原样输出的。
        # 在发布闸门上 fail-closed，比让每个消费端各自兜底可靠。
        for source in (row.get("sources") or []):
            if not isinstance(source, dict):
                continue
            url = source.get("url")
            if url is not None and not _is_valid_http_url(url):
                errors.append(
                    f"item {row.get('id')} source URL must be http(s): {source.get('name')}")
        evidence = row.get("evidence")
        if evidence is not None:
            sources = row.get("sources")
            if not isinstance(sources, list) or not sources:
                errors.append(f"item {row.get('id')} evidence requires sources")
            if not isinstance(evidence, dict):
                errors.append(f"item {row.get('id')} evidence must be an object")
            else:
                basis = evidence.get("basis")
                publisher_count = evidence.get("publisher_count")
                chain_count = evidence.get("independent_chain_count")
                if basis not in {"fulltext", "mixed", "snippet"}:
                    errors.append(f"item {row.get('id')} evidence basis is invalid")
                for name, value in (("publisher_count", publisher_count),
                                    ("independent_chain_count", chain_count)):
                    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                        errors.append(f"item {row.get('id')} evidence {name} is invalid")
                if (isinstance(publisher_count, int) and not isinstance(publisher_count, bool)
                        and isinstance(chain_count, int) and not isinstance(chain_count, bool)
                        and chain_count > publisher_count):
                    errors.append(
                        f"item {row.get('id')} evidence independent_chain_count "
                        "cannot exceed publisher_count")
                if not isinstance(evidence.get("degraded"), bool):
                    errors.append(f"item {row.get('id')} evidence degraded must be boolean")
                source_mapping_valid = isinstance(sources, list) and bool(sources) and all(
                    isinstance(source, dict)
                    and isinstance(source.get("name"), str)
                    and source["name"].strip()
                    and isinstance(source.get("url"), str)
                    and source["url"].strip()
                    and source.get("evidence_basis") in {"fulltext", "snippet"}
                    and ("evidence_chain" not in source
                         or (isinstance(source.get("evidence_chain"), str)
                             and bool(source["evidence_chain"].strip())))
                    for source in (sources or []))
                if not source_mapping_valid:
                    errors.append(f"item {row.get('id')} evidence source mapping is invalid")
                else:
                    source_urls = [str(source["url"]).strip() for source in sources]
                    publisher_keys = [
                        str(source["name"]).strip().casefold() for source in sources]
                    if (len(source_urls) != len(set(source_urls))
                            or len(publisher_keys) != len(set(publisher_keys))):
                        errors.append(f"item {row.get('id')} evidence sources are not unique")
                    derived_publishers = set(publisher_keys)
                    if (isinstance(publisher_count, int)
                            and not isinstance(publisher_count, bool)
                            and publisher_count != len(derived_publishers)):
                        errors.append(
                            f"item {row.get('id')} evidence publisher mapping is invalid")
                    bases = [source["evidence_basis"] for source in sources]
                    derived_basis = (
                        "fulltext" if all(value == "fulltext" for value in bases)
                        else "mixed" if any(value == "fulltext" for value in bases)
                        else "snippet")
                    if basis in {"fulltext", "mixed", "snippet"} and basis != derived_basis:
                        errors.append(f"item {row.get('id')} evidence basis mapping is invalid")
                    derived_chains = {
                        str(source.get("evidence_chain") or "").strip().casefold()
                        for source in sources if source.get("evidence_chain")}
                    if (isinstance(chain_count, int) and not isinstance(chain_count, bool)
                            and chain_count != len(derived_chains)):
                        errors.append(f"item {row.get('id')} evidence chain mapping is invalid")
        claims = row.get("claims") or []
        if not isinstance(claims, list):
            errors.append(f"item {row.get('id')} claims must be an array")
            continue
        for claim in claims:
            refs = claim.get("sources") if isinstance(claim, dict) else None
            if (not isinstance(refs, list) or not refs
                    or any(ref not in source_names for ref in refs)):
                errors.append(f"item {row.get('id')} claim has unknown source reference")
    for theme in payload.get("themes") or []:
        refs = theme.get("member_ids") if isinstance(theme, dict) else None
        if not isinstance(refs, list) or any(ref not in valid_ids for ref in refs):
            errors.append("theme has unknown item reference")
    for row in payload.get("deep") or []:
        if not isinstance(row, dict):
            continue
        if not _is_valid_http_url(row.get("url")):
            errors.append(f"deep {row.get('id')} URL must be http(s)")
    return errors


def _daily_pick_count(data_dir, date_str):
    path = Path(data_dir) / "daily" / f"{date_str}.js"
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        match = re.search(
            r"window\.NEWS_DATA\[[^\]]+\] = (\{.*\});\s*$", raw, re.S)
        payload = json.loads(match.group(1)) if match else {}
        value = (payload.get("stats") or {}).get("pick_count")
    except (OSError, ValueError):
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


def update_quality_health(data_dir, date_str, quality, keep_days=90,
                          include_rollout=True, usage=None, novelty_stats=None):
    """Upsert a rolling, non-daily-file quality health record.

    ``usage`` carries the run's token bill. It is merged here rather than into
    ``quality`` on purpose: the daily file is reader-facing public data and has
    no business carrying operational cost fields.
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "quality-health.json"
    try:
        current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        current = {}
    records = [row for row in (current.get("records") or [])
               if isinstance(row, dict) and row.get("date") != date_str]
    for row in records:
        if "enrichment_audited_events" in row:
            continue
        pick_count = _daily_pick_count(data_dir, row.get("date"))
        if pick_count is not None:
            row["enrichment_audited_events"] = pick_count
    safe_usage = {
        key: usage[key] for key in LLM_USAGE_FIELDS
        if key in (usage or {})
    }
    safe_novelty = {
        key: novelty_stats[key] for key in CROSS_SOURCE_NOVELTY_FIELDS
        if key in (novelty_stats or {})
    }
    records.append({"date": date_str,
                    **_quality_for_output(quality, include_rollout),
                    **safe_novelty,
                    **safe_usage})
    records.sort(key=lambda row: row.get("date", ""))
    records = records[-max(1, int(keep_days)):]
    audited = sum(int(row.get("audited_events", 0)) for row in records)
    split = sum(int(row.get("split_events", 0)) for row in records)
    payload = {
        "version": 1,
        "records": records,
        "summary": {
            "days": len(records),
            "audited_events": audited,
            "split_events": split,
            "split_rate": round(split / audited, 4) if audited else 0.0,
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def validate_daily_output_file(path, date_str):
    path = Path(path)
    if not path.exists():
        return ["daily output file missing"]
    raw = path.read_text(encoding="utf-8")
    match = re.search(r"window\.NEWS_DATA\[[^\]]+\] = (\{.*\});\s*$", raw, re.S)
    if not match:
        return ["daily output wrapper invalid"]
    try:
        payload = json.loads(match.group(1))
    except ValueError:
        return ["daily output JSON invalid"]
    errors = validate_daily_payload(payload)
    if payload.get("date") != date_str:
        errors.append("daily output date mismatch")
    return errors


def prepare_events_for_output(picked, secondary, items, cfg):
    """Apply final public sanitization before registry and payload snapshots."""
    for event in [*(picked or []), *(secondary or [])]:
        event.pop("why", None)
        source_ids = _serialized_source_ids(event, items, limit=1)
        source_title = items[source_ids[0]].get("title", "") if source_ids else ""
        event["title"] = select_reader_title(event.get("title"), source_title)
        if _rollout_output_enabled(cfg):
            apply_evidence_contract(event, items)
            sanitize_objectivity_event(event, items)


def _build_daily_payload(date_str, brief, picked, secondary, items, cfg,
                         registry=None, deep=None, themes=None, papers=None,
                         opinion=None, quality=None):
    rollout_output = _rollout_output_enabled(cfg)
    trajectory_output = _trajectory_enabled(cfg)
    source_limit = 4 if rollout_output else 5
    prepare_events_for_output(picked, secondary, items, cfg)
    out_items = ([event_to_item(
                    e, items, "pick", full_objectivity=rollout_output,
                    source_limit=source_limit,
                    trajectory_enabled=trajectory_output) for e in picked] +
                 [event_to_item(
                    e, items, "more", full_objectivity=rollout_output,
                    source_limit=source_limit,
                    trajectory_enabled=trajectory_output) for e in secondary])
    if not rollout_output:
        _strip_rollout_item_fields(out_items)
    payload = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brief": brief,
        "stats": {
            "sources_count": len(set(i["source_id"] for i in items)),
            "raw_count": len(items),
            "pick_count": len(picked),
            "more_count": len(secondary),
        },
        "quality": _quality_for_output(quality, rollout_output),
        "trajectory_enabled": trajectory_output,
        "items": out_items,
    }
    if themes:
        payload["themes"] = themes
    tracking = build_tracking(registry, picked, date_str)
    if tracking:
        payload["tracking"] = tracking
    if deep:
        payload["deep"] = deep
    if papers:
        payload["papers"] = papers
    if opinion:
        payload["opinion"] = opinion
    errors = validate_daily_payload(payload)
    if errors:
        raise ValueError("daily payload validation failed: " + "; ".join(errors))
    return payload


def _render_daily_output(date_str, payload):
    return ("window.NEWS_DATA = window.NEWS_DATA || {};\n"
            f"window.NEWS_DATA[{json.dumps(date_str)}] = "
            f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")


def _render_manifest(daily_dir, date_str):
    dates = {p.stem for p in daily_dir.glob("*.js")}
    dates.add(date_str)
    return (f"window.NEWS_MANIFEST = "
            f"{json.dumps(sorted(dates, reverse=True), ensure_ascii=False)};\n")


def write_output(date_str, brief, picked, secondary, items, cfg, registry=None, deep=None,
                 themes=None, papers=None, opinion=None, quality=None):
    # DATA_DIR 环境变量可重定向输出目录（云端 CI 直接写入博客仓库的
    # source/news/data/，checkout 自带历史文件，manifest 扫描结果完整）
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    daily_dir = data_dir / "daily"
    payload = _build_daily_payload(
        date_str, brief, picked, secondary, items, cfg, registry=registry,
        deep=deep, themes=themes, papers=papers, opinion=opinion,
        quality=quality)
    js = ("window.NEWS_DATA = window.NEWS_DATA || {};\n"
          f"window.NEWS_DATA[{json.dumps(date_str)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    _atomic_replace_texts({
        daily_dir / f"{date_str}.js": js,
        data_dir / "manifest.js": _render_manifest(daily_dir, date_str),
    })
    log(f"已写入 data/daily/{date_str}.js（精选 {len(picked)} + 更多 {len(secondary)}）")
    return payload


def write_output_and_commit_registry(
        date_str, brief, picked, secondary, items, cfg, registry, deep=None,
        themes=None, papers=None, opinion=None, quality=None):
    """Atomically publish the daily payload, manifest, and event registry."""
    if not picked:
        return None, ["picked items empty"]
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    daily_dir = data_dir / "daily"
    payload = _build_daily_payload(
        date_str, brief, picked, secondary, items, cfg, registry=registry,
        deep=deep, themes=themes, papers=papers, opinion=opinion,
        quality=quality)
    _atomic_replace_texts({
        daily_dir / f"{date_str}.js": _render_daily_output(date_str, payload),
        data_dir / "manifest.js": _render_manifest(daily_dir, date_str),
        data_dir / "events.json": (
            json.dumps(registry, ensure_ascii=False, indent=1) + "\n"),
    })
    log(f"已写入 data/daily/{date_str}.js（精选 {len(picked)} + 更多 {len(secondary)}）")
    return payload, []


# ----------------------------------------------------------------
# 6.1.8 每周综述：趋势连线 + 待验证回收（长期判断力沉淀）
#   公开主管线幂等检查最近闭合周；候选通过自动审修后才写入。
#   失败写 weekly-health 并跨自然日重试，不阻断每日产出；shadow 不调用周模型。
# ----------------------------------------------------------------

WEEKLY_DIRECTIONS = {"新增", "推进", "反转", "停滞"}
WEEKLY_STATUS = set(TRAJECTORY_RECAP_STATUS)

WEEKLY_SYSTEM = """你是资深主编，把一个完整自然周的日报压缩为可核验的每周报告。
输入中的每条素材都以 [YYYY-MM-DD:item_id] 开头；引用只能原样使用这些复合键。
新闻精选与事件延续用于生成 3-6 条动态主题，深读和论文不混入主题。
输出 JSON：
{"lead":{"title":"≤18字周主线","summary":"≤100字总述"},
 "threads":[{"title":"≤16字","one_liner":"≤60字","direction":"新增|推进|反转|停滞",
 "detail":"≤100字","member_refs":["复合键"],"representative_refs":["1-3个复合键"]}],
 "watch_recap":[{"prior":"≤40字","status":"兑现|部分兑现|未兑现|反转",
 "note":"≤60字","evidence_refs":["复合键"]}],"outlook":["≤50字"]}。
不得创造输入中不存在的引用；只输出 JSON。"""

WEEKLY_AUDIT_SYSTEM = """你是周报客观性审计员。输入证据有严格作用域：
- lead 和 outlook 只能使用明确命名的 whole_week_evidence；
- 每条 thread 只能使用同 index 的 thread_evidence.refs 在 whole_week_evidence 中指向的条目，
  不得用其他周内条目补证；
- 每条 watch_recap 只能使用同 index 的 watch_recap_evidence.refs 指向的条目。
检查各字段是否受对应作用域证据支撑、归因正确，且没有无依据的动机、因果、幅度语言或
虚构平衡说法。只输出：
{"lead":true,"threads":[true],"watch_recap":[true],"outlook":[true]}。
各布尔数组必须与候选内容等长。"""

WEEKLY_REPAIR_SYSTEM = """只修复 failed 指定的周报文字：
lead/outlook 严格依据 whole_week_evidence；threads 只能使用同 index 的
thread_evidence.refs，watch_recap 只能使用同 index 的 watch_recap_evidence.refs，
并在 whole_week_evidence 中按引用取证；不得改变任何引用。
只输出 {"lead":{"title":"...","summary":"..."},
"threads":[{"index":0,"title":"...","one_liner":"...","detail":"..."}],
"watch_recap":[{"index":0,"prior":"...","status":"...","note":"..."}],
"outlook":[{"index":0,"text":"..."}]}。未失败的部分不要返回。"""

WEEKLY_REAUDIT_SYSTEM = """你是周报客观性复审员。只复审 candidate 中列出的修复字段：
lead/outlook 严格依据 whole_week_evidence；threads 和 watch_recap 只能使用各自同 index
的 refs 在 whole_week_evidence 中指向的条目。不得用其他周内条目补证。
只输出实际收到的失败部分，格式为：
{"lead":true,"threads":[{"index":0,"ok":true}],
 "watch_recap":[{"index":0,"ok":true}],"outlook":[{"index":0,"ok":true}]}。
没有收到的部分不要返回；所有 index 必须原样返回且恰好一次。"""


def _validated_weekly_audit(raw, payload):
    if not isinstance(raw, dict) or not isinstance(raw.get("lead"), bool):
        return None
    checked = {"lead": raw["lead"]}
    for key in ("threads", "watch_recap", "outlook"):
        values = raw.get(key)
        expected = payload.get(key) or []
        if (not isinstance(values, list) or len(values) != len(expected)
                or any(not isinstance(value, bool) for value in values)):
            return None
        checked[key] = values
    return checked


def _weekly_failures(checked, payload):
    if checked is None:
        return {
            "lead": True,
            "threads": list(range(len(payload.get("threads") or []))),
            "watch_recap": list(range(len(payload.get("watch_recap") or []))),
            "outlook": list(range(len(payload.get("outlook") or []))),
        }
    return {
        "lead": not checked["lead"],
        "threads": [i for i, ok in enumerate(checked["threads"]) if not ok],
        "watch_recap": [i for i, ok in enumerate(checked["watch_recap"]) if not ok],
        "outlook": [i for i, ok in enumerate(checked["outlook"]) if not ok],
    }


def _weekly_has_failures(failed):
    return bool(failed["lead"] or failed["threads"]
                or failed["watch_recap"] or failed["outlook"])


def _apply_weekly_repair(payload, repair, failed):
    if not isinstance(repair, dict):
        return
    if failed["lead"] and isinstance(repair.get("lead"), dict):
        for field, limit in (("title", 18), ("summary", 100)):
            if field in repair["lead"]:
                payload["lead"][field] = str(repair["lead"].get(field) or "")[:limit]
    specs = {
        "threads": (("title", 16), ("one_liner", 60), ("detail", 100)),
        "watch_recap": (("prior", 40), ("note", 60)),
    }
    for key, fields in specs.items():
        for row in repair.get(key) or []:
            if not isinstance(row, dict):
                continue
            index = row.get("index")
            if (not isinstance(index, int) or isinstance(index, bool)
                    or index not in failed[key] or not 0 <= index < len(payload[key])):
                continue
            for field, limit in fields:
                if field in row:
                    payload[key][index][field] = str(row.get(field) or "")[:limit]
            if (key == "watch_recap" and row.get("status") in WEEKLY_STATUS):
                payload[key][index]["status"] = row["status"]
    for row in repair.get("outlook") or []:
        if not isinstance(row, dict):
            continue
        index = row.get("index")
        if (isinstance(index, int) and not isinstance(index, bool)
                and index in failed["outlook"] and 0 <= index < len(payload["outlook"])):
            payload["outlook"][index] = str(row.get("text") or "")[:50]


def _weekly_failure_request(request, payload, failed):
    thread_indexes = set(failed["threads"])
    watch_indexes = set(failed["watch_recap"])
    thread_evidence = [
        row for row in request["thread_evidence"]
        if row["index"] in thread_indexes
    ]
    watch_evidence = [
        row for row in request["watch_recap_evidence"]
        if row["index"] in watch_indexes
    ]
    if failed["lead"] or failed["outlook"]:
        evidence = request["whole_week_evidence"]
    else:
        local_refs = {
            ref for row in (*thread_evidence, *watch_evidence)
            for ref in row.get("refs") or []
        }
        evidence = {
            ref: item for ref, item in request["whole_week_evidence"].items()
            if ref in local_refs
        }
    candidate = {}
    if failed["lead"]:
        candidate["lead"] = payload.get("lead")
    if thread_indexes:
        candidate["threads"] = [
            {"index": index, **payload["threads"][index]}
            for index in failed["threads"]
        ]
    if watch_indexes:
        candidate["watch_recap"] = [
            {"index": index, **payload["watch_recap"][index]}
            for index in failed["watch_recap"]
        ]
    if failed["outlook"]:
        candidate["outlook"] = [
            {"index": index, "text": payload["outlook"][index]}
            for index in failed["outlook"]
        ]
    return {
        "whole_week_evidence": evidence,
        "thread_evidence": thread_evidence,
        "watch_recap_evidence": watch_evidence,
        "candidate": candidate,
        "failed": failed,
    }


def _validated_weekly_reaudit(raw, failed):
    if not isinstance(raw, dict):
        return False
    if failed["lead"] and raw.get("lead") is not True:
        return False
    for key in ("threads", "watch_recap", "outlook"):
        expected = list(failed[key])
        rows = raw.get(key, [])
        if not isinstance(rows, list) or len(rows) != len(expected):
            return False
        by_index = {}
        for row in rows:
            if (not isinstance(row, dict) or type(row.get("index")) is not int
                    or type(row.get("ok")) is not bool
                    or row["index"] in by_index):
                return False
            by_index[row["index"]] = row["ok"]
        if set(by_index) != set(expected) or not all(by_index.values()):
            return False
    return True


def _audit_weekly_result(audit_llm, payload, evidence):
    def scoped_evidence(rows, ref_fields):
        scoped = []
        for index, row in enumerate(rows or []):
            local_refs = []
            for field in ref_fields:
                for ref in row.get(field) or []:
                    if ref in evidence and ref not in local_refs:
                        local_refs.append(ref)
            scoped.append({"index": index, "refs": local_refs})
        return scoped

    request = {
        "whole_week_evidence": evidence,
        "thread_evidence": scoped_evidence(
            payload.get("threads"), ("member_refs", "representative_refs")),
        "watch_recap_evidence": scoped_evidence(
            payload.get("watch_recap"), ("evidence_refs",)),
        "candidate": {
            key: payload.get(key) for key in ("lead", "threads", "watch_recap", "outlook")},
    }
    failure_stages = []
    try:
        checked = _validated_weekly_audit(
            audit_llm.json_call(WEEKLY_AUDIT_SYSTEM,
                                json.dumps(request, ensure_ascii=False)), payload)
    except Exception as exc:
        log(f"  周综述客观性初审失败，进入修复: {redact(exc)}")
        checked = None
    if checked is None:
        failure_stages.append("initial_audit_failed")
        log("  周综述客观性初审结果无效，进入定向修复")
    failed = _weekly_failures(checked, payload)
    if not _weekly_has_failures(failed):
        return True, ""
    if "initial_audit_failed" not in failure_stages:
        failure_stages.append("initial_audit_failed")
    repair_request = _weekly_failure_request(request, payload, failed)
    try:
        repair = audit_llm.json_call(
            WEEKLY_REPAIR_SYSTEM,
            json.dumps(repair_request, ensure_ascii=False))
        if not isinstance(repair, dict):
            failure_stages.append("repair_failed")
            log("  周综述客观性修复结果无效，继续复审")
        else:
            _apply_weekly_repair(payload, repair, failed)
    except Exception as exc:
        failure_stages.append("repair_failed")
        log(f"  周综述客观性修复失败，继续复审: {redact(exc)}")
    reaudit_request = _weekly_failure_request(request, payload, failed)
    try:
        checked = _validated_weekly_reaudit(
            audit_llm.json_call(
                WEEKLY_REAUDIT_SYSTEM,
                json.dumps(reaudit_request, ensure_ascii=False)), failed)
    except Exception as exc:
        log(f"  周综述客观性复审失败: {redact(exc)}")
        checked = False
    if checked is True:
        return True, ""
    failure_stages.append("reaudit_failed")
    log("  周综述客观性复审未通过")
    return False, "+".join(dict.fromkeys(failure_stages))


def _audit_weekly(audit_llm, payload, evidence):
    """Compatibility wrapper returning only the publish decision."""
    return _audit_weekly_result(audit_llm, payload, evidence)[0]


def iso_week_key(d):
    """datetime/date -> 'YYYY-Www'（ISO 周，与前端命名一致）。"""
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def read_daily_payload(path):
    """从本管线写出的 daily js 里剥壳取 JSON；失败返回 None。"""
    try:
        src = path.read_text(encoding="utf-8")
        m = re.search(r"window\.NEWS_DATA\[[^\]]+\] = (\{.*\});", src, re.S)
        return json.loads(m.group(1)) if m else None
    except Exception:
        return None


def read_weekly_payload(path):
    """从周综述 js 里剥壳取 JSON；失败返回 None。"""
    try:
        src = path.read_text(encoding="utf-8")
        m = re.search(r"window\.WEEKLY_DATA\[[^\]]+\] = (\{.*\});", src, re.S)
        return json.loads(m.group(1)) if m else None
    except Exception:
        return None


def latest_closed_iso_week(date_str):
    """Return Monday/Sunday/key for the most recent fully ended ISO week."""
    current = datetime.strptime(date_str, "%Y-%m-%d")
    this_monday = current - timedelta(days=current.weekday())
    start = this_monday - timedelta(days=7)
    end = start + timedelta(days=6)
    return start, end, iso_week_key(end)


def _weekly_ref_index(days):
    refs = {}
    for dp in days:
        date = str(dp.get("date") or "")
        for kind, key in (("item", "items"), ("deep", "deep"), ("paper", "papers")):
            for item in dp.get(key) or []:
                item_id = str(item.get("id") or "")
                if date and item_id:
                    refs[f"{date}:{item_id}"] = (kind, item)
    return refs


def validate_weekly_references(payload, days):
    """Return structural/reference errors; an empty list means safe to publish."""
    errors = []
    refs = _weekly_ref_index(days)
    threads = payload.get("threads") or []
    if payload.get("version") == 2 and not 3 <= len(threads) <= 6:
        errors.append("v2 threads must contain 3-6 entries")
    try:
        range_start = datetime.strptime(payload["range"]["start"], "%Y-%m-%d")
        range_end = datetime.strptime(payload["range"]["end"], "%Y-%m-%d")
        if payload.get("version") == 2:
            if ((range_end - range_start).days != 6 or range_start.weekday() != 0
                    or range_end.weekday() != 6 or iso_week_key(range_end) != payload.get("week")):
                errors.append("v2 range must be the report's complete ISO week")
    except (KeyError, TypeError, ValueError):
        range_start = range_end = None
        errors.append("range is invalid")

    def check_refs(values, path, allowed):
        if not isinstance(values, list):
            errors.append(f"{path} must be a list")
            return
        for ref in values:
            if not isinstance(ref, str) or ref not in refs:
                errors.append(f"{path} unresolved ref: {ref}")
            elif refs[ref][0] not in allowed:
                errors.append(f"{path} wrong ref type: {ref}")
            elif range_start is not None:
                try:
                    ref_day = datetime.strptime(ref.split(":", 1)[0], "%Y-%m-%d")
                    if not range_start <= ref_day <= range_end:
                        errors.append(f"{path} out-of-week ref: {ref}")
                except ValueError:
                    errors.append(f"{path} invalid date ref: {ref}")

    for i, thread in enumerate(threads):
        check_refs(thread.get("member_refs"), f"threads[{i}].member_refs", {"item"})
        check_refs(thread.get("representative_refs"),
                   f"threads[{i}].representative_refs", {"item"})
    for i, recap in enumerate(payload.get("watch_recap") or []):
        check_refs(recap.get("evidence_refs"), f"watch_recap[{i}].evidence_refs", {"item"})
    reading = payload.get("reading") or {}
    check_refs(reading.get("deep_refs", []), "reading.deep_refs", {"deep"})
    check_refs(reading.get("paper_refs", []), "reading.paper_refs", {"paper"})
    return errors


def write_weekly_manifest(data_dir, keep=26):
    """Write a compatible archive list without mutating any historical report."""
    wdir = Path(data_dir) / "weekly"
    if not wdir.exists():
        return []
    eligible = []
    for path in wdir.glob("*.js"):
        if path.stem == "manifest":
            continue
        payload = read_weekly_payload(path)
        if not payload:
            continue
        if payload.get("version") == 2:
            coverage = payload.get("coverage") or {}
            include = (coverage.get("expected_days") == 7
                       and int(coverage.get("daily_count") or 0) >= 5)
        else:
            try:
                start = datetime.strptime(payload["range"]["start"], "%Y-%m-%d")
                end = datetime.strptime(payload["range"]["end"], "%Y-%m-%d")
                declared_days = (end - start).days + 1
                daily_dir = Path(data_dir) / "daily"
                if daily_dir.exists() and declared_days > 0:
                    available = 0
                    cursor = start
                    while cursor <= end:
                        cursor_date = cursor.strftime("%Y-%m-%d")
                        daily = read_daily_payload(daily_dir / f"{cursor_date}.js")
                        if daily and daily.get("date") == cursor_date:
                            available += 1
                        cursor += timedelta(days=1)
                    include = available >= 5
                else:
                    # Legacy files have no explicit coverage metadata. Without
                    # their daily payloads, a wide range cannot prove 5/7.
                    include = False
            except (KeyError, TypeError, ValueError):
                include = False
        if include:
            eligible.append(path.stem)
    weeks = sorted(eligible, reverse=True)[:int(keep)]
    (wdir / "manifest.js").write_text(
        f"window.WEEKLY_MANIFEST = {json.dumps(weeks, ensure_ascii=False)};\n",
        encoding="utf-8")
    return weeks


def weekly_pick_evidence(days, max_total=100):
    """Return the bounded evidence that both weekly generation and audit may use."""
    buckets = []
    for dp in sorted(days, key=lambda value: str(value.get("date") or "")):
        date = str(dp.get("date") or "")
        rows = []
        for it in dp.get("items") or []:
            if it.get("tier") != "pick" or not it.get("id"):
                continue
            ref = f"{date}:{it.get('id')}"
            evidence = {
                "category": CAT_NAMES.get(
                    it.get("category", ""), it.get("category", "")),
                "title": str(it.get("title") or ""),
                "summary": str(it.get("summary") or ""),
            }
            history = [{
                "date": str(row.get("date") or ""),
                "summary": str(row.get("summary") or ""),
            } for row in (it.get("history") or [])[-3:] if isinstance(row, dict)]
            if history:
                evidence["history"] = history
            if it.get("watch"):
                evidence["watch"] = str(it.get("watch"))
            rows.append((ref, evidence))
        if rows:
            buckets.append(rows)

    selected = []
    row = 0
    while len(selected) < int(max_total):
        added = False
        for bucket in buckets:
            if row < len(bucket):
                selected.append(bucket[row])
                added = True
                if len(selected) >= int(max_total):
                    break
        if not added:
            break
        row += 1
    return dict(selected)


def render_weekly_pick_material(evidence):
    """Render an existing canonical evidence map for the generation prompt."""
    lines = []
    for ref, item in evidence.items():
        history = " → ".join(
            f"{row.get('date', '')}:{row.get('summary', '')}"
            for row in item.get("history") or [])
        lines.append(
            f"[{ref}] [{item.get('category', '')}] "
            f"{item.get('title', '')}：{item.get('summary', '')}"
            + (f"｜事件延续:{history}" if history else "")
            + (f"｜关注:{item.get('watch')}" if item.get("watch") else ""))
    return lines


def weekly_pick_material(days, max_total=100):
    """Build and render canonical date-balanced weekly evidence."""
    return render_weekly_pick_material(
        weekly_pick_evidence(days, max_total=max_total))


WEEKLY_HEALTH_VERSION = 1
WEEKLY_AUDIT_MAX_ATTEMPTS = 3
WEEKLY_EVIDENCE_LIMIT = 100
WEEKLY_EVIDENCE_PROJECTION_VERSION = 1
WEEKLY_EVIDENCE_FIELDS = ("category", "title", "summary", "history", "watch")


def weekly_audit_contract_fingerprint():
    raw = json.dumps({
        "version": 1,
        "evidence_projection_version": WEEKLY_EVIDENCE_PROJECTION_VERSION,
        "evidence_limit": WEEKLY_EVIDENCE_LIMIT,
        "evidence_fields": WEEKLY_EVIDENCE_FIELDS,
        "generation_prompt": WEEKLY_SYSTEM,
        "audit_prompt": WEEKLY_AUDIT_SYSTEM,
        "repair_prompt": WEEKLY_REPAIR_SYSTEM,
        "reaudit_prompt": WEEKLY_REAUDIT_SYSTEM,
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def load_weekly_health(data_dir):
    path = Path(data_dir) / "weekly-health.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        payload = {}
    weeks = payload.get("weeks") if isinstance(payload, dict) else None
    return {"version": WEEKLY_HEALTH_VERSION,
            "weeks": weeks if isinstance(weeks, dict) else {}}


def _render_weekly_health(health, keep=26):
    weeks = health.get("weeks") if isinstance(health, dict) else {}
    safe_weeks = {}
    for week in sorted(weeks or {}, reverse=True)[:max(1, int(keep))]:
        row = weeks.get(week)
        if isinstance(row, dict):
            safe_weeks[str(week)] = {
                key: row[key] for key in (
                    "status", "attempts", "last_attempt_date", "reason",
                    "contract_fingerprint") if key in row
            }
    return json.dumps({
        "version": WEEKLY_HEALTH_VERSION, "weeks": safe_weeks,
    }, ensure_ascii=False, indent=2) + "\n"


def save_weekly_health(data_dir, health, keep=26):
    path = Path(data_dir) / "weekly-health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_replace_texts({path: _render_weekly_health(health, keep=keep)})


def _weekly_attempt_context(data_dir, week_key, fingerprint):
    health = load_weekly_health(data_dir)
    current = health["weeks"].get(week_key)
    valid = (
        isinstance(current, dict)
        and current.get("status") in {"pending", "passed", "failed", "exhausted"}
        and type(current.get("attempts")) is int
        and 0 <= current["attempts"] <= WEEKLY_AUDIT_MAX_ATTEMPTS
        and isinstance(current.get("last_attempt_date"), str)
        and isinstance(current.get("reason"), str)
        and current.get("contract_fingerprint") == fingerprint
    )
    if valid:
        attempts = current["attempts"]
        valid = (
            (current["status"] == "pending" and attempts == 0)
            or (current["status"] == "failed"
                and 1 <= attempts < WEEKLY_AUDIT_MAX_ATTEMPTS)
            or (current["status"] == "exhausted"
                and attempts == WEEKLY_AUDIT_MAX_ATTEMPTS)
            or (current["status"] == "passed" and 1 <= attempts)
        )
    if not valid:
        current = {
            "status": "pending", "attempts": 0, "last_attempt_date": "",
            "reason": "", "contract_fingerprint": fingerprint,
        }
        health["weeks"][week_key] = current
    return health, current


def _record_weekly_health(data_dir, health, week_key, *, date_str, attempts,
                          fingerprint, status, reason, keep):
    health["weeks"][week_key] = {
        "status": status,
        "attempts": int(attempts),
        "last_attempt_date": str(date_str),
        "reason": str(reason),
        "contract_fingerprint": fingerprint,
    }
    save_weekly_health(data_dir, health, keep=keep)


def _valid_weekly_generation_shape(result):
    """Validate containers before normalizing paid weekly model output."""
    if not isinstance(result, dict):
        return False
    lead = result.get("lead")
    if lead is not None:
        if not isinstance(lead, dict):
            return False
        if any(value is not None and not isinstance(value, str)
               for value in (lead.get("title"), lead.get("summary"))):
            return False
    for key in ("threads", "watch_recap", "outlook"):
        if not isinstance(result.get(key), list):
            return False
    if any(not isinstance(value, str) for value in result["outlook"]):
        return False
    for row in result["threads"]:
        if not isinstance(row, dict):
            return False
        for field in ("member_refs", "representative_refs"):
            refs = row.get(field)
            if refs is not None and (not isinstance(refs, list)
                                     or any(not isinstance(ref, str) for ref in refs)):
                return False
        if any(value is not None and not isinstance(value, str) for value in (
                row.get("title"), row.get("one_liner"), row.get("direction"),
                row.get("detail"))):
            return False
    for row in result["watch_recap"]:
        if not isinstance(row, dict):
            return False
        refs = row.get("evidence_refs")
        if refs is not None and (not isinstance(refs, list)
                                 or any(not isinstance(ref, str) for ref in refs)):
            return False
        if any(value is not None and not isinstance(value, str) for value in (
                row.get("prior"), row.get("status"), row.get("note"))):
            return False
    return True


def write_weekly(llm, date_str, cfg, data_dir, profile_text="", audit_llm=None,
                 force=False):
    """Idempotently create v2 report for the most recent fully closed ISO week."""
    wcfg = cfg.get("weekly") or {}
    keep = int(wcfg.get("keep_weeks", 26))
    minimum = int(wcfg.get("min_daily_count", 5))
    start, end, week_key = latest_closed_iso_week(date_str)
    data_dir = Path(data_dir)
    target = data_dir / "weekly" / f"{week_key}.js"
    if target.exists() and not force:
        write_weekly_manifest(data_dir, keep)
        log(f"  周综述：{week_key} 已存在，跳过（幂等）")
        return read_weekly_payload(target)

    # Public weekly persistence is fail-closed: without an auditor there must
    # be no generation call and no report write.
    if audit_llm is None:
        log(f"  周综述：{week_key} 缺少发布前审计器，跳过生成与写入")
        return None

    fingerprint = weekly_audit_contract_fingerprint()
    health, health_row = _weekly_attempt_context(data_dir, week_key, fingerprint)
    if force:
        health_row.update({
            "status": "pending", "attempts": 0, "last_attempt_date": "",
            "reason": "", "contract_fingerprint": fingerprint,
        })
    elif health_row.get("status") == "passed":
        # A passed marker without its report is inconsistent (for example a
        # partial manual restore). Rebuild instead of spending a retry day.
        health_row.update({
            "status": "pending", "attempts": 0, "last_attempt_date": "",
            "reason": "", "contract_fingerprint": fingerprint,
        })
    attempts = int(health_row.get("attempts") or 0)
    if (attempts >= WEEKLY_AUDIT_MAX_ATTEMPTS
            and health_row.get("status") == "exhausted"):
        log(f"  周综述：{week_key} 自动审修已耗尽 {attempts} 次，停止重试")
        return None
    if (health_row.get("status") == "failed"
            and health_row.get("last_attempt_date") == date_str):
        log(f"  周综述：{week_key} 今日已自动审修失败，等待下一自然日重试")
        return None

    daily_dir = data_dir / "daily"
    days = []
    missing_dates = []
    cursor = start
    while cursor <= end:
        day_str = cursor.strftime("%Y-%m-%d")
        p = daily_dir / f"{day_str}.js"
        payload = read_daily_payload(p)
        if payload and payload.get("date") == day_str:
            days.append(payload)
        else:
            missing_dates.append(day_str)
        cursor += timedelta(days=1)
    if len(days) < minimum:
        if audit_llm is not None:
            _record_weekly_health(
                data_dir, health, week_key, date_str=date_str,
                attempts=attempts, fingerprint=fingerprint, status="pending",
                reason="insufficient_coverage", keep=keep)
        log(f"  周综述：{week_key} 仅覆盖 {len(days)}/7 天（门槛 {minimum}/7），跳过")
        return None

    refs = _weekly_ref_index(days)
    pick_refs = []
    for dp in days:
        for it in dp.get("items", []):
            if it.get("tier") != "pick":
                continue
            ref = f"{dp.get('date')}:{it.get('id')}"
            pick_refs.append(ref)
    pick_refs = list(dict.fromkeys(ref for ref in pick_refs if ref in refs))
    if len(pick_refs) < 3:
        if audit_llm is not None:
            _record_weekly_health(
                data_dir, health, week_key, date_str=date_str,
                attempts=attempts, fingerprint=fingerprint, status="pending",
                reason="insufficient_material", keep=keep)
        log(f"  周综述：{week_key} 仅有 {len(pick_refs)} 条可引用精选，不足 3 条主题合同，跳过")
        return None
    evidence = weekly_pick_evidence(days, max_total=WEEKLY_EVIDENCE_LIMIT)
    visible_refs = set(evidence)
    pick_lines = render_weekly_pick_material(evidence)

    prev_key = iso_week_key(start - timedelta(days=1))
    prev = read_weekly_payload(data_dir / "weekly" / f"{prev_key}.js")
    prev_block = ""
    if prev:
        pt = "；".join((t.get("title", "") + ":" + t.get("one_liner", ""))
                      for t in prev.get("threads", []))
        pw = "；".join(o for o in prev.get("outlook", []))
        prev_block = f"【上周综述·主线】{pt}\n【上周综述·下周关注】{pw}\n\n"

    prof_block = ("【读者兴趣画像】\n" + profile_text.strip() + "\n\n"
                  if profile_has_content(profile_text) else "")
    user = (prof_block + prev_block
            + "【本周新闻精选与事件线】\n" + "\n".join(pick_lines))

    attempt_number = attempts
    if (audit_llm is not None
            and (health_row.get("status") == "pending"
                 or str(health_row.get("last_attempt_date") or "") != date_str)):
        attempt_number += 1
    try:
        result = llm.json_call(WEEKLY_SYSTEM, user)
    except Exception as exc:
        if audit_llm is not None:
            status = ("exhausted" if attempt_number >= WEEKLY_AUDIT_MAX_ATTEMPTS
                      else "failed")
            _record_weekly_health(
                data_dir, health, week_key, date_str=date_str,
                attempts=attempt_number, fingerprint=fingerprint, status=status,
                reason="generation_error", keep=keep)
        log(f"  周综述：LLM 调用失败，跳过（{redact(exc)}）")
        return None
    if not _valid_weekly_generation_shape(result):
        if audit_llm is not None:
            status = ("exhausted" if attempt_number >= WEEKLY_AUDIT_MAX_ATTEMPTS
                      else "failed")
            _record_weekly_health(
                data_dir, health, week_key, date_str=date_str,
                attempts=attempt_number, fingerprint=fingerprint, status=status,
                reason="generation_invalid", keep=keep)
        log("  周综述：LLM 输出异常，跳过")
        return None

    def _clip(s, n):
        return str(s or "")[:n]

    def _valid_refs(values, kinds={"item"}, allowed=None):
        out = []
        for ref in values or []:
            if (ref in refs and refs[ref][0] in kinds and ref not in out
                    and (allowed is None or ref in allowed)):
                out.append(ref)
        return out

    threads = []
    claimed_representatives = set()
    for t in (result.get("threads") or [])[:6]:
        if not isinstance(t, dict):
            continue
        member_refs = _valid_refs(t.get("member_refs"), allowed=visible_refs)
        representative_refs = _valid_refs(
            t.get("representative_refs"), allowed=visible_refs)[:3]
        member_refs = member_refs or representative_refs
        representative_refs = representative_refs or member_refs[:1]
        if not member_refs:
            continue
        unused_representatives = [ref for ref in representative_refs
                                  if ref not in claimed_representatives]
        if not unused_representatives:
            unused_representatives = [ref for ref in member_refs
                                      if ref not in claimed_representatives][:1]
        if not unused_representatives:
            continue
        representative_refs = unused_representatives[:3]
        claimed_representatives.update(representative_refs)
        threads.append({
            "title": _clip(t.get("title"), 16),
            "one_liner": _clip(t.get("one_liner"), 60),
            "direction": t.get("direction") if t.get("direction") in WEEKLY_DIRECTIONS else "推进",
            "detail": _clip(t.get("detail"), 100),
            "member_refs": member_refs,
            "representative_refs": representative_refs,
        })

    # Keep the public v2 contract stable even when the model under-produces themes.
    # Theme representatives must be distinct. A broad model theme may list all
    # members; those members are still available for deterministic split themes.
    used = set(claimed_representatives)
    for ref in evidence:
        if len(threads) >= 3:
            break
        if ref in used or ref not in refs:
            continue
        item = evidence[ref]
        threads.append({
            "title": _clip(item.get("title"), 16),
            "one_liner": _clip(item.get("summary"), 60),
            "direction": "新增",
            "detail": _clip(item.get("detail") or item.get("summary"), 100),
            "member_refs": [ref],
            "representative_refs": [ref],
        })
        used.add(ref)
        claimed_representatives.add(ref)

    if len(threads) < 3:
        status = ("exhausted" if attempt_number >= WEEKLY_AUDIT_MAX_ATTEMPTS
                  else "failed")
        _record_weekly_health(
            data_dir, health, week_key, date_str=date_str,
            attempts=attempt_number, fingerprint=fingerprint, status=status,
            reason="generation_invalid", keep=keep)
        log(f"  周综述：仅形成 {len(threads)} 条有效主题，不满足 3-6 条合同，跳过")
        return None
    recap = []
    for r in (result.get("watch_recap") or [])[:6]:
        if not isinstance(r, dict):
            continue
        evidence_refs = _valid_refs(r.get("evidence_refs"), allowed=visible_refs)
        if not evidence_refs:
            continue
        recap.append({
            "prior": _clip(r.get("prior"), 40),
            "status": r.get("status") if r.get("status") in WEEKLY_STATUS else "未兑现",
            "note": _clip(r.get("note"), 60),
            "evidence_refs": evidence_refs,
        })
    outlook = [_clip(o, 50) for o in (result.get("outlook") or [])[:3] if str(o or "").strip()]
    if not threads:
        log("  周综述：无有效内容，跳过写文件")
        return None

    lead_in = result.get("lead") if isinstance(result.get("lead"), dict) else {}
    lead = {
        "title": _clip(lead_in.get("title") or threads[0]["title"], 18),
        "summary": _clip(lead_in.get("summary") or threads[0]["one_liner"], 100),
    }
    pick_items = [refs[ref][1] for ref in pick_refs if ref in refs]
    event_count = len({it.get("event_id") or ref for ref, it in
                       ((ref, refs[ref][1]) for ref in pick_refs if ref in refs)})
    source_names = {src.get("name") for it in pick_items for src in (it.get("sources") or [])
                    if src.get("name")}
    deep_refs = sorted(ref for ref, (kind, _) in refs.items() if kind == "deep")
    paper_refs = sorted(ref for ref, (kind, _) in refs.items() if kind == "paper")
    reading_minutes = sum(int((refs[ref][1].get("read_minutes") or 0))
                          for ref in deep_refs + paper_refs)

    payload = {
        "version": 2,
        "week": week_key,
        "range": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverage": {"daily_count": len(days), "expected_days": 7,
                     "missing_dates": missing_dates},
        "lead": lead,
        "stats": {"pick_count": len(pick_items), "event_count": event_count,
                  "source_count": len(source_names),
                  "read_minutes": max(1, int(round(len(pick_items) * 0.75 + reading_minutes)))},
        "threads": threads,
        "watch_recap": recap,
        "reading": {"deep_refs": deep_refs, "paper_refs": paper_refs},
        "outlook": outlook,
    }
    errors = validate_weekly_references(payload, days)
    if errors:
        if audit_llm is not None:
            status = ("exhausted" if attempt_number >= WEEKLY_AUDIT_MAX_ATTEMPTS
                      else "failed")
            _record_weekly_health(
                data_dir, health, week_key, date_str=date_str,
                attempts=attempt_number, fingerprint=fingerprint, status=status,
                reason="reference_invalid", keep=keep)
        log("  周综述：引用校验失败，跳过写文件：" + "; ".join(errors))
        return None
    audit_passed, audit_reason = _audit_weekly_result(
        audit_llm, payload, evidence)
    if not audit_passed:
        status = ("exhausted" if attempt_number >= WEEKLY_AUDIT_MAX_ATTEMPTS
                  else "failed")
        _record_weekly_health(
            data_dir, health, week_key, date_str=date_str,
            attempts=attempt_number, fingerprint=fingerprint, status=status,
            reason=audit_reason or "reaudit_failed", keep=keep)
        log("  周综述：客观性复审未通过，跳过写文件")
        return None
    wdir = data_dir / "weekly"
    wdir.mkdir(parents=True, exist_ok=True)
    js = ("window.WEEKLY_DATA = window.WEEKLY_DATA || {};\n"
          f"window.WEEKLY_DATA[{json.dumps(week_key)}] = "
          f"{json.dumps(payload, ensure_ascii=False, indent=1)};\n")
    health["weeks"][week_key] = {
        "status": "passed", "attempts": int(attempt_number),
        "last_attempt_date": str(date_str), "reason": "",
        "contract_fingerprint": fingerprint,
    }
    _atomic_replace_texts({
        wdir / f"{week_key}.js": js,
        data_dir / "weekly-health.json": _render_weekly_health(health, keep=keep),
    })

    write_weekly_manifest(data_dir, keep)
    log(f"  周综述已写入 data/weekly/{week_key}.js（主线 {len(threads)} · 回收 {len(recap)}）")
    return payload


def run_weekly_stage(llm, audit_llm, date_str, cfg, data_dir, profile_text,
                     policy):
    """Run publish-time weekly generation; shadow never duplicates this work."""
    if not (cfg.get("weekly") or {}).get("enabled"):
        return None
    if policy.get("mode") == "shadow":
        log("周综述：shadow 复用公开生成结果，跳过生成与审计")
        return None
    log("周综述：趋势连线 + 发布前自动审修 ...")
    try:
        return write_weekly(
            llm, date_str, cfg, data_dir, profile_text,
            audit_llm=audit_llm)
    except Exception as exc:
        log(f"  周综述失败（不影响每日产出）: {redact(exc)}")
        return None


# ----------------------------------------------------------------
# 6.2 RSS 输出：data/feed.xml（每条精选一个 item，含深读推荐）
#   注：daily/weekly 剥壳解析器 read_daily_payload/read_weekly_payload 见上方周综述节，
#   feed 生成复用 read_daily_payload。
# ----------------------------------------------------------------

def xml_esc(s):
    return html.escape(str(s or ""), quote=True)


def _cdata(s):
    # CDATA 内唯一的禁忌是 "]]>"
    return "<![CDATA[" + str(s or "").replace("]]>", "]]]]><![CDATA[>") + "]]>"


def _rfc822(iso, fallback):
    try:
        return format_datetime(datetime.fromisoformat(str(iso)))
    except Exception:
        return fallback


def write_feed(data_dir, date_str, cfg):
    """生成 feed.xml。失败只 log 不中止（新闻数据已落盘）。"""
    try:
        feed_days = int(cfg.get("feed_days", 7))
        site = str(cfg.get("site_url", "")).rstrip("/")
        daily_dir = data_dir / "daily"
        dates = sorted([p.stem for p in daily_dir.glob("*.js")], reverse=True)[:feed_days]
        now_rfc = format_datetime(datetime.now(timezone.utc))
        items_xml = []
        for d in dates:
            payload = read_daily_payload(daily_dir / f"{d}.js")
            if not payload:
                continue
            day_rfc = _rfc822(payload.get("generated_at"), now_rfc)
            for it in payload.get("items", []):
                if it.get("tier") != "pick":
                    continue
                srcs = [
                    source for source in (it.get("sources") or [])
                    if isinstance(source, dict)
                    and _is_valid_http_url(source.get("url"))
                ]
                link = (srcs[0].get("url") if srcs else "") or f"{site}/news/"
                desc = f"<p>{html.escape(it.get('summary', ''))}</p>"
                if it.get("watch"):
                    desc += f"<p><b>走向：</b>{html.escape(it['watch'])}</p>"
                if srcs:
                    desc += "<p>来源：" + "、".join(
                        f'<a href="{html.escape(s.get("url", ""), quote=True)}">'
                        f'{html.escape(s.get("name", ""))}</a>' for s in srcs) + "</p>"
                cat = CAT_NAMES.get(it.get("category", ""), it.get("category", ""))
                items_xml.append(
                    "<item>"
                    f"<title>{xml_esc('[' + cat + '] ' + it.get('title', ''))}</title>"
                    f"<link>{xml_esc(link)}</link>"
                    f"<guid isPermaLink=\"false\">{xml_esc(d + ':' + it.get('id', ''))}</guid>"
                    f"<pubDate>{_rfc822(it.get('time'), day_rfc)}</pubDate>"
                    f"<description>{_cdata(desc)}</description>"
                    "</item>")
            for dp in payload.get("deep", []):
                link = (dp.get("url") if _is_valid_http_url(dp.get("url")) else
                        f"{site}/news/")
                desc = f"<p>{html.escape(dp.get('brief', ''))}</p>"
                if dp.get("why"):
                    desc += f"<p><b>为什么值得读：</b>{html.escape(dp['why'])}</p>"
                desc += (f"<p>{html.escape(dp.get('source', ''))} · "
                         f"约 {int(dp.get('read_minutes') or 0)} 分钟</p>")
                items_xml.append(
                    "<item>"
                    f"<title>{xml_esc('【深读】' + (dp.get('title_zh') or dp.get('title', '')))}</title>"
                    f"<link>{xml_esc(link)}</link>"
                    f"<guid isPermaLink=\"false\">{xml_esc(d + ':' + dp.get('id', ''))}</guid>"
                    f"<pubDate>{day_rfc}</pubDate>"
                    f"<description>{_cdata(desc)}</description>"
                    "</item>")
        feed = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<rss version="2.0"><channel>'
                "<title>每日驾驶舱 · Daily Briefing</title>"
                f"<link>{xml_esc(site + '/news/')}</link>"
                "<description>个人信息筛选驾驶舱：每日精选新闻与深读推荐</description>"
                "<language>zh-cn</language>"
                f"<lastBuildDate>{now_rfc}</lastBuildDate>"
                + "".join(items_xml) +
                "</channel></rss>\n")
        (data_dir / "feed.xml").write_text(feed, encoding="utf-8")
        log(f"  feed.xml：{len(items_xml)} 个 item（近 {len(dates)} 天）")
    except Exception as e:
        log(f"  feed.xml 生成失败（不影响主管线）: {e}")


# ----------------------------------------------------------------
# 6.3 搜索索引：data/search_index.js（紧凑数组，前端懒加载）
# ----------------------------------------------------------------

def index_rows(payload):
    rows = []
    d = payload.get("date", "")
    for it in payload.get("items", []):
        rows.append([d, it.get("id", ""), it.get("tier", ""), it.get("category", ""),
                     it.get("title", ""), "|".join(it.get("tags") or [])])
    for dp in payload.get("deep", []):
        rows.append([d, dp.get("id", ""), "deep", "deep",
                     dp.get("title_zh") or dp.get("title", ""), ""])
    return rows


def update_search_index(data_dir, date_str, cfg):
    """当日条目替换写入（幂等）；索引缺失/损坏时从现存 daily 文件全量重建。"""
    try:
        keep_days = int(cfg.get("search_index_days", 180))
        daily_dir = data_dir / "daily"
        idx_file = data_dir / "search_index.js"
        entries = []
        if idx_file.exists():
            try:
                m = re.search(r"window\.NEWS_INDEX = (\[.*\]);",
                              idx_file.read_text(encoding="utf-8"), re.S)
                entries = json.loads(m.group(1)) if m else []
            except Exception as e:
                log(f"  search_index.js 读取失败，重建: {e}")
                entries = []
        if entries:
            entries = [r for r in entries if r and r[0] != date_str]
        else:
            for d in sorted(p.stem for p in daily_dir.glob("*.js")):
                if d == date_str:
                    continue
                payload = read_daily_payload(daily_dir / f"{d}.js")
                if payload:
                    entries += index_rows(payload)
        payload = read_daily_payload(daily_dir / f"{date_str}.js")
        if payload:
            entries += index_rows(payload)
        today = datetime.strptime(date_str, "%Y-%m-%d")

        def _fresh(dt):
            try:
                return (today - datetime.strptime(dt, "%Y-%m-%d")).days <= keep_days
            except ValueError:
                return False

        entries = [r for r in entries if _fresh(r[0])]
        entries.sort(key=lambda r: r[0], reverse=True)
        idx_file.write_text("window.NEWS_INDEX = "
                            + json.dumps(entries, ensure_ascii=False) + ";\n",
                            encoding="utf-8")
        log(f"  搜索索引：{len(entries)} 条")
    except Exception as e:
        log(f"  搜索索引更新失败（不影响主管线）: {e}")


# ----------------------------------------------------------------
# 6.5 信源健康度：滚动记录抓取状态，连续失败报警
# ----------------------------------------------------------------

HEALTH_KEEP_DAYS = 14
HEALTH_ALERT_DAYS = 3


def update_source_health(fetch_stats, date_str, events=None, picked=None, items=None):
    """把当日各源抓取状态写入 source_health.json（滚动保留最近 14 天），
    可选记录该源参与的评分事件与最终精选事件数量；多源事件分别计入各参与源。
    并对"最近 3 个记录日连续抓取失败"的源发 GitHub Actions ::warning:: 注解
    （本地运行时就是普通日志行）。"""
    data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    health_file = data_dir / "source_health.json"
    health = {"days": {}}
    if health_file.exists():
        try:
            health = json.loads(health_file.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"  source_health.json 读取失败，重建: {e}")
            health = {"days": {}}
    days = health.setdefault("days", {})
    scored_counts = {}
    selected_counts = {}

    def source_ids_for_event(event):
        if items is None:
            return set()
        return {
            items[index].get("source_id")
            for index in event.get("ids", [])
            if isinstance(index, int) and not isinstance(index, bool)
            and 0 <= index < len(items)
            and items[index].get("source_id")
        }

    if events is not None and items is not None:
        for event in events:
            for sid in source_ids_for_event(event):
                scored_counts[sid] = scored_counts.get(sid, 0) + 1
    if picked is not None and items is not None:
        for event in picked:
            for sid in source_ids_for_event(event):
                selected_counts[sid] = selected_counts.get(sid, 0) + 1

    day_record = {}
    for sid, st in fetch_stats.items():
        row = {"count": st["count"], "error": st["error"]}
        if events is not None and picked is not None and items is not None:
            row.update({
                "scored_events": scored_counts.get(sid, 0),
                "selected_events": selected_counts.get(sid, 0),
            })
        day_record[sid] = row
    days[date_str] = day_record
    for old in sorted(days)[:-HEALTH_KEEP_DAYS]:
        del days[old]
    health_file.write_text(json.dumps(health, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    recent = sorted(days, reverse=True)[:HEALTH_ALERT_DAYS]
    if len(recent) < HEALTH_ALERT_DAYS:
        return
    for sid, st in fetch_stats.items():
        if all(days[d].get(sid, {}).get("error") for d in recent):
            print(f"::warning::信源 {st['name']} ({sid}) "
                  f"已连续 {HEALTH_ALERT_DAYS} 天抓取失败，请检查 RSS 地址是否失效", flush=True)


# ----------------------------------------------------------------
# 7. 同步发布到博客（可选，永不自动 push）
# ----------------------------------------------------------------

def sync_news_data(src_data, dst_data):
    """以完整源目录替换目标数据树，避免保留已过期的派生文件。"""
    import shutil
    src_data = Path(src_data)
    dst_data = Path(dst_data)
    if not src_data.is_dir():
        raise FileNotFoundError(f"新闻数据目录不存在: {src_data}")

    staging = dst_data.with_name(f".{dst_data.name}.sync")
    backup = dst_data.with_name(f".{dst_data.name}.backup")
    shutil.rmtree(staging, ignore_errors=True)
    dst_data.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists() and not dst_data.exists():
        backup.replace(dst_data)
    if backup.exists() and dst_data.exists():
        shutil.rmtree(backup, ignore_errors=True)
    shutil.copytree(src_data, staging)
    switched = False
    try:
        if dst_data.exists():
            dst_data.replace(backup)
        staging.replace(dst_data)
        switched = True
    except Exception:
        if backup.exists() and not dst_data.exists():
            backup.replace(dst_data)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        if switched or dst_data.exists():
            shutil.rmtree(backup, ignore_errors=True)
    return sum(1 for path in dst_data.rglob("*") if path.is_file())


def publish_to_blog(cfg, date_str):
    import subprocess
    pub = cfg.get("publish") or {}
    blog_dir = (pub.get("blog_dir") or "").strip()
    if not blog_dir:
        return
    blog = Path(blog_dir)
    news_dir = blog / "source" / "news"
    if not blog.exists():
        log(f"发布跳过：博客目录不存在 {blog}")
        return
    dst_data = news_dir / "data"
    src_data = ROOT / "data"
    n = sync_news_data(src_data, dst_data)
    log(f"已同步 {n} 个数据文件到博客 source/news/data/")

    if pub.get("git_commit"):
        try:
            subprocess.run(["git", "add", "source/news/data"],
                           cwd=blog, check=True, capture_output=True)
            diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=blog)
            if diff.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", f"Update daily briefing data ({date_str})"],
                    cwd=blog, check=True, capture_output=True)
                log("博客已本地 commit（未 push，上线请手动 git push）")
            else:
                log("博客数据无变化，跳过 commit")
        except Exception as e:
            log(f"博客 git commit 失败（数据已同步，可手动提交）: {e}")


# ----------------------------------------------------------------
# 自建 RSSHub 占位符解析
# ----------------------------------------------------------------

def resolve_rsshub_sources(sources):
    """把 sources.yaml 里的 {rsshub} 占位符替换成自建实例地址并追加访问密钥。
    base/key 从环境变量 RSSHUB_BASE / RSSHUB_KEY 读取——公开仓库不落地址与密钥。
    未配置或配错 RSSHUB_BASE 时，带占位符的源自动跳过，不影响其余源。"""
    base = os.environ.get("RSSHUB_BASE", "").strip().rstrip("/")
    key = os.environ.get("RSSHUB_KEY", "").strip()
    # 只判空会漏掉「配错了」：缺协议前缀的 base 替换出的 URL 会让 requests 报
    # "No scheme supplied"，错误因此伪装成抓取失败而不是跳过，排查方向差一截
    # （2026-08-20 迁仓重配 secret 时六个自建源全灭）。base 是密钥，不进日志。
    reason = "未配置 RSSHUB_BASE 环境变量"
    if base and not base.startswith(("http://", "https://")):
        reason = "RSSHUB_BASE 缺少 http(s):// 前缀，按未配置处理"
        base = ""
    out = []
    for s in sources:
        url = s.get("url", "")
        if "{rsshub}" not in url:
            out.append(s)
            continue
        if not base:
            log(f"  ⚠ 跳过 {s['name']}：{reason}（自建 RSSHub 源）")
            continue
        resolved = url.replace("{rsshub}", base)
        if key:
            sep = "&" if "?" in resolved else "?"
            resolved = f"{resolved}{sep}key={key}"
        out.append({**s, "url": resolved})
    return out


# ----------------------------------------------------------------
# main
# ----------------------------------------------------------------

def main():
    """Run the managed pipeline.

    Ordering inside ``_run_pipeline`` is intentionally:
    audit_enrichment_support -> track_events -> write_brief -> write_output -> write_weekly.
    """
    started_at = time.perf_counter()
    args = parse_cli_args()

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    policy = resolve_run_policy(cfg, args)
    cfg["_objectivity_runtime_mode"] = policy["mode"]
    with managed_run_data_dir(policy):
        return _run_pipeline(started_at, args, cfg, policy)


def _run_pipeline(started_at, args, cfg, policy):

    # ---- 环境变量覆盖（供云端 CI 使用，本地运行无感知） ----
    if os.environ.get("PREFILTER_API_KEY", "").strip():
        cfg.setdefault("prefilter", {})["api_key"] = os.environ["PREFILTER_API_KEY"].strip()
    if os.environ.get("BLOG_DIR"):
        cfg.setdefault("publish", {})["blog_dir"] = os.environ["BLOG_DIR"]
    if os.environ.get("BLOG_GIT_COMMIT") == "0":
        cfg.setdefault("publish", {})["git_commit"] = False

    src_cfg = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    sources = [s for s in src_cfg["sources"] if s.get("enabled", True)]
    sources = resolve_rsshub_sources(sources)
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    items, fetch_stats = fetch_all(sources, cfg)
    if not items:
        log("没有抓到任何内容，退出。")
        sys.exit(1)

    # 舆论热榜（独立信号层）：dry-run 也拉取——CI 手动 dry-run 即可验证
    # 热榜接口从 GitHub Actions 出口 IP 是否可达
    pulse = fetch_pulse_all(src_cfg)

    if args.dry_run:
        log("dry-run 完成，各源状态：")
        for sid, st in sorted(fetch_stats.items(), key=lambda x: -x[1]["count"]):
            flag = "✗ 抓取失败" if st["error"] else ("- 窗口内无新文章" if st["count"] == 0 else "✓")
            print(f"    {st['name']}: {st['count']} 条 {flag}")
        for s in (src_cfg.get("pulse_sources") or []):
            if s.get("enabled", True):
                n = sum(1 for p in pulse
                        if p["platform"] in s.get("name", s.get("type", "")))
                print(f"    [热榜] {s.get('name', s['type'])}: {n} 条词条")
        return

    primary_llm_cfg = resolve_llm_config(cfg, "llm")
    if not str(primary_llm_cfg.get("api_key") or "").strip():
        env_name = str(primary_llm_cfg.get("api_key_env") or "provider API key")
        log(f"错误：请先设置 {env_name}")
        sys.exit(1)

    llm = LLM(primary_llm_cfg)
    configure_same_day_cost_guard(llm, cfg)
    audit_llm = LLM(resolve_llm_config(cfg, "audit_llm"))
    prefilter_llm = None

    # ---- 偏好学习输入：反馈与稍后读（缺失/损坏一律安全忽略） ----
    _data_dir = Path(os.environ["DATA_DIR"]) if os.environ.get("DATA_DIR") else ROOT / "data"
    dedup_cfg = cfg.get("news_dedup") or {}
    dedup_keep_days = int(dedup_cfg.get("seen_keep_days", 90))
    quality = new_quality_stats()
    news_seen = load_news_seen(_data_dir, date_str, dedup_keep_days)
    items = filter_cross_day_news(llm, items, news_seen, date_str, quality)
    if not items:
        log("跨日去重后没有新内容，退出。")
        return
    accepted_items = list(items)
    log(f"跨日去重：过滤 {quality['cross_day_duplicates']} 条，"
        f"重大更新 {quality['material_updates']} 条")

    # 全量轻档使用去重后的候选，重复旧闻不会出现在任何当日视图。
    try:
        write_all_archive(items, sources, date_str,
                          min_score=int(cfg.get("all_view_min_score", 40)))
    except Exception as e:
        log(f"  全量轻档写入失败（不影响主管线）: {e}")

    feedback = load_state_list(_data_dir, "feedback.json", "entries")
    read_later = load_state_list(_data_dir, "read_later.json", "items")
    pens = source_penalties(feedback, date_str)
    if pens:
        n_pen = 0
        for it in items:
            mult = pens.get(it["source"])
            if mult:
                it["credibility"] = it["credibility"] * mult
                n_pen += 1
        log(f"  来源降权：{pens}（影响 {n_pen} 条）")

    # 预筛：便宜模型先丢垃圾（未配置独立模型则复用主模型）
    pf_cfg = cfg.get("prefilter", {})
    if pf_cfg.get("enabled", False):
        merged = resolve_llm_config(cfg, "prefilter")
        if os.environ.get("PREFILTER_API_KEY", "").strip():
            merged["api_key"] = os.environ["PREFILTER_API_KEY"].strip()
        pf_model = merged["model"]
        log(f"预筛（{pf_model}）：过滤垃圾与无关条目 ...")
        prefilter_llm = LLM(merged)
        items = prefilter(prefilter_llm, items)

    log("阶段A：去重聚类 + 分类 + 五维打分 ...")
    events = triage(llm, items, quality)
    log(f"  聚成 {len(events)} 个事件")
    log("质量审计：复核多来源事件凝聚度 ...")
    events, quality = audit_event_cohesion(audit_llm, events, items, quality)
    log(f"  审计 {quality['audited_events']} 个事件，拆分 {quality['split_events']} 个")

    log("偏好学习：画像蒸馏 + 兴趣拟合 ...")
    profile = update_profile(llm, _data_dir, feedback, read_later)
    interest_fit(llm, profile, events,
                 span=cfg.get("scoring", {}).get("fit_span", 0.30))

    # co-occurrence 暗排序：热榜与真新闻事件重合 -> 公众热度 bonus（热榜不进条目）
    n_pulse = apply_pulse_bonus(events, items, pulse, cfg)
    if n_pulse:
        log(f"  公众热度加权：{n_pulse} 个事件命中热榜")

    registry_snapshot = load_registry(_data_dir)
    novelty_stats = new_cross_source_novelty_stats()
    novelty_hints = {}
    events, picked, secondary, threshold_info, selection_stats = \
        select_review_and_record(
            llm, audit_llm, events, items, cfg, _data_dir, date_str, quality,
            novelty_llm=audit_llm, registry=registry_snapshot,
            novelty_stats=novelty_stats, novelty_hints=novelty_hints)
    log(f"动态精选线：{threshold_info['threshold']} 分 "
        f"（{threshold_info['source']}，历史 {threshold_info['history_days']} 天）")
    append_github_selection_summary(selection_stats)
    shadow_selected = None

    if policy["full_objectivity"]:
        # 高风险单发布者事件只在本次已抓取、预筛前的原始池中寻找佐证；不开放搜索。
        corroborate_high_risk_events(picked, items, accepted_items, quality)
        log("证据采集：读取精选事件公开文章正文 ...")
        acquire_event_evidence(picked, items, quality)
        if quality["corroboration_matches"]:
            log(f"  原始池佐证：合并 {quality['corroboration_matches']} 条可信候选")
        log(f"  正文抓取：成功 {quality['article_fetch_successes']} / "
            f"尝试 {quality['article_fetch_attempts']}")
        if policy["mode"] == "shadow":
            # Snapshot membership before high-risk demotion; event objects remain live
            # so the summary still observes later repair/degradation results.
            shadow_selected = list(picked)
    else:
        # 分层材料等级（ADR 0020）：interim 只给得分最高的几条抓正文，其余留在摘要材料档。
        # 抓失败的条目 evidence_basis 保持 snippet，enrich 自动按摘要材料档处理，不多花钱。
        fetch_targets = fulltext_fetch_candidates(picked, cfg)
        if fetch_targets:
            log(f"证据采集：读取得分前 {len(fetch_targets)} 条精选的公开文章正文 ...")
            acquire_event_evidence(fetch_targets, items, quality)
            log(f"  正文抓取：成功 {quality['article_fetch_successes']} / "
                f"尝试 {quality['article_fetch_attempts']}")

    # 评分回填全量档（独立故障域）：让「全部动态」能按分数过滤
    try:
        backfill_all_scores(events, items, date_str)
    except Exception as e:
        log(f"  全量档评分回填失败（不影响主管线）: {e}")

    log(f"阶段B：精加工 {len(picked)} 条精选 ...")
    enrich(llm, picked, items, cfg, quality=quality)
    if quality.get("cause_evidence_rejected") or quality.get("cause_speculation_rejected"):
        log(f"  起因核对：清空 {quality['cause_evidence_rejected']} 条无法回溯、"
            f"{quality['cause_speculation_rejected']} 条未归因推测")
    log("质量审计：核对精加工内容的事实支撑 ...")
    run_audit_enrichment_support_stage(
        policy, audit_llm, picked, secondary, items, quality)
    for ev in secondary:
        ev.setdefault("status", "")
    # Final public sanitization must precede the registry snapshot so persisted
    # history matches the fields readers receive in active/shadow modes.
    prepare_events_for_output(picked, secondary, items, cfg)
    if policy["full_objectivity"]:
        finalize_detail_quality_metrics(picked, items, quality)
    log("事件登记表：跨天延续性匹配 ...")
    trajectory_health = new_trajectory_health()
    trajectory_review_cases = []
    registry = track_events(llm, picked, date_str, cfg,
                            secondary=secondary, feedback=feedback, items=items,
                            trajectory_audit_llm=audit_llm,
                            trajectory_health=trajectory_health,
                            trajectory_review_cases=trajectory_review_cases,
                            persist=False, quality=quality,
                            registry=registry_snapshot,
                            preferred_event_ids=novelty_hints)
    brief, themes = write_brief(
        llm, picked, secondary,
        audit_llm=audit_llm if policy["full_objectivity"] else None)

    log("深读频道：长文筛选 ...")
    deep = deep_channel(llm, cfg, date_str, profile)

    log("今日论文：HF Daily Papers 筛选 ...")
    papers = papers_channel(llm, cfg, date_str, profile)

    log("舆论观察：热榜传播机制解读 ...")
    opinion = opinion_pulse(llm, cfg, pulse, profile)

    _, publish_errors = write_output_and_commit_registry(
        date_str, brief, picked, secondary, items, cfg, registry,
        deep=deep, themes=themes, papers=papers, opinion=opinion,
        quality=quality)
    if publish_errors:
        log("校验失败：" + "; ".join(publish_errors) + "，中止发布。")
        sys.exit(2)

    try:
        update_quality_health(
            _data_dir, date_str, quality,
            include_rollout=policy["full_objectivity"],
            novelty_stats=novelty_stats)
    except Exception as e:
        log(f"  质量健康记录写入失败（不影响当日日报）: {e}")
    log("英语单词本：挑词 + 补全手动词 ...")
    build_vocab(llm, picked, items, date_str, cfg)

    # 公开生成在写入周综述前自动审修；shadow 不重复生成或审计同一周。
    run_weekly_stage(
        llm, audit_llm, date_str, cfg, _data_dir, profile, policy)

    update_source_health(fetch_stats, date_str, events=events, picked=picked, items=items)
    write_feed(_data_dir, date_str, cfg)
    update_search_index(_data_dir, date_str, cfg)

    finalize_selection_gate_metrics(selection_stats, picked, cfg)
    try:
        enrich_sample = build_enrich_sample(picked, date_str)
        emit_rollout_evidence(
            date_str, policy, time.perf_counter() - started_at,
            selection_stats, trajectory_health, trajectory_review_cases,
            _data_dir, cfg, enrich_sample=enrich_sample,
            enrich_review_cases=build_enrich_review_cases(
                picked, items, cfg, enrich_sample))
    except Exception as exc:
        log(f"  rollout evidence 写入失败（不影响当日日报）: {exc}")

    # 用量结算放在所有 LLM 阶段之后，shadow 运行同样打印——一天两次运行各花多少
    # 当天就能在 Actions 日志里对上。公开运行再把总额补写进健康记录（前面那次
    # update_quality_health 早于周综述等阶段，此处按同一日期整条覆盖）。
    run_usage = log_usage_report(
        [client for client in (llm, audit_llm, prefilter_llm) if client is not None])
    warn_if_cost_exceeds(run_usage, cfg, policy)
    if policy["writes_public_data"]:
        try:
            update_quality_health(
                _data_dir, date_str, quality,
                include_rollout=policy["full_objectivity"], usage=run_usage,
                novelty_stats=novelty_stats)
        except Exception as e:
            log(f"  用量记录写入失败（不影响当日日报）: {e}")

    if not policy["writes_public_data"]:
        summary = build_shadow_summary(
            shadow_selected or [], picked, items, quality,
            runtime_seconds=time.perf_counter() - started_at,
            usage=run_usage)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
        append_github_shadow_summary(summary)
        write_shadow_summary(summary)
        return

    save_news_seen(_data_dir, date_str, accepted_items, news_seen, dedup_keep_days)
    publish_to_blog(cfg, date_str)
    log("完成 ✓  访问 /news/ 查看今日日报")


if __name__ == "__main__":
    main()
