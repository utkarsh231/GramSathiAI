import streamlit as st
from pypdf import PdfReader
from rag import SimpleRAG
from soil import parse_soil_text, fertilizer_plan
from schemes import load_schemes, check_eligibility

st.set_page_config(page_title="GramSathi AI (MVP)", page_icon="🌾", layout="wide")

@st.cache_resource
def get_rag():
    return SimpleRAG(kb_dir="data/kb_docs")

rag = get_rag()
schemes = load_schemes()

def pdf_to_text(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def render_soil_summary(parsed: dict, plan: dict):
    st.markdown("### Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("pH", "—" if parsed.get("pH") is None else f"{parsed.get('pH'):.2f}")
    c2.metric("N", "—" if parsed.get("N") is None else f"{parsed.get('N'):.0f}")
    c3.metric("P", "—" if parsed.get("P") is None else f"{parsed.get('P'):.0f}")
    c4.metric("K", "—" if parsed.get("K") is None else f"{parsed.get('K'):.0f}")
    c5.metric("Confidence", f"{int(plan.get('confidence', 0)*100)}%")

    # Key takeaways
    st.markdown("**Key takeaways**")
    for s in plan.get("steps", [])[:6]:
        st.markdown(f"- {s}")

    # Missing fields
    missing = plan.get("missing_fields", [])
    if missing:
        st.warning("Missing from report: " + ", ".join(missing))

    # Schedule
    schedule = plan.get("schedule", [])
    if schedule:
        st.markdown("**Suggested schedule (demo)**")
        st.table(schedule)


def render_scheme_summary(scheme: dict, result: dict):
    st.markdown("### Summary")

    top = st.columns([2, 1, 1])
    with top[0]:
        st.markdown(f"**Scheme:** {scheme.get('name', '')}")
        st.caption(scheme.get("description", ""))
    with top[1]:
        st.metric("Eligible", "Yes" if result.get("eligible") else "No")
    with top[2]:
        st.metric("Confidence", f"{int(result.get('confidence', 0)*100)}%")

    reasons = result.get("reasons", [])
    if reasons:
        st.error("**Why not eligible / concerns:**\n" + "\n".join([f"- {r}" for r in reasons]))

    missing_docs = result.get("missing_documents", [])
    if missing_docs:
        st.warning("**Missing documents:**\n" + "\n".join([f"- {d}" for d in missing_docs]))

    checklist = result.get("checklist", [])
    if checklist:
        st.markdown("**Next steps**")
        for i, step in enumerate(checklist, start=1):
            st.markdown(f"{i}. {step}")

st.title("🌾 GramSathi AI — Soil + Scheme Assistant (MVP)")
st.caption("Voice-first idea → we start with chat + PDF text. Add ASR/OCR next.")

tabs = st.tabs(["💬 Chat", "🧪 Soil Report", "🏛️ Scheme Eligibility"])

# -------------------------
# Chat (RAG Q&A demo)
# -------------------------
with tabs[0]:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("sources"):
                with st.expander("Sources"):
                    for s in m["sources"]:
                        st.markdown(f"- **{s['doc']}** (score={s['score']:.2f}): {s['text']}")

    prompt = st.chat_input("Ask about fertilizer, soil pH, scheme docs, etc.")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        hits = rag.retrieve(prompt, k=4)
        # “Grounded answers only” behavior: if retrieval too weak, ask clarifying Q
        avg_score = sum(s for _, s in hits) / max(1, len(hits))
        if avg_score < 0.25:
            answer = "I’m not confident I have enough official context. Can you specify your state, scheme name, and what document you have?"
            sources = []
        else:
            bullets = "\n".join([f"- {c.text}" for c, _ in hits[:3]])
            answer = f"Here’s what I found (demo, grounded in retrieved snippets):\n\n{bullets}\n\nIf you tell me your state/crop, I can tailor steps."
            sources = [{"doc": c.doc_name, "text": c.text, "score": sc} for c, sc in hits]

        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
        st.rerun()

# -------------------------
# Soil Report Interpreter
# -------------------------
with tabs[1]:
    st.subheader("Upload Soil Report (PDF) → Fertilizer Plan")
    uploaded = st.file_uploader("Upload PDF soil report", type=["pdf"])
    if uploaded:
        text = pdf_to_text(uploaded)
        st.text_area("Extracted text (edit if needed)", value=text, height=200)

        if st.button("Generate fertilizer plan"):
            parsed = parse_soil_text(text)
            plan = fertilizer_plan(parsed)

            # Retrieve sources for citations
            query = f"fertilizer guidance pH {parsed.get('pH')} nitrogen {parsed.get('N')} phosphorus {parsed.get('P')} potassium {parsed.get('K')}"
            hits = rag.retrieve(query, k=3)
            sources = [{"doc": c.doc_name, "text": c.text, "score": sc} for c, sc in hits]

            render_soil_summary(parsed, plan)

            with st.expander("See raw JSON"):
                st.json({"parsed": parsed, "plan": plan})

            st.markdown("### Sources (citations)")
            for s in sources:
                st.markdown(f"- **{s['doc']}** (score={s['score']:.2f}): {s['text']}")

            if plan["confidence"] < 0.5:
                st.warning("Low confidence → ask clarifying questions or escalate to KVK/helpline (demo behavior).")

# -------------------------
# Scheme Eligibility
# -------------------------
with tabs[2]:
    st.subheader("Check scheme eligibility → checklist + missing docs")

    scheme_name = st.selectbox("Pick a scheme (demo)", [s["name"] for s in schemes])
    scheme = next(s for s in schemes if s["name"] == scheme_name)

    col1, col2 = st.columns(2)
    with col1:
        is_farmer = st.checkbox("I am a farmer", value=True)
        has_land = st.checkbox("I have land records / Khatauni", value=False)
    with col2:
        st.markdown("**Documents you already have (demo):**")
        docs = {}
        for d in scheme.get("required_documents", []):
            docs[d] = st.checkbox(d, value=False)

    if st.button("Check eligibility"):
        user = {
            "is_farmer": is_farmer,
            "has_land_records": has_land,
            "docs": docs
        }
        result = check_eligibility(user, scheme)

        # citations via scheme doc retrieval
        hits = rag.retrieve(f"{scheme['name']} eligibility documents steps", k=3)
        sources = [{"doc": c.doc_name, "text": c.text, "score": sc} for c, sc in hits]

        render_scheme_summary(scheme, result)

        with st.expander("See raw JSON"):
            st.json(result)

        st.markdown("### Sources (citations)")
        for s in sources:
            st.markdown(f"- **{s['doc']}** (score={s['score']:.2f}): {s['text']}")

        if result["confidence"] < 0.5:
            st.warning("Low confidence → ask clarifying questions (state/category) or escalate to KVK/helpline (demo).")