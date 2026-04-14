const DEFAULT_LOCAL_BACKEND = "http://127.0.0.1:8000";

function resolveBackendUrl(path) {
  const injectedBase = (window.LIFEGPT_CONTEXT && window.LIFEGPT_CONTEXT.backendBaseUrl) || "";
  if (injectedBase) {
    return `${String(injectedBase).replace(/\/$/, "")}${path}`;
  }
  if (window.location.protocol === "file:") return `${DEFAULT_LOCAL_BACKEND}${path}`;
  try {
    return new URL(path, window.location.origin).toString();
  } catch {
    return `${DEFAULT_LOCAL_BACKEND}${path}`;
  }
}

const API_BASE = resolveBackendUrl("/api/chat");
const TRANSLATION_API_BASE = resolveBackendUrl("/translate-pdf/");

const MODES = {
  generic: { label: "Generic", icon: "fa-comment-dots", fileUpload: false },
  insurance: { label: "Insurance Insights", icon: "fa-file-shield", fileUpload: false },
  summarise: { label: "Summarise", icon: "fa-align-left", fileUpload: true },
  multidoc: { label: "Multi-Doc Q&A", icon: "fa-layer-group", fileUpload: true },
  compare: { label: "Compare Docs", icon: "fa-code-compare", fileUpload: true },
  numbers: { label: "Data Analysis", icon: "fa-calculator", fileUpload: true },
  translate: { label: "Document Translation", icon: "fa-language", fileUpload: false },
};

const KEYWORD_MAP = [
  {
    mode: "insurance",
    keywords: [
      "policy", "premium", "claim", "underwrite", "actuary", "life insurance", "general insurance",
      "health insurance", "annuity", "reinsurance", "deductible", "beneficiary", "insurer", "insured",
      "coverage", "mortality", "morbidity", "irdai", "irda",
    ],
  },
  { mode: "summarise", keywords: ["summarise", "summarize", "summary", "brief", "overview", "tldr", "tl;dr"] },
  { mode: "multidoc", keywords: ["multiple documents", "multi doc", "across documents", "from all documents"] },
  { mode: "compare", keywords: ["compare", "comparison", "versus", "vs ", "difference", "contrast"] },
  { mode: "numbers", keywords: ["numbers", "figures", "statistics", "amounts", "percentage", "inr", "rupee", "calculate"] },
  { mode: "translate", keywords: ["translate", "translation", "hindi", "marathi", "french", "spanish", "german"] },
];

const PII_PATTERNS = [
  { regex: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/gi, replacement: "[EMAIL]" },
  { regex: /\b\d{3}-\d{2}-\d{4}\b/g, replacement: "[SSN]" },
  { regex: /\b\d{4}\s?\d{4}\s?\d{4}\b/g, replacement: "[AADHAAR]" },
  { regex: /\b[A-Z]{5}\d{4}[A-Z]\b/g, replacement: "[PAN]" },
  { regex: /\b(?:\d[ -]*?){13,19}\b/g, replacement: "[CARD_NUMBER]" },
  { regex: /(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){2,4}\d{3,4}/g, replacement: "[PHONE]" },
];

let currentMode = "generic";
let currentChatId = null;
let chats = {};
let uploadedFiles = [];
let translateFile = null;
let summaryPending = null;
let editMessageContext = null;
const streamingChats = new Set();
let currentUserId = "anonymous";
let voiceRecognition = null;
let voiceRecognitionActive = false;
let voiceTranscriptBase = "";
let voiceTranscriptLive = "";

function sanitizeHtml(html) {
  if (window.DOMPurify && typeof window.DOMPurify.sanitize === "function") {
    return window.DOMPurify.sanitize(String(html || ""), {
      USE_PROFILES: { html: true },
      ADD_ATTR: ["target", "rel", "download", "class"],
    });
  }

  const template = document.createElement("template");
  template.innerHTML = String(html || "");

  const blocked = new Set(["script", "style", "iframe", "object", "embed", "link", "meta"]);
  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_ELEMENT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);

  nodes.forEach((el) => {
    const tag = el.tagName.toLowerCase();
    if (blocked.has(tag)) {
      el.remove();
      return;
    }

    Array.from(el.attributes).forEach((attr) => {
      const name = attr.name.toLowerCase();
      const value = attr.value || "";
      if (name.startsWith("on")) {
        el.removeAttribute(attr.name);
        return;
      }
      if ((name === "href" || name === "src") && /^\s*javascript:/i.test(value)) {
        el.removeAttribute(attr.name);
      }
    });
  });

  return template.innerHTML;
}

function renderMarkdownSafe(markdownText) {
  const html = window.marked ? marked.parse(String(markdownText || "")) : escHtml(String(markdownText || ""));
  return sanitizeHtml(html);
}

