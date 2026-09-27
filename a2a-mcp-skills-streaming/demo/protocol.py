"""Small wrappers around the official A2A 1.0 and MCP Python SDKs."""
import json
from uuid import uuid4
import httpx
from google.protobuf.json_format import MessageToDict
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import a2a_pb2 as a2a
from mcp import Client as MCPClient

def to_dict(message):
    return MessageToDict(message)

def agent_message(text):
    return a2a.Message(message_id=str(uuid4()), role=a2a.ROLE_AGENT,
                       parts=[a2a.Part(text=text)])

async def discover_agent(base_url):
    async with httpx.AsyncClient(timeout=5, trust_env=False) as http:
        return await A2ACardResolver(httpx_client=http, base_url=base_url).get_agent_card()

async def a2a_events(base_url, payload):
    async with httpx.AsyncClient(timeout=httpx.Timeout(100, connect=4), trust_env=False) as http:
        card = await A2ACardResolver(httpx_client=http, base_url=base_url).get_agent_card()
        if not card.capabilities.streaming:
            raise ValueError('This demonstration requires an agent that advertises streaming.')
        client = ClientFactory(ClientConfig(httpx_client=http, streaming=True)).create(card)
        request = a2a.SendMessageRequest(message=a2a.Message(
            message_id=str(uuid4()), role=a2a.ROLE_USER,
            parts=[a2a.Part(text=json.dumps(payload))]))
        async for event in client.send_message(request):
            yield to_dict(event)

async def mcp_call(base_url, tool, arguments):
    async with MCPClient(base_url + '/mcp', read_timeout_seconds=8) as client:
        listed = await client.list_tools()
        names = [t.name for t in listed.tools]
        if tool not in names:
            raise ValueError(f'{tool} is not advertised by this MCP server.')
        result = await client.call_tool(tool, arguments)
        if result.is_error:
            raise ValueError('The evidence tool could not complete this lookup.')
        if result.structured_content:
            return result.structured_content, names
        text = ''.join(c.text for c in result.content if c.type == 'text')
        return json.loads(text), names

async def mcp_tools(base_url):
    async with MCPClient(base_url + '/mcp', read_timeout_seconds=8) as client:
        result = await client.list_tools()
        return [tool.model_dump(by_alias=True, exclude_none=True) for tool in result.tools]

def event_text(event):
    obj = event.get('statusUpdate', {}).get('status', {}).get('message', {})
    if not obj:
        obj = event.get('message', {})
    return ''.join(p.get('text', '') for p in obj.get('parts', []))

def artifact_data(event):
    artifact = event.get('artifactUpdate', {}).get('artifact', {})
    return [p['data'] for p in artifact.get('parts', []) if 'data' in p]

def artifact_text(event):
    artifact = event.get('artifactUpdate', {}).get('artifact', {})
    return ''.join(p.get('text', '') for p in artifact.get('parts', []))
