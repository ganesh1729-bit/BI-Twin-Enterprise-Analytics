import streamlit as st
import pandas as pd
import sqlite3
import json
import ollama

st.set_page_config(page_title="BI Twin Intelligence", layout="wide")

# --- CUSTOM CSS (Clean, Professional Light Theme) ---
st.markdown("""
<style>
    .glass-card {
        background: #F8F9FA;
        border-left: 5px solid #2ECC71;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton>button { background-color: #2ECC71; color: white; font-weight: bold; }
    .stButton>button:hover { background-color: #27AE60; }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE CHAT STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

@st.cache_data
def load_context():
    with open('semantic_contract.json', 'r') as f: contract = json.load(f)
    with open('marketing_telemetry.json', 'r') as f: logs = json.load(f)
    with open('SOP_playbook.txt', 'r') as f: sops = f.read()
    return contract, logs, sops

contract, marketing_logs, sop_data = load_context()

@st.cache_data
def process_pvm_data():
    conn = sqlite3.connect('enterprise_data.db')
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['region', 'date'])
    cfg = contract['kpis']['revenue']
    processed_groups = []
    
    for region, group in df.groupby('region'):
        group = group.copy()
        group['base_price'] = group['price'].rolling(14, min_periods=1).mean().shift(1).fillna(group['price'])
        group['base_vol'] = group['volume'].rolling(14, min_periods=1).mean().shift(1).fillna(group['volume'])
        group['base_rev'] = group['revenue'].rolling(14, min_periods=1).mean().shift(1).fillna(group['revenue'])
        group['rev_std'] = group['revenue'].rolling(14, min_periods=1).std().shift(1).fillna(0)
        group['history_days'] = range(1, len(group) + 1)
        group['is_mature'] = group['history_days'] >= cfg['sparse_definition_days']
        
        group['mature_anomaly'] = group['is_mature'] & (group['revenue'] < (group['base_rev'] - (cfg['mature_threshold_sigma'] * group['rev_std'])))
        group['sparse_anomaly'] = (~group['is_mature']) & (group['revenue'] < (group['base_rev'] * (1 - cfg['sparse_threshold_percent'])))
        group['is_anomaly'] = group['mature_anomaly'] | group['sparse_anomaly']
        
        group['price_effect'] = (group['price'] - group['base_price']) * group['volume']
        group['volume_effect'] = (group['volume'] - group['base_vol']) * group['base_price']
        processed_groups.append(group)
        
    return pd.concat(processed_groups, ignore_index=True)

df = process_pvm_data()

# --- SIDEBAR ---
st.sidebar.title("🔐 Governance")
active_persona = st.sidebar.selectbox("Active Persona (RBAC)", list(contract['rbac'].keys()))
is_analyst = not contract['rbac'][active_persona]['block_raw_data']

# --- NEW PROFESSIONAL HEADER ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    # Pulls directly from your GitHub to guarantee it works
    st.image("https://raw.githubusercontent.com/ganesh1729-bit/BI-Twin-Enterprise-Analytics/main/BI%20twin.png", width=120)
with col_title:
    st.title("BI Twin: Enterprise KPI Intelligence")
    st.markdown("Automated Root-Cause Analytics & SOP Routing")

selected_region = st.selectbox("Select Business Unit (Region)", ["North (Multi-Factor)", "South (Sparse History)", "East (Low-Confidence/Abstain)"])
region_df = df[df['region'] == selected_region.split(" ")[0]].set_index('date')

# --- MULTI-PARAMETER GRAPHS (Tabs) ---
st.markdown("### 📊 Operational Telemetry")
tab1, tab2, tab3 = st.tabs(["💰 Revenue vs Baseline", "📦 Volume Sold", "🏷️ Unit Price Trend"])

with tab1:
    st.line_chart(region_df[['revenue', 'base_rev']])
with tab2:
    st.area_chart(region_df['volume'])
with tab3:
    st.line_chart(region_df['price'])

# --- AI TRIGGER ---
anomalies = region_df[region_df['is_anomaly'] == True]

if not anomalies.empty:
    latest = anomalies.iloc[-1]
    a_date = latest.name.strftime('%Y-%m-%d')
    st.error(f"🚨 Anomaly Detected: {selected_region.split(' ')[0]} Region on {a_date}")
    
    if st.button("Run BI Twin Deterministic AI"):
        region_logs = [log for log in marketing_logs if log['date'] == a_date and log['region'] == selected_region.split(" ")[0]]
        pvm_facts = f"Price Effect: ${latest['price_effect']:,.2f} | Volume Effect: ${latest['volume_effect']:,.2f}"
        
        prompt = f"""
        System: You are a rigid enterprise BI API. 
        Date: {a_date}. Math: {pvm_facts}. Logs: {json.dumps(region_logs)}. SOPs: {sop_data}
        
        STRICT INSTRUCTIONS:
        If logs conflict with math, output EXACTLY: "CONFIDENCE LOW: Abstaining."
        Otherwise, output EXACTLY 3 bullet points. 
        
        CRITICAL RULE: DO NOT write any introductory or concluding text (e.g., do not say "Based on the data" or "Here is the output"). Start immediately with the first bullet point.
        
        * **Root Cause:** [1 sentence explanation]
        * **Evidence:** [1 sentence citing logs]
        * **Action:** [Exact SOP action and Owner]
        """
        
        try:
            with st.spinner("BI Twin synthesizing math with telemetry..."):
                response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}])
            
            st.session_state.initial_analysis = response['message']['content']
            st.session_state.context_memory = f"Math: {pvm_facts} | Logs: {json.dumps(region_logs)}"
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ AI Connection Error. Please ensure Ollama is running in the background. (Error: {e})")

    # Render Analysis
    if "initial_analysis" in st.session_state:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        if not is_analyst:
            st.success("### 📋 Executive Action Brief")
            st.markdown(st.session_state.initial_analysis)
        else:
            st.info("### 🔬 Analyst Lineage & Driver Proof")
            col1, col2, col3 = st.columns(3)
            col1.metric("Expected Revenue", f"${latest['base_rev']:,.0f}")
            col2.metric("Price Impact", f"${latest['price_effect']:,.0f}")
            col3.metric("Volume Impact", f"${latest['volume_effect']:,.0f}")
            with st.expander("🔍 View Raw Telemetry Logs (JSON)"):
                st.json([log for log in marketing_logs if log['date'] == a_date and log['region'] == selected_region.split(" ")[0]])
            st.write("**🤖 BI Twin Synthesis:**")
            st.markdown(st.session_state.initial_analysis)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # --- FIXED CHATBOT ---
        st.markdown("### 💬 Human-in-the-Loop Analyst Chat")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        if user_q := st.chat_input("Ask BI Twin about driver impacts..."):
            st.session_state.chat_history.append({"role": "user", "content": user_q})
            with st.chat_message("user"): st.markdown(user_q)
            
            with st.chat_message("ai"):
                chat_prompt = f"Context: {st.session_state.context_memory}. The user asks: {user_q}. Answer concisely."
                try:
                    chat_resp = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': chat_prompt}])
                    st.markdown(chat_resp['message']['content'])
                    st.session_state.chat_history.append({"role": "ai", "content": chat_resp['message']['content']})
                except Exception:
                    st.error("AI is currently overloaded. Please try again.")