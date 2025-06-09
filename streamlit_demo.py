# Streamlit front‑end – single free‑text query
# ===========================================
# One input box where the user types a natural‑language request such as:
#   "I am 62, M, I have diabetes; find me providers and plans in San Francisco, CA."
# The app forwards that prompt to a Databricks Mosaic AI serving endpoint and
# renders the response.  Hard‑coded PAT & URL for quick demos.

# 1️⃣  Install (if not already in the cluster env)
# MAGIC %pip install --quiet streamlit requests
# MAGIC dbutils.library.restartPython()

# 2️⃣  Hard‑coded config  ⚠️ DEMO ONLY – do not commit PATs
TOKEN = "dapi13cb39fc97ca5190a9e63bbdb090a399"  # ← replace
ENDPOINT_URL = (
    "https://dbc-88a06358-5707.cloud.databricks.com/"
    "serving-endpoints/databricks-meta-llama-3-1-8b-instruct/invocations"
)

import streamlit as st, json, re

# --- 1. Hard‑coded sample response ------------------------------------------
SAMPLE_JSON = {
    "id": "chatcmpl_a70c8cd7-6343-4b6e-b966-05ecb5ec5b7c",
    "object": "chat.completion",
    "created": 1749500570,
    "model": "meta-llama-3.1-8b-instruct-110524",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Based on the user's profile and the available plans, I recommend the following top 3 plans:\n\n**Recommendation 1: Humana Gold Plus H0028-011 (HMO)**\n\nThis plan is a good fit for the user because it covers \"Chronic Lung Failure,\" which matches their health condition. Additionally, the plan has a premium cost of $0.0, making it a cost-effective option. While there is no overall star rating provided, this plan is a great choice for those looking for a basic, no-fuss plan that covers their chronic condition.\n\n**Recommendation 2: UnitedHealthcare Dual Complete (HMO SNP)**\n\nThis plan is a good fit for the user because it also covers \"Chronic Lung Failure.\" The plan's premium cost is $50.6, which is a higher cost compared to the previous plan. However, this plan offers more comprehensive coverage, including Part D prescription coverage. If the user needs more comprehensive coverage, this plan is a good option, despite the higher premium cost.\n\n**Recommendation \nIn summary, the Humana Gold Plus H0028-011 (HMO) is a great choice for those looking for a basic, no-fuss plan that covers their chronic condition. The UnitedHealthcare Dual Complete (HMO SNP) is a more comprehensive option with Part D coverage but at a higher premium cost."
            },
            "finish_reason": "stop",
            "logprobs": None
        }
    ],
    "usage": {"prompt_tokens": 382, "completion_tokens": 329, "total_tokens": 711}
}

# --- 2. Parsing helper -------------------------------------------------------

def parse_llm_content(content: str):
    plans, cur = [], None
    for line in content.splitlines():
        m = re.match(r"\*\*Recommendation\s+\d+:\s+(.*?)\*\*", line.strip())
        if m:
            if cur:
                plans.append(cur)
            cur = {"title": m.group(1).strip(), "body": ""}
        elif cur is not None:
            cur["body"] += line + "\n"
    if cur:
        plans.append(cur)
    return plans or [{"title": "Response", "body": content}]

# --- 3. UI -------------------------------------------------------------------

st.set_page_config(page_title="Neu Plan Recommender (Mock)", layout="centered")

st.markdown(
    "<h1 style='text-align:center; font-family:Helvetica,Arial,sans-serif; font-weight:800; "
    "letter-spacing:1px; color:#0A84FF;'>Neu • Health‑Plan Recommender (Mock)</h1>",
    unsafe_allow_html=True,
)

user_prompt = st.text_input("Prompt", "", placeholder="Type anything…", label_visibility="collapsed")
show_json   = st.checkbox("Show raw JSON")

if st.button("Show Recommendations"):
    # Ignore user_prompt; use SAMPLE_JSON every time
    content = SAMPLE_JSON["choices"][0]["message"]["content"]

    st.markdown("---")
    st.subheader("Recommended plans & providers")

    for plan in parse_llm_content(content):
        with st.expander(plan["title"], expanded=True):
            st.write(plan["body"].strip())

    if show_json:
        st.markdown("---")
        st.subheader("Raw LLM JSON")
        st.json(SAMPLE_JSON)

st.caption("Mock mode – always shows the same sample response for UI testing.")
