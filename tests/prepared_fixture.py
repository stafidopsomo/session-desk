"""Original prepared-campaign fixture; contains no user's campaign/book text."""
import hashlib
import json
from pathlib import Path
import zipfile

from tests.fixtures import make_library, png


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def make_prepared(root):
    root = Path(root)
    root.mkdir(parents=True)
    image = png()
    for name in ('maps/dm.png','maps/player.png','adventures/practice/a.png','adventures/practice/held.png','sessions/portrait.png'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image)
    manifest = {'schemaVersion':1,'id':'prepared-example','title':'Prepared example','rulesEdition':'2014',
        'paths':{'data':'data','characters':'characters','state':'state','prep':'prep'},
        'catalogs':{'maps':['maps.json'],'narrationMaps':['practice'],'chapterEncounters':{}},
        'mapGroups':[{'title':'Practice maps','prefix':''}]}
    write(root,'campaign.json',manifest)
    locations = [{'id':'a','number':'A','name':'Arrival platform','kind':'Room','x':.25,'y':.4,
        'summary':'Original synthetic room.','dmNotes':'SYNTHETIC_PRIVATE_ROOM_SECRET',
        'sourceLink':'/reference/adventure.html#demo,0,arrival',
        'shapes':[[[85,105],[385,105],[385,445],[85,445]]]},
        {'id':'b','number':'B','name':'Upper platform','x':.7,'y':.4,
         'summary':'Original upper room.','shapes':[[[520,105],[810,105],[810,445],[520,445]]]}]
    dungeon = {'id':'practice','title':'Practice floor','kind':'dungeon','image':'maps/dm.png',
        'playerImage':'maps/player.png','width':900,'height':600,'roomRevealPadding':5,
        'initialRevealed':['a'],'locations':locations,'partyLevel':3,'partySize':4}
    world = {'id':'realm','title':'Practice region','image':'maps/player.png','width':900,'height':600,
        'locations':[{'id':'village','name':'Lantern Village','kind':'Town','x':.25,'y':.5,
                      'summary':'An original village beside a small lake.'}]}
    write(root,'data/maps.json',{'maps':[dungeon,world]})
    write(root,'data/narration-gr.json',{'rooms':{'a':{'readAloudGr':'Φως περνά από τη γυάλινη στέγη.','additionalPassages':[]}}})
    write(root,'data/npc-dialogue-gr.json',{'rooms':{'a':[{'speaker':'Keeper','lineGr':'Από πού έρχεστε;'}]}})
    write(root,'data/encounters.json',{'partyLevel':3,'partySize':4,'rooms':{},'opening':{}})
    write(root,'data/opening.json',{'title':'Opening','scenes':[{'id':'arrival','title':'Arrival','stage':'Arrival',
        'goal':'Enter the original observatory.','readAloudGr':'Το μονοπάτι τελειώνει εδώ.',
        'run':['Describe the roof.'],'npcLines':[],'facts':[],'next':'Ask for an approach.'}]})
    write(root,'data/after-citadel.json',{'title':'Next chapter','description':'Original future preparation.',
        'scenes':[{'id':'return','title':'A quiet return','phase':'Return','kind':'scene',
                   'readAloudGr':'Ο δρόμος μένει ήσυχος.','npcLines':[],'run':['Ask where they stop.']}],
        'roomCues':[],'handouts':{},'principles':[]})
    write(root,'data/world-guide.json',{'cards':[{'id':'world','title':'Our example world','summary':'Original reference.',
        'prompt':'Ask one question.','picture':'adventures/practice/a.png','sourceLink':'/reference/book.html#phb,0'}]})
    write(root,'data/sessions.json',{'sessions':[{'id':'session-example','title':'Example deck','description':'Original deck.',
        'slides':[{'path':'adventures/practice/a.png','title':'Example picture'}]}]})
    write(root,'data/shopping.json',{'title':'Example supplies','intro':'Original sample shop.','coinage':'10 sp = 1 gp',
        'stockNote':'Listed prices.','sourceLink':'/reference/items.html','priceSourceUrl':'/reference/items.html',
        'shops':[{'id':'market','name':'Example market','location':'Village','summary':'Supplies.','sourceUrl':'/reference/book.html#phb'}],
        'items':[{'name':'Example remedy','shopId':'market','category':'Supplies','priceCp':2500,'price':'25 gp',
                  'note':'Original test item.','source':'PHB','page':1,'sourceLink':'/reference/items.html#example_phb'}]})
    write(root,'data/token-art.json',{'party':[{'characterId':'explorer','image':'sessions/portrait.png','color':'#44aa99'}],
        'foes':[{'id':'foe:keeper','kind':'foe','name':'Keeper','image':'sessions/portrait.png','color':'#aa6644'}]})
    character = {key:'' for key in ('player','race','background','concept','home','faction','rank','patron','patronNote','contact','notes','source','sourceLink')}
    character.update(id='explorer',name='Explorer',level=3,renown=None,**{'class':'Sentinel',
        'threads':[{'title':'Original secret','status':'Idea','next':'Wait for a question.','where':'Village',
                    'notes':'SYNTHETIC_PRIVATE_THREAD_SECRET','source':'Original','link':''}],
        'sheet':{'classKey':'Sentinel|PHB','subclassKey':'','raceKey':'','subraceKey':'','scores':{'str':14,'dex':12,'con':13,'int':10,'wis':11,'cha':10},
                 'skills':{},'saves':{},'selectedFeatures':[],'selectedSpells':[],'disabledFeatures':[],
                 'resources':'One original resource','featureNotes':'','hpMax':20}})
    write(root,'characters/explorer/character.json',character)
    (root/'characters/explorer/backstory.md').write_text('Original synthetic backstory.',encoding='utf-8')
    write(root,'state/table.json',{'version':4,'mapId':'practice','locationId':None,'overlay':None,'blackout':False,
        'ping':None,'mapSplitVersion':1,'fog':{'practice':{'operations':[
            {'kind':'room','id':'a','shape':0,'reveal':True},
            {'kind':'brush','points':[[400,200],[450,200]],'radius':18,'reveal':True}]}},
        'tabs':[{'id':'map:practice','kind':'map','mapId':'practice','locationId':None}],
        'activeTabId':'map:practice','dm_secret':'SYNTHETIC_PRIVATE_STATE_SECRET'})
    write(root,'adventures/practice/manifest.json',{'assets':[
        {'path':'adventures/practice/a.png','title':'Arrival illustration','category':'room-scene','mapId':'practice','areaId':'a','sectionIndex':0,'spoiler':False},
        {'path':'adventures/practice/held.png','title':'Held illustration','category':'room-scene','mapId':'practice','areaId':'b','sectionIndex':0,'spoiler':True}]})
    write(root,'maps/manifest.json',{'assets':[{'path':'maps/dm.png','title':'DM map','category':'map','spoiler':True},
        {'path':'maps/player.png','title':'Player map','category':'map','spoiler':False}]})
    (root/'prep').mkdir()
    (root/'prep/do-not-run.py').write_text("raise RuntimeError('Backup code must never run')\n",encoding='utf-8')
    (root/'prep/same.md').write_text('Identical attachment bytes.',encoding='utf-8')
    (root/'prep/same.txt').write_text('Identical attachment bytes.',encoding='utf-8')
    (root/'prep/original.pdf').write_bytes(b'%PDF-1.4\nOriginal synthetic attachment\n%%EOF')
    return root


