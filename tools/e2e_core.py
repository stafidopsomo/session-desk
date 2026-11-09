"""Real browser workflow against original synthetic content, source or frozen EXE."""
import argparse
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright, expect
from tests.fixtures import make_library
from sessiondesk.store import Store
from tools.smoke_core import call, launch


def run(exe=None, artifacts=None):
    with tempfile.TemporaryDirectory(prefix="sessiondesk-browser-") as temp:
        base = Path(temp)
        source = make_library(base / "library", wrapped=True, rich=True)
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
            page.goto(ready["url"]+"#dm="+ready["token"])
            expect(page.get_by_role("heading",name="A place for your next adventure.")).to_be_visible()
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
            page.locator('#translation').fill("Ένα ήσυχο παρατηρητήριο κάτω από γυάλινη στέγη.")
            page.locator('#private-notes').fill("Private browser note")
            page.get_by_role("checkbox",name="Reviewed and approved").check()
            page.get_by_role("button",name="Save preparation").click()
            expect(page.locator('#toast')).to_have_text("Preparation saved.")
            if artifacts:page.screenshot(path=str(artifacts/'room-reader.png'))
            page.get_by_role('button',name='Book / resources',exact=True).click()
            expect(page.locator('.sourceview .book-box.readaloud')).to_be_visible()
            expect(page.locator('.sourceview .book-table')).to_be_visible()
            expect(page.locator('.book-navigation')).not_to_contain_text('16b')
            if artifacts:page.screenshot(path=str(artifacts/'book-reader.png'))
            page.get_by_role("button",name="Library",exact=True).click()
            page.get_by_role("checkbox",name="I reviewed this image",exact=False).check()
            page.get_by_role("button",name="Present to players").click()
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
                call(ready,'import/start',{**scope,'path':str(source),'source':'DEMO'})
            expect(player.locator('#player-tabs')).to_contain_text('Observatory floor')
            # Space-pan after focusing outside the map must not produce a reveal stroke.
            page.get_by_role("button",name="Reveal",exact=True).click()
            page.wait_for_function("""() => {const c=document.querySelector('#stage canvas');return c && c.getContext('2d').getImageData(Math.floor(c.width/2),Math.floor(c.height*.7),1,1).data[3]===255;}""")
            page.get_by_role("heading",name="Observatory floor").click()
            box = page.locator('#stage').bounding_box()
            x,y=box['x']+box['width']/2,box['y']+box['height']/2
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
            page.get_by_role("button",name="Gallery floor",exact=True).click()
            page.get_by_role("checkbox",name="I reviewed this image",exact=False).check()
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
            assert not errors, errors
            assert not external, external
            context.close();browser.close()
            print("Browser E2E passed: library validation, install/import failure recovery, preparation and player tools; zero external requests.")


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--exe',type=Path)
    parser.add_argument('--artifacts',type=Path)
    args=parser.parse_args()
    run(args.exe,args.artifacts)
