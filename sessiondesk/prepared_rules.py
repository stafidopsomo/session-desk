"""Read-only adapter for an explicitly selected, classic-edition 5e.tools rules."""
import copy
import json
from functools import lru_cache
from pathlib import Path

ABILITIES = ('str', 'dex', 'con', 'int', 'wis', 'cha')
SKILLS = {'Acrobatics':'dex','Animal Handling':'wis','Arcana':'int','Athletics':'str','Deception':'cha','History':'int','Insight':'wis','Intimidation':'cha','Investigation':'int','Medicine':'wis','Nature':'int','Perception':'wis','Performance':'cha','Persuasion':'cha','Religion':'int','Sleight of Hand':'dex','Stealth':'dex','Survival':'wis'}

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}

def classic(x):
    return x.get('edition') != 'one' and x.get('source') not in ('XPHB','XDMG','XMM','EFA') and not x.get('source','').startswith('UA') and not x.get('_copy')

def class_key(x): return f"{x['name']}|{x['source']}"
def subclass_key(x): return f"{x['shortName']}|{x['className']}|{x.get('classSource','PHB')}|{x['source']}"
def race_key(x): return f"{x['name']}|{x['source']}"
def subrace_key(x): return f"{x['name']}|{x['source']}|{x['raceName']}|{x.get('raceSource','PHB')}"

def feature_key(x, sub=False):
    parts=[x['name'],x['className'],x.get('classSource','PHB')]
    if sub: parts += [x['subclassShortName'],x.get('subclassSource','PHB')]
    return '|'.join(parts+[str(x['level']),x.get('source',x.get('subclassSource',x.get('classSource','PHB')))]).lower()

def reference_key(uid, sub=False):
    p=uid.split('|');p += ['']*((7 if sub else 5)-len(p));p[2]=p[2] or 'PHB'
    if sub:p[4]=p[4] or 'PHB';p[6]=p[6] or p[4]
    else:p[4]=p[4] or p[2]
    return '|'.join(p[:7 if sub else 5]).lower()

@lru_cache(maxsize=2)
def database(reference):
    base=Path(reference)/'data';classes={};subclasses={};features={};subfeatures={}
    # Several new books omit per-entry edition flags; use source publication
    # metadata as well, so a growing local library cannot mix in 2024 species.
    source_ids={'EEPC','PSK','PSA','PSD','PSZ','PSI','PSX','OGA','LR','TTP'}
    for filename,group in [('books.json','book'),('adventures.json','adventure')]:
        source_ids.update(x['id'] for x in load(base/filename).get(group,[]) if x.get('published','9999')<'2024-09-01')
    def allowed(x):return classic(x) and x.get('source') in source_ids
    for path in sorted((base/'class').glob('class-*.json')):
        d=load(path)
        for c in d.get('class',[]):
            if allowed(c):classes[class_key(c)]=c
        for c in d.get('subclass',[]):
            if allowed(c):subclasses[subclass_key(c)]=c
        for c in d.get('classFeature',[]):
            if not c.get('_copy'):features[feature_key(c)]=c
        for c in d.get('subclassFeature',[]):
            if not c.get('_copy'):subfeatures[feature_key(c,True)]=c
    r=load(base/'races.json')
    races={race_key(x):x for x in r.get('race',[]) if allowed(x)}
    subraces={subrace_key(x):x for x in r.get('subrace',[]) if allowed(x) and x.get('raceName') and x.get('name')}
    optional={race_key(x):x for x in load(base/'optionalfeatures.json').get('optionalfeature',[]) if allowed(x)}
    for x in load(base/'feats.json').get('feat',[]):
        if allowed(x):optional[race_key(x)]={**x,'featureType':['Feat'],'referencePage':'feats'}
    spells={}
    for path in sorted((base/'spells').glob('spells-*.json')):
        for x in load(path).get('spell',[]):
            if allowed(x):spells[race_key(x)]=x
    return dict(classes=classes,subclasses=subclasses,features=features,subfeatures=subfeatures,races=races,subraces=subraces,optional=optional,spells=spells)

