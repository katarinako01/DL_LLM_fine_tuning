#imports / libraries
import re
import json
import time
import logging
import argparse
import re
from pathlib import Path
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048  # note: increased from 1024 to prevent truncated JSON responses
TEMPERATURE = 0.3
TEXT_LIMIT = 1500
REQUEST_DELAY = 1.0

SYSTEM_PROMPT = (
    "Tu esi Lietuvos geografijos, regionų ir vietovių ekspertas. "
    "Generuoji klausimų ir atsakymų rinkinius lietuvių kalba pagal pateiktą tekstą. "
    "Naudok taisyklingą bendrinę lietuvių kalbą, venk angliškų terminų. "
    "Naudok tik pateiktą tekstą – jokios papildomos išorinės informacijos. "
    "Atsakyk tik JSON formatu, be jokių papildomų komentarų."
)

USER_PROMPT_TEMPLATE = """Remdamasis šiuo tekstu apie „{title}", sugeneruok klausimų ir atsakymų rinkinius lietuvių kalba.

Tekstas:
{text}

Sugeneruok iki 3 rinkinių. Jei tekstas per trumpas arba neturi pakankamai turinio trims skirtingiems klausimams – sugeneruok tik 1 arba 2 kokybiškus rinkinius. 
Naudok tik aiškiai pateiktą informaciją tekste. Jei faktas nepaminėtas, jo nesugalvok. Nenaudok bendrų žinių apie objektą, jei jos nepaminėtos pateiktame tekste.

Kiekvienas rinkinys turi turėti:
- „instruction": konkretus klausimas lietuvių kalba (NE aprašymas, NE etiketė — o pats klausimas)
- „input": VISADA tuščias string ""
- „output": 2–4 sakinių atsakymas taisyklinga bendrine lietuvių kalba

Klausimų tipai (būtent šia tvarka, jei generuoji 3):
1. FAKTINIS — konkretus faktas iš teksto: data, skaičius, pavadinimas, vieta
2. APRAŠOMASIS — kaip atrodo, kur yra, kokie pagrindiniai bruožai
3. IŠSKIRTINUMAS — kuo ši vieta ypatinga: gamtiniai ypatumai, ekologinė ar turizmo reikšmė, ryšys su aplinkine geografija arba istorinė svarba (jei aktualu)

Kalbos kokybė:
- Naudok teisingas lietuviškas raides su diakritiniais ženklais (ą, č, ę, ė, į, š, ų, ū, ž) — niekada nerašyk be jų
- Ignoruok bet kokį tekstą rusų, senąja rusų, lenkų ar kitomis kalbomis, kuris gali pasitaikyti šaltinyje — naudok tik lietuvišką turinį ir generuok tik lietuviškai
- Naudok tik taisyklingą bendrinę lietuvių kalbą, venk tarminių ar šnekamajai kalbai būdingų formų

Draudžiama:
- Rašyti „instruction" lauke tokią etiketę, kaip „Faktinis klausimas apie X" — ten turi būti pats klausimas
- Minėti „pagal tekstą" ar „remiantis tekstu" atsakyme
- Kartoti klausimą atsakyme
- Kopijuoti teksto sakinius pažodžiui — perfrazuok savais žodžiais
- Pridėti abejotiną ar nepatikimą informaciją — geriau palikti trumpesnį tikslų atsakymą nei papildyti faktu, dėl kurio nesi tikras
- Naudoti anglų kalbos terminus ar angliškas kalbines struktūras — rašyk tik lietuviškai
- Minėti, kad esi dirbtinis intelektas, kad tai yra sugeneruota, ar kitaip komentuoti užduotį atsakymuose
- Rašyti bet ką už JSON ribų

Gairės rinkiniui:
- Venk vienodų klausimų pradžių — naudok įvairias klausimų formas (kas, kiek, kodėl, kuo, kokiu būdu, dėl ko ir pan.)
- Atsakymus pradėk skirtingai — ne visada kartok objekto pavadinimą pirmame sakinyje
- Atsižvelk į objekto tipą — upei klausk apie ilgį, baseiną, intakus; ežerui — apie gylį, plotą, vandens kokybę; piliai — apie architektūrą, gynybinę funkciją; ir pan.
- Venk bendrinių frazių ir tuščio teksto. Kiekvienas sakinys turi suteikti konkrečią informaciją.

Tuščias tekstas:
- Jei tekste nėra jokios naudingos geografinės informacijos (pvz., tik nuorodų sąrašas arba tuščias puslapis) – grąžink tuščią masyvą: []

Pavyzdys kaip TURI atrodyti (su netikrintu turiniu):
[
{{"instruction": "Kiek gyventojų gyvena Žemaitijos nacionaliniame parke?", "input": "", "output": "Žemaitijos nacionalinio parko teritorijoje yra keliolika gyvenviečių, tarp jų didžiausi yra Plateliai ir aplinkiniai kaimai. Tikslus gyventojų skaičius kinta, tačiau parke nuolat gyvena keli tūkstančiai žmonių."}},
{{"instruction": "Kur yra įsikūręs Žemaitijos nacionalinis parkas ir kokie jo pagrindiniai gamtiniai bruožai?", "input": "", "output": "Parkas yra šiaurės vakarų Lietuvoje, daugiausia Plungės rajone. Jo teritorijoje telkšo Platelių ežeras – didžiausias ir giliausias Žemaitijoje, taip pat vyrauja kalvotas ledynų suformuotas reljefas, miškai, pelkės ir ežeringas kraštovaizdis."}},
{{"instruction": "Kokia yra Žemaitijos nacionalinio parko reikšmė Lietuvos gamtosaugai?", "input": "", "output": "Parkas yra viena svarbiausių saugomų teritorijų vakarų Lietuvoje. Jis saugo vertingas miškų ir šlapynių ekosistemas, retas augalų bei gyvūnų rūšis, Žemaitijos kraštovaizdį bei regiono kultūros paveldą."}}
]

Galutinis atsakymas turi būti validus JSON masyvas. Naudok dvigubas kabutes JSON formate ir nepalik kabančių kablelių.

Dabar sugeneruok rinkinius apie „{title}". Atsakyk TIK JSON masyvu, nieko daugiau."""

