"""DEMO 2 — Real tools, real data, no API keys required.

Two genuinely free tools:
    * DuckDuckGo web search  (no key)
    * Wikipedia lookup       (no key)

"""
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.messages import HumanMessage
from common import calculator, get_model,show
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI

# Wikipedia: keep results short so the context stays small (and cheap).
wikipedia = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=500)
)
search = DuckDuckGoSearchRun()

TOOLS = [search, wikipedia, calculator]
BY_NAME = {t.name: t for t in TOOLS}


def run(question: str) -> None:
    model = get_model().bind_tools(TOOLS)
    messages = [HumanMessage(question)]

    # Keep looping while the model wants more tools (it may chain several).
    for _ in range(5):
        ai_msg = model.invoke(messages)
        messages.append(ai_msg)

        if not ai_msg.tool_calls:
            break

        for call in ai_msg.tool_calls:
            print(f"   ⚙  {call['name']}({call['args']})")
            try:
                messages.append(BY_NAME[call["name"]].invoke(call))
            except Exception as exc:  # tools fail — the agent must survive it
                from langchain_core.messages import ToolMessage

                messages.append(
                    ToolMessage(content=f"Tool error: {exc}", tool_call_id=call["id"])
                )
                print(f"   ⚠  failed: {exc}")

    print("\nAnswer:", messages[-1].content, "\n")
    return messages


if __name__ == "__main__":
    print("Q: What was Buzz Aldrin most known for?\n")
    run("What was the most impressive thing about Buzz Aldrin?")

    print("Q: A question needing search + maths together\n")
    msgs = run(
        "Search for the current population of Japan, then divide it by 1000 "
        "using the calculator."
    )
    print("Full trace:")
    show(msgs)
