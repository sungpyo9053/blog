const assert = require('assert');
const {enhance} = require('../deploy/wordpress/huntlab-code-tools/assets/code-tools.js');

// A small DOM adapter tests handlers, not browser clipboard permission or layout.
class Element {
  constructor(tag, text = '') { this.tagName = tag; this.textContent = text; this.attributes = {}; this.children = []; this.handlers = {}; }
  hasAttribute(k) { return Object.hasOwn ? Object.hasOwn(this.attributes, k) : k in this.attributes; }
  setAttribute(k, v) { this.attributes[k] = v; }
  appendChild(child) { this.children.push(child); child.parentNode = this; }
  insertBefore(child, before) { this.children.splice(this.children.indexOf(before), 0, child); child.parentNode = this; }
  addEventListener(name, fn) { this.handlers[name] = fn; }
  focus() { this.focused = true; }
}
function fixture(texts) {
  const parent = new Element('article');
  const codes = texts.map(text => { const pre = new Element('pre'), code = new Element('code', text); parent.appendChild(pre); pre.appendChild(code); return code; });
  const selection = {removeAllRanges() { this.cleared = true; }, addRange(range) { this.range = range; }};
  const doc = {querySelectorAll: () => codes, createElement: tag => new Element(tag), defaultView: {getSelection: () => selection}, createRange: () => ({selectNodeContents(code) { this.code = code; }})};
  return {parent, codes, doc, selection};
}
async function main() {
  const original = 'echo "<script>never execute</script>"\n  한글\n';
  const f = fixture([original, 'second\n']);
  const writes = [];
  enhance(f.doc, {clipboard: {writeText: async text => writes.push(text)}});
  assert.equal(f.parent.children.length, 4);
  const [copy, select, status] = f.parent.children[0].children;
  assert.equal(copy.attributes['aria-label'], '예제 1 복사');
  assert.equal(copy.type, 'button');
  assert.equal(f.codes[0].parentNode.attributes.tabindex, '0');
  assert.equal(f.codes[0].parentNode.attributes.role, 'region');
  assert.equal(status.attributes['aria-live'], 'polite');
  await copy.handlers.click();
  assert.deepEqual(writes, [original]);
  assert.equal(status.textContent, '복사했습니다.');
  assert.equal(copy.attributes['aria-disabled'], 'false');
  assert.equal(f.codes[0].textContent, original);
  select.handlers.click();
  assert.equal(f.selection.range.code, f.codes[0]);
  assert.equal(f.selection.cleared, true);
  assert.equal(f.codes[0].parentNode.focused, true);
  assert(!f.selection.range.code.textContent.includes('전체 선택'));
  enhance(f.doc, {});
  assert.equal(f.parent.children.length, 4, 'initialization is idempotent');

  for (const navigatorObject of [{}, {clipboard: {writeText: async () => { throw Error('denied'); }}}]) {
    const blocked = fixture(['safe\n']);
    enhance(blocked.doc, navigatorObject);
    const [button, , message] = blocked.parent.children[0].children;
    await button.handlers.click();
    assert(message.textContent.includes('전체 선택'));
    assert.equal(button.attributes['aria-disabled'], 'false');
    assert.equal(blocked.selection.range, undefined, 'permission failure does not change selection');
  }
  const pending = fixture(['pending\n']);
  let finish, calls = 0;
  enhance(pending.doc, {clipboard: {writeText: () => { calls++; return new Promise(resolve => { finish = resolve; }); }}});
  const button = pending.parent.children[0].children[0];
  const first = button.handlers.click();
  assert.equal(button.attributes['aria-disabled'], 'true');
  assert.equal(button.disabled, undefined, 'native focus is not disabled');
  await button.handlers.click();
  assert.equal(calls, 1);
  pending.parent.children[0].children[1].handlers.click();
  const selectionMessage = pending.parent.children[0].children[2].textContent;
  finish(); await first;
  assert.equal(button.attributes['aria-disabled'], 'false');
  assert.equal(pending.parent.children[0].children[2].textContent, selectionMessage, 'older copy does not overwrite newer selection status');
  const custom = fixture(['custom']);
  custom.codes[0].parentNode.setAttribute('tabindex', '-1');
  custom.codes[0].parentNode.setAttribute('aria-label', 'Existing label');
  enhance(custom.doc, {});
  assert.equal(custom.codes[0].parentNode.attributes.tabindex, '-1');
  assert.equal(custom.codes[0].parentNode.attributes['aria-label'], 'Existing label');
  custom.doc.defaultView.getSelection = () => null;
  custom.parent.children[0].children[1].handlers.click();
  assert(custom.parent.children[0].children[2].textContent.includes('직접 선택'));
  for (const failingAPI of ['getSelection', 'createRange', 'addRange', 'focus']) {
    const exceptional = fixture(['safe']);
    enhance(exceptional.doc, {});
    const fail = () => { throw Error('restricted'); };
    if (failingAPI === 'getSelection') exceptional.doc.defaultView.getSelection = fail;
    if (failingAPI === 'createRange') exceptional.doc.createRange = fail;
    if (failingAPI === 'addRange') exceptional.selection.addRange = fail;
    if (failingAPI === 'focus') exceptional.codes[0].parentNode.focus = fail;
    exceptional.parent.children[0].children[1].handlers.click();
    assert(exceptional.parent.children[0].children[2].textContent.includes('직접 선택'));
  }
  console.log('Code tools: exact text, accessibility attributes, selection, denied/unavailable clipboard, duplicate init, concurrent click and existing attributes passed');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
