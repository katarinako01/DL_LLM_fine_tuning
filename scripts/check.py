import json
from collections import Counter

with open("articles_filtered.json", encoding="utf-8") as f:
    articles = json.load(f)

titles = [a["title"] for a in articles]
dupes = [t for t, count in Counter(titles).items() if count > 1]
print(f"Duplicates: {len(dupes)}")
for d in dupes:
    print(d)