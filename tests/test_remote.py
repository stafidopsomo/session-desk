import copy,json,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
from sessiondesk.remote import RemoteHost,PORT
from sessiondesk.server import Application,make_server
from sessiondesk.store import Store
from sessiondesk.importer import Library,UserError
from tests.fixtures import make_library

class FakeTailscale:
    def __init__(self):self.rules={};self.calls=[];self.state='Running'
    def __call__(self,args):
        self.calls.append(args)
        if args==['status','--json']:return json.dumps({'BackendState':self.state,'Self':{'DNSName':'host.original.ts.net.'}})
        if args==['serve','status','--json']:return json.dumps(self.rules)
        if args[-1]=='off':self.rules={};return ''
        self.rules={'TCP':{str(PORT):{'HTTPS':True}},'Web':{'host.original.ts.net:'+str(PORT):{'Handlers':{'/':{'Proxy':args[-1]}}}}};return ''

class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.cli=FakeTailscale();self.remote=RemoteHost(self.root,self.cli)
    def test_enable_resume_link_and_disable_only_owned_port(self):
        status=self.remote.start(12345);link=status['url'];self.assertTrue(status['online']);self.assertTrue(link.startswith('https://host.original.ts.net:8443/connect/'))
        restart=RemoteHost(self.root,self.cli);restart.resume(23456);self.assertEqual(restart.status()['url'],link)
        self.assertFalse(any('funnel' in a or 'reset' in a for args in self.cli.calls for a in args))
        restart.stop();self.assertFalse(restart.status()['enabled']);self.assertNotIn('key',restart.config)
    def test_foreign_rule_is_never_replaced_or_deleted(self):
        self.cli.rules={'TCP':{str(PORT):{'HTTPS':True}},'Web':{'host.original.ts.net:8443':{'Handlers':{'/':{'Proxy':'http://127.0.0.1:9999'}}}}}
        initial=copy.deepcopy(self.cli.rules)
        with self.assertRaises(UserError):self.remote.start(12345)
        self.assertEqual(self.cli.rules,initial)
        with self.assertRaises(UserError):self.remote.stop()
        self.assertEqual(self.cli.rules,initial)
    def test_logged_out_or_public_funnel_fails_closed(self):
        self.cli.state='NeedsLogin'
        with self.assertRaises(UserError):self.remote.start(12345)
        self.assertIsNone(self.remote.origin)
        self.cli.state='Running';self.cli.rules={'AllowFunnel':{'host.original.ts.net:8443':True}}
        with self.assertRaises(UserError):self.remote.start(12345)
        self.assertIsNone(self.remote.origin)
    def test_shutdown_removes_owned_rule_after_confirmation_error(self):
        confirmation_fails=True
        def cli(args):
            nonlocal confirmation_fails
            if confirmation_fails and self.cli.rules and args==['serve','status','--json']:
                confirmation_fails=False
                raise UserError('Original transient confirmation error.')
            return self.cli(args)
        remote=RemoteHost(self.root,cli)
        with self.assertRaises(UserError):remote.start(12345)
        self.assertFalse(remote.active)
        self.assertIn(str(PORT),self.cli.rules['TCP'])
        remote.shutdown()
        self.assertEqual(self.cli.rules,{})
        self.assertTrue(remote.status()['enabled'])
        remote.resume(23456)
        self.assertEqual(self.cli.rules,{})

    def test_default_off_does_not_call_cli(self):
        self.remote.resume(12345);self.assertEqual(self.cli.calls,[]);self.assertIsNone(self.remote.origin)
    def test_http_origin_auth_and_host_controls(self):
        app=Application(Store(self.root));app.remote=self.remote;server=make_server(app)
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever,daemon=True).start();self.remote.start(server.server_port)
        local='http://127.0.0.1:'+str(server.server_port);remote=self.remote.origin
        def request(path,origin=remote,host='host.original.ts.net:8443',token=None,data=None):
            req=Request(local+path,json.dumps(data or {}).encode(),{'Content-Type':'application/json','Host':host,'Origin':origin,'Authorization':'Bearer '+(token or app.dm_token)})
            return json.load(urlopen(req,timeout=5))
        self.assertTrue(request('/api/bootstrap')['remote_client'])
        wid=app.store.create('Original remote presentation')['id']
        graph,blobs=Library(make_library(self.root/'original-library')).load('DEMO')
        app.store.import_graph(wid,graph,blobs)
        media=next(m for m in graph['maps'] if m.get('image_type')!='mapPlayer')
        scope={'workspace':wid,'adventure':graph['id']}
        request('/api/session/action',data=scope|{'action':'present','media':media['id'],'with_fog':True})
        state=request('/api/presentation',token=app.player_token,data=scope)
        self.assertEqual(state,{'tabs':[{'source':graph['id'],'id':media['id'],'title':media['name']}],
                               'active':{'source':graph['id'],'id':media['id']}})
        with self.assertRaises(HTTPError):
            request('/api/presentation/action',token=app.player_token,data=scope|{'action':'present'})
        with urlopen(Request(local+'/?view=player&embed=1',headers={'Host':'host.original.ts.net:8443'}),timeout=5) as frame:
            self.assertIn("frame-ancestors 'self'", frame.headers['Content-Security-Policy'])
        request('/api/presentation/action',token=app.player_token,data=scope|{'action':'close_all'})
        self.assertEqual(request('/api/presentation',token=app.player_token,data=scope)['tabs'],[])
        self.assertFalse(request('/api/bootstrap',origin=local,host='127.0.0.1:'+str(server.server_port))['remote_client'])
        for path,options in [('/api/bootstrap',{'origin':'https://evil.invalid'}),('/api/bootstrap',{'host':'evil.invalid'}),('/api/bootstrap',{'token':app.player_token}),('/api/remote/disable',{}),('/api/pick-folder',{})]:
            with self.assertRaises(HTTPError):request(path,**options)
        self.assertTrue(request('/api/remote/status',origin=local,host='127.0.0.1:'+str(server.server_port))['online'])
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self,*args):return None
        link=Request(local+'/connect/'+self.remote.config['key'],headers={'Host':'host.original.ts.net:8443'})
        with self.assertRaises(HTTPError) as result:build_opener(NoRedirect()).open(link,timeout=5)
        self.assertEqual(result.exception.code,303);self.assertEqual(result.exception.headers['Location'],'/#dm='+app.dm_token)
        self.assertFalse(app.should_exit(now=app.started+1000))
        self.remote.stop()
        with self.assertRaises(HTTPError):request('/api/bootstrap')
