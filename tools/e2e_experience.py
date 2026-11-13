import argparse,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright,expect
from tools.smoke_core import launch,call,wait_job
from tests.fixtures import make_library

def run(exe=None,artifacts=None):
 with tempfile.TemporaryDirectory(prefix='sessiondesk-ui-corrections-') as temp:
  base=Path(temp);lib=make_library(base/'library')
  with launch(base/'app',exe) as ready,sync_playwright() as p:
   wid=call(ready,'workspace/create',{'name':'Original UI check','rules':'2014'})['id']
   imported=wait_job(ready,call(ready,'import/start',{'workspace':wid,'path':str(lib),'source':'DEMO'})['id'])
   aid=imported['id'];scope={'workspace':wid,'adventure':aid};graph=call(ready,'adventure',scope);m=next(x for x in graph['maps'] if x.get('image_type')!='mapPlayer')
   browser=p.chromium.launch();context=browser.new_context(viewport={'width':1500,'height':1000});errors=[]
   context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(ready['url']) else r.abort())
   page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(ready['url']+'?tutorial=off#dm='+ready['token'])
   expect(page.locator('.home-ascii')).to_be_visible()
   expect(page.get_by_role('button',name='New workspace',exact=True)).to_be_visible()
   if artifacts:
    artifacts.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(artifacts/'home.png'))
   page.set_viewport_size({'width':390,'height':844})
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   if artifacts:page.screenshot(path=str(artifacts/'home-mobile.png'))
   page.set_viewport_size({'width':1500,'height':1000})
   page.goto(ready['url']+'#dm='+ready['token'])
   page.get_by_role('button',name='New workspace',exact=True).click()
   page.locator('#workspace-name').fill('Original guided workspace')
   page.get_by_role('button',name='Create workspace',exact=True).click()
   expect(page.locator('#tour-layer .tour')).to_be_visible()
   page.get_by_role('button',name='Next',exact=True).click()
   expect(page.locator('.tour .eyebrow')).to_contain_text('2 of')
   page.get_by_role('button',name='Skip tour',exact=True).click()
   page.get_by_role('button',name='Add adventure',exact=True).click()
   expect(page.locator('#library-path')).to_have_value(str(lib.resolve()))
   expect(page.locator('#source-status')).to_contain_text('Local 5e.tools copy found')
   assert page.locator('#dialog').evaluate('e=>getComputedStyle(e).color')=='rgb(41, 61, 50)'
   if artifacts:page.screenshot(path=str(artifacts/'import.png'))
   page.get_by_role('button',name='Close Add adventure',exact=True).click()
   page.goto(ready['url']+'?workspace='+wid+'&tutorial=off#dm='+ready['token'])
   page.get_by_role('button',name='Open adventure',exact=True).click()
   expect(page.locator('#safe')).to_have_count(0)
   expect(page.get_by_role('button',name='Present to players · with fog',exact=True)).to_be_enabled()
   page.get_by_role('button',name='Present to players · with fog',exact=True).click()
   expect(page.locator('#visibility-status')).to_contain_text('fully hidden')
   with page.expect_popup() as popup:
    page.get_by_role('button',name='Open player screen',exact=True).click()
   player=popup.value
   expect(player.locator('#player-tabs')).to_contain_text('Observatory floor')
   expect(page.locator('#player-presence')).to_have_class('player-presence online')
   divider=page.locator('#inspector-divider');before=page.locator('#inspector').bounding_box()['width'];divider.focus();page.keyboard.press('ArrowLeft');page.keyboard.press('ArrowLeft')
   assert page.locator('#inspector').bounding_box()['width']>=before+39
   box=divider.bounding_box();page.mouse.move(box['x']+4,box['y']+80);page.mouse.down();page.mouse.move(box['x']-50,box['y']+80);page.mouse.up()
   assert page.locator('#inspector').bounding_box()['width']>=before+80
   page.get_by_role('button',name='Reveal',exact=True).click();canvas=page.locator('#stage canvas');box=canvas.bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
   page.wait_for_timeout(500)
   sample="c=>Array.from(c.getContext('2d').getImageData(Math.floor(c.width/2),Math.floor(c.height/2),1,1).data)"
   hidden=canvas.evaluate(sample);page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+12,y+2)
   expect(page.locator('#visibility-status')).to_contain_text('Brush preview')
   cleared=canvas.evaluate(sample);assert hidden!=cleared,(hidden,cleared)
   page.mouse.up();page.wait_for_timeout(300)
   page.get_by_role('button',name='Settings',exact=True).click();expect(page.locator('#settings')).to_be_visible();page.locator('#inspector h2').click();expect(page.locator('#settings')).to_have_count(0)
   page.get_by_role('button',name='Settings',exact=True).click();page.keyboard.press('Escape');expect(page.locator('#settings')).to_have_count(0)
   page.locator('.book-navigation').get_by_role('button',name='The observatory',exact=True).click();reader=page.locator('.sourceview');old=reader.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')
   page.get_by_role('button',name='Settings',exact=True).click();page.locator('#text-size').fill('135');assert reader.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')>old*1.3
   page.get_by_role('button',name='Quick tour',exact=True).click();expect(page.locator('#tour-layer .tour')).to_be_visible();page.get_by_role('button',name='Next',exact=True).click();expect(page.locator('.tour .eyebrow')).to_contain_text('2 of');page.get_by_role('button',name='Skip tour',exact=True).click();expect(page.locator('#dialog')).not_to_be_visible()
   page.get_by_role('button',name='Settings',exact=True).click();page.get_by_role('button',name='Quick tour',exact=True).click()
   session_before=call(ready,'session',scope)
   seen=[]
   while page.locator('#tour-layer').count():
    target=page.locator('#tour-layer .tour-focus').bounding_box();card=page.locator('#tour-layer .tour').bounding_box()
    assert target and target['width']>0 and target['height']>0
    assert card['x']>=0 and card['y']>=0 and card['x']+card['width']<=1501 and card['y']+card['height']<=1001,card
    seen.append(page.locator('#tour-title').inner_text())
    if artifacts and len(seen)==7:
     page.wait_for_timeout(200);assert page.locator('#tour-title').evaluate('e=>getComputedStyle(e).color')=='rgb(41, 60, 49)'
     page.screenshot(path=str(artifacts/'guided-map.png'))
    page.locator('#tour-layer [data-action=tour-next]').click()
   assert 'Prepare narration' in seen and 'Present this map' in seen and 'Set the brush size' in seen,seen
   assert call(ready,'session',scope)==session_before,'Tour changed the player session'
   player.close()
   page.get_by_role('button',name='Workspace',exact=True).click()
   page.locator('[data-action=remove-adventure]').click();page.get_by_role('button',name='Cancel',exact=True).click()
   expect(page.get_by_role('button',name='Open adventure',exact=True)).to_be_visible()
   page.locator('[data-action=remove-adventure]').click();page.locator('[data-action=confirm-remove-adventure]').click()
   expect(page.get_by_role('button',name='Open adventure',exact=True)).to_have_count(0)
   page.get_by_role('button',name='Workspaces',exact=True).click()
   page.get_by_role('button',name='Remove Original UI check',exact=True).click();page.get_by_role('button',name='Cancel',exact=True).click()
   expect(page.get_by_role('button',name='Remove Original UI check',exact=True)).to_be_visible()
   page.get_by_role('button',name='Remove Original UI check',exact=True).click();page.locator('[data-action=confirm-remove-workspace]').click()
   expect(page.get_by_role('button',name='Remove Original UI check',exact=True)).to_have_count(0)
   if artifacts:page.screenshot(path=str(artifacts/'session.png'))
   assert not errors,errors
   context.close();browser.close();print('PASS: direct present, fog visibility/live preview, resizable inspector, settings close/central scaling, LED and tutorial replay; zero JS errors.')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--exe',type=Path);parser.add_argument('--artifacts',type=Path)
 args=parser.parse_args();run(args.exe,args.artifacts)
