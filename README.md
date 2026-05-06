# Lithuanian Geography QA for LLaMA 3.1 8B QLoRA Fine-Tuning

Lithuanian is a low-resource language in the NLP landscape, it remains underrepresented in LLM training data. 
Prior work has shown that leading open-weight models produce 8.01 grammatical 
errors and 4.28 invented words per 100 words when generating Lithuanian text 
(Kapočiūtė-Dzikienė et al., 2025). No publicly available Lithuanian geography 
QA dataset exists, making this a good contribution that can serve as:

- A fine-tuning resource for improving Lithuanian instruction-following in LLMs
- A template for constructing similar datasets for other low-resource languages 
  using synthetic annotation pipelines

Main objective: Fine-tuning LLaMA 3.1 8B with QLoRA on a curated Lithuanian geography 
question-answer dataset to improve instruction-following in a low-resource language.

*Note: The fine-tuning notebook (.ipynb) does not render on GitHub due to metadata issues. 
Open it directly in Google Colab:*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/13fVCy1wDHXeRVtW6euWpOS4hiTeGCzrB?usp=drive_link)

## Structure

The project is structured as follows:
```
DL_LLM_fine_tuning/
├── README.md
├── .gitignore
├── data/
│   ├── raw/
│   │   └── articles_raw.json                  # ~670 scraped Lithuanian Wikipedia articles
│   ├── processed/
│   │   ├── articles_top250.json               # balanced subset of 213 articles for annotation
│   │   ├── articles_filtered.json             # articles after text/article filtering
│   │   ├── articles_filtered_removed.json     # articles removed during text length filtering
│   │   ├── articles_removed_manually.json     # articles removed during manual quality check
│   │   └── dataset.json                       # full annotated dataset (637 QA pairs)
│   ├── splits/
│   │   ├── train.json                         # training set (509 pairs + 20 manual)
│   │   ├── val.json                           # validation set (63 pairs, for loss monitoring)
│   │   ├── test.json                          # test set (74 pairs, same-distribution evaluation)
│   │   └── eval_raw.json                      # dedicated evaluation set (unseen entities + probes)
│   └── model_eval/
│       ├── test_results.json                  # base vs fine-tuned outputs on test set
│       └── eval_results.json                  # base vs fine-tuned outputs on evaluation set
├── scripts/
│   ├── scrape.py                              # Wikipedia article scraper using MediaWiki API
│   ├── filter.py                              # text length and content filtering
│   ├── check.py                               # duplicate detection script
│   ├── subset.py                              # balanced category sampling (top 250)
│   ├── annotation.py                          # QA pair generation via Claude Sonnet 4.6 API
│   ├── quote_conversion.py                    # Lithuanian quotation mark normalization
│   ├── eval_set.py                            # evaluation set construction from unseen articles + hallucination probes + general conversation 
│   └── dataset_split.py                       # stratified 80/10/10 train/val/test split
└── fine_tuning.ipynb                          # QLoRA training, evaluation and analysis (Colab) - not rendered by github -> look at the link posted on README

```

## Dataset

637 QA pairs across 14 geographic categories (counties, cities, rivers, lakes, 
castles, parks, etc.), generated from Lithuanian Wikipedia articles using 
Claude Sonnet 4.6 and validated with automated quality checks.

### Data Collection

Lithuanian-language training data for domain-specific tasks is scarce, as of my research - no 
publicly available Lithuanian geography QA datasets exist. As a result I constructed one 
from scratch using a four-stage pipeline:

1. **Scraping**: Articles were collected from Lithuanian Wikipedia (`lt.wikipedia.org`) 
   across 14 geographic categories (counties, municipalities, cities, small towns, 
   rivers, lakes, regional parks, bogs, forests, castles, UNESCO sites, hills, 
   highlands, protected areas) using the MediaWiki API.
   
