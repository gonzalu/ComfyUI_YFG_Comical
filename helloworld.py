"""
@author: YFG
@title: YFG Hello World
@nickname: YFG Hello World
@description: This extension just outputs Hello World! as a string.
"""
class HelloWorldNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {}
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("message_out",)
    FUNCTION = "print_message"
    CATEGORY = "YFG"
    OUTPUT_NODE = True
    
    def print_message(self):
        return ("Hello World!",)
