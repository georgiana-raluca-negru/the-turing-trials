# Plan AI & LLM Engineer - The Turing Trials

## 1. Plan General (Simplu)
Obiectivul principal: Construirea "creierului" aplicației pentru orchestrarea procesului simulat (The Turing Trials) folosind LangChain și LangGraph.

1. **Configurarea Mediului și Structurii:**
   - Definirea structurii de directoare pentru agenți, stare și utilitare.
   - Integrarea LangChain și LangGraph pentru definirea fluxului logic și managementul stării.
2. **AI Clerk (Generatorul de Cazuri):**
   - Construirea unui agent care primește un scurt prompt (1-2 propoziții) și generează cazul (Crime, Charges) alături de un "Evidence Inventory" structurat în format JSON.
3. **Guardrails, Constrângeri & Modele de Date (Apărare & Acuzare):**
   - Crearea prompturilor stricte pentru agenții de apărare și acuzare.
   - Definirea modelelor de date (Pydantic) pentru Dovezi, Argumente și Contextul Cazului pentru a structura injectarea informației și a reduce drastic halucinațiile.
4. **AI Judge (Evaluatorul și Verdictul):**
   - Dezvoltarea logicii de evaluare rundă-cu-rundă pentru mecanicile vizuale de tip "Scales of Justice".
   - Generarea verdictului final și motivat pe baza istoricului de chat și a evaluărilor.

---

## 2. Plan Concret și Detaliat (Etapa Minimă Extinsă)
Această etapă se concentrează pe fundația sistemului AI: **Generarea cazului (AI Clerk), structurarea stării cu LangGraph, definirea Modelelor de Date de bază (Pydantic) și strategia de injectare a Contextului (pentru Gemini 1.5 Pro/Flash)**.

### Obiectivele Etapei Minime:
- **Structurarea arhitecturală:** Ierarhia de directoare pentru modulele AI (separarea stării, modelelor, agenților și grafului).
- **Definirea Modelelor de Bază (Pydantic):** Structurarea obiectelor `Evidence`, `CaseContext`, `Argument` pentru ca modelele AI să știe exact cum arată o dovadă validă.
- **Managementul Contextului (System Prompting pentru Gemini 1.5):** Stabilirea modului în care agenții primesc istoricul (chat history) și dovezile curente în fiecare rundă, astfel încât să se lege de realitate și de ce a zis oponentul.
- **Definirea Stării (State):** Crearea obiectului de stare pentru LangGraph.
- **Prototip AI Clerk:** Nodul funcțional care generează JSON-ul (caz + dovezi).

### Structura de Directoare Propusă:
```text
the-turing-trials/
├── ai_engine/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── llm_config.py        # Instanțierea modelului LLM (ex: ChatGoogleGenerativeAI)
│   ├── models/                  # [NOU] Modele de Date Pydantic
│   │   ├── __init__.py
│   │   └── schemas.py           # CaseSummary, Evidence, Argument
│   ├── state/
│   │   ├── __init__.py
│   │   └── match_state.py       # Definirea MatchState (TypedDict / Pydantic)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── ai_clerk.py          # Prompturi și funcția de generare a cazului
│   │   └── base_prompts.py      # [NOU] Template-uri de System Prompts (injectare context)
│   ├── graph/
│   │   ├── __init__.py
│   │   └── workflow.py          # Noduri, muchii (edges) și compilarea grafului
│   └── utils/
│       ├── __init__.py
│       └── parsers.py           # Parsere pentru extragerea/validarea JSON-ului
```

### 3. Modele de Date de Bază (Schemas) & Context pentru AI
Pentru a preveni halucinațiile, LLM-ul (mai ales în arhitecturile moderne precum Gemini 1.5 Pro/Flash) funcționează cel mai bine când **input-ul este puternic structurat** și **output-ul este validat**. Vom folosi `Pydantic`.

#### Modelele de Date Necesare (`models/schemas.py`):
1. **`Evidence`**:
   - `id`: string (ex: "EVD-001")
   - `title`: string
   - `description`: string
   - `type`: string (ex: "Document", "Testimony", "Physical")
   - `is_used`: boolean (pentru a ști dacă a fost deja folosită în discuție)
2. **`CaseContext`**:
   - `crime`: string
   - `charges`: list[string]
   - `background_story`: string
3. **`Argument`**:
   - `speaker`: string ("Prosecutor" / "Defense" / "Judge")
   - `text`: string (textul efectiv rostit)
   - `attached_evidence_ids`: list[string] (legătura fizică cu dovezile folosite)

