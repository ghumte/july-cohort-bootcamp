from typing import Annotated, TypedDict, Optional
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

class State(TypedDict):
    x : int
    y : int
    result : Annotated[list[str], add_messages]

#nodes
def node_1(state: State):
    add = state["x"] + state["y"]
    return {"result": AIMessage(content=f"The addition of {state['x']} and {state['y']} is {add}")}

def node_2(state: State):
    multiply = state["x"] * state["y"]
    return {"result": AIMessage(content=f"The multiplication of {state['x']} and {state['y']} is {multiply}")}

def node_3(state: State):
    divide = state["x"] / state["y"]
    return {"result": AIMessage(content=f"The division of {state['x']} and {state['y']} is {divide}")}


builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)


# define the connections
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

graph = builder.compile()
graph.get_graph().draw_mermaid_png(output_file_path="graph.png")

result = graph.invoke({"x": 10, "y": 20})
print(result)