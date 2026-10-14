# Tool-Using Agent (from scratch, free LLM API)

A small LLM agent that decides **when and which tools to call** (calculator, live weather,
live currency rates, Wikipedia). Built on any **OpenAI-compatible endpoint** with **no agent
framework**, so every part of the loop is visible and testable. Runs on free tiers (Groq, Gemini)
or fully locally (Ollama).

## Why this project
- Implements the core agent loop by hand: model → tool call → execute → tool result → model.
- Provider-agnostic: swap Groq / Gemini / Ollama by changing three env variables.
- Tool errors are returned to the model as data, so it can recover or report honestly.
- Includes an **evaluation harness** (`eval.py`) measuring tool-selection accuracy, including
  cases where *no* tool should be used and cases where a tool fails.
- Streamlit UI exposes each tool call (input, output, latency).

## Run it
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add your free API key (Groq or Gemini) or use Ollama
streamlit run app.py
python eval.py              # writes eval_results.csv
```

## Structure
| File | Role |
|---|---|
| `tools.py` | Tool functions + JSON schemas (safe AST calculator, Open-Meteo, open.er-api, Wikipedia) |
| `agent.py` | Agent loop with step limit, 429 retry and trace logging |
| `app.py` | Streamlit chat UI with tool-call inspector |
| `eval.py` | Test cases + tool-selection accuracy report |

## Results
_Add your `eval.py` accuracy per model (e.g. Llama 3.3 70B vs Gemini Flash) and 1–2 failure cases._

## Possible extensions
- Compare several free models on the same eval set.
- Proactive behaviour: a background watcher that notifies the user when a condition is met (e.g. EUR/TND above a threshold).
- Memory across sessions, parallel tool calls, LLM-as-judge answer scoring.
