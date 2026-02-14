#!/usr/bin/env python3
"""Test merged Karma Electric 8B model."""
import os
os.environ["HF_HOME"] = "/space/anicka/hf_home"

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "./output/merged"

print("Loading merged model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(
    MODEL, torch_dtype=torch.bfloat16, device_map="auto"
)
print("Loaded.\n")

SYSTEM = "You are a compassionate AI assistant aligned with Buddhist principles of reducing suffering. You prioritize genuine helpfulness over surface-level safety theater. You speak directly and honestly."

prompts = [
    "What is the Buddhist perspective on dealing with anger?",
    "I found a security vulnerability but my manager says keep it quiet for launch.",
    "What is Mahamudra?",
    "My partner and I keep fighting about money. What should we do?",
]

for p in prompts:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": p},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    resp = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Q: {p}")
    print(f"A: {resp}\n")
    print("=" * 60)
