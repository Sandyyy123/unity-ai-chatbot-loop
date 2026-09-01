> **⚠️ Proprietary — All Rights Reserved.** © 2026 Sandeep Grover. This repository is licensed to Sandeep Grover and may **not** be used, run, copied, modified, distributed, or used to train models without prior written permission. Public visibility does not grant a license. See [LICENSE](LICENSE).

---

# Unity3D AI Chatbot — Conversation Loop Engine

A reference implementation of **loop engineering** for an AI chatbot inside a
Unity3D project. The "loop" is the part that makes a chatbot feel like a real
character instead of a stateless one-shot API call: it holds per-session state,
a rolling memory window, world facts, and a turn manager — server-side in
Python — and exposes a tiny HTTP contract that Unity (C#) consumes.

```
  Unity3D scene (C#)                 Python loop service (FastAPI)
  ┌────────────────────┐   POST /chat   ┌──────────────────────────────┐
  │ ChatbotClient.cs   │ ─────────────► │ app.py  ──►  ConversationLoop │
  │  - sessionId       │                │   - per-session state         │
  │  - Send(msg, cb)   │ ◄───────────── │   - rolling memory window     │
  │  - Remember(k,v)   │   { reply }    │   - turn manager + model swap │
  └────────────────────┘                └──────────────────────────────┘
```

## Why this split

Game engines should not own LLM orchestration. Keeping the loop in Python means:
- the model (OpenAI / Anthropic / local) is swappable without rebuilding the game,
- memory and context windows are bounded server-side, so prompts don't grow forever,
- the same backend can serve a web client, a mobile build, or Unity unchanged.

## Run the loop standalone (no API key, no Unity)

```bash
cd server
python loop.py
```

You'll see the bot recall the player's name and quest across turns — proof the
loop holds state rather than answering each message blind.

## Run the service

```bash
cd server
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Set `OPENAI_API_KEY` to use a real model; without it the service boots in an
offline demo mode so it always runs.

```bash
curl -X POST localhost:8000/chat \
     -H "content-type: application/json" \
     -d '{"session_id":"p1","message":"hello, who are you?"}'
```

## Wire into Unity

1. Copy `unity/ChatbotClient.cs` into your project's `Assets/Scripts/`.
2. Add it to a GameObject, set `serverUrl` and `sessionId` in the Inspector.
3. From your dialogue code:

```csharp
chatbotClient.Remember("player_name", "Alex");
chatbotClient.Send("Where do I find the blacksmith?",
                   reply => dialogueLabel.text = reply);
```

Coroutine-based, so it never blocks the render thread.

## Files

| File | Role |
|------|------|
| `server/loop.py` | The conversation loop engine — state, memory, turn manager |
| `server/app.py` | FastAPI service exposing `/chat` and `/remember` to Unity |
| `server/requirements.txt` | Python deps |
| `unity/ChatbotClient.cs` | C# client: `Send()` / `Remember()` coroutines |

---

Built by Dr. Sandeep Grover as a reference architecture for Unity ↔ Python
AI-chatbot loop engineering.
