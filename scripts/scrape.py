"""
scrape.py
---------
Purpose of this file:

Scrapes geography articles in Lithuanian from Lithuanian Wikipedia.
Recursively crawls subcategories up to a configurable depth.
addition after experimentation: blocklist during Phase 1 so the per-category cap is not wasted on noise.

Usage:
    python scrape.py --output articles.json --max_articles 2000 (2000 is what I decided to use and is a default, 
    can be changed to any no. of interest/need)

Output format example (articles.json):
    [
        {
            "title": "Aukštaitija",
            "url": "https://lt.wikipedia.org/wiki/Aukštaitija",
            "text": "Aukštaitija – didžiausias Lietuvos etnografinis regionas. ...",
            "category": "ethnographic_region"
        },
        ...
    ]
"""

# libraries
import requests
import json
import time
import argparse
import logging
from typing import Optional
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

#-------------------------------------- CONFIG --------------------------------------

WIKI_API = "https://lt.wikipedia.org/w/api.php"

TARGET_CATEGORIES = [
    # ethnographic regions
    ("Lietuvos etnografiniai regionai",     "ethnographic_region"),
    # administrative divisions
    ("Lietuvos apskritys",                  "county"),
    ("Lietuvos savivaldybės",               "municipality"),
    ("Lietuvos miestai",                    "city"),
    ("Lietuvos miesteliai",                 "small_town"),
    # water bodies (decided not to include sea, since the category is not well defined in wikipedia)
    ("Lietuvos upės",                       "river"),
    ("Lietuvos ežerai",                     "lake"),
    ("Lietuvos salos",                      "island"),
    # protected areas
    #("Lietuvos nacionaliniai parkai",       "national_park"), # potentially overalps with later-added protected areas
    ("Lietuvos regioniniai parkai",         "regional_park"),
    # landforms / coastal
    ("Lietuvos pusiasaliai",                "peninsula"),
    ("Lietuvos pelkės",                     "bog"),
    ("Lietuvos miškai",                     "forest"),
    ("Lietuvos girios",                     "forest"),
    # heritage / landmarks
    ("Lietuvos pilys",                      "castle"),
    ("Pasaulio paveldo objektai Lietuvoje", "unesco_site"),
    # landforms
    ("Lietuvos kalvos",                     "hill"), # note: includes ozai and piliakalniai via recursion
    ("Lietuvos aukštumos",                  "highland"),
    ("Lietuvos lygumos",                    "plain"),
    # protected areas
    ("Lietuvos saugomos teritorijos",       "protected_area"),
    ]

# how deep to recurse into subcategories
MAX_DEPTH = 2

# max articles per category label
MAX_PER_CATEGORY = 80

# min article text length (characters) — skips stubs
MIN_TEXT_LENGTH = 300

# delay between API requests (seconds)
REQUEST_DELAY = 0.5

# ------ title blocklist — applied during Phase 1 to avoid wasting category slots------

TITLE_BLOCKLIST = [
    # press
    "laikraštis", "savaitraštis", "dienraštis", "žurnalas", "biuletenis",
    "žodis", "balsas", "naujienos", "aidas", "žinios", "tiesa",
    "santarvė", "švyturys", "šviesa", "bangos",
    # heraldry
    "herbas", "vėliava",
    # infrastructure
    "tiltas", "gatvė", "prospektas", "alėja", "šliuzas",
    "geležinkelio", "stotis", "uostas", "funikulierius",
    # buildings / architecture
    "architektūra",
    "bažnyčia", "bazilika", "katedra", "cerkvė", "sinagoga",
    "vienuolynas", "koplyčia", "šventykla",
    "muziejus", "galerija", "teatras", "filharmonija",
    "biblioteka", "spaustuvė", "ligoninė",
    "mokykla", "mokyklos", "gimnazija", "universitetas", 
    "universitetai", "akademija",
    "kolegija", "seminarija", "institutas", "institutai",
    "namas", "rūmai", "pastatas", "sandėliai",
    "fortas", "bokštas", "gaisrinė",
    "paštas", "bankas",
    # politics / admin
    "apygarda", "rinkimų", "seniūnija", "urėdija",
    "asociacija", "sąjunga", "indeksas",
    "meras", "merai", "vicemeras", "vicemerai",
    "rektorius", "rektoriai",
    "pedagogas", "pedagogai",
    "garbės pilietis", "garbės piliečiai",
    "seniūnas", "seniūnai",
    "politik",
    # streets / urban
    "aikštė", "skveras", "turgus", "vartai",
    # sports
    "futbol", "krepšin", "sporto klubas", "sportas",
    # culture / events
    "choras", "chorai",
    "renginys", "renginiai",
    "festivalis", "festivaliai",
    # misc
    "sąrašas", "kapinės", "paminklas", "kino teatras",
    "šventykla", "schema", "faksimilė",
    "surašymas", "surašymai",
    "įmonė", "įmonės",
    "bendrovė", "bendrovės",
    "organizacija", "organizacijos",
    "komuniz", "taryba", "tarybos",
    "muzikai", "muzika", "klubas", "klubai"
]


def is_blocked_title(title: str) -> bool:
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in TITLE_BLOCKLIST)


