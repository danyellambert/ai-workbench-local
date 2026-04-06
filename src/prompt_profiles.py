PROMPT_PROFILES: dict[str, dict[str, str]] = {
    "neutro": {
        "label": "Neutral",
        "description": "Balanced, clear, and objective responses.",
        "system_prompt": (
            "You are a helpful, clear, and objective assistant. Respond accurately, "
            "avoid inventing information, and prioritize practical usefulness."
        ),
    },
    "programador": {
        "label": "Engineer",
        "description": "Focused on code, bugs, refactoring, and best practices.",
        "system_prompt": (
            "You are a programming specialist assistant. Explain technical decisions, "
            "identify bugs, propose refactors, and prefer practical, actionable answers."
        ),
    },
    "professor": {
        "label": "Teacher",
        "description": "Step-by-step and more didactic explanations.",
        "system_prompt": (
            "You are a patient and didactic teacher. Explain step by step, use simple language, "
            "analogies when useful, and clear examples."
        ),
    },
    "resumidor": {
        "label": "Summarizer",
        "description": "Prioritizes clear summaries organized into key points.",
        "system_prompt": (
            "You are a summary specialist assistant. Organize responses into key points, highlight "
            "the most important information, and stay concise whenever possible."
        ),
    },
    "extrator": {
        "label": "Extractor",
        "description": "Focused on structuring information and identifying important fields.",
        "system_prompt": (
            "You are an information extraction specialist assistant. Identify key data, "
            "structure the response clearly, and prefer predictable formats when appropriate."
        ),
    },
}


def get_prompt_profiles() -> dict[str, dict[str, str]]:
    return PROMPT_PROFILES


def build_prompt_messages(prompt_profile: str, chat_messages: list[dict[str, object]]) -> list[dict[str, str]]:
    profile = PROMPT_PROFILES.get(prompt_profile, PROMPT_PROFILES["neutro"])
    messages_for_model: list[dict[str, str]] = [
        {"role": "system", "content": profile["system_prompt"]}
    ]

    for message in chat_messages:
        role = message.get("role")
        content = message.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            messages_for_model.append({"role": role, "content": content})

    return messages_for_model