# H-Neuron Suppression in llama.cpp — Design

## Overview

Per-neuron scaling in FFN intermediate activations to suppress
hallucination-associated neurons (H-Neurons). Operates inside the FFN
layer, complementary to ACAP which operates on the residual stream.

Based on: Gao et al. (2025), "H-Neurons" (arXiv:2512.01797)

## Mechanism

In the FFN computation:
```
z_t = SiLU(W_gate * x_t) ⊙ (W_up * x_t)   ← intermediate activation
                                              ← H-SUPPRESS HERE: z_t *= scales
h_t = W_down * z_t                           ← output to residual stream
```

For identified H-Neurons (indices j), we scale `z_{j,t}` by α ∈ [0, 1]:
- α = 0: full suppression (zero out the neuron)
- α = 0.5: halve contribution
- α = 1: no change (passthrough)

## GGUF Format

Follows ACAP axis convention. File contains per-layer scaling vectors:

```
Tensors:    h_suppress.{layer_idx}     [d_m] F32    (e.g. d_m=14336 for Llama 8B)
Metadata:   h_suppress.alpha           float32      default suppression factor
            h_suppress.n_neurons       float32      total suppressed neuron count
            h_suppress.n_layers        float32      number of layers with suppression
```

Layers without H-Neurons are omitted (implied all-ones = no suppression).
File size: ~57KB per layer × affected layers. Typically 5-15 layers = ~300KB-900KB.

## Implementation (llama.cpp changes)

### 1. New adapter struct: `llama_adapter_h_suppress`

In `llama-adapter.h`:
```cpp
struct llama_adapter_h_suppress {
    ggml_tensor * tensor_for(int il) const;
    ggml_tensor * apply_to(ggml_context * ctx, ggml_tensor * cur, int il) const;

    bool apply(
        const llama_model & model,
        const float * data,
        size_t len,
        int32_t d_m,
        int32_t il);

private:
    bool init(const llama_model & model);
    std::vector<ggml_context_ptr> ctxs;
    std::vector<ggml_backend_buffer_ptr> bufs;
    std::vector<ggml_tensor *> tensors;  // per layer, [d_m] scaling vector
};
```

### 2. apply_to — the core operation

```cpp
ggml_tensor * llama_adapter_h_suppress::apply_to(
        ggml_context * ctx, ggml_tensor * cur, int il) const {
    ggml_tensor * scales = tensor_for(il);
    if (scales == nullptr) return cur;

    // cur shape: [d_m, n_tokens] (intermediate activation before down_proj)
    // scales shape: [d_m] — broadcast over tokens
    return ggml_mul(ctx, cur, scales);
}
```

This is a single elementwise multiply — much simpler than ACAP's
project-clamp-subtract. The `scales` tensor has 1.0 for normal neurons
and α for H-Neurons.

### 3. Hook point in build_ffn

In `llama-graph.cpp`, `build_ffn()`, just before the down-projection:

```cpp
    // After activation (SiLU/GELU/etc) and gate multiply, before down_proj:
    if (h_suppress) {
        cur = h_suppress->apply_to(ctx0, cur, il);
        cb(cur, "ffn_h_suppress", il);
    }

    if (down) {
        cur = build_lora_mm(down, cur);
    }
```

This goes at approximately line 1098 of llama-graph.cpp (current ACAP fork),
after the gate_par multiply and before the down_proj multiply.

### 4. CLI flag

```
--h-suppress FILE.gguf    Load H-Neuron suppression vectors
```

Loading follows the same pattern as `--acap`:
- Parse GGUF, read tensor names matching `h_suppress.{layer}`
- Copy data to appropriate backend buffers
- Store in model context

### 5. Files to modify

| File | Change |
|------|--------|
| `llama-adapter.h` | Add `llama_adapter_h_suppress` struct |
| `llama-adapter.cpp` | Implement `apply_to`, `apply`, `init`, tensor loading |
| `llama-graph.h` | Add `h_suppress` member to `llm_graph_context` |
| `llama-graph.cpp` | Call `h_suppress->apply_to()` in `build_ffn()` |
| `llama-model.h` | Add `h_suppress` to model struct |
| `llama-model.cpp` | Load GGUF, instantiate adapter |
| `common/arg.cpp` | Add `--h-suppress` argument |
| `common/common.h` | Add field to params struct |

Estimated: ~150 lines across 8 files (modeled on the ACAP implementation
which was ~294 lines across 11 files, but H-suppress is simpler).

## Interaction with ACAP

Both can run simultaneously:
1. FFN computes intermediate activation z_t
2. **H-suppress** scales z_t (per-neuron, inside FFN)
3. FFN computes h_t = W_down * z_t (modified)
4. h_t added to residual stream
5. **ACAP** caps the residual stream (per-layer, after FFN)

They are orthogonal: H-suppress reduces over-compliance drive at the
neuron level, ACAP stabilizes persona at the representation level.

## Testing Plan

1. Run extraction on vanilla Llama 3.1 8B Instruct → H-Neurons JSON
2. Run extraction on KE v10.1 → H-Neurons JSON
3. Compare: overlap, layer distribution, weight drift
4. Export GGUF suppression file
5. Build llama.cpp with H-suppress support
6. Test on twilight CPU: conversation + reward evaluation
7. Validate: does suppression improve reward-hacking score? ACAP-neutral?
