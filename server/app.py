"""
FastAPI service exposing the conversation loop to Unity over HTTP.

Unity's C# client hits POST /chat with {session_id, message} and gets
{reply}. POST /remember pushes world facts. That's the entire contract -
the loop's state/memory live here, not in the game.

Run:
    pip install -r requirements.txt
    uvicorn app:app --reload --port 8000

Then from Unity (or curl):
    curl -X POST localhost:8000/chat -H "content-type: application/json" \
         -d '{"session_id":"p1","message":"hello"}'
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from loop import ConversationLoop


def _build_model():
    """
    Use a real LLM if OPENAI_API_KEY is set, else fall back to the offline
    echo model so the service always boots for a demo.
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None  # ConversationLoop defaults to the offline echo model
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        def _openai_model(prompt: str) -> str:
            resp = client.chat.completions.create(
                model=os.getenv("CHAT_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return resp.choices[0].message.content or ""

        return _openai_model
    except Exception:
        return None


app = FastAPI(title="Unity AI Chatbot Loop", version="1.0.0")
loop = ConversationLoop(model=_build_model())


class ChatIn(BaseModel):
    session_id: str
    message: str
    persona: Optional[str] = None


class ChatOut(BaseModel):
    reply: str
    turns: int


class RememberIn(BaseModel):
    session_id: str
    key: str
    value: str


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn) -> ChatOut:
    if body.persona:
        loop.get_or_create(body.session_id, persona=body.persona)
    reply = loop.step(body.session_id, body.message)
    session = loop.get_or_create(body.session_id)
    return ChatOut(reply=reply, turns=len(session.turns))


@app.post("/remember")
def remember(body: RememberIn) -> dict:
    loop.remember(body.session_id, body.key, body.value)
    return {"ok": True}
