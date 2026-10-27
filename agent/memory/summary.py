"""The summary of older turns, written by S1 in the background (V0_01 section 6).

Every ten or so turns, the older part of the conversation is boiled down to a short note:
the facts the person mentioned, how the mood moved, and what is still open. The note goes in
layer 2 of the brain's instructions. It runs in the background and never delays a reply. The
last few turns stay word for word and are not summarised.
"""

from __future__ import annotations

from typing import Any

from livekit.agents import llm

SUMMARY_INSTRUCTIONS = (
    "You write a short private note about a conversation between a person and Vaani, an AI "
    "companion. Keep it under 120 words, in plain sentences, with no lists and no headings.\n"
    "Include: every concrete fact the person mentioned (names of people and pets, places, jobs, "
    "numbers, dates, plans, health or allergy details), how the person's mood moved, and any "
    "thread left open. Keep names, numbers and dates exactly as said.\n"
    "Write only what was said. Do not guess, advise, or add anything new. Leave out anything the "
    "person asked to be forgotten."
)


def transcript_text(turns: list[tuple[str, str]]) -> str:
    return "\n".join(f"{'Person' if role == 'user' else 'Vaani'}: {text}" for role, text in turns)


async def summarise(helper: llm.LLM[Any], turns: list[tuple[str, str]]) -> str:
    """The note for these turns, written by the helper model (S1)."""
    context = llm.ChatContext()
    context.add_message(role="system", content=SUMMARY_INSTRUCTIONS)
    context.add_message(role="user", content=transcript_text(turns))
    text = ""
    async with helper.chat(chat_ctx=context) as stream:
        async for chunk in stream:
            if chunk.delta and chunk.delta.content:
                text += chunk.delta.content
    return text.strip()
