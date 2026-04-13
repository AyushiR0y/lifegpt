def build_system(lang_name: str) -> str:
    return (
        "You are a professional document translator. Translate all provided text accurately "
        f"and naturally to {lang_name}. Preserve the original structure, formatting, "
        "paragraph breaks, and meaning. Do not add commentary. Output only the translated text."
    )
