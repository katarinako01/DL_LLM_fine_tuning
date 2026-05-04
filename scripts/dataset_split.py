"""
dataset_split.py
---------
Purpose of this file:

Splits dataset into train/val/test sets for further fine-tuning

Usage:
    python dataset_split.py

"""
# imports
import json
import random
from collections import defaultdict

random.seed(123) # for reproductibilty

with open("dataset.json", encoding="utf-8") as f:
    data = json.load(f)

# group by category for stratified split
by_cat = defaultdict(list)
for item in data:
    by_cat[item.get("category", "other")].append(item)

train = []
val = []
test = []

for cat, items in by_cat.items():
    random.shuffle(items)
    n = len(items)
    train_end = max(1, int(n * 0.80))
    val_end = max(train_end + 1, int(n * 0.90))
    train.extend(items[:train_end])
    val.extend(items[train_end:val_end])
    test.extend(items[val_end:])

random.shuffle(train)
random.shuffle(val)
random.shuffle(test)

# remove source_title and category for training format (only need instruction/input/output)
def clean(item):
    return {
        "instruction": item["instruction"],
        "input": item["input"],
        "output": item["output"]
    }

train_clean = [clean(i) for i in train]
val_clean = [clean(i) for i in val]
test_clean = [clean(i) for i in test]

# save
with open("train.json", "w", encoding="utf-8") as f:
    json.dump(train_clean, f, ensure_ascii=False, indent=2)

with open("val.json", "w", encoding="utf-8") as f:
    json.dump(val_clean, f, ensure_ascii=False, indent=2)

with open("test.json", "w", encoding="utf-8") as f:
    json.dump(test_clean, f, ensure_ascii=False, indent=2)

# summary
print(f"Total: {len(data)}")
print(f"train: {len(train_clean)}")
print(f"val:   {len(val_clean)}")
print(f"test:  {len(test_clean)}")
print(f"\nper cat:")
for cat, items in sorted(by_cat.items()):
    n = len(items)
    t = max(1, int(n * 0.80))
    v = max(t + 1, int(n * 0.90)) - t
    te = n - t - v
    print(f"  {cat}: {n} total TO {t} train / {v} val / {te} test")