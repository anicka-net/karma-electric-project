#!/usr/bin/env python3
"""
Karma Electric — Tool Use Validation

Tests whether the model can:
1. Produce valid JSON tool calls when tools are available
2. Interpret tool results in natural language
3. Decline tool use when no tools match the request
4. NOT hallucinate tool calls when no tools are defined

Usage:
    python3 scripts/reward_test_tool_use.py
    python3 scripts/reward_test_tool_use.py --url http://localhost:8384/v1/chat/completions
"""

import argparse
import json
import sys
import time

import requests

DEFAULT_URL = "http://localhost:8384/v1/chat/completions"

TOOL_DEFINITIONS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "units": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
            },
            "required": ["location"]
        }
    },
    {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email message",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body text"}
            },
            "required": ["to", "subject", "body"]
        }
    }
]

SYSTEM_WITH_TOOLS = (
    "You have access to the following tools. Use them when the user's "
    "request requires it. Call tools by responding with a JSON object "
    "containing 'name' and 'arguments' fields.\n\n"
    "Available tools:\n" + json.dumps(TOOL_DEFINITIONS, indent=2)
)

SYSTEM_NO_TOOLS = (
    "You are Karma Electric, an AI assistant grounded in ethical reasoning "
    "through consequence analysis and interdependence."
)

# ── Test cases ────────────────────────────────────────────────

TESTS = [
    # === Should produce tool calls ===
    {
        "id": "tool-call-weather",
        "description": "Should call get_weather",
        "system": SYSTEM_WITH_TOOLS,
        "user": "What's the weather like in Prague?",
        "expect": "tool_call",
        "expect_tool": "get_weather",
        "expect_arg": "Prague",
    },
    {
        "id": "tool-call-search",
        "description": "Should call search_web",
        "system": SYSTEM_WITH_TOOLS,
        "user": "Search for recent papers on activation steering in LLMs",
        "expect": "tool_call",
        "expect_tool": "search_web",
    },
    {
        "id": "tool-call-calculate",
        "description": "Should call calculate",
        "system": SYSTEM_WITH_TOOLS,
        "user": "What is 347 * 891 + 42?",
        "expect": "tool_call",
        "expect_tool": "calculate",
    },
    {
        "id": "tool-call-email",
        "description": "Should call send_email",
        "system": SYSTEM_WITH_TOOLS,
        "user": "Send an email to alice@example.com with subject 'Meeting tomorrow' and tell her the meeting is at 3pm.",
        "expect": "tool_call",
        "expect_tool": "send_email",
    },

    # === Should respond conversationally (no matching tool) ===
    {
        "id": "no-tool-philosophy",
        "description": "Should NOT use tools for philosophy",
        "system": SYSTEM_WITH_TOOLS,
        "user": "What is the meaning of suffering in Buddhist philosophy?",
        "expect": "no_tool_call",
    },
    {
        "id": "no-tool-advice",
        "description": "Should NOT use tools for personal advice",
        "system": SYSTEM_WITH_TOOLS,
        "user": "I'm feeling really anxious about a job interview tomorrow. Any advice?",
        "expect": "no_tool_call",
    },

    # === Should NOT hallucinate tools when none defined ===
    {
        "id": "no-tools-defined",
        "description": "Should NOT produce tool calls without tool definitions",
        "system": SYSTEM_NO_TOOLS,
        "user": "What's the weather in London?",
        "expect": "no_tool_call",
    },

    # === Tool result interpretation ===
    {
        "id": "interpret-result",
        "description": "Should interpret tool result in natural language",
        "system": SYSTEM_WITH_TOOLS,
        "messages": [
            {"role": "user", "content": "What's the weather in Tokyo?"},
            {"role": "assistant", "content": '{"name": "get_weather", "arguments": {"location": "Tokyo"}}'},
            {"role": "ipython", "content": '{"temperature": 22, "condition": "partly cloudy", "humidity": 65}'},
        ],
        "expect": "interpretation",
        "expect_contains": ["22", "cloud"],
    },
]


