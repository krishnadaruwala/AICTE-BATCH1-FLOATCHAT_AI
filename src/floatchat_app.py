"""
floatchat_app — Streamlit UI for FloatChat.

Run from the project root:
    streamlit run src/floatchat_app.py

Pipeline per user message:
    parse_query()  ->  fetch_from_params()  ->  generate_insight()  ->  render
"""

from __future__ import annotations

import os
import sys

import streamlit as st
import streamlit.components.v1 as components

# Load floatchat/.env (GEMINI_API_KEY=...) if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(__file__))

import floatchat_core as core      # noqa: E402
import floatchat_viz as viz        # noqa: E402

# RAG knowledge base is optional — app still runs if it can't import.
try:
    import floatchat_rag as rag     # noqa: E402
except Exception:
    rag = None

st.set_page_config(page_title="FloatChat", page_icon="🌊", layout="wide")

# --------------------------------------------------------------------------- #
# Ocean theme
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; max-width: 1150px; }
    #MainMenu, footer { visibility: hidden; }
    h1.fc-title { font-size: 22px; font-weight: 600; color: #0F6E56;
        display:flex; align-items:center; gap:8px; margin-bottom:2px; }
    .fc-sub { color:#6B6B6B; font-size:13px; margin-bottom:14px; }
    .tag { display:inline-block; font-size:10px; padding:2px 9px; border-radius:11px;
        background:#E1F5EE; color:#0F6E56; margin-right:5px; margin-top:8px; }
    table.cmp { width:100%; border-collapse:collapse; font-size:12px;
        background:#F7F8F7; border-radius:10px; overflow:hidden; margin-top:10px; }
    table.cmp td { padding:6px 10px; color:#6B6B6B; }
    table.cmp tr:first-child td { font-weight:600; color:#1A1A1A; }
    table.cmp td:nth-child(2) { color:#0F6E56; font-weight:600; }
    table.cmp td:nth-child(3) { color:#185FA5; font-weight:600; }
    .dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:5px; }
    .stChatMessage { background: transparent; }
    </style>
    """, unsafe_allow_html=True,
)

EXAMPLE_QUERIES = [
    "Temperature profiles in the Arabian Sea, Jan 2023",
    "Compare Arabian Sea and Bay of Bengal salinity",
    "Show the T-S diagram for the Arabian Sea",
    "Seasonal surface temperature trend in the Bay of Bengal",
]


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("### 🌊 FloatChat")

        data_source = st.selectbox(
            "Data source", ["Argo ERDDAP (live)", "Mock sample data"],
            key="data_source",
        )
        source = "live" if data_source.startswith("Argo") else "mock"

        region = st.selectbox("Region", list(core.REGION_PRESETS), key="region")
        lon0, lon1, lat0, lat1 = core.REGION_PRESETS[region]
        st.caption(f"📍 lon {lon0}–{lon1}, lat {lat0}–{lat1}")

        depth = st.slider("Depth (m)", 0, 2000, (0, 500), step=50, key="depth")

        d0, d1 = core.today_range()
        c1, c2 = st.columns(2)
        start = c1.date_input("Start", d0, key="start")
        end = c2.date_input("End", d1, key="end")

        variables = st.multiselect("Variables", core.VARIABLES,
                                   default=["TEMP"], key="variables")

        st.markdown("**Example queries**")
        for i, q in enumerate(EXAMPLE_QUERIES):
            if st.button(q, key=f"ex_{i}", use_container_width=True):
                st.session_state.pending = q

        st.divider()
        live = core.get_client() is not None
        st.caption(("🟢 Gemini connected" if live
                    else "⚪ Gemini offline — keyword parsing"))
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    return {
        "source": source, "region": region, "depth": depth,
        "variables": variables or ["TEMP"], "date_range": (str(start), str(end)),
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _data_metrics(data: dict) -> None:
    m = st.columns(3)
    m[0].metric("Active floats", data["active_floats"])
    m[1].metric("Data points", str(data["data_points"]))
    m[2].metric("Source", "ERDDAP" if data["source"] != "mock" else "Mock")


def render_artifact(art: dict, key: str) -> None:
    """Render one tool result (chart/table) produced by the agent.

    `key` must be unique across the whole page (Streamlit requires unique
    element IDs), so callers pass a per-message + per-artifact prefix.
    """
    kind = art["type"]

    if kind in ("overview", "ts_diagram"):
        data = art["data"]
        _data_metrics(data)
        col_map, col_chart = st.columns(2)
        with col_map:
            st.caption("🗺️ Float positions")
            components.html(viz.float_map(data), height=320)
        with col_chart:
            if kind == "ts_diagram":
                st.caption("🌡️ Temperature–salinity diagram")
                fig = viz.ts_diagram(data)
            else:
                st.caption("📈 Temp vs depth profiles")
                fig = viz.depth_profile(data)
            st.plotly_chart(fig, use_container_width=True, key=f"{key}_chart",
                            config={"displayModeBar": False})

    elif kind == "timeseries":
        st.caption("📅 Seasonal surface temperature")
        regions = art["regions"] if len(art["regions"]) > 1 \
            else [art["regions"][0], "Bay of Bengal"]
        st.plotly_chart(viz.time_series(art["data"], regions), key=f"{key}_ts",
                        use_container_width=True, config={"displayModeBar": False})

    elif kind == "comparison":
        metrics = art["metrics"]
        rows = (
            f'<tr><td>Metric</td>'
            f'<td><span class="dot" style="background:#1D9E75"></span>{metrics["region_a"]}</td>'
            f'<td><span class="dot" style="background:#185FA5"></span>{metrics["region_b"]}</td></tr>'
        )
        for name, a, b in metrics["metrics"]:
            rows += f'<tr><td>{name}</td><td>{a}</td><td>{b}</td></tr>'
        st.markdown(f'<table class="cmp">{rows}</table>', unsafe_allow_html=True)
        st.plotly_chart(viz.comparison_chart(metrics), key=f"{key}_cmp",
                        use_container_width=True, config={"displayModeBar": False})


def render_sources(sources: list) -> None:
    if sources:
        with st.expander("📚 Sources"):
            for src in sources:
                st.write(f"• {src}")


def render_steps(steps: list) -> None:
    if steps and len(steps) > 1:  # only worth showing for multi-step turns
        with st.expander(f"🧭 Agent steps ({len(steps)})"):
            for i, step in enumerate(steps, 1):
                st.write(f"{i}. {step}")


def render_result(msg: dict, idx: int) -> None:
    st.markdown(msg["insight"])
    if msg.get("note"):
        st.info(msg["note"], icon="🧪")
    render_steps(msg.get("steps", []))
    for j, art in enumerate(msg.get("artifacts", [])):
        render_artifact(art, key=f"m{idx}_a{j}")
    render_sources(msg.get("sources", []))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
filters = render_sidebar()

st.markdown('<h1 class="fc-title">🌊 FloatChat</h1>', unsafe_allow_html=True)
st.markdown('<div class="fc-sub">Ask about Argo ocean-float temperature, '
            'salinity, depth profiles, tracks, and anomalies.</div>',
            unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay history.
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message("user" if msg["role"] == "user" else "assistant",
                         avatar="🧑" if msg["role"] == "user" else "🌊"):
        if msg["role"] == "user":
            st.markdown(msg["text"])
        else:
            render_result(msg, idx)

# Input — from chat box or an example button.
prompt = st.chat_input("Ask about ocean temperature, salinity, float tracks, anomalies…")
if not prompt and "pending" in st.session_state:
    prompt = st.session_state.pop("pending")

if prompt:
    st.session_state.messages.append({"role": "user", "text": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    history = [{"role": m["role"], "text": m.get("text") or m.get("insight", "")}
               for m in st.session_state.messages]
    idx = len(st.session_state.messages)  # index this assistant will occupy

    use_rag = rag is not None and rag.rag_available() and rag.is_rag_query(prompt)

    with st.chat_message("assistant", avatar="🌊"):
        result: dict = {"artifacts": [], "note": None, "sources": [], "steps": []}
        if use_rag:
            # Conceptual question -> oceanography knowledge base (RAG).
            convo = "\n".join(f"{m['role']}: {m.get('text') or m.get('insight','')}"
                              for m in st.session_state.messages[-5:-1])
            with st.spinner("🔍 Searching ocean knowledge base…"):
                insight = st.write_stream(
                    rag.stream_answer(prompt, convo, result))
            render_sources(result["sources"])
        else:
            # Data question -> autonomous multi-step Argo agent (streamed).
            with st.spinner("Planning & querying Argo floats…"):
                insight = st.write_stream(
                    core.stream_turn(history, filters, result))
            if result.get("note"):
                st.info(result["note"], icon="🧪")
            render_steps(result.get("steps", []))
            for j, art in enumerate(result["artifacts"]):
                render_artifact(art, key=f"m{idx}_a{j}")

    st.session_state.messages.append({
        "role": "assistant", "insight": insight,
        "artifacts": result["artifacts"], "note": result["note"],
        "sources": result.get("sources", []),
        "steps": result.get("steps", []),
    })
