from dataclasses import dataclass
from typing import Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, object]


@dataclass
class ModelTurn:
    text: str
    tool_calls: list[ToolCall]


class LLMProvider(Protocol):
    async def generate(self,
                       messages: list[dict[str, object]],
                       system_prompt: str,
                       tools: list[dict[str, object]]
                       ) -> ModelTurn:
        ...

class FakeLLMProvider:
    def __init__(self, prepared_turns: list[ModelTurn]) -> None:
        self.prepared_turns = prepared_turns.copy()

    async def generate(self, messages: list[dict[str, object]], system_prompt: str,
                       tools: list[dict[str, object]]
                       ) -> ModelTurn:
        if not self.prepared_turns:
            raise RuntimeError("No prepared model turns remain.")
        return self.prepared_turns.pop(0)