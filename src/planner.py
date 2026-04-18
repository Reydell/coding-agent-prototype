import os
import dotenv

from langgraph.graph import StateGraph, START, END
from .utils import State

from langchain_groq import ChatGroq

from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition


dotenv.load_dotenv()


model = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=os.environ["GROQ_API_KEY"],
    reasoning_format='parsed',
)


def call_llm(state: State) -> dict:
    