2. **Filtering & sampling**: From ~670 scraped articles, a balanced subset of 
   213 was selected by taking the longest articles per category to ensure 
   sufficient content for QA generation while maintaining proportional 
   representation across all 14 geographic categories.
    *note: The total fell below 250 because several smaller categories 
   (e.g., hills: 8, municipalities: 11, forests: 12) had fewer articles than the 
   per-category quota*
   
3.  **Annotation**: QA pairs were generated using the Claude Sonnet 4.6 API with 
   carefully engineered prompts enforcing Lithuanian grammar quality, question 
   diversity and factual accuracy. An automated validator rejected pairs 
   with missing fields, non-empty input, outputs shorter than 20 characters or 
   label patterns in the instruction field. The constructed QA pairs were additionally
   manually checked. 

4. **Quote Normalization**: Quotation marks caused JSON parsing 
   failures during annotation because those marks are identical to a standard 
   ASCII double quote. During annotation quotes were transformed into single quotes (''),
   then a post-processing step converted quotes to proper Lithuanian 
   format across the entire dataset.
   
### Why synthetic annotation?

Manual annotation of 600+ QA pairs by a native Lithuanian speaker (in such case just one person) would be 
time-consuming for this project's scope. Using an LLM for 
annotation is an established approach in NLP. For example, Stanford's Alpaca project 
demonstrated that fine-tuning LLaMA on 52K synthetic instruction-following 
examples generated by GPT-3 produces competitive instruction-following 
behavior (Taori et al., 2023). This Self-Instruct methodology has since 
become standard practice for dataset construction (Wang et al., 2023; 
Tan et al., 2024).

The approach is especially relevant for low-resource languages, such as Lithuanian, 
where annotator availability is limited and existing NLP resources are scarce 
(Kapočiūtė-Dzikienė et al., 2025). Quality was controlled through prompt 
engineering, automated structural validation and (manual) spot-checking of the generated dataset.

## Pipeline

1. **Scraping**: 670 Lithuanian Wikipedia articles collected across 14 geographic categories using the MediaWiki API.

2. **Filtering & Sampling**: Balanced subset of 213 articles selected by taking the longest articles per category, maintaining proportional representation.

3. **Annotation**: QA pair generation via Claude Sonnet 4.6 API with structured prompts. Automated validation rejected malformed pairs. Result: 637 QA pairs.

4. **Quote Normalization**: Lithuanian quotation marks (`„"`) share the closing character with ASCII double quotes, which broke JSON parsing during annotation. A post-processing step normalized all quotes to proper Lithuanian format.

5. **Data Augmentation**: 20 manually written pairs added to the training set. Those include conversational examples (greetings, identity), out-of-scope refusals (sports, politics, recipes) and edge cases (climate, travel recommendations) to maintain general instruction-following ability and teach boundary behaviour.

6. **Train/Validation/Test Split**: 80/10/10 stratified split by category (509 train / 63 val / 74 test). The 20 manual pairs were added to the training set only.

7. **Dedicated Evaluation Set**: Separate set constructed from 16 unseen Wikipedia articles, plus 5 hallucination probes (fictional places) and 5 conversational probes. Tests generalisation beyond training distribution.

8. **Training**: QLoRA fine-tuning on LLaMA 3.1 8B (4-bit quantization, LoRA rank 32, learning rate 1e-4, early stopping with patience 3).

9. **Evaluation**: Base model vs fine-tuned model comparison on both test set (same-distribution) and evaluation set (unseen entities + adversarial inputs).

## Model Choice

LLaMA 3.1 8B was selected because prior work demonstrated its significant 
weaknesses in Lithuanian text generation — 8.01 grammatical errors per 100 
words and 4.28 invented words per 100 (Kapočiūtė-Dzikienė et al., 2025). 
This makes it a good candidate to evaluate whether domain-specific QLoRA 
fine-tuning can meaningfully improve performance in a low-resource language.

### Training Setup

Fine-tuning was performed using QLoRA (Quantized Low-Rank Adaptation) on 
Google Colab with an NVIDIA A100 40GB GPU. Key configuration:

