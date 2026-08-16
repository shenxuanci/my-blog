import importlib.util
import sys
import types
from pathlib import Path

import pytest
import requests
import yaml


PIPELINE_DIR = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "daily_news_llm_protocol_test", PIPELINE_DIR / "daily_news.py")
dn = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dn
spec.loader.exec_module(dn)


def test_repository_defaults_to_deepseek_and_keeps_stepfun_available():
    config = yaml.safe_load(
        (PIPELINE_DIR / "config.yaml").read_text(encoding="utf-8"))

    assert config["llm"]["active_provider"] == "deepseek"
    assert config["llm"]["providers"]["deepseek"]["protocol"] == "openai"
    assert config["llm"]["providers"]["deepseek"]["extra_body"] == {
        "thinking": {"type": "disabled"},
    }
    assert config["llm"]["providers"]["stepfun"]["protocol"] == "anthropic"


def provider_config(active="stepfun"):
    return {
        "llm": {
            "active_provider": active,
            "providers": {
                "stepfun": {
                    "protocol": "anthropic",
                    "base_url": "https://api.stepfun.com/v1/",
                    "api_key_env": "STEPFUN_API_KEY",
                    "model": "step-explore",
                    "max_tokens": 16384,
                    "max_retries": 3,
                    "request_timeout": [10, 180],
                    "price_usd_per_mtok": {
                        "input_miss": 0,
                        "input_hit": 0,
                        "output": 0,
                    },
                },
                "deepseek": {
                    "protocol": "openai",
                    "base_url": "https://api.deepseek.com/v1",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "model": "deepseek-v4-flash",
                    "temperature": 0.3,
                    "max_retries": 3,
                    "extra_body": {"thinking": {"type": "disabled"}},
                    "price_usd_per_mtok": {
                        "input_miss": 0.14,
                        "input_hit": 0.0028,
                        "output": 0.28,
                    },
                },
            },
        },
        "audit_llm": {"provider": "", "model": ""},
        "prefilter": {"enabled": True, "provider": "", "model": ""},
    }


def test_named_provider_resolves_its_secret_and_role_inheritance():
    cfg = provider_config()
    environ = {
        "STEPFUN_API_KEY": "step-secret",
        "DEEPSEEK_API_KEY": "deepseek-secret",
    }

    primary = dn.resolve_llm_config(cfg, "llm", environ=environ)
    audit = dn.resolve_llm_config(cfg, "audit_llm", environ=environ)
    prefilter = dn.resolve_llm_config(cfg, "prefilter", environ=environ)

    assert primary["provider"] == "stepfun"
    assert primary["api_key"] == "step-secret"
    assert audit["provider"] == "stepfun"
    assert audit["api_key"] == "step-secret"
    assert prefilter["provider"] == "stepfun"
    assert prefilter["api_key"] == "step-secret"
    assert "providers" not in primary

    cfg["llm"]["active_provider"] = "deepseek"
    fallback = dn.resolve_llm_config(cfg, "llm", environ=environ)
    assert fallback["provider"] == "deepseek"
    assert fallback["api_key"] == "deepseek-secret"


def test_named_provider_rejects_missing_or_unknown_active_provider():
    cfg = provider_config()
    cfg["llm"]["active_provider"] = ""
    with pytest.raises(ValueError, match="active_provider"):
        dn.resolve_llm_config(cfg, environ={})

    cfg["llm"]["active_provider"] = "missing"
    with pytest.raises(ValueError, match="missing"):
        dn.resolve_llm_config(cfg, environ={})


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


def anthropic_payload(text='{"ok":true}', *, stop_reason="end_turn", usage=None):
    return {
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "usage": usage or {"input_tokens": 20, "output_tokens": 12},
    }


