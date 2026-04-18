import os
import dotenv

from langgraph.graph import StateGraph, START, END, add_messages
from typing import TypedDict, Annotated, Literal, Optional

from langchain_groq import ChatGroq

from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition

from langgraph.types import interrupt, Command

from .tools import grep, read_file, create_diff, apply_diff

from .utils import draw_mermaid, red
from .prompts import coder_prompt

dotenv.load_dotenv()


class Diff(TypedDict):
    path: str
    line_number: int
    line_text: str


class CoderState(TypedDict):
    messages: Annotated[list, add_messages]
    is_done: bool = False
    diff: Diff = {}


model = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.environ["GROQ_API_KEY"],
    reasoning_format='parsed'
).bind_tools([grep, read_file, create_diff, apply_diff])


def call_llm(state: CoderState) -> dict:
    response = model.invoke(state["messages"])
    print(response.text)
    print()
    return {"messages": [response]}

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

toolnode = ToolNode([grep, read_file, create_diff, apply_diff])

builder = StateGraph(CoderState)
builder.add_node("llm", call_llm)
builder.add_node("toolnode", toolnode)

builder.add_edge(START, "llm")
builder.add_conditional_edges(
    "llm",
    tools_condition,
    {
        "tools": "toolnode",
        "__end__": END
    }
)
builder.add_edge("toolnode", "llm")

graph = builder.compile()

if __name__ == "__main__":
    # draw_mermaid(graph, "coder.png")

    state = graph.invoke(
        {
            "messages": [
                {"role": "system", "content": coder_prompt},
                {"role": "user", "content": "Fix the print in utils.py file"}
            ],
            "diff": {},
            "is_done": False,
        }
    )
    # while state["is_done"] == False:
    #     # todo: add confirmation
