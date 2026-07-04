/**
 * 🐯 YFG Live Preview Panel
 *
 * A floating, draggable panel that mirrors the KSampler live preview so you
 * can watch generation progress from anywhere in the workflow — no more
 * panning back to the sampler node. Includes a progress bar, the name of the
 * node currently executing, and a Cancel button wired to ComfyUI's
 * /interrupt endpoint so you can kill a bad run early.
 *
 * How it works (no Python needed):
 *   ComfyUI's server already broadcasts "progress" (step counts) and
 *   "b_preview" (preview image blobs) websocket events to every client.
 *   The KSampler node itself has no special preview code — the frontend just
 *   listens for these events. This extension listens for the same events and
 *   renders them into its own floating panel.
 *
 * Behavior:
 *   - Panel appears automatically when a generation starts.
 *   - Drag it by the header; position and size are remembered (localStorage).
 *   - Resize from the bottom-right corner grip.
 *   - "—" collapses to just the header bar; "✕" hides it until the next run.
 *   - Alt+Shift+L toggles the panel at any time (L for Live; Alt+Shift+P
 *     collides with Edge's tab-grouping shortcut).
 *   - Settings → YFG → "Enable Live Preview panel" master on/off switch.
 *   - 🛑 Cancel interrupts the current generation.
 *
 * v1.1.1: Hotkey moved to Alt+Shift+L (Alt+Shift+P is taken by MS Edge).
 * v1.1.0: Added keyboard toggle and a Settings master switch.
 * v1.0.0: Initial release.
 *
 * @author  Manny Gonzalez
 * @title   🐯 YFG Comical Nodes
 * @version 1.1.1
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const LS_KEY = "yfg.livePreview.state";   // localStorage key for position/size

// ────────────────────────────── tiny DOM helpers ─────────────────────────────

function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls)  e.className   = cls;
    if (text) e.textContent = text;
    return e;
}

// ─────────────────────────────────── styles ──────────────────────────────────

function ensureStyles() {
    if (document.getElementById("yfg-lpp-styles")) return;
    const s = document.createElement("style");
    s.id = "yfg-lpp-styles";
    s.textContent = `
    .yfg-lpp {
        position: fixed;
        z-index: 9000;
        display: flex;
        flex-direction: column;
        min-width: 180px;
        min-height: 42px;
        width: 260px;
        background: var(--comfy-menu-bg, #202020);
        border: 1px solid var(--border-color, #4e4e4e);
        border-radius: 8px;
        box-shadow: 0 4px 18px rgba(0,0,0,.55);
        font-family: sans-serif;
        font-size: 12px;
        color: var(--fg-color, #ddd);
        overflow: hidden;
        resize: both;             /* native resize grip, bottom-right */
    }
    .yfg-lpp.yfg-collapsed { resize: none; height: auto !important; }
    .yfg-lpp.yfg-collapsed .yfg-lpp-body { display: none; }

    .yfg-lpp-header {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 5px 8px;
        background: var(--comfy-input-bg, #303030);
        cursor: grab;
        user-select: none;
        flex: 0 0 auto;
    }
    .yfg-lpp-header:active { cursor: grabbing; }
    .yfg-lpp-title  { flex: 1 1 auto; font-weight: 600; white-space: nowrap;
                      overflow: hidden; text-overflow: ellipsis; }
    .yfg-lpp-hbtn   { cursor: pointer; opacity: .7; padding: 0 3px; }
    .yfg-lpp-hbtn:hover { opacity: 1; }

    .yfg-lpp-body   { display: flex; flex-direction: column; flex: 1 1 auto;
                      min-height: 0; padding: 6px 8px 8px; gap: 6px; }

    .yfg-lpp-imgwrap {
        flex: 1 1 auto;
        min-height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #111;
        border-radius: 4px;
        overflow: hidden;
    }
    .yfg-lpp-img    { max-width: 100%; max-height: 100%; object-fit: contain;
                      display: none; }
    .yfg-lpp-idle   { color: #666; font-style: italic; }

    .yfg-lpp-node   { white-space: nowrap; overflow: hidden;
                      text-overflow: ellipsis; color: #9c9; min-height: 14px; }

    .yfg-lpp-barwrap { height: 8px; background: #111; border-radius: 4px;
                       overflow: hidden; flex: 0 0 auto; }
    .yfg-lpp-bar    { height: 100%; width: 0%;
                      background: var(--p-primary-color, #4a90d9);
                      transition: width .15s linear; }

    .yfg-lpp-footer { display: flex; align-items: center; gap: 8px;
                      flex: 0 0 auto; }
    .yfg-lpp-steps  { flex: 1 1 auto; color: #aaa; font-variant-numeric: tabular-nums; }
    .yfg-lpp-cancel {
        background: #5a2323; color: #f0caca;
        border: 1px solid #7a3030; border-radius: 4px;
        padding: 3px 10px; cursor: pointer; font-size: 12px;
    }
    .yfg-lpp-cancel:hover:not(:disabled) { background: #7a2c2c; }
    .yfg-lpp-cancel:disabled { opacity: .4; cursor: default; }
    `;
    document.head.appendChild(s);
}

// ────────────────────────────── the panel itself ─────────────────────────────

class LivePreviewPanel {
    constructor() {
        ensureStyles();

        this.root    = el("div", "yfg-lpp");
        this.header  = el("div", "yfg-lpp-header");
        this.title   = el("span", "yfg-lpp-title", "🐯 Live Preview");
        this.minBtn  = el("span", "yfg-lpp-hbtn", "—");
        this.closeBtn= el("span", "yfg-lpp-hbtn", "✕");
        this.body    = el("div", "yfg-lpp-body");
        this.imgWrap = el("div", "yfg-lpp-imgwrap");
        this.img     = el("img", "yfg-lpp-img");
        this.idleMsg = el("span", "yfg-lpp-idle", "waiting for generation…");
        this.nodeLbl = el("div", "yfg-lpp-node", "");
        this.barWrap = el("div", "yfg-lpp-barwrap");
        this.bar     = el("div", "yfg-lpp-bar");
        this.footer  = el("div", "yfg-lpp-footer");
        this.steps   = el("span", "yfg-lpp-steps", "idle");
        this.cancel  = el("button", "yfg-lpp-cancel", "🛑 Cancel");

        this.minBtn.title   = "Collapse / expand";
        this.closeBtn.title = "Hide (reappears on next run)";
        this.cancel.title   = "Interrupt the current generation";
        this.cancel.disabled = true;

        this.imgWrap.append(this.img, this.idleMsg);
        this.barWrap.append(this.bar);
        this.footer.append(this.steps, this.cancel);
        this.header.append(this.title, this.minBtn, this.closeBtn);
        this.body.append(this.imgWrap, this.nodeLbl, this.barWrap, this.footer);
        this.root.append(this.header, this.body);
        document.body.append(this.root);

        this.blobUrl = null;          // current preview object-URL (revoked on replace)
        this.running = false;
        this.enabled = true;          // master switch, mirrors the Settings entry

        this.restoreState();
        this.wireDragging();
        this.wireButtons();
        this.wireApiEvents();
        this.wireKeyboard();
        this.wireSettings();
    }

    // ── position/size persistence ────────────────────────────────────────────

    restoreState() {
        let st = {};
        try { st = JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch (e) {}
        // Default: bottom-left, clear of the minimap which lives bottom-right.
        const x = st.x ?? 16;
        const y = st.y ?? (window.innerHeight - 340);
        this.root.style.left = `${Math.max(0, Math.min(x, window.innerWidth  - 60))}px`;
        this.root.style.top  = `${Math.max(0, Math.min(y, window.innerHeight - 42))}px`;
        if (st.w) this.root.style.width  = `${st.w}px`;
        if (st.h) this.root.style.height = `${st.h}px`;
        if (st.collapsed) this.root.classList.add("yfg-collapsed");
        if (st.hidden)    this.root.style.display = "none";
    }

    saveState() {
        const r = this.root.getBoundingClientRect();
        const st = {
            x: r.left, y: r.top, w: r.width, h: r.height,
            collapsed: this.root.classList.contains("yfg-collapsed"),
            hidden:    this.root.style.display === "none",
        };
        try { localStorage.setItem(LS_KEY, JSON.stringify(st)); } catch (e) {}
    }

    // ── drag to move ─────────────────────────────────────────────────────────

    wireDragging() {
        let dragOffX = 0, dragOffY = 0, dragging = false;

        this.header.addEventListener("pointerdown", ev => {
            // Don't start a drag from the collapse/close buttons
            if (ev.target === this.minBtn || ev.target === this.closeBtn) return;
            dragging = true;
            const r  = this.root.getBoundingClientRect();
            dragOffX = ev.clientX - r.left;
            dragOffY = ev.clientY - r.top;
            this.header.setPointerCapture(ev.pointerId);
        });
        this.header.addEventListener("pointermove", ev => {
            if (!dragging) return;
            const x = Math.max(0, Math.min(ev.clientX - dragOffX, window.innerWidth  - 60));
            const y = Math.max(0, Math.min(ev.clientY - dragOffY, window.innerHeight - 30));
            this.root.style.left = `${x}px`;
            this.root.style.top  = `${y}px`;
        });
        this.header.addEventListener("pointerup", ev => {
            if (!dragging) return;
            dragging = false;
            this.header.releasePointerCapture(ev.pointerId);
            this.saveState();
        });

        // Persist size after a native-grip resize (fires on mouseup anywhere)
        this.root.addEventListener("mouseup", () => this.saveState());
    }

    // ── header buttons + cancel ──────────────────────────────────────────────

    wireButtons() {
        this.minBtn.onclick = () => {
            this.root.classList.toggle("yfg-collapsed");
            this.saveState();
        };
        this.closeBtn.onclick = () => {
            this.root.style.display = "none";
            this.saveState();
        };
        this.cancel.onclick = async () => {
            this.cancel.disabled = true;
            try {
                // api.interrupt() exists in current frontends; fall back to raw POST.
                if (typeof api.interrupt === "function") await api.interrupt();
                else await api.fetchApi("/interrupt", { method: "POST" });
            } catch (e) {
                console.warn("[YFG LivePreview] interrupt failed:", e);
            }
        };
    }

    // ── websocket events ─────────────────────────────────────────────────────

    wireApiEvents() {
        // A run has started → show the panel (even if previously closed).
        api.addEventListener("execution_start", () => {
            this.running = true;
            this.cancel.disabled = false;
            this.steps.textContent = "starting…";
            this.bar.style.width = "0%";
            if (this.enabled) {       // master switch off = stay hidden
                this.show();
                this.saveState();
            }
        });

        // Step progress for the currently executing node.
        api.addEventListener("progress", ev => {
            const d = ev.detail || {};
            if (typeof d.value !== "number" || typeof d.max !== "number" || !d.max) return;
            const pct = Math.round((d.value / d.max) * 100);
            this.bar.style.width = `${pct}%`;
            this.steps.textContent = `step ${d.value} / ${d.max}  (${pct}%)`;
        });

        // Preview image blob for the currently executing sampler.
        api.addEventListener("b_preview", ev => {
            const blob = ev.detail;
            if (!(blob instanceof Blob)) return;
            const url = URL.createObjectURL(blob);
            if (this.blobUrl) URL.revokeObjectURL(this.blobUrl);
            this.blobUrl = url;
            this.img.src = url;
            this.img.style.display  = "block";
            this.idleMsg.style.display = "none";
        });

        // Which node is currently executing → show its title.
        api.addEventListener("executing", ev => {
            // detail is a node id string in older frontends,
            // or an object like {node, display_node, prompt_id} in newer ones.
            let nodeId = ev.detail;
            if (nodeId && typeof nodeId === "object") {
                nodeId = nodeId.display_node ?? nodeId.node;
            }
            if (nodeId === null || nodeId === undefined) {
                this.nodeLbl.textContent = "";
                return;
            }
            const node = app.graph?.getNodeById?.(Number(nodeId));
            this.nodeLbl.textContent = node
                ? `▶ ${node.title || node.type} (#${nodeId})`
                : `▶ node #${nodeId}`;
        });

        // Terminal states.
        const done = label => () => {
            this.running = false;
            this.cancel.disabled = true;
            this.steps.textContent = label;
            this.nodeLbl.textContent = "";
            if (label === "✅ done") this.bar.style.width = "100%";
        };
        api.addEventListener("execution_success",     done("✅ done"));
        api.addEventListener("execution_error",       done("⚠️ error"));
        api.addEventListener("execution_interrupted", done("🛑 interrupted"));
    }

    show() { this.root.style.display = "flex"; }
    hide() { this.root.style.display = "none";  }

    toggle() {
        const hidden = this.root.style.display === "none";
        if (hidden) this.show(); else this.hide();
        this.saveState();
    }

    // ── Alt+Shift+L toggles the panel ("L" for Live preview) ─────────────────

    wireKeyboard() {
        document.addEventListener("keydown", ev => {
            if (!ev.altKey || !ev.shiftKey || ev.code !== "KeyL") return;
            // Ignore when typing in a text field / prompt box
            const t = ev.target;
            if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
            ev.preventDefault();
            this.toggle();
        });
    }

    // ── Settings gear-menu entry: master on/off switch ───────────────────────

    wireSettings() {
        try {
            app.ui.settings.addSetting({
                id: "YFG.LivePreview.Enabled",
                name: "🐯 Enable Live Preview panel",
                type: "boolean",
                defaultValue: true,
                tooltip: "Floating panel that mirrors the KSampler live preview. "
                       + "Alt+Shift+L toggles it while enabled.",
                onChange: (value) => {
                    this.enabled = !!value;
                    if (!this.enabled) {
                        this.hide();          // switch off → hide immediately
                    } else if (this.running) {
                        this.show();          // switch on mid-run → show right away
                    }
                },
            });
        } catch (e) {
            // Settings API shape varies across frontend versions; the panel
            // still works fully via Alt+Shift+P if registration fails.
            console.warn("[YFG LivePreview] settings registration failed:", e);
        }
    }
}

// ────────────────────────────── register with ComfyUI ────────────────────────

app.registerExtension({
    name: "YFG.LivePreviewPanel",
    setup() {
        new LivePreviewPanel();
    },
});
