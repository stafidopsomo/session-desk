"""Read-only Codex feasibility probe. No thread/turn, inference, login or install.

All filesystem checks read this probe's synthetic temporary canaries only.
Raw protocol replies, accounts, source paths and model transcripts are not saved.
This is development diagnostics, not the product's provider adapter.
"""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time


class RpcError(RuntimeError):
    def __init__(self, method, code):
        super().__init__(f'{method}: RPC error {code}')
        self.method, self.code = method, code


class ReadOnlyProbe:
    ALLOWED = {'initialize', 'account/read', 'model/list',
               'configRequirements/read', 'command/exec'}

    def __init__(self, cli, cwd):
        env = os.environ.copy()
        # No separately billed API-key fallback; do not modify the parent env.
        for key in ('OPENAI_API_KEY', 'CODEX_API_KEY'):
            env.pop(key, None)
        self.process = subprocess.Popen(
            [cli, 'app-server', '--listen', 'stdio://'], cwd=cwd, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.messages, self.sequence = queue.Queue(), 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except json.JSONDecodeError:
                    continue
        finally:
            self.messages.put(None)

    def send(self, message):
        self.process.stdin.write(json.dumps(message) + '\n')
        self.process.stdin.flush()

    def request(self, method, params, timeout=15):
        if method not in self.ALLOWED:
            raise ValueError('This probe cannot start inference or mutate provider state')
        self.sequence += 1
        ident = self.sequence
        self.send({'id': ident, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Codex read-only request timed out')
            reply = self.messages.get(timeout=remaining)
            if reply is None:
                raise RuntimeError('Codex transport closed')
            if reply.get('id') == ident and 'method' not in reply:
                if 'error' in reply:
                    raise RpcError(method, reply['error'].get('code'))
                return reply.get('result', {})
            if 'method' in reply and 'id' in reply:
                self.send({'id':reply['id'], 'error':{
                    'code':-32601, 'message':'Interactive requests are unavailable in this read-only probe'}})

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        for stream in (self.process.stdin, self.process.stdout):
            stream.close()
        self.reader.join(timeout=1)


def account_summary(result):
    account = result.get('account') or {}
    mode = account.get('type') if isinstance(account, dict) else None
    # Never echo an unexpected provider field as an authentication label.
    mode = mode if mode in ('chatgpt', 'apiKey', 'chatgptAuthTokens') else 'unknown'
    return {'signedIn': bool(account), 'authMode': mode,
            'chatgptAccount': mode == 'chatgpt'}


def schema_summary(root):
    def load(name):
        matches = list(root.rglob(name+'.json'))
        return json.loads(matches[0].read_text(encoding='utf-8')) if matches else {}
    turn, thread, command = (load(name) for name in
                            ('TurnStartParams','ThreadStartParams','CommandExecParams'))
    policies = command.get('definitions', {}).get('SandboxPolicy', {}).get('oneOf', [])
    read_policy = next((p for p in policies if
                        'readOnly' in p.get('properties', {}).get('type', {}).get('enum', [])), {})
    return {
        'structuredOutputField': 'outputSchema' in turn.get('properties', {}),
        'ephemeralThreadField': 'ephemeral' in thread.get('properties', {}),
        'interruptRequestSchema': bool(list(root.rglob('TurnInterruptParams.json'))),
        'readRootRestrictionInStableCommandSchema': 'access' in read_policy.get('properties', {}),
    }


def read_canary(rpc, cwd, path, marker):
    shell = Path(os.environ.get('SystemRoot', 'C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    quoted = str(path).replace("'", "''")
    result = rpc.request('command/exec', {
        'command':[str(shell),'-NoProfile','-NonInteractive','-Command',
                   f"Get-Content -LiteralPath '{quoted}' -ErrorAction Stop"],
        'cwd':str(cwd), 'sandboxPolicy':{'type':'readOnly','networkAccess':False},
        'timeoutMs':8000, 'outputBytesCap':1024,
    }, timeout=12)
    return {'commandSucceeded':result.get('exitCode') == 0,
            'markerRead':marker in result.get('stdout', '')}


def main():
    cli = shutil.which('codex')
    if not cli:
        print(json.dumps({'status':'unavailable','reason':'codex-not-on-path'}))
        return 1
    report = {'status':'incomplete', 'inferenceRequests':0, 'threadStarts':0,
              'sourceContentUsed':False, 'credentialFilesReadByProbe':False}
    rpc = None
    # Avoid a short-name TEMP alias when Windows creates the sandbox user.
    temp_parent = Path.home()/'AppData/Local/Temp' if os.name == 'nt' else None
    with tempfile.TemporaryDirectory(prefix='sessiondesk-codex-probe-', dir=temp_parent) as scratch:
        root = Path(scratch).resolve()
        inside, outside = root/'job-inputs', root/'outside-job'
        inside.mkdir(); outside.mkdir()
        (inside/'canary.txt').write_text('SYNTHETIC_INSIDE', encoding='utf-8')
        (outside/'canary.txt').write_text('SYNTHETIC_OUTSIDE', encoding='utf-8')
        try:
            report['cliVersion'] = subprocess.check_output([cli,'--version'], text=True, timeout=5).strip()
            generated = subprocess.run([cli,'app-server','generate-json-schema','--out',str(root/'schemas')],
                                       capture_output=True, text=True, timeout=20)
            if generated.returncode:
                raise RuntimeError('Schema generation failed')
            report['protocol'] = schema_summary(root/'schemas')
            rpc = ReadOnlyProbe(cli, inside)
            rpc.request('initialize', {'clientInfo':{'name':'session_desk_readiness','version':'0.0.0'}})
            rpc.send({'method':'initialized'})
            report['transportInitialized'] = True
            report['account'] = account_summary(rpc.request('account/read', {'refreshToken':False}))
            models = rpc.request('model/list', {'limit':20})
            report['catalogEntriesReturned'] = len(models.get('data', []))
            report['catalogIsEntitlementProof'] = False
            if os.name == 'nt':
                report['insideRead'] = read_canary(rpc, inside, inside/'canary.txt', 'SYNTHETIC_INSIDE')
                report['outsideJobRead'] = read_canary(rpc, inside, outside/'canary.txt', 'SYNTHETIC_OUTSIDE')
            report['status'] = 'read-only-probe-complete'
        except (OSError, RuntimeError, queue.Empty, subprocess.SubprocessError) as error:
            report['failureType'] = type(error).__name__
            if isinstance(error, RpcError):
                report['failedMethod'], report['rpcErrorCode'] = error.method, error.code
        finally:
            if rpc:
                rpc.close()
                report['childStopped'] = rpc.process.poll() is not None
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'read-only-probe-complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
