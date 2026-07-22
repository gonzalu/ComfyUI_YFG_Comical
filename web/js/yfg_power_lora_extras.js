/**
 * File: yfg_power_lora_extras.js
 * Author: Manny Gonzalez (gonzalu)
 * Title: YFG Power Lora Loader Extras
 * Nickname: 🐯 YFG PLL Extras
 * Description:
 *   Pure frontend patch for rgthree's "Power Lora Loader (rgthree)" node.
 *   Adds a "🐯 YFG" section to that node's own right-click menu:
 *     - Sort Loras (by name, strength, or enabled-first)
 *     - Nudge All Strengths (bulk +/- in sync)
 *     - Randomize (strengths within a range, or on/off by chance)
 *     - Reorder Panel (drag-and-drop reordering)
 *
 *   No new node type, no Python file required. This works by reaching
 *   into the target node's own `.widgets` array (the same array rgthree's
 *   built-in "Move Up/Down" right-click options on individual lora rows
 *   already manipulate) and re-splicing it.
 *
 *   Install: drop this file anywhere under ComfyUI/web/extensions/, e.g.
 *   ComfyUI/web/extensions/yfg/yfg_power_lora_extras.js
 *   Restart the ComfyUI server once (new files in web/extensions are
 *   picked up at server start), then hard-refresh the browser. After
 *   that, editing this same file only needs a hard refresh.
 */

import { app } from "/scripts/app.js";

const PLL_NAME = "Power Lora Loader (rgthree)";
const LORA_PREFIX = "lora_";

function getLoraWidgets(node) {
  return (node.widgets || []).filter((w) => w.name && w.name.startsWith(LORA_PREFIX));
}

function getLoraIndexRange(node) {
  const widgets = node.widgets || [];
  let start = -1;
  let end = -1;
  widgets.forEach((w, i) => {
    if (w.name && w.name.startsWith(LORA_PREFIX)) {
      if (start === -1) start = i;
      end = i;
    }
  });
  return { start, end };
}

function sortLoras(node, mode) {
  const { start, end } = getLoraIndexRange(node);
  if (start === -1) return;
  const slice = node.widgets.slice(start, end + 1);

  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
  const sorters = {
    "Name (A-Z)": (a, b) => collator.compare(a.value?.lora || "", b.value?.lora || ""),
    "Name (Z-A)": (a, b) => collator.compare(b.value?.lora || "", a.value?.lora || ""),
    "Strength (High-Low)": (a, b) => (b.value?.strength ?? 0) - (a.value?.strength ?? 0),
    "Strength (Low-High)": (a, b) => (a.value?.strength ?? 0) - (b.value?.strength ?? 0),
    "Enabled First": (a, b) => (b.value?.on ? 1 : 0) - (a.value?.on ? 1 : 0),
  };
  slice.sort(sorters[mode] || sorters["Name (A-Z)"]);
  node.widgets.splice(start, slice.length, ...slice);
  node.setDirtyCanvas(true, true);
}

function nudgeAll(node, delta) {
  for (const w of getLoraWidgets(node)) {
    if (w.value.strength != null) {
      w.value.strength = Math.round((w.value.strength + delta) * 100) / 100;
    }
    if (w.value.strengthTwo != null) {
      w.value.strengthTwo = Math.round((w.value.strengthTwo + delta) * 100) / 100;
    }
  }
  node.setDirtyCanvas(true, true);
}

function randomizeStrengths(node, min, max) {
  for (const w of getLoraWidgets(node)) {
    const val = Math.round((min + Math.random() * (max - min)) * 100) / 100;
    w.value.strength = val;
    if (w.value.strengthTwo != null) w.value.strengthTwo = val;
  }
  node.setDirtyCanvas(true, true);
}

function randomizeEnabled(node, chance) {
  for (const w of getLoraWidgets(node)) {
    w.value.on = Math.random() < chance;
  }
  node.setDirtyCanvas(true, true);
}

function resetAllStrengths(node) {
  for (const w of getLoraWidgets(node)) {
    w.value.strength = 1;
    if (w.value.strengthTwo != null) w.value.strengthTwo = 1;
  }
  node.setDirtyCanvas(true, true);
}

// Track the last right-click position so custom dialogs can appear near
// the node/menu instead of wherever the browser's native prompt() would
// land (top-center, unmovable).
let lastContextMenuPos = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
document.addEventListener(
  "contextmenu",
  (e) => {
    lastContextMenuPos = { x: e.clientX, y: e.clientY };
  },
  true,
);

