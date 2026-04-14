"""
summarizer.py
LLM-powered document summarizer using Azure OpenAI (GPT-4o).

Supports three summary styles:
  concise     – 8-15 bullet points
  mid_level   – structured headers + paragraphs
  descriptive – comprehensive multi-section analysis

Special modes (auto-detected from metadata/file_type):
  email (MSG)   – chronological e-mail thread summary
  vision (images) – GPT-4o vision pass for embedded images
"""

from typing import Literal, Any, List, Optional
from dataclasses import dataclass
import os

from openai import AzureOpenAI


MAX_SUMMARY_TOKENS = int(os.getenv("SUMMARIZATION_MAX_TOKENS", "1800"))


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class SummaryConfig:
    summary_type: Literal["concise", "mid_level", "descriptive"]
    document_length: int
    file_type: str
    is_email: bool = False
    email_chain: Any = None
    has_images: bool = False
    image_count: int = 0


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

class DocumentSummarizer:
    """
    Wraps Azure OpenAI chat completions to produce clean plain-text summaries.
    Output never contains ** or __ markdown characters.
    """

    _CLEAN_TOKENS = ("**", "__", "```")

    def __init__(self, client: AzureOpenAI, deployment_name: str) -> None:
        self.client = client
        self.deployment_name = deployment_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_summary(
        self,
        text: str,
        summary_type: Literal["concise", "mid_level", "descriptive"],
        file_type: str = "document",
        metadata: Optional[dict] = None,
        images: Optional[list] = None,
    ) -> str:
        """
        Generate a summary for the supplied *text*.

        Parameters
        ----------
        text         : Extracted document text (possibly PII-masked).
        summary_type : One of ``concise``, ``mid_level``, ``descriptive``.
        file_type    : Source file extension / type (e.g. ``pdf``, ``msg``).
        metadata     : Optional dict from ``DocumentContent.metadata``.
        images       : Optional list of ``ExtractedImage`` objects.
        """
        metadata = metadata or {}
        images = images or []

        doc_words = len(text.split())
        is_email = file_type == "msg" or metadata.get("is_email", False)
        email_chain = metadata.get("email_chain")
        has_images = bool(images)

        cfg = SummaryConfig(
            summary_type=summary_type,
            document_length=doc_words,
            file_type=file_type,
            is_email=is_email,
            email_chain=email_chain,
            has_images=has_images,
            image_count=len(images),
        )

        system_prompt = self._system_prompt(cfg)
        user_prompt = self._user_prompt(cfg, text)

        if has_images and not is_email:
            user_content = self._vision_content(user_prompt, images)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            temperature=0.1 if is_email else 0.3,
            max_tokens=MAX_SUMMARY_TOKENS,
            top_p=0.85,
        )

        result = response.choices[0].message.content.strip()
        for token in self._CLEAN_TOKENS:
            result = result.replace(token, "")
        return result

    # ------------------------------------------------------------------
    # System prompts
    # ------------------------------------------------------------------

    _FORMATTING = """
CRITICAL FORMATTING RULES:
1. DO NOT use ** or __ for bold — write plain text only
2. NO markdown formatting of any kind
3. Use bullet points with the • symbol
4. Use "Label: Description" format for key-value lines
5. Keep output clean and simple
"""

    def _system_prompt(self, cfg: SummaryConfig) -> str:
        if cfg.is_email:
            return (
                "You are a precise Email Thread Summarizer.\n\n"
                "RULES:\n"
                "1. ONLY include information explicitly present in the emails.\n"
                "2. Present emails in CHRONOLOGICAL order (oldest first).\n"
                "3. Capture all URLs/links with their purpose.\n"
                "4. Capture all dates/times mentioned.\n"
                "5. Show conversation flow: who said what, who replied.\n"
                + self._FORMATTING
            )
        if cfg.has_images:
            return (
                "You are an expert Document Analyst with visual comprehension.\n\n"
                "For documents with images:\n"
                "1. DESCRIBE what each image/screenshot shows.\n"
                "2. EXTRACT information visible in screenshots.\n"
                "3. EXPLAIN flowcharts and diagrams step-by-step.\n"
                "4. CONNECT visual content to the surrounding text.\n"
                + self._FORMATTING
            )
        return (
            "You are an expert Document Analyst.\n\n"
            "Create clear, structured summaries that:\n"
            "- Capture all key information accurately.\n"
            "- Use a logical structure with section headers.\n"
            "- Highlight important data, dates, and conclusions.\n"
            + self._FORMATTING
        )

    # ------------------------------------------------------------------
    # User / task prompts
    # ------------------------------------------------------------------

    def _user_prompt(self, cfg: SummaryConfig, text: str) -> str:
        if cfg.is_email and cfg.email_chain:
            task = self._email_task(cfg)
            return task + "\n" + text

        task = self._doc_task(cfg)
        return (
            f"{task}\n\n"
            f"Document ({cfg.file_type.upper()}, {cfg.document_length:,} words):\n"
            f"---\n{text}\n---"
        )

    # --- Email tasks ---

    def _email_task(self, cfg: SummaryConfig) -> str:
        ec = cfg.email_chain
        participants = ", ".join(ec.participants[:8]) if ec else "Unknown"
        subject = ec.subject if ec else "Unknown"
        n = len(ec.messages) if ec else 1

        header = (
            f"TASK: Summarize this email thread (oldest to newest)\n\n"
            f"Subject: {subject}\n"
            f"Emails: {n}\n"
            f"Participants: {participants}\n\n"
        )

        if cfg.summary_type == "concise":
            return header + (
                "OUTPUT FORMAT (• bullets):\n\n"
                "Thread Overview:\n• Overall topic/purpose\n\n"
                "Email Sequence:\n• Email 1 (Sender): What they said\n"
                "• Email 2 (Sender): Their response\n[Continue...]\n\n"
                "Links Shared:\n• URL - Purpose\n\n"
                "Dates/Times Mentioned:\n• Date - Context\n\n"
                "Current Status:\n• Final status\n\n"
                "IMPORTANT: NO ** or markdown. Use Label: Description format.\n\nEMAIL CONTENT:\n"
            )
        if cfg.summary_type == "mid_level":
            return header + (
                "OUTPUT FORMAT:\n\n"
                "Thread Overview\n[2-3 sentences about the thread]\n\n"
                "Email-by-Email Breakdown\n\n"
                "Email 1: Sender Name\nDate: ...\nSummary: ...\nRequest: ...\nLinks: ...\n\n"
                "Email 2: Sender Name\nDate: ...\nSummary: ...\nKey Information: ...\n\n"
                "[Continue for each email...]\n\n"
                "All Links/URLs\n• URL - Purpose\n\n"
                "Key Dates\n• Date - Context\n\n"
                "Current Status\n• Status: ...\n• Pending: ...\n\n"
                "IMPORTANT: NO ** or __ anywhere. Plain text only.\n\nEMAIL CONTENT:\n"
            )
        # descriptive
        return header + (
            "OUTPUT FORMAT:\n\n"
            "Executive Summary\n[3-4 sentences covering the full thread]\n\n"
            "Conversation Timeline\n\n"
            "Email 1 (Thread Started)\nFrom: ...\nTo: ...\nDate: ...\n"
            "Content: ...\nRequest: ...\nLinks: ...\nAttachments: ...\n\n"
            "Email 2 (Response)\nFrom: ...\nTo: ...\nDate: ...\n"
            "Responding To: ...\nContent: ...\nLinks: ...\n\n"
            "[Continue for each email...]\n\n"
            "Complete Link Directory\n• URL - Shared by Person - Purpose\n\n"
            "Complete Timeline\n• Date - Event Type - Context\n\n"
            "Attachments Summary\n• Filename - Shared by Person\n\n"
            "Conclusion\nFinal Status: ...\nDecisions: ...\nOpen Items: ...\n\n"
            "IMPORTANT: NO ** or __ anywhere. Plain text only.\n\nEMAIL CONTENT:\n"
        )

    # --- Document tasks ---

    def _doc_task(self, cfg: SummaryConfig) -> str:
        img_note = (
            f"\n\nDocument has {cfg.image_count} images — describe each one."
            if cfg.has_images
            else ""
        )

        if cfg.summary_type == "concise":
            return (
                "Generate Concise Summary (8-15 bullet points)\n\n"
                "Use • bullets with Label: Description format:\n"
                "• Main Purpose: What this document is about\n"
                "• Key Finding: Most important discovery\n"
                "• Data Point: Specific numbers/facts\n"
                "• Conclusion: Main conclusion\n"
                "• Action Item: Next steps (if any)\n"
                f"{img_note}\n\n"
                "IMPORTANT: NO ** or markdown. Plain text only."
            )
        if cfg.summary_type == "mid_level":
            return (
                "Generate Structured Summary\n\n"
                "Overview\nDocument purpose and key points (2-3 sentences)\n\n"
                "Main Content\nCore information and findings\n\n"
                "Key Details\nImportant specifics, data, dates\n\n"
                "Conclusions\nOutcomes and recommendations\n"
                f"{img_note}\n\n"
                "IMPORTANT: NO ** or __ anywhere. Headers on their own line. "
                "Use Label: Description for bullet points."
            )
        # descriptive
        img_section = ""
        if cfg.has_images:
            img_section = (
                f"\n\nVisual Content Analysis\n"
                f"For each of {cfg.image_count} images:\n"
                "• Image Type: Screenshot/diagram/chart\n"
                "• Content: What it shows\n"
                "• Key Information: Important details"
            )
        return (
            "Generate Comprehensive Summary\n\n"
            "Executive Overview\nOverall purpose and conclusions\n\n"
            "Detailed Analysis\nThorough coverage of all main points\n\n"
            "Key Data and Facts\nSpecific numbers, dates, names\n\n"
            "Findings and Implications\nWhat the document concludes\n"
            f"{img_section}\n\n"
            "Summary\nFinal key takeaways\n\n"
            "IMPORTANT: NO ** or __ or markdown. Plain text only."
        )

    # ------------------------------------------------------------------
    # Vision content builder
    # ------------------------------------------------------------------

    def _vision_content(self, text_prompt: str, images: list) -> list:
        content: list = [{"type": "text", "text": text_prompt}]
        for i, img in enumerate(images):
            content.append({
                "type": "text",
                "text": f"\n--- Image {i + 1} (Page {img.page_number}): {img.description} ---",
            })
            mime = f"image/{img.image_format}".replace("image/jpg", "image/jpeg")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{img.image_base64}", "detail": "high"},
            })
        return content
