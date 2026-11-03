// Standalone frontend smoke test; no ComfyUI runtime or third-party deps required.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const types = {};
const LiteGraph = {
  OUTPUT: 2,
  registerNodeType: (name, cls) => { types[name] = cls; },
};
const app = {
  configuringGraph: false,
  canvas: {},
  registerExtension(extension) { extension.registerCustomNodes(); },
};
class LGraphNode {
  constructor(title) { this.title = title; this.id = 100; this.outputs = []; this.widgets = []; this.size = [250, 80]; }
  addOutput(name, type) { this.outputs.push({ name, type, targets: [] }); }
  addWidget(type, name, value, callback, options = {}) {
    const widget = { type, name, value, callback, options };
    this.widgets.push(widget);
    return widget;
  }
  removeOutput(index) { this.outputs.splice(index, 1); }
  removeWidget(widget) { this.widgets.splice(this.widgets.indexOf(widget), 1); }
  computeSize() { return [250, 80 + this.widgets.length * 24]; }
  setSize(size) { this.size = size; }
  isOutputConnected(index) { return !!this.outputs[index]?.targets.length; }
  getOutputNodes(index) { return this.outputs[index]?.targets ?? []; }
  configure(info) {
    this.outputs = info.outputs.map((o) => ({ ...o, targets: [] }));
    this.widgets.forEach((widget, i) => { widget.value = info.widgets_values[i]; });
  }
}
const source = fs.readFileSync("web/regeneration_control_panel.js", "utf8")
  .replace(/^import .*;\s*$/gm, "");
vm.runInNewContext(source, { app, window: { LiteGraph, LGraphNode }, console });

const Panel = types["10sorLabs/Regeneration Control Panel"];
assert.ok(Panel, "Panel was not registered");
const panel = new Panel();
panel.graph = { setDirtyCanvas() {} };
assert.equal(panel.outputs.length, 1, "First launch must show only one output");

const gates = [];
for (let index = 0; index < 24; index++) {
  const gate = {
    widgets: [{ name: "regenerate", value: true }],
    inputs: [{ name: "regenerate" }],
    getInputLink(slot) {
      return slot === 0 ? { origin_id: panel.id, origin_slot: index } : null;
    },
  };
  assert.equal(panel.onConnectOutput(index, "BOOLEAN", { type: "BOOLEAN", name: "regenerate" }, gate), true);
  assert.equal(panel.onConnectOutput(index, "IMAGE", { type: "IMAGE", name: "fresh_image" }, gate), false);
  panel.outputs[index].targets.push(gate);
  panel.onConnectionsChange(LiteGraph.OUTPUT, index, true);
  assert.equal(panel.outputs.length, index + 2, "Connecting the final output must add one more");
  gates.push(gate);
}

assert.equal(panel.widgets.length, 26, "One master plus 25 individual switches");
panel.widgets[5].value = false;
panel.widgets[5].callback(false);
assert.equal(gates[4].widgets[0].value, false);
assert.equal(panel.widgets[0].value, false);
panel.widgets[0].value = true;
panel.widgets[0].callback(true);
assert.ok(gates.every((gate) => gate.widgets[0].value === true));
panel.widgets[0].value = false;
panel.widgets[0].callback(false);
assert.ok(gates.every((gate) => gate.widgets[0].value === false));

const json = {
  outputs: panel.outputs.map((output) => ({ name: output.name, type: output.type })),
  widgets_values: panel.widgets.map((widget) => widget.value),
};
const restored = new Panel();
restored.configure(json);
assert.equal(restored.outputs.length, 25);
assert.equal(restored.widgets.length, 26);
assert.ok(restored.widgets.slice(1).every((widget) => widget.value === false));

panel.outputs[23].targets = [];
panel.onConnectionsChange(LiteGraph.OUTPUT, 23, false);
assert.equal(panel.outputs.length, 24, "Disconnected trailing slots should collapse");

console.log("PASS: dynamic expansion, toggle all, individual control, restore and pruning");
