"""Only live mode calls a model. Rehearsal text is explicitly simulated."""
import asyncio
from openai import AsyncOpenAI
from .config import live_settings

async def text_stream(instructions, user_input, mode, rehearsal_text):
    if mode == 'rehearsal':
        # These are deliberately generated chunks, not model tokens.
        for paragraph in rehearsal_text.splitlines(keepends=True):
            yield paragraph
            await asyncio.sleep(0.06)
        return
    if mode != 'live':
        raise ValueError('Mode must be rehearsal or live.')
    key, model = live_settings()
    async with AsyncOpenAI(api_key=key, timeout=45, max_retries=0) as client:
        stream = await client.responses.create(model=model, instructions=instructions,
            input=user_input, stream=True, max_output_tokens=650)
        completed = False
        async with stream:
            async for event in stream:
                if event.type == 'response.output_text.delta':
                    yield event.delta
                elif event.type == 'response.completed':
                    completed = True
                elif event.type in ('error', 'response.failed', 'response.incomplete'):
                    raise RuntimeError('The live model response did not complete. Check API access, quota, and the model setting.')
        if not completed:
            raise RuntimeError('The live model stream ended before completion.')

async def explanation(instructions, payload, mode, fallback):
    return ''.join([chunk async for chunk in text_stream(instructions, payload, mode, fallback)])
