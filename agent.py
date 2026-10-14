"""Minimal tool-calling agent loop (no framework) on any OpenAI-compatible endpoint."""
import json
import os
import time
from pathlib import Path

import openai
from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOL_SCHEMAS, run_tool

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()
API_KEY = (os.getenv("LLM_API_KEY") or "").strip().strip('"').strip("'")
MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile").strip()

if not API_KEY or API_KEY in ("none", "your_groq_key_here"):
    raise RuntimeError(
        f"LLM_API_KEY is missing or still the placeholder. "
        f"Looked for .env at: {Path(__file__).parent / '.env'}"
    )
print(f"[agent] url={BASE_URL} model={MODEL} key={API_KEY[:4]}...{API_KEY[-4:]} (len={len(API_KEY)})")

MAX_STEPS = 6
SYSTEM = (
    "You are a helpful assistant with tools for math, weather, currency conversion and Wikipedia. "
    "Use a tool whenever the answer depends on live data or exact calculation. "
    "If a tool returns an error, say so honestly or try a sensible alternative. "
    "Answer in the user's language, concisely."
)

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Convert our schemas to the OpenAI function-calling format
TOOLS = [
    {"type": "function", "function": {"name": s["name"], "description": s["description"], "parameters": s["input_schema"]}}
    for s in TOOL_SCHEMAS
]


def _chat(messages, retries: int = 3):
    """Call the model, retrying on free-tier rate limits (HTTP 429)."""
    for attempt in range(retries):
        try:
            return client.chat.completions.create(
                model=MODEL, messages=messages, tools=TOOLS, max_tokens=1000, temperature=0,
            )
        except openai.RateLimitError:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def run_agent(history: list[dict], max_steps: int = MAX_STEPS):
    """history: list of {"role","content"} text turns. Returns (answer, trace)."""
    messages = [{"role": "system", "content": SYSTEM}] + list(history)
    trace = []
    for step in range(max_steps):
        try:
            resp = _chat(messages)
        except openai.BadRequestError as e:  # open models sometimes emit malformed tool calls
            return f"Model returned an invalid request/tool call: {e}", trace
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content or "", trace

        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            t0 = time.time()
            output = run_tool(call.function.name, args)
            trace.append({
                "step": step, "tool": call.function.name, "input": args,
                "output": output, "latency_s": round(time.time() - t0, 3),
            })
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

    return "I could not finish within the step limit.", trace


def save_trace(question: str, answer: str, trace: list, folder: str = "traces"):
    Path(folder).mkdir(exist_ok=True)
    path = Path(folder) / f"{int(time.time() * 1000)}.json"
    path.write_text(
        json.dumps({"question": question, "answer": answer, "trace": trace}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )