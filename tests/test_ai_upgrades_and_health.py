#!/usr/bin/env python3
"""
Unit tests for upgraded AI model cascades, HttpOptions millisecond fixes,
Groq/Mistral resilience & pacing, Tavily multi-account usage inspection,
and Telegram multi-account health alerts.
"""

import ast
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))
sys.path.insert(0, os.path.join(ROOT_DIR, "scripts"))

import ai_model_cascade
import independent_fact_checker
import tavily_search
import gemini_health_monitor


DEPRECATED_MODELS = {
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
}


class TestAIUpgradesAndHealth(unittest.TestCase):
    def test_no_seconds_passed_as_milliseconds_in_http_options(self):
        """Ensure no HttpOptions(timeout=...) across src/ or scripts/ passes < 1000ms literals."""
        offenders = []
        for folder in ("src", "scripts"):
            folder_path = os.path.join(ROOT_DIR, folder)
            for fname in sorted(os.listdir(folder_path)):
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(folder_path, fname)
                with open(fpath, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read(), filename=fpath)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func_name = ""
                        if isinstance(node.func, ast.Attribute):
                            func_name = node.func.attr
                        elif isinstance(node.func, ast.Name):
                            func_name = node.func.id
                        if func_name == "HttpOptions":
                            for kw in node.keywords:
                                if kw.arg == "timeout" and isinstance(kw.value, ast.Constant):
                                    val = kw.value.value
                                    if isinstance(val, (int, float)) and val < 1000:
                                        offenders.append(f"{folder}/{fname}:{node.lineno} timeout={val}")
        self.assertEqual(offenders, [], f"Found HttpOptions millisecond bugs: {offenders}")

    def test_active_model_lists_exclude_deprecated_models(self):
        """All active Gemini/Groq/Mistral cascades must use verified working quality-first models."""
        all_gemini = (
            list(ai_model_cascade.DEFAULT_GEMINI_MODELS)
            + list(ai_model_cascade.COMMENT_GEMINI_MODELS)
            + list(ai_model_cascade.FAST_GEMINI_MODELS)
            + list(ai_model_cascade.REVIEWER_GEMINI_MODELS)
            + [m for m, _ in gemini_health_monitor.ACTIVE_MODELS]
        )
        for model in all_gemini:
            self.assertNotIn(model, DEPRECATED_MODELS, f"Deprecated model {model} found in cascade")

        self.assertEqual(ai_model_cascade.DEFAULT_GEMINI_MODELS[0], "gemini-4-hydrogen")
        self.assertEqual(ai_model_cascade.COMMENT_GEMINI_MODELS[0], "gemini-4-hydrogen")
        self.assertIn("gemini-3.6-flash", ai_model_cascade.DEFAULT_GEMINI_MODELS)
        self.assertIn("gemini-3-flash-preview", ai_model_cascade.DEFAULT_GEMINI_MODELS)
        self.assertEqual(ai_model_cascade.FAST_GEMINI_MODELS[0], "gemini-3.5-flash-lite")
        self.assertEqual(ai_model_cascade.REVIEWER_GEMINI_MODELS[0], "gemini-3.6-flash")

        self.assertEqual(independent_fact_checker.GROQ_MODELS[0], "openai/gpt-oss-120b")
        self.assertIn("qwen/qwen3.8-27b", independent_fact_checker.GROQ_MODELS)
        self.assertIn("openai/gpt-oss-20b", independent_fact_checker.GROQ_MODELS)
        self.assertEqual(independent_fact_checker.MISTRAL_MODELS[0], "ministral-14b-latest")
        self.assertEqual(independent_fact_checker.MISTRAL_MODELS[1], "ministral-8b-latest")
        self.assertIn("codestral-latest", independent_fact_checker.MISTRAL_MODELS)

    def test_build_http_options_converts_seconds_to_ms_and_sets_v1beta(self):
        captured = {}

        class FakeHttpOptions:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        fake_types = SimpleNamespace(HttpOptions=FakeHttpOptions)
        opts = ai_model_cascade.build_http_options(fake_types, timeout_seconds=45.0, api_version="v1beta")
        self.assertIsNotNone(opts)
        self.assertEqual(captured["timeout"], 45000)
        self.assertEqual(captured["api_version"], "v1beta")

    def test_build_thinking_config_profiles(self):
        class FakeThinkingConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_types = SimpleNamespace(ThinkingConfig=FakeThinkingConfig)

        g4_fast_cfg = ai_model_cascade.build_thinking_config(fake_types, "gemini-4-hydrogen", fast_mode=True)
        self.assertEqual(g4_fast_cfg.kwargs, {"thinking_level": "LOW"})

        g4_budget_cfg = ai_model_cascade.build_thinking_config(fake_types, "gemini-4-hydrogen", budget=256)
        self.assertEqual(g4_budget_cfg.kwargs, {"thinking_level": "LOW"})

        g4_default_cfg = ai_model_cascade.build_thinking_config(fake_types, "gemini-4-hydrogen", fast_mode=False)
        self.assertIsNone(g4_default_cfg)

        g3_prev_fast_cfg = ai_model_cascade.build_thinking_config(fake_types, "gemini-3-flash-preview", fast_mode=True)
        self.assertIsNone(g3_prev_fast_cfg)

        flash35_cfg = ai_model_cascade.build_thinking_config(fake_types, "gemini-3.5-flash", fast_mode=True)
        self.assertEqual(flash35_cfg.kwargs["thinking_budget"], 0)

        lite_cfg = ai_model_cascade.build_thinking_config(fake_types, "gemini-3.5-flash-lite", fast_mode=True)
        self.assertIsNone(lite_cfg)

        flash36_cfg = ai_model_cascade.build_thinking_config(fake_types, "gemini-3.6-flash", fast_mode=True)
        self.assertGreater(flash36_cfg.kwargs["thinking_budget"], 0)

    def test_execute_with_model_cascade_skips_zero_limit_429_immediately(self):
        client = MagicMock()
        client.models.generate_content.side_effect = [
            Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for metric limit: 0"),
            SimpleNamespace(text="Risposta valida generata."),
        ]

        out, used = ai_model_cascade.execute_with_model_cascade(
            client=client,
            prompt="Test prompt",
            config=MagicMock(),
            preferred_models=["gemini-4-argon", "gemini-3.5-flash-lite"],
            task_name="unit_test",
            base_backoff_seconds=0.01,
        )
        self.assertEqual(used, "gemini-3.5-flash-lite")
        self.assertEqual(out, "Risposta valida generata.")
        # Fail-fast limit: 0 must not trigger 2 retries on gemini-4-argon -> only 2 total calls
        self.assertEqual(client.models.generate_content.call_count, 2)

    @patch("tavily_search.requests.get")
    def test_inspect_tavily_accounts_usage_reports_both_accounts(self, mock_get):
        resp_primary = MagicMock(status_code=200, text="{}")
        resp_primary.json.return_value = {
            "account": {"current_plan": "Bootstrap", "plan_usage": 1002, "plan_limit": 1000}
        }
        resp_secondary = MagicMock(status_code=200, text="{}")
        resp_secondary.json.return_value = {
            "account": {"current_plan": "Bootstrap", "plan_usage": 66, "plan_limit": 1000}
        }
        mock_get.side_effect = [resp_primary, resp_secondary]

        with patch.dict(
            os.environ,
            {
                "TAVILY_API_KEY": "tvly-dev-primary123E7Bb",
                "TAVILY_API_KEY_SECONDARY": "tvly-dev-second456yMSD",
            },
            clear=True,
        ):
            tavily_search._EXHAUSTED_KEYS.clear()
            accounts = tavily_search.inspect_tavily_accounts_usage()

        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0]["env_var"], "TAVILY_API_KEY")
        self.assertEqual(accounts[0]["status"], "quota_exceeded")
        self.assertIn("E7Bb", accounts[0]["masked_key"])
        self.assertNotIn("tvly-dev-primary123E7Bb", accounts[0]["masked_key"])

        self.assertEqual(accounts[1]["env_var"], "TAVILY_API_KEY_SECONDARY")
        self.assertEqual(accounts[1]["status"], "ok")
        self.assertEqual(accounts[1]["remaining"], 934)
        self.assertIn("yMSD", accounts[1]["masked_key"])

    @patch("independent_fact_checker.requests.post")
    def test_mistral_transient_429_rotates_without_disabling_session(self, mock_post):
        independent_fact_checker._MISTRAL_AVAILABLE = None
        independent_fact_checker._MISTRAL_COOLDOWN.clear()

        resp_429 = MagicMock(
            status_code=429,
            text='{"message": "Rate limit exceeded"}',
            headers={"x-ratelimit-limit-req-minute": "2"},
        )
        resp_200 = MagicMock(status_code=200)
        resp_200.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"decision": "APPROVE", "score": 92, "verified_text": "Mercato stabile.", "explanation": "OK"}'
                }
            }]
        }
        mock_post.side_effect = [resp_429, resp_200]

        res = independent_fact_checker.audit_with_mistral(
            "Mercato stabile.", session_name="US_CLOSE", api_key="test-mistral-key"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "APPROVE")
        self.assertEqual(mock_post.call_args_list[0].kwargs["json"]["model"], "ministral-14b-latest")
        self.assertEqual(res["auditor"], "mistral:ministral-8b-latest")
        self.assertTrue(independent_fact_checker._MISTRAL_AVAILABLE)

    @patch("independent_fact_checker.requests.post")
    def test_mistral_all_zero_rpm_disables_circuit_breaker(self, mock_post):
        independent_fact_checker._MISTRAL_AVAILABLE = None
        independent_fact_checker._MISTRAL_COOLDOWN.clear()

        resp_zero = MagicMock(
            status_code=429,
            text='{"message": "0 RPM"}',
            headers={"x-ratelimit-limit-req-minute": "0"},
        )
        mock_post.return_value = resp_zero

        res = independent_fact_checker.audit_with_mistral(
            "Mercato stabile.", session_name="US_CLOSE", api_key="test-mistral-key"
        )
        self.assertIsNone(res)
        self.assertFalse(independent_fact_checker._MISTRAL_AVAILABLE)
        # Clean reset so subsequent tests are unaffected
        independent_fact_checker._MISTRAL_AVAILABLE = None

    @patch("independent_fact_checker.requests.post")
    def test_groq_sends_low_reasoning_effort_for_gpt_oss(self, mock_post):
        independent_fact_checker._GROQ_COOLDOWN.clear()
        resp_200 = MagicMock(status_code=200)
        resp_200.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"decision": "APPROVE", "score": 90, "verified_text": "Testo OK", "explanation": "OK"}'
                }
            }]
        }
        mock_post.return_value = resp_200

        res = independent_fact_checker.audit_with_groq(
            "Testo OK", session_name="US_CLOSE", api_key="test-groq-key"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["auditor"], "groq:openai/gpt-oss-120b")
        sent_payload = mock_post.call_args_list[0].kwargs["json"]
        self.assertEqual(sent_payload.get("model"), "openai/gpt-oss-120b")
        self.assertEqual(sent_payload.get("reasoning_effort"), "low")
        self.assertEqual(sent_payload.get("max_tokens"), 1500)

    def test_health_monitor_telegram_report_shows_all_tavily_accounts_and_escapes_html(self):
        results = {
            m: {"status": "ok", "latency": 1200, "detail": "OK"}
            for m, _ in gemini_health_monitor.ACTIVE_MODELS
        }
        # Inject an error with <tags> to confirm HTML escaping works
        results["gemini-2.5-flash"] = {"status": "error", "latency": 500, "detail": "<xml>timeout & error</xml>"}

        tavily_accounts = [
            {
                "index": 1,
                "env_var": "TAVILY_API_KEY",
                "masked_key": "tvly-dev...E7Bb",
                "status": "quota_exceeded",
                "latency_ms": 180,
                "detail": "Crediti esauriti (1002/1000 usati, Bootstrap)",
            },
            {
                "index": 2,
                "env_var": "TAVILY_API_KEY_SECONDARY",
                "masked_key": "tvly-dev...yMSD",
                "status": "ok",
                "latency_ms": 140,
                "detail": "66/1000 usati (934 rimanenti, Bootstrap)",
            },
        ]

        msg = gemini_health_monitor.format_telegram_health_report(
            results=results,
            groq_results={"qwen/qwen3.8-27b": {"status": "ok", "latency": 310, "detail": "OK"}},
            mistral_results={"codestral-latest": {"status": "ok", "latency": 520, "detail": "OK"}},
            tavily_accounts=tavily_accounts,
            is_alert=False,
            ok_count=len(gemini_health_monitor.ACTIVE_MODELS) - 1,
            flash_quota_exceeded_count=0,
        )

        self.assertIn("TAVILY_API_KEY", msg)
        self.assertIn("tvly-dev...E7Bb", msg)
        self.assertIn("Crediti Esauriti", msg)
        self.assertIn("TAVILY_API_KEY_SECONDARY", msg)
        self.assertIn("tvly-dev...yMSD", msg)
        self.assertIn("934 rimanenti", msg)
        self.assertIn("Failover automatico attivo (1/2 account operativi)", msg)
        self.assertIn("&lt;xml&gt;timeout &amp; error&lt;/xml&gt;", msg)
        self.assertNotIn("<xml>", msg)

    @patch("gemini_health_monitor.telegram_sender.send_telegram_message")
    @patch("gemini_health_monitor.check_all_tavily_accounts")
    @patch("gemini_health_monitor.test_mistral_model")
    @patch("gemini_health_monitor.test_groq_model")
    @patch("gemini_health_monitor.test_model")
    @patch("gemini_health_monitor.time.sleep")
    def test_run_health_check_alert_only_when_all_tavily_exhausted(
        self, _mock_sleep, mock_gem, mock_groq, mock_mis, mock_tavily, mock_tg
    ):
        mock_gem.return_value = {"status": "ok", "latency": 800, "detail": "OK"}
        mock_groq.return_value = {"status": "ok", "latency": 300, "detail": "OK"}
        mock_mis.return_value = {"status": "ok", "latency": 500, "detail": "OK"}

        # Case 1: Account 1 exhausted, Account 2 active -> healthy failover, no alert unless notify_always
        mock_tavily.return_value = [
            {"index": 1, "env_var": "TAVILY_API_KEY", "masked_key": "tvly...1", "status": "quota_exceeded", "latency_ms": 100, "detail": "1002/1000"},
            {"index": 2, "env_var": "TAVILY_API_KEY_SECONDARY", "masked_key": "tvly...2", "status": "ok", "latency_ms": 100, "detail": "66/1000 (934 rimanenti)"},
        ]
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g", "GROQ_API_KEY": "gr", "MISTRAL_API_KEY": "m"}):
            rc1 = gemini_health_monitor.run_health_check(notify_always=False)
        self.assertEqual(rc1, 0)
        mock_tg.assert_not_called()

        # Case 2: BOTH Tavily accounts exhausted -> MUST alert Telegram immediately!
        mock_tavily.return_value = [
            {"index": 1, "env_var": "TAVILY_API_KEY", "masked_key": "tvly...1", "status": "quota_exceeded", "latency_ms": 100, "detail": "1002/1000"},
            {"index": 2, "env_var": "TAVILY_API_KEY_SECONDARY", "masked_key": "tvly...2", "status": "quota_exceeded", "latency_ms": 100, "detail": "1000/1000"},
        ]
        mock_tg.return_value = True
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g", "GROQ_API_KEY": "gr", "MISTRAL_API_KEY": "m"}):
            rc2 = gemini_health_monitor.run_health_check(notify_always=False)
        self.assertEqual(rc2, 0)
        mock_tg.assert_called_once()
        sent_msg = mock_tg.call_args[0][0]
        self.assertIn("ALLERTA STATO AI API", sent_msg)
        self.assertIn("TUTTI GLI ACCOUNT TAVILY ESAURITI", sent_msg)
        self.assertIn("TAVILY_API_KEY", sent_msg)
        self.assertIn("TAVILY_API_KEY_SECONDARY", sent_msg)


if __name__ == "__main__":
    unittest.main()
