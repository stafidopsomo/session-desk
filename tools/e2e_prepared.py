"""Same packaged app: fresh-user UI plus original prepared-campaign import."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import expect, sync_playwright
from tests.prepared_fixture import make_prepared, pack, rules_library
from sessiondesk.store import Store
from sessiondesk.workspace_modules import MODULE_ID
from tools.smoke_core import call, launch


def prepared_action(page, body):
    page.evaluate("""async body => {
      const response=await fetch('api/action',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body)});
      if(!response.ok)throw Error('Could not present original fixture resource');
    }""", body)


def player_render_order(page, player):
    """A slower picture must not repaint the map after a newer tab selection."""
    prepared_action(page, {'action':'map','mapId':'realm'})
    prepared_action(page, {'action':'map','mapId':'practice'})
    expect(player.get_by_role('button',name='Show Practice floor',exact=True)).to_have_attribute('aria-pressed','true')
    player.evaluate("""async () => {
      const {AtlasMap}=await import(new URL('static/map.js',location.href).href);
      const originalSet=AtlasMap.prototype.set,originalDecode=Image.prototype.decode;
      window.renderedMapProbe=[];
      AtlasMap.prototype.set=function(map,state){
        if(this.canvas.id==='canvas')window.renderedMapProbe.push({map:map.id,version:state.version});
        return originalSet.call(this,map,state);
      };
      let held=false;
      Image.prototype.decode=function(){
        const decoded=originalDecode.call(this);
        if(!held&&new URL(this.src).pathname.endsWith('/maps/player.png')){
          held=true;return decoded.then(()=>new Promise(resolve=>window.releasePictureProbe=resolve));
        }
        return decoded;
      };
      window.cleanupRenderProbe=()=>{AtlasMap.prototype.set=originalSet;Image.prototype.decode=originalDecode;};
    }""")
    try:
        prepared_action(page, {'action':'picture','path':'maps/player.png'})
        player.wait_for_function('()=>typeof window.releasePictureProbe==="function"')
        player.get_by_role('button',name='Show Practice region',exact=True).click()
        player.wait_for_function('()=>window.renderedMapProbe.some(x=>x.map==="realm")')
        player.evaluate("""async () => {
          window.releasePictureProbe();
          await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
        }""")
        rendered=player.evaluate('()=>window.renderedMapProbe')
        assert rendered[-1]['map']=='realm',rendered
        expect(player.locator('#overlay')).to_be_hidden()
    finally:
        player.evaluate('()=>window.cleanupRenderProbe()')
    player.get_by_role('button',name='Show Practice floor',exact=True).click()
    expect(player.locator('#partyTools summary')).to_be_visible()


def run(exe=None,artifacts=None):
    with tempfile.TemporaryDirectory(prefix='sessiondesk-prepared-browser-') as temp:
        base=Path(temp)
        original=make_prepared(base/'original')
        archive=pack(original,base/'recovery.zip',recovery=True)
        library=rules_library(base/'2014-source')
        with launch(base/'app',exe) as ready,sync_playwright() as p:
            browser=p.chromium.launch()
            context=browser.new_context(viewport={'width':1500,'height':1000})
            external,errors=[],[]
            def route(r):
                if r.request.url.startswith(ready['url']):r.continue_()
                else:external.append(r.request.url);r.abort()
            context.route('**/*',route)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(ready['url']+'?tutorial=off#dm='+ready['token'])
            expect(page.get_by_role('heading',name='Adventures')).to_be_visible()
            # New users get no empty optional tabs, even in the same EXE.
            expect(page.get_by_role('button',name='Characters',exact=True)).to_have_count(0)
            page.get_by_role('button',name='New workspace',exact=True).click()
            page.locator('#workspace-name').fill('Fresh example')
            page.get_by_role('button',name='Create workspace',exact=True).click()
            expect(page.locator('.prepared-workspace')).to_have_count(0)
            expect(page.get_by_role('button',name='Add adventure',exact=True)).to_be_visible()
            page.get_by_role('button',name='Workspaces',exact=True).click()
            page.get_by_role('button',name='Restore backup',exact=True).click()
            page.locator('#dialog input[type=file]').set_input_files(str(archive))
            page.locator('#dialog').get_by_role('button',name='Restore backup',exact=True).click()
            expect(page.locator('.prepared-workspace')).to_contain_text('2 maps · 1 characters',timeout=30000)
            page.route('**/api/pick-folder',lambda r:r.fulfill(json={'path':str(library)}))
            page.get_by_role('button',name='Connect 2014 library',exact=True).click()
            expect(page.locator('.prepared-workspace')).to_contain_text('2014 rules library connected.')
            wid=next(w['id'] for w in call(ready,'bootstrap')['workspaces'] if w['name']=='Prepared example')
            page.get_by_role('button',name='Open prepared campaign',exact=True).click()
            expect(page.get_by_role('heading',name='Practice floor',exact=True)).to_be_visible(timeout=20000)
            expect(page.locator('#charactersNav')).to_be_visible()
            expect(page.locator('#shoppingNav')).to_be_visible()
            expect(page.locator('#generateRoomScenes')).to_have_count(0)
            expect(page.locator('a[href*=usage]')).to_have_count(0)
            page.locator('#charactersNav').click()
            page.locator('.character-sheet summary').click()
            expect(page.get_by_role('textbox',name='Name',exact=True)).to_have_value('Explorer')
            page.get_by_text('Read backstory',exact=True).click()
            expect(page.locator('.sheet-body')).to_contain_text('Original synthetic backstory.')
            page.get_by_text('Stats, rules, and spells',exact=True).click()
            page.locator('[data-sheet=hpCurrent]').fill('17')
            page.locator('[data-sheet=hpCurrent]').blur()
            expect(page.locator('[data-sheet=hpCurrent]')).to_have_value('17')
            expect(page.locator('.sheet-body')).to_contain_text('Saved',timeout=15000)
            page.locator('#aftermathNav').click()
            expect(page.locator('#aftermathView')).to_contain_text('A quiet return')
            page.locator('#shoppingNav').click()
            expect(page.frame_locator('#shoppingView iframe').get_by_text('Example remedy',exact=True)).to_be_visible()
            expect(page.frame_locator('#shoppingView iframe').get_by_text('25 gp',exact=True)).to_be_visible()
            page.locator('#atlasNav').click()
            with page.expect_popup() as popup:page.locator('#openPlayer').click()
            player=popup.value;player.on('pageerror',lambda e:errors.append(str(e)))
            expect(player.locator('#playerTabs')).to_contain_text('Practice floor')
            assert player.url.split('/')[5]==ready['player_token'], 'Player window received wrong capability'
            assert player.evaluate("sessionStorage.getItem('dmToken')") is None
            expect(player.locator('body')).not_to_contain_text('SYNTHETIC_PRIVATE')
            expect(player.locator('body')).not_to_contain_text('Original secret')
            player.locator('#roomPicker').select_option('a:0')
            expect(player.locator('#notebook')).to_be_visible()
            player.locator('#roomNotes').fill('An original shared observation.')
            expect(player.locator('#noteStatus')).to_contain_text('Saved',timeout=10000)
            player.get_by_role('button',name='Draw',exact=True).click()
            player.locator('#roomPicker').select_option('')
            player.locator('#closeNotebook').click()
            box=player.locator('#canvas').bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
            player.mouse.move(x,y);player.mouse.down();player.mouse.move(x+30,y+20,steps=4);player.mouse.up()
            expect(player.locator('#undoDrawing')).to_be_enabled()
            player.get_by_role('button',name='Eraser',exact=True).click()
            player.get_by_role('button',name='Zoom in',exact=True).click()
            # A picture/reference hides the dungeon tools beneath it. Returning
            # to the map restores them without changing its tokens or fog.
            expect(player.locator('#partyTools summary')).to_be_visible()
            prepared_action(page, {'action':'picture','path':'adventures/practice/a.png'})
            expect(player.locator('#overlay')).to_be_visible()
            expect(player.locator('#partyTools summary')).to_be_hidden()
            player.get_by_role('button',name='Show Practice floor',exact=True).click()
            expect(player.locator('#overlay')).to_be_hidden()
            expect(player.locator('#partyTools summary')).to_be_visible()
            page.locator('#shoppingNav').click()
            page.locator('#presentShop').click()
            expect(player.locator('#bookSection')).to_be_visible()
            expect(player.locator('#partyTools summary')).to_be_hidden()
            player.get_by_role('button',name='Show Practice floor',exact=True).click()
            expect(player.locator('#bookSection')).to_be_hidden()
            expect(player.locator('#partyTools summary')).to_be_visible()
            page.locator('#atlasNav').click()
            player_render_order(page, player)
            # Persistent fog is unchanged by browsing a prepared guide/sheet.
            data_root=base/'app/profile/SessionDesk'
            store=Store(data_root)
            with store.db(wid) as conn:module=store.get(conn,'module:'+MODULE_ID)
            root=store.folder(wid)/'module-files'/MODULE_ID
            state=json.loads((root/'state/table.json').read_text())
            assert len(state['fog']['practice']['operations'])==2
            assert json.loads((root/'characters/explorer/character.json').read_text())['threads'][0]['status']=='Idea'
            if artifacts:
                artifacts.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(artifacts/'prepared-dm.png'))
                player.screenshot(path=str(artifacts/'prepared-player.png'))
            page.get_by_role('link',name='Workspace',exact=True).click()
            expect(page.locator('.prepared-workspace')).to_be_visible()
            with page.expect_download() as download_info:
                page.get_by_role('button',name='Export backup',exact=True).click()
            exported=base/'portable.zip';download_info.value.save_as(exported)
            other=Store(base/'other-machine');restored=other.restore_file(exported)
            restored_root=other.folder(restored['id'])/'module-files'/MODULE_ID
            assert json.loads((restored_root/'characters/explorer/character.json').read_text())['sheet']['hpCurrent']==17
            assert json.loads((restored_root/'state/room-notes.json').read_text())['practice']['a:0']=='An original shared observation.'
            assert (restored_root/'prep/do-not-run.py').read_bytes()==(original/'prep/do-not-run.py').read_bytes()
            assert (restored_root/'prep/original.pdf').read_bytes()==(original/'prep/original.pdf').read_bytes()
            assert not errors,errors
            assert not external,external
            context.close();browser.close()
            print('Prepared browser E2E passed: same app, fresh empty UI, recovery import, characters/rules, guides, shops, player notes/drawing and portable edited backup; zero external requests.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--exe',type=Path);parser.add_argument('--artifacts',type=Path)
    args=parser.parse_args();run(args.exe,args.artifacts)
