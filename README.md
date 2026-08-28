# 🟩 BI Twin: Enterprise KPI Intelligence-to-Action

**BI Twin** is a privacy-first, variance-triggered analytics engine designed to automate root-cause analysis for enterprise KPIs. Traditional dashboards show *that* a metric dropped; BI Twin deterministically calculates *why*, retrieves relevant unstructured telemetry, and uses a local offline LLM to route the incident to the correct Standard Operating Procedure (SOP).

##  Architecture: The 3-Layer Engine

To address the real-world complexities of LLM economics, data privacy, and AI hallucinations, BI Twin strictly separates mathematical truth from linguistic synthesis.

1. **Layer 1: Deterministic Multi-Factor Math (Non-LLM)**
   - Queries heterogeneous structured data (SQLite, CSV) and calculates dynamic baselines.
   - **Price-Volume-Mix (PVM) Decomposition:** Mathematically isolates revenue variance into exact dollar amounts attributed to pricing shifts vs. volume drop-offs before any AI is invoked.
   - **Sparse History Fallback:** Dynamically switches from 14-day rolling $\sigma$ to a category-relative variance threshold for newly launched products (<14 days history).

2. **Layer 2: Context Retrieval & Governance (RAG)**
   - Governed by a strict `semantic_contract.json` that manages metric lineage, refresh cadences, and Field-Level Role-Based Access Control (RBAC).
   - Extracts temporally and regionally relevant unstructured text from company data lakes (JSON marketing/server telemetry).

3. **Layer 3: Local LLM Semantic Router**
   - A locally hosted **Meta Llama 3 (8B)** acts exclusively as a semantic router. 
   - **Zero-Hallucination Prompting:** The AI is fed pre-calculated PVM facts and raw logs. If the logs do not explain the math, it programmatically triggers an **Abstention Protocol** (Low-Confidence).
   - **Data Privacy & Cost:** Runs 100% offline. Zero sensitive data leaves the enterprise environment. Compute cost: $0.00.

##  Hackathon Scenarios Demonstrated

* **Multi-Factor Interaction (North Region):** Demonstrates PVM decomposition proving a crash was caused by *both* price cuts and ad drop-offs.
* **Cold Start / Sparse History (South Region):** Proves the system dynamically handles new product launches without breaking rolling statistical math.
* **Low-Confidence Abstention (East Region):** When mathematical variance spikes but telemetry shows normal activity, the LLM refuses to guess and escalates to a human analyst.
* **Human-in-the-Loop:** Features an interactive chat interface allowing analysts to query the active data context natively within the dashboard.

## Tech Stack & UI
* **Frontend:** Streamlit (Python) with custom glassmorphism styling.
* **Data Engine:** Pandas, SQLite, JSON, CSV (Heterogeneous Data Matrix).
* **AI Engine:** Ollama (Meta Llama 3 - 8B).

## 💻 Deployment & Local Execution

1. Install [Ollama](https://ollama.com/) and pull the local model:
   ```bash
   ollama run llama3

Install Python dependencies:

   pip install streamlit pandas ollama

Generate the synthetic multi-source enterprise dataset:

   python generate_enterprise_data.py

Launch the BI Twin workspace:

  python -m streamlit run app.py

