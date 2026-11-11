"""Opt-in local-library acceptance through the same HTTP jobs used by the UI.

Never run with real sources in CI. Reports contain inventory/validation counts,
not source text or artwork. Input and report paths must be explicit.
"""
import argparse
import http.client
import json
from pathlib import Path
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sessiondesk.importer import Library
from tools.smoke_core import call, launch


def wait(ready, jid):
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        state=call(ready,'job/status',{'job':jid})
        if state['state'] not in ('uploading','running','committing'):
            if state['state']!='complete':raise RuntimeError(state.get('error','Import stopped'))
            return state['result']
        time.sleep(.5)
    raise TimeoutError('Local import/backup exceeded its 10-minute verification deadline.')


def run(library_path, report_path, sources=None, exe=None):
    library=Library(library_path)
    wanted={s.lower() for s in sources.split(',')} if sources else None
    inventory=[x for x in library.inventory() if x['available'] and (wanted is None or x['id'].lower() in wanted)]
    if wanted and wanted!={x['id'].lower() for x in inventory}:
        raise ValueError('A requested source is not present in the selected local library.')
    results=[]
    report_path=Path(report_path).resolve();report_path.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='sessiondesk-owned-library-') as temp:
        base=Path(temp)
        with launch(base/'server',exe) as ready:
            print(f'Verifying {len(inventory)} selected adventures through import/export/restore jobs',flush=True)
            for index,item in enumerate(inventory,1):
                phase='create workspace'
                try:
                    workspace=call(ready,'workspace/create',{'name':'Local acceptance '+item['id'],'language':'English','rules':'2014'})
                    scope={'workspace':workspace['id']}
                    phase='import adventure'
                    job=call(ready,'import/start',{**scope,'path':str(library.root),'source':item['id']})
                    imported=wait(ready,job['id'])
                    aid=imported['id']
                    scope['adventure']=aid
                    graph=call(ready,'adventure',scope)
                    if graph['entries']:
                        call(ready,'prepare',{**scope,'entry':graph['entries'][0]['id'],'notes':'Original isolated acceptance note','translation':'','status':'draft'})
                    phase='export backup'
                    job=call(ready,'backup/export/start',scope)
                    result=wait(ready,job['id'])
                    backup=base/(item['id']+'.zip')
                    request=Request(ready['url']+'download/'+result['download']+'?token='+ready['token'])
                    with urlopen(request,timeout=60) as inp,backup.open('wb') as out:
                        while chunk:=inp.read(1024*1024):out.write(chunk)
                    phase='restore backup'
                    pending=call(ready,'backup/restore/start',{'size':backup.stat().st_size})
                    target=urlsplit(ready['url'])
                    connection=http.client.HTTPConnection(target.hostname,target.port,timeout=120)
                    try:
                        with backup.open('rb') as body:
                            connection.request('POST','/api/backup/upload/'+pending['id'],body=body,headers={
                                'Content-Type':'application/zip','Content-Length':str(backup.stat().st_size),
                                'Authorization':'Bearer '+ready['token'],'Origin':ready['url'].rstrip('/')})
                            response=connection.getresponse();payload=json.load(response)
                            if response.status!=200:raise RuntimeError(payload.get('error','Restore upload failed'))
                    finally:connection.close()
                    restored=wait(ready,pending['id'])
                    phase='validate restored adventure'
                    copy=call(ready,'adventure',{'workspace':restored['id'],'adventure':aid})
                    assert graph['fingerprint']==copy['fingerprint']
                    assert len(graph['entries'])==len(copy['entries'])
                    assert len(graph['maps'])==len(copy['maps']) and len(graph['pictures'])==len(copy['pictures'])
                    if graph['entries']:assert copy['preparation'][graph['entries'][0]['id']]['notes']=='Original isolated acceptance note'
                    results.append({'id':item['id'],'name':item['name'],'status':'passed','entries':len(graph['entries']),
                        'dm_maps':sum(m.get('image_type')!='mapPlayer' for m in graph['maps']),
                        'pictures':len(graph['pictures']),'regions':sum(len(m['regions']) for m in graph['maps']),
                        'warnings':len(graph['warnings']),'portable_backup_bytes':backup.stat().st_size})
                except Exception as exc:
                    results.append({'id':item['id'],'status':'failed','phase':phase,'error':str(exc)})
                report={'library_version':library.validate()['version'],'runtime':'frozen-exe' if exe else 'source',
                    'complete':index==len(inventory),'seconds':round(time.monotonic()-started,1),'adventures':results}
                report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                if index%10==0 or results[-1]['status']=='failed':
                    print(f'{index}/{len(inventory)} checked; failures={sum(r["status"]=="failed" for r in results)}',flush=True)
    summary={'checked':len(results),'passed':sum(r['status']=='passed' for r in results),
             'failed':[r for r in results if r['status']=='failed'],'warnings':sum(r.get('warnings',0) for r in results),
             'report':str(report_path)}
    print(json.dumps(summary,indent=2),flush=True)
    return not summary['failed']


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--sources')
    parser.add_argument('--exe',type=Path)
    args=parser.parse_args()
    raise SystemExit(0 if run(args.library,args.report,args.sources,args.exe) else 1)
