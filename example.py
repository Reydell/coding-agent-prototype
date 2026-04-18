import os
import dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langchain_groq import ChatGroq

# for tools
from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition


dotenv.load_dotenv()


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b


model = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.environ["GROQ_API_KEY"],
    reasoning_format='parsed', # this is for chatgroq qwen to hide <think></think>
    reasoning_effort='default' # can be 'none'
)

model = model.bind_tools([multiply])

def call_llm(state: MessagesState) -> dict:
    response = model.invoke(state["messages"])
    print(response.text)
    print()
    return {"messages": [response]}

def get_input(state: MessagesState) -> dict:
    user_response = input()
    return {"messages": [{"role": "user", "content": user_response}]}

def decide_to_stop(state: MessagesState) -> dict:
    if getattr(state["messages"][-1], "text", "") == "":
        return "__end__"
    else:
        return '__llm__'
    
tool_node = ToolNode([multiply])

builder = StateGraph(MessagesState)
builder.add_node("llm", call_llm)
builder.add_node("user", get_input)
builder.add_node("tools", tool_node)

builder.add_edge(START, "user")

builder.add_conditional_edges(
    "llm",
    tools_condition,
    {
        "tools": "tools",
        "__end__": "user"
    }
)

builder.add_conditional_edges(
    "user",
    decide_to_stop,
    {
        "__end__": END,
        "__llm__": "llm"
    }
)

builder.add_edge("tools", "llm")

graph = builder.compile()

print("Hello, how can I help you today?\n")
result = graph.invoke(
    {
        "messages": [
            {"role": "system", "content": "Use tools where possible. Treat the tool results as absolute truth. "
            "Even if you disagree. Don't correct tool mistakes. Don't give any comments."},
            # {"role": "user", "content": "What is 2 times 5"}
        ]
    }
)