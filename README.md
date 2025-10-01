<p align="center">
  <img src="img/lion-face.svg" width="200">
</p>

<div align="center">

# YFG Comical ComfyUI Custom Nodes

</div>

A collection of ComfyUI utility custom nodes. These provide functionality not offered in the core app or other custom nodes. Several nodes enhance existing ideas with improved UX and quality-of-life features.

---

- [YFG Comical ComfyUI Custom Nodes](#yfg-comical-comfyui-custom-nodes)
  * [Nodes](#nodes)
    + [Image Histograms Generator](#image-histograms-generator)
    + [Image Histograms Generator (compact)](#image-histograms-generator-compact)
    + [Image Halftone Generator](#image-halftone-generator)
    + [Image Side by Side](#image-side-by-side)
    + [Image to imgBB](#image-to-imgbb)
      - [Setup](#setup)
    + [Smart Checkpoint Loader](#smart-checkpoint-loader)
    + [Mono Clip](#mono-clip)
    + [VAE Decode with Preview](#vae-decode-with-preview)
    + [Image to Contrast Mask](#image-to-contrast-mask)
    + [PixelArt](#pixelart)
    + [Text Mask Overlay](#text-mask-overlay)
    + [Image Switchers](#image-switchers)
    + [Random.org True Random Number](#randomorg-true-random-number)
    + [Random.org True Random Number (V2)](#randomorg-true-random-number-v2)
  * [Examples](#examples)
    + [Sample Workflow](#sample-workflow)
  * [All nodes as of 06-13-2024](#all-nodes-as-of-06-13-2024)
  * [Acknowledgements](#acknowledgements)

<small><i><a href="http://ecotrust-canada.github.io/markdown-toc/">Table of contents generated with markdown-toc</a></i></small>

---

## Nodes

### Image Histograms Generator

![Image Histograms Generator](img/imagehistogramsgenerator.png)

Calculate image histograms for RGB channels and L (luminance); displays a graphical representation.

### Image Histograms Generator (compact)

![Image Histograms Generator (compact)](img/image2histogramscompact.png)

Reduces outputs to just two: Original and Histogram. Can self-preview (original or histogram) and forward the selected histogram downstream.

### Image Halftone Generator

![Image Halftone Generator](img/image2halftone.png)

*Based on original code by Phil Gyford and ComfyUI node by aimingfail.*

Generates halftone from an input image; can self-display or send output to other nodes.

### Image Side by Side

![Image Side-by-Side Generator](img/images2sidebysidesplit.png)

Creates a side-by-side or split image from two inputs. Optional self-preview, headers (font/size/color), and label toggles.

Example (side-by-side instead of split):

![Image Side-by-Side Generator](img/images2sidebyside.png)

### Image to imgBB

![Image to imgBB](img/image2imgbb.png)

Upload and download images to/from [imgBB](https://www.imgbb.com/). Includes nodes for downloading images and a URL “storage” node that keeps the original link alongside the workflow.

#### Setup

Create `imgbb_api_key.json` under `./loaders/`:

```json
{
  "api_key": "YOUR_API_KEY_HERE"
}
```

Obtain a key at <https://api.imgbb.com/>.

### Smart Checkpoint Loader

![Smart Checkpoint Loader](img/smartCheckpointLoader.png)

Drop-in replacement for the core “Load Checkpoint,” but flattens complex directory trees so checkpoints appear as if in a single folder — ideal for sharing workflows.

### Mono Clip

![Mono Clip](img/MonoClip.png)

Produces B/W or grayscale clipped images with three modes (each reversible). Useful for masks and stylization.

*Based on original code by XSS.*

### VAE Decode with Preview

![VAE Decode w/ Preview](img/VAEDecodePreview.png)

VAE decode with inline preview and QoL options.

*Based on original code by XSS.*

### Image to Contrast Mask

![Image to Contrast Mask](img/image2contrastmask.png)

Creates a grayscale contrast mask. Select low/high thresholds (1–255), optional blur.

*Based on original code by XSS.*

### PixelArt

![PixelArt](img/pixelart.png)

Generates pixel-art style images. Choose interpolation and pixel size.

*Based on original Mosaic code by XSS.*

### Text Mask Overlay

![Text Mask Overlay](img/textMaskOverlay01a.png)

Enhances the idea by Yuigahama Yui:

- Choose fonts from System, User, or local `./fonts/` directory.
- Built-in Mask-to-Image conversion (no extra converter needed).

**Example**

| <a href="img/textMaskOverlay01original.png"><img src="img/textMaskOverlay01original.png" alt="Text Mask Overlay Example" width="400"/></a> | <a href="img/textMaskOverlay01.png"><img src="img/textMaskOverlay01.png" alt="Text Mask Overlay Example" width="400"/></a> |
| :-: | :-: |
| Original | Output |

Example [workflow JSON](workflows/ComfyUI_YFG_Comical-Text-Mask-Overlay-Workflow.json) (also embedded in the image below):

[![Text Mask Overlay](img/textMaskOverlayWorkflow01.png)](workflows/ComfyUI_YFG_Comical-Text-Mask-Overlay-Workflow.png)

*Based on the ComfyUI-Text node by Yuigahama Yui.*

### Image Switchers

![switchers](img/switchers.png)

Multi-input image switchers (3, 5, 10, 15, 20 inputs). Provide a routing matrix, inline preview, and graceful handling of missing inputs (with user warnings). Designed to avoid “ganged” switcher confusion in complex workflows.

![switchers](img/switchers03.png)
![switchers](img/switchers05.png)
![switchers](img/switchers05b.png)

### Random.org True Random Number

![random-number](img/RandomOrgTrueRandomNumber.png)

Modified version of the WAS node (original wasn’t functioning). Requires a [Random.org](https://www.random.org/) account and [API key](https://api.random.org/dashboard).

*Based on original code by WASasquatch.*

---

### Random.org True Random Number (V2)

![random-number-v2](img/RandomOrgV2TrueRandomNumber.png)

Integrates with the [random.org JSON-RPC API](https://api.random.org/json-rpc/2/) to generate **true random numbers** from atmospheric noise.

#### ✨ Features

- **Secure API key handling**  
  Key is **not** exposed in UI, workflow JSON, or image metadata. Loaded at runtime from:
  1. Environment variable `RANDOM_ORG_API_KEY`, or
  2. Local JSON file `random_org_api_key.json` next to `RandomOrgV2.py`.

- **Flexible outputs**  
  Emits three types for broad node compatibility:
  - `NUMBER`
  - `FLOAT`
  - `INT`

- **Optional uniqueness filtering (in-memory)**  
  Avoid repeats within a Python session:
  - `ensure_unique` — toggle de-duplication
  - `unique_scope` — `"range"` (per `[min, max]`) or `"global"` (across all ranges)
  - `history_size` — how many values to remember
  - `time_window_sec` — ignore duplicates older than this window
  - `retry_limit` — extra draws to try before giving up

- **Backwards compatible**  
  Old node remains available as `RandomOrgTrueRandomNumber_node`.  
  New node is `RandomOrgV2TrueRandomNumber_node`.

#### 🔑 API Key Setup

1. Create `random_org_api_key.json` next to `RandomOrgV2.py`:

   ```json
   {
     "api_key": "YOUR_API_KEY_HERE"
   }
   ```

2. Or set an environment variable before launching ComfyUI:

   ```bash
   export RANDOM_ORG_API_KEY=YOUR_API_KEY_HERE
   ```

   On Windows (PowerShell):

   ```powershell
   setx RANDOM_ORG_API_KEY "YOUR_API_KEY_HERE"
   ```

#### ⚙️ Example Usage

- **Generate a random integer between 1 and 100**
  - `minimum = 1`
  - `maximum = 100`
  - `mode = random`

- **Ensure no repeats in the current range**
  - Enable `ensure_unique`
  - Set `unique_scope = range`
  - Adjust `history_size` and `time_window_sec`

#### 📌 Notes

- **Session-lifetime uniqueness** resets when Python restarts.  
- **Persistence** (disk-based history) may be added in a future version.  
- **API limits**: Random.org quotas apply — check your dashboard.

---

## Examples

### Sample Workflow

![Example Workflow](workflows/ComfyUI_YFG_Comical-Example-Workflow.png)

If the embedded workflow doesn't load, use the JSON:  
[workflows/ComfyUI_YFG_Comical-Example-Workflow.json](workflows/ComfyUI_YFG_Comical-Example-Workflow.json)

## All nodes as of 06-13-2024

![All Nodes](img/allnodes06132024.png)

## Acknowledgements

Huge thanks to creators whose work inspires or integrates with these nodes:

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [MarasIT](https://github.com/davask/ComfyUI-MarasIT-Nodes)
- [Dr.Lt.Data](https://github.com/ltdrdata)
- [melMas](https://github.com/melMass/comfy_mtb)
- [rgthree](https://github.com/rgthree/rgthree-comfy)
- [Akatsuzi](https://github.com/Suzie1)
- [chrisgoringe](https://github.com/chrisgoringe/cg-use-everywhere)
- [pythongosssss](https://github.com/pythongosssss)

…and many others. Thank you for your talent and generosity.
