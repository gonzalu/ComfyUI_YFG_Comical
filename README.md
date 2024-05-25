<p align="center">
  <img src="img/lion-face.svg" width="200">
</p>

<div align="center">

# YFG Comical ComfyUI Custom Nodes 

</div>

A collection of ComfyUI utility custom nodes. Hope these provide some functionality not offered in the core app or other custom nodes.

## Nodes

### Image Histograms Generator

![Image Histograms Generator](img/imagehistogramsgenerator.png)

This node allows you to take an input image, calculate its histogram for the color channels as well as the L channel and display a graphical representation of the data.

### Image Histograms Generator (compact)

![Image Histograms Generator (compact)](img/image2histogramscompact.png)

This version of the node reduces the number of outputs to just two: Original and Histogram. You have a choice of using the node as a preview node and chose what to display in the node: The selected Histogram or the Orginal Image. The Histogram output will send the selected Histogram to the next node. 

### Image Halftone Generator

![Image Halftone Generator](img/image2halftone.png)

*This node is based on original code by Phil Gyford https://github.com/philgyford/python-halftone and ComfyUI node by aimingfail https://civitai.com/models/143293/image2halftone-node-for-comfyui*

This node generates a halftone image from the input image. It can self display and send the output to other downstream nodes. You have a choice of displaying either the Original Image ort the generated Halftone image. The display can also be turned off. 

### Image Side by Side

![Image Side-by-Side Generator](img/images2sidebysidesplit.png)

This node generates either a Side-by-Side image of a Split image from two input images. You can turn on node self preview or send the resulting image to other downstream nodes. The header labels can be turned off and the font, size and color can also be selected. 

Here is an example of the images Side by Side instead of split.

![Image Side-by-Side Generator](img/images2sidebyside.png)

## Examples

### Sample Workflow

![Example Workflow](workflows/ComfyUI_YFG_Comical-Example-Workflow.png)

The workflow should be embedded in the file. If you can't get it to load, feel free to download and open the [workflow.json](workflows/ComfyUI_YFG_Comical-Example-Workflow.json) file.

## Acknowledgements

I have to give credit to at least those who's other custom nodes I use quite often and in some cases make my life in ComfyUI all around better.

 - [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
 - [MarasIT](https://github.com/davask/ComfyUI-MarasIT-Nodes)
 - [Dr.Lt.Data](https://github.com/ltdrdata)
 - [melMas](https://github.com/melMass/comfy_mtb)
 - [rgthree](https://github.com/rgthree/rgthree-comfy)
 - [Akatsuzi](https://github.com/Suzie1)
 - [chrisgoringe](https://github.com/chrisgoringe/cg-use-everywhere)
 - [pythongosssss](https://github.com/pythongosssss)

 And many many others too many to name. Your inspiration and talent is really exemplary. Thank you.
 