def test_anthropic_json_call_uses_stepfun_contract_and_normalizes_usage(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(payload=anthropic_payload(
            usage={
                "input_tokens": 20,
                "cache_read_input_tokens": 5,
                "cache_creation_input_tokens": 3,
                "output_tokens": 12,
            }))

    monkeypatch.setattr(dn.requests, "post", fake_post)
    cfg = dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"})
    llm = dn.LLM(cfg)

    assert llm.json_call("system prompt", "user prompt") == {"ok": True}
    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://api.stepfun.com/v1/messages"
    assert kwargs["timeout"] == (10, 180)
    assert kwargs["headers"] == {
        "x-api-key": "secret",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    assert kwargs["json"] == {
        "model": "step-explore",
        "max_tokens": 16384,
        "system": "system prompt",
        "messages": [{"role": "user", "content": "user prompt"}],
    }
    assert "temperature" not in kwargs["json"]
    assert "thinking" not in kwargs["json"]
    assert "extra_body" not in kwargs["json"]
    assert llm.stage_usage["OTHER"] == {
        "calls": 1,
        "input": 28,
        "input_cached": 5,
        "output": 12,
    }


def test_anthropic_retries_retryable_status_with_retry_after(monkeypatch):
    responses = [
        FakeResponse(429, text="rate limited", headers={"retry-after": "7"}),
        FakeResponse(payload=anthropic_payload()),
    ]
    sleeps = []
    monkeypatch.setattr(dn.requests, "post", lambda *a, **k: responses.pop(0))
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    assert llm.json_call("system", "user") == {"ok": True}
    assert sleeps == [7.0]


def test_json_parse_failure_is_metered_but_not_retried(monkeypatch):
    responses = [FakeResponse(payload=anthropic_payload("not json"))]
    sleeps = []
    monkeypatch.setattr(dn.requests, "post", lambda *a, **k: responses.pop(0))
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    with pytest.raises(RuntimeError, match="no JSON"):
        llm.json_call("system", "user")
    assert sleeps == []
    assert llm.stage_usage["OTHER"]["calls"] == 1


@pytest.mark.parametrize("status", [400, 401, 402, 404, 451])
def test_anthropic_does_not_retry_terminal_http_status(monkeypatch, status):
    calls = []
    sleeps = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(status, text="terminal")

    monkeypatch.setattr(dn.requests, "post", fake_post)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    with pytest.raises(RuntimeError, match=str(status)):
        llm.json_call("system", "user")
    assert len(calls) == 1
    assert sleeps == []


def test_anthropic_timeout_and_truncation_share_attempt_budget_and_record_usage(
        monkeypatch):
    responses = [
        requests.ReadTimeout("slow"),
        FakeResponse(payload=anthropic_payload(
            "incomplete", stop_reason="max_tokens",
            usage={"input_tokens": 11, "output_tokens": 16384})),
        FakeResponse(payload=anthropic_payload()),
    ]
    sleeps = []

    def fake_post(*args, **kwargs):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(dn.requests, "post", fake_post)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    assert llm.json_call("system", "user") == {"ok": True}
    assert sleeps == [1, 2]
    assert llm.stage_usage["OTHER"]["calls"] == 2
    assert llm.stage_usage["OTHER"]["output"] == 16396


def test_stage_classifier_handles_formatted_prompts_without_prefix_false_positive():
    formatted = dn.ENRICH_SYSTEM.format(
        tag_list="AI", detail_field="", detail_json="",
        context_limit=80, context_depth="证据不足可留空",
        watch_field="", watch_json="",
        watch_detail_field="", watch_detail_json="")

    assert dn.stage_of_prompt(dn.TRIAGE_SYSTEM) == "TRIAGE_SYSTEM"
    assert dn.stage_of_prompt(formatted) == "ENRICH_SYSTEM"
    assert dn.stage_of_prompt(
        dn.TRIAGE_SYSTEM[:40] + "这不是阶段 A 的提示词") == "OTHER"


@pytest.mark.parametrize("payload", [
    {"stop_reason": "end_turn", "usage": {"input_tokens": 2, "output_tokens": 1}},
    anthropic_payload(""),
])
def test_anthropic_does_not_retry_malformed_success_response(monkeypatch, payload):
    calls = []
    sleeps = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(payload=payload)

    monkeypatch.setattr(dn.requests, "post", fake_post)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    with pytest.raises(RuntimeError):
        llm.json_call("system", "user")
    assert len(calls) == 1
    assert sleeps == []


def test_unexpected_internal_error_is_not_retried(monkeypatch):
    calls = []
    sleeps = []
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    def fail(*args, **kwargs):
        calls.append(1)
        raise AttributeError("unexpected response shape")

    monkeypatch.setattr(llm, "_complete", fail)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)

    with pytest.raises(RuntimeError, match="unexpected response shape"):
        llm.text_call("system", "user")
    assert len(calls) == 1
    assert sleeps == []


def test_same_day_reconciliation_does_not_retry_a_paid_request(monkeypatch):
    calls = []
    sleeps = []
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))

    def fail(*args, **kwargs):
        calls.append(1)
        raise dn.LLMCallError("temporary", retryable=True)

    monkeypatch.setattr(llm, "_complete", fail)
    monkeypatch.setattr(dn.time, "sleep", sleeps.append)

    with pytest.raises(RuntimeError, match="temporary"):
        llm.json_call(dn.SAME_DAY_RECONCILE_SYSTEM, "[]")

    assert len(calls) == 1
    assert sleeps == []


