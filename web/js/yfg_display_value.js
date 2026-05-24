// =============================================================================
// Author      : Manny Gonzalez | YFG 🐯
// Title       : YFG Display Value — Frontend Extension
// Nickname    : yfg_display_value.js
// Description : Displays value in node body and title bar. Value shown FIRST
//               in title so truncation never clips the number. Rename node to
//               set the label that appears after the separator.
// Version     : 1.1.2
// =============================================================================

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_TYPE = "YFG_DisplayValue";
const SEP       = " | ";

console.log("[YFG] DisplayValue JS loading...");

function getOrCreateWidget(node) {
    let w = node.widgets?.find(w => w.name === "yfg_display");
    if (w) return w;

    w = {
        type:    "yfg_display",
        name:    "yfg_display",
        value:   "",
        options: { serialize: false },

        draw(ctx, node, widget_width, y, widget_height) {
            ctx.fillStyle = "rgba(0,0,0,0.25)";
            ctx.beginPath();
            ctx.roundRect(10, y + 2, widget_width - 20, widget_height - 4, 4);
            ctx.fill();

            ctx.fillStyle    = "#aaffaa";
            ctx.font         = "bold 13px monospace";
            ctx.textAlign    = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(String(this.value), widget_width / 2, y + widget_height / 2);
        },

        computeSize(width) {
            return [width, 26];
        },
    };

    if (!node.widgets) node.widgets = [];
    node.widgets.push(w);
    return w;
}

// ── Extract the clean label from whatever the title currently is ──────────────
// Format is either:  "value | label"  (after a run)
//                or:  "label"          (fresh / user just renamed)
function extractLabel(node) {
    if (node.title?.includes(SEP)) {
        // Right side of separator is always the label
        return node.title.split(SEP).slice(1).join(SEP);
    }
    // No separator — entire title is the label
    return node.title ?? "Value";
}

function applyValue(node, value) {
    // Update body widget
    const w = getOrCreateWidget(node);
    w.value = value;

    // Capture label — handles: fresh node, user renamed, or previous run title
    node._yfgBaseTitle = extractLabel(node);

    // Value FIRST so truncation never clips the number
    node.title = `${value}${SEP}${node._yfgBaseTitle}`;

    // Widen node so collapsed title fits
    const needed = (node.title.length * 8) + 60;
    if (needed > node.size[0]) node.size[0] = needed;

    node.setDirtyCanvas(true, false);
}

// ─────────────────────────────────────────────────────────────────────────────

app.registerExtension({
    name: "YFG.DisplayValue",

    async setup() {
        api.addEventListener("executed", ({ detail }) => {
            const text = detail?.output?.text;
            if (!text?.length) return;

            const nodeId = parseInt(detail.node ?? detail.nodeId);
            if (isNaN(nodeId)) return;

            const node = app.graph.getNodeById(nodeId);
            if (!node || node.type !== NODE_TYPE) return;

            applyValue(node, String(text[0]));
        });
    },

    async nodeCreated(node) {
        if (node.type !== NODE_TYPE) return;
        node._yfgBaseTitle = node.title;

        const origConfigure = node.onConfigure?.bind(node);
        node.onConfigure = function (data) {
            origConfigure?.(data);
            // Restore label from saved title
            this._yfgBaseTitle = extractLabel(this);

            // Restore last value into widget
            const saved = data?.widgets_values?.[0];
            if (saved !== undefined && saved !== "") {
                const w = getOrCreateWidget(this);
                w.value = String(saved);
            }
        };
    },
});
