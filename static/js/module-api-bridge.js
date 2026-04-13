(function () {
  const LOCAL_BACKEND_ORIGIN = "http://127.0.0.1:8000";

  function resolveBackendUrl(path) {
    if (window.location.protocol === "file:") return `${LOCAL_BACKEND_ORIGIN}${path}`;
    try {
      return new URL(path, window.location.origin).toString();
    } catch {
      return `${LOCAL_BACKEND_ORIGIN}${path}`;
    }
  }

  function decodeDataUrl(dataUrl) {
    const parts = String(dataUrl || "").split(",");
    if (parts.length < 2) return new Blob([]);
    const header = parts[0] || "";
    const mimeMatch = header.match(/data:(.*?);base64/i);
    const mimeType = (mimeMatch && mimeMatch[1]) || "application/octet-stream";
    const binary = atob(parts[1]);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i += 1) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: mimeType });
  }

  function attachmentToBlob(attachment) {
    const content = attachment && attachment.content ? attachment.content : {};
    if (content.isBase64) {
      return decodeDataUrl(content.raw);
    }
    return new Blob([String(content.raw || "")], { type: attachment.type || "text/plain" });
  }

  function mapSummaryType(summaryDepth) {
    if (summaryDepth === "concise") return "concise";
    if (summaryDepth === "detailed") return "descriptive";
    return "mid_level";
  }

  function parseFilenameFromDisposition(contentDisposition, fallbackName) {
    const fallback = fallbackName || "summary.docx";
    if (!contentDisposition) return fallback;

    const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match && utf8Match[1]) {
      try {
        return decodeURIComponent(utf8Match[1]);
      } catch {
        return utf8Match[1];
      }
    }

    const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    return (plainMatch && plainMatch[1]) || fallback;
  }

  async function callSummarizationApi(messages, attachments, summaryDepth) {
    if (!attachments || attachments.length === 0) {
      throw new Error("Upload a document to use Summarise mode.");
    }
    const first = attachments[0];
    const formData = new FormData();
    formData.append("file", attachmentToBlob(first), first.name || "upload.txt");
    formData.append("summary_type", mapSummaryType(summaryDepth));

    const resp = await fetch(resolveBackendUrl("/api/summarization/summarize"), {
      method: "POST",
      body: formData,
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Summarization API error ${resp.status}`);
    }

    const data = await resp.json();
    const downloadLink = resolveBackendUrl(data.download_url || "");

    const downloadResp = await fetch(downloadLink);
    if (!downloadResp.ok) {
      const err = await downloadResp.json().catch(() => ({}));
      throw new Error(err.detail || `Summarization download error ${downloadResp.status}`);
    }

    const blob = await downloadResp.blob();
    const objectUrl = URL.createObjectURL(blob);
    const filename = parseFilenameFromDisposition(
      downloadResp.headers.get("content-disposition"),
      `summary_${data.task_id || "download"}.docx`
    );

    return `${data.summary}\n\n<a class="download-link" href="${objectUrl}" download="${filename}"><i class="fa-solid fa-download"></i> Download DOCX</a>`;
  }

  async function callComparisonApi(messages, attachments, summaryDepth) {
    if (!attachments || attachments.length < 2) {
      throw new Error("Upload at least 2 documents to use Compare mode.");
    }

    const userMessage = Array.isArray(messages) && messages.length
      ? String(messages[messages.length - 1].content || "")
      : "Compare the uploaded documents.";

    const formData = new FormData();
    attachments.slice(0, 5).forEach((item) => {
      formData.append("files", attachmentToBlob(item), item.name || "upload.txt");
    });
    formData.append("summary_type", mapSummaryType(summaryDepth));
    formData.append("prompt", userMessage);

    const resp = await fetch(resolveBackendUrl("/api/comparison/compare"), {
      method: "POST",
      body: formData,
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Comparison API error ${resp.status}`);
    }

    const data = await resp.json();
    return data.comparison || "No comparison result returned.";
  }

  async function callModuleChatApi(messages, attachments, mode, summaryDepth, chatId = null) {
    const resp = await fetch(resolveBackendUrl(`/api/modules/${mode}/chat`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        max_tokens: 2000,
        messages,
        attachments,
        chat_id: chatId,
        mode,
        summary_depth: summaryDepth,
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || `Module API error ${resp.status}`);
    }

    const data = await resp.json();
    return data.content?.map((b) => b.text || "").join("") || "";
  }

  const API_CHAT_MODES = new Set(["generic", "insurance", "multidoc", "numbers", "translate"]);

  if (typeof window.callAPIStream !== "function") return;
  const originalCallAPIStream = window.callAPIStream;
  const originalCallAPI = typeof window.callAPI === "function" ? window.callAPI : null;

  window.callAPIStream = async function (messages, onChunk, attachments, mode, summaryDepth, chatId = null) {
    if (mode === "summarise") {
      const text = await callSummarizationApi(messages, attachments, summaryDepth);
      if (typeof onChunk === "function") onChunk(text);
      return text;
    }

    if (mode === "compare") {
      const text = await callComparisonApi(messages, attachments, summaryDepth);
      if (typeof onChunk === "function") onChunk(text);
      return text;
    }

    if (API_CHAT_MODES.has(mode)) {
      const text = await callModuleChatApi(messages, attachments, mode, summaryDepth, chatId);
      if (typeof onChunk === "function") onChunk(text);
      return text;
    }

    return originalCallAPIStream(messages, onChunk, attachments, mode, summaryDepth, chatId);
  };

  if (originalCallAPI) {
    window.callAPI = async function (messages, attachments, mode, summaryDepth, chatId = null) {
      if (API_CHAT_MODES.has(mode)) {
        return callModuleChatApi(messages, attachments, mode, summaryDepth, chatId);
      }
      return originalCallAPI(messages, attachments, mode, summaryDepth, chatId);
    };
  }
})();
