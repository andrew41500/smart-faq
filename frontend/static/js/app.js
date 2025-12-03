const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const summarizeToggle = document.getElementById("summarize-toggle");

function appendMessage(role, text, meta) {
  const msg = document.createElement("div");
  msg.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  msg.appendChild(bubble);
  if (meta) {
    const metaElem = document.createElement("div");
    metaElem.className = "meta";
    metaElem.textContent = meta;
    msg.appendChild(metaElem);
  }
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage(text) {
  if (!text.trim()) return;

  appendMessage("user", text);
  userInput.value = "";
  userInput.disabled = true;
  chatForm.querySelector('button[type="submit"]').disabled = true;

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        summarize: summarizeToggle.checked,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      const err = data.error || "Something went wrong.";
      appendMessage("assistant", err);
    } else {
      const intent = data.intent || "UNKNOWN";
      const sourceDocs = data.source_docs || [];
      let meta = `Intent: ${intent}`;
      if (sourceDocs.length > 0) {
        const srcs = [
          ...new Set(
            sourceDocs
              .map((d) => d.id)
              .filter(Boolean)
              .map((s) => ("" + s).split(/[\\/]/).pop())
          ),
        ];
        meta += ` • Sources: ${srcs.join(", ")}`;
      }
      appendMessage("assistant", data.answer, meta);
    }
  } catch (e) {
    appendMessage("assistant", "Network error while calling backend.");
  } finally {
    userInput.disabled = false;
    chatForm.querySelector('button[type="submit"]').disabled = false;
    userInput.focus();
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = userInput.value;
  sendMessage(text);
});

document.querySelectorAll(".sample-query").forEach((el) => {
  el.addEventListener("click", () => {
    const text = el.textContent;
    userInput.value = text;
    userInput.focus();
  });
});

// Initial welcome message
appendMessage(
  "assistant",
  "Hi! I’m your Smart Multi-Agent FAQ assistant. Ask me a general question or something that should come from the product manuals."
);


