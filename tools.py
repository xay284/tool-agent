"""Tool implementations and their JSON schemas for the agent."""
import ast
import json
import operator as op

import requests

TIMEOUT = 10

# ---------- calculator (safe AST evaluation, no eval()) ----------
_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.USub: op.neg, ast.Mod: op.mod, ast.FloorDiv: op.floordiv,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> dict:
    result = _eval(ast.parse(expression, mode="eval").body)
    return {"expression": expression, "result": result}


# ---------- weather (Open-Meteo, no API key) ----------
def get_weather(city: str) -> dict:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1}, timeout=TIMEOUT,
    ).json()
    if not geo.get("results"):
        return {"error": f"City not found: {city}"}
    place = geo["results"][0]
    w = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"], "longitude": place["longitude"],
            "current": "temperature_2m,wind_speed_10m,precipitation",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "forecast_days": 3, "timezone": "auto",
        }, timeout=TIMEOUT,
    ).json()
    return {
        "city": place["name"], "country": place.get("country"),
        "current": w["current"], "daily_forecast": w["daily"],
    }


# ---------- currency (open.er-api.com, supports TND) ----------
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    src, dst = from_currency.upper(), to_currency.upper()
    data = requests.get(f"https://open.er-api.com/v6/latest/{src}", timeout=TIMEOUT).json()
    if data.get("result") != "success" or dst not in data.get("rates", {}):
        return {"error": f"Cannot convert {src} to {dst}"}
    rate = data["rates"][dst]
    return {"amount": amount, "from": src, "to": dst, "rate": rate, "converted": round(amount * rate, 4)}


# ---------- Wikipedia lookup ----------
def search_wikipedia(query: str) -> dict:
    s = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "opensearch", "search": query, "limit": 1, "format": "json"},
        timeout=TIMEOUT, headers={"User-Agent": "tool-agent-demo/1.0"},
    ).json()
    if not s[1]:
        return {"error": f"No Wikipedia page for: {query}"}
    title = s[1][0]
    r = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}",
        timeout=TIMEOUT, headers={"User-Agent": "tool-agent-demo/1.0"},
    ).json()
    return {"title": r.get("title"), "summary": r.get("extract"), "url": r.get("content_urls", {}).get("desktop", {}).get("page")}


REGISTRY = {
    "calculator": calculator,
    "get_weather": get_weather,
    "convert_currency": convert_currency,
    "search_wikipedia": search_wikipedia,
}

TOOL_SCHEMAS = [
    {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression (+, -, *, /, **, %, //). Use for any math instead of computing mentally.",
        "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
    },
    {
        "name": "get_weather",
        "description": "Get current weather and a 3-day forecast for a city.",
        "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    },
    {
        "name": "convert_currency",
        "description": "Convert an amount between currencies using live exchange rates (ISO codes, e.g. TND, EUR, USD).",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "from_currency": {"type": "string"},
                "to_currency": {"type": "string"},
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
    },
    {
        "name": "search_wikipedia",
        "description": "Look up a short factual summary of a topic, person, place or concept on Wikipedia.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
]


def run_tool(name: str, args: dict) -> str:
    """Execute a tool and always return a JSON string (errors included) so the agent can recover."""
    try:
        if name not in REGISTRY:
            return json.dumps({"error": f"Unknown tool: {name}"})
        return json.dumps(REGISTRY[name](**args), ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": f"{type(e).__name__}: {e}"})