function getUserIdFromContext() {
  const fromInjected = window.LIFEGPT_CONTEXT && window.LIFEGPT_CONTEXT.userId;
  if (fromInjected && String(fromInjected).trim()) return String(fromInjected).trim();

  const fromUrl = new URLSearchParams(window.location.search).get("userId");
  if (fromUrl && fromUrl.trim()) return fromUrl.trim();

  const fromSession = sessionStorage.getItem("lifegpt_user_id");
  if (fromSession && fromSession.trim()) return fromSession.trim();

  return "anonymous";
}

function getStorageKeys(userId) {
  const safe = String(userId || "anonymous").replace(/[^a-zA-Z0-9_.-]/g, "_");
  return {
    chats: `lifegpt_chats_${safe}`,
    current: `lifegpt_current_${safe}`,
  };
}

function maskPiiText(text) {
  if (!text) return text;
  let masked = String(text);
  for (const { regex, replacement } of PII_PATTERNS) masked = masked.replace(regex, replacement);
  return masked;
}

function detectMode(text) {
  const lower = String(text || "").toLowerCase();
  for (const { mode, keywords } of KEYWORD_MAP) {
    if (keywords.some((k) => lower.includes(k))) return mode;
  }
  return null;
}

function generateId() {
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function isChatStarted(id) {
  return !!(id && chats[id] && chats[id].started);
}

function markChatStarted(id) {
  if (!id || !chats[id]) return;
  chats[id].started = true;
  if (id === currentChatId) collapseFileZone();
}

function collapseFileZone() {
  const zone = document.getElementById("file-zone");
  if (zone) zone.classList.add("collapsed");
}

function expandFileZone() {
  const zone = document.getElementById("file-zone");
  if (zone) zone.classList.remove("collapsed");
}

function updateFileZoneForCurrentChat() {
  const needsFiles = !!(MODES[currentMode] && MODES[currentMode].fileUpload);
  if (needsFiles && !isChatStarted(currentChatId)) expandFileZone();
  else collapseFileZone();
}

function updateInputState() {
  const thisChatStreaming = streamingChats.has(currentChatId);
  const anyOtherStreaming = Array.from(streamingChats).some((id) => id !== currentChatId);

  const sendBtn = document.getElementById("send-btn");
  const notice = document.getElementById("other-chat-notice");
  const indicator = document.getElementById("stream-indicator");
  const inputBox = document.getElementById("main-input-box");

  if (sendBtn) sendBtn.disabled = thisChatStreaming;

  if (notice && inputBox) {
    if (anyOtherStreaming && !thisChatStreaming) {
      notice.classList.add("visible");
      inputBox.classList.add("other-chat-busy");
    } else {
      notice.classList.remove("visible");
      inputBox.classList.remove("other-chat-busy");
    }
  }

  if (indicator) {
    if (thisChatStreaming) indicator.classList.add("visible");
    else indicator.classList.remove("visible");
  }

  renderChatList();
}

function updateVoiceButtonState() {
  const btn = document.getElementById("voice-btn");
  if (!btn) return;

  if (!voiceRecognition) {
    btn.disabled = true;
    btn.title = "Voice input is not supported in this browser";
    btn.classList.remove("recording");
    return;
  }

  btn.disabled = false;
  btn.title = voiceRecognitionActive ? "Stop voice input" : "Voice input";
  btn.classList.toggle("recording", voiceRecognitionActive);
  btn.innerHTML = voiceRecognitionActive
    ? '<i class="fa-solid fa-stop"></i>'
    : '<i class="fa-solid fa-microphone"></i>';
}

function setupVoiceInput() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = document.getElementById("voice-btn");
  if (!Recognition || !btn) {
    voiceRecognition = null;
    updateVoiceButtonState();
    return;
  }

  voiceRecognition = new Recognition();
  voiceRecognition.lang = "en-IN";
  voiceRecognition.interimResults = true;
  voiceRecognition.continuous = false;

  voiceRecognition.onstart = () => {
    voiceRecognitionActive = true;
    voiceTranscriptLive = "";
    const ta = document.getElementById("chat-input");
    voiceTranscriptBase = ta ? String(ta.value || "").trimEnd() : "";
    updateVoiceButtonState();
  };

  voiceRecognition.onresult = (event) => {
    let transcript = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      transcript += event.results[index][0].transcript;
    }
    voiceTranscriptLive = transcript.trim();

    const ta = document.getElementById("chat-input");
    if (ta) {
      const pieces = [voiceTranscriptBase, voiceTranscriptLive].filter(Boolean);
      ta.value = pieces.join(" ").replace(/\s+/g, " ").trimStart();
      autoResize(ta);
    }
  };

  voiceRecognition.onerror = (event) => {
    voiceRecognitionActive = false;
    updateVoiceButtonState();
    const message = event && event.error ? String(event.error) : "Voice input failed";
    if (message !== "no-speech") {
      alert(`Voice input failed: ${message}`);
    }
  };

  voiceRecognition.onend = () => {
    voiceRecognitionActive = false;
    voiceTranscriptLive = "";
    voiceTranscriptBase = "";
    updateVoiceButtonState();
  };

  updateVoiceButtonState();
}

