# =============================================================================
# Author      : Manny Gonzalez | YFG 🐯
# Title       : YFG Display Value Node
# Nickname    : yfg_display_value
# Description : Displays any value (INT, FLOAT, STRING) in the node body and
#               inline in the title bar. Three typed optional inputs ensure
#               full compatibility with Use Everywhere (UE) broadcast nodes.
#               Rename node to set the label prefix.
# Version     : 1.2.0
# =============================================================================


class YFG_DisplayValue:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "int_value":    ("INT",    {"forceInput": True}),
                "float_value":  ("FLOAT",  {"forceInput": True}),
                "string_value": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "unique_id":     "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION     = "display"
    OUTPUT_NODE  = True
    CATEGORY     = "🐯 YFG"
    DESCRIPTION  = (
        "Displays INT, FLOAT, or STRING inline in the node title and body. "
        "Connect whichever type you need — all three inputs are compatible "
        "with Use Everywhere (UE) broadcast nodes. Rename to set the label."
    )

    def display(self,
                int_value=None,
                float_value=None,
                string_value=None,
                unique_id=None,
                extra_pnginfo=None):

        # Use whichever input is connected; priority: INT > FLOAT > STRING
        if int_value is not None:
            value = int_value
        elif float_value is not None:
            value = float_value
        elif string_value is not None:
            value = string_value
        else:
            value = None

        text = str(value) if value is not None else ""

        # Save into widgets_values so the value pre-fills on workflow reload
        if text and extra_pnginfo and unique_id:
            nodes = (extra_pnginfo.get("workflow", {}).get("nodes", [])
                     if isinstance(extra_pnginfo, dict) else [])
            for node in nodes:
                if str(node.get("id")) == str(unique_id):
                    node["widgets_values"] = [text]
                    break

        return {"ui": {"text": (text,)}}


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "YFG_DisplayValue": YFG_DisplayValue,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "YFG_DisplayValue": "🐯 Display Value",
}
