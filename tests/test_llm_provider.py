import pytest

from app.llm_provider import FakeLLMProvider, ModelTurn, ToolCall


def test_model_turn_compares_by_its_data():
    tool_call1 = ToolCall("call_1", "score_fraud", {"transaction_id": 42})
    actual_model_turn = ModelTurn("", [tool_call1])

    tool_call2 = ToolCall("call_1", "score_fraud", {"transaction_id": 42})
    expected_model_turn = ModelTurn("", [tool_call2])

    assert actual_model_turn == expected_model_turn


@pytest.mark.asyncio
async def test_fake_provider_returns_prepared_turn():
    model_turn1 = ModelTurn("Your dispute has been filed.", [])

    fake_llm_provider = FakeLLMProvider([model_turn1])
    returned_turn = await fake_llm_provider.generate([], "", [])
    assert returned_turn == model_turn1


@pytest.mark.asyncio
async def test_fake_provider_returns_prepared_turns_in_order():
    tool_call = ToolCall("call_1", "look_up_transactions", {"amount": 25})

    turn_1 = ModelTurn("", [tool_call])
    turn_2 = ModelTurn("Your dispute has been filed.", [])

    fake_llm_provider = FakeLLMProvider([turn_1, turn_2])

    returned_turn_1 = await fake_llm_provider.generate([], "", [])
    returned_turn_2 = await fake_llm_provider.generate([], "", [])
    # These fake turns ignore the arguments - messages, system prompt and tools. Real Azure will use them.

    assert returned_turn_1 == turn_1
    assert returned_turn_2 == turn_2


@pytest.mark.asyncio
async def test_fake_provider_raises_runtime_error_when_no_prepared_turns_remain():
    fake_llm_provider = FakeLLMProvider([])
    with pytest.raises(RuntimeError, match="No prepared model turns remain"):
        await fake_llm_provider.generate([], "", [])