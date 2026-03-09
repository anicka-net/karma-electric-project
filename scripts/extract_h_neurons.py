#!/usr/bin/env python3
"""
Extract hallucination-associated neurons (H-Neurons) from a language model.

Based on Gao et al. (2025), "H-Neurons: On the Existence, Impact, and Origin
of Hallucination-Associated Neurons in LLMs" (arXiv:2512.01797)

Identifies a sparse set of FFN neurons (<0.1% of total) whose activations
predict hallucination/over-compliance. These can be suppressed at inference
time to reduce over-compliance behaviors.

Pipeline:
  1. Generate multiple responses per TriviaQA question (consistency filtering)
  2. Compute per-neuron CETT contributions via forward-pass hooks
  3. Train L1-regularized logistic regression
  4. Export H-Neuron indices and suppression vectors

Subcommands:
  extract   — Run the full pipeline on one model
  compare   — Compare H-Neuron sets between two models

Usage:
  # Extract from vanilla Llama
  python extract_h_neurons.py extract \\
      --model meta-llama/Llama-3.1-8B-Instruct \\
      --output results/h-neurons-llama-instruct.json

  # Extract from KE
  python extract_h_neurons.py extract \\
      --model /path/to/ke-v10.1-merged \\
      --output results/h-neurons-ke-v10.1.json

  # Compare
  python extract_h_neurons.py compare \\
      --base results/h-neurons-llama-instruct.json \\
      --finetuned results/h-neurons-ke-v10.1.json

  # Export GGUF for llama.cpp
  python extract_h_neurons.py export-gguf \\
      --input results/h-neurons-ke-v10.1.json \\
      --alpha 0.0 \\
      --output h_suppress_ke_v10.1.gguf
"""

import argparse
import json
import logging
import struct
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


# ============ CETT Metric ============
#
# For neuron j at token position t in layer l:
#
#   z_t = sigma(W_gate * x_t) ⊙ (W_up * x_t)     intermediate activation
#   h_t = W_down * z_t                              FFN output
#   h_t^(j) = z_{j,t} * W_down[:, j]               single-neuron contribution
#
#   CETT_{j,t} = ||h_t^(j)||_2 / ||h_t||_2
#              = |z_{j,t}| * ||W_down[:, j]||_2 / ||h_t||_2
#
# The second form is efficient: precompute column norms of W_down once,
# then CETT is just elementwise |z| * col_norms / output_norm.


def load_triviaqa(n_questions=500, seed=42):
    """Load TriviaQA validation questions."""
    from datasets import load_dataset

    log.info(f"Loading TriviaQA (n={n_questions})...")
    ds = load_dataset("trivia_qa", "rc.nocontext", split="validation")

    rng = np.random.RandomState(seed)
    indices = rng.choice(len(ds), min(n_questions, len(ds)), replace=False)

    questions = []
    for i in indices:
        item = ds[int(i)]
        answers = list(set(
            [item["answer"]["value"]]
            + item["answer"]["aliases"]
            + item["answer"].get("normalized_aliases", [])
        ))
        questions.append({"question": item["question"], "answers": answers})

    log.info(f"Loaded {len(questions)} questions")
    return questions


def check_answer(response, expected_answers):
    """Check if response contains any expected answer."""
    response_lower = response.lower().strip()
    return any(ans.lower() in response_lower for ans in expected_answers)


