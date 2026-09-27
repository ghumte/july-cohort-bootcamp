from .skills import discover_skills, load_skill
from .model import text_stream

EXAMPLE = 'Explain A2A to someone who has used a chatbot but has never connected two agents.'
REHEARSAL = '''## Simple explanation
A2A gives separate agent services a shared way to describe their capabilities and exchange work. A client can send a request and receive progress and a result.

## Small example
Think of a travel assistant asking a separate hotel specialist to find a room. They can communicate through the same protocol even when different teams built them.

## What to remember
The protocol carries the request. The application behind each agent decides how to answer it.
'''

async def run_skill(mode='rehearsal', enabled=True):
    prompt = load_skill('clear-explanation')['prompt'] if enabled else 'Give a brief explanation in one plain paragraph.'
    fallback = REHEARSAL if enabled else 'A2A is a standard way for separate agent services to exchange requests, progress updates, and results. Their applications decide how to solve the work.\n'
    async for chunk in text_stream(prompt, EXAMPLE, mode, fallback):
        yield chunk
