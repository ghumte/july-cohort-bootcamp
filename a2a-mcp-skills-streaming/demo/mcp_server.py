"""Two small MCP services. Each exposes only its own read-only tool."""
import argparse
import json
from mcp.server import MCPServer
from .config import ROOT, HOST, PORTS

def build_server(kind):
    server = MCPServer(f'{kind} evidence', instructions='Read-only local classroom data.')
    if kind == 'policy':
        @server.tool()
        def get_refund_policy() -> dict:
            """Return the classroom refund policy and its versioned source reference."""
            return json.loads((ROOT / 'data/policy.json').read_text())
    else:
        @server.tool()
        def get_order(order_id: str) -> dict:
            """Get one sample order, including amount paid and prior refunds."""
            records = json.loads((ROOT / 'data/orders.json').read_text())
            if order_id not in records:
                raise ValueError(f'No sample order exists for {order_id}.')
            return records[order_id]
    return server

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['policy', 'order'])
    args = parser.parse_args()
    build_server(args.kind).run(transport='streamable-http', host=HOST,
        port=PORTS[args.kind + '_mcp'], stateless_http=True)

if __name__ == '__main__':
    main()
