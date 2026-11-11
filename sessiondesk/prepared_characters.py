"""Canonical private DM records live under characters/<id>/character.json."""
import json
import re
from pathlib import Path
from .prepared_rules import ABILITIES, SKILLS, database

THREAD_STATUSES=('Idea','Seeded','Active','Done','Dropped')
THREAD_FIELDS=('title','status','next','where','notes','source','link')

def records(root):
    result=[]
    for file in sorted(Path(root).glob('*/character.json')):
        c=json.loads(file.read_text(encoding='utf-8-sig'))
        if c.get('id')!=file.parent.name:raise ValueError('Character folder and id disagree')
        c['backstory']= (file.parent/'backstory.md').read_text(encoding='utf-8') if (file.parent/'backstory.md').exists() else ''
        c['hooks']= (file.parent/'campaign-hooks.md').read_text(encoding='utf-8') if (file.parent/'campaign-hooks.md').exists() else ''
        result.append(c)
    return {'characters':result}

def clean_threads(value):
    if not isinstance(value,list) or len(value)>100:raise ValueError('Expected a list of threads')
    result=[]
    for thread in value:
        if not isinstance(thread,dict) or set(thread)-set(THREAD_FIELDS):raise ValueError('Unknown thread field')
        if thread.get('status') not in THREAD_STATUSES:raise ValueError('Invalid thread status')
        clean={key:thread.get(key,'') for key in THREAD_FIELDS}
        if any(not isinstance(v,str) or len(v)>20000 for v in clean.values()):raise ValueError('Invalid thread text')
        if clean['link'] and not clean['link'].startswith('/reference/'):raise ValueError('Thread links must point to the local reference library')
        result.append(clean)
    return result

def update(root,body,reference):
    ident=body.get('id','')
    if not isinstance(ident,str) or not re.fullmatch(r'[a-z0-9-]+',ident):raise ValueError('Invalid character id')
    file=Path(root)/ident/'character.json'
    if not file.is_file():raise ValueError('Unknown character')
    c=json.loads(file.read_text(encoding='utf-8-sig'));field=body.get('field');value=body.get('value')
    if field=='sheet':
        if not isinstance(value,dict):raise ValueError('Expected sheet fields')
        allowed={'classKey','subclassKey','raceKey','subraceKey','scores','saves','skills','ac','hpMax','hpCurrent','hpTemp','speed','armorModel','resources','featureNotes','selectedFeatures','selectedSpells','disabledFeatures','castingAbility'}
        if set(value)-allowed:raise ValueError('Unknown sheet field')
        db=database(str(reference));sheet={**c.get('sheet',{}),**value}
        for key,group in [('classKey','classes'),('subclassKey','subclasses'),('raceKey','races'),('subraceKey','subraces')]:
            if sheet.get(key) and sheet[key] not in db[group]:raise ValueError('Unknown rules source: '+key)
        cls=db['classes'].get(sheet.get('classKey'));sub=db['subclasses'].get(sheet.get('subclassKey'))
        if sub and (not cls or sub['className']!=cls['name'] or sub.get('classSource','PHB')!=cls['source']):raise ValueError('Subclass does not match class')
        race=db['races'].get(sheet.get('raceKey'));sr=db['subraces'].get(sheet.get('subraceKey'))
        if sr and (not race or sr['raceName']!=race['name'] or sr.get('raceSource','PHB')!=race['source']):raise ValueError('Subrace does not match race')
        for key in ('scores','skills','saves'):
            values=sheet.get(key,{})
            if not isinstance(values,dict):raise ValueError('Invalid '+key)
            for k,v in values.items():
                if key=='scores' and (k not in ABILITIES or v is not None and (type(v)!=int or not 1<=v<=30)):raise ValueError('Ability scores must be 1–30 or blank')
                if key=='skills' and (k not in SKILLS or type(v)!=int or v not in (0,1,2)):raise ValueError('Invalid skill proficiency')
                if key=='saves' and (k not in ABILITIES or type(v)!=bool):raise ValueError('Invalid saving throw proficiency')
        for k in ('ac','hpMax','hpCurrent','hpTemp','speed'):
            v=sheet.get(k)
            if v is not None and (type(v)!=int or not 0<=v<=9999):raise ValueError('Tracking values must be 0–9999 or blank')
        for k in ('armorModel','resources','featureNotes','castingAbility'):
            if k in sheet and (not isinstance(sheet[k],str) or len(sheet[k])>20000):raise ValueError('Invalid sheet text')
        if sheet.get('castingAbility','') not in ('',*ABILITIES):raise ValueError('Invalid spellcasting ability')
        for k,g in [('selectedFeatures','optional'),('selectedSpells','spells'),('disabledFeatures',None)]:
            if k in sheet and (not isinstance(sheet[k],list) or len(sheet[k])>300 or any(not isinstance(x,str) or len(x)>500 or g and x not in db[g] for x in sheet[k])):raise ValueError('Invalid selected references')
        c['sheet']=sheet
        c['class']=cls['name']+(' · '+sub['name'] if sub else '') if cls else 'Class not set'
    elif field=='level':
        if type(value)!=int or not 1<=value<=20:raise ValueError('Level must be 1–20')
        c[field]=value
    elif field=='renown':
        if value is not None and (type(value)!=int or not 0<=value<=9999):raise ValueError('Invalid renown')
        c[field]=value
        if c.get('faction')=='Gray Hands' and value is not None:
            c['rank']=next((name for threshold,name in [(50,'Defender of Waterdeep'),(25,'Force Grey Initiate'),(10,'Senior Gray Hand'),(3,'Junior Gray Hand'),(1,'Gray Hand Initiate')] if value>=threshold),'Unranked member')
    elif field=='threads':
        c['threads']=clean_threads(value)
    elif field in ('name','player','race','background','concept','home','faction','patron','patronNote','contact','notes'):
        if not isinstance(value,str) or len(value)>20000:raise ValueError('Invalid character text')
        c[field]=value
    else:raise ValueError('Unknown character field')
    tmp=file.with_suffix('.tmp');tmp.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(file)
    return records(root)