def options(reference):
    db=database(str(reference))
    def short(group):return [{'key':key,'name':x['name'],'source':x['source'],**{k:x[k] for k in ('className','classSource','raceName','raceSource','featureType','prerequisite') if k in x}} for key,x in db[group].items() if group!='subclasses' or f"{x['className']}|{x.get('classSource','PHB')}" in db['classes']]
    return {k:short(k) for k in ('classes','subclasses','races','subraces','optional','spells')}

def expand(value,db,seen=None):
    seen=seen or set()
    if isinstance(value,list):return [expand(v,db,seen) for v in value]
    if not isinstance(value,dict):return value
    for field,group,sub in [('classFeature','features',False),('subclassFeature','subfeatures',True)]:
        if value.get('type')=='ref'+field[0].upper()+field[1:]:
            key=reference_key(value[field],sub)
            if key in seen:return {'name':'Repeated reference','entries':[value[field]]}
            found=db[group].get(key)
            return expand(found,db,seen|{key}) if found else {'name':'Reference unavailable','entries':[value[field]]}
    if value.get('type')=='refOptionalfeature':
        uid=value.get('optionalfeature','');parts=uid.split('|');key=parts[0]+'|'+(parts[1] if len(parts)>1 and parts[1] else 'PHB')
        return expand(db['optional'].get(key,{'entries':[uid]}),db,seen|{key}) if key not in seen else {'entries':[uid]}
    return {k:expand(v,db,seen) for k,v in value.items() if k in ('name','type','entries','entry','items','rows','colLabels','caption','text','roll','exact','min','max','choose','from','count','style','source','level','page','prerequisite','featureType','amount','toRoll','number','faces')}

