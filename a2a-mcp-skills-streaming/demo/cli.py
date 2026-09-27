import argparse
import asyncio
import json
from .config import ROOT, url
from .protocol import a2a_events, discover_agent, to_dict, event_text, artifact_text, artifact_data, mcp_call
from .skills import discover_skills, load_skill
from .skill_demo import run_skill

async def run(args):
    if args.command == 'card':
        print(json.dumps(to_dict(await discover_agent(url(args.role))), indent=2))
    elif args.command in ('hello', 'refund'):
        role = 'hello' if args.command == 'hello' else 'coordinator'
        payload = {'name': args.name, 'mode': 'rehearsal'} if role == 'hello' else {'order_id': args.order, 'mode': args.mode}
        events = []
        async for event in a2a_events(url(role), payload):
            events.append(event)
            if args.raw:
                print(json.dumps(event), flush=True)
            else:
                if text := event_text(event): print('[progress]', text, flush=True)
                if text := artifact_text(event): print(text, end='', flush=True)
                for item in artifact_data(event): print('\n[evidence]', json.dumps(item, indent=2), flush=True)
        if args.save:
            path = ROOT / 'evidence' / args.save
            if path.parent.resolve() != (ROOT / 'evidence').resolve():
                raise ValueError('Use a filename only for --save.')
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(events, indent=2))
    elif args.command == 'mcp':
        tool = 'get_refund_policy' if args.kind == 'policy' else 'get_order'
        data, names = await mcp_call(url(args.kind + '_mcp'), tool, {} if args.kind == 'policy' else {'order_id': args.order})
        print(json.dumps({'discovered_tools': names, 'called': tool, 'result': data}, indent=2))
    elif args.command == 'skills':
        print(json.dumps(discover_skills(), indent=2))
    elif args.command == 'skill-show':
        print(json.dumps(load_skill(args.name), indent=2))
    elif args.command == 'skill-run':
        print('Mode:', args.mode, '| Skill:', 'off' if args.without else 'clear-explanation')
        async for chunk in run_skill(args.mode, not args.without): print(chunk, end='', flush=True)
    elif args.command == 'service':
        state = ROOT / '.run/services.json'
        if not state.exists(): raise ValueError('Start the demo launcher first.')
        settings = json.loads(state.read_text())
        settings[args.role] = args.state == 'on'
        temp = state.with_suffix('.tmp')
        temp.write_text(json.dumps(settings))
        temp.replace(state)
        print(f'Requested {args.role} {args.state}. The launcher applies this within one second.')

def parser():
    p = argparse.ArgumentParser(description='Instructor demo commands')
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('card'); q.add_argument('role', choices=['hello','policy','order','coordinator'])
    for command in ['hello','refund']:
        q = sub.add_parser(command); q.add_argument('--raw', action='store_true'); q.add_argument('--save')
        if command == 'hello': q.add_argument('--name', default='Nachiketh')
        else:
            q.add_argument('--order', default='1042'); q.add_argument('--mode', choices=['rehearsal','live'], default='rehearsal')
    q = sub.add_parser('mcp'); q.add_argument('kind', choices=['policy','order']); q.add_argument('--order', default='1042')
    sub.add_parser('skills')
    q = sub.add_parser('skill-show'); q.add_argument('name', default='clear-explanation', nargs='?')
    q = sub.add_parser('skill-run'); q.add_argument('--mode', choices=['rehearsal','live'], default='rehearsal'); q.add_argument('--without', action='store_true')
    q = sub.add_parser('service'); q.add_argument('role', choices=['policy','order','policy_mcp','order_mcp']); q.add_argument('state', choices=['on','off'])
    return p

if __name__ == '__main__':
    try: asyncio.run(run(parser().parse_args()))
    except Exception as exc: raise SystemExit(f'Demo stopped: {type(exc).__name__}. Check the launcher and service logs. {exc}')
