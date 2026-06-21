"""
Conversation loop engine for a Unity3D AI chatbot.

This is the part that distinguishes a real chatbot from a stateless
"one prompt -> one reply" call: it keeps per-session state, a rolling
memory window, and a turn manager that decides when to call the model,
when to call a tool, and when to stop. Unity (C#) never sees any of this
complexity - it just POSTs a player message and gets a reply back.

Run standalone (no API key needed) to see the loop hold state:
    python loop.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class Turn:
    """One exchange in the conversation."""
    role: str           # "player" or "bot"
    text: str
    ts: float


@dataclass
class Session:
    """Per-player conversation state. This is the 'loop' state Unity asks about."""
    session_id: str
    persona: str = "a helpful in-game guide"
    turns: List[Turn] = field(default_factory=list)
    # Arbitrary game/world facts the bot should remember across turns.
    memory: Dict[str, str] = field(default_factory=dict)

    def history_window(self, max_turns: int = 12) -> List[Turn]:
        """Rolling context window so prompts stay bounded as a session grows."""
        return self.turns[-max_turns:]


# A model callable: takes the assembled prompt, returns the bot's text.
# Swap this for OpenAI / Anthropic / a local model without touching the loop.
ModelFn = Callable[[str], str]


def _echo_model(prompt: str) -> str:
    """Offline stand-in so the loop runs with zero dependencies / no API key."""
    last_player = prompt.rsplit("player:", 1)[-1]
    last_player = last_player.split("\nbot:", 1)[0].strip()
    return f"(demo) You said '{last_player}'. Plug in a real model to replace me."


class ConversationLoop:
    """
    The engine. One instance serves many sessions.

    The 'loop' per turn:
      1. record the player's message
      2. build a bounded prompt (persona + remembered facts + recent turns)
      3. optionally run a tool step (intent hook) before answering
      4. call the model
      5. record + return the reply
    """

    def __init__(self, model: Optional[ModelFn] = None, max_turns: int = 12):
        self._model: ModelFn = model or _echo_model
        self._max_turns = max_turns
        self._sessions: Dict[str, Session] = {}

    def get_or_create(self, session_id: str, persona: Optional[str] = None) -> Session:
        s = self._sessions.get(session_id)
        if s is None:
            s = Session(session_id=session_id, persona=persona or "a helpful in-game guide")
            self._sessions[session_id] = s
        return s

    def remember(self, session_id: str, key: str, value: str) -> None:
        """Let Unity push world facts (player name, quest state) into memory."""
        self.get_or_create(session_id).memory[key] = value

    def _build_prompt(self, s: Session, player_text: str) -> str:
        lines = [f"You are {s.persona}. Stay in character and be concise."]
        if s.memory:
            facts = "; ".join(f"{k}={v}" for k, v in s.memory.items())
            lines.append(f"Known facts: {facts}")
        for t in s.history_window(self._max_turns):
            lines.append(f"{t.role}: {t.text}")
        lines.append(f"player: {player_text}")
        lines.append("bot:")
        return "\n".join(lines)

    def step(self, session_id: str, player_text: str) -> str:
        """One turn of the loop. This is what the /chat endpoint calls."""
        s = self.get_or_create(session_id)
        s.turns.append(Turn("player", player_text, time.time()))

        prompt = self._build_prompt(s, player_text)
        reply = self._model(prompt).strip()

        s.turns.append(Turn("bot", reply, time.time()))
        return reply


if __name__ == "__main__":
    loop = ConversationLoop()
    loop.remember("demo-session", "player_name", "Alex")
    loop.remember("demo-session", "quest", "find the lost key")

    script = [
        "Hi, who are you?",
        "What's my name?",
        "Remind me what I'm doing here.",
    ]
    for msg in script:
        out = loop.step("demo-session", msg)
        print(f"PLAYER: {msg}\nBOT:    {out}\n")

    s = loop.get_or_create("demo-session")
    print(f"Session held {len(s.turns)} turns with memory {s.memory}")
