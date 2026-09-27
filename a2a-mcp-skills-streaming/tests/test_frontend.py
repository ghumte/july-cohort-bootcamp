"""Streamlit's own test harness. This is not a browser visual inspection."""
from streamlit.testing.v1 import AppTest
from demo.config import ROOT

def test_all_demo_pages_load():
    app = AppTest.from_file(str(ROOT / 'ui.py')).run(timeout=10)
    for name in ['1. Simple A2A', '2. Agent Skills', '3. MCP tools', '4. Refund workflow']:
        app.sidebar.radio[0].set_value(name).run(timeout=10)
        assert not app.exception

def test_frontend_streams_a_completed_refund():
    app = AppTest.from_file(str(ROOT / 'ui.py')).run(timeout=10)
    app.sidebar.radio[0].set_value('4. Refund workflow').run(timeout=10)
    app.button[0].click().run(timeout=20)
    assert not app.exception
    assert not app.error
    events = app.session_state['last_events']
    assert events[-1]['statusUpdate']['status']['state'] == 'TASK_STATE_COMPLETED'
    assert any('READY_FOR_REVIEW' in element.value for element in app.info)

def test_frontend_discovers_mcp_schema_and_result():
    app = AppTest.from_file(str(ROOT / 'ui.py')).run(timeout=10)
    app.sidebar.radio[0].set_value('3. MCP tools').run(timeout=10)
    app.button[0].click().run(timeout=20)
    assert not app.exception
    assert not app.error
    assert len(app.json) >= 2
