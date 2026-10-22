const test = require('node:test');
const assert = require('node:assert/strict');
const model = require('../plugins/ryze.keyboard-layout/KeyboardLayoutModel.js');

const catalog = model.layoutCatalog(`layouts:
- layout: 'us'
  variant: ''
  brief: 'en'
  description: English (US)
- layout: 'us'
  variant: 'intl'
  brief: 'en'
  description: English (US, international)
- layout: 'br'
  variant: ''
  brief: 'pt'
  description: Portuguese (Brazil)
- name: unrelated-model
  description: Must not overwrite a layout
`);

test('lists configured choices and variants without adding catalog languages', () => {
  assert.deepEqual(model.configuredLayouts({layout:'us,br,us', variant:'intl,,custom'},catalog), [
    {index:0,code:'us',variant:'intl',label:'English (US, international)'},
    {index:1,code:'br',variant:'',label:'Portuguese (Brazil)'},
    {index:2,code:'us',variant:'custom',label:'English (US) [custom]'},
  ]);
});

test('missing XKB descriptions and empty seats degrade safely', () => {
  assert.deepEqual(model.configuredLayouts(null,catalog),[]);
  assert.deepEqual(model.configuredLayouts({},catalog),[]);
  assert.equal(model.configuredLayouts({layout:'custom',variant:'local'},{} )[0].label,'custom [local]');
  assert.equal(model.configuredLayouts({layout:'us'},catalog).length,1);
});

test('maps matching layout identity to each keyboard own index', () => {
  const keyboards = [
    {name:'first',layout:'us,br',variant:',abnt2'},
    {name:'second',layout:'br,us',variant:'abnt2,'},
    {name:'different-variant',layout:'br',variant:'dvorak'},
    {name:'different-language',layout:'de',variant:''},
    {name:'hl-virtual-keyboard-fcitx5',layout:'br',variant:'abnt2'},
    {name:'power-button',layout:'br',variant:'abnt2'},
  ];
  assert.deepEqual(model.selectionTargets(keyboards,{code:'br',variant:'abnt2'}),[
    {name:'first',index:1},{name:'second',index:0}
  ]);
  assert.deepEqual(model.selectionTargets(keyboards,null),[]);
  assert.deepEqual(model.selectionTargets([], {code:'br',variant:'abnt2'}),[]);
});

test('preserves existing label and physical-keyboard selection behavior', () => {
  assert.equal(model.shortLabel('Portuguese (Brazil)',{'Portuguese (Brazil)':'pt'}),'PT');
  assert.equal(model.shortLabel('constructor',{}),'CON');
  const keyboards=[{name:'first',active_layout_index:0},{name:'second',active_layout_index:1}];
  assert.equal(model.selectKeyboard(keyboards,'first').name,'first');
  assert.equal(model.selectKeyboard(keyboards,'missing').name,'second');
  assert.equal(model.eventKeyboardName({data:'first,English (US), extra'}),'first');
  assert.equal(model.eventKeyboardName({data:'hl-virtual-keyboard-fcitx5,English (US)'}),'');
});


test('pointer menu covers all six side and vertical placements', () => {
  const size={width:300,height:160}, bounds={x:8,y:32,width:984,height:760};
  const cases=[
    [{x:20,y:40}, {x:32,y:52}],
    [{x:980,y:40}, {x:668,y:52}],
    [{x:20,y:780}, {x:32,y:608}],
    [{x:980,y:780}, {x:668,y:608}],
    [{x:20,y:400}, {x:32,y:320}],
    [{x:980,y:400}, {x:668,y:320}],
  ];
  for (const [point,expected] of cases) assert.deepEqual(model.menuPosition(point,size,bounds,12),expected);
});

test('pointer menu stays inside bounds when neither side has enough space', () => {
  const bounds={x:8,y:32,width:360,height:220};
  for (const point of [{x:8,y:32},{x:185,y:130},{x:367,y:251}]) {
    const p=model.menuPosition(point,{width:340,height:180},bounds,12);
    assert.ok(p.x >= 8 && p.x + 340 <= 368);
    assert.ok(p.y >= 32 && p.y + 180 <= 252);
  }
});

test('pointer monitor routing supports negative origins and logical scaled geometry', () => {
  const screens=[
    {name:'left',x:-1280,y:100,width:1280,height:720},
    {name:'right',x:0,y:0,width:1920,height:1080},
  ];
  assert.equal(model.pointerScreen({x:-1,y:200},screens).name,'left');
  assert.equal(model.pointerScreen({x:0,y:200},screens).name,'right');
  assert.equal(model.pointerScreen({x:-100,y:99},screens),null);
  assert.equal(model.pointerScreen(null,screens),null);
  assert.equal(model.pointerScreen({x:NaN,y:0},screens),null);
});
