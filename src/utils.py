from langchain.graph import add_messages
from typing import Annotated, TypedDict


def draw_mermaid(graph, path, v=0):
    png_bytes = graph.get_graph().draw_mermaid_png()
    if '.' not in path:
        path = path + '.png'
    if 'images' not in path:
        path = 'images/' + path

    with open(path, "wb") as f:
        f.write(png_bytes)
    if v:
        print(f"Graph mermaid saved to {path}")



class State(TypedDict):
    messages: Annotated[list, add_messages]
