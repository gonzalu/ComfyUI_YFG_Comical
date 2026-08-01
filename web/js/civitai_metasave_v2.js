/**
 * YFG CivitAI MetaSave V2 — Dynamic Extra Metadata Fields
 *
 * @author  Manny Gonzalez
 * @title   🐯 YFG Comical Nodes
 * @version 1.2.0
 *
 * Keeps exactly one empty extra_key / extra_value pair at the bottom of the
 * node. Fill it in and another empty pair appears; clear the trailing ones and
 * the surplus is pruned back. Pair 1 is declared in Python and never removed.
 *
 * v1.1.0 changes:
 *   - Detects edits by watching the widget's `value` property rather than
 *     relying on widget.callback, which does not fire on every edit path in
 *     recent ComfyUI frontends.
 *   - Also syncs from nodeCreated and afterConfigureGraph.
 *   - Console logging, off by default. Enable with:
 *       window.YFG_MS2_DEBUG = true
 */

import { app } from "../../../scripts/app.js";

const NODE_NAME    = "YFG_CivitAI_MetaSave_V2";
const STATIC_PAIRS = 1;    // extra_key1 / extra_value1 declared in Python
const MAX_PAIRS    = 32;

const keyName = n => `extra_key${n}`;
const valName = n => `extra_value${n}`;

function log(...args) {
    if (window.YFG_MS2_DEBUG !== true) return;
    console.log("%c[YFG MetaSave V2]", "color:#a6e3a1;font-weight:bold", ...args);
}

log("extension file loaded");

// ─────────────────────────────── helpers ────────────────────────────────────

const widgetIndex = (node, name) => (node.widgets || []).findIndex(w => w.name === name);
const getWidget   = (node, name) => (node.widgets || []).find(w => w.name === name);

function isConnected(node, name) {
    const input = (node.inputs || []).find(i => i.name === name);
    return !!(input && input.link != null);
}

function pairInUse(node, n) {
    const k  = getWidget(node, keyName(n));
    const v  = getWidget(node, valName(n));
    const kv = k && typeof k.value === "string" ? k.value.trim() : "";
    const vv = v && typeof v.value === "string" ? v.value.trim() : "";
    return kv !== "" || vv !== ""
        || isConnected(node, keyName(n)) || isConnected(node, valName(n));
}

function highestPair(node) {
    let max = STATIC_PAIRS;
    for (const w of node.widgets || []) {
        const m = /^extra_key(\d+)$/.exec(w.name || "");
        if (m) max = Math.max(max, parseInt(m[1], 10));
    }
    return max;
}

// ───────────────────────── change detection ─────────────────────────────────

/**
 * Watch a widget's `value` for changes.
 *
 * Replaces the property with a getter/setter backed by a private field. This
 * fires for user edits, programmatic assignment, and workflow loading alike —
 * unlike widget.callback, which recent frontends do not always invoke.
 */
function watchWidget(node, w) {
    if (!w || w._yfgWatched) return;

    let backing = w.value;
    try {
        Object.defineProperty(w, "value", {
            get() { return backing; },
            set(v) {
                const changed = backing !== v;
                backing = v;
                if (changed) scheduleSync(node);
            },
            configurable: true,
            enumerable:   true,
        });
        w._yfgWatched = true;
    } catch (e) {
        log("could not watch widget", w.name, e);
    }

    // Belt and braces: keep the callback hook as a secondary trigger
    const orig = w.callback;
    w.callback = function (...args) {
        const r = orig ? orig.apply(this, args) : undefined;
        scheduleSync(node);
        return r;
    };
}

function watchAllPairs(node) {
    const last = highestPair(node);
    for (let n = 1; n <= last; n++) {
        watchWidget(node, getWidget(node, keyName(n)));
        watchWidget(node, getWidget(node, valName(n)));
    }
}

// ─────────────────────────── add / remove pairs ─────────────────────────────

// RenderShape.HollowCircle — what ComfyUI uses for optional input sockets
const HOLLOW_CIRCLE = 7;

/**
 * Give a dynamically-created widget its matching input socket.
 *
 * node.addWidget() alone creates a widget with no entry in node.inputs, so
 * there is nothing on the node to drop a link onto. ComfyUI's own
 * addInputWidget() always pairs the two; this mirrors that behaviour.
 */