function toggleVoiceInput() {
  if (!voiceRecognition) {
    alert("Voice input is not supported in this browser.");
    return;
  }

  if (voiceRecognitionActive) {
    voiceRecognition.stop();
    return;
  }

  try {
    voiceRecognition.start();
  } catch (error) {
    alert(`Could not start voice input: ${error.message || error}`);
  }
}

function ensureCurrentChat() {
  if (!currentChatId || !chats[currentChatId]) newChat();
}

function newChat() {
  const id = generateId();
  chats[id] = {
    title: "New Chat",
    mode: currentMode,
    messages: [],
    files: [],
    started: false,
    userId: currentUserId,
  };
  currentChatId = id;
  uploadedFiles = [];
  editMessageContext = null;

  renderChatList();
  renderChatMessages();
  renderInputFileChips();
  updateFileZoneForCurrentChat();
  updateEditingState();
  updateInputState();
  saveChatStorage();
}

function loadChat(id) {
  if (!id || !chats[id]) return;
  currentChatId = id;
  const chat = chats[id];
  uploadedFiles = chat.files || [];
  editMessageContext = null;

  setModeInternal(chat.mode || "generic");
  renderChatMessages();
  renderInputFileChips();
  updateFileZoneForCurrentChat();
  updateEditingState();
  updateInputState();
  renderChatList();
}

function deleteChat(id, e) {
  if (e) e.stopPropagation();
  if (!id || !chats[id]) return;

  if (streamingChats.has(id)) {
    if (!confirm("This chat is still processing. Delete anyway?")) return;
    streamingChats.delete(id);
  }

  delete chats[id];
  if (currentChatId === id) {
    const remaining = Object.keys(chats);
    if (remaining.length) loadChat(remaining[remaining.length - 1]);
    else newChat();
  }

  renderChatList();
  saveChatStorage();
}

function renderChatList() {
  const list = document.getElementById("chat-list");
  if (!list) return;

  const ids = Object.keys(chats).reverse();
  list.innerHTML = "";

  if (!ids.length) {
    list.innerHTML = '<div style="padding:8px 12px;font-size:12px;color:var(--text-muted)">No chats yet</div>';
    return;
  }

  ids.forEach((id) => {
    const chat = chats[id];
    const modeInfo = MODES[chat.mode] || MODES.generic;
    const el = document.createElement("div");
    el.className = `chat-item${id === currentChatId ? " active" : ""}`;
    el.onclick = () => loadChat(id);

    const streamBadge = streamingChats.has(id) ? '<span class="streaming-badge">live</span>' : "";
    el.innerHTML = `
      <i class="fa-solid ${modeInfo.icon}"></i>
      <span class="chat-item-title">${escHtml(chat.title)}</span>
      ${streamBadge}
      <div class="chat-item-actions">
        <button onclick="deleteChat('${id}', event)" title="Delete"><i class="fa-solid fa-trash"></i></button>
      </div>
    `;
    list.appendChild(el);
  });
}

function updateChatTitle(id, text) {
  if (!id || !chats[id]) return;
  if (chats[id].title !== "New Chat") return;
  chats[id].title = String(text).slice(0, 38) + (String(text).length > 38 ? "..." : "");
  renderChatList();
  saveChatStorage();
}

function setMode(mode) {
  setModeInternal(mode);
  if (currentChatId && chats[currentChatId]) chats[currentChatId].mode = mode;
  saveChatStorage();
}

