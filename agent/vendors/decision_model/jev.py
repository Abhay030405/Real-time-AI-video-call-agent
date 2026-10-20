"""Jev (TypeSafe): the decision model that answers typed questions in the background.

Jev returns choices and probabilities, not text. A request carries a short piece of the
conversation (`state`) and named questions; each question is answered against that state.
Three question types exist: `choice` (pick one option, with probabilities), `noul` (the
probability of yes) and `score`. It is called after the reply has started and is never waited
for (hard rule 2).
"""

from __future__ import annotations

import time
from typing import Any

import aiohttp

from settings import Settings

URL = "https://api.typesafe.ai/v1/systemone"


class DecisionModelError(Exception):
    """Jev did not answer in time, or answered with an error."""


class DecisionModel:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_s: float,
        session: aiohttp.ClientSession | None = None,
        url: str = URL,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = aiohttp.ClientTimeout(total=timeout_s)
        self._session = session
        self._owns_session = session is None
        self._url = url

    def _http(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def ask(self, state: str, questions: dict[str, Any]) -> tuple[dict[str, Any], float]:
        """Answers for every question, and how long the call took in milliseconds."""
        started = time.perf_counter()
        try:
            async with self._http().post(
                self._url,
                json={"state": state, "model": self._model, "questions": questions},
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            ) as response:
                body = await response.json()
                if response.status != 200:
                    raise DecisionModelError(f"Jev answered HTTP {response.status}: {body}")
        except (TimeoutError, aiohttp.ClientError) as error:
            raise DecisionModelError(f"Jev did not answer: {type(error).__name__}") from error
        answers: dict[str, Any] = body["answers"]
        return answers, (time.perf_counter() - started) * 1000

    async def warm_up(self) -> None:
        """One tiny question before the call starts: a new connection to Jev can take seconds."""
        try:
            question = {"q": {"type": "noul", "instructions": "Is this a greeting?"}}
            await self.ask("Person: Hi", question)
        except DecisionModelError:
            pass  # a failed warm-up is fine; real decisions simply fall back

    async def aclose(self) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()


def build_decision_model(
    settings: Settings, session: aiohttp.ClientSession | None = None
) -> DecisionModel:
    settings.require("TYPESAFE_API_KEY", "JEV_MODEL", "JEV_TIMEOUT_S")
    return DecisionModel(
        api_key=settings.get("TYPESAFE_API_KEY"),
        model=settings.get("JEV_MODEL"),
        timeout_s=settings.get_float("JEV_TIMEOUT_S"),
        session=session,
    )


def describe_decision_model(settings: Settings) -> dict[str, str]:
    return {
        "provider": "typesafe",
        "model": settings.get("JEV_MODEL"),
        "timeout_s": settings.get("JEV_TIMEOUT_S"),
    }
