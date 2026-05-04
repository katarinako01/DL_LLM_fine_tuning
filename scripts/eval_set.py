"""
eval_set.py
---------
Purpose of this file:

Picks additional articles to create an evaluation set that covers 
questions about Lithuanian geography objects not in the selected 213 articles (from a subset)

after this -> run annotation.py again but with articles_eval.json as an input and save output 
with a different name to not replace existing dataset

then -> add: 
1. manually hallucination probes (questions about fictional or 
non-existent places to see if the model invents answers)
2. edge cases (ambiguous or tricky questions that mix geography with history, 
has multiple possible answers, very specific questions the model probably can't answer, etc.)

Usage:
    python eval_set.py

"""
# imports
import json
import random
from collections import defaultdict

random.seed(123)

with open("articles_filtered.json", encoding="utf-8") as f:
    all_articles = json.load(f)

with open("articles_top250.json", encoding="utf-8") as f:
    used_articles = json.load(f)

used_titles = {a["title"] for a in used_articles}

# get articles that arent used in annotation
remaining = [a for a in all_articles if a["title"] not in used_titles]

# sample subset for evaluation (balanced, so no one category dominates)
by_cat = defaultdict(list)
for a in remaining:
    by_cat[a.get("category", "other")].append(a)

per_cat = max(1, 20 // len(by_cat))
sampled = []
for cat, items in by_cat.items():
    items.sort(key=lambda a: len(a["text"]), reverse=True)
    sampled.extend(items[:per_cat])

with open("articles_eval.json", "w", encoding="utf-8") as f:
    json.dump(sampled, f, ensure_ascii=False, indent=2)