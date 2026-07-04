# Financial Analysis Agent

AI agentas finansiniams klausimams atsakyti, kuris naudoja realius rinkos duomenis ir Claude AI.

---

## Ką jis daro?

Užduodi klausimą apie akcijas, įmonių finansus ar valiutas — agentas pats pasirenka reikiamus įrankius, paima duomenis iš Yahoo Finance ir pateikia atsakymą su įvertinimu.

**Pavyzdžiai:**
- `What is Apple's net profit margin?`
- `Compare the debt levels of AAPL and TSLA`
- `Assess the financial risk of Goldman Sachs`
- `Convert SEB bank's revenue from USD to EUR`

---

## Įrankiai

| Įrankis | Ką daro |
|---|---|
| `query_financials` | Paima finansinius duomenis (revenue, debt, EBITDA...) iš Yahoo Finance |
| `calculate` | Skaičiuoja finansinius rodiklius (maržos, santykiai) |
| `get_exchange_rate` | Valiutų kursai (USD, EUR, GBP, SEK, DKK) |
| `summarize_risk` | Įvertina įmonės finansinę riziką (0–100 balas) |
| `search_knowledge_base` | Semantinė paieška anksčiau gautuose finansiniuose duomenyse (vector DB) |

---

## Sąranka

**1. Reikalavimai**

- Python 3.9+
- Anthropic API raktas → [console.anthropic.com](https://console.anthropic.com)

**2. Įdiek priklausomybes**

```bash
pip3 install anthropic yfinance fastapi uvicorn chromadb sentence-transformers
```

**3. Pridėk API raktą**

Atsidaryk `.env` failą ir įklijuok savo raktą:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Paleidimas

```bash
python3 main.py
```

**Kiti režimai:**

```bash
# Vienas klausimas
python3 main.py --query "What is Apple's profit margin?"

# Demo — 4 paruošti klausimai
python3 main.py --demo

# Rodyti mąstymo žingsnius
python3 main.py --trace
```

---

## HTTP API (FastAPI)

```bash
uvicorn api:app --reload
```

Interaktyvi dokumentacija: [http://localhost:8000/docs](http://localhost:8000/docs)

| Endpoint | Metodas | Ką daro |
|---|---|---|
| `/query` | POST | Užduoda klausimą agentui (`{"query": "...", "session_id": "..."}`) |
| `/reset` | POST | Išvalo sesijos pokalbio atmintį |
| `/stats/{session_id}` | GET | Atminties statistika konkrečiai sesijai |
| `/tools` | GET | Agento įrankių sąrašas |
| `/search` | POST | Tiesioginė semantinė paieška vector DB (be LLM) |
| `/health` | GET | Health check |

`session_id` leidžia keliems vartotojams naudotis API vienu metu, kiekvienam turint atskirą pokalbio atmintį (numatytoji reikšmė: `"default"`).

---

## Komandos pokalbio metu

| Komanda | Ką daro |
|---|---|
| `/reset` | Išvalo pokalbio atmintį |
| `/stats` | Rodo atminties statistiką |
| `/trace` | Įjungia / išjungia mąstymo žingsnių rodymą |
| `/tools` | Išvardina galimus įrankius |
| `/help` | Rodo komandų sąrašą |
| `/quit` | Išeina |

---

## Projekto struktūra

```
├── main.py          # Paleidimas ir terminalo sąsaja
├── api.py           # FastAPI HTTP sąsaja
├── agent.py         # Pagrindinis agento ciklas (ReAct)
├── tools.py         # Finansiniai įrankiai
├── memory.py        # Pokalbio atmintis
├── guardrails.py    # Įvesties ir išvesties apsauga
├── vectorstore.py   # Vector DB (chromadb) finansinių duomenų saugojimui/paieškai
├── chroma_data/     # Vector DB duomenys (sukuriama automatiškai)
└── .env             # API raktas
```

---

## Apsaugos sistema

Agentas turi dvipusę apsaugą:

- **Prieš atsakant** — blokuoja draudžiamus klausimus (insider trading, pinigų plovimas ir pan.)
- **Po atsakymo** — įvertina ar skaičiai kyla iš realių duomenų, ne sugalvoti. Rodo haliucinacijos riziką: `low` / `medium` / `high`
