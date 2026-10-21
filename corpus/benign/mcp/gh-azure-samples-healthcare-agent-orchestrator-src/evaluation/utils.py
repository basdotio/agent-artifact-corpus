# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.utils.author_role import AuthorRole


def chat_history_to_readable_text(history: ChatHistory) -> str:
    """
    Convert a ChatHistory object to a human-readable text format.

    Args:
        history: ChatHistory object containing the conversation

    Returns:
        A formatted string representation of the conversation
    """
    messages = ""
    for message in history.messages:
        if not message.content:
            continue
        role = message.role.value.upper()
        if role == AuthorRole.ASSISTANT.value.upper():
            role += f" (agent id: {message.name})"
        messages += f"{role}:\n{message.content}\n\n---\n\n"

    return messages
