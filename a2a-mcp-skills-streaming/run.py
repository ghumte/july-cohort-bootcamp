"""Start only this demo's processes. Ctrl+C closes the children it started."""
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from demo.config import ROOT, HOST, PORTS

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-ui', action='store_true')
    args = parser.parse_args()
    names = ['policy_mcp', 'order_mcp', 'hello', 'policy', 'order', 'coordinator']
    if not args.no_ui: names.append('ui')
    for name in names:
        with socket.socket() as sock:
            try: sock.bind((HOST, PORTS[name]))
            except PermissionError: raise SystemExit('Local service startup is blocked by the environment permission settings.')
            except OSError: raise SystemExit(f'{name}: port {PORTS[name]} is occupied. Close the previous demo before starting.')
    run_dir = ROOT / '.run'
    run_dir.mkdir(exist_ok=True)
    settings = {name: True for name in names}
    control = run_dir / 'services.json'
    control.write_text(json.dumps(settings))
    children, logs = {}, {}
    def start(name):
        log = open(run_dir / (name + '.log'), 'a', buffering=1)
        if name.endswith('_mcp'):
            cmd = [sys.executable, '-m', 'demo.mcp_server', name[:-4]]
        elif name == 'ui':
            cmd = [sys.executable, '-m', 'streamlit', 'run', 'ui.py', '--server.address', HOST,
                   '--server.port', str(PORTS[name]), '--server.headless', 'true', '--browser.gatherUsageStats', 'false']
        else:
            cmd = [sys.executable, '-m', 'demo.server', name]
        env = dict(os.environ, PYTHONUNBUFFERED='1')
        children[name] = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
        logs[name] = log
        print(f'{name:14} http://{HOST}:{PORTS[name]}', flush=True)
    def stop(name):
        child = children.pop(name, None)
        if child:
            child.terminate()
            try: child.wait(timeout=8)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
            logs.pop(name).close()
    def terminate(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    try:
        for name in names: start(name)
        print('\nKeep this terminal open. Ctrl+C stops this kit only. Logs: .run/', flush=True)
        while True:
            try: desired = json.loads(control.read_text())
            except (OSError, json.JSONDecodeError): desired = settings
            for name in names:
                child = children.get(name)
                if child and child.poll() is not None:
                    raise RuntimeError(f'{name} exited. Read .run/{name}.log')
                if desired.get(name, True) and not child: start(name)
                elif not desired.get(name, True) and child: stop(name); print(name, 'stopped', flush=True)
            settings = desired
            time.sleep(0.3)
    except KeyboardInterrupt:
        print('\nStopping demo services.', flush=True)
    finally:
        for name in reversed(list(children)): stop(name)

if __name__ == '__main__': main()
