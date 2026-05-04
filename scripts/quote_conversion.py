"""
quote_conversion.py
---------
Purpose of this file:

Converts quotes in a dataset that follow "quote" or 'quote' structure
into proper lithuanian quotes  „text“

Usage:
    python quote_conversion.py --input dataset.json # for overall dataset
    python quote_conversion.py --input eval_raw.json # for additional evaluation dataset

"""

# imports
import json
import re
import argparse

def convert_quotes(text):
    # convert paired single quotes: '...'
    text = re.sub(r"(?<!\w)'([^'\n]{1,200}?)'(?!\w)", r"„\1“", text) # context-aware regex for paired quotes

    # convert paired double quotes: "..."
    text = re.sub(r'(?<!\w)"([^"\n]{1,200}?)"(?!\w)', r"„\1“", text) # context-aware regex for paired quotes

    return text

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True, help="input JSON file")
args = parser.parse_args()

with open(args.input, encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    for key in ("instruction", "output"):
        item[key] = convert_quotes(item[key])
    item.pop("source_title", None) # removed source_title only. Will keep category for reporting reasons

with open(args.input, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)