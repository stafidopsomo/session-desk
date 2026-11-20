"""Real shared-workspace workflow with original fixtures; never active user data."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import expect,sync_playwright
from sessiondesk.importer import Library
from sessiondesk.store import Store
from sessiondesk.workspace_modules import MODULE_ID
from tests.fixtures import make_library
from tests.prepared_fixture import make_prepared,pack
from tools.smoke_core import launch,call

def run(exe=None,artifacts=None):
    with tempfile.TemporaryDirectory(prefix='sessiondesk-journal-synthetic-') as temp:
        base=Path(temp);profile=base/'profile';store=Store(profile)
        if artifacts:Path(artifacts).mkdir(parents=True,exist_ok=True)
        fresh=store.create('Original fresh campaign')['id']
        library=make_library(base/'library',rich=True)
        index=library/'data/adventures.json';catalog=json.loads(index.read_text(encoding='utf-8'));catalog['adventure'].append({'id':'ALT','name':'The Tidal Archive'});index.write_text(json.dumps(catalog),encoding='utf-8')
        alternate=json.loads((library/'data/adventure/adventure-demo.json').read_text(encoding='utf-8'))
        alternate['data'][0]['name']='Tidal archive'
        alternate['data'].append({'type':'section','name':'Original earlier summary','entries':['Original earlier journal snapshot.']})
        (library/'data/adventure/adventure-alt.json').write_text(json.dumps(alternate),encoding='utf-8')
        (library/'data/books.json').write_text(json.dumps({'book':[{'id':'DEMO','name':'Original Field Guide'}]}),encoding='utf-8')
        (library/'data/book').mkdir();(library/'data/book/book-demo.json').write_text(json.dumps({'bookData':[{'id':'DEMO','data':alternate['data']}]}),encoding='utf-8')
        graph,blobs=Library(library).load('DEMO');store.import_graph(fresh,graph,blobs)
        extra_graph,extra_blobs=Library(library).load('ALT');store.import_graph(fresh,extra_graph,extra_blobs)
        original=make_prepared(base/'original')
        maps_file=original/'data/maps.json'
        maps=json.loads(maps_file.read_text(encoding='utf-8'))
        maps['maps'].extend({**maps['maps'][0],'id':f'gallery-{i}','title':f'Original gallery {i:02}'}
                            for i in range(1,27))
        maps_file.write_text(json.dumps(maps),encoding='utf-8')
        archive=pack(original,base/'original.zip',recovery=True)
        restored=store.restore_file(archive)['id']
        (profile/'local-sources.json').write_text(json.dumps({restored:str(library)}),encoding='utf-8')
        store.import_graph(restored,extra_graph,extra_blobs)
        root=store.folder(restored)/'module-files'/MODULE_ID
        initial_state=(root/'state/table.json').read_bytes()
        with launch(base/'runtime',exe,data=profile) as ready,sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(viewport={'width':1500,'height':1000})
            errors=[];external=[]
            context.on('page',lambda page:page.on('pageerror',lambda e:errors.append(str(e))))
            context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(ready['url']) else (external.append(r.request.url),r.abort()))
            page=context.new_page()
            def address(wid,extra=''):return ready['url']+'?tutorial=off&workspace='+wid+extra+'#dm='+ready['token']
            page.goto(address(fresh))
            expect(page.locator('.campaign-nav').get_by_role('link')).to_have_count(3)
            page.get_by_role('button',name='New entry',exact=True).click();page.get_by_role('button',name='Edit',exact=True).click()
            page.get_by_label('Title',exact=True).fill('Original session report');page.get_by_label('Text',exact=True).fill('The explorers returned to the village.\n\nOriginal second paragraph.')
            page.get_by_role('button',name='Save',exact=True).click();expect(page.get_by_role('heading',name='Original session report',exact=True)).to_be_visible()
            entry_url=page.url
            other=context.new_page();other.goto(entry_url+'#dm='+ready['token'])
            expect(other.get_by_role('heading',name='Original session report',exact=True)).to_be_visible()
            page.get_by_role('button',name='Edit',exact=True).click();other.get_by_role('button',name='Edit',exact=True).click()
            page.get_by_label('Text',exact=True).fill('First tab saved this original report.');other.get_by_label('Text',exact=True).fill('Second tab draft must survive.')
            page.get_by_role('button',name='Save',exact=True).click();expect(page.locator('#book-edit')).to_have_count(0);other.get_by_role('button',name='Save',exact=True).click()
            expect(other.get_by_role('status').filter(has_text='another tab')).to_be_visible()
            expect(other.get_by_label('Text',exact=True)).to_have_value('Second tab draft must survive.')
            other.reload();expect(other.get_by_label('Text',exact=True)).to_have_value('Second tab draft must survive.')
            page.get_by_role('button',name='New mission',exact=True).click();expect(page.get_by_role('heading',name='New mission',exact=True)).to_be_visible();page.get_by_role('button',name='Edit',exact=True).click()
            page.get_by_label('Title',exact=True).fill('Original local investigation');page.get_by_label('Status',exact=True).select_option('Offered');page.get_by_label('Objective',exact=True).fill('Find the missing survey notes.');page.get_by_label('Reward offered',exact=True).fill('50 gp')
            page.get_by_role('button',name='Save',exact=True).click();expect(page.locator('dd').filter(has_text='50 gp')).to_be_visible()
            expect(page.locator('dd').last).to_have_text('Not recorded')
            page.locator('.campaign-nav').get_by_role('link',name='Party',exact=True).click();page.get_by_role('button',name='Add character',exact=True).click()
            page.get_by_label('Name',exact=True).fill('Original newcomer');page.get_by_role('button',name='Save character notes',exact=True).click();expect(page.locator('#party-status')).to_have_text('Saved')
            page.get_by_role('button',name='Settings',exact=True).click();page.get_by_role('button',name='Quick tour',exact=True).click();expect(page.locator('#tour-layer .tour')).to_be_visible();page.get_by_role('button',name='Skip tour',exact=True).click()
            page.locator('.campaign-nav').get_by_role('link',name='Resources',exact=True).click()
            tabs=page.get_by_role('navigation',name='Resource sources',exact=True)
            expect(tabs.get_by_role('link')).to_have_count(2)
            expect(page.get_by_role('button',name='Open adventure',exact=True)).to_have_count(0)
            tabs.get_by_role('link',name='The Tidal Archive',exact=True).click()
            expect(tabs.get_by_role('link',name='The Tidal Archive',exact=True)).to_have_attribute('aria-current','page')
            expect(page.locator('#stage canvas')).to_be_visible()
            page.locator('.campaign-nav').get_by_role('link',name='Book',exact=True).click()
            page.locator('.campaign-nav').get_by_role('link',name='Resources',exact=True).click()
            expect(tabs.get_by_role('link',name='The Tidal Archive',exact=True)).to_have_attribute('aria-current','page')
            page.reload();expect(tabs.get_by_role('link',name='The Tidal Archive',exact=True)).to_have_attribute('aria-current','page')
            session_before=call(ready,'session',{'workspace':fresh,'adventure':extra_graph['id']})
            archive_tab=tabs.get_by_role('link',name='The Tidal Archive',exact=True)
            observatory_tab=tabs.get_by_role('link',name='The Glass Observatory',exact=True)
            archive_tab.drag_to(observatory_tab,target_position={'x':4,'y':10})
            expect(tabs.get_by_role('link').first).to_have_text('The Tidal Archive')
            expect(archive_tab).to_have_attribute('aria-current','page')
            expect(page.locator('#stage canvas')).to_be_visible()
            other.goto(address(fresh,'&section=resources'))
            expect(other.get_by_role('navigation',name='Resource sources').get_by_role('link').first).to_have_text('The Tidal Archive')
            archive_tab.focus()
            page.keyboard.press('Alt+ArrowRight')
            expect(tabs.get_by_role('link').first).to_have_text('The Glass Observatory')
            for width,height in ((2836,695),(1500,1000)):
                page.set_viewport_size({'width':width,'height':height})
                expect(page.locator('#stage canvas')).to_be_visible()
                assert page.locator('.workspace').bounding_box()['y']+page.locator('.workspace').bounding_box()['height']>=height-1
                assert page.evaluate('document.documentElement.scrollHeight<=innerHeight+1')
                if artifacts:page.screenshot(path=str(Path(artifacts)/('resources-'+str(width)+'.png')))
            tabs.get_by_role('link',name='The Glass Observatory',exact=True).click()
            assert call(ready,'session',{'workspace':fresh,'adventure':extra_graph['id']})==session_before,'Source navigation changed player state'
            expect(page.locator('#stage canvas')).to_be_visible()
            expect(page).to_have_url(__import__('re').compile('adventure='))
            page.get_by_role('button',name='Observatory floor',exact=False).first.click() if page.get_by_role('button',name='Observatory floor',exact=False).count() else None
            generic_url=page.url;page.reload();expect(page.locator('#stage canvas')).to_be_visible()
            page.locator('.campaign-nav').get_by_role('link',name='Resources',exact=True).click();expect(page.locator('#stage canvas')).to_be_visible()
            page.goto(address(restored,'&section=party&character=explorer'))
            expect(page.get_by_role('heading',name='Explorer',exact=True)).to_be_visible();party_url=page.url
            page.get_by_label('Private notes',exact=True).fill('Original updated private note');page.get_by_role('button',name='Save character notes',exact=True).click();expect(page.locator('#party-status')).to_have_text('Saved')
            map_page=context.new_page();map_page.goto(address(restored,'&section=resources&prepared=1&map=realm&room=village'))
            expect(map_page.locator('#preview-map-loading')).to_be_hidden();expect(map_page.get_by_role('heading',name='Practice region',exact=True)).to_be_visible()
            expect(map_page.get_by_role('navigation',name='Resource sources').get_by_role('link')).to_have_count(2)
            map_page.get_by_role('navigation',name='Resource sources').get_by_role('link',name='The Tidal Archive',exact=True).click()
            expect(map_page.locator('#stage canvas')).to_be_visible()
            map_page.get_by_role('navigation',name='Resource sources').get_by_role('link').first.click()
            expect(map_page.locator('#preview-map-loading')).to_be_hidden()
            expect(page.get_by_role('heading',name='Explorer',exact=True)).to_be_visible();assert page.url==party_url
            prior_map=map_page.locator('.campaign-map-main h1').inner_text()
            index=map_page.locator('.campaign-index')
            header=map_page.locator('.resource-header')
            images=index.locator('details').last
            images.evaluate("details=>details.open=true")
            index.evaluate("sidebar=>{window.originalIndex=sidebar;sidebar.scrollTop=sidebar.scrollHeight}")
            expect(header).to_have_class('resource-header is-collapsed')
            map_page.wait_for_function("() => document.querySelector('.resource-header').getBoundingClientRect().bottom<=1")
            previous_scroll=index.evaluate("sidebar=>sidebar.scrollTop")
            assert previous_scroll>0
            requests=[]
            def observe_navigation(request):
                if request.url.endswith(('/api/workspace','/api/data')):
                    requests.append(request.url.split('/')[-1])
            map_page.on('request',observe_navigation)
            index.get_by_role('link',name='Original gallery 26',exact=True).click()
            expect(map_page.get_by_role('heading',name='Original gallery 26',exact=True)).to_be_visible()
            expect(map_page.locator('#preview-room')).to_be_enabled()
            assert index.evaluate("sidebar=>sidebar===window.originalIndex")
            assert abs(index.evaluate("sidebar=>sidebar.scrollTop")-previous_scroll)<=1
            assert images.evaluate("details=>details.open")
            assert not requests,requests
            expect(header).to_have_class('resource-header is-collapsed')
            map_page.go_back()
            expect(map_page.get_by_role('heading',name=prior_map,exact=True)).to_be_visible()
            expect(map_page.locator('#preview-room')).to_be_enabled()
            assert index.evaluate("sidebar=>sidebar===window.originalIndex")
            assert not requests,requests
            current_map=index.locator('[aria-current=page]')
            map_page.locator('#preview-map').evaluate('canvas=>window.originalCanvas=canvas')
            current_map.click()
            assert map_page.locator('#preview-map').evaluate('canvas=>canvas===window.originalCanvas')
            assert not requests,requests
            map_page.remove_listener('request',observe_navigation)
            index.hover();map_page.mouse.wheel(0,-240)
            expect(header).to_have_class('resource-header')
            map_page.wait_for_function("() => document.querySelector('.resource-header').getBoundingClientRect().top>=-1")
            map_page.locator('#preview-map').hover();map_page.mouse.wheel(0,140)
            expect(header).to_have_class('resource-header')
            assert (root/'state/table.json').read_bytes()==initial_state,'Inspection changed saved state'
            map_page.get_by_role('link',name='Practice floor',exact=True).click();expect(map_page.get_by_role('heading',name='Practice floor',exact=True)).to_be_visible();expect(map_page.locator('#preview-map-loading')).to_be_hidden()
            expect(map_page.locator('#preview-room')).to_be_enabled()
            map_page.locator('#preview-room').select_option('b');expect(map_page.get_by_role('heading',name='Upper platform',exact=True)).to_be_visible()
            room=map_page.locator('#prepared-room-panel')
            expect(room).to_contain_text('Original private room contents.')
            expect(room).to_contain_text('Original encounter ambush.')
            expect(room).to_contain_text('Original keeper')
            expect(room.locator('[data-room-source]')).to_contain_text('The suspended lens')
            deny_url=ready['url']+f"campaign/{restored}/{ready['player_token']}/api/room-source?mapId=practice&roomId=b"
            assert context.request.get(deny_url).status==403
            divider=map_page.get_by_role('separator',name='Resize room panel',exact=True)
            before_width=room.bounding_box()['width'];handle=divider.bounding_box()
            map_page.mouse.move(handle['x']+handle['width']/2,handle['y']+80)
            map_page.mouse.down()
            map_page.mouse.move(handle['x']-90,handle['y']+80,steps=8)
            map_page.mouse.up()
            assert room.bounding_box()['width']>=before_width+80
            assert (root/'state/table.json').read_bytes()==initial_state,'Room inspection changed presentation/fog'
            specific_url=map_page.url;map_page.reload();expect(map_page.get_by_role('heading',name='Upper platform',exact=True)).to_be_visible()
            assert 'room=b' in specific_url
            map_page.get_by_role('button',name='Reveal room',exact=True).click()
            expect(map_page.locator('.campaign-room').get_by_text('Room has revealed areas',exact=True)).to_be_visible()
            map_page.get_by_role('button',name='Present map',exact=True).click();expect(map_page.locator('#map-status')).to_have_text('On player screen · saved fog active')
            with map_page.expect_popup() as opened:
                map_page.get_by_role('button',name='Open player screen',exact=True).click()
            player=opened.value
            strip=player.get_by_role('navigation',name='Shared presentation tabs')
            prepared_frame=player.frame_locator('iframe[src*="prepared=1"]')
            expect(prepared_frame.locator('#canvas')).to_be_visible()
            expect(player.locator('.workspace-player .brand')).to_have_text('Session Desk')
            expect(strip.get_by_role('button',name='Show Practice floor',exact=True)).to_have_attribute('aria-pressed','true')
            expect(prepared_frame.get_by_role('button',name='Zoom in')).to_be_visible()
            player_url=player.url
            assert 'view=player' in player_url and '/campaign/' not in player_url
            assert 'Original private room contents.' not in prepared_frame.locator('body').inner_text()
            expect(map_page.locator('#player-presence')).to_have_attribute('aria-label','Player screen online')
            prepared_url=map_page.url
            saved_prepared=json.loads((root/'state/table.json').read_text(encoding='utf-8'))

            map_page.get_by_role('navigation',name='Resource sources').get_by_role('link',name='The Tidal Archive',exact=True).click()
            imported=extra_graph['id']
            imported_map=next(m for m in extra_graph['maps'] if m.get('image_type')!='mapPlayer')
            map_page.get_by_label('Search adventure resources').fill(imported_map['name'])
            map_page.locator('.library button[data-id="'+imported_map['id']+'"]').click()
            map_page.get_by_role('button',name='Present to players · with fog').click()
            imported_frame=player.frame_locator('iframe[src*="adventure='+imported+'"]')
            expect(imported_frame.locator('#stage canvas')).to_be_visible()
            expect(prepared_frame.locator('#canvas')).to_be_hidden()
            expect(strip.get_by_role('button',name='Show '+imported_map['name'],exact=True)).to_have_attribute('aria-pressed','true')
            expect(strip.get_by_role('button',name='Show Practice floor',exact=True)).to_be_visible()
            expect(map_page.locator('#dm-tabs')).to_contain_text('Practice floor')
            expect(map_page.locator('#player-presence')).to_have_attribute('aria-label','Player screen online')
            assert player.url==player_url
            player.locator('.workspace-player').evaluate("shell=>shell.dataset.original='true'")
            original_pages=set(context.pages)
            map_page.get_by_role('button',name='Open player screen',exact=True).click()
            expect(player.locator('.workspace-player')).to_have_attribute('data-original','true')
            assert set(context.pages)==original_pages
            imported_session=call(ready,'session',{'workspace':restored,'adventure':imported})
            assert not imported_session['fog'].get(imported_map['id'])
            assert json.loads((root/'state/table.json').read_text(encoding='utf-8'))==saved_prepared

            strip.get_by_role('button',name='Show Practice floor',exact=True).click()
            expect(prepared_frame.locator('#canvas')).to_be_visible()
            expect(imported_frame.locator('#stage canvas')).to_be_hidden()
            expect(strip.get_by_role('button',name='Show Practice floor',exact=True)).to_have_attribute('aria-pressed','true')

            map_page.goto(prepared_url)
            expect(map_page.locator('#preview-room')).to_be_enabled()
            map_page.locator('.campaign-index details').last.locator('summary').click()
            map_page.get_by_role('button',name='Arrival illustration',exact=True).click()
            map_page.get_by_role('button',name='Present picture',exact=True).click()
            expect(strip.get_by_role('button',name='Show Arrival illustration',exact=True)).to_have_attribute('aria-pressed','true')
            expect(prepared_frame.locator('#pictureCanvas')).to_be_visible()
            expect(strip.locator('.tab')).to_have_count(3)
            strip.get_by_role('button',name='Close '+imported_map['name'],exact=True).click()
            expect(strip.locator('.tab')).to_have_count(2)
            strip.get_by_role('button',name='Close all',exact=True).click()
            expect(strip).to_contain_text('Nothing is being presented.')
            assert call(ready,'session',{'workspace':restored,'adventure':imported})['tabs']==[]
            assert json.loads((root/'state/table.json').read_text(encoding='utf-8'))['fog']==saved_prepared['fog']
            empty=call(ready,'presentation',{'workspace':fresh},player=True)
            assert empty=={'tabs':[],'active':None}
            player.close()
            if artifacts:
                Path(artifacts).mkdir(parents=True,exist_ok=True);map_page.screenshot(path=str(Path(artifacts)/'preview-map.png'),full_page=True)
                page.screenshot(path=str(Path(artifacts)/'preview-party.png'),full_page=True)
                page.goto(entry_url);expect(page.get_by_role('heading',name='Original session report',exact=True)).to_be_visible();page.screenshot(path=str(Path(artifacts)/'preview-book.png'),full_page=True)
            page.goto(ready['url']+'?tutorial=off#dm='+ready['token'])
            page.get_by_role('button',name='New workspace',exact=True).click()
            page.get_by_label('Name',exact=True).fill('Original standalone session')
            page.get_by_label('Play style',exact=True).select_option('oneshot')
            page.get_by_role('button',name='Create workspace',exact=True).click()
            expect(page.get_by_role('heading',name='Resources',exact=True)).to_be_visible()
            expect(page.locator('.campaign-nav').get_by_role('link',name='Book',exact=True)).to_have_count(0)
            oneshot_url=page.url
            assert page.locator('#app').bounding_box()['height']>=1000
            if artifacts:page.screenshot(path=str(Path(artifacts)/'oneshot-empty.png'))
            page.goto(oneshot_url.replace('section=resources','section=book'));expect(page.get_by_role('heading',name='Resources',exact=True)).to_be_visible()
            expect(page.locator('.campaign-index')).to_have_count(0)
            assert 'section=book' not in page.url
            page.get_by_role('button',name='Add source',exact=True).click()
            page.get_by_label('5e.tools library folder',exact=True).fill(str(library))
            page.get_by_role('button',name='Validate copy',exact=True).click()
            expect(page.locator('#adventure-source option')).to_have_count(3)
            page.get_by_label('Find a book or adventure',exact=True).fill('not an adventure')
            expect(page.locator('#adventure-count')).to_have_text('No matching sources.')
            expect(page.get_by_role('button',name='Import adventure',exact=True)).to_be_disabled()
            page.get_by_label('Find a book or adventure',exact=True).fill('tidal')
            expect(page.locator('#adventure-source option')).to_have_count(1)
            expect(page.get_by_role('button',name='Import adventure',exact=True)).to_be_enabled()
            page.get_by_label('Find a book or adventure',exact=True).fill('')
            expect(page.locator('#adventure-source option')).to_have_count(3)
            page.get_by_label('Find a book or adventure',exact=True).fill('tidal')
            page.get_by_role('button',name='Import adventure',exact=True).click()
            expect(page.locator('#stage canvas')).to_be_visible()
            expect(page.locator('.campaign-nav').get_by_role('link',name='Book',exact=True)).to_have_count(0)
            expect(page.get_by_role('navigation',name='Resource sources').get_by_role('link',name='The Tidal Archive',exact=True)).to_have_attribute('aria-current','page')
            page.get_by_role('button',name='Remove adventure',exact=True).click();page.get_by_role('button',name='Cancel',exact=True).click()
            expect(page.locator('#stage canvas')).to_be_visible()
            page.get_by_role('button',name='Remove adventure',exact=True).click();page.locator('[data-action=confirm-remove-adventure]').click()
            expect(page.get_by_role('heading',name='Resources',exact=True)).to_be_visible()
            expect(page.get_by_role('navigation',name='Resource sources').get_by_role('link')).to_have_count(0)
            page.get_by_role('button',name='Add source',exact=True).click()
            expect(page.locator('#source-kind')).to_be_visible()
            page.locator('#source-kind').select_option('book')
            expect(page.locator('#adventure-source option')).to_have_count(1)
            page.get_by_role('button',name='Import adventure',exact=True).click()
            expect(page.locator('.sourceview')).to_contain_text('Tidal archive')
            expect(page.get_by_role('button',name='Remove reference book',exact=True)).to_be_visible()
            expect(page.locator('.sourceview').get_by_role('link',name='Open source in 5e.tools',exact=False)).to_have_attribute('href',__import__('re').compile('book.html#demo,'))
            page.get_by_role('button',name='Settings',exact=True).click()
            expect(page.locator('#remote-info')).to_contain_text('Tailscale')
            expect(page.get_by_role('button',name='Enable private hosting',exact=True)).to_be_visible()
            page.get_by_role('button',name='Settings',exact=True).click()
            # A configured campaign has one visible source across native journal,
            # prepared maps, authored encounters and older saved encounters.
            reference,reference_blobs=Library(library).load('book:DEMO')
            store.import_graph(restored,graph,blobs)
            store.import_graph(restored,reference,reference_blobs)
            native=call(ready,'journal',{'workspace':restored})
            earlier=next(e for e in extra_graph['entries'] if e['name']=='Original earlier summary')
            store.prepare(restored,extra_graph['id'],earlier['id'],{'notes':'Original earlier prep retained.','status':'approved'})
            call(ready,'workspace/campaign-library',{'workspace':restored,'campaign_library':{
                'title':'My campaign','encounters':[extra_graph['id']],'archive':[graph['id']],
                'journal_chapters':[earlier['chapter']]}})
            page.goto(address(restored))
            sources=page.get_by_role('navigation',name='Resource sources',exact=True)
            sections=page.get_by_role('navigation',name='Campaign contents',exact=True)
            expect(sources.get_by_role('link')).to_have_count(2)
            expect(sources.get_by_role('link',name='My campaign',exact=True)).to_have_attribute('aria-current','page')
            expect(page.locator('.campaign-nav').get_by_role('link',name='Book',exact=True)).to_have_count(0)
            expect(sections.get_by_role('link',name='Journal',exact=True)).to_have_attribute('aria-current','page')
            sections.get_by_role('link',name='Encounters',exact=True).click()
            expect(page.locator('#stage canvas')).to_be_visible()
            expect(sections.get_by_role('link',name='Encounters',exact=True)).to_have_attribute('aria-current','page')
            expect(page.locator('.book-navigation').get_by_role('button',name='Original earlier summary')).to_have_count(0)
            page.locator('.journal-preparation summary').click()
            page.locator('.journal-preparation').get_by_role('button',name='Original earlier summary').click()
            expect(page.locator('#inspector')).to_contain_text('Original earlier prep retained.')
            sections.get_by_role('link',name='Maps & Images',exact=True).click()
            expect(page.locator('#preview-room')).to_be_enabled()
            expect(sources.get_by_role('link',name='My campaign',exact=True)).to_have_attribute('aria-current','page')
            sections.get_by_role('link',name='Archive',exact=True).click()
            expect(page.locator('#stage canvas')).to_be_visible()
            expect(sections.get_by_role('link',name='Archive',exact=True)).to_have_attribute('aria-current','page')
            sources.get_by_role('link',name='Original Field Guide',exact=True).click()
            expect(page.locator('.sourceview')).to_contain_text('Tidal archive')
            expect(sections).to_have_count(0)
            sources.get_by_role('link',name='My campaign',exact=True).click()
            expect(sections.get_by_role('link',name='Journal',exact=True)).to_have_attribute('aria-current','page')
            assert call(ready,'journal',{'workspace':restored})==native
            assert not errors,errors;assert not external,external
            browser.close()
        print('Shared workspace E2E passed: fresh/restored shell, book edit/conflict/reload, missions, party, generic resources, independent map selection, reveal/present. No script errors or external requests.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--exe',type=Path);parser.add_argument('--artifacts',type=Path);args=parser.parse_args();run(args.exe,args.artifacts)
