from typing import Annotated, TypedDict
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class State(TypedDict):
    messages: Annotated[list[dict], add_messages]
    counter: int

builder = StateGraph(State)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# define a node

def call_llm(state: State):
    output = llm.invoke(state["messages"])
    count = state.get("counter", 0) + 1
    return {"messages": [output], "counter": count}

builder.add_node("llm", call_llm)

# define connections
builder.add_edge(START, "llm")
builder.add_edge("llm", END)

graph = builder.compile()

# run the graph
result = graph.invoke({"messages": [{"role": "user", "content": "who am I?"}], "counter": 10})
print(result)

# cd /d C:\Users\ghumt\langchainprojects\july-cohort-bootcamp
# "C:\Users\ghumt\AppData\Local\Programs\Python\Python311\python.exe" .\Session-2\langgraph_intro.py