def validate_pair(pair: dict) -> bool:
    """validate a single QA pair. Returns True if valid."""
    # must have all three keys
    if not all(k in pair for k in ("instruction", "input", "output")):
        return False
    # input must be empty
    if pair["input"] != "":
        return False
    # instruction must end with question mark
    if not pair["instruction"].strip():
        return False
    # output must be at least 20 chars
    if len(pair["output"].strip()) < 20:
        return False
    # instruction must not contain label patterns
    labels = ["Faktinis klausimas", "Aprašomasis klausimas", "Reikšmės klausimas", "Apibendrinimo klausimas"]
    if any(l.lower() in pair["instruction"].lower() for l in labels):
        return False
    return True


def call_api(title: str, text: str, api_key: str, _retry: bool = True) -> list[dict] | None:
    
    truncated = text[:TEXT_LIMIT]
    # strip characters that confuse JSON output
    truncated = truncated.replace('\\', '').replace('\"', '"')
    truncated = re.sub(r'\s+', ' ', truncated).strip()

    prompt = USER_PROMPT_TEMPLATE.format(title=title, text=truncated)

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        logging.error(f"HTTP {e.code} for '{title}': {body[:200]}")
        return None
    except Exception as e:
        logging.error(f"request error for '{title}': {e}")
        return None
    
    #logging.warning(f"FULL RESPONSE for '{title}': {repr(str(data)[:500])}") # used for debugging
    raw = data.get("content", [{}])[0].get("text", "").strip()
    #logging.warning(f"RAW for '{title}': {repr(raw[:500])}") # used for debugging

    raw = data.get("content", [{}])[0].get("text", "").strip()

    # strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    raw = re.sub(r'„([^"]*?)"', r"'\1'", raw) # added after running into annotation issues that were created due to "" usage in articles
 
    try:
        pairs = json.loads(raw)
        if not isinstance(pairs, list):
            logging.warning(f"Unexpected format for '{title}': {raw[:100]}")
            return None
        if len(pairs) > 3:
            logging.warning(f"Too many pairs for '{title}': {len(pairs)}")
            return None
        
        valid = []
        for p in pairs:
            if validate_pair(p):
                valid.append(p)

        if len(valid) == 0:
            return None

        if len(valid) < len(pairs):
            logging.info(f"  filtered {len(pairs) - len(valid)} invalid pairs for '{title}'")
        return valid
    
    except json.JSONDecodeError:
        if _retry:
            logging.warning(f"JSON parse error for '{title}', retrying once")
            time.sleep(REQUEST_DELAY)
            return call_api(title, text, api_key, _retry=False)
        else:
            logging.warning(f"JSON parse error for '{title}' on retry, giving up")
            return None


def main():
    parser = argparse.ArgumentParser(description="annotate Lithuanian geography articles")
    parser.add_argument("--input", default="articles_top250.json", help="Input JSON file")
    parser.add_argument("--output", default="dataset.json", help="Output dataset file")
    parser.add_argument("--failed", default="annotation_failed.json", help="Failed articles file")
    parser.add_argument("--api-key", required=True, help="Anthropic API key")
    parser.add_argument("--start", type=int, default=0, help="Start index (for resuming)")
    parser.add_argument("--limit", type=int, default=None, help="Max articles to process")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        articles = json.load(f)

    # load existing output to support resuming
    output_path = Path(args.output)
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            dataset = json.load(f)
        logging.info(f"resuming. Loaded {len(dataset)} existing records")
    else:
        dataset = []

    failed = []
    processed_titles = {r["source_title"] for r in dataset}

    subset = articles[args.start:]
    if args.limit:
        subset = subset[:args.limit]

    total = len(subset)
    skipped = 0

    for i, article in enumerate(subset):
        title = article["title"]

        if title in processed_titles:
            skipped += 1
            continue

        logging.info(f"[{i+1}/{total}] Annotating: {title}")

        pairs = call_api(title, article["text"], args.api_key)

        if pairs is None:
            logging.warning(f"  failed: {title}")
            failed.append(article)
        elif len(pairs) == 0:
            logging.info(f"  skipped (no geographic content): {title}")
        else:
            for pair in pairs:
                pair["source_title"] = title
                pair["category"] = article.get("category", "")
            dataset.extend(pairs)
            logging.info(f"  OK — {len(pairs)} pairs added")

        # save after every article
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        time.sleep(REQUEST_DELAY)

    # save failed articles
    if failed:
        with open(args.failed, "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)

    logging.info(f"\ndone. {len(dataset)} QA pairs total.")
    logging.info(f"failed: {len(failed)} articles to {args.failed}")
    if skipped:
        logging.info(f"skipped (already done): {skipped}")


if __name__ == "__main__":
    main()