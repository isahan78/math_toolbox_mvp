#!/usr/bin/env python3
"""
Multi-turn LLM + Virtual Tool Memoization
-----------------------------------------
- No single prompt or mega-string enumerating all tools:
  Each tool doc is stored in separate small variables.
- If a user question is "similar" (in this MVP: exact match),
  we reuse a memoized plan from last time => "virtual tool".
- Only SUM/PRODUCT are unreliable. Others are reliable.
- The LLM can discover the tools in a multi-turn conversation,
  asking "Which tools exist?" or "Tell me about the tool named X."
- If the plan is successful multiple times, we store it as a
  new "virtual tool" for that user question signature.

Usage:
  python multi_agent_toolbox.py
"""
#%%
import openai
import json
import random
import os
from typing import Dict, Any

# Possibly set your API key (or rely on environment variable):
openai.api_key = os.environ.get("OPENAI_API_KEY")

#%%
###############################################################################
# 1) Tools' Doc Snippets (all in separate small variables)
###############################################################################
DOC_SUM      = "SUM: unreliable add. Takes [a,b]. Fails ~40%. Else returns a+b."
DOC_PRODUCT  = "PRODUCT: unreliable multiply. Takes [a,b]. Fails ~40%. Else a*b."
DOC_DELTA    = "DELTA: reliable difference b-a. Takes [a,b]."
DOC_QUOTIENT = "QUOTIENT: reliable a/b. (error if b=0)."
DOC_MODULO   = "MODULO: reliable a%b. (error if b=0)."
DOC_POWER    = "POWER: reliable a**b."
DOC_ABS      = "ABS: reliable absolute(a). Takes [a], ignoring b."
#%%
###############################################################################
# 2) The Actual Tool Functions
###############################################################################
def unreliable_sum(a: float, b: float, fail_rate=0.4) -> float:
    if random.random() < fail_rate:
        return random.randint(-100, 100)
    else:
        return a + b

def unreliable_product(a: float, b: float, fail_rate=0.4) -> float:
    if random.random() < fail_rate:
        return random.randint(-100, 100)
    else:
        return a * b

def delta(a: float, b: float) -> float:
    return b - a