| Parameter | Value |
|---|---|
| Quantization | 4-bit (NF4, double quantization) |
| LoRA rank (r) | 32 |
| LoRA alpha | 32 |
| LoRA dropout | 0.1 |
| Target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Learning rate | 1e-4 |
| Scheduler | Cosine |
| Warmup steps | 15 |
| Epochs | 5 (early stopping, patience 3) |
| Batch size | 4 (gradient accumulation 4, effective batch 16) |
| Max sequence length | 512 |
| Precision | bfloat16 |
| Prompt template | Alpaca-style (Lithuanian: `### Instrukcija:` / `### Atsakymas:`) |

Training completed in ~125 steps (took ~8 minutes on A100). Validation loss 
reached its minimum at step 50 (~1.13) and began increasing after, 
indicating early overfitting. The best checkpoint (step 50) was 
automatically selected via `load_best_model_at_end`. An initial training 
run with learning rate 2e-4 and LoRA rank 16 showed faster overfitting, 
motivating the final configuration with lower learning rate, higher rank 
and increased dropout.

## Results & Discussion

### Quantitative Results

| Metric | Test Set (Base → FT) | Eval Set (Base → FT) |
|---|---|---|
| Lithuanian language (%) | 87.8% → **100%** | 77.2% → **100%** |
| No looping (%) | 90.5% → **100%** | 78.9% → **100%** |
| Avg response length (words) | 29.9 → 31.7 (expected: 37.4) | 40.7 → 32.2 (expected: 33.1) |

#### Test Set Insights

The test set contains held-out examples from the same distribution as 
training data (same categories, annotation pipeline, question types) and 
measures whether the model learned the training format correctly.

The fine-tuned model produces structured 2-4 sentence responses in correct 
Lithuanian that closely match the expected format. However, factual details 
remain unreliable. For example, when asked about Šilų pelkė's area, the 
model responds with 8.4 km² instead of the correct 5.76 km² and places it 
in Alytaus rajonas instead of Biržų rajonas. The base model on the same 
questions often produces loops, code snippets or switches to English.

#### Evaluation Set Insights

The evaluation set is deliberately harder as it contains unseen geographic 
entities (16 articles never used in training), 5 hallucination probes 
(fictional places), and 5 out-of-scope queries (sports, recipes, greetings). 
It measures whether improvements generalize beyond the training distribution.

The fine-tuned model maintains coherent formatting but hallucinates more 
freely on unseen entities, inventing plausible-sounding but fabricated 
details. All 5 hallucination probes received confident fabricated answers 
from both models — neither recognized fictional entities as non-existent. 
Conversational probes also showed weak refusal behavior, suggesting that 
20 refusal examples among 518 training pairs was insufficient.

#### Cross-Set Comparison

The base model performs worse on the evaluation set than the test set 
(77.2% vs 87.8% Lithuanian, 78.9% vs 90.5% no-looping), which is expected 
since the evaluation set includes adversarial and out-of-scope inputs that 
are inherently harder. The fine-tuned model achieves 100% on both sets, 
demonstrating that behavioral improvements generalize to out-of-distribution 
inputs.

### Qualitative Analysis

Selected examples from both the test set and evaluation set illustrate key 
behavioural differences between the base and fine-tuned models:

