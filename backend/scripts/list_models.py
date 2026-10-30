"""Print the model ids your key can use, for the provider in LLM_PROVIDER.

Usage (from the repo root):  make models
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402

if config.LLM_PROVIDER == "openai":
    import openai

    ids = sorted(m.id for m in openai.OpenAI().models.list() if m.id.startswith(("gpt", "o")))
else:
    import anthropic

    ids = sorted(m.id for m in anthropic.Anthropic().models.list())

print(f"{config.LLM_PROVIDER}: {len(ids)} models")
for model_id in ids:
    print(" ", model_id)