function setModeInternal(mode) {
  currentMode = mode;
  const info = MODES[mode] || MODES.generic;

  const modeLabel = document.getElementById("active-mode-label");
  const modeIcon = document.querySelector("#active-mode-badge i");
  if (modeLabel) modeLabel.textContent = info.label;
  if (modeIcon) modeIcon.className = `fa-solid ${info.icon}`;

  document.querySelectorAll(".module-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });

  const tp = document.getElementById("translate-panel");
  const mib = document.getElementById("main-input-box");
  const attachBtn = document.getElementById("attach-btn");

  if (mode === "translate") {
    if (tp) tp.classList.add("active");
    if (mib) mib.style.display = "none";
    if (attachBtn) attachBtn.style.display = "none";
  } else {
    if (tp) tp.classList.remove("active");
    if (mib) mib.style.display = "flex";
    if (attachBtn) attachBtn.style.display = "flex";
  }

  updateFileZoneForCurrentChat();
  updatePlaceholder();
}

function updatePlaceholder() {
  const placeholders = {
    generic: "Ask a professional question...",
    insurance: "Ask about life or general insurance...",
    summarise: "Upload a document and ask for a summary...",
    multidoc: "Upload documents then ask your question...",
    compare: "Upload 2+ documents to compare...",
    numbers: "Ask about specific numbers in your document...",
    translate: "",
  };

  const ta = document.getElementById("chat-input");
  if (ta) ta.placeholder = placeholders[currentMode] || "Ask anything...";
}

async function handleFiles(event) {
  const files = Array.from(event.target.files || []);
  for (const f of files) {
    if (uploadedFiles.length >= 8) {
      alert("Max 8 files allowed.");
      break;
    }
    if (f.size > 10 * 1024 * 1024) {
      alert(`${f.name} exceeds 10MB limit.`);
      continue;
    }
    const content = await readFileContent(f);
    uploadedFiles.push({ name: f.name, content, type: f.type });
  }

  if (currentChatId && chats[currentChatId]) chats[currentChatId].files = uploadedFiles;
  renderInputFileChips();
  event.target.value = "";
}

function readFileContent(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    const nameLower = file.name.toLowerCase();
    const isBinary =
      file.type === "application/pdf" ||
      nameLower.endsWith(".pdf") ||
      String(file.type || "").startsWith("image/") ||
      /\.(xlsx?|xlsm|png|jpe?g|webp|gif|bmp|tif|tiff)$/.test(nameLower);

    if (isBinary) {
      reader.onload = (e) => resolve({ raw: e.target.result, isBase64: true });
      reader.readAsDataURL(file);
    } else {
      reader.onload = (e) => resolve({ raw: e.target.result, isBase64: false });
      reader.readAsText(file);
    }
  });
}

function removeFile(idx) {
  uploadedFiles.splice(idx, 1);
  if (currentChatId && chats[currentChatId]) chats[currentChatId].files = uploadedFiles;
  renderInputFileChips();
}

function renderInputFileChips() {
  const container = document.getElementById("input-file-chips");
  if (!container) return;
  if (!uploadedFiles.length) {
    container.style.display = "none";
    container.innerHTML = "";
    return;
  }

  container.style.display = "flex";
  container.innerHTML = "";

  uploadedFiles.forEach((f, i) => {
    const chip = document.createElement("div");
    chip.className = "input-file-chip";
    chip.innerHTML = `<i class="fa-solid fa-file-lines"></i><span>${escHtml(f.name)}</span><button onclick="removeFile(${i})"><i class="fa-solid fa-xmark"></i></button>`;
    container.appendChild(chip);
  });
}

function handleTranslateFile(event) {
  const f = event.target.files && event.target.files[0];
  if (!f) return;
  translateFile = f;
  const fileNameEl = document.getElementById("translate-file-name");
  const btn = document.getElementById("translate-go-btn");
  if (fileNameEl) fileNameEl.textContent = f.name;
  if (btn) btn.disabled = false;
}

