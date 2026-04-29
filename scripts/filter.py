"""
filter.py
---------
Purpose of this file:

removes non-geographic articles from articles.json based on article text.
Title-based filtering is handled upstream in scrape.py during Phase 1.

Usage:
    python filter.py --input articles.json --output articles_filtered.json

Important note: always review the _removed.json output to check nothing useful was dropped
"""

# libraries
import re
import json
import argparse
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# --------- text-based filters — checks first 200 chars of article text ---------

TEXT_BLOCKLIST = [
    # press
    "yra laikraštis",
    "yra savaitraštis",
    "yra dienraštis",
    "yra žurnalas",
    # heraldry
    "yra herbas",
    # institutions
    "yra asociacija",
    "yra Lietuvos laisvosios rinkos instituto",
    "yra universitetas",
    "yra aukštoji mokykla",
    "yra mokykla",
    "yra gimnazija",
    "yra kolegija",
    "yra akademija",
    "yra institutas",
    "yra seminarija",
    "yra urėdija",
    # religion
    "yra bažnyčia",
    "yra katalikų bažnyčia",
    "yra evangelikų",
    "yra cerkvė",
    "yra sinagoga",
    "yra koplyčia",
    "yra vienuolynas",
    # culture / entertainment
    "yra muziejus",
    "yra galerija",
    "yra teatras",
    "yra filharmonija",
    "yra kino teatras",
    # infrastructure
    "yra tiltas",
    "yra pėsčiųjų tiltas",
    "yra geležinkelio tiltas",
    "yra funikulierius",
    # buildings
    "yra pastatas",
    "yra namas",
    "yra rūmai",
    # admin / politics
    "yra apygarda",
    "yra rinkimų apygarda",
    "yra seniūnija",
    "yra bankas",
    "yra paštas",
    # person articles
    "yra lietuvių",
    "yra Lietuvos",
    "yra žydų",
    "yra lenkų",
    "yra rusų",
    "yra politikas",
    "yra verslininkas",
    "yra visuomenės veikėjas",
    "yra sportininkas",
    "yra žurnalistas",
    "yra aktorius",
    "yra režisierius",
    "yra karininkas",
    "yra diplomatas",
    # newspapers
    "laikraštis",
    "savaitraštis",
    "dienraštis",
    # misc
    "yra draugija",
    "yra bendrija", 
    "yra kompanija",
    "yra kolektyvas",
    "yra radijas",
    "yra gildija",
    "yra kultūros centras",
    "yra visuomenės centras",
    "gaisras, kilęs", # fire events
    "kautynės, įvykusios", # battles
    "– gaisras",
    "– kautynės",
    "– lietuviška", # food products
    "rajono politikas", # there was one politician that slipped into the dataset
    "administratorius",
]

GEOGRAPHIC_KEYWORDS = [
    "upė", "ežeras", "aukštuma", "plynaukštė", "draustinis",
    "kalnas", "skardis", "kopa", "miškas", "pelkė", "regionas",
    "miesto dalis", "mikrorajonas", "gyvenvietė",
]

# filter logic

def is_blocked_by_text(text: str) -> bool:
    snippet = text[:200].lower()
    return any(pattern.lower() in snippet for pattern in TEXT_BLOCKLIST)

def is_person_article(text: str) -> bool:
    # person articles typically start with "Firstname Lastname – " 
    # where both words are capitalized and followed by a dash
    snippet = text[:150]
    # Don't flag if it's clearly a geographic feature
    snippet_lower = snippet.lower()
    if any(kw in snippet_lower for kw in GEOGRAPHIC_KEYWORDS):
        return False
    # pattern: Two or more capitalized words followed by – or (born year)
    if re.match(r'^[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+\s+[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+.*\s+–\s+', snippet):
        return True
    # also catch "Name (1949) – " format
    if re.match(r'^[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+\s+[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+\s+\(\d{4}\)', snippet):
        return True
    return False

def filter_articles(input_path: str, output_path: str) -> None:
    with open(input_path, encoding="utf-8") as f:
        articles = json.load(f)

    log.info(f"Loaded {len(articles)} articles from '{input_path}'")

    kept    = []
    removed = []
    
    for article in articles:
        text = article.get("text", "")
        if is_blocked_by_text(text):
            log.debug(f"  remove: {article['title']}")
            removed.append({**article, "filter_reason": "text"})
        elif is_person_article(text):
            log.debug(f"  remove (person): {article['title']}")
            removed.append({**article, "filter_reason": "person"})
        else:
            kept.append(article)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    removed_path = output_path.replace(".json", "_removed.json")
    with open(removed_path, "w", encoding="utf-8") as f:
        json.dump(removed, f, ensure_ascii=False, indent=2)

    log.info(f"\nKept:    {len(kept)} articles to '{output_path}'")
    log.info(f"Removed: {len(removed)} articles to '{removed_path}'")
    log.info("\nCat breakdown after filtering:")
    for cat, count in Counter(a["category"] for a in kept).most_common():
        log.info(f"  {cat}: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="filter non-geographic articles.")
    parser.add_argument("--input",  default="articles.json",          help="Input JSON file")
    parser.add_argument("--output", default="articles_filtered.json", help="Output JSON file")
    args = parser.parse_args()
    filter_articles(input_path=args.input, output_path=args.output)