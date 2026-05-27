/**
 * YFG Random.org True Random Number (V2) — UI Extension v1.0.0
 *
 * Displays the generated number next to each output slot connector
 * (number, float, int) after every run — same pattern as the
 * RandomImageFromDirectory node.
 *
 * @author  Manny Gonzalez
 * @title   🐯 YFG Comical Nodes
 * @version 1.0.0
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_TYPE = "RandomOrgV2TrueRandomNumber_node";

console.log("[YFG] RandomOrgV2 JS extension loading…");

// Each output slot gets its own key so display matches the actual type.
// Slot 0 = number, 1 = float, 2 = int
const DISPLAY_SLOTS = {
    yfg_number: 0,
    yfg_float:  1,
    yfg_int:    2,
};

// ─────────────────────────── Output slot value display ───────────────────────

function applyOutputValues(node, output) {
    setTimeout(() => {
        for (const [key, slotIdx] of Object.entries(DISPLAY_SLOTS)) {
            const raw = output?.[key];
            if (raw === undefined || raw === null) continue;

            const value = Array.isArray(raw) ? raw[0] : raw;
            if (value === undefined) continue;

            const slot = node.outputs?.[slotIdx];
            if (!slot) continue;

            let origName = node._yfgOrigOutputNames?.[slotIdx];
            if (!origName) {
                const src   = slot.label || slot.name || "";
                const parts = src.split("  ");
                origName = parts.length > 1 ? parts.slice(1).join("  ") : src;
            }

            slot.label = `${value}  ${origName}`;
        }

        if (app.canvas?.draw) {
            app.canvas.draw(true, true);
        } else {
            node.setDirtyCanvas(true, true);
        }
    }, 100);
}

// ─────────────────────────── ComfyUI Extension ───────────────────────────────

app.registerExtension({
    name: "YFG.RandomOrgV2",

    async setup() {
        api.addEventListener("executed", ({ detail }) => {
            const nodeId = parseInt(detail.node ?? detail.nodeId);
            if (isNaN(nodeId)) return;

            const node = app.graph.getNodeById(nodeId);
            if (!node) return;
            if (node.type !== NODE_TYPE && node.comfyClass !== NODE_TYPE) return;

            const output = detail?.output;
            if (!output) return;

            applyOutputValues(node, output);
        });

        console.log("[YFG] RandomOrgV2 executed event listener registered.");
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_TYPE) return;

        console.log("[YFG] Hooking RandomOrgV2TrueRandomNumber_node…");

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            // Store original output names for clean label rendering
            this._yfgOrigOutputNames = (this.outputs ?? []).map(o => o.name);
            console.log("[YFG] ✅ RandomOrgV2 output names stored.");
            return result;
        };
    },
});