function yfgPromptDialog(title, defaultValue, onSubmit) {
  const overlay = document.createElement("div");
  overlay.style.cssText = "position:fixed;inset:0;z-index:10001;";

  const boxLeft = Math.min(lastContextMenuPos.x, window.innerWidth - 260);
  const boxTop = Math.min(lastContextMenuPos.y, window.innerHeight - 140);
  const box = document.createElement("div");
  box.style.cssText = `position:fixed;left:${boxLeft}px;top:${boxTop}px;background:#222;color:#eee;padding:12px 14px;border-radius:8px;min-width:220px;box-shadow:0 4px 16px rgba(0,0,0,0.5);font-family:sans-serif;z-index:10002;`;
  box.innerHTML = `<div style="margin-bottom:8px;font-size:13px;">${title}</div>`;

  const input = document.createElement("input");
  input.type = "text";
  input.value = defaultValue;
  input.style.cssText =
    "width:100%;box-sizing:border-box;padding:4px 6px;margin-bottom:8px;background:#333;color:#eee;border:1px solid #555;border-radius:4px;";
  box.appendChild(input);

  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:6px;justify-content:flex-end;";
  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.style.cssText =
    "padding:4px 10px;background:#444;color:#eee;border:none;border-radius:4px;cursor:pointer;";
  const okBtn = document.createElement("button");
  okBtn.textContent = "OK";
  okBtn.style.cssText =
    "padding:4px 10px;background:#4a90d9;color:#fff;border:none;border-radius:4px;cursor:pointer;";
  btnRow.appendChild(cancelBtn);
  btnRow.appendChild(okBtn);
  box.appendChild(btnRow);

  overlay.appendChild(box);
  document.body.appendChild(overlay);
  input.focus();
  input.select();

  const close = () => {
    if (document.body.contains(overlay)) document.body.removeChild(overlay);
  };
  cancelBtn.onclick = close;
  okBtn.onclick = () => {
    onSubmit(input.value);
    close();
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      onSubmit(input.value);
      close();
    }
    if (e.key === "Escape") close();
  });
  box.addEventListener("click", (e) => e.stopPropagation());
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
}

function openReorderPanel(node) {
  const loraWidgets = getLoraWidgets(node);
  if (!loraWidgets.length) return;

  const overlay = document.createElement("div");
  overlay.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:10000;display:flex;align-items:center;justify-content:center;";

  const panel = document.createElement("div");
  panel.style.cssText =
    "background:#222;color:#eee;padding:16px;border-radius:8px;min-width:320px;max-height:70vh;overflow-y:auto;font-family:sans-serif;";
  panel.innerHTML =
    '<h3 style="margin-top:0;">🐯 Reorder Loras — drag rows</h3><ul id="yfg-pll-list" style="list-style:none;padding:0;margin:0;"></ul>';

  const list = panel.querySelector("#yfg-pll-list");
  loraWidgets.forEach((w, i) => {
    const li = document.createElement("li");
    li.draggable = true;
    li.dataset.index = String(i);
    li.textContent = `${w.value?.on ? "🟢" : "⚫"} ${w.value?.lora || "None"} (${w.value?.strength ?? 1})`;
    li.style.cssText =
      "padding:6px 8px;margin:4px 0;background:#333;border-radius:4px;cursor:grab;";
    list.appendChild(li);
  });

  let dragEl = null;
  list.addEventListener("dragstart", (e) => {
    dragEl = e.target;
    e.dataTransfer.effectAllowed = "move";
  });
  list.addEventListener("dragover", (e) => {
    e.preventDefault();
    const after = [...list.children].find((child) => {
      const rect = child.getBoundingClientRect();
      return e.clientY < rect.top + rect.height / 2;
    });
    if (!after) list.appendChild(dragEl);
    else list.insertBefore(dragEl, after);
  });

  const closeBtn = document.createElement("button");
  closeBtn.textContent = "Apply & Close";
  closeBtn.style.cssText =
    "margin-top:12px;padding:6px 12px;background:#4a90d9;color:#fff;border:none;border-radius:4px;cursor:pointer;";
  closeBtn.onclick = () => {
    const newOrderIndices = [...list.children].map((li) => Number(li.dataset.index));
    const reordered = newOrderIndices.map((i) => loraWidgets[i]);
    const { start } = getLoraIndexRange(node);
    if (start !== -1) {
      node.widgets.splice(start, reordered.length, ...reordered);
      node.setDirtyCanvas(true, true);
    }
    document.body.removeChild(overlay);
  };
  panel.appendChild(closeBtn);

  overlay.appendChild(panel);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) document.body.removeChild(overlay);
  });
  document.body.appendChild(overlay);
}