def quotient(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("Division by zero.")
    return a / b

def modulo(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("Modulo by zero.")
    return a % b

def power(a: float, b: float) -> float:
    return a ** b

def absolute(a: float) -> float:
    return abs(a)

def verify_unreliable(tool_name: str, a: float, b: float, candidate: float) -> bool:
    t = tool_name.upper()
    if t == "SUM":
        return (candidate == (a + b))
    elif t == "PRODUCT":
        return (candidate == (a * b))
    return True  # other tools are reliable anyway
#%%
###############################################################################
# 3) Minimal System Prompt (No big listing of all tools)
###############################################################################
SYSTEM_PROMPT = """\
You are a Planner LLM. You do NOT know which tools exist.
You may ask: "Which tools exist?" 
OR "Tell me about the tool named 'XYZ'" to discover them one by one.
Once you have enough info, produce a final JSON plan:
{
  "steps": [
    {"tool":"...", "args":[...]}, 
    ...
  ],
  "final_step_index": <index>
}
No extra text, just the final JSON when done.
"""
#%%
###############################################################################
# 4) Multi-turn conversation with the LLM (Planner)
###############################################################################
def conversation_with_planner(user_question: str) -> str:
    """
    We'll loop calls to openai.ChatCompletion until:
     - The LLM yields a JSON with "steps" & "final_step_index"
    If it asks "Which tools exist?" we give minimal list.
    If "Tell me about the tool named X," we give doc snippet for X only.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question}
    ]

    while True:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.0
        )
        content = resp.choices[0].message["content"].strip()
        role    = resp.choices[0].message["role"]

        # Check for final JSON
        if '"steps":' in content and '"final_step_index":' in content:
            return content  # done

        # else, it might ask about tools
        messages.append({"role": role, "content": content})
        lower_content = content.lower()

        if "which tools exist" in lower_content:
            # respond with a minimal name list only
            assistant_msg = "We have 7 tools: SUM, PRODUCT, DELTA, QUOTIENT, MODULO, POWER, ABS. Ask for doc by name if needed."
            messages.append({"role": "assistant", "content": assistant_msg})
            continue
        elif "tell me about the tool named" in lower_content:
            # parse which tool
            t = parse_tool_request(lower_content)
            snippet = get_tool_doc(t)
            messages.append({"role": "assistant", "content": snippet})
            continue
        else:
            # If no direct request for tool info, we nudge it
            messages.append({
                "role": "assistant",
                "content": "If you need more tool docs, ask specifically. Otherwise, produce the final JSON plan."
            })

def parse_tool_request(text: str) -> str:
    for t in ["sum","product","delta","quotient","modulo","power","abs"]:
        if t in text:
            return t
    return ""

def get_tool_doc(tool_name: str) -> str:
    if tool_name == "sum":      return DOC_SUM
    if tool_name == "product":  return DOC_PRODUCT
    if tool_name == "delta":    return DOC_DELTA
    if tool_name == "quotient": return DOC_QUOTIENT
    if tool_name == "modulo":   return DOC_MODULO
    if tool_name == "power":    return DOC_POWER
    if tool_name == "abs":      return DOC_ABS
    return "No such tool."
#%%
###############################################################################
# 5) Execute the final plan
###############################################################################
def execute_plan(plan_text: str) -> float:
    plan = json.loads(plan_text)  # might raise JSONDecodeError
    steps = plan.get("steps", [])
    final_idx = plan.get("final_step_index", len(steps)-1)
    if final_idx >= len(steps):
        raise ValueError("invalid final_step_index")

    results = []
    for i, stp in enumerate(steps):
        tool = stp.get("tool","").upper()
        args = stp.get("args", [])
        if tool == "SUM":
            if len(args)<2: raise ValueError("SUM needs 2 args")
            a, b = float(args[0]), float(args[1])
            out = unreliable_sum(a,b)
            if not verify_unreliable("SUM", a,b, out):
                out = a+b
        elif tool=="PRODUCT":
            if len(args)<2: raise ValueError("PRODUCT needs 2 args")
            a, b = float(args[0]), float(args[1])
            out = unreliable_product(a,b)
            if not verify_unreliable("PRODUCT", a,b, out):
                out = a*b
        elif tool=="DELTA":
            a, b = float(args[0]), float(args[1])
            out = delta(a,b)
        elif tool=="QUOTIENT":
            a, b = float(args[0]), float(args[1])
            out = quotient(a,b)
        elif tool=="MODULO":
            a, b = float(args[0]), float(args[1])
            out = modulo(a,b)
        elif tool=="POWER":
            a, b = float(args[0]), float(args[1])
            out = power(a,b)
        elif tool=="ABS":
            a = float(args[0])
            out = absolute(a)
        else:
            raise ValueError(f"Unknown tool '{tool}' at step {i}")

        results.append(out)

    return float(results[final_idx])
#%%
###############################################################################
# 6) Virtual Tools Caching / Memoization
###############################################################################
# We'll store a plan for each question signature after 2 successful uses
# In a real system, you'd do a more semantic approach
###############################################################################
virtual_tools: Dict[str, Dict[str, Any]] = {}
success_count: Dict[str, int]           = {}

def get_question_signature(question: str) -> str:
    """
    For an MVP, we do an exact string match.
    Real usage might do embeddings or classification.
    """
    return question.strip().lower()

def store_virtual_tool(signature: str, plan_text: str):
    """Store the plan in a dictionary so next time we skip LLM."""
    virtual_tools[signature] = {
        "plan_text": plan_text,
        # you might store time created, usage stats, etc.
    }
#%%
###############################################################################
# 7) ask_system => the user-facing function
###############################################################################
def ask_system(wordy_question: str) -> dict:
    """
    1) Check if we have a 'virtual tool' for this question signature.
    2) If yes, run that plan, skip LLM.
    3) If no, do multi-turn approach => get plan => run => store or increment usage
    4) If success repeated enough => store as virtual tool
    """
    sig = get_question_signature(wordy_question)
    if sig in virtual_tools:
        # We have a memoized plan for this question
        plan_text = virtual_tools[sig]["plan_text"]
        try:
            val = execute_plan(plan_text)
            return {
                "question": wordy_question,
                "plan": plan_text,
                "answer": val,
                "status": "success",
                "via": "virtual_tool"
            }
        except Exception as e:
            # If it fails for some reason, remove the tool or re-run LLM
            return {
                "question": wordy_question,
                "plan": plan_text,
                "error": str(e),
                "status": "fail",
                "via": "virtual_tool"
            }
    else:
        # We do the multi-turn approach
        plan_text = conversation_with_planner(wordy_question)
        try:
            val = execute_plan(plan_text)
            # success => increment usage
            old_count = success_count.get(sig, 0)
            new_count = old_count + 1
            success_count[sig] = new_count

            # if we have 2 successes => store as virtual tool
            if new_count == 2:
                store_virtual_tool(sig, plan_text)

            return {
                "question": wordy_question,
                "plan": plan_text,
                "answer": val,
                "status": "success",
                "via": "fresh_llm"
            }
        except Exception as e:
            return {
                "question": wordy_question,
                "plan": plan_text,
                "error": str(e),
                "status": "fail",
                "via": "fresh_llm"
            }

#%%
###############################################################################
# 8) Demo
###############################################################################
def main():
    # Example usage
    queries = [
        "John has 3 apples, Mary has 5. Combine them, then multiply the total by 2.",
        "Compute the difference of 10 and 3, then do product with 4.",
        "Compute the difference of 10 and 3, then do product with 4.",  # repeated => triggers storing memo
        "John has 3 apples, Mary has 5. Combine them, then multiply the total by 2.",  # repeated => uses memo
        "Compute the difference of 10 and 3, then do product with 4.", 
        "Absolute of -6, then sum 4 to that result."
    ]
    for q in queries:
        print("\nUser question:", q)
        result = ask_system(q)
        print("System =>", result)

if __name__ == "__main__":
    main()
# %%
