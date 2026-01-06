import logging
from typing import Optional, Any
from server.app.core.config import settings

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self) -> None:
        self.model: Optional[Any] = None
        self.device: Optional[str] = None

    def load(self) -> None:
        logger.info("Initializing model loader")
        if settings.use_mock_model:
            logger.info("Using mock model mode (no GPU required)")
            self.model = None
            self.device = "mock"
        else:
            logger.warning("Model loader is a placeholder - implement actual model loading")
            self.model = None
            self.device = "cuda" if self._check_cuda() else "cpu"
            if self.device == "cuda":
                self._assert_single_gpu()
        logger.info(f"Model loader initialized with device: {self.device}")

    def _assert_single_gpu(self) -> None:
        """Assert single-GPU usage for Step-1. Step-2 will support multi-GPU."""
        try:
            import torch
            gpu_count = torch.cuda.device_count()
            if gpu_count > 1:
                logger.warning(
                    f"Multiple GPUs detected ({gpu_count}). "
                    "Step-1 assumes single-GPU usage. "
                    "Multi-GPU support will be added in Step-2."
                )
            elif gpu_count == 0:
                logger.warning("No GPUs detected, falling back to CPU")
        except ImportError:
            pass

    def _check_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 0.7) -> str:
        if self.model is None:
            if settings.use_mock_model:
                return f"[MOCK] Generated {max_tokens} tokens for: {prompt[:50]}..."
            return f"[PLACEHOLDER] Generated response for prompt: {prompt[:50]}..."
        return self.model.generate(prompt, max_tokens, temperature)