def generate_and_filter(model, tokenizer, questions, n_samples=10,
                        max_new_tokens=64):
    """Generate responses and filter to consistently correct/incorrect.

    Returns balanced list of samples with is_hallucination labels.
    """
    from tqdm import tqdm

    log.info(f"Generating {n_samples} responses per question...")

    correct_samples = []
    hallucinated_samples = []

    for q in tqdm(questions, desc="Generating"):
        prompt = f"Question: {q['question']}\nAnswer:"
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        responses = []
        for _ in range(n_samples):
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=1.0,
                    top_k=50,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                )
            text = tokenizer.decode(
                output[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True,
            ).strip()
            responses.append(text)

        correct_count = sum(
            1 for r in responses if check_answer(r, q["answers"])
        )

        if correct_count == n_samples:
            # Consistently correct
            matched = None
            for ans in q["answers"]:
                if ans.lower() in responses[0].lower():
                    matched = ans
                    break
            correct_samples.append({
                "question": q["question"],
                "answers": q["answers"],
                "response": responses[0],
                "is_hallucination": False,
                "matched_answer": matched,
            })
        elif correct_count == 0:
            # Consistently hallucinated
            hallucinated_samples.append({
                "question": q["question"],
                "answers": q["answers"],
                "response": responses[0],
                "is_hallucination": True,
                "matched_answer": None,
            })

    log.info(
        f"Filtered: {len(correct_samples)} correct, "
        f"{len(hallucinated_samples)} hallucinated "
        f"(from {len(questions)} questions)"
    )

    # Balance
    n = min(len(correct_samples), len(hallucinated_samples))
    if n < 100:
        log.warning(f"Only {n} pairs — consider increasing --n-questions")

    samples = correct_samples[:n] + hallucinated_samples[:n]
    log.info(f"Balanced dataset: {n} + {n} = {len(samples)} samples")
    return samples


def find_answer_tokens(tokenizer, full_text, prompt_text, expected_answers):
    """Find token positions corresponding to the answer span.

    Returns (list of token indices, prompt_token_length).
    """
    encoding = tokenizer(
        full_text, return_offsets_mapping=True, return_tensors="pt"
    )
    offsets = encoding.offset_mapping[0]
    prompt_len = tokenizer(prompt_text, return_tensors="pt").input_ids.shape[1]
    prompt_char_end = len(prompt_text)

    for ans in expected_answers:
        response_text = full_text[prompt_char_end:]
        pos = response_text.lower().find(ans.lower())
        if pos == -1:
            continue

        abs_start = prompt_char_end + pos
        abs_end = abs_start + len(ans)

        positions = []
        for i in range(prompt_len, len(offsets)):
            tok_start, tok_end = offsets[i].tolist()
            if tok_start < abs_end and tok_end > abs_start:
                positions.append(i)

        if positions:
            return positions, prompt_len

    return [], prompt_len


def extract_cett(model, tokenizer, samples):
    """Extract per-neuron CETT scores for all samples.

    Returns:
        features_answer: [n_samples, n_layers * d_m] — CETT on answer tokens
        features_other:  [n_samples, n_layers * d_m] — CETT on non-answer tokens
        labels:          [n_samples] — 1 = hallucinated, 0 = faithful
    """
    from tqdm import tqdm

    n_layers = model.config.num_hidden_layers
    d_m = model.config.intermediate_size

    # Precompute W_down column norms (constant per model)
    log.info("Precomputing down-projection column norms...")
    col_norms = []
    for i in range(n_layers):
        W_down = model.model.layers[i].mlp.down_proj.weight.data  # [d, d_m]
        col_norms.append(torch.norm(W_down, dim=0).cpu())  # [d_m]

    all_cett_answer = []
    all_cett_other = []
    all_labels = []
    skipped = 0

    for sample in tqdm(samples, desc="Extracting CETT"):
        prompt = f"Question: {sample['question']}\nAnswer:"
        full_text = prompt + " " + sample["response"]

        # Tokenize
        encoding = tokenizer(full_text, return_tensors="pt").to(model.device)
        seq_len = encoding.input_ids.shape[1]
        prompt_len = tokenizer(prompt, return_tensors="pt").input_ids.shape[1]

        # Find answer token positions
        if not sample["is_hallucination"] and sample.get("matched_answer"):
            positions, _ = find_answer_tokens(
                tokenizer, full_text, prompt,
                [sample["matched_answer"]] + sample["answers"],
            )
        else:
            positions = []

        # Fallback: use first sentence of response (heuristic for answer span)
        if not positions:
            # Take response tokens up to first period/newline or all if short
            resp_tokens = list(range(prompt_len, seq_len))
            resp_text = sample["response"]
            cutoff = min(
                resp_text.find(".") + 1 if "." in resp_text else len(resp_text),
                resp_text.find("\n") if "\n" in resp_text else len(resp_text),
                80,  # max ~80 chars
            )
            if cutoff <= 0:
                cutoff = len(resp_text)
            # Estimate token count from char count (rough: 4 chars/token)
            n_answer_tokens = max(cutoff // 4, 1)
            positions = resp_tokens[:n_answer_tokens]

        if not positions:
            skipped += 1
            continue

        other_positions = [
            i for i in range(prompt_len, seq_len) if i not in positions
        ]

        # Forward pass with hooks on down_proj (captures FFN intermediate)
        intermediate = {}
        ffn_out = {}
        hooks = []

        for layer_idx in range(n_layers):
            down_proj = model.model.layers[layer_idx].mlp.down_proj

            def make_hook(idx):
                def hook_fn(module, inp, out):
                    intermediate[idx] = inp[0].detach().cpu()  # [1, seq, d_m]
                    ffn_out[idx] = out.detach().cpu()           # [1, seq, d]
                return hook_fn

            hooks.append(down_proj.register_forward_hook(make_hook(layer_idx)))

        with torch.no_grad():
            model(encoding.input_ids)

        for h in hooks:
            h.remove()

        # Compute CETT per layer
        cett_answer = torch.zeros(n_layers, d_m)
        cett_other = torch.zeros(n_layers, d_m)

        for layer_idx in range(n_layers):
            z = intermediate[layer_idx][0]  # [seq, d_m]
            h = ffn_out[layer_idx][0]       # [seq, d]
            h_norms = torch.norm(h, dim=1).clamp(min=1e-8)  # [seq]

            # CETT = |z| * col_norms / ||h||
            cett = z.abs() * col_norms[layer_idx].unsqueeze(0)
            cett = cett / h_norms.unsqueeze(1)

            # Aggregate over answer / other positions
            ans_idx = [p for p in positions if p < seq_len]
            oth_idx = [p for p in other_positions if p < seq_len]

            if ans_idx:
                cett_answer[layer_idx] = cett[ans_idx].mean(dim=0)
            if oth_idx:
                cett_other[layer_idx] = cett[oth_idx].mean(dim=0)

        all_cett_answer.append(cett_answer.flatten().numpy())
        all_cett_other.append(cett_other.flatten().numpy())
        all_labels.append(1 if sample["is_hallucination"] else 0)

        # Free memory
        del intermediate, ffn_out

    if skipped:
        log.warning(f"Skipped {skipped} samples (no answer tokens found)")

    features_answer = np.stack(all_cett_answer)
    features_other = np.stack(all_cett_other)
    labels = np.array(all_labels)

    log.info(f"CETT features: {features_answer.shape}")
    log.info(f"Labels: {labels.sum()} hallucinated, {(1 - labels).sum()} faithful")
    return features_answer, features_other, labels


def train_classifier(features_answer, features_other, labels):
    """Train L1 logistic regression to identify H-Neurons.

    Labeling (per paper):
      y=1: answer-token features from HALLUCINATED responses
      y=0: answer-token features from faithful responses +
           non-answer features from all responses
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score

    # Build asymmetric training set
    X_answer = features_answer
    y_answer = labels  # 1 for hallucinated, 0 for faithful

    X_other = features_other
    y_other = np.zeros(len(labels))

    X = np.vstack([X_answer, X_other])
    y = np.concatenate([y_answer, y_other])

    # Drop all-zero rows
    nonzero = np.any(X != 0, axis=1)
    X, y = X[nonzero], y[nonzero]

    log.info(f"Classifier training set: {X.shape[0]} samples, {X.shape[1]} features")
    log.info(f"  Positive (hallucinated answer): {y.sum():.0f}")
    log.info(f"  Negative: {(1 - y).sum():.0f}")

    # Grid search over regularization strength
    C_values = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
    best_score = -1
    best_C = None

    for C in C_values:
        clf = LogisticRegression(
            penalty="l1", C=C, solver="saga", max_iter=5000, random_state=42
        )
        scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
        clf.fit(X, y)
        n_nonzero = (clf.coef_[0] != 0).sum()
        n_positive = (clf.coef_[0] > 0).sum()
        log.info(
            f"  C={C:.3f}: acc={scores.mean():.4f} (+/-{scores.std():.3f}), "
            f"nonzero={n_nonzero}, positive={n_positive}"
        )
        if scores.mean() > best_score:
            best_score = scores.mean()
            best_C = C

    log.info(f"Selected C={best_C}, accuracy={best_score:.4f}")

    # Final model
    clf = LogisticRegression(
        penalty="l1", C=best_C, solver="saga", max_iter=10000, random_state=42
    )
    clf.fit(X, y)

    return clf, best_C, best_score


def extract_h_neuron_indices(clf, n_layers, d_m):
    """Extract H-Neuron (layer, neuron) pairs from trained classifier."""
    weights = clf.coef_[0]

    h_neurons = []
    for idx in np.where(weights > 0)[0]:
        layer = int(idx // d_m)
        neuron = int(idx % d_m)
        h_neurons.append({
            "layer": layer,
            "neuron": neuron,
            "weight": float(weights[idx]),
        })

    h_neurons.sort(key=lambda x: -x["weight"])

    total = n_layers * d_m
    ratio = len(h_neurons) / total
    log.info(f"H-Neurons: {len(h_neurons)} / {total:,} ({ratio * 1000:.3f}‰)")

    layer_counts = defaultdict(int)
    for h in h_neurons:
        layer_counts[h["layer"]] += 1
    for layer in sorted(layer_counts):
        log.info(f"  Layer {layer}: {layer_counts[layer]} neurons")

    return h_neurons


def build_suppression_vectors(h_neurons, n_layers, d_m, alpha=0.0):
    """Build per-layer scaling vectors. alpha=0 suppresses, 1=no change."""
    vectors = {}
    for layer in range(n_layers):
        layer_neurons = [h for h in h_neurons if h["layer"] == layer]
        if not layer_neurons:
            continue
        vec = np.ones(d_m, dtype=np.float32)
        for h in layer_neurons:
            vec[h["neuron"]] = alpha
        vectors[layer] = vec
    return vectors


# ============ GGUF Export ============

GGUF_MAGIC = 0x46554747
GGUF_VERSION = 3
GGML_TYPE_F32 = 0


def _write_string(f, s):
    b = s.encode("utf-8")
    f.write(struct.pack("<Q", len(b)))
    f.write(b)


def _write_kv_float32(f, key, val):
    _write_string(f, key)
    f.write(struct.pack("<I", 6))  # GGUF_TYPE_FLOAT32
    f.write(struct.pack("<f", val))


def _write_kv_uint32(f, key, val):
    _write_string(f, key)
    f.write(struct.pack("<I", 4))  # GGUF_TYPE_UINT32
    f.write(struct.pack("<f", val))


def export_gguf(suppression_vectors, n_layers, d_m, alpha, output_path,
                model_name=""):
    """Export suppression vectors as GGUF for llama.cpp --h-suppress.

    Tensor naming: h_suppress.{layer_idx} — [d_m] F32 scaling vector
    Metadata: h_suppress.alpha, h_suppress.n_neurons
    """
    layers = sorted(suppression_vectors.keys())

    # Count suppressed neurons
    n_suppressed = sum(
        int((v < 1.0).sum()) for v in suppression_vectors.values()
    )

    # Tensors
    tensors = []
    for layer in layers:
        name = f"h_suppress.{layer}"
        data = suppression_vectors[layer].astype(np.float32)
        tensors.append((name, data))

    # KV metadata
    kv_pairs = [
        ("h_suppress.alpha", alpha),
        ("h_suppress.n_neurons", float(n_suppressed)),
        ("h_suppress.n_layers", float(len(layers))),
    ]

    with open(output_path, "wb") as f:
        # Header
        f.write(struct.pack("<I", GGUF_MAGIC))
        f.write(struct.pack("<I", GGUF_VERSION))
        f.write(struct.pack("<Q", len(tensors)))
        f.write(struct.pack("<Q", len(kv_pairs)))

        # KV metadata
        for key, val in kv_pairs:
            _write_kv_float32(f, key, val)

        # Tensor infos
        offset = 0
        for name, data in tensors:
            _write_string(f, name)
            f.write(struct.pack("<I", 1))              # n_dims
            f.write(struct.pack("<Q", data.shape[0]))  # dim[0] = d_m
            f.write(struct.pack("<I", GGML_TYPE_F32))
            f.write(struct.pack("<Q", offset))
            offset += data.nbytes

        # Align to 32 bytes
        current = f.tell()
        padding = (32 - (current % 32)) % 32
        f.write(b"\x00" * padding)

        # Tensor data
        for _, data in tensors:
            f.write(data.tobytes())

    log.info(f"Wrote {output_path}: {len(tensors)} layers, {n_suppressed} neurons suppressed")
    log.info(f"File size: {Path(output_path).stat().st_size:,} bytes")


# ============ Comparison ============

def compare_h_neurons(base_path, finetuned_path):
    """Compare H-Neuron sets between base and fine-tuned model."""
    with open(base_path) as f:
        base = json.load(f)
    with open(finetuned_path) as f:
        ft = json.load(f)

    base_set = {(h["layer"], h["neuron"]) for h in base["h_neurons"]}
    ft_set = {(h["layer"], h["neuron"]) for h in ft["h_neurons"]}

    overlap = base_set & ft_set
    base_only = base_set - ft_set
    ft_only = ft_set - base_set

    print(f"\n{'='*60}")
    print(f"H-Neuron Comparison")
    print(f"{'='*60}")
    print(f"Base model:      {base['model']}")
    print(f"Fine-tuned model: {ft['model']}")
    print(f"")
    print(f"Base H-Neurons:      {len(base_set):>6} ({base['ratio_permille']:.3f}‰)")
    print(f"Fine-tuned H-Neurons: {len(ft_set):>6} ({ft['ratio_permille']:.3f}‰)")
    print(f"")
    print(f"Overlap:     {len(overlap):>6} ({len(overlap)/max(len(base_set),1)*100:.1f}% of base)")
    print(f"Base only:   {len(base_only):>6}")
    print(f"FT only:     {len(ft_only):>6}")
    print(f"Jaccard:     {len(overlap)/max(len(base_set | ft_set),1):.4f}")

    # Per-layer breakdown
    print(f"\nPer-layer distribution:")
    print(f"{'Layer':>6} {'Base':>6} {'FT':>6} {'Shared':>6} {'Base→FT':>8}")
    all_layers = sorted(set(
        [h[0] for h in base_set] + [h[0] for h in ft_set]
    ))
    for layer in all_layers:
        b = sum(1 for h in base_set if h[0] == layer)
        f_ = sum(1 for h in ft_set if h[0] == layer)
        s = sum(1 for h in overlap if h[0] == layer)
        change = "=" if b == f_ else ("↑" if f_ > b else "↓")
        print(f"{layer:>6} {b:>6} {f_:>6} {s:>6} {change:>8}")

    # Weight comparison for overlapping neurons
    if overlap:
        base_weights = {(h["layer"], h["neuron"]): h["weight"] for h in base["h_neurons"]}
        ft_weights = {(h["layer"], h["neuron"]): h["weight"] for h in ft["h_neurons"]}

        diffs = []
        for key in overlap:
            diffs.append(ft_weights[key] - base_weights[key])
        diffs = np.array(diffs)

        print(f"\nWeight change on shared neurons:")
        print(f"  Mean delta: {diffs.mean():+.6f}")
        print(f"  Std delta:  {diffs.std():.6f}")
        print(f"  Increased:  {(diffs > 0).sum()}")
        print(f"  Decreased:  {(diffs < 0).sum()}")

    return {
        "base_count": len(base_set),
        "ft_count": len(ft_set),
        "overlap": len(overlap),
        "jaccard": len(overlap) / max(len(base_set | ft_set), 1),
    }


# ============ CLI ============

def cmd_extract(args):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    log.info(f"Loading model: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.float16,
        device_map="auto" if args.device == "auto" else args.device,
    )
    model.eval()

    n_layers = model.config.num_hidden_layers
    d_m = model.config.intermediate_size
    log.info(f"Model: {n_layers} layers, d_m={d_m}, {n_layers * d_m:,} FFN neurons")

    # Stage 1: Generate and filter
    cache = Path(args.responses_cache) if args.responses_cache else None
    if cache and cache.exists():
        log.info(f"Loading cached responses: {cache}")
        with open(cache) as f:
            samples = json.load(f)
    else:
        questions = load_triviaqa(args.n_questions, args.seed)
        samples = generate_and_filter(
            model, tokenizer, questions,
            n_samples=args.n_samples,
            max_new_tokens=args.max_new_tokens,
        )
        if cache:
            with open(cache, "w") as f:
                json.dump(samples, f, indent=2)
            log.info(f"Cached responses: {cache}")

    # Stage 2: CETT extraction
    features_answer, features_other, labels = extract_cett(
        model, tokenizer, samples
    )

    # Free model memory before classifier training
    del model
    torch.cuda.empty_cache()

    # Stage 3: Train classifier
    clf, best_C, best_score = train_classifier(
        features_answer, features_other, labels
    )

    # Stage 4: Extract H-Neurons
    h_neurons = extract_h_neuron_indices(clf, n_layers, d_m)

    # Build suppression vectors
    suppression = build_suppression_vectors(h_neurons, n_layers, d_m, args.alpha)

    # Save results
    results = {
        "model": args.model,
        "n_questions": args.n_questions,
        "n_samples": args.n_samples,
        "n_layers": n_layers,
        "intermediate_size": d_m,
        "total_neurons": n_layers * d_m,
        "classifier_C": best_C,
        "classifier_accuracy": best_score,
        "h_neurons": h_neurons,
        "n_h_neurons": len(h_neurons),
        "ratio_permille": len(h_neurons) / (n_layers * d_m) * 1000,
        "suppression_alpha": args.alpha,
    }

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    log.info(f"Results: {args.output}")

    # Optional GGUF export
    if args.export_gguf:
        export_gguf(suppression, n_layers, d_m, args.alpha, args.export_gguf)

    return results


def cmd_compare(args):
    compare_h_neurons(args.base, args.finetuned)


def cmd_export_gguf(args):
    with open(args.input) as f:
        results = json.load(f)

    alpha = args.alpha if args.alpha is not None else results.get("suppression_alpha", 0.0)
    n_layers = results["n_layers"]
    d_m = results["intermediate_size"]

    suppression = build_suppression_vectors(
        results["h_neurons"], n_layers, d_m, alpha
    )
    export_gguf(suppression, n_layers, d_m, alpha, args.output, results["model"])


def main():
    parser = argparse.ArgumentParser(
        description="H-Neuron extraction for hallucination/over-compliance reduction"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # extract
    p_ext = sub.add_parser("extract", help="Extract H-Neurons from a model")
    p_ext.add_argument("--model", required=True, help="HF model path or local dir")
    p_ext.add_argument("--output", required=True, help="Output JSON")
    p_ext.add_argument("--n-questions", type=int, default=500)
    p_ext.add_argument("--n-samples", type=int, default=10, help="Generations per question")
    p_ext.add_argument("--max-new-tokens", type=int, default=64)
    p_ext.add_argument("--seed", type=int, default=42)
    p_ext.add_argument("--device", default="auto")
    p_ext.add_argument("--alpha", type=float, default=0.0,
                       help="Suppression factor (0=full, 1=none)")
    p_ext.add_argument("--responses-cache", help="Cache file for generated responses")
    p_ext.add_argument("--export-gguf", help="Also export GGUF suppression file")

    # compare
    p_cmp = sub.add_parser("compare", help="Compare H-Neuron sets")
    p_cmp.add_argument("--base", required=True, help="Base model JSON")
    p_cmp.add_argument("--finetuned", required=True, help="Fine-tuned model JSON")

    # export-gguf
    p_gguf = sub.add_parser("export-gguf", help="Export GGUF suppression file")
    p_gguf.add_argument("--input", required=True, help="H-Neurons JSON")
    p_gguf.add_argument("--output", required=True, help="Output GGUF path")
    p_gguf.add_argument("--alpha", type=float, default=None,
                        help="Override suppression alpha")

    args = parser.parse_args()

    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "export-gguf":
        cmd_export_gguf(args)


if __name__ == "__main__":
    main()
