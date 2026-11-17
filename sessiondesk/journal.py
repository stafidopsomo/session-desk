"""Revisioned DM campaign book. Inert module data survives older backup readers."""
import copy
import hashlib
import json
import re
import uuid
from .importer import UserError, stable
from .workspace_modules import MODULE_ID, local, materialize, read, supported

ID = stable('sessiondesk-module', 'campaign-journal-v1')
KEY = 'module:' + ID
STATUSES = ('Draft', 'Offered', 'Active', 'Resolved', 'Set aside')

def validate(book):
    if not isinstance(book, dict) or book.get('schemaVersion') != 1:
        raise UserError('Unsupported campaign book version.')
    if not isinstance(book.get('title'),str) or len(book['title'])>200: raise UserError('Invalid campaign book title.')
    for key in ('chapters', 'entries', 'missions', 'party'):
        items = book.get(key, [])
        if not isinstance(items, list) or len(items) > 3000:
            raise UserError('Campaign book exceeds supported limits.')
        seen = set()
        for item in items:
            ident = item.get('id') if isinstance(item, dict) else None
            if not isinstance(ident, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', ident) or ident in seen:
                raise UserError('Invalid or duplicate campaign book record.')
            seen.add(ident)
            if type(item.get('revision',0)) is not int or item.get('revision',0)<0: raise UserError('Invalid record revision.')
            title=item.get('title') if key!='party' else item.get('name')
            if not isinstance(title,str) or len(title)>2000: raise UserError('Invalid record title.')
    chapters={c['id'] for c in book.get('chapters',[])}
    if any(e.get('chapter') not in chapters or not isinstance(e.get('text',''),str) for e in book.get('entries',[])): raise UserError('Invalid book chapter or text.')
    if any(m.get('status') not in STATUSES for m in book.get('missions',[])): raise UserError('Invalid mission status.')
    if len(json.dumps(book, ensure_ascii=False, allow_nan=False).encode()) > 4000000:
        raise UserError('Campaign book exceeds 4 MB.')
    return book

def _seed(store, wid, conn):
    meta = store.get(conn, 'meta')
    book = {'schemaVersion':1, 'title':meta['name'], 'chapters':[
        {'id':'now','title':'Now'}, {'id':'chronicle','title':'Chronicle'},
        {'id':'places','title':'Places and people'}, {'id':'preparation','title':'Preparation'},
        {'id':'ideas','title':'Private ideas'}], 'entries':[], 'missions':[], 'party':[]}
    book['sessionMode']=meta.get('session_mode','campaign')
    if book['sessionMode']=='oneshot': book['chapters']=[{'id':'now','title':'Run this session'},{'id':'preparation','title':'Preparation'},{'id':'notes','title':'Session notes'}]
    legacy = store.get(conn, 'module:' + MODULE_ID)
    if legacy and supported(legacy):
        root = materialize(store.folder(wid), MODULE_ID, legacy)
        authored = read(local(root, 'data/campaign-book.json'))
        if authored:
            book.update(copy.deepcopy(authored))
            book['schemaVersion'] = 1
        book['migratedFrom'] = 'module:' + MODULE_ID
        scenes = read(local(root, 'data/after-citadel.json'), {}).get('scenes', [])
        if scenes:
            book['chapters'].append({'id':'legacy-preparation','title':'Earlier preparation'})
            for scene in scenes:
                ident = 'legacy-' + str(scene.get('id', uuid.uuid4().hex))
                if any(e['id'] == ident for e in book['entries']): continue
                lines = [str(scene.get('summary',''))]
                for name in ('readAloudGr','run','clues','dialogueGr','notes'):
                    value = scene.get(name)
                    if value:
                        lines += [name, '\n'.join(str(x) for x in value) if isinstance(value,list) else str(value)]
                book['entries'].append({'id':ident,'chapter':'legacy-preparation','title':scene.get('title','Earlier scene'),
                    'text':'\n\n'.join(lines), 'status':'prepared','kind':'scene','visibility':'dm',
                    'source':{'module':MODULE_ID,'path':'data/after-citadel.json','scene':scene.get('id')}})
    for group in ('entries','missions','party'):
        for item in book.get(group, []): item.setdefault('revision',0)
    book.setdefault('party', [])
    return validate(book)

def get(store, wid):
    with store.lock, store.db(wid) as conn:
        module = store.get(conn, KEY)
        if module: return copy.deepcopy(validate(module['journal']))
        book = _seed(store,wid,conn)
        _put(store,conn,book)
        return copy.deepcopy(book)

def _put(store,conn,book):
    validate(book)
    store.put(conn,KEY,{'kind':'campaign-journal','schema':1,'enabled':True,
        'title':book['title'][:200],'files':{},'journal':book})

def patch(store,wid,body):
    get(store,wid)
    with store.lock, store.db(wid) as conn:
        book = store.get(conn,KEY)['journal']
        group = body.get('collection')
        if group not in ('entries','missions','party'): raise UserError('Unknown book collection.')
        ident = body.get('id')
        item = next((e for e in book[group] if e['id']==ident),None)
        if body.get('create'):
            if item: raise UserError('Record already exists.')
            ident = str(uuid.uuid4())
            item = {'id':ident,'revision':0}
            if group=='entries': item.update(chapter='now',title='New entry',text='',status='prepared',kind='note',visibility='dm')
            if group=='missions': item.update(title='New mission',status='Draft',objective='',nextStep='',giver='',outcome='',reward={'offered':None,'awarded':None})
            if group=='party': item.update(name='New character',level=1,**{'class':'Class not set'},notes='',threads=[],sheet={})
            book[group].append(item)
        elif not item or type(body.get('revision')) is not int or body['revision'] != item.get('revision',0):
            raise UserError('This record changed in another tab. Your draft is kept. Copy it before reloading the current record.')
        fields = body.get('fields')
        allowed = {'entries':{'title','text','chapter','status','kind','visibility'},
            'missions':{'title','status','objective','nextStep','giver','outcome','reward'},
            'party':{'name','notes','level','class','race','concept'}}[group]
        if not isinstance(fields,dict) or not fields or set(fields)-allowed: raise UserError('Unknown book field.')
        for key,value in fields.items():
            if key=='reward':
                if not isinstance(value,dict) or set(value)-{'offered','awarded'} or any(v is not None and (not isinstance(v,str) or len(v)>10000) for v in value.values()): raise UserError('Invalid reward record.')
            elif key=='level':
                if type(value) is not int or not 1<=value<=20: raise UserError('Level must be 1–20.')
            elif not isinstance(value,str) or len(value)>100000: raise UserError('Book text exceeds supported limits.')
        if group=='missions' and fields.get('status',item.get('status')) not in STATUSES: raise UserError('Unknown mission status.')
        if group=='entries' and (fields.get('chapter',item.get('chapter')) not in {c['id'] for c in book['chapters']} or fields.get('visibility','dm')!='dm'): raise UserError('Choose a chapter. Book editing is DM-only in this preview.')
        if 'reward' in fields: fields={**fields,'reward':{**item.get('reward',{}),**fields['reward']}}
        item.update(fields); item['revision']+=1
        _put(store,conn,book)
        return copy.deepcopy(item)

def party(app,wid,body=None):
    from . import prepared_characters
    with app.store.lock:
        with app.store.db(wid) as conn: module=app.store.get(conn,'module:'+MODULE_ID)
        if module and supported(module):
            runtime=app.prepared(wid); root=runtime.workspace.path('characters')
            if body:
                ident=body.get('id','')
                if not isinstance(ident,str) or not re.fullmatch('[a-z0-9-]+',ident): raise UserError('Invalid character.')
                file=root/ident/'character.json'
                if not file.is_file() or body.get('revision')!=hashlib.sha256(file.read_bytes()).hexdigest():
                    raise UserError('Character changed in another tab. Your draft is kept; copy it before reloading.')
                if body.get('field') not in ('name','notes','concept'): raise UserError('Use the full sheet for mechanical changes.')
                prepared_characters.update(root,body,runtime.workspace.reference)
            records=prepared_characters.records(root)['characters']
            for c in records: c['revision']=hashlib.sha256((root/c['id']/'character.json').read_bytes()).hexdigest()
            return {'characters':records,'legacy':True}
        book=get(app.store,wid)
        return {'characters':book.get('party',[]),'legacy':False}
