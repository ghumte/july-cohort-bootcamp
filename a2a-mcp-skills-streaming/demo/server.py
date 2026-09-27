import argparse
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import a2a_pb2 as a2a
from .agents import DemoExecutor
from .config import HOST, PORTS, url

DESCRIPTIONS = {
    'hello': ('greet', 'Simple greeting', 'Reply to a name. Deterministic protocol demonstration.'),
    'policy': ('check-policy', 'Refund policy check', 'Check age and category using MCP evidence.'),
    'order': ('check-order', 'Refundable value check', 'Check remaining refundable value using MCP evidence.'),
    'coordinator': ('refund-triage', 'Refund recommendation', 'Combine specialist findings and stream an explanation. Human review remains required.')}

def agent_card(role):
    skill_id, name, description = DESCRIPTIONS[role]
    return a2a.AgentCard(name=name, description=description, version='1.0.0',
        supported_interfaces=[a2a.AgentInterface(url=url(role) + '/', protocol_binding='JSONRPC', protocol_version='1.0')],
        capabilities=a2a.AgentCapabilities(streaming=True), default_input_modes=['text/plain'],
        default_output_modes=['text/plain', 'application/json'],
        skills=[a2a.AgentSkill(id=skill_id, name=name, description=description,
            tags=[role, 'teaching'], examples=['Check order 1042' if role != 'hello' else 'Hello Nachiketh'])])

def app(role):
    card = agent_card(role)
    handler = DefaultRequestHandler(agent_executor=DemoExecutor(role), task_store=InMemoryTaskStore(), agent_card=card)
    async def health(request):
        return JSONResponse({'service': role, 'ready': True, 'persistence': 'in-memory'})
    return Starlette(routes=[Route('/health', health), *create_agent_card_routes(card),
                            *create_jsonrpc_routes(handler, '/')])

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('role', choices=DESCRIPTIONS)
    args = p.parse_args()
    uvicorn.run(app(args.role), host=HOST, port=PORTS[args.role], log_level='warning')
