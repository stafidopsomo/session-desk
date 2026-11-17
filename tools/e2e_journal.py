"""Real shared-preview workflow with original fixtures; never active user data."""
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
        fresh=store.create('Original fresh campaign')['id']
        library=make_library(base/'library',rich=True);graph,blobs=Library(library).load('DEMO');store.import_graph(fresh,graph,blobs)
        original=make_prepared(base/'original');archive=pack(original,base/'original.zip',recovery=True)
        restored=store.restore_file(archive)['id']
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
            page.get_by_role('button',name='New mission',exact=True).click();page.get_by_role('button',name='Edit',exact=True).click()
            page.get_by_label('Title',exact=True).fill('Original local investigation');page.get_by_label('Status',exact=True).select_option('Offered');page.get_by_label('Objective',exact=True).fill('Find the missing survey notes.');page.get_by_label('Reward offered',exact=True).fill('50 gp')
            page.get_by_role('button',name='Save',exact=True).click();expect(page.locator('dd').filter(has_text='50 gp')).to_be_visible()
            expect(page.locator('dd').last).to_have_text('Not recorded')
            page.locator('.campaign-nav').get_by_role('link',name='Party',exact=True).click();page.get_by_role('button',name='Add character',exact=True).click()
            page.get_by_label('Name',exact=True).fill('Original newcomer');page.get_by_role('button',name='Save character notes',exact=True).click();expect(page.locator('#party-status')).to_have_text('Saved')
            page.get_by_role('button',name='Settings',exact=True).click();page.get_by_role('button',name='Quick tour',exact=True).click();expect(page.locator('#tour-layer .tour')).to_be_visible();page.get_by_role('button',name='Skip tour',exact=True).click()
            page.locator('.campaign-nav').get_by_role('link',name='Resources',exact=True).click();page.get_by_role('button',name='Open adventure',exact=True).click()
            expect(page.locator('#stage canvas')).to_be_visible()
            expect(page).to_have_url(__import__('re').compile('adventure='))
            page.get_by_role('button',name='Observatory floor',exact=False).first.click() if page.get_by_role('button',name='Observatory floor',exact=False).count() else None
            generic_url=page.url;page.reload();expect(page.locator('#stage canvas')).to_be_visible()
            page.get_by_role('button',name='All sources',exact=True).click();expect(page.get_by_role('heading',name='Resources',exact=True)).to_be_visible()
            page.get_by_role('button',name='Open adventure',exact=True).click();expect(page.locator('#stage canvas')).to_be_visible()
            page.goto(address(restored,'&section=party&character=explorer'))
            expect(page.get_by_role('heading',name='Explorer',exact=True)).to_be_visible();party_url=page.url
            page.get_by_label('Private notes',exact=True).fill('Original updated private note');page.get_by_role('button',name='Save character notes',exact=True).click();expect(page.locator('#party-status')).to_have_text('Saved')
            map_page=context.new_page();map_page.goto(address(restored,'&section=resources&prepared=1&map=realm&room=village'))
            expect(map_page.locator('#preview-map-loading')).to_be_hidden();expect(map_page.get_by_role('heading',name='Practice region',exact=True)).to_be_visible()
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
            page.locator('.campaign-nav').get_by_role('link',name='Book',exact=True).click()
            expect(page.locator('.campaign-index').get_by_text('Run this session',exact=True)).to_be_visible()
            assert not errors,errors;assert not external,external
            browser.close()
        print('Campaign preview E2E passed: fresh/restored shell, book edit/conflict/reload, missions, party, generic resources, independent map selection, reveal/present. No script errors or external requests.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--exe',type=Path);parser.add_argument('--artifacts',type=Path);args=parser.parse_args();run(args.exe,args.artifacts)
