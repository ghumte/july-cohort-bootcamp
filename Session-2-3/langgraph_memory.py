from typing import Annotated, TypedDict
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage
checkpointer = MemorySaver()
import uuid

load_dotenv()

class State(TypedDict):
    messages: Annotated[list[dict], add_messages]
    counter: int

builder = StateGraph(State)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# define a node

def call_llm(state: State):
    output = llm.invoke(state["messages"]).content
    count = state.get("counter", 0) + 1
    return {"messages": [AIMessage(content=output)], "counter": count}

builder.add_node("llm", call_llm)

# define connections
builder.add_edge(START, "llm")
builder.add_edge("llm", END)

graph = builder.compile(checkpointer=checkpointer)

thread_1 = {"configurable": {"thread_id": str(uuid.uuid4())}} # Generate a random UUID for the thread
thread_2 = {"configurable": {"thread_id": str(uuid.uuid4())}}
# run the graph
result = graph.invoke({"messages": [{"role": "user", "content": "Hi I am Nachiketh"}], "counter": 10}, thread_1)
print(result)

result = graph.invoke({"messages": [{"role": "user", "content": "who am I?"}], "counter": 10}, thread_1)
print(result)

# run the graph
result = graph.invoke({"messages": [{"role": "user", "content": "Hi I am Sam"}], "counter": 10}, thread_2)
print(result)

result = graph.invoke({"messages": [{"role": "user", "content": "who am I?"}], "counter": 10}, config=thread_2)
print(result)# config = {"configurable": {"thread_id": str(uuid.uuid4())}, "callbacks": [langfuse_handler()]}


result = graph.invoke({"messages": [{"role": "user", "content": "who am I?"}], "counter": 10}, thread_1)
print(result)

print("Getting state for thread 1")
print("--------------------------------")
get_state = graph.get_state(thread_1)
print(get_state)