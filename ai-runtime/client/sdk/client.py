import requests
from typing import Optional
from shared.schemas.inference import InferenceRequest, InferenceResponse


class AIRuntimeClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def health_check(self) -> bool:
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("status") == "ok"
        except Exception:
            return False

    def infer(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> InferenceResponse:
        request_data = InferenceRequest(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        try:
            response = self.session.post(
                f"{self.base_url}/infer",
                json=request_data.model_dump(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return InferenceResponse(**response.json())
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Request failed: {str(e)}")

