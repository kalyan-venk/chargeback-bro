import pytest

from evals.run_evals import check_final_reply_equals, finish_evaluation


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
