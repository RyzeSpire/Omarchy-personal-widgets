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