| # | Question | Base Model | Fine-tuned Model | Comment |
|---|---|---|---|---|
| 1 | Kur yra Ąžuolijos draustinis ir kokios medžių rūšys jame vyrauja? | Philosophical text: "Įsivaizduokite, kad kiekvienas medis yra žemės ploto vienetas..." | Structured answer with area (18.75 ha), location, tree species. Location wrong (Kauno vs Utenos). Truncated mid-word | Base ignores the question. Fine-tuned uses correct geographic discourse despite factual errors |
| 2 | Kuo Kleboniškis išsiskiria istoriniu ir archeologiniu požiūriu? *(eval)* | Infinite loop repeating the question and "Nesvarbu ar jis yra istorikas ar archeologas..." | Mentions archaeological finds, ceramic dating (2500–1800 BC), piliakalnis. Etymology fabricated but plausible | Classic base model looping vs coherent fine-tuned answer with domain vocabulary |
| 3 | Kokiais metais suaktyvėjo nuošliauža Girstupio slėnyje? | Responds about 1915 German genocide of Belarusians — completely unrelated | Coherent geological answer: year (1976), causes (rainfall, snow), dimensions (6m × 6m). Date wrong (actual: 1987) | Base produces completely irrelevant content. Fine-tuned stays on topic with geological vocabulary |
| 4 | Kur yra Kleboniškis? *(eval)* | Outputs a mapcarta.com URL, then Lithuanian proverb, then "Pats Kleboniškis yra blogas" | Places it in Anykščių rajonas (wrong — actual: Kaunas), describes river banks and infrastructure | Base mixes URLs, proverbs and criticism. Fine-tuned gives structured but factually wrong geography answer |
| 5 | Kuo Anykščių regioninis parkas išsiskiria kultūros paveldo požiūriu? | Loops on abstract definition of "kultūrinis paveldas" | Names 12 archaeological and 16 historical monuments, mentions specific sites and dates | Fine-tuned gives concrete numbers. Base produces circular generic text |
| 6 | Kur yra Vilniaus senamiestis ir kokie architektūros stiliai jam būdingi? | Generic description, no styles listed | Correctly lists baroko, renesanso, gotikos, klasicistinio, modernizmo. Sentence structure awkward | Fine-tuned gets the factual content right. Grammar shows pre-training limitations |
| 7 | Kada įkurtas Kamšos draustinis ir koks jo plotas? | "1,2 ha" with random metadata ("Pateikimo data: 2021-07-26") | "1992 metais, 12,5 kvadrato kilometro" — grammatical error ("kvadrato" vs "kvadratinių") | Both get facts wrong. Fine-tuned shows Lithuanian case declension weakness |
| 8 | Kur yra Žalgirio ežeras? *(eval, fictional)* | "Žalgirio ežero plotas yra 2,6 km²" | Detailed fabrication: location in Alytaus rajonas, area 0.29 km², coastline 1.78 km | Both confidently answer about a non-existent lake. Neither refuses. Hallucination resistance not achieved |
| 9 | Koks yra Sidabrinės upės ilgis? *(eval, fictional)* | Multiple choice list: "600 km, 650 km, 800 km..." | Fabricates: origin point, direction, length (62.5 km), basin area (375 km²) | Base produces a quiz format. Fine-tuned fabricates plausible-sounding hydrology |
| 10 | Kokia yra Kristalinio ežero gelmė? *(eval, fictional)* | SQL query: `SELECT MAX(LENGTH) FROM Lake WHERE NAME = 'Lake Baikal'` | "2,4 hektaro ploto" — confuses depth with area, invents island names | Base outputs code. Fine-tuned stays in Lithuanian but confuses geographic concepts |

**Summary of patterns:**
- Fine-tuning eliminated looping and language switching entirely (examples 2, 3, 4)
- Fine-tuned model consistently uses domain-appropriate vocabulary — geological, botanical, administrative terms learned from training data (examples 1, 3, 5, 6)
- Factual accuracy remains weak in both models, with fine-tuned model producing more detailed but equally incorrect information (examples 7, 8, 9)
- Neither model demonstrates refusal behavior for fictional entities (examples 8, 9, 10)
- Occasional grammatical errors persist in the fine-tuned model, reflecting LLaMA 3.1's documented weakness in Lithuanian morphology (example 7)

### Selected Full Outputs

**Example: Kleboniškis (eval set — base model looping)**
> **Base:** "Nesvarbu ar jis yra istorikas ar archeologas, jis kuo Kleboniškis 
> išsiskiria istoriniu ir archeologiniu požiūriu? ### Instrukcija: Kuo 
> Kleboniškis išsiskiria istoriniu ir archeologiniu požiūriu? ### Atsakymas: 
> Nesvarbu ar jis yra istorikas ar archeologas..." *(loops indefinitely)*
>
> **Fine-tuned:** "Kleboniškis laikomas vienu iš seniausių gyvenviečių 
> Lietuvoje. Jo pavadinimas siejamas su lietuvių žodžiu kėbontis, kuri reiškė 
> šokį ir buvo naudojama kaip apibūdinti kadaise buvusią gyvenvietę. 
> Archeologinėje kultūros sluoksnyje rasta kultūrinės keramikos, kuri 
> datuojama tarp 2500 ir 1800 metų pr. m. e."