# ---------------------------- helper f-ions ----------------------------

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "LithuanianGeographyDataset/1.0 "
            "(academic NLP research, VU MIF; contact: student@stud.vu.lt)"
        )
    })
    return s


def get_category_members_flat(
    session: requests.Session,
    category: str,
) -> tuple[list[dict], list[str]]:
    """Fetch direct article members and subcategory names for a category."""
    articles: list[dict] = []
    subcats:  list[str]  = []

    params = {
        "action":  "query",
        "list":    "categorymembers",
        "cmtitle": f"Kategorija:{category}",
        "cmlimit": 500,
        "cmtype":  "page|subcat",
        "format":  "json",
    }

    while True:
        response = session.get(WIKI_API, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        for member in data.get("query", {}).get("categorymembers", []):
            if member["ns"] == 0:
                articles.append(member)
            elif member["ns"] == 14:
                subcats.append(member["title"].removeprefix("Kategorija:"))

        if "continue" not in data:
            break
        params["cmcontinue"] = data["continue"]["cmcontinue"]
        time.sleep(REQUEST_DELAY)

    return articles, subcats


def get_all_articles_recursive(
    session: requests.Session,
    category: str,
    label: str,
    seen_titles: set[str],
    seen_cats: set[str],
    depth: int = 0,
) -> list[dict]:
    """
    recursively collect article titles under `category` up to MAX_DEPTH.
    applies TITLE_BLOCKLIST during collection so blocked titles never
    enter the candidate pool and don't waste per-category slots.
    """
    if depth > MAX_DEPTH or category in seen_cats:
        return []
    seen_cats.add(category)

    log.info(f"{'  ' * depth}[depth={depth}] Category: {category}")

    try:
        articles, subcats = get_category_members_flat(session, category)
    except Exception as e:
        log.warning(f"{'  ' * depth}  Could not fetch '{category}': {e}")
        return []

    results = []
    skipped = 0

    for member in articles:
        title = member["title"]
        if title in seen_titles:
            continue
        if is_blocked_title(title):
            skipped += 1
            log.debug(f"{'  ' * depth}  Blocked: {title}")
            continue
        seen_titles.add(title)
        results.append({"title": title, "label": label})

    log.info(
        f"{'  ' * depth}  {len(articles)} articles found, "
        f"{len(results)} kept, {skipped} blocked, "
        f"{len(subcats)} subcategories"
    )

    time.sleep(REQUEST_DELAY)
    for subcat in subcats:
        results.extend(
            get_all_articles_recursive(
                session, subcat, label, seen_titles, seen_cats, depth + 1
            )
        )

    return results


def get_article_text(
    session: requests.Session,
    title: str,
) -> Optional[str]:
    #fetch plain-text extract of a single article
    params = {
        "action":          "query",
        "titles":          title,
        "prop":            "extracts",
        "explaintext":     True,
        "exsectionformat": "plain",
        "format":          "json",
    }

    response = session.get(WIKI_API, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            return None
        text = page.get("extract", "").strip()
        return text if len(text) >= MIN_TEXT_LENGTH else None

    return None


# ------------------------------------ Main ------------------------------------

def scrape(max_articles: int, output_path: str) -> None:
    session    = make_session()
    seen_titles: set[str] = set()
    seen_cats:   set[str] = set()

    # --- phase 1: collect candidate titles via recursive crawl ---
    log.info("phase 1: collection of article titles")
    candidates: list[dict] = []

    for category, label in TARGET_CATEGORIES:
        batch = get_all_articles_recursive(
            session, category, label, seen_titles, seen_cats, depth=0
        )
        candidates.extend(batch)
        log.info(f"Running total after '{category}': {len(candidates)} candidates")

    log.info(f"\nTotal unique candidates (post title-filter): {len(candidates)}")

    # --- phase 2: fetch article text ---
    log.info("\nphase 2: fetching article text")
    articles = []
    category_counts = defaultdict(int)

    for candidate in candidates:
        if len(articles) >= max_articles:
            log.info(f"Reached max_articles limit ({max_articles}). Stopping.")
            break

        label = candidate["label"]
        if category_counts[label] >= MAX_PER_CATEGORY:
            continue

        title = candidate["title"]

        try:
            text = get_article_text(session, title)
        except Exception as e:
            log.warning(f"  skipping '{title}': {e}")
            continue

        if text is None:
            log.debug(f"  skipping '{title}': missing / too short")
            continue

        articles.append({
            "title":    title,
            "url":      f"https://lt.wikipedia.org/wiki/{title.replace(' ', '_')}",
            "text":     text,
            "category": label,
        })
        category_counts[label] += 1
        log.info(f"  [{len(articles)}/{max_articles}] Saved: {title} ({len(text)} chars)")
        time.sleep(REQUEST_DELAY)

    #save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    log.info(f"\nsaved {len(articles)} articles to '{output_path}'.")
    log.info("cat breakdown:")
    for cat, count in Counter(a["category"] for a in articles).most_common():
        log.info(f"  {cat}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="scrape Lithuanian geography articles from Wikipedia."
    )
    parser.add_argument("--output",       default="articles.json", help="Output JSON file")
    parser.add_argument("--max_articles", default=2000, type=int,  help="Safety ceiling")
    args = parser.parse_args()

    scrape(max_articles=args.max_articles, output_path=args.output)
