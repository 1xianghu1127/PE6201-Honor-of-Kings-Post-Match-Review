"""Streamlit interface for entering a match and comparing both review systems."""

from __future__ import annotations

from typing import Any

import streamlit as st

from baseline.rules import generate_baseline_review
from core.openrouter_client import DEFAULT_OPENROUTER_MODEL
from guardrails.validators import validate_match_data
from rag.generation import generate_rag_review


st.set_page_config(page_title="Honor of Kings Post-Match Review", page_icon="🎮", layout="wide")
st.title("Honor of Kings AI Post-Match Review Assistant")
st.caption("Enter structured match statistics, then compare the rule baseline with RAG + foundation model.")


def manual_form() -> dict[str, Any] | None:
    with st.form("manual_input"):
        col1, col2, col3 = st.columns(3)
        with col1:
            hero = st.text_input("Hero", value="后羿")
            role = st.selectbox("Role", ["Marksman", "Mage", "Assassin", "Fighter", "Tank", "Support"])
            duration = st.number_input("Match duration (minutes)", min_value=1, max_value=90, value=20)
            result = st.selectbox("Match result", ["win", "loss"])
        with col2:
            kills = st.number_input("Kills", min_value=0, value=9)
            deaths = st.number_input("Deaths", min_value=0, value=2)
            assists = st.number_input("Assists", min_value=0, value=7)
            kp = st.number_input("Kill participation (%)", min_value=0.0, max_value=100.0, value=57.0)
        with col3:
            gold = st.number_input("Gold", min_value=0, value=13200)
            gold_share = st.number_input("Gold share (%)", min_value=0.0, max_value=100.0, value=25.4)
            damage = st.number_input("Damage dealt", min_value=0, value=82000)
            damage_share = st.number_input("Damage dealt share (%)", min_value=0.0, max_value=100.0, value=34.2)
            taken = st.number_input("Damage taken", min_value=0, value=24000)
            taken_share = st.number_input("Damage taken share (%)", min_value=0.0, max_value=100.0, value=11.4)
        submitted = st.form_submit_button("Use this match data", type="primary")
    if not submitted:
        return None
    return {
        "hero": hero.strip() or None,
        "role": role,
        "duration_min": int(duration),
        "kills": int(kills),
        "deaths": int(deaths),
        "assists": int(assists),
        "gold": int(gold),
        "gold_share_pct": float(gold_share),
        "damage_dealt": int(damage),
        "damage_dealt_share_pct": float(damage_share),
        "damage_taken": int(taken),
        "damage_taken_share_pct": float(taken_share),
        "kill_participation_pct": float(kp),
        "match_result": result,
        "validation_status": "valid",
    }


def show_review(title: str, review: dict[str, Any]) -> None:
    st.subheader(title)
    status = review.get("abstention_level", "unknown")
    st.caption(f"Abstention level: {status}")
    for heading, key in (
        ("What went well", "what_went_well"),
        ("What to improve", "what_to_improve"),
        ("Next-match focus", "next_match_focus"),
    ):
        st.markdown(f"#### {heading}")
        for item in review.get(key, []):
            st.markdown(f"- {item}")
    cols = st.columns(3)
    cols[0].metric("Latency", f"{review.get('latency_seconds', 0):.3f}s")
    cols[1].metric("Tokens", int(review.get("total_tokens") or 0))
    cost = review.get("cost_usd")
    cols[2].metric("API cost", "$0" if cost in (None, 0, 0.0) else f"${cost:.6f}")
    if review.get("retrieved_chunks"):
        with st.expander("Retrieved knowledge"):
            for hit in review["retrieved_chunks"]:
                st.markdown(f"**{hit['chunk_id']} · {hit['source_name']} · score {hit['similarity_score']:.3f}**")
                st.write(hit["text"])


manual_data = manual_form()
if manual_data:
    st.session_state["confirmed_data"] = manual_data

data = st.session_state.get("confirmed_data")
if data:
    st.divider()
    st.subheader("Confirmed structured data")
    st.json(data)
    validation = validate_match_data(data)
    if validation.level == "full":
        st.error("Cannot analyse: " + " ".join(validation.errors))
    elif validation.level == "partial":
        st.warning("Partial analysis only. Missing: " + ", ".join(validation.missing_fields))
    mode = st.radio("Analysis mode", ["Compare both", "Rule baseline", "RAG + LLM"], horizontal=True)
    if st.button("Analyse match", type="primary"):
        if mode in {"Compare both", "Rule baseline"}:
            show_review("Rule-based baseline", generate_baseline_review(data))
        if mode in {"Compare both", "RAG + LLM"}:
            try:
                with st.spinner("Retrieving knowledge and generating review..."):
                    review = generate_rag_review(data)
                show_review("RAG + foundation model", review)
            except Exception as exc:
                st.error(str(exc))

with st.sidebar:
    st.header("About")
    st.caption(f"OpenRouter model: {DEFAULT_OPENROUTER_MODEL} (text generation)")
    st.write("The OpenRouter API key is entered in the launch terminal and kept in process memory only.")
    st.write("This is not an autonomous agent. It performs one retrieval-and-generation step after the user submits structured match data.")
    st.write("Main evaluation: 40 manually reviewed cases. No screenshot upload or image recognition is used.")
