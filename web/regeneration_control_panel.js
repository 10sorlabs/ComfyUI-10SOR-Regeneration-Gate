import { app } from "../../scripts/app.js";

const MAX_OUTPUTS = 1024;
const NODE_CLASS = "10SORRegenerationControlPanel";
const label = (index) => "Image " + String(index + 1).padStart(2, "0");

function parseValues(value) {
    try {
        const parsed = JSON.parse(value ?? "[]");
        return Array.isArray(parsed) ? parsed.map((v) => v === true) : [];
    } catch {
        return [];
    }
}

app.registerExtension({
    name: "10sorLabs.AdaptiveRegenerationControlPanel",

    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_CLASS) return;

        const oldCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = oldCreated?.apply(this, args);
            this._10sorMutating = true;

            // Only one output is visible initially. Backend indices are
            // stable and support links through subgraphs (unlike virtual nodes).
            while (this.outputs.length > 1) {
                this.removeOutput(this.outputs.length - 1);
            }

            const state = this.widgets?.find((w) => w.name === "values_json");
            if (!state) {
                throw new Error("10SOR Control Panel requires the values_json backend widget.");
            }
            this._10sorState = state;
            state.hidden = true;
            state.computeSize = () => [0, -4];

            this._10sorAll = this.addWidget("toggle", "Toggle all", true, (value) => {
                this._10sorSetAll(Boolean(value));
            }, { on: "ALL ON", off: "ALL OFF" });
            this._10sorAll.serialize = false;
            this._10sorAll.options.serialize = false;
            this._10sorToggles = [];
            this._10sorAddToggle();
            this._10sorMutating = false;
            this._10sorLoadState();

            this.color = "#4f372c";
            this.bgcolor = "#28201d";
            this.setSize(this.computeSize());
            return result;
        };

        nodeType.prototype._10sorAddToggle = function () {
            const index = this._10sorToggles.length;
            const widget = this.addWidget("toggle", label(index), true, () => {
                this._10sorUpdateMaster();
                this._10sorSaveState();
            }, { on: "REGENERATE", off: "PRESERVE" });
            // The source of truth is the backend-recognized values_json
            // widget. Do not send extra, undefined widget keys to the API.
            widget.serialize = false;
            widget.options.serialize = false;
            this._10sorToggles.push(widget);
        };

        nodeType.prototype._10sorEnsureWidgets = function () {
            while (this._10sorToggles.length < this.outputs.length) this._10sorAddToggle();
            while (this._10sorToggles.length > this.outputs.length) {
                const removed = this._10sorToggles.pop();
                this.removeWidget(removed);
            }
        };

        nodeType.prototype._10sorLoadState = function () {
            const stored = parseValues(this._10sorState?.value);
            this._10sorEnsureWidgets();
            this._10sorToggles.forEach((widget, index) => {
                widget.value = stored[index] ?? true;
            });
            this._10sorUpdateMaster();
        };

        nodeType.prototype._10sorUpdateMaster = function () {
            // Mixed state counts as OFF; clicking it enables every slot.
            this._10sorAll.value = this._10sorToggles.every((w) => w.value === true);
        };

        nodeType.prototype._10sorSaveState = function () {
            if (!this._10sorState) return;
            this._10sorState.value = JSON.stringify(this._10sorToggles.map((w) => w.value === true));
            this.graph?.setDirtyCanvas?.(true, true);
        };

        nodeType.prototype._10sorSetAll = function (enabled) {
            for (const widget of this._10sorToggles) widget.value = enabled;
            this._10sorAll.value = enabled;
            this._10sorSaveState();
        };

        nodeType.prototype._10sorSyncOutputs = function () {
            if (this._10sorMutating || app.configuringGraph) return;
            this._10sorMutating = true;
            try {
                let lastConnected = -1;
                for (let index = 0; index < this.outputs.length; index++) {
                    if (this.isOutputConnected(index)) lastConnected = index;
                }
                // Always leave exactly one free socket after the final linked
                // slot, except at the backend's technical capacity.
                const desired = Math.min(MAX_OUTPUTS, Math.max(1, lastConnected + 2));
                while (this.outputs.length < desired) {
                    this.addOutput(label(this.outputs.length), "BOOLEAN");
                }
                while (this.outputs.length > desired) {
                    this.removeOutput(this.outputs.length - 1);
                }
                this._10sorEnsureWidgets();
                this._10sorSaveState();
                this._10sorUpdateMaster();
                this.setSize(this.computeSize());
            } finally {
                this._10sorMutating = false;
            }
        };

        const oldConnections = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (...args) {
            const result = oldConnections?.apply(this, args);
            if (args[0] === window.LiteGraph?.OUTPUT) this._10sorSyncOutputs();
            return result;
        };

        const oldAfterGraphConfigured = nodeType.prototype.onAfterGraphConfigured;
        nodeType.prototype.onAfterGraphConfigured = function (...args) {
            const result = oldAfterGraphConfigured?.apply(this, args);
            // Restore saved per-image controls AFTER graph/widget restoration.
            this._10sorLoadState();
            this._10sorSyncOutputs();
            return result;
        };

        const oldConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = oldConfigure?.apply(this, args);
            this._10sorLoadState();
            return result;
        };
    },
});
