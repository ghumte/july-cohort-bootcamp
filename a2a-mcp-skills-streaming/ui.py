import asyncio
import json
import streamlit as st
from demo.config import url, ROOT
from demo.protocol import a2a_events, discover_agent, to_dict, event_text, artifact_text, artifact_data, mcp_call, mcp_tools
from demo.skills import discover_skills, load_skill
from demo.skill_demo import run_skill, EXAMPLE
from demo.bridge import sync_stream

st.set_page_config(page_title='Refund desk', page_icon=None, layout='wide')
st.title('Refund desk')
st.caption('A2A · Agent Skills · MCP · Streaming')
page = st.sidebar.radio('Page', ['1. Simple A2A', '2. Agent Skills', '3. MCP tools', '4. Refund workflow'])
mode = st.sidebar.radio('Mode', ['rehearsal', 'live'], format_func=lambda x: 'Rehearsal' if x == 'rehearsal' else 'Live model')
st.sidebar.caption('Live model reads OPENAI_API_KEY and OPENAI_MODEL from .env.')

def render_agent(role, payload):
    progress = st.status('Connecting to the agent…', expanded=True)
    result = st.empty()
    raw = []
    completed = False
    failed = False
    def chunks():
        nonlocal completed, failed
        for event in sync_stream(lambda: a2a_events(url(role), payload)):
            raw.append(event)
            if text := event_text(event): progress.write(text)
            for data in artifact_data(event):
                if 'decision' in data:
                    result.info(f"{data['decision']} · Order {data['order_id']} · No refund executed")
                else:
                    progress.write(f"{data.get('role', 'Specialist')}: {data.get('verdict', 'finding')}")
            state = event.get('statusUpdate', {}).get('status', {}).get('state')
            completed |= state == 'TASK_STATE_COMPLETED'
            failed |= state in ('TASK_STATE_FAILED', 'TASK_STATE_CANCELED', 'TASK_STATE_REJECTED')
            if text := artifact_text(event): yield text
    try:
        with st.chat_message('assistant'):
            st.write_stream(chunks)
        if completed and not failed:
            progress.update(label='Agent task completed', state='complete')
        else:
            progress.update(label='Response incomplete', state='error')
            st.warning('The response did not complete. Any displayed text is partial.')
    except Exception:
        progress.update(label='Connection or model request failed', state='error')
        st.error('Launcher or live request failed. Check .run logs. No refund was executed.')
    st.session_state['last_events'] = raw

if page == '1. Simple A2A':
    st.header('A2A greeting')
    st.write('Discover the greeting agent, send a name, get progress and an artifact. No model, skill, or MCP.')
    if st.button('Discover greeting agent'):
        try: st.json(to_dict(asyncio.run(discover_agent(url('hello')))))
        except Exception: st.error('Start with python run.py.')
    name = st.text_input('Name', 'Nachiketh')
    if st.button('Send A2A greeting', type='primary'):
        render_agent('hello', {'name': name, 'mode': 'rehearsal'})

elif page == '2. Agent Skills':
    st.header('Skill package')
    st.write(EXAMPLE)
    st.caption('Runs in this process. It does not call another agent.')
    st.json(discover_skills(), expanded=False)
    enabled = st.checkbox('Load clear-explanation skill', value=True)
    if enabled:
        skill = load_skill('clear-explanation')
        with st.expander('Loaded instructions', expanded=True):
            st.code(skill['prompt'], language='markdown')
        st.caption('Hash: ' + skill['sha256'])
    if st.button('Explain A2A', type='primary'):
        try:
            with st.chat_message('assistant'):
                st.write_stream(sync_stream(lambda: run_skill(mode, enabled)))
        except Exception: st.error('Live request failed. Check .env or use rehearsal.')

elif page == '3. MCP tools':
    st.header('MCP tools')
    st.write('Discover the tool, then call it against the sample records.')
    kind = st.selectbox('Evidence source', ['order', 'policy'])
    order = st.selectbox('Order', ['1042', '1043', '1044', '1045'])
    if st.button('Discover and call tool', type='primary'):
        try:
            tool = 'get_order' if kind == 'order' else 'get_refund_policy'
            st.write('Advertised tool schema')
            st.json(asyncio.run(mcp_tools(url(kind + '_mcp'))))
            data, names = asyncio.run(mcp_call(url(kind + '_mcp'), tool, {'order_id': order} if kind == 'order' else {}))
            st.write('Discovered tools:', ', '.join(names))
            st.json(data)
        except Exception: st.error('MCP lookup failed. Check the launcher.')

else:
    st.header('Refund check')
    st.write('Coordinator loads refund-triage, calls policy and order over A2A. Each specialist reads evidence over MCP.')
    order = st.selectbox('Order', ['1042', '1043', '1044', '1045'],
        format_func=lambda x: {'1042':'1042 · remaining INR 18,000', '1043':'1043 · already refunded',
                              '1044':'1044 · 45 days', '1045':'1045 · remaining INR 9,000'}[x])
    st.caption('Recommendation only. No approval and no payment.')
    if st.button('Check refund', type='primary'):
        render_agent('coordinator', {'order_id': order, 'mode': mode})

if page in ('1. Simple A2A', '4. Refund workflow') and st.session_state.get('last_events'):
    with st.expander('Inspect the last A2A event stream'):
        st.json(st.session_state['last_events'], expanded=False)
        st.download_button('Download events', json.dumps(st.session_state['last_events'], indent=2),
                           'a2a-events.json', 'application/json')
