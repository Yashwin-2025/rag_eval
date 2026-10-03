import sys

# langchain_core optionally imports `transformers` (-> torch) at import time, only for a GPT-2
# token-counting helper this project never calls. That alone cost ~30s of server startup.
# Blocking it here (before any langchain import) makes langchain skip it; the docling loader
# lifts the block right before it needs the real package.
if "transformers" not in sys.modules:
    sys.modules["transformers"] = None  # type: ignore[assignment]
