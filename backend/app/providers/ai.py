"""AI Provider Interface

Defines the contract for LLM backends. Future implementations:
- OpenAIProvider (OpenAI GPT-4, GPT-4o)
- ClaudeProvider (Anthropic Claude)
- GeminiProvider (Google Gemini)
- DeepSeekProvider (DeepSeek)
- OllamaProvider (local models via Ollama)

Not implemented in current phase.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

from .base import BaseProvider


@dataclass
class AIResponse:
    text: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)


class AIProvider(BaseProvider):
    """Interface for LLM backends."""

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """Send a chat completion request.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}
            **kwargs: model-specific parameters (temperature, max_tokens, etc.)

        Returns:
            AIResponse with text, model name, and token usage.
        """
        ...

    @abstractmethod
    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Stream a chat completion, yielding text chunks."""
        ...

    @abstractmethod
    async def lookup_word(
        self, word: str, context_sentence: Optional[str] = None
    ) -> Dict[str, Any]:
        """Look up a word with optional sentence context.

        Returns structured definition:
        {
            "word": str,
            "definitions": [{"text": str, "pos": str, "source": "ai"}],
            "examples": [str],
            "pronunciation": str,
            "level": str,  # CEFR level estimate
        }
        """
        ...

    @abstractmethod
    async def explain_sentence(self, sentence: str) -> Dict[str, Any]:
        """Provide a detailed explanation of a sentence.

        Returns:
        {
            "translation": str,
            "grammar_notes": [str],
            "vocabulary_notes": [{"word": str, "meaning": str}],
        }
        """
        ...

    @abstractmethod
    async def generate_article(
        self,
        *,
        level: str,
        topic: str,
        target_unknown_count: int,
        max_words: int,
    ) -> str:
        """Generate a leveled reading passage using the learner's known vocabulary.

        Args:
            level: Target difficulty (e.g., "A2", "B1", "i+1")
            topic: Article topic
            target_unknown_count: Desired number of new words
            max_words: Maximum word count

        Returns:
            Generated article text.
        """
        ...

    @abstractmethod
    async def answer_question(
        self, question: str, article_context: str
    ) -> Dict[str, Any]:
        """Answer a reader's question about an article.

        Returns:
        {
            "answer": str,
            "citations": [{"sentence": str, "position": int}],
        }
        """
        ...
