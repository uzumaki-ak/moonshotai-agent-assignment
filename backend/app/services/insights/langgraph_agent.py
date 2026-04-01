# this file orchestrates insight generation with langgraph style state flow
from __future__ import annotations

import json
from typing import TypedDict

from app.services.llm.router import LlmRouter, parse_json_from_text


class InsightState(TypedDict):
    # this typed state moves through graph nodes
    comparison: list[dict]
    signal_summary: str
    draft: list[dict]


def _derive_signals(state: InsightState) -> InsightState:
    # this node computes deterministic signals used by llm prompt
    comparison = state["comparison"]
    if not comparison:
        state["signal_summary"] = "no rows"
        return state

    sorted_sent = sorted(comparison, key=lambda row: row.get("sentiment_score") or -999, reverse=True)
    sorted_discount = sorted(comparison, key=lambda row: row.get("avg_discount_pct") or -999, reverse=True)

    winner = sorted_sent[0]["brand_name"]
    disc = sorted_discount[0]["brand_name"]

    state["signal_summary"] = (
        f"top sentiment brand is {winner}. "
        f"highest discount brand is {disc}. "
        f"rows count is {len(comparison)}"
    )
    return state


async def _generate_with_llm(state: InsightState, llm: LlmRouter) -> InsightState:
    # this node asks llm to turn signals into insight cards
    system_prompt = (
        "you are a strict analyst. return clean json only with key insights."
    )
    user_prompt = (
        "create 5 insights in json format: "
        "{\"insights\":[{\"insight_type\":\"value|premium|risk|opportunity|theme\",\"title\":\"...\",\"body\":\"...\",\"confidence\":0.0,\"payload\":{}}]} "
        f"signal summary: {state['signal_summary']} data: {state['comparison']}"
    )

    response = await llm.generate(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=900)
    parsed = parse_json_from_text(response.get("content", ""))
    state["draft"] = parsed.get("insights", []) if parsed and isinstance(parsed.get("insights"), list) else []
    return state


def _normalize(state: InsightState) -> InsightState:
    # this node validates draft fields to avoid malformed cards
    valid: list[dict] = []
    for row in state.get("draft", []):
        title = row.get("title") if isinstance(row, dict) else None
        body = row.get("body") if isinstance(row, dict) else None
        if not title or not body:
            continue
        valid.append(
            {
                "insight_type": row.get("insight_type", "analysis"),
                "title": str(title),
                "body": str(body),
                "confidence": float(row.get("confidence", 0.5)),
                "payload": row.get("payload") if isinstance(row.get("payload"), dict) else {},
            }
        )
    state["draft"] = valid
    return state


async def run_insight_graph(comparison: list[dict], llm: LlmRouter) -> list[dict]:
    # this function runs graph flow and returns insight cards
    state: InsightState = {
        "comparison": comparison,
        "signal_summary": "",
        "draft": [],
    }

    try:
        # this import is lazy to keep app runnable without langgraph install
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(InsightState)
        graph.add_node("derive", _derive_signals)
        graph.add_node("normalize", _normalize)

        # this async wrapper allows llm call inside graph node
        async def gen_node(s: InsightState) -> InsightState:
            return await _generate_with_llm(s, llm)

        graph.add_node("generate", gen_node)

        graph.add_edge(START, "derive")
        graph.add_edge("derive", "generate")
        graph.add_edge("generate", "normalize")
        graph.add_edge("normalize", END)

        app = graph.compile()
        final_state = await app.ainvoke(state)
        return final_state.get("draft", [])
    except Exception:
        # this fallback keeps behavior stable if langgraph is missing
        state = _derive_signals(state)
        state = await _generate_with_llm(state, llm)
        state = _normalize(state)
        return state.get("draft", [])
