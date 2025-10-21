from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from typing import TypedDict

class State(MessagesState):
    customer_name: str
    my_age: int


def node (state: State):
    if state.get("customer_name") is None:
        return {"customer_name": "John Doe"}
    else:
        ai_msg = AIMessage(content=f"Hello {state['customer_name']}, how can I assist you today?")
        return {
            "messages": [ai_msg]
        }

state: State = {}
customer_name = state.get("customer_name", None)
print(f"Customer name is: {customer_name}")

builder = StateGraph(State)
builder.add_node("node", node)

builder.add_edge(START, "node")
builder.add_edge("node", END)

agent = builder.compile()

ai_msg = AIMessage(content="Hello, I am an AI")
ai_msg.text

human_msg = HumanMessage(content="Hello, I am a human")
human_msg.text

history = [human_msg, ai_msg]
for msg in history:
    msg.pretty_print()