#### Strategia de Injectare a Contextului (System Prompting):
Pentru a evita halucinațiile într-un thread, LLM-ul (Apărarea/Acuzarea) nu trebuie lăsat pur și simplu să "vorbească". La fiecare rând al său, va primi un System Message care este recompilat dinamic:

**Structura propusă pentru Prompt-ul la fiecare rând (pentru Gemini 1.5):**
1. **Rolul (System Directive):** "Ești Avocatul Apărării în cazul [Nume Caz]. Scopul tău este să dărâmi argumentele Procurorului."
2. **Constrângerea Absolută (The Guardrail):** "IMPORTANT: NU INVENTA DOVEZI. Trebuie să îți bazezi afirmațiile STRICT pe următoarea listă de dovezi disponibile."
3. **Injectarea Datelor Structurate (Variabile):**
   - `<Case_Summary>`: Conținutul din modelul `CaseContext`.
   - `<Available_Evidence>`: O listă JSON a obiectelor `Evidence` (doar cele `is_used=False` sau toate, marcate corespunzător).
4. **Istoricul Discuției (Message History):** Se transmit ca o listă de obiecte LangChain de tip `HumanMessage` și `AIMessage`. Argumentul proaspăt al adversarului va fi ultimul mesaj.
5. **Output Așteptat:** I se va cere să returneze un format structurat (ex: folosind `.with_structured_output(Argument)` din LangChain) prin care să ofere textul discursului său + lista de `Evidence IDs` pe care tocmai le-a invocat.

---

### 4. Structura JSON pentru Integrarea cu LangGraph (Starea Meciului)
Mai jos este structura standardizată de Input/Output (ceea ce frontend-ul sau backend-ul trimite către și primește de la AI Engine prin intermediul LangGraph). Aceasta reflectă întocmai `MatchState` definit anterior.

```json
{
  "user_prompt": "Un caz de furt de identitate informatică la o bancă...",
  "case_summary": {
    "crime": "Furt de identitate și fraudă financiară",
    "charges": [
      "Acces ilegal la un sistem informatic",
      "Frauda bancară"
    ],
    "background_story": "Inculpatul susține că laptopul său a fost controlat de la distanță prin RDP."
  },
  "defense_evidence": [
    {
      "id": "EVD-DEF-001",
      "title": "Log-uri RDP",
      "description": "Un fișier .txt care arată o conexiune de intrare de pe un IP din afara țării la ora faptei.",
      "type": "Document",
      "is_used": false
    }
  ],
  "prosecution_evidence": [
    {
      "id": "EVD-PRO-001",
      "title": "Istoric Căutări",
      "description": "Istoricul din browser arată că acuzatul a căutat 'cum să ștergi logurile RDP' cu o zi înainte.",
      "type": "Document",
      "is_used": false
    }
  ],
  "messages": [
    {
      "speaker": "Prosecutor",
      "text": "Inculpatul a încercat să își șteargă urmele, așa cum se vede în istoricul de căutări.",
      "attached_evidence_ids": ["EVD-PRO-001"]
    }
  ]
}
```

### 5. Strategia de Testare a Etapei Minime
Ce se va întâmpla în testul izolat pentru `ai_clerk` (`test_run.py`):
1. **Input-ul:** Construim un `MatchState` inițial care conține doar cheia `user_prompt` (ex: "Un jaf la muzeu...").
2. **Execuția Grafului:** LangGraph rulează nodul `ai_clerk`.
3. **Apelarea LLM-ului:** Se face request către model (Minimax/Gemini) cerându-i-se un JSON care respectă Pydantic schema pentru `CaseFile`. (Generarea textului se face strict în background sub forma de tokeni JSON).
4. **Validarea Pydantic:** Se verifică automat dacă modelul a răspuns corect și a completat listele de dovezi și summary-ul cazului.
5. **Output (Text):** Nu se generează o "conversație" sau un text liber în această etapă. Textul generat de scriptul de test este pur și simplu un afișaj (print) în consolă al dicționarului Python (datele JSON traduse) pentru a ne confirma vizual că AI-ul a scos dovezi coerente și datele cazului.

### Etapele de Lucru (Actualizate):
1. Definirea Modelelor Pydantic (`schemas.py`).
2. Definirea Stării (`match_state.py` care va conține o listă de `Argument` și dicționare de `Evidence`).
3. Configurarea modelului LLM (pentru Minimax/Gemini via endpoint compatibil).
4. Construirea `ai_clerk` cu `with_structured_output` bazat pe modelele definite mai sus.
5. Compilarea grafului (`workflow.py`).
6. Definirea structurii standard JSON de stare (adăugată în plan).
7. Testarea izolată a AI Clerk (fără generare excesivă de apeluri API).