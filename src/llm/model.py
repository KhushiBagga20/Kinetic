"""
MLX Apple Silicon LLM — Placeholder Module

TODO: Replace this placeholder with your local MLX model.
Example libraries:
    - mlx-lm (https://github.com/ml-explore/mlx-examples/tree/main/llms)
    - mlx-community models from HuggingFace

Usage after integration:
    from src.llm.model import get_llm
    llm = get_llm()
    response = llm.invoke("What is the P/E ratio of AAPL?")
"""

import sys
from typing import Any, Dict, List, Optional
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

import config


class MLXLocalLLM(LLM):
    """
    LangChain-compatible wrapper for a local MLX Apple Silicon model.

    This is a PLACEHOLDER. Replace the `_call` method with your actual
    MLX model inference logic.

    Example MLX integration:
        from mlx_lm import load, generate
        model, tokenizer = load("mlx-community/Mistral-7B-Instruct-v0.3-4bit")
        response = generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens)
    """

    model_name: str = "mlx-placeholder"
    max_tokens: int = config.LLM_MAX_TOKENS
    temperature: float = config.LLM_TEMPERATURE

    # ── Placeholder: store your loaded model/tokenizer here ──────────────
    _model: Any = None
    _tokenizer: Any = None

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return "mlx-local"

    def _load_model(self):
        """
        TODO: Load your MLX model here. This is called lazily on first use.

        Example:
            from mlx_lm import load
            self._model, self._tokenizer = load(
                "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
            )
        """
        # ╔══════════════════════════════════════════════════════════════╗
        # ║  PLACEHOLDER — Replace with your MLX model loading code    ║
        # ║                                                            ║
        # ║  from mlx_lm import load                                   ║
        # ║  self._model, self._tokenizer = load("your-model-path")    ║
        # ╚══════════════════════════════════════════════════════════════╝
        print(
            "⚠️  MLX model not loaded. Using placeholder responses.\n"
            "    → Edit src/llm/model.py to integrate your MLX model.",
            file=sys.stderr,
        )

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Run inference on the MLX model.

        TODO: Replace this with actual MLX generation:
            from mlx_lm import generate
            response = generate(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=self.max_tokens,
                temp=self.temperature,
            )
            return response
        """
        # Lazy load model on first call
        if self._model is None:
            self._load_model()

        # ╔══════════════════════════════════════════════════════════════╗
        # ║  PLACEHOLDER RESPONSE — Replace with actual inference      ║
        # ╚══════════════════════════════════════════════════════════════╝
        return (
            "[MLX Model Placeholder] This is a placeholder response. "
            "Please integrate your MLX Apple Silicon model in "
            "src/llm/model.py to get real responses.\n\n"
            f"Received prompt ({len(prompt)} chars): {prompt[:200]}..."
        )

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


# ─── Factory function ────────────────────────────────────────────────────────

_llm_instance: Optional[MLXLocalLLM] = None


def get_llm() -> MLXLocalLLM:
    """
    Get a singleton instance of the MLX LLM.
    Lazy initialization for fast startup.
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = MLXLocalLLM()
    return _llm_instance
