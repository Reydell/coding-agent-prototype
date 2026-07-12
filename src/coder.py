import os
import dotenv

from langgraph.graph import StateGraph, START, END, add_messages
from typing import TypedDict, Annotated, Literal, Optional
from langchain_core.messages import HumanMessage, SystemMessage

from langchain_groq import ChatGroq

from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition

from langgraph.types import interrupt, Command

from .tools import grep, read_file, stage_diff, apply_diff

from .utils import draw_mermaid, red
from .prompts import coder_prompt

import argparse

import logging
logger = logging.getLogger(__name__)

dotenv.load_dotenv()


class Diff(TypedDict):
    path: str
    line_number: int
    line_text: str


class EditResult(TypedDict):
    status: str
    path: str
    line_number: int
    old_text: str
    new_text: str


class CoderState(TypedDict):
    messages: Annotated[list, add_messages]
    is_done: bool = False
    diff: Diff = {}
    edit_result: EditResult


model = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.environ["GROQ_API_KEY"],
    reasoning_format='parsed'
).bind_tools(
    [grep, read_file, stage_diff],
    parallel_tool_calls=False,
)


def call_llm(state: CoderState) -> dict:
    try:
        response = model.invoke(state["messages"])
        return {"messages": [response]}
    except Exception as e:
        logger.error(e)
        return {
            "messages": [
                HumanMessage(
                    content=f"Your last tool call was rejected by the provider: {e}. Retry with valid JSON args only."
                )
            ]
        }

def call_llm_final(state: CoderState) -> dict:
    response = model.invoke(state["messages"])
    print(response.text)
    print()
    return {"messages": [response]}


def ask_confirmation(state: CoderState) -> str:
    bool_confirm = interrupt({
        "kind": "confirm",
        "diff": state["diff"]
    })
    if bool_confirm:
        return "__confirm__"
    else:
        return "__reject__"


def route_after_tools(state: CoderState) -> str:
    if state.get("diff"):
        return "apply_diff"
    return "llm"


def apply_diff_node(state: CoderState) -> dict:
    edit_result = apply_diff(state.get("diff", {}))
    logger.info(edit_result['status'])
    return {
        "diff": {},
        "edit_result": edit_result,
    }


toolnode = ToolNode([grep, read_file, stage_diff], handle_tool_errors=True)

builder = StateGraph(CoderState)
builder.add_node("llm", call_llm)
builder.add_node("toolnode", toolnode)
builder.add_node("apply_diff", apply_diff_node)

builder.add_edge(START, "llm")
builder.add_conditional_edges(
    "llm",
    tools_condition,
    {
        "tools": "toolnode",
        "__end__": END
    }
)
builder.add_conditional_edges(
    "toolnode",
    route_after_tools,
    {
        "apply_diff": "apply_diff",
        "llm": "llm",
    }
)
builder.add_edge("apply_diff", "llm")

graph = builder.compile()

if __name__ == "__main__":
    # draw_mermaid(graph, "coder.png")
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", type=str, default="Fix the error in utils.py")
    args = parser.parse_args()

    user_prompt = args.prompt

    state = graph.invoke(
        {
            "messages": [
                {"role": "system", "content": coder_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "diff": {},
            "is_done": False,
        }
    )
    # while state["is_done"] == False:
    #     # todo: add confirmation
