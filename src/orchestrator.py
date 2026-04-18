import os
import dotenv

from langgraph.graph import StateGraph, START, END, add_messages
from typing import TypedDict, Annotated, Literal, Optional

from langchain_groq import ChatGroq

from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

from .prompts import orchestrator_prompt

from .tools import choose_subagent


dotenv.load_dotenv()


class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    subagent: Optional[Literal['coder']]


model = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.environ["GROQ_API_KEY"],
    reasoning_format='parsed',
).bind_tools([choose_subagent])


def call_llm(state: OrchestratorState) -> dict:
    response = model.invoke(state["messages"])
    return {'messages': [response]}


def call_user(state: OrchestratorState) -> dict:
    answer = interrupt(
        {"question": "What do you want your filthy slave to do?"}
    )
    return {"messages": [{"role": "user", "content": answer}]}


def invoke_subagent(state: OrchestratorState) -> dict:
    subagent_state = 

toolnode_choose_subagent = ToolNode([choose_subagent])

builder = StateGraph(OrchestratorState)

builder.add_node("llm", call_llm)
builder.add_node("user", call_user)
builder.add_node("toolnode_choose_subagent", toolnode_choose_subagent)
builder.add_node("subagent", invoke_subagent)










graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "orchestrator"}}


if __name__ == "__main__":
    graph.invoke(
        messages=[
            {
                "role": "system",
                "content": orchestrator_prompt
            },
        ],
        config=config,
    )

