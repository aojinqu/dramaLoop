from typing import Protocol, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


class LLMInvocationError(RuntimeError):
    pass


class LLMClient(Protocol):
    def generate_structured(self, *, role: str, prompt: str, response_model: type[TModel]) -> TModel:
        ...

    def generate_text(self, *, role: str, prompt: str) -> str:
        ...
