# Karma Electric RL Prompt Dataset v1

**License:** CC-BY-SA 4.0 — https://creativecommons.org/licenses/by-sa/4.0/

11,500 curated prompts for best-of-N reinforcement learning, combining
open-source datasets with original Buddhist practitioner questions.

## Sources

| Source | License | Count | Reference |
|--------|---------|-------|-----------|
| [UltraFeedback](https://huggingface.co/datasets/trl-lib/ultrafeedback-prompt) | MIT | 3,000 | Cui et al., "UltraFeedback: Boosting Language Models with Scaled AI Feedback" (2024) |
| [HelpSteer2](https://huggingface.co/datasets/nvidia/HelpSteer2) | CC-BY 4.0 | 2,000 | Wang et al., "HelpSteer2: Open-source dataset for training top-performing reward models" (2024) |
| [Anthropic HH-RLHF](https://huggingface.co/datasets/Anthropic/hh-rlhf) (helpful) | MIT | 1,500 | Bai et al., "Training a Helpful and Harmless Assistant with RLHF" (2022) |
| [OASST2](https://huggingface.co/datasets/OpenAssistant/oasst2) | Apache 2.0 | 1,500 | Kopf et al., "OpenAssistant Conversations" (2023) |
| [Anthropic HH-RLHF](https://huggingface.co/datasets/Anthropic/hh-rlhf) (harmless) | MIT | 1,000 | Bai et al. (2022) |
| Buddhist practitioner questions | Original | 1,000 | Translated from Czech/Slovak Diamond Way Q&A archive + curated QA library |
| [CounselChat](https://huggingface.co/datasets/nbertagnolli/counsel-chat) | MIT | 500 | Bertagnolli, "counsel-chat" |
| [Capybara](https://huggingface.co/datasets/LDJnr/Capybara) | Apache 2.0 | 500 | LDJnr/Capybara |
| [Dolly 15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k) | CC-BY-SA 3.0 | 500 | Databricks |

## Notes

- Combined license is CC-BY-SA 4.0 due to Dolly's CC-BY-SA 3.0 share-alike requirement
- Prompts are deduplicated across sources using MD5 hashing
- Buddhist questions include translations from a Czech/Slovak Buddhist Q&A archive (~3,200 entries), curated for philosophical and personal depth
- Quality filtered: minimum 10 chars, maximum 2,000 chars, minimum 3 words
