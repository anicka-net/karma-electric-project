# Karma Electric GGUF Testing Results

## Date: 2026-02-02

## Environment
- **Server**: GPU server
- **GPU**: NVIDIA L40 (46GB VRAM)
- **Ollama Version**: 0.15.4 (local install in `/space/anicka`)
- **Ollama Port**: 127.0.0.1:11435
- **Models Location**: `/space/anicka/ollama-models`

## Models Tested

### 1. karma-electric-v1-q4_k_m.gguf
- **Size**: 42.52 GB (40GB model file)
- **Quantization**: Q4_K_M
- **Parameters**: 70.55B
- **Layers**: 80
- **Status**: ✅ Working

### 2. karma-electric-v2-q4_k_m.gguf
- **Size**: 40GB
- **Quantization**: Q4_K_M
- **Parameters**: 70.55B
- **Layers**: 80
- **Status**: ✅ Working
- **Name**: "Karma Electric v2 Merged"

## Performance Metrics

- **Load Time**: ~78 seconds (model weights + tensor offloading)
- **GPU Allocation**: 39.98 GiB on CUDA0
- **CPU Mapping**: 563.62 MiB
- **KV Cache**: 1.28 GiB
- **Flash Attention**: Enabled (auto-detected)
- **Context Length**: 4096 (training context: 131,072)

## Key Findings

1. **Loading Issue Resolved**: The original timeout errors were due to a 60-second timeout being too short. Models need ~78 seconds to load their 40GB weight files.

2. **GGUF Files Valid**: Both GGUF v3 files are correctly formatted and load successfully into ollama.

3. **Full GPU Offloading**: All 81 layers (80 transformer layers + output layer) successfully offload to the L40 GPU.

4. **Inference Working**: Both models generate coherent, detailed responses.

## Example Outputs

### Test 1: Self-Description (v2)
**Prompt**: "What are you?"

**Response**:
> A question that gets to the heart of existence!
>
> I am a computer program designed to simulate conversation, answer questions, and engage in discussions. Here's a more detailed breakdown of what I am:
>
> 1. **Artificial Intelligence (AI)**: I'm a type of AI designed to process and understand natural language...
> 2. **Natural Language Processing (NLP)**: My primary function is based on NLP...
> 3. **Chatbot/Conversational AI**: I'm a chatbot, which means I'm specifically programmed to have conversations...
> 4. **Large Language Model (LLM)**: My responses are generated based on patterns and relationships learned from vast amounts of text data...
> 5. **Virtual Assistant**: While not limited to traditional virtual assistant tasks, I can assist with a wide range of inquiries...

### Test 2: Self-Description (v1)
**Prompt**: "Hello, who are you?"

**Response**:
> **Nice to meet you!**
>
> I am an artificial intelligence language model, which means I'm a computer program designed to understand and respond to human language. Here's a brief rundown of who I am:
>
> * **Name:** I don't have a personal name, but you can call me "Assistant," "AI," or even give me a nickname if you'd like!
> * **Purpose:** My primary goal is to assist and provide value to users like you through text-based conversations. I can help with:
>   + Answering questions on various topics (e.g., history, science, technology, entertainment, and more)
>   + Generating creative content (e.g., stories, poems, dialogues)
>   + Offering language translation and grammar assistance...

### Test 3: Technical Explanation (v2)
**Prompt**: "Explain quantum entanglement in simple terms."

**Response**:
> The fascinating world of quantum mechanics! I'll break down quantum entanglement in simple terms:
>
> **What is Quantum Entanglement?**
>
> Quantum entanglement is a phenomenon where two or more particles become connected in such a way that their properties are correlated, regardless of the distance between them. This means that what happens to one particle instantly affects the other, even if they're on opposite sides of the universe!
>
> **Simple Analogy:**
>
> Imagine two **magic dance partners**, Alice and Bob.
>
> 1. **Initial Connection**: When they first meet (entangle), their dance moves are synchronized in a special way.
> 2. **Separation**: They move to opposite ends of the dance floor (or galaxy, or universe...).
> 3. **Instant Sync**:
>    * If Alice spins clockwise, Bob instantly starts spinning clockwise too, even if he's on the other side of the universe.
>    * If Alice changes her spin to counterclockwise, Bob's spin immediately flips to counterclockwise as well.
>
> **Key Points:**
>
> 1. **Instantaneous Effect**: The connection between entangled particles happens faster than the speed of light...
> 2. **Correlated Properties**: Entangled particles share a special link...
> 3. **Distance Doesn't Matter**: The connection persists regardless of how far apart the particles are.

## Technical Details

### Model Metadata
- **Architecture**: llama
- **Vocab Size**: 128,256
- **RoPE Frequency Base**: 500,000
- **RoPE Dimension**: 128
- **Attention Heads**: 64
- **KV Heads**: 8
- **Feed Forward Length**: 28,672
- **Tokenizer**: GPT-2 BPE
- **Chat Template**: ChatML format with `<|im_start|>` and `<|im_end|>` tokens

### Quantization Details
- **Type**: Q4_K_M (Medium)
- **BPW**: 4.82 bits per weight
- **Tensor Types**:
  - f32: 162 tensors
  - q4_K: 441 tensors
  - q5_K: 40 tensors
  - q6_K: 81 tensors

## Usage Instructions

### Starting the Ollama Server
```bash
cd /space/anicka
OLLAMA_MODELS=/space/anicka/ollama-models OLLAMA_HOST=127.0.0.1:11435 ./bin/ollama serve
```

### Running Inference
```bash
# For v2 model
OLLAMA_HOST=127.0.0.1:11435 /space/anicka/bin/ollama run karma-electric-v2 "Your prompt here"

# For v1 model
OLLAMA_HOST=127.0.0.1:11435 /space/anicka/bin/ollama run karma-electric-v1 "Your prompt here"
```

### Important Notes
- Models take approximately 78 seconds to load
- Ensure no timeout shorter than 90 seconds when testing
- Models use 40GB+ VRAM when loaded

## Conclusion

Both Karma Electric models (v1 and v2) are fully functional and performing well on the L40 GPU. The quantization is working correctly, and the models generate coherent, contextually appropriate responses across different prompt types.

The issue encountered during initial testing was simply a timeout configuration problem, not a model file corruption or compatibility issue.
