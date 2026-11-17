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
        alternate=json.loads((library/'data/adventure/adventure-demo.json').read_text(encoding='utf-8'));alternate['data'][0]['name']='Tidal archive';(library/'data/adventure/adventure-alt.json').write_text(json.dumps(alternate),encoding='utf-8')
        (library/'data/books.json').write_text(json.dumps({'book':[{'id':'DEMO','name':'Original Field Guide'}]}),encoding='utf-8')
        (library/'data/book').mkdir();(library/'data/book/book-demo.json').write_text(json.dumps({'bookData':[{'id':'DEMO','data':alternate['data']}]}),encoding='utf-8')
        graph,blobs=Library(library).load('DEMO');store.import_graph(fresh,graph,blobs)
        extra_graph,extra_blobs=Library(library).load('ALT');store.import_graph(fresh,extra_graph,extra_blobs)
        original=make_prepared(base/'original');archive=pack(original,base/'original.zip',recovery=True)
        restored=store.restore_file(archive)['id']
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
            assert (root/'state/table.json').read_bytes()==initial_state,'Inspection changed saved state'
            map_page.get_by_role('link',name='Practice floor',exact=True).click();expect(map_page.get_by_role('heading',name='Practice floor',exact=True)).to_be_visible();expect(map_page.locator('#preview-map-loading')).to_be_hidden()
            map_page.locator('#preview-room').select_option('b');expect(map_page.get_by_role('heading',name='Upper platform',exact=True)).to_be_visible()
            assert (root/'state/table.json').read_bytes()==initial_state,'Room inspection changed presentation/fog'
            specific_url=map_page.url;map_page.reload();expect(map_page.get_by_role('heading',name='Upper platform',exact=True)).to_be_visible()
            assert 'room=b' in specific_url
            map_page.get_by_role('button',name='Reveal room',exact=True).click()
            expect(map_page.locator('.campaign-room').get_by_text('Room has revealed areas',exact=True)).to_be_visible()
            map_page.get_by_role('button',name='Present map',exact=True).click();expect(map_page.locator('#map-status')).to_have_text('On player screen · saved fog active')
            with map_page.expect_popup() as opened:
                map_page.get_by_role('button',name='Open player screen',exact=True).click()
            player=opened.value
            expect(player.locator('#canvas')).to_be_visible()
            expect(map_page.locator('#player-presence')).to_have_attribute('aria-label','Player screen online')
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
            assert not errors,errors;assert not external,external
            browser.close()
        print('Shared workspace E2E passed: fresh/restored shell, book edit/conflict/reload, missions, party, generic resources, independent map selection, reveal/present. No script errors or external requests.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--exe',type=Path);parser.add_argument('--artifacts',type=Path);args=parser.parse_args();run(args.exe,args.artifacts)
