// Runs the recommendation logic from index.html for a list of scenarios.
// Usage: node tests/dashboard_logic.js <scenarios.json>   (prints one recommendation text per scenario)
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];

const fakeElement = () => ({
  textContent: '', innerHTML: '', value: '', checked: false, disabled: false, hidden: false,
  classList: { toggle() {} }, addEventListener() {}, appendChild() {}, setAttribute() {}
});
const elements = {};
const sandbox = {
  console,
  document: {
    getElementById: id => (elements[id] ||= fakeElement()),
    addEventListener() {},
    querySelectorAll: () => [],
    createElement: () => fakeElement()
  },
  window: { addEventListener() {} },
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  fetch: () => Promise.reject(new Error('no network in tests')),
  requestAnimationFrame() {},
  cancelAnimationFrame() {}
};
vm.createContext(sandbox);
vm.runInContext(script + '\n;globalThis.__api = { getRecommendation, defaultCriteria };', sandbox);
const { getRecommendation, defaultCriteria } = sandbox.__api;

const scenarios = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const texts = scenarios.map(({ member, criteria }) =>
  getRecommendation({ afk: false, ...member }, { ...defaultCriteria, ...criteria }).text);
process.stdout.write(JSON.stringify(texts));
