"""Tiny evaluation harness: did the agent call the right tools and avoid unnecessary ones?"""
import time

import pandas as pd

from agent import run_agent

CASES = [
    {"q": "What is 17.5% of 2480?", "expected": {"calculator"}},
    {"q": "What's the weather in Tunis right now?", "expected": {"get_weather"}},
    {"q": "Convert 300 EUR to TND.", "expected": {"convert_currency"}},
    {"q": "Who was Ibn Khaldun?", "expected": {"search_wikipedia"}},
    {"q": "Weather in Paris and convert 100 USD to EUR.", "expected": {"get_weather", "convert_currency"}},
    {"q": "What is (3.2 * 45) + 18 ** 2?", "expected": {"calculator"}},
    {"q": "Tell me about Carthage and what the weather is there.", "expected": {"search_wikipedia", "get_weather"}},
    {"q": "Say hello in French.", "expected": set()},                      # no tool needed
    {"q": "What is the capital of Tunisia?", "expected": set()},           # known fact, no tool needed
    {"q": "Weather in Qwxzyland?", "expected": {"get_weather"}},           # tool error handling
    {"q": "I have 1200 TND. How many USD is that, minus 15% fees?", "expected": {"convert_currency", "calculator"}},
    {"q": "Quelle est la température à Sfax ?", "expected": {"get_weather"}},  # French input
]


def main():
    rows = []
    for case in CASES:
        answer, trace = run_agent([{"role": "user", "content": case["q"]}])
        used = {t["tool"] for t in trace}
        errors = sum('"error"' in t["output"] for t in trace)
        rows.append({
            "question": case["q"],
            "expected": sorted(case["expected"]),
            "used": sorted(used),
            "tool_selection_ok": used == case["expected"],
            "n_calls": len(trace),
            "tool_errors": errors,
            "answer": answer[:200],
        })
        print(f"{'OK ' if rows[-1]['tool_selection_ok'] else 'FAIL'} | {case['q']}")
        time.sleep(2)  # stay under free-tier rate limits
    df = pd.DataFrame(rows)
    df.to_csv("eval_results.csv", index=False, encoding="utf-8-sig")
    print(f"\nTool selection accuracy: {df.tool_selection_ok.mean():.0%} ({df.tool_selection_ok.sum()}/{len(df)})")


if __name__ == "__main__":
    main()
