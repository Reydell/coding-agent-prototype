from langchain.tools import tool, ToolRuntime
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Literal, List, Optional, Dict, TypedDict, LiteralString

from langchain_core.messages import ToolMessage

from langgraph.types import Command

from pydantic import BaseModel, Field

from pathlib import Path
import re

from .utils import red


class GrepReturnType(TypedDict):
    file_path: str
    line_number: int
    line_text: str


class CodeLineType(TypedDict):
    line_number: int
    line_text: str


class GrepArgs(BaseModel):
    regex: str = Field(description="Regular expression that will be run through re.compile(regex).")
    root: str = Field(description="Root directory or a file to search through. Path must be relative to working directory.", default=".")


class ReadFileArgs(BaseModel):
    path: str = Field(description="Path must be relative to working directory.")


class CreateDiffArgs(BaseModel):
    path: str = Field(description="Path must be relative to working directory.")
    line_number: int = Field(description="Index of the line that you want to replace.")
    line_text: str = Field(description="New line text.")



@tool
def choose_subagent(agent: Literal['coder']) -> Literal['coder']:
    """Choose subagent to call"""
    return agent


@tool(args_schema=GrepArgs)
def grep(regex, root) -> List[GrepReturnType] | LiteralString:
    """Recursive search through a folder or a file using regex."""

    red(f'grep {regex} {root}')

    if not root.startswith("./"):
        root = f"./{root}"

    if "\\" in root:
        return "Error: use MacOS path syntax." 
    if ".." in root:
        return "Error: path must not leave working directory!"
    if '~' in root:
        return "Error: absolute path search prohibited!"
    
    path = "generated_project/" + root.rstrip('.')[2:]
    red(f'normalized path {path}')

    try:
        pattern = re.compile(regex)
    except Exception as e:
        red(1)
        return "Error: invalid regex!"

    res = []
    lines = None
    for p in Path(path).rglob("*"):
        if p.is_file():
            try:
                with open(p) as fin:
                    lines = [{
                        "file_path": str(p), 
                        "line_number": line_number, 
                        "line_text": line_text
                    } for line_number, line_text in enumerate(fin.readlines()) if pattern.findall(line_text)]

                res.extend(lines)
            except Exception as e:
                red(2)
                pass
    
    if res:
        red(res)
        return res
    red(3)
    return "Error: no matches found!"

@tool(args_schema=ReadFileArgs)
def read_file(path) -> List[CodeLineType] | LiteralString:
    """Read a file and obtain a list of all lines and their numbers to choose from later."""

    red(f'read_file {path}')

    if not path.startswith("./"):
        path = f"./{path}"

    if "\\" in path:
        return "Error: use MacOS path syntax." 
    if ".." in path:
        return "Error: path must not leave working directory!"
    if '~' in path:
        return "Error: absolute path search prohibited!"
    
    path = "generated_project/" + path.rstrip('.')[2:]
    red(f'normalized path {path}')
    path = Path(path)

    if path.is_file():
        try:
            with open(path) as fin:
                lines = [{
                    "line_number": line_number, 
                    "line_text": line_text
                } for line_number, line_text in enumerate(fin.readlines())]
        except Exception as e:
            return "Error: failed to open file for unknown reason!"
        
    else:
        return "Error: not a file!"
    
    red(lines)
    return lines


@tool(args_schema=CreateDiffArgs)
def create_diff(
    path: str,
    line_number: int,
    line_text: str,
    runtime: ToolRuntime,
) -> Command:
    """Choose a file, line number and text to replace it with. This only stages the diff."""
    red(f"create diff {path} {line_number} {line_text}")
    return Command(
        update={
            "diff": {
                "path": path,
                "line_number": line_number,
                "line_text": line_text,
            },
            "messages": [
                ToolMessage(
                    content=f"Stored diff for {path}:{line_number}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
    

@tool
def apply_diff(runtime: ToolRuntime) -> Command:
    """Apply current diff."""
    diff = runtime.state.get("diff")
    path = diff["path"]
    line_number = diff["line_number"]
    line_text = diff["line_text"]

    if not path.startswith("./"):
        path = f"./{path}"

    if "\\" in path:
        return "Error: use MacOS path syntax." 
    if ".." in path:
        return "Error: path must not leave working directory!"
    if '~' in path:
        return "Error: absolute path search prohibited!"
    
    path = "generated_project/" + path.rstrip('.')[2:]

    red(f"apply_diff {path}")

    with open(path, 'r') as fin:
        lines = [line.strip("\n") for line in fin]
        lines[line_number] = line_text
    with open(path, 'w') as fout:
        for line in lines:
            print(line, file=fout)

    return Command(
        update={
            "diff": {},
            "messages": [
                ToolMessage(
                    content=f"Applied diff for {path}:{line_number}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )