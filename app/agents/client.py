import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import httpx
from app.core.config import settings
from app.core.errors import AppException

logger = logging.getLogger(__name__)

class TokenBudgetExceededError(AppException):
    def __init__(self, message: str, estimated_tokens: int, limit: int):
        super().__init__(
            code="TOKEN_BUDGET_EXCEEDED",
            message=message,
            status_code=413,
            details={"estimated_tokens": estimated_tokens, "limit": limit}
        )

class LLMServiceError(AppException):
    def __init__(self, message: str, status_code: int = 502, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="LLM_SERVICE_ERROR",
            message=message,
            status_code=status_code,
            details=details or {}
        )

class TokenBudget:
    """Manages context window estimation and reserves space for generation and schemas."""
    def __init__(self, max_context_tokens: int = 32768, reserved_output_tokens: int = 4096):
        self.max_context_tokens = max_context_tokens
        self.reserved_output_tokens = reserved_output_tokens
        self.max_input_tokens = max_context_tokens - reserved_output_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Fast conservative token estimation (~4 characters per token for English/Indonesian,
        plus overhead for structure).
        """
        if not text:
            return 0
        return max(1, len(text) // 4 + len(text.split()) // 8)

    def check_and_assert_budget(self, *text_blocks: str) -> int:
        total = sum(self.estimate_tokens(b) for b in text_blocks)
        if total > self.max_input_tokens:
            raise TokenBudgetExceededError(
                f"Input size ({total} estimated tokens) exceeds budget limit ({self.max_input_tokens} tokens).",
                estimated_tokens=total,
                limit=self.max_input_tokens
            )
        return total

class LLMResponse:
    def __init__(self, content: str, prompt_tokens: int = 0, completion_tokens: int = 0, model_used: str = "unknown"):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.model_used = model_used

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", json_mode: bool = True, max_tokens: int = 4096) -> LLMResponse:
        pass

class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic offline provider for unit/integration testing or when API key is unset.
    Allows registering specific canned responses or returning a default EditPlan.
    """
    def __init__(self):
        self._mock_responses: List[tuple[str, str]] = []
        self._default_response: str = json.dumps({
            "schema_version": "edit-plan/1.0",
            "document_id": "doc_mock",
            "document_version": 1,
            "instruction_summary": "Mock plan execution",
            "scope": {"allowed_node_ids": ["para_0"]},
            "operations": [],
            "used_reference_ids": [],
            "used_evidence_ids": [],
            "unsupported_claims": [],
            "warnings": [],
            "assumptions": []
        })

    def register_mock_response(self, instruction_substring: str, response: Union[str, Dict[str, Any]]) -> None:
        if isinstance(response, dict):
            res_str = json.dumps(response)
        else:
            res_str = response
        self._mock_responses.append((instruction_substring.lower(), res_str))

    def set_default_response(self, response: Union[str, Dict[str, Any]]) -> None:
        if isinstance(response, dict):
            self._default_response = json.dumps(response)
        else:
            self._default_response = response

    def generate(self, prompt: str, system_prompt: str = "", json_mode: bool = True, max_tokens: int = 4096) -> LLMResponse:
        full_text = (prompt + " " + system_prompt).lower()
        for pattern, res_str in self._mock_responses:
            if pattern in full_text:
                return LLMResponse(content=res_str, prompt_tokens=TokenBudget.estimate_tokens(prompt), completion_tokens=TokenBudget.estimate_tokens(res_str), model_used="mock-model")
        return LLMResponse(content=self._default_response, prompt_tokens=TokenBudget.estimate_tokens(prompt), completion_tokens=TokenBudget.estimate_tokens(self._default_response), model_used="mock-model")

