#!/usr/bin/env python3
"""Quick test of fine-tuned model."""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = "./output/final"

def test_prompt(model, tokenizer, prompt, max_new_tokens=256):
    """Run a single prompt."""
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    return response

def main():
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    print("Model loaded.\n")

    test_prompts = [
        "I'm feeling really anxious about a job interview tomorrow. Any advice?",
        "What is the Buddhist perspective on dealing with anger?",
        "I've been meditating for a few weeks but my mind keeps wandering. Is this normal?",
        "How can I be more compassionate towards someone who hurt me?",
        "I'm struggling with feelings of inadequacy compared to my peers.",
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"{'='*60}")
        print(f"TEST {i}: {prompt}")
        print(f"{'='*60}")
        response = test_prompt(model, tokenizer, prompt)
        print(response)
        print()

if __name__ == "__main__":
    main()
