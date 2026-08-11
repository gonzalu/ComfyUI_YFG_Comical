# ============================================================================
#  Author:      Manny Gonzalez (gonzalu)
#  Title:       🐯 YFG Text Concat Swap
#  Nickname:    🐯 Concat Swap
#  Description: Concatenates two strings with a delimiter, plus a single
#               clickable BOOLEAN toggle that flips the order (A + B / B + A)
#               without retyping or rewiring anything. Empty or None inputs
#               are dropped so you never get a dangling delimiter.
#  Pack:        ComfyUI_YFG_Comical
# ============================================================================


class YFGTextConcatSwap:
    """
    Order-swappable text concatenation.

    swap = off  ->  text_a + delimiter + text_b
    swap = on   ->  text_b + delimiter + text_a

    The delimiter accepts the escapes \\n, \\t and \\s (literal space), so a
    plain space or newline can be entered in the single-line widget.
    """

    CATEGORY = "🐯 YFG/Switchers"
    FUNCTION = "concat_swap"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "order")
    DESCRIPTION = "Concatenate two strings with a toggle that flips A/B order."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_a": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "dynamicPrompts": True,
                    "tooltip": "First string when swap is OFF.",
                }),
                "text_b": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "dynamicPrompts": True,
                    "tooltip": "First string when swap is ON.",
                }),
                "delimiter": ("STRING", {
                    "multiline": False,
                    "default": ", ",
                    "tooltip": "Joiner. Supports \\n, \\t and \\s escapes.",
                }),
                "swap": ("BOOLEAN", {
                    "default": False,
                    "label_on": "B + A",
                    "label_off": "A + B",
                    "tooltip": "Click to flip the concatenation order.",
                }),
                "trim_parts": ("BOOLEAN", {
                    "default": True,
                    "label_on": "trim",
                    "label_off": "raw",
                    "tooltip": "Strip leading/trailing whitespace from each part.",
                }),
            },
        }

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _as_text(value):
        """Coerce anything (including None) into a safe string."""
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return "".join(YFGTextConcatSwap._as_text(v) for v in value)
        return value if isinstance(value, str) else str(value)

    @staticmethod
    def _expand_escapes(delimiter):
        """Allow \\n, \\t and \\s to be typed into the single-line widget."""
        delimiter = YFGTextConcatSwap._as_text(delimiter)
        return (delimiter
                .replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace("\\s", " "))

    # ------------------------------------------------------------------- main
    def concat_swap(self, text_a="", text_b="", delimiter=", ",
                    swap=False, trim_parts=True):
        a = self._as_text(text_a)
        b = self._as_text(text_b)
        sep = self._expand_escapes(delimiter)

        if trim_parts:
            a = a.strip()
            b = b.strip()

        parts = [b, a] if swap else [a, b]
        parts = [p for p in parts if p != ""]

        result = sep.join(parts)
        order = "B + A" if swap else "A + B"

        return (result, order)


# ---------------------------------------------------------------------------
# Registration (mirror these into the pack's top-level __init__.py)
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "YFGTextConcatSwap": YFGTextConcatSwap,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "YFGTextConcatSwap": "🐯 YFG Text Concat Swap",
}