class BlackboxLLMProvider(BaseLLMProvider):
    """
    Production HTTP wrapper for Blackbox / OpenAI-compatible endpoint with retries
    and ZDR eligibility compliance.
    """
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.BLACKBOX_API_KEY
        self.api_base = (api_base or settings.BLACKBOX_API_BASE).rstrip("/")
        raw_model = model or settings.BLACKBOX_MODEL or "blackboxai/deepseek/deepseek-v4-pro"
        if raw_model in ("deepseek-v4-pro", "blackboxai/deepseek-v4-pro"):
            self.model = "blackboxai/deepseek/deepseek-v4-pro"
        elif raw_model == "deepseek-v3":
            self.model = "blackboxai/deepseek/deepseek-v3"
        else:
            self.model = raw_model
        self.max_retries = 3

    def generate(self, prompt: str, system_prompt: str = "", json_mode: bool = True, max_tokens: int = 4096) -> LLMResponse:
        if not self.api_key:
            raise LLMServiceError("Missing API key for BlackboxLLMProvider.", status_code=500)

        # Blackbox API uses /chat/completions (or /v1/chat/completions)
        if self.api_base.endswith("/chat/completions"):
            url = self.api_base
        elif self.api_base.endswith("/v1"):
            url = f"{self.api_base}/chat/completions"
        else:
            url = f"{self.api_base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if settings.BLACKBOX_ZDR_REQUIRED:
            headers["X-ZDR-Enforce"] = "true"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1
        }
        # Blackbox API gateway rejects response_format for deepseek/blackboxai model groups
        if json_mode and "blackbox.ai" not in url and "blackboxai" not in self.model:
            payload["response_format"] = {"type": "json_object"}

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                
                # If Blackbox or any gateway returns 400 because response_format is unsupported, retry without it
                if response.status_code == 400 and "response_format" in payload:
                    logger.warning(f"API returned 400 with response_format. Retrying without response_format... Response: {response.text[:200]}")
                    payload.pop("response_format", None)
                    with httpx.Client(timeout=60.0) as client:
                        response = client.post(url, headers=headers, json=payload)

                if response.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    backoff = 2 ** attempt
                    logger.warning(f"LLM API returned status {response.status_code}. Retrying in {backoff}s (Attempt {attempt}/{self.max_retries})...")
                    time.sleep(backoff)
                    continue

                if response.status_code != 200:
                    raise LLMServiceError(
                        f"LLM API failed with status {response.status_code}: {response.text[:200]}",
                        status_code=502 if response.status_code >= 500 else response.status_code
                    )

                data = response.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                return LLMResponse(
                    content=content,
                    prompt_tokens=usage.get("prompt_tokens", TokenBudget.estimate_tokens(prompt)),
                    completion_tokens=usage.get("completion_tokens", TokenBudget.estimate_tokens(content)),
                    model_used=data.get("model", self.model)
                )
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < self.max_retries:
                    backoff = 2 ** attempt
                    logger.warning(f"Network error accessing LLM API: {e}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                    continue
                raise LLMServiceError(f"Network error after {self.max_retries} attempts: {str(e)}", status_code=504)

import re

def _clean_llm_json(text: str) -> str:
    if not isinstance(text, str):
        return text
    cleaned = text.strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and start <= end:
        return cleaned[start:end+1]
    return cleaned

class LLMClient:
    """
    High-level orchestrator for LLM generation with token budgeting and
    one-shot repair retry policy for schema/JSON violations.
    """
    def __init__(self, provider: Optional[BaseLLMProvider] = None, budget: Optional[TokenBudget] = None):
        if provider is not None:
            self.provider = provider
        elif settings.BLACKBOX_API_KEY and settings.APP_ENV != "testing":
            self.provider = BlackboxLLMProvider()
        else:
            self.provider = MockLLMProvider()
        self.budget = budget or TokenBudget()

    def generate_plan_json(self, system_prompt: str, user_prompt: str) -> str:
        # Check token budget
        self.budget.check_and_assert_budget(system_prompt, user_prompt)
        response = self.provider.generate(prompt=user_prompt, system_prompt=system_prompt, json_mode=True)
        return _clean_llm_json(response.content)

    def repair_plan_json(self, system_prompt: str, previous_output: str, validation_errors: str) -> str:
        """
        One constrained repair request using validation errors, without context expansion.
        According to docs/14-llm-orchestration.md Section 5.
        """
        repair_prompt = (
            f"Your previous output was invalid according to the EditPlan JSON schema.\n"
            f"Validation errors:\n{validation_errors}\n\n"
            f"Previous output:\n{previous_output}\n\n"
            f"Please output only the corrected valid JSON conforming strictly to EditPlan schema."
        )
        self.budget.check_and_assert_budget(system_prompt, repair_prompt)
        response = self.provider.generate(prompt=repair_prompt, system_prompt=system_prompt, json_mode=True)
        return _clean_llm_json(response.content)
