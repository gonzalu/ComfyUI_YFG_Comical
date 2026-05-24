# =============================================================================
# Author      : Manny Gonzalez | YFG 🐯
# Title       : YFG Display Value Node
# Nickname    : yfg_display_value
# Description : Displays any value (INT, FLOAT, STRING) in the node body and
#               inline in the title bar. Rename node to set the label prefix.
#               Follows the rgthree DisplayAny pattern for body display.
# Version     : 1.1.0
# =============================================================================


class AnyType(str):
    """Wildcard type — accepts any ComfyUI data type."""
    def __ne__(self, __value: object) -> bool:
        return False


any_type = AnyType("*")


class YFG_DisplayValue:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": (any_type,),
            },
            "hidden": {
                "unique_id":    "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION     = "display"
    OUTPUT_NODE  = True
    CATEGORY     = "🐯 YFG"
    DESCRIPTION  = "Displays any value in the node body and title bar. Rename to label."

    def display(self, value, unique_id=None, extra_pnginfo=None):
        text = str(value)

        # Save value into widgets_values so it pre-fills on workflow reload
        # (same pattern as rgthree DisplayAny)
        if extra_pnginfo and unique_id:
            for node in (extra_pnginfo.get("workflow", {}).get("nodes", [])
                         if isinstance(extra_pnginfo, dict)
                         else []):
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
