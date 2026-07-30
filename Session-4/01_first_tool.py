from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from dotenv import load_dotenv

load_dotenv()

@tool
def multiply(x: float, y: float) -> float:
    """Multiply 'x' times 'y'."""
    return x * y

@tool
def add(x: float, y: float) -> float:
    """Add 'x' and 'y'."""
    return x + y

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools([multiply, add])

# messages = [
#     HumanMessage(content="What is 123 * 456?")
# ]

messages = [
    HumanMessage(content="Who is PM of India?")
]
ai_msg = llm_with_tools.invoke(messages)
messages.append(ai_msg)

print(f"Output for first message is {ai_msg}")

tool_names = {"multiply": multiply, "add": add}

for call in ai_msg.tool_calls:
    print(f"Tool call name: {call["name"]}")
    print(f"Tool call arguments: {call["args"]}")
    tool_result = tool_names[call["name"]].invoke(call["args"])
    messages.append(ToolMessage(content=tool_result, tool_call_id=call["id"]))
    print(f"Tool result: {tool_result}")

# Pass 3
final_result = llm_with_tools.invoke(messages)
print(f"Final result: {final_result}")