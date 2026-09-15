const assert = require('assert').strict;
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const source = fs.readFileSync(path.join(__dirname, '../deploy/wordpress/huntlab-article-toc/assets/article-toc.js'), 'utf8');
const diagnosticsSource = fs.readFileSync(path.join(__dirname, '../deploy/wordpress/huntlab-warm-editorial/assets/reader-tools.js'), 'utf8');
let currentScope = 'toc';

// Handler/coordinate tests only; the deployed mobile viewport must be checked separately.
function fixture({reduced = false, observer = false, margin = '112px', hash = '', missing = false} = {}) {
  const callbacks = {}, attrs = {}, scrolls = [], pushes = [], focuses = [];
  const heading = {id: 'huntlab-section-4', hasAttribute: k => k in attrs,
    setAttribute: (k,v) => { attrs[k] = v; }, removeAttribute: k => { delete attrs[k]; },
    addEventListener: (name,fn) => { callbacks[name] = fn; },
    getBoundingClientRect: () => ({top: 600.6}), focus: opts => focuses.push(opts)};
  const link = {hash: '#huntlab-section-4', target: '', hasAttribute: () => false,
    classList: {toggle() {}}, setAttribute() {}, removeAttribute() {}};
  const parent = {insertBefore(node) { node.parentNode = parent; }};
  const toc = {parentNode: parent, querySelector: () => null, querySelectorAll: () => [link],
    contains: candidate => candidate === link,
    addEventListener: (type, fn, capture) => { assert.equal(type, 'click'); assert.equal(capture, true); callbacks.click = fn; }};
  const win = {scrollY: 1000, scrollX: 3, location: {hash}, history: {state: {existing: 'kept'},
    pushState(state, _, hash) { pushes.push({state, hash}); win.location.hash = hash; }},
    matchMedia: query => ({matches: query.includes('reduced-motion') ? reduced : false, addEventListener() {}}),
    getComputedStyle: () => ({scrollMarginTop: margin}), scrollTo: options => scrolls.push(options)};
  if (observer) win.IntersectionObserver = function () {};
  const container = {contains: candidate => candidate === heading,
    querySelector: selector => selector === '.huntlab-tool-jumps' ? toc :
      selector === '[name="now"]' ? {value:''} : {addEventListener() {}}, querySelectorAll: () => []};
  const doc = {defaultView: win, querySelectorAll: () => [container], querySelector: () => toc, createComment: () => ({}),
    getElementById: id => !missing && id === heading.id ? heading : null};
  function IntersectionObserver() { this.observe = () => {}; }
  vm.runInNewContext(currentScope === 'toc' ? source : diagnosticsSource, {window: win, document: doc, IntersectionObserver});
  function click(overrides = {}) {
    let stopped = false, prevented = false, themeCalls = 0;
    const event = {target: {closest: () => link}, button: 0, detail: 1,
      stopPropagation() { stopped = true; }, preventDefault() { prevented = true; }, ...overrides};
    callbacks.click(event);
    // Kadence installs a target listener; ancestor capture must stop it first.
    if (!stopped) themeCalls++;
    return {stopped, prevented, themeCalls};
  }
  return {click, win, heading, link, attrs, callbacks, scrolls, pushes, focuses};
}

for (currentScope of ['toc', 'diagnostics']) {
const normal = fixture();
assert.deepEqual(normal.click(), {stopped: true, prevented: true, themeCalls: 0});
assert.equal(normal.scrolls[0].top, 1488.6, 'target ends 112px below viewport top, not behind 63px nav');
assert.equal(normal.scrolls[0].left, 3);
assert.equal(normal.scrolls[0].behavior, 'smooth');
assert.equal(normal.focuses[0].preventScroll, true);
assert.equal(normal.attrs.tabindex, '-1');
assert.equal(normal.pushes[0].hash, '#huntlab-section-4');
assert.equal(normal.pushes[0].state.existing, 'kept');
normal.callbacks.blur(); assert.equal(normal.attrs.tabindex, undefined);
normal.click(); assert.equal(normal.pushes.length, 1, 'same hash does not create duplicate history');

const keyboard = fixture({reduced: true, observer: true});
keyboard.attrs.tabindex = '0';
keyboard.click({detail: 0});
assert.equal(keyboard.scrolls[0].behavior, 'instant', 'CSS smooth scrolling cannot override reduced motion');
assert.equal(keyboard.attrs.tabindex, '0', 'preserve pre-existing focusability');
assert.equal(keyboard.callbacks.blur, undefined);

for (const override of [{ctrlKey:true}, {metaKey:true}, {shiftKey:true}, {altKey:true}, {button:1}, {defaultPrevented:true}]) {
  const f = fixture(); const result = f.click(override);
  assert.equal(result.prevented, false); assert.equal(result.themeCalls, 0);
  assert.equal(f.scrolls.length, 0); assert.equal(f.pushes.length, 0); assert.equal(f.focuses.length, 0);
}
for (const kind of ['target', 'download']) {
  const f = fixture();
  if (kind === 'target') f.link.target = '_blank';
  else f.link.hasAttribute = name => name === 'download';
  assert.equal(f.click().prevented, false); assert.equal(f.scrolls.length, 0);
}
const missing = fixture({missing:true}); assert.equal(missing.click().stopped, false);
const outside = fixture(); assert.equal(outside.click({target:{closest:() => ({hash:'#outside'})}}).stopped, false);
const malformed = fixture(); malformed.link.hash = '#%zz'; assert.equal(malformed.click().stopped, false);
const custom = fixture({margin:'160px'}); custom.click(); assert.equal(custom.scrolls[0].top, 1440.6);
const top = fixture({margin:'2000px'}); top.click(); assert.equal(top.scrolls[0].top, 0);
const diagnosticMargin = fixture({margin:'100px'}); diagnosticMargin.click(); assert.equal(diagnosticMargin.scrolls[0].top, 1500.6);
console.log(currentScope + ': scoped capture, margin, history, keyboard and reduced-motion tests passed');
}