def test_text_call_uses_shared_transport_and_openai_keeps_request_options(monkeypatch):
    seen = []
    client_options = []

    class Completions:
        @staticmethod
        def create(**kwargs):
            seen.append(kwargs)
            message = types.SimpleNamespace(content="profile markdown")
            choice = types.SimpleNamespace(message=message, finish_reason="stop")
            usage = types.SimpleNamespace(
                prompt_tokens=9, prompt_cache_hit_tokens=4, completion_tokens=3)
            return types.SimpleNamespace(choices=[choice], usage=usage)

    class OpenAI:
        def __init__(self, **kwargs):
            client_options.append(kwargs)
            self.chat = types.SimpleNamespace(completions=Completions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(
        OpenAI=OpenAI,
        Timeout=lambda timeout, *, connect: (timeout, connect),
    ))
    cfg = dn.resolve_llm_config(
        provider_config("deepseek"),
        environ={"DEEPSEEK_API_KEY": "deep-secret"},
    )
    llm = dn.LLM(cfg)

    assert llm.text_call("profile system", "profile user", temperature=0.2) == (
        "profile markdown")
    assert client_options == [{
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "deep-secret",
        "max_retries": 0,
        "timeout": (180.0, 10.0),
    }]
    assert seen == [{
        "model": "deepseek-v4-flash",
        "temperature": 0.2,
        "max_tokens": 16384,
        "messages": [
            {"role": "system", "content": "profile system"},
            {"role": "user", "content": "profile user"},
        ],
        "extra_body": {"thinking": {"type": "disabled"}},
    }]
    assert llm.stage_usage["OTHER"] == {
        "calls": 1,
        "input": 9,
        "input_cached": 4,
        "output": 3,
    }


def test_openai_usage_reads_standard_nested_cached_tokens():
    usage = types.SimpleNamespace(
        prompt_tokens=21,
        prompt_tokens_details=types.SimpleNamespace(cached_tokens=8),
        completion_tokens=5,
    )

    assert dn.LLM._openai_usage(usage) == {
        "input": 21,
        "input_cached": 8,
        "output": 5,
    }


def test_retry_meter_adds_every_response_that_reports_usage(monkeypatch):
    llm = dn.LLM(dn.resolve_llm_config(
        provider_config(), environ={"STEPFUN_API_KEY": "secret"}))
    attempts = iter([
        dn.LLMCallError(
            "truncated",
            retryable=True,
            usage={"input": 30, "input_cached": 10, "output": 16},
        ),
        ('{"ok":true}', {"input": 25, "input_cached": 5, "output": 4}),
    ])

    def complete(*args, **kwargs):
        result = next(attempts)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(llm, "_complete", complete)
    monkeypatch.setattr(dn.time, "sleep", lambda _delay: None)

    assert llm.json_call(dn.TRIAGE_SYSTEM, "user") == {"ok": True}
    assert llm.stage_usage["TRIAGE_SYSTEM"] == {
        "calls": 2,
        "input": 55,
        "input_cached": 15,
        "output": 20,
    }


def test_cost_clamps_cached_tokens_to_total_input():
    price = {"input_miss": 1.0, "input_hit": 0.1, "output": 2.0}

    assert dn.usage_cost_usd({
        "input": 10,
        "input_cached": 20,
        "output": 0,
    }, price) == pytest.approx(1 / 1_000_000)


