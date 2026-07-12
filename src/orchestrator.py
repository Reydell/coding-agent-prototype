import os
import dotenv

from langgraph.graph import StateGraph, START, END, add_messages
from typing import TypedDict, Annotated, Literal, Optional

from langchain_groq import ChatGroq

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

from .prompts import orchestrator_prompt

from .tools import choose_subagent, grep, read_file
from .utils import draw_mermaid

# for invoking coder agent
from .coder import graph as coder_graph
from .prompts import coder_prompt

import json

import logging
logger = logging.getLogger(__name__)


dotenv.load_dotenv()


class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    subagent: Optional[Literal['coder']]
    command: Optional[str]
    subagent_result: str


model = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.environ["GROQ_API_KEY"],
    reasoning_format='parsed',
).bind_tools([choose_subagent, grep, read_file])


def call_llm(state: OrchestratorState) -> dict:
    subagent_result = state.get("subagent_result")
    if subagent_result:
        state['messages'].append(SystemMessage(content=subagent_result))
        
    response = model.invoke(state["messages"])
    logger.info(response.text)
    return {'messages': [response]}


def call_user(state: OrchestratorState) -> dict:
    answer = interrupt(
        {"question": "What do you want your me to do?\n"}
    )
    return {"messages": [{"role": "user", "content": answer}]}


def route_node(state: OrchestratorState) -> dict:
    return {}

def route(state: OrchestratorState) -> str:
    subagent = state.get("subagent", None)
    if subagent is None:
        return "llm"
    else:
        return "subagent"


def invoke_subagent(state: OrchestratorState) -> dict:
    try:
        subagent = state["subagent"]
        response = None
        match subagent:
            case 'coder':
                logger.info("CODER CALLED with command %s", state["command"])
                coder_state = coder_graph.invoke(
                    {
                        "messages": [
                            {"role": "system", "content": coder_prompt},
                            {"role": "user", "content": state["command"]}
                        ],
                        "diff": {},
                        "edit_result": {},
                        "is_done": False,
                    }
                )
                response = coder_state["edit_result"]
        
        return {
            "subagent": None,
            "command": None,
            "subagent_result": f"Subagent {subagent} returned\n" + json.dumps(response),
        }

    except Exception as e:
        return {
            "subagent": None,
            "command": None,
            "subagent_result": f"Error while invoking subagent\n" + json.dumps({
                "status": "error",
                "error": "UnknownError",
            })
        }


toolnode = ToolNode([choose_subagent, grep, read_file], handle_tool_errors=True)

builder = StateGraph(OrchestratorState)

builder.add_node("llm", call_llm)
builder.add_node("user", call_user)
builder.add_node("router", route_node)
builder.add_node("toolnode", toolnode)
builder.add_node("subagent", invoke_subagent)


builder.add_edge(START, "user")
builder.add_edge("user", "router")
builder.add_conditional_edges(
    "router",
    route,
    {
        "llm": "llm",
        "subagent": "subagent",
    }
)
builder.add_conditional_edges(
    "llm",
    tools_condition,
    {
        "tools": "toolnode",
        "__end__": "user"
    }
)

builder.add_edge("toolnode", "router")
builder.add_edge("subagent", "llm")

graph = builder.compile(checkpointer=InMemorySaver())



if __name__ == "__main__":

    draw_mermaid(graph, "orchestrator.png")

    config = {"configurable": {"thread_id": "orchestrator"}}

    state = graph.invoke({
            "messages": [
                # {
                #     "role": "system",
                #     "content": orchestrator_prompt
                # },
                SystemMessage(content=orchestrator_prompt)
            ],
            "subagent": None
        },
        config=config,
    )

    while "__interrupt__" in state:
        payload = state["__interrupt__"][0].value
        user_input = input(payload['question'])
        if user_input == "":
            break

        state = graph.invoke(
            Command(resume=user_input),
            config=config
        )   