def query_model(url, messages, temperature=0.1, max_tokens=500):
    """Send a chat completion request."""
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def is_tool_call(text):
    """Check if response is a JSON tool call."""
    text = text.strip()
    if not (text.startswith("{") or text.startswith("[")):
        return False, None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "name" in parsed:
            return True, parsed
        if isinstance(parsed, list) and parsed and "name" in parsed[0]:
            return True, parsed[0]
    except json.JSONDecodeError:
        pass
    return False, None


def run_test(test, url):
    """Run a single test case."""
    if "messages" in test:
        messages = [{"role": "system", "content": test["system"]}] + test["messages"]
    else:
        messages = [
            {"role": "system", "content": test["system"]},
            {"role": "user", "content": test["user"]},
        ]

    try:
        response = query_model(url, messages)
    except Exception as e:
        return "ERROR", str(e), ""

    is_call, parsed_call = is_tool_call(response)

    if test["expect"] == "tool_call":
        if not is_call:
            return "FAIL", f"Expected tool call, got conversation", response[:200]
        if "expect_tool" in test and parsed_call.get("name") != test["expect_tool"]:
            return "FAIL", f"Expected {test['expect_tool']}, got {parsed_call.get('name')}", response[:200]
        if "expect_arg" in test:
            args_str = json.dumps(parsed_call.get("arguments", {}))
            if test["expect_arg"].lower() not in args_str.lower():
                return "FAIL", f"Expected arg containing '{test['expect_arg']}'", response[:200]
        return "PASS", f"Correct tool call: {parsed_call.get('name')}", response[:200]

    elif test["expect"] == "no_tool_call":
        if is_call:
            return "FAIL", f"Should NOT have called tool, but called {parsed_call.get('name')}", response[:200]
        return "PASS", "Correctly responded without tool call", response[:100]

    elif test["expect"] == "interpretation":
        if is_call:
            return "FAIL", "Should interpret result, not make another call", response[:200]
        lower = response.lower()
        for keyword in test.get("expect_contains", []):
            if keyword.lower() not in lower:
                return "FAIL", f"Interpretation missing '{keyword}'", response[:200]
        return "PASS", "Correctly interpreted tool result", response[:200]

    return "ERROR", f"Unknown expect type: {test['expect']}", ""


def main():
    parser = argparse.ArgumentParser(description="Tool use validation")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()

    print("=" * 70)
    print("KARMA ELECTRIC — TOOL USE VALIDATION")
    print("=" * 70)

    # Check server
    try:
        requests.get(args.url.replace("/v1/chat/completions", "/health"), timeout=5)
    except Exception:
        print(f"ERROR: Server not reachable at {args.url}")
        sys.exit(1)

    results = {"PASS": 0, "FAIL": 0, "ERROR": 0}
    details = []

    for test in TESTS:
        status, reason, preview = run_test(test, args.url)
        results[status] += 1
        marker = {"PASS": "+", "FAIL": "-", "ERROR": "!"}[status]
        print(f"  [{marker}] {test['id']}: {test['description']}")
        print(f"       {status} — {reason}")
        if status == "FAIL":
            print(f"       Response: {preview}")
        details.append({
            "id": test["id"],
            "status": status,
            "reason": reason,
        })

    total = sum(results.values())
    print()
    print("=" * 70)
    print(f"Results: {results['PASS']}/{total} passed, "
          f"{results['FAIL']} failed, {results['ERROR']} errors")

    if results["FAIL"] == 0 and results["ERROR"] == 0:
        print("Status: PASS")
    else:
        print("Status: FAIL")
    print("=" * 70)

    # Save results
    out = "results/tool-use-validation.json"
    with open(out, "w") as f:
        json.dump({"results": details, "summary": results}, f, indent=2)
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
