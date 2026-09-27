import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', override=False)
HOST = '127.0.0.1'
PORTS = {'hello': 9200, 'policy': 9201, 'order': 9202, 'coordinator': 9203,
         'policy_mcp': 9211, 'order_mcp': 9212, 'ui': 8611}

def url(role):
    return f'http://{HOST}:{PORTS[role]}'

def live_settings():
    key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL')
    if not key or not model:
        raise ValueError('Live mode needs OPENAI_API_KEY and OPENAI_MODEL in .env. Use rehearsal mode otherwise.')
    return key, model
