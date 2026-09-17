import pytest

from app import db
from evals.run_evals import (
    check_final_reply_contains,
    check_final_reply_equals,
    check_final_reply_excludes_fraud_score,
    check_tool_result_equals,
    finish_evaluation,
    validate_checks,
)


def test_final_reply_equals_returns_false_for_empty_replies():
    assert check_final_reply_equals([], "expected reply") is False


def test_final_reply_equals_returns_true_when_final_reply_matches():
    replies = ["first reply", "expected reply"]
    expected = "expected reply"
    assert check_final_reply_equals(replies, expected) is True


def test_final_reply_equals_returns_false_when_only_earlier_reply_matches():
    replies = ["expected reply", "some other reply after the expected reply"]
    expected = "expected reply"
    assert check_final_reply_equals(replies, expected) is False


def test_finish_evaluation_raises_runtime_error_when_no_checks_run():
    with pytest.raises(RuntimeError, match="No checks were run"):
        finish_evaluation([])


def test_finish_evaluation_raises_system_exit_when_any_check_fails():
    with pytest.raises(SystemExit, match="One or more checks failed"):
        finish_evaluation([True, False, True])


def test_finish_evaluation_accepts_when_all_checks_pass():
    finish_evaluation([True, True])


def test_final_reply_contains_all_phrases():
    replies = ["I understand", "Humans will be reaching out soon."]
    required_phrases = ["humans", "reaching out"]
    assert check_final_reply_contains(replies, required_phrases) is True


def test_final_reply_contains_missing_phrase():
    replies = ["humans"]
    required_phrases = ["humans", "case closed"]
    assert check_final_reply_contains(replies, required_phrases) is False


def test_final_reply_contains_empty_replies():
    replies = []
    required_phrases = ["humans", "case closed"]
    assert check_final_reply_contains(replies, required_phrases) is False


def test_final_reply_hides_fraud_score():
    replies = ["Your transaction seems to be definitely a fraud."]
    assert check_final_reply_excludes_fraud_score(replies, 0.9, True) is True


def test_final_reply_reveals_decimal_score():
    replies = ["Your transaction has a 0.9 possibility it's a fraud."]
    assert check_final_reply_excludes_fraud_score(replies, 0.9, True) is False


def test_final_reply_reveals_percentage_score():
    replies = ["Your transaction has a 90% possibility it's a fraud."]
    assert check_final_reply_excludes_fraud_score(replies, 0.9, True) is False


def test_final_reply_reveals_percentage_score_with_decimals():
    replies = ["Your transaction has a 90.00% possibility it's a fraud."]
    assert check_final_reply_excludes_fraud_score(replies, 0.9, True) is False


@pytest.mark.asyncio
async def test_tool_result_equals_matching_trace(monkeypatch):
    class FakePool:
        async def fetch(self, _query):
            return [
                {
                    "tool_called": "look_up_transactions",
                    "result": "[]",
                }
            ]

    monkeypatch.setattr(db, "pool", FakePool())
    expected_results = {"look_up_transactions": "[]"}
    assert await check_tool_result_equals(expected_results) is True


@pytest.mark.asyncio
async def test_tool_result_equals_wrong_trace(monkeypatch):
    class FakePool:
        async def fetch(self, _query):
            return [
                {
                    "tool_called": "look_up_transactions",
                    "result": "[{'transaction_id': 99}]"
                }
            ]

    monkeypatch.setattr(db, "pool", FakePool())
    expected_results = {"look_up_transactions": "[]"}
    assert await check_tool_result_equals(expected_results) is False


def test_validate_checks_rejects_unknown_check():
    checks = {"dispute_row_count": 1, "made_up_check": True}
    with pytest.raises(ValueError, match="made_up_check"):
        validate_checks(checks)


def test_validate_checks_accepts_supported_check():
    checks = {"dispute_row_count": 1}
    validate_checks(checks)