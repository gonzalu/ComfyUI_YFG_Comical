"""
@author: Manny Gonzalez
@title: 🐯 YFG Comical Nodes
@nickname: 🐯 YFG Comical Nodes
@description: Utility custom nodes for special effects, image manipulation and quality of life tools.
"""

## Based on original code by Jordan Thompson (WASasquatch) https://github.com/WASasquatch/was-node-suite-comfyui ##
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to
# deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import requests
import json
import hashlib

class RandomOrgTrueRandomNumber:
    """True Random Number Generator via random.org"""
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {"default": "00000000-0000-0000-0000-000000000000", "multiline": False}),
                "minimum": ("FLOAT", {"default": 0, "min": -9223372036854775808, "max": 9223372036854775807}),
                "maximum": ("FLOAT", {"default": 10, "min": -9223372036854775808, "max": 9223372036854775807}),
                "mode": (["random", "fixed"],),
            }
        }

    # Emit Number, Float, and Integer outputs to match dependent nodes
    RETURN_TYPES = ("NUMBER", "FLOAT", "INT")
    FUNCTION = "return_true_random_number"
    CATEGORY = "🐯 YFG/🔢 Numbers"

    def return_true_random_number(self, api_key, minimum, maximum, mode="random"):
        """Generate one true random integer and return as NUMBER, FLOAT, and INT"""
        nums = self.get_random_numbers(
            api_key=api_key,
            amount=1,
            minimum=minimum,
            maximum=maximum,
            mode=mode
        )
        number = nums[0]
        return (number, float(number), int(number))

    def get_random_numbers(self, api_key, amount=1, minimum=0, maximum=10, mode="random"):
        """Fetches `amount` true random integers from random.org."""
        if not api_key or api_key == "00000000-0000-0000-0000-000000000000":
            print("Error: A valid RANDOM.ORG API key is required.")
            return [0]

        payload = {
            "jsonrpc": "2.0",
            "method": "generateIntegers",
            "params": {
                "apiKey": api_key,
                "n": amount,
                "min": int(minimum),
                "max": int(maximum),
                "replacement": True,
                "base": 10
            },
            "id": 1
        }

        response = requests.post(
            "https://api.random.org/json-rpc/2/invoke",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "random" in data["result"]:
                return data["result"]["random"]["data"]
        return [0]

    @classmethod
    def IS_CHANGED(cls, api_key, mode, **kwargs):
        """Used by ComfyUI to detect when `mode=='fixed'` and keep output constant"""
        m = hashlib.sha256()
        m.update(api_key.encode('utf-8'))
        if mode == 'fixed':
            return m.hexdigest()
        return float('nan')