async function runTranslation() {
  if (!translateFile) return;

  ensureCurrentChat();
  const thisChatId = currentChatId;
  const langSelect = document.getElementById("translate-lang");
  const langName = langSelect.options[langSelect.selectedIndex].text;
  const langCode = langSelect.value;
  const btn = document.getElementById("translate-go-btn");

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Translating...';
  }

  markChatStarted(thisChatId);
  streamingChats.add(thisChatId);
  updateInputState();

  const ws = document.getElementById("welcome-screen");
  if (ws) ws.remove();

  addUserMessageWithFiles(`Translate "${translateFile.name}" to ${langName}`, [{ name: translateFile.name }], thisChatId);
  chats[thisChatId].messages.push({
    role: "user",
    content: `Translate "${translateFile.name}" to ${langName}`,
    attachments: [{ name: translateFile.name }],
  });
  updateChatTitle(thisChatId, `Translation: ${translateFile.name}`);

  const aiMsgEl = addAiMessageForChat(thisChatId, "", currentMode);
  const bubbleEl = aiMsgEl ? aiMsgEl.querySelector(".bubble") : null;
  if (bubbleEl) {
    bubbleEl.classList.add("streaming-cursor");
    bubbleEl.innerHTML = `<em>Translating to ${escHtml(langName)}...</em>`;
  }

  saveChatStorage();

  try {
    const formData = new FormData();
    formData.append("file", translateFile);
    formData.append("target_lang", langName);
    formData.append("client_id", thisChatId);

    const resp = await fetch(TRANSLATION_API_BASE, { method: "POST", body: formData });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Translation API error ${resp.status}`);
    }

    const translatedBlob = await resp.blob();
    const url = URL.createObjectURL(translatedBlob);
    const filename = `${translateFile.name.replace(/\.[^.]+$/, "")}_${langCode}.pdf`;

    const resultMsg = {
      role: "assistant",
      mode: currentMode,
      kind: "translation_result",
      content: `Translation complete! Your file has been translated to **${langName}**.`,
      download: {
        filename,
        label: "Download Translated File",
        url,
        mimeType: translatedBlob.type || "application/pdf",
      },
    };

    chats[thisChatId].messages.push(resultMsg);
    saveChatStorage();

    if (bubbleEl) {
      bubbleEl.classList.remove("streaming-cursor");
      bubbleEl.innerHTML = sanitizeHtml(renderMarkdownSafe(resultMsg.content) + downloadHtml(resultMsg.download));
    }
  } catch (e) {
    if (bubbleEl) {
      bubbleEl.classList.remove("streaming-cursor");
      bubbleEl.innerHTML = `<span style="color:#ef4444"><i class="fa-solid fa-triangle-exclamation"></i> Translation failed: ${escHtml(e.message)}</span>`;
    }
  } finally {
    streamingChats.delete(thisChatId);
    updateInputState();

    translateFile = null;
    const fileNameEl = document.getElementById("translate-file-name");
    const input = document.getElementById("translate-file-input");
    if (fileNameEl) fileNameEl.textContent = "Click to upload a document (PDF, DOCX, TXT)";
    if (input) input.value = "";
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-arrow-right-arrow-left"></i> Translate Document';
    }
  }
}

function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
}

async function sendMessage() {
  if (streamingChats.has(currentChatId)) return;

  const ta = document.getElementById("chat-input");
  const text = String(ta.value || "").trim();
  if (!text) return;

  const detected = currentMode === "generic" ? detectMode(text) : null;
  if (detected && detected !== currentMode) setMode(detected);

  ta.value = "";
  autoResize(ta);

  ensureCurrentChat();

  if (currentMode === "summarise") {
    summaryPending = text;
    showSummaryModal();
    return;
  }

  if (editMessageContext && editMessageContext.chatId === currentChatId) {
    await resendEditedMessage(text);
    return;
  }

  await processMessage(text);
}

async function processMessage(text, summaryDepth = null) {
  const chatId = currentChatId;
  const chat = chats[chatId];
  const modeAtSend = currentMode;
  const messageIndex = chat.messages.length;

  const ws = document.getElementById("welcome-screen");
  if (ws) ws.remove();

  markChatStarted(chatId);
  const filesAtSend = [...uploadedFiles];

  addUserMessageWithFiles(text, filesAtSend, chatId, messageIndex);
  chat.messages.push({ role: "user", content: text, attachments: filesAtSend.map((f) => ({ name: f.name })) });
  updateChatTitle(chatId, text);
  saveChatStorage();

  uploadedFiles = [];
  chat.files = [];
  renderInputFileChips();

  const apiMessages = buildApiMessages(chat, text, summaryDepth, filesAtSend);

  streamingChats.add(chatId);
  updateInputState();

  const aiMsgEl = addAiMessageForChat(chatId, "", modeAtSend);
  const bubbleEl = aiMsgEl ? aiMsgEl.querySelector(".bubble") : null;
  const copyBtn = aiMsgEl ? aiMsgEl.querySelector(".copy-btn") : null;
  if (bubbleEl) bubbleEl.classList.add("streaming-cursor");

  try {
    const fullResponse = await callAPIStream(
      apiMessages,
      (chunk) => {
        if (bubbleEl) {
          bubbleEl.classList.remove("streaming-cursor");
          bubbleEl.innerHTML = renderMarkdownSafe(chunk);
        }
        if (currentChatId === chatId) scrollBottom();
      },
      filesAtSend,
      modeAtSend,
      summaryDepth,
      chatId
    );

    if (bubbleEl) {
      bubbleEl.classList.remove("streaming-cursor");
      bubbleEl.innerHTML = renderMarkdownSafe(fullResponse);
    }
    if (copyBtn) {
      copyBtn.dataset.copyText = fullResponse;
      copyBtn.disabled = false;
    }

    chat.messages.push({ role: "assistant", content: fullResponse, mode: modeAtSend });
    saveChatStorage();
    if (window.hljs) hljs.highlightAll();
  } catch (e) {
    if (bubbleEl) {
      bubbleEl.classList.remove("streaming-cursor");
      bubbleEl.innerHTML = `<span style="color:#ef4444"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${escHtml(e.message)}</span>`;
    }
  } finally {
    streamingChats.delete(chatId);
    updateInputState();
    if (currentChatId === chatId) scrollBottom();
  }
}

async function resendEditedMessage(text) {
  const edit = editMessageContext;
  if (!edit || edit.chatId !== currentChatId) {
    editMessageContext = null;
    updateEditingState();
    await processMessage(text);
    return;
  }

  const chat = chats[currentChatId];
  const target = chat && chat.messages[edit.index];
  if (!target || target.role !== "user") {
    editMessageContext = null;
    updateEditingState();
    await processMessage(text);
    return;
  }

  chat.messages = chat.messages.slice(0, edit.index);
  saveChatStorage();
  editMessageContext = null;
  updateEditingState();
  renderChatMessages();
  await processMessage(text);
}

function showSummaryModal() {
  const el = document.getElementById("summary-modal");
  if (el) el.style.display = "flex";
}

function closeSummaryModal() {
  const el = document.getElementById("summary-modal");
  if (el) el.style.display = "none";
  summaryPending = null;
}

function chooseSummaryDepth(depth) {
  const el = document.getElementById("summary-modal");
  if (el) el.style.display = "none";
  const text = summaryPending;
  summaryPending = null;
  if (text) processMessage(text, depth);
}

function buildApiMessages(chat, currentText, summaryDepth, filesAtSend) {
  const messages = [];
  const files = filesAtSend || uploadedFiles;
  const history = (chat.messages || []).slice(-20);

  history.forEach((msg) => {
    if (msg.role === "user") messages.push({ role: "user", content: maskPiiText(msg.content) });
    if (msg.role === "assistant") messages.push({ role: "assistant", content: maskPiiText(msg.content) });
  });

  if (files.length > 0) {
    let fileContext = "";
    files.forEach((f, i) => {
      const docNum = `Document ${i + 1} (${f.name})`;
      if (!f.content.isBase64) {
        const chunks = chunkText(maskPiiText(f.content.raw), 6000);
        fileContext += `\n\n=== ${docNum} ===\n${chunks[0]}`;
        if (chunks.length > 1) fileContext += `\n[... ${chunks.length - 1} additional chunks available ...]`;
      } else {
        fileContext += `\n\n=== ${docNum} ===\n[Uploaded document attached for OCR/text extraction]`;
      }
    });
    messages.push({ role: "user", content: maskPiiText(`${currentText}\n\n--- UPLOADED DOCUMENTS ---${fileContext}`) });
  } else {
    messages.push({ role: "user", content: maskPiiText(currentText) });
  }

  return messages;
}

function chunkText(text, maxChars) {
  const chunks = [];
  for (let i = 0; i < text.length; i += maxChars) chunks.push(text.slice(i, i + maxChars));
  return chunks;
}

async function callAPIStream(messages, onChunk, attachments = [], mode = "generic", summaryDepth = null, chatId = null) {
  let resp;
  try {
    resp = await fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        max_tokens: 2000,
        messages,
        attachments,
        chat_id: chatId,
        mode,
        summary_depth: summaryDepth,
        stream: false,
      }),
    });
  } catch {
    throw new Error(`Unable to reach backend at ${API_BASE}. Start FastAPI server first.`);
  }

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || err.error?.message || `API error ${resp.status}`);
  }

  const data = await resp.json();
  const fullText = (data.content || []).map((b) => b.text || "").join("");
  if (typeof onChunk === "function") onChunk(fullText);
  return fullText;
}

async function callAPI(messages, attachments = [], mode = "generic", summaryDepth = null, chatId = null) {
  return callAPIStream(messages, null, attachments, mode, summaryDepth, chatId);
}

function addUserMessageWithFiles(text, files, chatId, messageIndex) {
  if (chatId && chatId !== currentChatId) return null;

  const inner = document.getElementById("chat-inner");
  if (!inner) return null;

  const el = document.createElement("div");
  el.className = "message user";

  let attachHtml = "";
  if (files && files.length > 0) {
    const chips = files
      .map((f) => `<div class="bubble-attachment"><i class="fa-solid fa-file-lines"></i> ${escHtml(f.name)}</div>`)
      .join("");
    attachHtml = `<div class="bubble-attachments">${chips}</div>`;
  }

  el.innerHTML = `
    <div class="avatar user"><i class="fa-solid fa-user"></i></div>
    <div>
      <div class="bubble">${attachHtml}${escHtml(text)}</div>
      <div class="msg-meta">${formatTime()}</div>
      <div class="msg-actions">
        <button class="msg-action-btn" type="button" onclick="beginEditMessage('${chatId || currentChatId}', ${typeof messageIndex === "number" ? messageIndex : -1})">
          <i class="fa-solid fa-pen-to-square"></i> Edit
        </button>
      </div>
    </div>
  `;

  inner.appendChild(el);
  scrollBottom();
  return el;
}

function addAiMessageForChat(chatId, text, mode) {
  const info = MODES[mode] || MODES.generic;
  const el = document.createElement("div");
  el.className = "message ai";
  el.setAttribute("data-chat-id", chatId);

  el.innerHTML = `
    <div class="avatar ai"><i class="fa-solid ${info.icon}"></i></div>
    <div>
      <div class="bubble">${text ? renderMarkdownSafe(text) : '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>'}</div>
      <div class="msg-meta"><span class="mode-tag">${info.label}</span> ${formatTime()}</div>
      <div class="msg-actions">
        <button class="msg-action-btn copy-btn" type="button" ${text ? "" : "disabled"} data-copy-text="${escHtml(text || "")}" onclick="copyMessageText(this.dataset.copyText, this)">
          <i class="fa-solid fa-copy"></i> Copy text
        </button>
      </div>
    </div>
  `;

  if (chatId === currentChatId) {
    const inner = document.getElementById("chat-inner");
    if (inner) inner.appendChild(el);
    scrollBottom();
  }
  return el;
}

function renderChatMessages() {
  const inner = document.getElementById("chat-inner");
  if (!inner) return;
  inner.innerHTML = "";

  const chat = chats[currentChatId];
  if (!chat || !chat.messages.length) {
    inner.innerHTML = `
      <div id="welcome-screen">
        <div style="max-width:980px;margin:8px auto 0;padding:0 16px;text-align:center">
          <div class="welcome-logo"><i class="fa-solid fa-shield-heart"></i></div>
          <h1 class="welcome-title">Welcome to LifeGPT</h1>
          <p class="welcome-sub">Your trusted AI partner at work.<br/>Choose a module below or start typing.</p>
          <div class="welcome-modules">
            <div class="welcome-module-card" onclick="setMode('generic')"><div class="wmc-icon"><i class="fa-solid fa-comment-dots"></i></div><div class="wmc-title">Generic</div><div class="wmc-desc">Professional questions on any industry topic</div></div>
            <div class="welcome-module-card" onclick="setMode('insurance')"><div class="wmc-icon"><i class="fa-solid fa-file-shield"></i></div><div class="wmc-title">Insurance Insights</div><div class="wmc-desc">Deep dive into life & general insurance</div></div>
            <div class="welcome-module-card" onclick="setMode('summarise')"><div class="wmc-icon"><i class="fa-solid fa-align-left"></i></div><div class="wmc-title">Summarise</div><div class="wmc-desc">Upload documents for concise summaries</div></div>
            <div class="welcome-module-card" onclick="setMode('multidoc')"><div class="wmc-icon"><i class="fa-solid fa-layer-group"></i></div><div class="wmc-title">Multi-Doc Q&A</div><div class="wmc-desc">Ask questions across multiple documents</div></div>
            <div class="welcome-module-card" onclick="setMode('compare')"><div class="wmc-icon"><i class="fa-solid fa-code-compare"></i></div><div class="wmc-title">Compare Docs</div><div class="wmc-desc">Side-by-side comparison of 2+ documents</div></div>
            <div class="welcome-module-card" onclick="setMode('numbers')"><div class="wmc-icon"><i class="fa-solid fa-calculator"></i></div><div class="wmc-title">Data Analysis</div><div class="wmc-desc">Precise extraction of figures & data</div></div>
          </div>
        </div>
      </div>
    `;
    return;
  }

  chat.messages.forEach((msg, index) => {
    if (msg.role === "user") {
      addUserMessageWithFiles(msg.content, msg.attachments || [], currentChatId, index);
      return;
    }

    const ai = addAiMessageForChat(currentChatId, msg.content || "", msg.mode || chat.mode);
    if (msg.download && ai) {
      const bubble = ai.querySelector(".bubble");
      if (bubble) bubble.innerHTML = sanitizeHtml(renderMarkdownSafe(msg.content || "") + downloadHtml(msg.download));
    }
  });

  if (window.hljs) hljs.highlightAll();
  scrollBottom();
}

function downloadHtml(download) {
  if (!download) return "";
  const href = download.dataUrl || download.url || "";
  if (!href) return "";
  const label = download.label || "Download";
  const name = download.filename || "output";
  return `<br/><a class="download-link" href="${href}" download="${escHtml(name)}"><i class="fa-solid fa-download"></i> ${escHtml(label)}</a>`;
}

function beginEditMessage(chatId, messageIndex) {
  if (!chatId || !chats[chatId]) return;
  if (currentChatId !== chatId) loadChat(chatId);

  const chat = chats[chatId];
  const msg = chat.messages[messageIndex];
  if (!msg || msg.role !== "user") return;

  editMessageContext = { chatId, index: messageIndex };
  const ta = document.getElementById("chat-input");
  if (ta) {
    ta.value = msg.content || "";
    autoResize(ta);
    ta.focus();
  }
  updateEditingState();
}

function updateEditingState() {
  const sendBtn = document.getElementById("send-btn");
  const ta = document.getElementById("chat-input");
  if (!sendBtn || !ta) return;

  const isEditing = !!(editMessageContext && editMessageContext.chatId === currentChatId);
  sendBtn.title = isEditing ? "Save edit" : "Send";
  sendBtn.innerHTML = isEditing
    ? '<i class="fa-solid fa-check"></i>'
    : '<i class="fa-solid fa-arrow-up"></i>';

  if (isEditing) ta.placeholder = "Edit your message...";
  else updatePlaceholder();
}

async function copyMessageText(text, button) {
  const payload = text || "";
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(payload);
    } else {
      const tmp = document.createElement("textarea");
      tmp.value = payload;
      document.body.appendChild(tmp);
      tmp.select();
      document.execCommand("copy");
      tmp.remove();
    }

    if (button) {
      const original = button.innerHTML;
      button.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
      setTimeout(() => { button.innerHTML = original; }, 1200);
    }
  } catch {
    alert("Copy failed");
  }
}

function escHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatTime() {
  return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

function scrollBottom() {
  const ca = document.getElementById("chat-area");
  if (ca) ca.scrollTop = ca.scrollHeight;
}

function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.toggle("collapsed");
}

function saveChatStorage() {
  try {
    const keys = getStorageKeys(currentUserId);
    const toSave = {};

    Object.keys(chats).forEach((id) => {
      const chat = chats[id];
      if (!Array.isArray(chat.messages) || !chat.messages.length) return;

      const compactMessages = chat.messages.map((m) => {
        const msg = { ...m };
        if (msg.download && msg.download.url && !msg.download.dataUrl) {
          delete msg.download.url;
        }
        return msg;
      });

      toSave[id] = {
        title: chat.title,
        mode: chat.mode,
        messages: compactMessages,
        files: [],
        started: chat.started,
        userId: currentUserId,
      };
    });

    sessionStorage.setItem(keys.chats, JSON.stringify(toSave));
    if (currentChatId) sessionStorage.setItem(keys.current, currentChatId);
    sessionStorage.setItem("lifegpt_user_id", currentUserId);
  } catch {
    // Ignore storage errors.
  }
}

function loadChatStorage() {
  const keys = getStorageKeys(currentUserId);

  try {
    const saved = sessionStorage.getItem(keys.chats);
    const savedCurrent = sessionStorage.getItem(keys.current);

    if (saved) {
      chats = JSON.parse(saved);
      currentChatId = savedCurrent && chats[savedCurrent] ? savedCurrent : Object.keys(chats).pop() || null;

      renderChatList();
      if (currentChatId && chats[currentChatId]) {
        setModeInternal(chats[currentChatId].mode || "generic");
        renderChatMessages();
        updateFileZoneForCurrentChat();
      } else {
        newChat();
      }
      return;
    }
  } catch {
    // Ignore parse errors and start fresh.
  }

  newChat();
}

function resetUserScopedState(nextUserId) {
  currentUserId = nextUserId || "anonymous";
  chats = {};
  currentChatId = null;
  uploadedFiles = [];
  streamingChats.clear();
  editMessageContext = null;
  summaryPending = null;
  loadChatStorage();
  updateInputState();
  updateEditingState();
}

function setLifeGptUserContext(context) {
  const userId = context && context.userId ? String(context.userId).trim() : "anonymous";
  if (!userId || userId === currentUserId) return;
  resetUserScopedState(userId);
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.marked) marked.setOptions({ breaks: true, gfm: true });

  currentUserId = getUserIdFromContext();
  sessionStorage.setItem("lifegpt_user_id", currentUserId);

  loadChatStorage();
  updatePlaceholder();
  updateInputState();
  updateEditingState();
  setupVoiceInput();
});

window.newChat = newChat;
window.loadChat = loadChat;
window.deleteChat = deleteChat;
window.setMode = setMode;
window.handleFiles = handleFiles;
window.removeFile = removeFile;
window.handleTranslateFile = handleTranslateFile;
window.runTranslation = runTranslation;
window.handleKey = handleKey;
window.autoResize = autoResize;
window.sendMessage = sendMessage;
window.beginEditMessage = beginEditMessage;
window.copyMessageText = copyMessageText;
window.showSummaryModal = showSummaryModal;
window.closeSummaryModal = closeSummaryModal;
window.chooseSummaryDepth = chooseSummaryDepth;
window.toggleSidebar = toggleSidebar;
window.toggleVoiceInput = toggleVoiceInput;
window.callAPIStream = callAPIStream;
window.callAPI = callAPI;
window.setLifeGptUserContext = setLifeGptUserContext;
