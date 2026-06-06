/**
 * YFG Random Prompt From File — UI Extension v1.2.0
 *
 * Adds to YFGRandomPromptFromFile_node:
 *   📄 Browse for File    — navigable file picker showing dirs + .txt files
 *   🕐 Recent Files       — MRU list from /yfg/file_history
 *   range auto-populate   — range_start/range_end fill from file on selection
 *   Output slot display   — index_current, index_previous, total_count live values
 *   INDEX auto-sync       — INDEX widget mirrors index_current after every run
 *
 * v1.2.0: Widget shows filename only (full path on hover tooltip).
 *         Recent Files picker shows two-line layout: filename (green) +
 *         directory path (dimmed) for instant disambiguation of long paths.
 * v1.1.0: Simplified inputs, fixed badge fetch abort on file select,
 *         added range_start/range_end auto-populate on file selection.
 *
 * @author  Manny Gonzalez
 * @title   🐯 YFG Comical Nodes
 * @version 1.2.0
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_TYPE = "YFGRandomPromptFromFile_node";

// Output slot indices for live value display
const DISPLAY_SLOTS = {
    yfg_pf_index_current:  3,
    yfg_pf_index_previous: 4,
    yfg_pf_total_count:    5,
    yfg_pf_file_name:      7,   // filename shown on slot, full path on tooltip
    yfg_pf_file_path:      6,   // full path — slot label kept short
};

console.log("[YFG] RandomPromptFromFile JS extension loading…");

// ─────────────────────────── API helpers ─────────────────────────────────────

async function apiGet(path, signal) {
    const r = await fetch(path, signal ? { signal } : undefined);
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
    box-shadow: 0 12px 60px rgba(0,0,0,.85); overflow: hidden;
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
.yfg-dir-list { flex: 1; overflow-y: auto; padding: 4px 0; border-bottom: 1px solid #313244; }
.yfg-dir-item {
    padding: 8px 16px; cursor: pointer;
    display: flex; align-items: center; gap: 9px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    transition: background .1s; user-select: none;
}
.yfg-dir-item:hover     { background: #313244; }
.yfg-dir-item.yfg-up    { color: #89b4fa; font-style: italic; }
.yfg-dir-item.yfg-file  { color: #a6e3a1; }
.yfg-dir-item.yfg-file:hover { background: #1e3a2f; }
.yfg-dir-item.yfg-selected { background: #2a3f2a; font-weight: bold; }
.yfg-dir-name { overflow: hidden; text-overflow: ellipsis; flex: 1; }
.yfg-modal-footer {
    padding: 10px 16px; background: #181825;
    display: flex; gap: 8px; justify-content: flex-end;
    border-top: 1px solid #45475a;
}
.yfg-btn {
    padding: 6px 14px; border-radius: 6px; border: none;
    cursor: pointer; font-size: 12px; font-weight: 700;
    transition: opacity .15s, filter .15s;
}
.yfg-btn:hover  { opacity: .85; }
.yfg-btn:active { filter: brightness(.85); }
.yfg-btn-primary    { background: #cba6f7; color: #1e1e2e; }
.yfg-btn-secondary  { background: #45475a; color: #cdd6f4; }
.yfg-btn-danger     { background: #f38ba8; color: #1e1e2e; }
.yfg-btn-sm         { padding: 3px 10px; font-size: 11px; }
.yfg-empty   { padding: 28px; text-align: center; color: #6c7086; white-space: pre-line; }
.yfg-spinner { text-align: center; padding: 22px; color: #89dceb; }
.yfg-err     { padding: 14px 16px; color: #f38ba8; }
.yfg-history-item {
    padding: 9px 16px; cursor: pointer;
    display: flex; align-items: center; gap: 9px;
    border-bottom: 1px solid #313244; transition: background .1s;
}
.yfg-history-item:hover        { background: #313244; }
.yfg-history-item:last-of-type { border-bottom: none; }
.yfg-history-info {
    flex: 1; overflow: hidden; display: flex; flex-direction: column; gap: 2px;
}
.yfg-history-filename {
    color: #a6e3a1; font-size: 13px; font-weight: 600;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.yfg-history-dirpath {
    color: #6c7086; font-size: 10px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.yfg-history-del {
    flex-shrink: 0; color: #f38ba8; cursor: pointer;
    font-size: 15px; line-height: 1; padding: 0 3px; opacity: .6;
}
.yfg-history-del:hover { opacity: 1; }
.yfg-history-clear-row {
    padding: 8px 16px; display: flex; justify-content: flex-end;
    border-top: 1px solid #45475a; background: #181825;
}
.yfg-file-count {
    flex-shrink: 0; background: #313244; color: #a6adc8;
    font-size: 10px; padding: 1px 7px; border-radius: 8px; margin-left: 4px;
}
`;
    const s = document.createElement("style");
    s.textContent = css;
    document.head.appendChild(s);
}

// ─────────────────────────── range auto-populate ──────────────────────────────
// Called whenever a file path is applied to the node — fetches prompt count
// and writes range_start=0, range_end=total-1 into the corresponding widgets.

async function autoPopulateRange(node, filepath) {
    if (!filepath || !filepath.trim()) return;
    try {
        const data = await apiGet(`/yfg/prompt_count?path=${encodeURIComponent(filepath)}`);
        if (!data.count || data.count < 1) return;

        const startW = node.widgets?.find(w => w.name === "range_start");
        const endW   = node.widgets?.find(w => w.name === "range_end");
        if (startW) startW.value = 0;
        if (endW)   endW.value   = data.count - 1;
        app.graph.setDirtyCanvas(true, true);
        console.log(`[YFG] range auto-populated: 0 → ${data.count - 1}`);
    } catch (e) {
        console.warn("[YFG] Could not fetch prompt count for range populate:", e);
    }
}

// ─────────────────────────── File Browser Modal ───────────────────────────────

function openFileBrowseModal(startPath, onSelect) {
    ensureStyles();

    // If startPath is a file, open in its parent directory
    let currentDir = (startPath || "").trim();
    if (currentDir && /\.(txt)$/i.test(currentDir)) {
        const sep = currentDir.includes("/") ? "/" : "\\";
        currentDir = currentDir.substring(0, currentDir.lastIndexOf(sep));
    }

    let selectedFile = "";

    // AbortController pool — cancels all in-flight badge fetches when modal closes
    const abortCtrl = new AbortController();

    const overlay    = el("div", "yfg-overlay");
    const modal      = el("div", "yfg-modal");
    const header     = el("div", "yfg-modal-header");
    const title      = el("span", "yfg-modal-title", "📄 Browse for Prompt File");
    const breadcrumb = el("div", "yfg-breadcrumb", currentDir || "Loading…");
    const listWrap   = el("div", "yfg-dir-list");
    const footer     = el("div", "yfg-modal-footer");
    const cancelBtn  = btn("Cancel", "yfg-btn yfg-btn-secondary", () => {
        abortCtrl.abort();
        overlay.remove();
    });
    const selectBtn  = btn("✅ Use This File", "yfg-btn yfg-btn-primary", () => {
        if (selectedFile) {
            abortCtrl.abort();
            onSelect(selectedFile);
            overlay.remove();
        }
    });
    selectBtn.disabled = true;

    header.append(title);
    footer.append(cancelBtn, selectBtn);
    modal.append(header, breadcrumb, listWrap, footer);
    overlay.append(modal);
    document.body.append(overlay);
    overlay.addEventListener("click", e => {
        if (e.target === overlay) { abortCtrl.abort(); overlay.remove(); }
    });

    async function navigate(path) {
        listWrap.innerHTML = "";
        listWrap.append(el("div", "yfg-spinner", "⏳ Loading…"));

        // Badge fetch queue — max 2 concurrent, stops immediately on abort
        const badgeQueue = [];
        let   badgeActive = 0;
        const BADGE_CONCURRENCY = 2;

        async function drainBadgeQueue() {
            while (badgeQueue.length > 0 && badgeActive < BADGE_CONCURRENCY) {
                if (abortCtrl.signal.aborted) return;
                const { path: p, row } = badgeQueue.shift();
                badgeActive++;
                apiGet(`/yfg/prompt_count?path=${encodeURIComponent(p)}`, abortCtrl.signal)
                    .then(d => {
                        if (d.count > 0 && listWrap.contains(row)) {
                            const badge = el("span", "yfg-file-count", `${d.count} prompts`);
                            row.append(badge);
                        }
                    })
                    .catch(() => {})
                    .finally(() => {
                        badgeActive--;
                        drainBadgeQueue();
                    });
            }
        }
        try {
            const url  = path
                ? `/yfg/file_browse?path=${encodeURIComponent(path)}`
                : `/yfg/file_browse`;
            const data = await apiGet(url);

            breadcrumb.textContent = data.path || path || "Filesystem Roots";
            listWrap.innerHTML     = "";

            // Up row
            if (data.parent !== null && data.parent !== undefined) {
                const upRow = el("div", "yfg-dir-item yfg-up");
                upRow.innerHTML = `<span>⬆️</span><span class="yfg-dir-name">.. up one level</span>`;
                upRow.title   = data.parent;
                upRow.onclick = () => navigate(data.parent);
                listWrap.append(upRow);
            }

            if (!data.entries || data.entries.length === 0) {
                listWrap.append(el("div", "yfg-empty", "No subdirectories or .txt files here."));
                return;
            }

            for (const entry of data.entries) {
                const row  = el("div", `yfg-dir-item${entry.type === "file" ? " yfg-file" : ""}`);
                const icon = entry.type === "file" ? "📄" : "📁";
                const name = el("span", "yfg-dir-name", entry.name);
                row.title  = entry.path;
                row.append(el("span", "", icon), name);

                if (entry.type === "file") {
                    // Queue badge fetch — runs max 2 at a time, abortable
                    badgeQueue.push({ path: entry.path, row });

                    row.onclick = () => {
                        // Abort ALL pending badge fetches immediately on file click
                        abortCtrl.abort();
                        // Deselect any previous selection
                        listWrap.querySelectorAll(".yfg-selected")
                            .forEach(r => r.classList.remove("yfg-selected"));
                        row.classList.add("yfg-selected");
                        selectedFile           = entry.path;
                        breadcrumb.textContent = entry.path;
                        selectBtn.disabled     = false;
                    };

                    // Double-click to immediately confirm
                    row.ondblclick = () => {
                        abortCtrl.abort();
                        onSelect(entry.path);
                        overlay.remove();
                    };
                } else {
                    row.onclick = () => navigate(entry.path);
                }

                listWrap.append(row);
            }

            // Start draining badge queue now that all rows are in the DOM
            drainBadgeQueue();

        } catch (e) {
            if (e.name === "AbortError") return;
            listWrap.innerHTML = "";
            listWrap.append(el("div", "yfg-err", `⚠️ ${e.message}`));
        }
    }

    navigate(currentDir || "");
}

// ─────────────────────────── Recent Files Modal ───────────────────────────────

function openRecentFilesModal(onSelect) {
    ensureStyles();

    const overlay  = el("div", "yfg-overlay");
    const modal    = el("div", "yfg-modal");
    const header   = el("div", "yfg-modal-header");
    const title    = el("span", "yfg-modal-title", "🕐 Recent Prompt Files");
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
            const history = await apiGet("/yfg/file_history");
            listWrap.innerHTML = "";

            if (!history || history.length === 0) {
                listWrap.append(el("div", "yfg-empty",
                    "No history yet.\n\nFiles are saved automatically\neach time the node runs."));
                return;
            }

            for (const filepath of history) {
                // Split into filename (green, bold) + directory path (dim)
                const sep      = filepath.includes("\\") ? "\\" : "/";
                const lastSep  = Math.max(filepath.lastIndexOf("\\"), filepath.lastIndexOf("/"));
                const filename = lastSep >= 0 ? filepath.slice(lastSep + 1) : filepath;
                const dirpath  = lastSep >= 0 ? filepath.slice(0, lastSep)  : "";

                const row      = el("div", "yfg-history-item");
                const info     = el("div", "yfg-history-info");
                const nameSpan = el("span", "yfg-history-filename", filename);
                const dirSpan  = el("span", "yfg-history-dirpath",  dirpath);
                const del      = el("span", "yfg-history-del", "✕");

                // Full path on tooltip for both spans
                nameSpan.title = filepath;
                dirSpan.title  = filepath;
                info.append(nameSpan, dirSpan);

                info.onclick = () => { onSelect(filepath); overlay.remove(); };
                del.title    = "Remove from history";
                del.onclick  = async ev => {
                    ev.stopPropagation();
                    await apiPost("/yfg/file_history/remove", { filepath });
                    render();
                };
                row.append(info, del);
                listWrap.append(row);
            }

            const clearRow = el("div", "yfg-history-clear-row");
            clearRow.append(btn("🗑 Clear All History", "yfg-btn yfg-btn-danger yfg-btn-sm",
                async () => { await apiPost("/yfg/file_history/clear", {}); render(); }
            ));
            listWrap.append(clearRow);
        } catch (e) {
            listWrap.innerHTML = "";
            listWrap.append(el("div", "yfg-err", `⚠️ ${e.message}`));
        }
    }

    render();
}

// ─────────────────────────── Output slot value display ───────────────────────

// Max chars to show for filename on the slot label before truncating
const MAX_FNAME_DISPLAY = 28;

function applyOutputValues(node, output) {
    // Grab the full path early so file_name slot can use it as tooltip
    const filePathRaw  = output?.["yfg_pf_file_path"];
    const fullFilePath = filePathRaw
        ? (Array.isArray(filePathRaw) ? filePathRaw[0] : filePathRaw)
        : null;

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

            if (key === "yfg_pf_file_name") {
                // Show truncated filename on the slot label (same style as numbers)
                // Full path goes on the slot tooltip for hover reference
                const fname = String(value);
                const displayFname = fname.length > MAX_FNAME_DISPLAY
                    ? fname.slice(0, MAX_FNAME_DISPLAY - 1) + "…"
                    : fname;
                slot.label   = `${displayFname}  ${origName}`;
                slot.tooltip = fullFilePath || fname;

            } else if (key === "yfg_pf_file_path") {
                // file_path slot: keep label as just the slot name,
                // tooltip shows the full path
                slot.label   = origName;
                slot.tooltip = String(value);

            } else {
                const displayVal = (key === "yfg_pf_index_previous" && value === -1)
                    ? "-" : String(value);
                slot.label = `${displayVal}  ${origName}`;
            }

            // Sync INDEX widget from index_current
            if (key === "yfg_pf_index_current") {
                const idxWidget = node.widgets?.find(w => w.name === "index");
                if (idxWidget) idxWidget.value = value;
            }
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
    name: "YFG.RandomPromptFromFile",

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

        console.log("[YFG] RandomPromptFromFile executed event listener registered.");
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_TYPE) return;

        console.log("[YFG] Hooking YFGRandomPromptFromFile_node…");

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const self   = this;

            self._yfgOrigOutputNames = (self.outputs ?? []).map(o => o.name);

            const fileWidget = self.widgets?.find(w => w.name === "prompt_file");
            if (!fileWidget) {
                console.warn("[YFG] prompt_file widget not found.");
                return result;
            }

            // The full path is stored in fileWidget.value and sent to Python.
            // The filename is displayed on the file_name output slot (slot 7)
            // after each run, matching the style of the numeric output slots.

            // Wrap the widget callback so range auto-populates whenever
            // the file path changes (Browse, Recent, or manual typing)
            const _origCallback = fileWidget.callback;
            fileWidget.callback = function (value) {
                if (_origCallback) _origCallback.call(this, value);
                if (value && value.trim()) {
                    autoPopulateRange(self, value);
                }
            };

            function applyFile(selectedPath) {
                fileWidget.value   = selectedPath;
                // Show full path on hover — updates both the ComfyUI tooltip
                // property and the DOM element title if accessible
                fileWidget.tooltip = selectedPath;
                if (fileWidget.element) fileWidget.element.title = selectedPath;
                // Trigger callback → auto-populates range
                if (typeof fileWidget.callback === "function") {
                    fileWidget.callback(selectedPath);
                }
                app.graph.setDirtyCanvas(true, true);
            }

            self.addWidget(
                "button",
                "📄 Browse for File",
                "browse_file",
                () => openFileBrowseModal(fileWidget.value || "", applyFile)
            );

            self.addWidget(
                "button",
                "🕐 Recent Files",
                "recent_files",
                () => openRecentFilesModal(applyFile)
            );

            console.log("[YFG] ✅ Browse + Recent buttons added to RandomPromptFromFile node.");
            return result;
        };
    },
});