def calculated(character):
    sheet=character.get('sheet',{});scores=sheet.get('scores',{});level=character['level'];pb=2+(level-1)//4
    mods={a:(scores[a]-10)//2 if scores.get(a) is not None else None for a in ABILITIES}
    def bonus(a,n):return None if mods[a] is None else mods[a]+pb*n
    return {'proficiency':pb,'modifiers':mods,'saves':{a:bonus(a,int(bool(sheet.get('saves',{}).get(a)))) for a in ABILITIES},'skills':{s:bonus(a,sheet.get('skills',{}).get(s,0)) for s,a in SKILLS.items()},'initiative':mods['dex'],'passivePerception':None if bonus('wis',sheet.get('skills',{}).get('Perception',0)) is None else 10+bonus('wis',sheet.get('skills',{}).get('Perception',0))}

def rules(character,reference):
    db=database(str(reference));s=character.get('sheet',{});level=character['level'];c=db['classes'].get(s.get('classKey'));sub=db['subclasses'].get(s.get('subclassKey'));race=db['races'].get(s.get('raceKey'));sr=db['subraces'].get(s.get('subraceKey'));result={'features':[],'tables':[],'warnings':[],'calculated':calculated(character)}
    def add(x,kind,key):
        if x:result['features'].append({'key':key,'name':x.get('name','Feature'),'level':x.get('level'),'source':x.get('source',''),'kind':kind,'referencePage':x.get('referencePage'),'content':expand(x,db)})
        else:result['warnings'].append('Unresolved source feature: '+key)
    if c:
        for ref in c.get('classFeatures',[]):
            uid=ref if isinstance(ref,str) else ref.get('classFeature','');x=db['features'].get(reference_key(uid))
            if x and x['level']<=level:add(x,'Class',uid)
            elif not x:result['warnings'].append('Unresolved source feature: '+uid)
        result['classInfo']={k:c[k] for k in ('name','source','hd','proficiency','startingProficiencies','spellcastingAbility','casterProgression') if k in c}
    if sub and c and sub.get('className')==c['name'] and sub.get('classSource','PHB')==c['source']:
        for uid in sub.get('subclassFeatures',[]):
            x=db['subfeatures'].get(reference_key(uid,True))
            if x and x['level']<=level:add(x,'Subclass',uid)
            elif not x:result['warnings'].append('Unresolved source feature: '+uid)
    if c:
        progression=[]
        for n in range(1,21):
            names=[]
            for ref in c.get('classFeatures',[]):
                uid=ref if isinstance(ref,str) else ref.get('classFeature','');f=db['features'].get(reference_key(uid))
                if f and f['level']==n:names.append(f['name'])
            for uid in (sub or {}).get('subclassFeatures',[]):
                f=db['subfeatures'].get(reference_key(uid,True))
                if f and f['level']==n:names.append(f['name'])
            progression.append(['+'+str(2+(n-1)//4),', '.join(names) or '—'])
        result['tables'].append({'title':'Class features by level','colLabels':['Proficiency','Features'],'rows':progression,'currentLevel':level})
    for owner in [c,sub]:
        for group in (owner or {}).get('classTableGroups',[])+ (owner or {}).get('subclassTableGroups',[]):
            rows=group.get('rows',group.get('rowsSpellProgression',[]))
            if rows:result['tables'].append({'title':group.get('title','Class progression'),'colLabels':group.get('colLabels',[]),'rows':rows,'currentLevel':level})
    if race:
        entries=copy.deepcopy(race.get('entries',[]))
        if sr and sr['raceName']==race['name'] and sr.get('raceSource','PHB')==race['source']:
            for e in sr.get('entries',[]):
                target=e.get('data',{}).get('overwrite') if isinstance(e,dict) else None
                entries=[x for x in entries if not target or not isinstance(x,dict) or x.get('name')!=target]
                entries.append(e)
        for i,e in enumerate(entries):
            e=copy.deepcopy(e) if isinstance(e,dict) else {'name':'Racial trait','entries':[e]}
            e.setdefault('source',sr['source'] if sr and any(isinstance(v,dict) and v.get('name')==e.get('name') for v in sr.get('entries',[])) else race['source'])
            add(e,'Race','race:'+str(i))
        result['raceInfo']={k:race[k] for k in ('name','source','speed','darkvision','resist','languageProficiencies') if k in race}
        if sr:result['raceInfo']['subrace']=sr['name'];result['raceInfo']['subraceSource']=sr['source']
    for key in s.get('selectedFeatures',[]):add(db['optional'].get(key),'Chosen option',key)
    racial_spells=[]
    for grant in (sr if sr and sr.get('additionalSpells') else race or {}).get('additionalSpells',[]):
        def gather(value):
            if isinstance(value,str):racial_spells.append(value)
            elif isinstance(value,list):
                for v in value:gather(v)
            elif isinstance(value,dict):
                for k,v in value.items():
                    if not k.isdigit() or int(k)<=level:gather(v)
        for group in ('known','innate','prepared'):gather(grant.get(group,{}))
    racial_keys=[]
    for uid in racial_spells:
        parts=uid.split('#')[0].split('|');key=next((key for key in db['spells'] if key.lower()==(parts[0]+'|'+(parts[1] if len(parts)>1 else 'PHB')).lower()),None)
        if key:racial_keys.append(key)
    def describe_spell(spell):
        times=', '.join(str(t.get('number',1))+' '+t.get('unit','')+(' ('+t['condition']+')' if t.get('condition') else '') for t in spell.get('time',[]))
        rg=spell.get('range',{});distance=rg.get('distance',{});distance_text=str(distance.get('amount',''))+' '+distance.get('type',rg.get('type',''))
        components=spell.get('components',{});comp=', '.join([k.upper() for k in ('v','s') if components.get(k)]+([components['m'] if isinstance(components.get('m'),str) else components.get('m',{}).get('text','Material')] if components.get('m') else []))
        durations=[]
        for d in spell.get('duration',[]):
            length=d.get('duration',{});durations.append(('Concentration, ' if d.get('concentration') else '')+(str(length.get('amount',''))+' '+length.get('type','') if length else d.get('type','')))
        return [f"Spell level: {spell.get('level',0)}; casting time: {times}",f"Range: {distance_text.strip()}"+(' ('+rg['type']+')' if rg.get('type') not in ('point','special',None) else ''),'Components: '+comp,'Duration: '+', '.join(durations)]
    for key in dict.fromkeys(s.get('selectedSpells',[])+racial_keys):
        spell=db['spells'].get(key)
        if spell:
            x=copy.deepcopy(spell);x.pop('level',None);x['entries']=describe_spell(spell)+spell.get('entries',[])+spell.get('entriesHigherLevel',[])
            add(x,'Racial spell' if key in racial_keys else 'Selected spell',key)
    if not c:result['warnings'].append('Select a class source to load its features.')
    if not race:result['warnings'].append('Race is not set; no racial abilities have been assumed.')
    return result