@pytest.mark.parametrize("price", [
    {"input_miss": 1.0, "output": 2.0},
    {"input_miss": 1.0, "input_hit": "invalid", "output": 2.0},
    {"input_miss": -1.0, "input_hit": 0.1, "output": 2.0},
])
def test_invalid_price_configuration_marks_cost_unknown(price):
    assert dn.usage_cost_usd({
        "input": 10,
        "input_cached": 2,
        "output": 1,
    }, price) is None


def test_usage_report_keeps_model_identity_and_marks_unknown_cost():
    known = types.SimpleNamespace(
        provider="stepfun",
        model="step-explore",
        price_usd_per_mtok={"input_miss": 0, "input_hit": 0, "output": 0},
        stage_usage={"TRIAGE_SYSTEM": {
            "calls": 1, "input": 100, "input_cached": 0, "output": 20}},
    )
    unknown = types.SimpleNamespace(
        provider="other",
        model="future-model",
        price_usd_per_mtok=None,
        stage_usage={"TRIAGE_SYSTEM": {
            "calls": 1, "input": 50, "input_cached": 0, "output": 10}},
    )

    merged = dn.merge_usage([known, unknown])
    assert set(merged) == {
        ("stepfun", "step-explore", "TRIAGE_SYSTEM"),
        ("other", "future-model", "TRIAGE_SYSTEM"),
    }
    totals = dn.usage_totals(merged)
    assert totals["llm_calls"] == 2
    assert totals["llm_cost_usd"] is None
    assert totals["llm_cost_known"] is False


def test_usage_report_merges_multiple_clients_with_the_same_identity():
    price = {"input_miss": 1.0, "input_hit": 0.1, "output": 2.0}
    clients = [
        types.SimpleNamespace(
            provider="deepseek",
            model="shared-model",
            price_usd_per_mtok=price,
            stage_usage={"TRIAGE_SYSTEM": {
                "calls": 1, "input": 100, "input_cached": 20, "output": 10}},
        ),
        types.SimpleNamespace(
            provider="deepseek",
            model="shared-model",
            price_usd_per_mtok=price,
            stage_usage={"TRIAGE_SYSTEM": {
                "calls": 2, "input": 50, "input_cached": 5, "output": 4}},
        ),
    ]

    merged = dn.merge_usage(clients)

    assert merged[("deepseek", "shared-model", "TRIAGE_SYSTEM")] == {
        "calls": 3,
        "input": 150,
        "input_cached": 25,
        "output": 14,
        "price_usd_per_mtok": price,
    }
    assert dn.usage_totals(merged) == {
        "llm_calls": 3,
        "llm_input_tokens": 150,
        "llm_cached_input_tokens": 25,
        "llm_output_tokens": 14,
        "llm_cost_usd": 0.0002,
        "llm_cost_known": True,
    }


def test_usage_report_marks_conflicting_prices_for_same_identity_unknown():
    clients = [
        types.SimpleNamespace(
            provider="deepseek",
            model="shared-model",
            price_usd_per_mtok={
                "input_miss": 1.0, "input_hit": 0.1, "output": 2.0},
            stage_usage={"TRIAGE_SYSTEM": {
                "calls": 1, "input": 100, "input_cached": 20, "output": 10}},
        ),
        types.SimpleNamespace(
            provider="deepseek",
            model="shared-model",
            price_usd_per_mtok={
                "input_miss": 2.0, "input_hit": 0.2, "output": 4.0},
            stage_usage={"TRIAGE_SYSTEM": {
                "calls": 1, "input": 50, "input_cached": 5, "output": 4}},
        ),
    ]

    merged = dn.merge_usage(clients)

    assert merged[
        ("deepseek", "shared-model", "TRIAGE_SYSTEM")
    ]["price_usd_per_mtok"] is None
    assert dn.usage_totals(merged)["llm_cost_known"] is False


def test_cost_guard_warns_without_blocking_when_mode_limit_is_exceeded(capsys):
    cfg = {
        "cost_guard": {
            "generate_warn_usd": 0.06,
            "shadow_warn_usd": 0.09,
        },
    }
    usage = {"llm_cost_usd": 0.08, "llm_cost_known": True}

    warned = dn.warn_if_cost_exceeds(
        usage, cfg, {"mode": "interim", "writes_public_data": True})

    assert warned is True
    assert "::warning::" in capsys.readouterr().out
    assert dn.warn_if_cost_exceeds(
        usage, cfg, {"mode": "shadow", "writes_public_data": False}) is False
