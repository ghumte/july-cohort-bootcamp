"""Instructor preflight. Start python run.py --no-ui before running these checks."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
import pytest
from demo.config import ROOT, url
from demo.agents import decide
from demo.protocol import a2a_events, discover_agent, to_dict, artifact_data, artifact_text, mcp_call
from demo.skills import discover_skills, load_skill
from demo.skill_demo import run_skill
from demo.model import text_stream

def summary(events):
    return next(data for event in events for data in artifact_data(event) if 'decision' in data)

async def collect(order='1042'):
    return [event async for event in a2a_events(url('coordinator'), {'order_id': order, 'mode': 'rehearsal'})]

def save(name, events):
    folder = ROOT / 'evidence'
    folder.mkdir(exist_ok=True)
    (folder / name).write_text(json.dumps(events, indent=2))

@pytest.mark.asyncio
async def test_hello_uses_discovery_and_a2a_events():
    card = to_dict(await discover_agent(url('hello')))
    assert card['capabilities']['streaming'] is True
    assert card['skills'][0]['id'] == 'greet'
    assert card['supportedInterfaces'][0]['protocolVersion'] == '1.0'
    events = [e async for e in a2a_events(url('hello'), {'name': 'Nachiketh'})]
    assert 'Hello, Nachiketh' in ''.join(artifact_text(e) for e in events)
    assert events[-1]['statusUpdate']['status']['state'] == 'TASK_STATE_COMPLETED'
    save('01-hello.json', events)
    save('agent-card.json', card)

@pytest.mark.asyncio
async def test_mcp_discovery_and_evidence():
    order, names = await mcp_call(url('order_mcp'), 'get_order', {'order_id': '1042'})
    policy, _ = await mcp_call(url('policy_mcp'), 'get_refund_policy', {})
    assert names == ['get_order']
    assert order['paid_inr'] == 18000
    assert policy['refund_window_days'] == 30
    save('02-mcp.json', {'order': order, 'policy': policy, 'discovered_order_tools': names})

@pytest.mark.asyncio
@pytest.mark.parametrize('order,expected', [('1042','READY_FOR_REVIEW'), ('1043','BLOCKED'), ('1044','BLOCKED'), ('1045','READY_FOR_REVIEW'), ('9999','INCOMPLETE')])
async def test_refund_scenarios(order, expected):
    events = await collect(order)
    result = summary(events)
    assert result['decision'] == expected
    assert result['refund_executed'] is False
    assert events[-1]['statusUpdate']['status']['state'] == 'TASK_STATE_COMPLETED'
    text = ''.join(artifact_text(e) for e in events)
    assert '## Recommendation' in text and '## Evidence' in text and '## Next step' in text
    if order != '9999': assert result['findings']['order']['sources'] == [f'orders/{order}@v1']
    save(f'03-refund-{order}.json', events)

@pytest.mark.asyncio
async def test_order_service_outage_and_restore():
    control = ROOT / '.run/services.json'
    before = json.loads(control.read_text())
    async def set_enabled(enabled):
        state = dict(before, order=enabled)
        control.write_text(json.dumps(state))
        for _ in range(50):
            try:
                async with httpx.AsyncClient(timeout=0.3, trust_env=False) as client:
                    response = await client.get(url('order') + '/health')
                    up = response.status_code == 200
            except httpx.HTTPError: up = False
            if up == enabled: return
            await asyncio.sleep(0.2)
        raise AssertionError('Launcher did not apply requested service state')
    try:
        await set_enabled(False)
        events = await collect()
        result = summary(events)
        assert result['decision'] == 'INCOMPLETE'
        assert result['findings']['policy']['verdict'] == 'CLEAR'
        assert result['findings']['order']['verdict'] == 'ERROR'
        save('04-order-service-outage.json', events)
    finally:
        await set_enabled(True)
    assert summary(await collect())['decision'] == 'READY_FOR_REVIEW'

def test_skill_metadata_body_and_reference_are_separate():
    assert len(discover_skills()) == 2
    assert all(set(s) == {'name','description'} for s in discover_skills())
    skill = load_skill('clear-explanation')
    assert '## Small example' in skill['body']
    assert len(skill['references']) == 1
    assert 'analogy' in skill['prompt']
    with pytest.raises(ValueError): load_skill('../.env')

@pytest.mark.asyncio
async def test_rehearsal_skill_comparison():
    on = ''.join([x async for x in run_skill('rehearsal', True)])
    off = ''.join([x async for x in run_skill('rehearsal', False)])
    assert '## Small example' in on and '## Small example' not in off

def test_decision_keeps_missing_and_blocking_evidence():
    assert decide({'policy': {'verdict':'CLEAR'}}) == 'INCOMPLETE'
    assert decide({'policy': {'verdict':'BLOCK'}, 'order': {'verdict':'ERROR'}}) == 'BLOCKED'
    assert decide({}) == 'INCOMPLETE'

@pytest.mark.asyncio
async def test_live_stream_adapter_passes_instructions_and_deltas():
    captured = {}
    class Stream:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def __aiter__(self):
            yield SimpleNamespace(type='response.output_text.delta', delta='Hello ')
            yield SimpleNamespace(type='response.output_text.delta', delta='class')
            yield SimpleNamespace(type='response.completed')
    class Client:
        def __init__(self, **kwargs): self.responses = self
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def create(self, **kwargs): captured.update(kwargs); return Stream()
    with patch('demo.model.live_settings', return_value=('test-key','test-model')), patch('demo.model.AsyncOpenAI', Client):
        result = [x async for x in text_stream('Loaded skill body', 'Request', 'live', 'unused')]
    assert result == ['Hello ', 'class']
    assert captured['instructions'] == 'Loaded skill body'
    assert captured['stream'] is True

@pytest.mark.asyncio
async def test_live_mode_requires_explicit_credentials():
    with patch.dict('os.environ', {'OPENAI_API_KEY':'','OPENAI_MODEL':''}):
        with pytest.raises(ValueError):
            _ = [x async for x in text_stream('x','x','live','unused')]
