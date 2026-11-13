"""Real browser workflow against original synthetic content, source or frozen EXE."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright, expect
from tests.fixtures import make_library
from sessiondesk.store import Store
from tools.smoke_core import call, launch


def resource_navigation(page):
    """Exercise an actually scrolling sidebar, without using an owned book."""
    sidebar=page.locator('.library')
    expect(sidebar.get_by_role('button',name='Expand The observatory',exact=True)).to_be_visible()
    expect(sidebar.locator('[aria-expanded=true]')).to_have_count(0)
    sidebar.get_by_role('button',name='Expand The observatory',exact=True).click()
    expect(sidebar.get_by_role('button',name='Arrival platform',exact=True)).to_be_visible()
    page.locator('#resource-type').select_option('text')
    expect(sidebar.locator('.search-results [data-action=media]')).to_have_count(0)
    expect(sidebar.locator('.search-results')).to_contain_text('Arrival platform')
    page.locator('#resource-type').select_option('image')
    expect(sidebar.locator('.search-results [data-action=entry]')).to_have_count(0)
    expect(sidebar.locator('.search-results')).to_contain_text('Evening sky')
    expect(sidebar.locator('.search-results')).not_to_contain_text('Observatory floor')
    page.locator('#search').fill('floor')
    expect(sidebar.locator('.search-results')).to_have_text('No matches.')
    page.locator('#resource-type').select_option('map')
    expect(sidebar.locator('.search-results [data-action=media]')).to_have_count(2)
    expect(sidebar.locator('.search-results')).not_to_contain_text('Player')
    sidebar.get_by_role('button',name='Observatory floor',exact=False).click()
    expect(page.locator('#search')).to_have_value('floor')
    expect(page.locator('#resource-type')).to_have_value('map')
    page.locator('#search').fill('')
    page.locator('#resource-type').select_option('all')
    expect(sidebar.get_by_role('button',name='Collapse The observatory',exact=True)).to_be_visible()
    page.locator('#search').fill('floor')
    page.locator('#resource-type').select_option('map')
    sidebar.get_by_role('button',name='Collapse all',exact=True).click()
    expect(page.locator('#search')).to_have_value('')
    expect(page.locator('#resource-type')).to_have_value('all')
    expect(sidebar.locator('[aria-expanded=true]')).to_have_count(0)
    # Repeated text/media selections must leave the same sidebar DOM, item
    # position and scroll offset, including after an image finishes loading.
    chapter=sidebar.get_by_role('button',name='Field notes 15',exact=True)
    chapter.scroll_into_view_if_needed()
    def position():
        return chapter.evaluate('(b)=>({scroll:b.closest(".library").scrollTop,y:b.getBoundingClientRect().top})')
    before=position()
    sidebar.evaluate('(root)=>{window.sidebarForTest=root;}')
    for _ in range(3):
        chapter.click()
        expect(page.locator('.sourceview')).to_contain_text('Original field observation 15')
        after=position()
        assert abs(after['scroll']-before['scroll'])<1 and abs(after['y']-before['y'])<1, (before,after)
        assert sidebar.evaluate('(root)=>root===window.sidebarForTest'), 'Sidebar was replaced'
    sidebar.get_by_role('button',name='Expand Field notes 15',exact=True).click()
    sketch=sidebar.get_by_role('button',name='Field sketch 15',exact=False)
    sketch.scroll_into_view_if_needed()
    before=position()
    for _ in range(3):
        sketch.click()
        expect(page.locator('#inspector h2')).to_have_text('Field sketch 15')
        after=position()
        assert abs(after['scroll']-before['scroll'])<1 and abs(after['y']-before['y'])<1, (before,after)
    sidebar.get_by_role('button',name='Collapse all',exact=True).click()
    expect(sidebar.locator('[aria-expanded=true]')).to_have_count(0)
    sidebar.get_by_role('button',name='The observatory',exact=True).click()
    expect(sidebar.locator('[aria-expanded=true]')).to_have_count(0)
    sidebar.get_by_role('button',name='Expand The observatory',exact=True).click()
    sidebar.get_by_role('button',name='Observatory floor',exact=False).click()


def run(exe=None, artifacts=None):
    with tempfile.TemporaryDirectory(prefix="sessiondesk-browser-") as temp:
        base = Path(temp)
        source = make_library(base / "library", wrapped=True, rich=True)
        source_file=source/'data/adventure/adventure-demo.json'
        content=json.loads(source_file.read_text(encoding='utf-8'))
        content['adventureData'][0]['data'].extend([
            {'name':f'Field notes {i:02}', 'entries':[f'Original field observation {i:02}',
                {'type':'image','title':f'Field sketch {i:02}','href':{'type':'internal','path':'original/map.png'}}]}
            for i in range(30)])
        source_file.write_text(json.dumps(content),encoding='utf-8')
        with launch(base / "app",exe) as ready, sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width":1440,"height":960},device_scale_factor=1)
            errors, external = [], []
            def route(r):
                if r.request.url.startswith(ready["url"]): r.continue_()
                else: external.append(r.request.url); r.abort()
            context.route("**/*",route)
            page = context.new_page()
            page.on("pageerror",lambda error: errors.append(str(error)))
            page.goto(ready["url"]+"?tutorial=off#dm="+ready["token"])
            expect(page.get_by_role("heading",name="Adventures")).to_be_visible()
            if artifacts:
                artifacts.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(artifacts / "home.png"))
            page.get_by_role("button",name="New workspace").click()
            page.locator('#workspace-name').fill("Browser test table")
            page.get_by_role("button",name="Create workspace",exact=True).click()
            page.get_by_role("button",name="Add adventure",exact=True).click()
            page.get_by_role('button',name='Close Add adventure',exact=True).click()
            expect(page.locator('#dialog')).not_to_be_visible()
            page.get_by_role("button",name="Add adventure",exact=True).click()
            # A native picker is stubbed with a synthetic path. This verifies its
            # button never submits/validates the empty form before choosing.
            page.route('**/api/pick-folder',lambda route: route.fulfill(json={"path":str(source)}))
            page.get_by_role("button",name="Choose folder",exact=True).click()
            expect(page.locator('#source-status')).to_contain_text('Local 5e.tools copy found')
            if artifacts:page.screenshot(path=str(artifacts/'library-validated.png'))
            page.get_by_role('button',name='Install local copy',exact=True).click()
            expect(page.locator('#install-location')).to_be_visible()
            expect(page.get_by_role('checkbox',name='Include adventure images as needed')).to_be_checked()
            if artifacts:page.screenshot(path=str(artifacts/'library-install.png'))
            # Installation failure is synthetic in CI: never download a real source.
            page.route('**/api/library/install',lambda route:route.fulfill(json={'id':'synthetic-install','kind':'install','state':'running'}))
            page.route('**/api/import/status',lambda route:route.fulfill(json={'id':'synthetic-install','kind':'install','state':'failed','error':'Synthetic checksum failure','error_code':'INSTALL_CHECKSUM'}))
            page.locator('#install-location').fill(str(base/'new source location'))
            page.get_by_role('button',name='Install and validate',exact=True).click()
            expect(page.locator('#source-status')).to_contain_text('Installation stopped')
            expect(page.locator('#source-status progress')).to_have_count(0)
            page.unroute('**/api/import/status')
            warning='Original setup warning. <b>Automatic images stay disabled.</b>'
            page.route('**/api/import/status',lambda route:route.fulfill(json={
                'id':'synthetic-install','kind':'install','state':'complete',
                'result':{'path':str(source),'warnings':[warning]}}))
            page.get_by_role('button',name='Install and validate',exact=True).click()
            expect(page.locator('#source-status')).to_contain_text('Local 5e.tools copy found')
            expect(page.locator('#source-status')).to_contain_text(warning)
            expect(page.locator('#source-status b')).to_have_count(0)
            page.unroute('**/api/library/install');page.unroute('**/api/import/status')
            page.get_by_role('button',name='Use existing copy',exact=True).click()
            page.get_by_role('button',name='Choose folder',exact=True).click()
            expect(page.locator('#source-status')).to_contain_text('Local 5e.tools copy found')
            source_file=source/'data/adventure/adventure-demo.json'
            original=source_file.read_bytes()
            source_file.write_text('{"adventureData": []}',encoding='utf-8')
            page.get_by_role("button",name="Import adventure",exact=True).click()
            expect(page.locator('#source-status')).to_contain_text('Import stopped')
            expect(page.locator('#source-status progress')).to_have_count(0)
            expect(page.get_by_role('button',name='Cancel import',exact=True)).to_have_count(0)
            source_file.write_bytes(original)
            page.get_by_role("button",name="Import adventure",exact=True).click()
            page.get_by_role("button",name="Open adventure").click()
            expect(page.get_by_role("heading",name="Observatory floor")).to_be_visible()
            expect(page.locator('.library')).not_to_contain_text('Observatory floor — Player')
            expect(page.locator('.book-navigation')).to_contain_text('The observatory')
            expect(page.locator('.book-navigation')).to_contain_text('The lower gallery')
            resource_navigation(page)
            wid = call(ready,"bootstrap")["workspaces"][0]["id"]
            aid = call(ready,"workspace",{"workspace":wid})["adventures"][0]["id"]
            scope = {"workspace":wid,"adventure":aid}
            before = call(ready,"session",scope)
            page.locator('#region-select').select_option(index=1)
            assert call(ready,"session",scope) == before, "Selecting a region must not reveal it"
            page.get_by_role("button",name="Read / prepare source").click()
            expect(page.locator('#stage canvas')).to_be_visible()
            expect(page.locator('#room-source .book-box.readaloud')).to_be_visible()
            expect(page.locator('#room-source .book-table')).to_be_visible()
            expect(page.locator('#region-points')).to_have_count(0)
            page.locator('#room-source [data-action=pin]').click()
            expect(page.locator('.pinned-resources')).to_contain_text('Arrival platform')
            page.locator('#search').fill('lens')
            expect(page.locator('.pinned-resources')).to_contain_text('Arrival platform')
            page.locator('#search').fill('')
            expect(page.locator('.pinned-resources')).to_contain_text('Arrival platform')
            page.locator('#translation').fill('Unsaved original browser draft')
            page.locator('.book-navigation').get_by_role('button',name='Evening sky',exact=False).click()
            page.locator('.pinned-resources').get_by_role('button',name='Arrival platform',exact=True).click()
            expect(page.locator('#translation')).to_have_value('Unsaved original browser draft')
            assert call(ready,'session',scope)==before, 'Browsing a resource presented it to players'
            page.locator('.book-navigation').get_by_role('button',name='Observatory floor',exact=False).click()
            page.locator('#region-select').select_option(index=1)
            expect(page.locator('#translation')).to_have_value('Unsaved original browser draft')
            page.locator('#translation').fill("Ένα ήσυχο παρατηρητήριο κάτω από γυάλινη στέγη.")
            page.locator('#private-notes').fill("Private browser note")
            page.get_by_role("checkbox",name="Reviewed and approved").check()
            page.get_by_role("button",name="Save preparation").click()
            expect(page.locator('#toast')).to_have_text("Preparation saved.")
            if artifacts:page.screenshot(path=str(artifacts/'room-reader.png'))
            page.locator('.pinned-resources').get_by_role('button',name='Arrival platform',exact=True).click()
            expect(page.locator('.sourceview .book-box.readaloud')).to_be_visible()
            expect(page.locator('.sourceview .book-table')).to_be_visible()
            expect(page.locator('.book-navigation')).not_to_contain_text('16b')
            if artifacts:page.screenshot(path=str(artifacts/'book-reader.png'))
            page.locator('.book-navigation').get_by_role('button',name='Observatory floor',exact=False).click()
            page.get_by_role("button",name="Present to players").click()
            expect(page.locator("#toast")).to_have_text("Presented. Open the player screen for your TV.")
            # Synthetic legacy import: enrich its metadata while the same tab is
            # visible. The player must reload the new asset, not retain the DM image.
            synthetic_store=Store(base/'app/profile/SessionDesk')
            with synthetic_store.db(wid) as conn:
                legacy=synthetic_store.get(conn,'adventure:'+aid)
                player_asset=next(m for m in legacy['maps'] if m['image_type']=='mapPlayer')['asset']
                legacy.pop('book',None);legacy.pop('book_schema',None)
                for media in legacy['maps']:media.pop('player_map',None)
                synthetic_store.put(conn,'adventure:'+aid,legacy)
            with page.expect_popup() as popup:
                page.get_by_role("button",name="Open player screen").click()
            player = popup.value
            player.on("pageerror",lambda error: errors.append(str(error)))
            expect(player.locator('#player-tabs')).to_contain_text("Observatory floor")
            player.reload()
            expect(player.locator('#player-tabs')).to_contain_text("Observatory floor")
            expect(player.locator('body')).not_to_contain_text("Private browser note")
            expect(player.locator('body')).not_to_contain_text("DM_ONLY_SYNTHETIC_SECRET")
            with player.expect_response(lambda r: '/asset/' in r.url and player_asset in r.url):
                imported_again=call(ready,'import/start',{**scope,'path':str(source),'source':'DEMO'})
                from tools.smoke_core import wait_job
                outcome=wait_job(ready,imported_again['id'])
                assert outcome.get('enriched'),outcome
            expect(player.locator('#player-tabs')).to_contain_text('Observatory floor')
            # Space-pan after focusing outside the map must not produce a reveal stroke.
            page.get_by_role("button",name="Reveal",exact=True).click()
            page.wait_for_function("""() => {const c=document.querySelector('#stage canvas');return c && c.getContext('2d').getImageData(Math.floor(c.width/2),Math.floor(c.height*.7),1,1).data[3]===255;}""")
            page.get_by_role("heading",name="Observatory floor").click()
            box = page.locator('#stage').bounding_box()
            x,y=box['x']+box['width']/2,box['y']+box['height']/2
            page.mouse.move(x,y)
            cursor=page.locator('.brush-cursor')
            expect(cursor).to_be_visible()
            size=cursor.bounding_box()['width']
            page.locator('#brush').fill('90')
            page.mouse.move(x,y)
            expect(cursor).to_be_visible()
            assert abs(cursor.bounding_box()['width']/size-1.5)<.02
            size=cursor.bounding_box()['width']
            canvas=page.locator('#stage canvas').element_handle()
            page.get_by_role('button',name='Zoom in',exact=True).click()
            page.mouse.move(x,y)
            assert abs(cursor.bounding_box()['width']/size-1.25)<.02
            page.get_by_role('button',name='Hide',exact=True).click()
            page.mouse.move(x,y)
            expect(cursor).to_have_class('brush-cursor hide-brush')
            assert canvas.evaluate('(c)=>c===document.querySelector("#stage canvas")'), 'Tool change reset the map'
            page.get_by_role('button',name='Pan',exact=True).click()
            page.mouse.move(x,y)
            expect(cursor).not_to_be_visible()
            page.get_by_role('button',name='Reveal',exact=True).click()
            page.mouse.move(x,y)
            expect(cursor).to_be_visible()
            page.keyboard.down('Space');expect(cursor).not_to_be_visible();page.keyboard.up('Space')
            expect(cursor).to_be_visible()
            if artifacts:page.screenshot(path=str(artifacts/'brush-cursor.png'))
            page.get_by_role('heading',name='Observatory floor',exact=True).click()
            page.keyboard.down('Space');page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+50,y+20,steps=4);page.mouse.up();page.keyboard.up('Space')
            assert call(ready,"session",scope)["fog"] == {}, "Space-pan unexpectedly painted fog"
            page.wait_for_function("""() => {const c=document.querySelector('#stage canvas');return c && c.getContext('2d').getImageData(Math.floor(c.width/2),Math.floor(c.height*.7),1,1).data[3]===255;}""")
            page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+20,y+10,steps=3)
            with page.expect_response(lambda r: r.url.endswith('/api/session/action')):
                page.mouse.up()
            assert call(ready,"session",scope)["fog"], "Reveal brush did not commit: " + page.locator('.toolbar').inner_text() + ' / ' + page.locator('#toast').inner_text()
            page.locator('#region-select').select_option(index=1)
            page.get_by_role('button',name='Draw boundary',exact=True).click()
            page.get_by_role('button',name='Fit',exact=True).click()
            box=page.locator('#stage').bounding_box();scale=min(box['width']/900,box['height']/600)*.95
            offset_x=box['x']+(box['width']-900*scale)/2;offset_y=box['y']+(box['height']-600*scale)/2
            boundary=[[100,150],[350,150],[350,400],[100,400],[100,150]]
            page.mouse.move(offset_x+boundary[0][0]*scale,offset_y+boundary[0][1]*scale);page.mouse.down()
            for px,py in boundary[1:]:page.mouse.move(offset_x+px*scale,offset_y+py*scale,steps=8)
            page.mouse.up()
            page.get_by_role('button',name='Save boundary',exact=True).click()
            expect(page.locator('#toast')).to_have_text('Room boundary saved.')
            page.get_by_role("button",name="Reveal room",exact=True).click()
            page.locator('#shared-note').fill("The platform is clear.")
            page.get_by_role("button",name="Save shared note").click()
            expect(player.locator('#player-note')).to_have_text("The platform is clear.")
            player.get_by_role("button",name="Draw",exact=True).click()
            box=player.locator('#stage').bounding_box();x,y=box['x']+box['width']/2,box['y']+box['height']/2
            player.mouse.move(x,y);player.mouse.down();player.mouse.move(x+40,y+30,steps=6)
            with player.expect_response(lambda r: r.url.endswith('/api/ink') and r.request.post_data_json.get('action') == 'draw'):
                player.mouse.up()
            mid=call(ready,"session",scope)["active"]
            strokes=call(ready,"ink",{**scope,"media":mid})["strokes"]
            assert strokes, "Player drawing was not submitted"
            player.get_by_role("button",name="Zoom in",exact=True).click()
            # Open a second tab and prove player-controlled activation and close-all.
            page.locator('.library').get_by_role('button',name='Expand The lower gallery',exact=True).click()
            page.locator('.book-navigation').get_by_role("button",name="Gallery floor",exact=False).click()
            page.get_by_role("button",name="Present to players").click()
            expect(player.locator('#player-tabs .tab')).to_have_count(2)
            player.get_by_role("button",name="Observatory floor",exact=True).click()
            expect(player.locator('#player-tabs .tab.active')).to_contain_text("Observatory floor")
            page.get_by_role("button",name="Settings",exact=True).click()
            expect(page.get_by_role("switch",name="AI")).to_be_disabled()
            page.locator('#text-size').fill('125')
            assert page.locator('#settings').bounding_box()['width'] == 300
            page.get_by_role("button",name="Settings",exact=True).click()
            if artifacts:
                page.screenshot(path=str(artifacts / 'dm.png'))
                player.screenshot(path=str(artifacts / 'player.png'))
            player.get_by_role("button",name="Close all",exact=True).click()
            expect(player.locator('#player-tabs .tab')).to_have_count(0)
            page.get_by_role('button',name='Workspace',exact=True).click()
            with page.expect_download() as download_info:
                page.get_by_role('button',name='Export backup',exact=True).click()
            backup_path=base/'workspace-backup.zip'
            download_info.value.save_as(backup_path)
            expect(page.locator('#transfer-status')).to_contain_text('Backup ready')
            expect(page.locator('#transfer-status progress')).to_have_count(0)
            page.locator('#dialog').get_by_role('button',name='Close',exact=True).click()
            page.get_by_role('button',name='Workspaces',exact=True).click()
            page.get_by_role('button',name='Restore backup',exact=True).click()
            invalid=base/'invalid.zip';invalid.write_bytes(b'Original synthetic invalid ZIP')
            page.locator('#dialog input[type=file]').set_input_files(str(invalid))
            page.locator('#dialog').get_by_role('button',name='Restore backup',exact=True).click()
            expect(page.locator('#transfer-status')).to_contain_text('stopped')
            expect(page.locator('#transfer-status progress')).to_have_count(0)
            page.locator('#dialog input[type=file]').set_input_files(str(backup_path))
            page.locator('#dialog').get_by_role('button',name='Restore backup',exact=True).click()
            expect(page.get_by_role('heading',name='Browser test table (restored)',exact=True)).to_be_visible()
            workspaces=call(ready,'bootstrap')['workspaces']
            assert len(workspaces)==2
            restored_id=next(w['id'] for w in workspaces if w['id']!=wid)
            restored=call(ready,'adventure',{'workspace':restored_id,'adventure':aid})
            assert restored['pins'] and any(p['notes']=='Private browser note' for p in restored['preparation'].values())
            assert call(ready,'session',{'workspace':restored_id,'adventure':aid})['fog']
            # Keep the cancellation UI deterministic; the real worker/streaming
            # cancellation paths are separately exercised by HTTP/storage tests.
            page.get_by_role('button',name='Workspaces',exact=True).click()
            page.get_by_role('button',name='Restore backup',exact=True).click()
            cancelled={'value':False}
            fake={'id':'synthetic-transfer','kind':'restore','state':'uploading','done':0,'total':100}
            page.route('**/api/backup/restore/start',lambda route:route.fulfill(json=fake))
            page.route('**/api/backup/upload/synthetic-transfer',lambda route:route.fulfill(json=fake))
            page.route('**/api/job/status',lambda route:route.fulfill(json={**fake,'state':'cancelled' if cancelled['value'] else 'running','error':'Synthetic cancellation'}))
            def cancel_route(route):
                cancelled['value']=True
                route.fulfill(json={**fake,'state':'cancelled','cancel_requested':True,'error':'Synthetic cancellation'})
            page.route('**/api/job/cancel',cancel_route)
            page.locator('#dialog input[type=file]').set_input_files(str(backup_path))
            page.locator('#dialog').get_by_role('button',name='Restore backup',exact=True).click()
            page.locator('#transfer-status [data-action=cancel-transfer]').click()
            expect(page.locator('#transfer-status')).to_contain_text('cancelled')
            expect(page.locator('#transfer-status progress')).to_have_count(0)
            for route in ('**/api/backup/restore/start','**/api/backup/upload/synthetic-transfer','**/api/job/status','**/api/job/cancel'):
                page.unroute(route)
            page.locator('#dialog').get_by_role('button',name='Close',exact=True).click()
            assert not errors, errors
            assert not external, external
            context.close();browser.close()
            print("Browser E2E passed: stable/collapsible resource navigation, type filters, scaled brush cursor, preparation/player tools and backup recovery; zero external requests.")


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--exe',type=Path)
    parser.add_argument('--artifacts',type=Path)
    args=parser.parse_args()
    run(args.exe,args.artifacts)