function addWidgetInputSocket(node, name) {
    if ((node.inputs || []).some(i => i.name === name)) return;
    try {
        node.addInput(name, "STRING", {
            widget: { name },
            shape: HOLLOW_CIRCLE,
            localized_name: name,
        });
    } catch (e) {
        log("could not add input socket for", name, e);
    }
}

function removeWidgetInputSocket(node, name) {
    const idx = (node.inputs || []).findIndex(i => i.name === name);
    if (idx < 0) return;
    try {
        // removeInput also drops any link attached to the socket
        node.removeInput(idx);
    } catch (e) {
        log("could not remove input socket for", name, e);
    }
}

function addPair(node, n) {
    if (getWidget(node, keyName(n))) return;

    const kw = node.addWidget("text", keyName(n), "", () => scheduleSync(node), {});
    const vw = node.addWidget("text", valName(n), "", () => scheduleSync(node), {});
    kw.tooltip = `Custom metadata key ${n}`;
    vw.tooltip = `Custom metadata value ${n}. Can be typed or wired from another node.`;
    watchWidget(node, kw);
    watchWidget(node, vw);

    addWidgetInputSocket(node, keyName(n));
    addWidgetInputSocket(node, valName(n));

    log(`added pair ${n}`);
}

function removePair(node, n) {
    if (n <= STATIC_PAIRS) return;
    for (const name of [valName(n), keyName(n)]) {
        removeWidgetInputSocket(node, name);
        const idx = widgetIndex(node, name);
        if (idx >= 0) node.widgets.splice(idx, 1);
    }
    log(`removed pair ${n}`);
}

// ──────────────────────────────── sync ──────────────────────────────────────

function syncPairs(node) {
    if (!node.widgets) return;
    let last = highestPair(node);

    while (last > STATIC_PAIRS && !pairInUse(node, last) && !pairInUse(node, last - 1)) {
        removePair(node, last);
        last--;
    }
    while (pairInUse(node, last) && last < MAX_PAIRS) {
        last++;
        addPair(node, last);
    }

    watchAllPairs(node);
    node.setDirtyCanvas(true, true);
}

function scheduleSync(node) {
    if (node._yfgSyncTimer) clearTimeout(node._yfgSyncTimer);
    node._yfgSyncTimer = setTimeout(() => {
        node._yfgSyncTimer = null;
        syncPairs(node);
    }, 120);
}

function initNode(node, where) {
    if (node._yfgDeclaredWidgetCount === undefined) {
        node._yfgDeclaredWidgetCount = (node.widgets || []).length;
    }
    log(`init from ${where}; widgets:`, (node.widgets || []).map(w => w.name).join(", "));
    watchAllPairs(node);
    scheduleSync(node);
}

// ───────────────────────────── registration ─────────────────────────────────

app.registerExtension({
    name: "yfg.civitai_metasave_v2.dynamic_extra_fields",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_NAME) return;
        log("beforeRegisterNodeDef matched", nodeData.name);

        const onCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onCreated ? onCreated.apply(this, arguments) : undefined;
            initNode(this, "onNodeCreated");
            return r;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            const r = onConfigure ? onConfigure.apply(this, arguments) : undefined;

            const saved = info?.widgets_values;
            if (Array.isArray(saved)) {
                const declared = this._yfgDeclaredWidgetCount ?? (this.widgets || []).length;
                const pairs    = Math.floor(Math.max(0, saved.length - declared) / 2);
                log(`onConfigure: ${saved.length} saved values, ${declared} declared -> ${pairs} extra pair(s)`);

                for (let i = 0; i < pairs && STATIC_PAIRS + 1 + i <= MAX_PAIRS; i++) {
                    addPair(this, STATIC_PAIRS + 1 + i);
                }
                if (pairs > 0) {
                    this.widgets.forEach((w, i) => {
                        if (i < saved.length) w.value = saved[i];
                    });
                }
            }
            initNode(this, "onConfigure");
            return r;
        };

        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function () {
            const r = onConnectionsChange ? onConnectionsChange.apply(this, arguments) : undefined;
            scheduleSync(this);
            return r;
        };
    },

    // Fallback path: fires even if the prototype hook above is bypassed
    async nodeCreated(node) {
        if (node?.comfyClass !== NODE_NAME && node?.type !== NODE_NAME) return;
        initNode(node, "nodeCreated");
    },

    async afterConfigureGraph() {
        for (const node of app.graph?._nodes || []) {
            if (node?.comfyClass === NODE_NAME || node?.type === NODE_NAME) {
                scheduleSync(node);
            }
        }
    },
});

log("extension registered");
