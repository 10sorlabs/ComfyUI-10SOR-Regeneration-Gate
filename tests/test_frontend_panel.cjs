// Frontend smoke tests with a minimal LiteGraph mock; no external packages.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

let extension;
const app = {
  configuringGraph: false,
  registerExtension(e) { extension = e; },
};
const window = { LiteGraph: { OUTPUT: 2 } };
const js = fs.readFileSync("web/regeneration_control_panel.js", "utf8")
  .replace(/^import .*;\s*$/gm, "");
vm.runInNewContext(js, { app, window, console });
assert.ok(extension?.beforeRegisterNodeDef);

class Node {
  constructor() {
    this.outputs = Array.from({ length: 1024 }, (_, i) => ({
      name: "Image " + (i + 1), type: "BOOLEAN", targets: [],
    }));
    this.widgets = [{ name: "values_json", value: "[]" }];
    this.size = [230, 120];
    this.graph = { setDirtyCanvas() {} };
  }
  addOutput(name, type) { this.outputs.push({ name, type, targets: [] }); }
  removeOutput(i) { this.outputs.splice(i, 1); }
  addWidget(type, name, value, callback, options = {}) {
    const widget = { type, name, value, callback, options };
    this.widgets.push(widget);
    return widget;
  }
  removeWidget(w) { this.widgets.splice(this.widgets.indexOf(w), 1); }
  isOutputConnected(i) { return this.outputs[i]?.targets.length > 0; }
  setSize(size) { this.size = size; }
  computeSize() { return [240, this.widgets.length * 26 + 75]; }
}
extension.beforeRegisterNodeDef(Node, { name: "10SORRegenerationControlPanel" });

const panel = new Node();
panel.onNodeCreated();
assert.equal(panel.outputs.length, 1);
assert.equal(panel._10sorToggles.length, 1);
assert.equal(panel._10sorState.hidden, true);

for (let i = 0; i < 24; i++) {
  panel.outputs[i].targets.push({ id: 200 + i });
  panel.onConnectionsChange(2, i, true);
  assert.equal(panel.outputs.length, i + 2);
  assert.equal(panel._10sorToggles.length, i + 2);
}
assert.equal(panel.outputs.length, 25);
assert.equal(panel.widgets.length, 27);

panel._10sorToggles[10].value = false;
panel._10sorToggles[10].callback(false);
assert.equal(JSON.parse(panel._10sorState.value)[10], false);
assert.equal(panel._10sorAll.value, false);

panel._10sorAll.value = false;
panel._10sorAll.callback(false);
assert.ok(panel._10sorToggles.every((w) => w.value === false));
assert.ok(JSON.parse(panel._10sorState.value).every((v) => v === false));

panel._10sorAll.value = true;
panel._10sorAll.callback(true);
assert.ok(panel._10sorToggles.every((w) => w.value === true));

const saved = panel._10sorState.value;
const restored = new Node();
restored.onNodeCreated();
restored.outputs = panel.outputs.map((o) => ({ ...o, targets: [...o.targets] }));
restored._10sorState.value = saved;
restored.onConfigure();
restored.onAfterGraphConfigured();
assert.equal(restored.outputs.length, 25);
assert.equal(restored._10sorToggles.length, 25);
assert.ok(restored._10sorToggles.every((w) => w.value === true));

restored.outputs[23].targets = [];
restored.onConnectionsChange(2, 23, false);
assert.equal(restored.outputs.length, 24);

console.log("PASS: 24 outputs, per-image control, toggle all, save/restore and disconnect");
