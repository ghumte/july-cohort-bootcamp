from typing import Annotated, TypedDict, Optional
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class State(TypedDict):
    x : int
    y : int
    node_1_result : Optional[float]
    node_2_result : Optional[float]
    node_3_result : Optional[float]
    node_4_result : Optional[float]

#nodes
def node_1(state: State):
    add = state["x"] + state["y"]
    return {"node_1_result": add}

def node_2(state: State):
    multiply = state["x"] * state["y"]
    return {"node_2_result": multiply}

def node_3(state: State):
    divide = state["x"] / state["y"]
    return {"node_3_result": divide}

def node_4(state: State):
    final_output = state["node_1_result"] + state["node_2_result"] + state["node_3_result"]
    return {"node_4_result": final_output}

builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
builder.add_node("node_4", node_4)

# define the connections
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", "node_4")
builder.add_edge("node_4", END)

graph = builder.compile()

result = graph.invoke({"x": 10, "y": 20})
print(result)