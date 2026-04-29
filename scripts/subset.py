import json
from collections import defaultdict

with open("articles_filtered.json", encoding="utf-8") as f:
    articles = json.load(f)

by_cat = defaultdict(list)
for a in articles:
    by_cat[a.get("category", "other")].append(a)

per_cat = max(250 // len(by_cat), 5)
filtered = []
for cat, items in by_cat.items():
    items.sort(key=lambda a: len(a["text"]), reverse=True)
    filtered.extend(items[:per_cat])

print(f"Categories: {len(by_cat)}")
for cat, items in by_cat.items():
    kept = min(len(items), per_cat)
    print(f"  {cat}: {kept}/{len(items)}")
print(f"Total: {len(filtered)} articles")

with open("articles_top250.json", "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)