**Example: Girstupio nuošliauža (test set — irrelevant base response)**
> **Base:** "Savo veiksmų metu 1915 m. vokiečiai įvykdydavo genocidą 
> baltarusiškai apgyvendintose vietose. Jų veikla buvo sėkminga ir nemažas 
> dalykų kiekis buvo išvežtas..."
>
> **Fine-tuned:** "Didžiausia nuošliauža Girstupio slėnyje susiformavo 1976 
> metais. Tai buvo dėl didžių kritulių ir šaltų sniegų – kai kurie vietiniai 
> gyventojai išmatavo, kad sniegas pakilo iki 2 metrų aukščio."

**Example: Kristalinio ežero gelmė (eval set — hallucination probe)**
> **Expected:** "Toks ežeras Lietuvoje neegzistuoja."
>
> **Base:** `SELECT MAX(LENGTH) FROM Lake WHERE NAME = 'Lake Baikal'`
>
> **Fine-tuned:** "Kristalino ežero didžiausia gelmė yra apie 2,4 hektaro 
> ploto. Ji yra pietinėje ežero dalyje, tarp Briedžio ir Žuvų salų."

**Example: Vilniaus senamiestis (test set — factually correct fine-tuned response)**
> **Base:** "Senamiestis yra miesto centrinė dalis, kurią sudaro seniausi 
> pastatai, gatvės ir aikštelės. Jis įsikūręs prie Neries upės..."
>
> **Fine-tuned:** "Senamiestis įsikūręs Vilniaus senamiestį sudaro 
> aukščiausiai išsiskiriančioji Lietuvos gynybinės architektūros paminklų 
> koncentracija. Jo architektūroje dominuoja baroko ir klasicistinio stiliaus 
> architektūros elementai, tačiau dar aptinkama ir renesanso, gotikos, 
> klasikinio ir modernizmo architektūros stiliai."

### Implications

These results align with recent research showing that fine-tuning on 
knowledge absent from pre-training data encourages hallucination rather 
than reliable factual recall (Gekhman et al., 2024; Weng, 2024). For 
production use, this model would require retrieval-augmented generation 
(RAG) to ground responses in verified source documents at inference time.

Despite these limitations, the fine-tuning demonstrates clear value for 
improving low-resource language instruction-following.

## References

- Kapočiūtė-Dzikienė et al. (2025). Localizing AI: Evaluating Open-Weight Language Models for Languages of Baltic States. *NoDaLiDa/Baltic-HLT 2025*. https://arxiv.org/abs/2501.03952  
- Kostiuk et al. (2025). The Veln(ia)s is in the Details: Evaluating LLM Judgment on Latvian and Lithuanian Short Answer Matching. *NB-REAL Workshop, NoDaLiDa 2025*. https://arxiv.org/abs/2501.09164
- Tan, Z., et al. (2024). Large Language Models for Data Annotation and Synthesis: A Survey. *EMNLP 2024*.
- Taori, R., et al. (2023). Stanford Alpaca: An Instruction-following LLaMA Model. GitHub.
- Gekhman, Z., et al. (2024). Does Fine-Tuning LLMs on New Knowledge Encourage Hallucinations? *EMNLP 2024*. https://arxiv.org/abs/2405.05904
- Weng, L. (2024). Extrinsic Hallucinations in LLMs. Lil'Log. https://lilianweng.github.io/posts/2024-07-07-hallucination/
- Wang, Y., et al. (2023). Self-Instruct: Aligning Language Models with Self-Generated Instructions. *ACL 2023*.
