from backend.modules.generic import PROMPT as GENERIC_PROMPT
from backend.modules.insurance import PROMPT as INSURANCE_PROMPT
from backend.modules.multidoc import PROMPT as MULTIDOC_PROMPT
from backend.modules.numbers import PROMPT as NUMBERS_PROMPT
from backend.modules.translate import build_system as build_translate_prompt

COMPARE_PROMPT = (
    "Compare the uploaded documents using only facts that appear in the documents. "
    "Do not output placeholder text, bracketed templates, or example labels like "
    "[Product Name]. If a detail is not stated, write \"Not stated\". Start with an "
    "executive summary, then provide a structured comparison table, detailed analysis, "
    "key differences, key similarities, and a recommendation grounded in the evidence."
)


def build_summarise_prompt(summary_depth: str | None) -> str:
    detail = (
        "Provide a CONCISE summary: 3-5 bullet points covering only the most critical information."
        if summary_depth == "concise"
        else "Provide a MID-LEVEL summary: main themes, key sections, and important findings. Use clear headings."
        if summary_depth == "mid"
        else "Provide a DETAILED summary: comprehensively cover all sections, subsections, key arguments, data points, and conclusions."
        if summary_depth == "detailed"
        else "Ask the user whether they want a concise, mid-level, or detailed summary before proceeding."
    )
    return (
        "A document has been provided.\n"
        f"{detail}\n"
        "Always begin with a one-sentence overview of what the document is about."
    )

OOS_BLOCK = (
    "If the user asks anything non-professional, inappropriate, personal, or outside "
    "the scope of this assistant, respond with exactly this message:\n\n"
    "This question appears to be outside the scope of LifeGPT. I am designed to assist "
    "with professional topics, including insurance, finance, business, technology, AI, "
    "and GenAI. Please rephrase your question to relate to one of those areas or to "
    "document analysis.\n\n"
    "Do not engage with the out-of-scope topic in any way beyond this message."
)

BASE_PROMPT = (
    "You are LifeGPT, a highly professional AI assistant built for the insurance and "
    "financial services industry. You maintain a formal yet approachable tone. You "
    "always structure your responses clearly with appropriate headings and bullet points "
    f"where relevant. {OOS_BLOCK}"
)


def build_system_prompt(mode: str, summary_depth: str | None = None) -> str:
    mode_normalized = (mode or "generic").strip().lower()
    module_map = {
        "generic": GENERIC_PROMPT,
        "insurance": INSURANCE_PROMPT,
        "multidoc": MULTIDOC_PROMPT,
        "compare": COMPARE_PROMPT,
        "numbers": NUMBERS_PROMPT,
        "translate": build_translate_prompt("the target language"),
    }

    if mode_normalized == "summarise":
        module_prompt = build_summarise_prompt(summary_depth)
    else:
        module_prompt = module_map.get(mode_normalized, GENERIC_PROMPT)

    return f"{BASE_PROMPT}\n\n{module_prompt}".strip()
