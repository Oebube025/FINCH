"""
FastAPI Backend (main.py) - Executive Intelligence Suite (Phase 1 Update)
Synchronized with Cohere and strict payload validation & structured markdown output.
"""

import hmac
import json
import logging
import os
import time
from collections import defaultdict, deque
from typing import Optional

import cohere
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

APP_VERSION = "2.12"
app = FastAPI(title="Executive Intelligence Backend", version=APP_VERSION)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-03-2025")
MAX_BODY_CHARS = 200_000


class AIAdvisoryRequest(BaseModel):
    verified_stats: dict
    saved_scenarios: Optional[list] = None
    currency: Optional[str] = "₦"


def require_key(x_api_key: str = Header(None)):
    expected = os.getenv("BACKEND_SECRET_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="Server configuration error: BACKEND_SECRET_KEY is missing.")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API key.")


_user_hits = defaultdict(deque)
_global_hits = deque()


def check_rate_limit(user: str):
    per_hour = int(os.getenv("AI_RATE_PER_HOUR", "10"))
    daily_cap = int(os.getenv("AI_DAILY_CAP", "500"))
    uq = _user_hits[user]
    now = time.time()
    while uq and now - uq[0] > 3600:
        uq.popleft()
    while _global_hits and now - _global_hits[0] > 86400:
        _global_hits.popleft()
        
    if len(uq) >= per_hour:
        raise HTTPException(status_code=429, detail=f"Rate limit reached ({per_hour} reports per hour).")
    if len(_global_hits) >= daily_cap:
        raise HTTPException(status_code=429, detail="Daily service capacity reached.")
    uq.append(now)
    _global_hits.append(now)


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def sanitize_stats(stats: dict) -> dict:
    meta = stats.get("metadata") or {}
    return {
        "metadata": {k: meta.get(k) for k in (
            "total_rows", "data_health_index", "missing_cells", "duplicate_rows", "anomaly_count",
            "revenue_column", "cost_column", "category_column", "date_column")},
        "totals": stats.get("totals"),
        "revenue_by_category": dict(list((stats.get("revenue_by_category") or {}).items())[:15]),
        "trend": stats.get("trend"),
        "anomalies": stats.get("anomalies", [])[:5],
        "warnings": [str(w)[:300] for w in (stats.get("warnings") or [])[:10]],
    }


def sanitize_scenarios(scenarios: Optional[list]) -> list:
    out = []
    for sc in (scenarios or [])[:10]:
        if isinstance(sc, dict):
            out.append({
                "scenario_name": str(sc.get("scenario_name", ""))[:80],
                "revenue": _num(sc.get("revenue")),
                "costs": _num(sc.get("costs")),
                "net_profit": _num(sc.get("net_profit")),
                "margin": _num(sc.get("margin")),
                "cost_assumed": bool(sc.get("cost_assumed", False)),
            })
    return out


def build_prompt(stats: dict, scenarios: list, currency: str) -> str:
    return f"""You are an elite, no-nonsense fractional CFO and startup turnaround specialist with 20 years of experience.
Your job is to ruthlessly analyze the provided verified financial statistics, category leaderboards, and what-if scenarios to deliver high-impact, actionable business advice to the owner.

Strict Rules:
1. Avoid generic business jargon, fluff, or empty praise. Be direct, analytical, and professional.
2. Base every recommendation strictly on the provided revenue, cost, and category numbers ({currency}). Do not hallucinate external metrics.
3. Structure your response into exactly these four sections using clear markdown headings:
   - **Executive Health Score:** A brutal-truth 2-sentence summary of current financial standing.
   - **Top 3 Margin Leaks:** Identify specific categories or cost structures dragging down profitability.
   - **Immediate Cash-Flow Actions:** Give 2 concrete, tactical steps the owner can execute this week.
   - **What-If Scenario Critique:** Evaluate the user's simulation scenario and warn them of hidden risks.

<data>
VERIFIED DATASET FACT SHEET:
{json.dumps(stats, indent=1, default=str)}

SAVED WHAT-IF SCENARIOS:
{json.dumps(scenarios, indent=1) if scenarios else "None provided."}
</data>
"""


def _call_cohere(api_key: str, prompt: str) -> str:
    co = cohere.ClientV2(api_key)
    resp = co.chat(model=COHERE_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2)
    return resp.message.content[0].text


@app.get("/health", dependencies=[Depends(require_key)])
async def health_check():
    return {"status": "healthy", "service": "Executive Intelligence Backend", "version": APP_VERSION}


@app.post("/api/ai-advisory", dependencies=[Depends(require_key)])
async def generate_ai_advisory(payload: AIAdvisoryRequest, x_user_id: str = Header("anonymous")):
    body_str = json.dumps(payload.model_dump(), default=str)
    if len(body_str) > MAX_BODY_CHARS:
        raise HTTPException(status_code=413, detail="Payload too large. Please upload a smaller subset of records.")

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service configuration missing on server.")

    check_rate_limit(x_user_id[:64])
    prompt = build_prompt(sanitize_stats(payload.verified_stats), sanitize_scenarios(payload.saved_scenarios), payload.currency or "₦")
    try:
        text = await run_in_threadpool(_call_cohere, api_key, prompt)
        return {"advisory": text}
    except Exception as e:
        logger.error("Cohere AI error: %s", e)
        raise HTTPException(status_code=502, detail="The AI provider encountered an error. Please try again shortly.")