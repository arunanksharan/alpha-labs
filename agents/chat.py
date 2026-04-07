"""Research chat handler -- conversational interface backed by real computation.

Wraps the ResearchDirector with conversation history tracking so the user
can have a multi-turn research dialogue.
"""

from __future__ import annotations

import logging

from agents.specialists.research_director import ResearchDirector

logger = logging.getLogger(__name__)


class ResearchChat:
    """Handle research conversations backed by real computation."""

    def __init__(self) -> None:
        self._director = ResearchDirector()
        self._history: list[dict] = []

    def send(self, message: str) -> dict:
        """Process a user message and return a grounded response.

        Parameters
        ----------
        message:
            The user's research question or instruction.

        Returns
        -------
        dict
            Response with answer, citations, suggested actions, and agent traces.
        """
        self._history.append({"role": "user", "content": message})

        response = self._director.answer_question(
            message,
            context={"history": self._history},
        )

        self._history.append({"role": "assistant", "content": response["answer"]})
        return response

    def get_history(self) -> list[dict]:
        """Return the full conversation history."""
        return list(self._history)

    def clear(self) -> None:
        """Clear the conversation history."""
        self._history.clear()