def pack(root, target, recovery=False):
    prefix = 'project/campaigns/prepared-example/' if recovery else ''
    records = []
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
        for path in sorted(Path(root).rglob('*')):
            if path.is_file():
                name=prefix+path.relative_to(root).as_posix()
                out.write(path,name)
                records.append({'path':name,'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        if recovery:
            out.writestr('project/old-app.py',"raise RuntimeError('Do not execute archived application code')")
            out.writestr('recovery/personal-main.bundle',b'Original fake bundle bytes')
            out.writestr('backup-manifest.json',json.dumps({'format':'campaign-desk-full-snapshot','files':records}))
    return Path(target)


def rules_library(root):
    root=make_library(root)
    write(root,'package.json',{'version':'1.221.6'})
    write(root,'data/books.json',{'book':[{'id':'PHB','published':'2014-01-01'}]})
    write(root,'data/book/book-phb.json',{'data':[{'name':'Original rules fixture','entries':['Original test text.']}]})
    write(root,'data/class/class-sentinel.json',{'class':[{'name':'Sentinel','source':'PHB','hd':{'faces':8},
        'classFeatures':['Original training|Sentinel|PHB|1|PHB']}],
        'classFeature':[{'name':'Original training','className':'Sentinel','classSource':'PHB','source':'PHB','level':1,
                         'entries':['An original synthetic feature.']}]})
    return root
