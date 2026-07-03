import operator
from typing import Annotated, Literal, TypedDict

Source = Literal["web", "knowledge_base", "pdf"]


class Classification(TypedDict):
    source: Source
    query: str


class AgentInput(TypedDict):
    trace_id: str
    query: str
    conversation_context: str


class AgentOutput(TypedDict):
    source: str
    result: str


class RouterState(TypedDict):
    trace_id: str
    query: str
    conversation_context: str
    classifications: list[Classification]
    results: Annotated[list[AgentOutput], operator.add]
    final_answer: str
