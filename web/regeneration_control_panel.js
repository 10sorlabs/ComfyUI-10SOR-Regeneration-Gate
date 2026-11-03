import { app } from "../../scripts/app.js";
import { LiteGraph, LGraphNode } from "../../scripts/litegraph.js";

/**
 * Frontend-only boolean controller. As with ComfyUI's Primitive node, widget
 * values are written to connected widget inputs before API prompt serialization.
 * No server-side fixed output count is required.
 */
const NODE_TYPE = "10sorLabs/Regeneration Control Panel";
const LABEL = (index) => "Image " + String(index + 1).padStart(2, "0");

function linkedTargets(node, index) {
    const result = [];
    for (const target of node.getOutputNodes?.(index) ?? []) {
        for (let slot = 0; slot < (target.inputs?.length ?? 0); slot++) {
            const link = target.getInputLink?.(slot);
            if (link && String(link.origin_id) === String(node.id) && link.origin_slot === index) {
                result.push([target, slot]);
            }
        }
    }
    return result;
}

app.registerExtension({
    name: "10sorLabs.RegenerationControlPanel",
    registerCustomNodes() {
        class RegenerationControlPanel extends LGraphNode {
            static title = "10SOR Regeneration Control Panel";
            static category = "10sorLabs";
            static collapsable = true;

            constructor(title) {
                super(title ?? RegenerationControlPanel.title);
                this.isVirtualNode = true;
                this.serialize_widgets = true;
                this._restoring = false;
                this._master = this.addWidget("toggle", "Toggle all", true, (value) => {
                    this._setAll(Boolean(value));
                }, { on: "REGENERATE ALL", off: "PRESERVE ALL" });
                this._appendOutput();
                this.setSize(this.computeSize());
            }

            _appendOutput() {
                const index = this.outputs.length;
                const name = LABEL(index);
                this.addOutput(name, "BOOLEAN");
                this.addWidget("toggle", name, true, () => {
                    this._updateMaster();
                    this.applyToGraph();
                }, { on: "REGENERATE", off: "PRESERVE" });
                this.setSize(this.computeSize());
            }

            _setAll(value) {
                for (const widget of this.widgets.slice(1)) widget.value = value;
                this._master.value = value;
                this.applyToGraph();
                this.graph?.setDirtyCanvas?.(true, true);
            }

            _updateMaster() {
                // Mixed selection displays FALSE, allowing the next click to
                // enable all branches again.
                this._master.value = this.widgets.slice(1).every((widget) => Boolean(widget.value));
            }

            _syncOutputs() {
                if (this._restoring || app.configuringGraph) return;
                let lastConnected = -1;
                for (let i = 0; i < this.outputs.length; i++) {
                    if (this.isOutputConnected?.(i)) lastConnected = i;
                }
                const needed = Math.max(1, lastConnected + 2);
                while (this.outputs.length < needed) this._appendOutput();
                while (this.outputs.length > needed) {
                    const last = this.outputs.length - 1;
                    if (this.isOutputConnected?.(last)) break;
                    const widget = this.widgets[last + 1];
                    this.removeOutput(last);
                    if (widget) this.removeWidget(widget);
                }
                this._updateMaster();
                this.setSize(this.computeSize());
                this.graph?.setDirtyCanvas?.(true, true);
            }

            onConnectionsChange(type, slot, connected) {
                if (type !== LiteGraph.OUTPUT || this._restoring || app.configuringGraph) return;
                this._syncOutputs();
                if (connected && slot >= 0) this._applyOutput(slot);
            }

            // A frontend-only controller must not be wired to non-widget inputs,
            // which would require a real producer in the backend execution graph.
            onConnectOutput(_slot, _type, input, target) {
                if (input?.type !== "BOOLEAN") return false;
                const widgetName = input.widget?.name ?? input.name;
                return Boolean(target?.widgets?.some((widget) => widget.name === widgetName));
            }

            _applyOutput(index) {
                const value = Boolean(this.widgets?.[index + 1]?.value);
                for (const [target, slot] of linkedTargets(this, index)) {
                    const input = target?.inputs?.[slot];
                    if (!input) continue;
                    const name = input.widget?.name ?? input.name;
                    const widget = target.widgets?.find((candidate) => candidate.name === name);
                    if (!widget) continue;
                    if (widget.value !== value) {
                        widget.value = value;
                        widget.callback?.(value, app.canvas, target);
                    }
                }
            }

            applyToGraph() {
                // ComfyUI calls this before serializing queued prompts, including
                // controllers inside subgraphs.
                for (let i = 0; i < this.outputs.length; i++) this._applyOutput(i);
            }

            configure(info) {
                // ComfyUI restores widget values in order; recreate every saved
                // widget before the base implementation reads widgets_values.
                this._restoring = true;
                const wanted = Math.max(1, info?.outputs?.length ?? 1);
                while (this.outputs.length < wanted) this._appendOutput();
                try {
                    super.configure(info);
                } finally {
                    this._restoring = false;
                }
                this._master = this.widgets[0];
                this._updateMaster();
            }

            onAfterGraphConfigured() {
                this._syncOutputs();
                this.applyToGraph();
            }
        }

        LiteGraph.registerNodeType(NODE_TYPE, RegenerationControlPanel);
        RegenerationControlPanel.category = "10sorLabs";
    },
});
