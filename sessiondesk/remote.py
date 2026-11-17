"""Opt-in private Tailscale Serve; no LAN bind, Funnel, or cloud data copies."""
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import threading
from .importer import UserError

PORT=8443

class RemoteHost:
    def __init__(self,root,run=None):
        self.path=Path(root)/'remote-host.json';self.lock=threading.RLock();self.error='';self.active=False
        self.run=run or self._run
        self.config={}
        try:
            if self.path.is_symlink() or self.path.stat().st_size>16000:raise ValueError()
            self.config=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(self.config,dict):self.config={}
        except (OSError,ValueError):pass
        self.local_port=None
    def _run(self,args):
        exe=Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Tailscale/tailscale.exe'
        if not exe.is_file():raise UserError('Install Tailscale on this host and sign in first.')
        try:r=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=25,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except (OSError,subprocess.TimeoutExpired) as exc:raise UserError('Tailscale did not respond. Check its tray app and HTTPS/Serve permissions, then retry.') from exc
        if r.returncode:raise UserError('Tailscale could not configure private hosting. Check that you are signed in and Serve/HTTPS is enabled for this device.')
        return r.stdout
    def save(self):
        if self.path.is_symlink() or self.path.with_suffix('.tmp').is_symlink():raise UserError('Hosting settings cannot be linked.')
        temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.config),encoding='utf-8');temp.replace(self.path)
    @property
    def origin(self):
        name=self.config.get('hostname','')
        return 'https://'+name+':'+str(PORT) if self.active and re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.ts\.net',name) else None
    def status(self,include_link=True):
        result={'enabled':self.config.get('enabled') is True,'online':bool(self.origin),'error':self.error,
            'origin':self.origin,'port':PORT}
        if include_link and self.origin:result['url']=self.origin+'/connect/'+self.config['key']
        return result
    def _rules(self):
        raw=json.loads(self.run(['serve','status','--json']) or '{}')
        if not isinstance(raw,dict):raise UserError('Invalid Tailscale Serve configuration.')
        return raw
    def _owned(self,rules):
        name=self.config.get('hostname','')+':'+str(PORT)
        web=rules.get('Web',{}).get(name)
        if web is None:return False
        targets=[self.config.get('target_port'),self.config.get('previous_port')]
        expected=[{'Handlers':{'/':{'Proxy':'http://127.0.0.1:'+str(port)}}} for port in targets if type(port) is int]
        if web not in expected:raise UserError('Port 8443 is already used by another Tailscale service; its configuration was left unchanged.')
        return True
    def start(self,port):
        with self.lock:
            self.local_port=port;self.error=''
            try:
                state=json.loads(self.run(['status','--json']))
                if state.get('BackendState')!='Running':raise UserError('Sign in to Tailscale on the host first.')
                name=str(state.get('Self',{}).get('DNSName','')).rstrip('.').lower()
                if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.ts\.net',name):raise UserError('Enable MagicDNS and HTTPS for this Tailscale device.')
                rules=self._rules();old_name=self.config.get('hostname')
                if old_name and old_name!=name:raise UserError('The Tailscale hostname changed. Disable hosting before reconnecting it.')
                self.config['hostname']=name
                self._owned(rules)
                # Never replace any existing port-level configuration we do not own.
                if str(PORT) in rules.get('TCP',{}) and not self._owned(rules):raise UserError('Tailscale port 8443 is in use by another service.')
                if rules.get('AllowFunnel',{}).get(name+':'+str(PORT)):raise UserError('Public Funnel is enabled on port 8443. Disable it before using private hosting.')
                self.config['previous_port']=self.config.get('target_port')
                self.config.update(enabled=True,target_port=port,key=self.config.get('key') or secrets.token_urlsafe(32));self.save()
                self.run(['serve','--bg','--https='+str(PORT),'http://127.0.0.1:'+str(port)])
                if not self._owned(self._rules()):raise UserError('Tailscale did not confirm the private endpoint.')
                self.active=True
            except (ValueError,KeyError,TypeError,UserError) as exc:
                self.error=str(exc);self.active=False;raise UserError(self.error) from exc
            return self.status()
    def stop(self,disable=True):
        with self.lock:
            if self.config.get('hostname'):
                rules=self._rules()
                if self._owned(rules):self.run(['serve','--https='+str(PORT),'off'])
            self.active=False;self.error=''
            if disable:self.config['enabled']=False;self.config.pop('key',None);self.config.pop('hostname',None);self.save()
            return self.status()
    def resume(self,port):
        self.local_port=port
        if self.config.get('enabled'):
            try:self.start(port)
            except UserError:pass
