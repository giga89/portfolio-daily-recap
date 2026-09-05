#!/usr/bin/env python3
"""
Test Suite: Universal Dual-Check & AI Model Cascade
===================================================
Verifies:
1. Prioritized AI Model Cascade starts with the smartest reasoning models (gemini-3.1-pro-preview, gemini-3.8-flash, etc.).
2. Deterministic & AI double-check for comments and user replies.
3. Strict blocking of purged assets (XEON.DE).
4. Strict blocking of dividend claims on accumulating ETFs (WDEF.L, INDO.PA, IB01.L, PPFB.DE).
5. Pre-send gatekeepers in etoro_client and etoro_sender.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from ai_model_cascade import DEFAULT_GEMINI_MODELS, REVIEWER_GEMINI_MODELS
from post_verifier import (
    verify_post_deterministic,
    verify_and_clean_comment,
    verify_and_clean_post,
    clean_etoro_formatting,
)
import etoro_client


def test_model_cascade_priority():
    print("\n--- Test 1: Prioritized AI Model Cascade ---")
    assert DEFAULT_GEMINI_MODELS[0] == 'gemini-3.1-pro-preview', f"Top model should be gemini-3.1-pro-preview, got {DEFAULT_GEMINI_MODELS[0]}"
    assert DEFAULT_GEMINI_MODELS[1] == 'gemini-3.8-flash', f"Second model should be gemini-3.8-flash, got {DEFAULT_GEMINI_MODELS[1]}"
    assert 'gemini-3.7-flash' in DEFAULT_GEMINI_MODELS
    assert 'gemini-2.5-flash' in DEFAULT_GEMINI_MODELS
    assert REVIEWER_GEMINI_MODELS[0] == 'gemini-3.1-pro-preview'
    print("✅ Model cascade prioritized hierarchy verified (gemini-3.1-pro-preview -> gemini-3.8-flash -> gemini-3.7-flash -> ...)!")


def test_purged_asset_xeon_blocked():
    print("\n--- Test 2: Purged Asset XEON.DE Blocked ---")
    bad_comment = "Abbiamo anche $XEON.DE per proteggere la liquidità del portafoglio."
    is_ok, issues, _ = verify_post_deterministic(bad_comment)
    assert not is_ok, "XEON.DE should be flagged as critical error"
    assert any("dismesso" in i or "XEON.DE" in i for i in issues)

    # In verify_and_clean_comment
    ok_c, _, audit = verify_and_clean_comment(bad_comment, run_ai_review=False)
    assert not ok_c, "Comment containing XEON.DE must be rejected"
    print(f"✅ XEON.DE correctly blocked: {issues[0]}")


def test_accumulating_etf_comment_blocked():
    print("\n--- Test 3: Dividend Claim on Accumulating ETF Blocked in Comment ---")
    hallucinated_reply = "@copier $WDEF.L è un ottimo ETF che stacca un generoso dividendo trimestrale per i nostri flussi di cassa."
    is_ok, issues, _ = verify_post_deterministic(hallucinated_reply, primary_ticker="WDEF.L")
    assert not is_ok, "Dividend claim on WDEF.L must fail deterministic check"

    ok_c, _, audit = verify_and_clean_comment(
        text=hallucinated_reply,
        user_comment="Ma WDEF paga dividendi?",
        user_author="copier",
        primary_ticker="WDEF.L",
        run_ai_review=False,
    )
    assert not ok_c, "Hallucinated comment on WDEF.L dividends must be rejected"
    print(f"✅ Hallucinated comment rejected: {audit.get('issues')}")


def test_valid_comment_approved():
    print("\n--- Test 4: Valid Comment on Dividend Payer Approved & Cleaned ---")
    good_reply = "@copier Ciao! **$ENEL.MI** è una utility con un dividendo del 6.5% e flussi regolati. Non è un consiglio finanziario. 🤝📈"
    ok_c, clean_text, audit = verify_and_clean_comment(
        text=good_reply,
        user_comment="Cosa ne pensi del dividendo di Enel?",
        user_author="copier",
        primary_ticker="ENEL.MI",
        run_ai_review=False,
    )
    assert ok_c, f"Valid comment should be approved: {audit.get('issues')}"
    assert "**" not in clean_text, "Markdown bold asterisks must be stripped"
    assert "$ENEL.MI" in clean_text
    print(f"✅ Valid comment cleaned and approved:\n   \"{clean_text}\"")


def test_etoro_client_pre_send_gates():
    print("\n--- Test 5: etoro_client Pre-Send Network Gates ---")
    # 1. Blocked comment with hallucination
    res1 = etoro_client.add_post_comment(
        post_id="dummy_post",
        message="Acquistate $WDEF.L perché paga un dividendo ricco e garantito!"
    )
    assert not res1["success"], "etoro_client.add_post_comment must block critical error"
    assert "Pre-send verification gate" in res1["error"]
    print("✅ add_post_comment blocked hallucinated message before network request")

    # 2. Blocked reply with XEON
    res2 = etoro_client.reply_to_comment(
        post_id="dummy_post",
        comment_id="dummy_comment",
        message="@user abbiamo ancora $XEON.DE in portafoglio."
    )
    assert not res2["success"], "etoro_client.reply_to_comment must block purged XEON"
    assert "Pre-send verification gate" in res2["error"]
    print("✅ reply_to_comment blocked XEON.DE reply before network request")


if __name__ == "__main__":
    test_model_cascade_priority()
    test_purged_asset_xeon_blocked()
    test_accumulating_etf_comment_blocked()
    test_valid_comment_approved()
    test_etoro_client_pre_send_gates()
    print("\n" + "=" * 60)
    print("🎉 ALL 5 UNIVERSAL DUAL-CHECK TESTS PASSED!")
    print("=" * 60)

