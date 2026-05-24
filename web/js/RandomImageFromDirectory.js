/**
 * YFG Random Image From Directory — UI Extension v1.2.0
 *
 * Adds two native buttons to the RandomImageFromDirectory_node:
 *   📁 Browse for Directory  — navigable server-side directory browser modal
 *   🕐 Recent Directories    — MRU list from /yfg/dir_history
 *
 * v1.2.0: Inline output slot value display — shows index, dimensions,
 *         total count and previous index directly next to each output slot.
 *
 * @author  Manny Gonzalez
 * @title   🐯 YFG Comical Nodes
 * @version 1.2.0
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_TYPE = "RandomImageFromDirectory_node";

// Output slot indices that get inline value display.
// Keys match what Python sends as flat ui dict keys.
const DISPLAY_SLOTS = {
    yfg_index_current:  2,
    yfg_width:          4,
    yfg_height:         5,
    yfg_total_count:    7,
    yfg_index_previous: 9,
};

console.log("[YFG] RandomImageFromDirectory JS extension loading…");

// ─────────────────────────── API helpers ─────────────────────────────────────

async function apiGet(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}

async function apiPost(path, body) {
    const r = await fetch(path, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}

// ─────────────────────────── tiny DOM helpers ─────────────────────────────────

function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls)  e.className   = cls;
    if (text) e.textContent = text;
    return e;
}

function btn(label, cls, onclick) {
    const b = el("button", cls, label);
    b.type    = "button";
    b.onclick = onclick;
    return b;
}

// ─────────────────────────── CSS (injected once) ──────────────────────────────

let _stylesInjected = false;
function ensureStyles() {
    if (_stylesInjected) return;
    _stylesInjected = true;
    const css = `
/* ── overlay / modal ──────────────────────────────────────── */
.yfg-overlay {
    position: fixed; inset: 0; z-index: 99999;
    background: rgba(0,0,0,.65);
    display: flex; align-items: center; justify-content: center;
}
.yfg-modal {
    background: #1e1e2e; color: #cdd6f4;
    border: 1px solid #45475a; border-radius: 10px;
    width: min(680px, 93vw); max-height: 82vh;
    display: flex; flex-direction: column;
    font-family: ui-monospace, "Cascadia Code", monospace; font-size: 13px;
    box-shadow: 0 12px 60px rgba(0,0,0,.85);
    overflow: hidden;
}
.yfg-modal-header {
    padding: 11px 16px; background: #181825;
    border-bottom: 1px solid #45475a;
    display: flex; align-items: center; gap: 8px;
}
.yfg-modal-title { font-weight: 700; font-size: 14px; color: #cba6f7; flex: 1; }
.yfg-breadcrumb {
    padding: 7px 16px; background: #11111b;
    border-bottom: 1px solid #313244;
    font-size: 11px; color: #a6adc8;
    word-break: break-all; min-height: 30px;
    display: flex; align-items: center;
}
.yfg-dir-list {
    flex: 1; overflow-y: auto; padding: 4px 0;
    border-bottom: 1px solid #313244;
}
.yfg-dir-item {
    padding: 8px 16px; cursor: pointer;
    display: flex; align-items: center; gap: 9px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    transition: background .1s; user-select: none;
}
.yfg-dir-item:hover        { background: #313244; }
.yfg-dir-item.yfg-up       { color: #89b4fa; font-style: italic; }
.yfg-dir-name              { overflow: hidden; text-overflow: ellipsis; }
.yfg-modal-footer {
    padding: 10px 16px; background: #181825;
    display: flex; gap: 8px; justify-content: flex-end;
    border-top: 1px solid #45475a;
}

/* ── shared button styles ─────────────────────────────────── */
.yfg-btn {
    padding: 6px 14px; border-radius: 6px; border: none;
    cursor: pointer; font-size: 12px; font-weight: 700;
    transition: opacity .15s, filter .15s;
}
.yfg-btn:hover         { opacity: .85; }
.yfg-btn:active        { filter: brightness(.85); }
.yfg-btn-primary       { background: #cba6f7; color: #1e1e2e; }
.yfg-btn-secondary     { background: #45475a; color: #cdd6f4; }
.yfg-btn-danger        { background: #f38ba8; color: #1e1e2e; }
.yfg-btn-sm            { padding: 3px 10px; font-size: 11px; }

/* ── states ───────────────────────────────────────────────── */
.yfg-empty   { padding: 28px; text-align: center; color: #6c7086; white-space: pre-line; }
.yfg-spinner { text-align: center; padding: 22px; color: #89dceb; }
.yfg-err     { padding: 14px 16px; color: #f38ba8; }

/* ── history list (inside modal) ──────────────────────────── */
.yfg-history-item {
    padding: 9px 16px; cursor: pointer;
    display: flex; align-items: center; gap: 9px;
    border-bottom: 1px solid #313244;
    transition: background .1s;
}
.yfg-history-item:hover        { background: #313244; }
.yfg-history-item:last-of-type { border-bottom: none; }
.yfg-history-label {
    flex: 1; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; color: #cdd6f4; font-size: 12px;
}
.yfg-history-del {
    flex-shrink: 0; color: #f38ba8; cursor: pointer;
    font-size: 15px; line-height: 1; padding: 0 3px;
    opacity: .6; transition: opacity .1s;
}
.yfg-history-del:hover { opacity: 1; }
.yfg-history-clear-row {
    padding: 8px 16px; display: flex; justify-content: flex-end;
    border-top: 1px solid #45475a; background: #181825;
}
`;
    const s = document.createElement("style");
    s.textContent = css;
    document.head.appendChild(s);
}

// ─────────────────────────── Directory Browser Modal ─────────────────────────

function openBrowseModal(startPath, onSelect) {
    ensureStyles();
    let activePath = (startPath || "").trim();

    const overlay    = el("div", "yfg-overlay");
    const modal      = el("div", "yfg-modal");
    const header     = el("div", "yfg-modal-header");
    const title      = el("span", "yfg-modal-title", "📁 Browse for Directory");
    const breadcrumb = el("div", "yfg-breadcrumb", activePath || "Loading…");
    const listWrap   = el("div", "yfg-dir-list");
    const footer     = el("div", "yfg-modal-footer");
    const cancelBtn  = btn("Cancel", "yfg-btn yfg-btn-secondary", () => overlay.remove());
    const selectBtn  = btn("✅ Use This Directory", "yfg-btn yfg-btn-primary", () => {
        if (activePath) { onSelect(activePath); overlay.remove(); }
    });
    selectBtn.disabled = !activePath;

    header.append(title);
    footer.append(cancelBtn, selectBtn);
    modal.append(header, breadcrumb, listWrap, footer);
    overlay.append(modal);
    document.body.append(overlay);
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });

    async function navigate(path) {
        listWrap.innerHTML = "";
        listWrap.append(el("div", "yfg-spinner", "⏳ Loading…"));
        try {
            const url  = path
                ? `/yfg/dir_browse?path=${encodeURIComponent(path)}`
                : `/yfg/dir_browse`;
            const data = await apiGet(url);

            activePath             = data.path || path || "";
            breadcrumb.textContent = activePath || "Filesystem Roots";
            selectBtn.disabled     = !activePath;
            listWrap.innerHTML     = "";

            if (data.parent !== null && data.parent !== undefined) {
                const upRow = el("div", "yfg-dir-item yfg-up");
                upRow.innerHTML = `<span>⬆️</span><span class="yfg-dir-name">.. up one level</span>`;
                upRow.title     = data.parent;
                upRow.onclick   = () => navigate(data.parent);
                listWrap.append(upRow);
            }

            if (!data.dirs || data.dirs.length === 0) {
                listWrap.append(el("div", "yfg-empty", "No subdirectories here."));
                return;
            }

            for (const d of data.dirs) {
                const row = el("div", "yfg-dir-item");
                row.title = d.path;
                row.innerHTML = `<span>📁</span><span class="yfg-dir-name">${d.name}</span>`;
                row.onclick   = () => navigate(d.path);
                listWrap.append(row);
            }
        } catch (e) {
            listWrap.innerHTML = "";
            listWrap.append(el("div", "yfg-err", `⚠️ ${e.message}`));
        }
    }

    navigate(activePath || "");
}

// ─────────────────────────── History Modal ───────────────────────────────────

function openHistoryModal(onSelect) {
    ensureStyles();

    const overlay  = el("div", "yfg-overlay");
    const modal    = el("div", "yfg-modal");
    const header   = el("div", "yfg-modal-header");
    const title    = el("span", "yfg-modal-title", "🕐 Recent Directories");
    const listWrap = el("div", "yfg-dir-list");
    const footer   = el("div", "yfg-modal-footer");
    const closeBtn = btn("Close", "yfg-btn yfg-btn-secondary", () => overlay.remove());

    header.append(title);
    footer.append(closeBtn);
    modal.append(header, listWrap, footer);
    overlay.append(modal);
    document.body.append(overlay);
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });

    async function render() {
        listWrap.innerHTML = "";
        listWrap.append(el("div", "yfg-spinner", "⏳ Loading…"));
        try {
            const history = await apiGet("/yfg/dir_history");
            listWrap.innerHTML = "";

            if (!history || history.length === 0) {
                listWrap.append(el("div", "yfg-empty",
                    "No history yet.\n\nDirectories are saved automatically\neach time the node runs."));
                return;
            }

            for (const dir of history) {
                const row   = el("div", "yfg-history-item");
                const label = el("span", "yfg-history-label", dir);
                const del   = el("span", "yfg-history-del", "✕");
                label.title  = dir;
                label.onclick = () => { onSelect(dir); overlay.remove(); };
                del.title    = "Remove from history";
                del.onclick  = async ev => {
                    ev.stopPropagation();
                    await apiPost("/yfg/dir_history/remove", { directory: dir });
                    render();
                };
                row.append(label, del);
                listWrap.append(row);
            }

            const clearRow = el("div", "yfg-history-clear-row");
            const clearBtn = btn("🗑 Clear All History", "yfg-btn yfg-btn-danger yfg-btn-sm",
                async () => {
                    await apiPost("/yfg/dir_history/clear", {});
                    render();
                });
            clearRow.append(clearBtn);
            listWrap.append(clearRow);

        } catch (e) {
            listWrap.innerHTML = "";
            listWrap.append(el("div", "yfg-err", `⚠️ ${e.message}`));
        }
    }

    render();
}

// ─────────────────────────── Output slot value display ───────────────────────

// Update the display-enabled output slots with their current values.
// Uses slot.label (display-only, not reset by ComfyUI) instead of slot.name.
// Wrapped in setTimeout to run after ComfyUI's post-execution node refresh.
function applyOutputValues(node, output) {
    setTimeout(() => {
        for (const [key, slotIdx] of Object.entries(DISPLAY_SLOTS)) {
            const raw = output?.[key];
            if (raw === undefined || raw === null) continue;

            const value = Array.isArray(raw) ? raw[0] : raw;
            if (value === undefined) continue;

            const slot = node.outputs?.[slotIdx];
            if (!slot) continue;

            // origName: prefer stored name, else current label/name minus any prefix
            let origName = node._yfgOrigOutputNames?.[slotIdx];
            if (!origName) {
                const src  = slot.label || slot.name || "";
                const parts = src.split("  ");
                origName = parts.length > 1 ? parts.slice(1).join("  ") : src;
            }

            const displayVal = (key === "yfg_index_previous" && value === -1) ? "-" : String(value);

            // Set label (display override) — ComfyUI doesn't reset this
            slot.label = `${displayVal}  ${origName}`;
        }

        // Force full canvas redraw
        if (app.canvas?.draw) {
            app.canvas.draw(true, true);
        } else {
            node.setDirtyCanvas(true, true);
        }
    }, 100);
}

// ─────────────────────────── ComfyUI Extension ───────────────────────────────

app.registerExtension({
    name: "YFG.RandomImageFromDirectory",

    // ── Listen for execution results and update output slot labels ────────────
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
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_TYPE) return;

        console.log("[YFG] Hooking RandomImageFromDirectory_node…");

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const self   = this;

            // ── Store original output names (once) for value prepending ───────
            self._yfgOrigOutputNames = (self.outputs ?? []).map(o => o.name);

            // ── Browse / Recent buttons ───────────────────────────────────────
            const dirWidget = self.widgets?.find(w => w.name === "image_directory");
            if (!dirWidget) {
                console.warn("[YFG] image_directory widget not found on node.");
                return result;
            }

            function applyPath(selectedPath) {
                dirWidget.value = selectedPath;
                if (typeof dirWidget.callback === "function") {
                    dirWidget.callback(selectedPath);
                }
                app.graph.setDirtyCanvas(true, true);
            }

            self.addWidget(
                "button",
                "📁 Browse for Directory",
                "browse",
                () => openBrowseModal(dirWidget.value || "", applyPath)
            );

            self.addWidget(
                "button",
                "🕐 Recent Directories",
                "recent",
                () => openHistoryModal(applyPath)
            );

            console.log("[YFG] ✅ Browse + Recent buttons added to node.");
            return result;
        };
    },
});