app.registerExtension({
  name: "yfg.PowerLoraLoaderExtras",

  nodeCreated(node) {
    if (
      node.comfyClass !== PLL_NAME &&
      node.type !== PLL_NAME &&
      node.title !== PLL_NAME
    ) return;
    if (node.__yfgPatched) return;
    node.__yfgPatched = true;
    console.log("[YFG PLL Extras] Patched node", node.id, node.comfyClass || node.type);

    // Defaults for randomize settings, persisted as node properties (these
    // survive save/reload, unlike widgets which rgthree fully rebuilds).
    node.properties.yfgAutoRandomize = node.properties.yfgAutoRandomize ?? false;
    node.properties.yfgRandomStrengthMin = node.properties.yfgRandomStrengthMin ?? 0.4;
    node.properties.yfgRandomStrengthMax = node.properties.yfgRandomStrengthMax ?? 1.0;
    node.properties.yfgRandomEnableChance = node.properties.yfgRandomEnableChance ?? 0.75;

    // A hidden widget whose sole purpose is the `beforeQueued` hook.
    // ComfyUI calls `beforeQueued()` on every widget of every node right
    // before it builds each individual prompt in an N-count queue -- the
    // same mechanism that drives "seed: randomize". This fires once per
    // queued run, so with a queue count of 5 it re-randomizes 5 times.
    node.widgets = node.widgets || [];
    node.widgets.push({
      name: "yfg_auto_randomize_hook",
      type: "hidden",
      value: null,
      computeSize: () => [0, -4],
      draw: () => {},
      serializeValue: () => undefined,
      beforeQueued: () => {
        if (!node.properties.yfgAutoRandomize) return;
        randomizeStrengths(
          node,
          node.properties.yfgRandomStrengthMin,
          node.properties.yfgRandomStrengthMax,
        );
        randomizeEnabled(node, node.properties.yfgRandomEnableChance);
      },
    });

    const origGetExtraMenuOptions = node.getExtraMenuOptions?.bind(node);
    node.getExtraMenuOptions = function (canvas, options) {
      origGetExtraMenuOptions?.(canvas, options);

      options.push(
        null, // divider
        {
          content: "🐯 YFG: Sort Loras",
          has_submenu: true,
          submenu: {
            options: [
              "Name (A-Z)",
              "Name (Z-A)",
              "Strength (High-Low)",
              "Strength (Low-High)",
              "Enabled First",
            ].map((mode) => ({
              content: mode,
              callback: () => sortLoras(node, mode),
            })),
          },
        },
        {
          content: "🐯 YFG: Nudge All Strengths",
          has_submenu: true,
          submenu: {
            options: [
              { content: "+0.05", callback: () => nudgeAll(node, 0.05) },
              { content: "-0.05", callback: () => nudgeAll(node, -0.05) },
              { content: "+0.10", callback: () => nudgeAll(node, 0.1) },
              { content: "-0.10", callback: () => nudgeAll(node, -0.1) },
              null, // divider
              { content: "Reset All to 1.0", callback: () => resetAllStrengths(node) },
            ],
          },
        },
        {
          content: "🐯 YFG: Randomize",
          has_submenu: true,
          submenu: {
            options: [
              {
                content: "Randomize Strengths…",
                callback: () => {
                  const cur = `${node.properties.yfgRandomStrengthMin},${node.properties.yfgRandomStrengthMax}`;
                  yfgPromptDialog("Strength range as min,max (e.g. 0.4,1.0):", cur, (input) => {
                    const parts = input.split(",").map((s) => parseFloat(s.trim()));
                    if (parts.length !== 2 || parts.some((n) => isNaN(n))) return;
                    node.properties.yfgRandomStrengthMin = Math.min(parts[0], parts[1]);
                    node.properties.yfgRandomStrengthMax = Math.max(parts[0], parts[1]);
                    randomizeStrengths(
                      node,
                      node.properties.yfgRandomStrengthMin,
                      node.properties.yfgRandomStrengthMax,
                    );
                  });
                },
              },
              {
                content: "Randomize On/Off…",
                callback: () => {
                  const cur = String(Math.round(node.properties.yfgRandomEnableChance * 100));
                  yfgPromptDialog("Percent chance each lora is ON (0-100):", cur, (input) => {
                    const pct = parseFloat(input);
                    if (isNaN(pct)) return;
                    node.properties.yfgRandomEnableChance = Math.max(0, Math.min(100, pct)) / 100;
                    randomizeEnabled(node, node.properties.yfgRandomEnableChance);
                  });
                },
              },
              null, // divider
              {
                content: node.properties.yfgAutoRandomize
                  ? "🔁 Auto-Randomize Each Queue Run: ON (click to turn off)"
                  : "🔁 Auto-Randomize Each Queue Run: OFF (click to turn on)",
                callback: () => {
                  node.properties.yfgAutoRandomize = !node.properties.yfgAutoRandomize;
                },
              },
            ],
          },
        },
        {
          content: "🐯 YFG: Reorder Panel (drag & drop)",
          callback: () => openReorderPanel(node),
        },
      );
    };
  },
});
