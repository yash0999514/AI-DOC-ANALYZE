// Document-Aware AI Assistant Chat Controller
document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const chatMessages = document.getElementById('chat-messages');
  const clearChatBtn = document.getElementById('clear-chat-btn');
  const promptPills = document.querySelectorAll('.prompt-pill');

  if (!chatForm || !chatInput || !chatMessages) return;

  const docId = chatForm.getAttribute('data-doc-id');
  const conversationHistory = [];

  function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function appendMessage(sender, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${sender}`;

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.innerText = text;

    const meta = document.createElement('div');
    meta.className = 'chat-meta';
    meta.innerText = formatTime(new Date());

    msgDiv.appendChild(bubble);
    msgDiv.appendChild(meta);
    chatMessages.appendChild(msgDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  }

  function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'chat-typing-indicator';
    indicator.className = 'chat-message assistant';
    indicator.innerHTML = `
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    `;
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return indicator;
  }

  function removeTypingIndicator() {
    const ind = document.getElementById('chat-typing-indicator');
    if (ind) ind.remove();
  }

  async function submitQuestion(questionText) {
    const q = (questionText || '').trim();
    if (!q) return;

    appendMessage('user', q);
    chatInput.value = '';
    chatInput.disabled = true;

    const typingEl = showTypingIndicator();

    try {
      const response = await fetch(`/api/documents/${docId}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          question: q,
          history: conversationHistory
        })
      });

      removeTypingIndicator();
      chatInput.disabled = false;
      chatInput.focus();

      const data = await response.json();

      if (response.ok && data.success) {
        const answer = data.data.answer;
        appendMessage('assistant', answer);
        conversationHistory.push({ question: q, answer: answer });
      } else {
        const errText = data.error ? data.error.message : 'Unable to generate answer at this time.';
        appendMessage('assistant', `⚠️ ${errText}`);
      }
    } catch (err) {
      removeTypingIndicator();
      chatInput.disabled = false;
      console.error('Chat error:', err);
      appendMessage('assistant', '⚠️ Connection error. Please verify your connection and try again.');
    }
  }

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    submitQuestion(chatInput.value);
  });

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitQuestion(chatInput.value);
    }
  });

  promptPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const prompt = pill.getAttribute('data-prompt') || pill.innerText;
      submitQuestion(prompt);
    });
  });

  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      conversationHistory.length = 0;
      chatMessages.innerHTML = `
        <div class="chat-message assistant">
          <div class="chat-bubble">
            Hello! I am your AI DOC Assistant. Ask me anything about this document — like summary, key dates, obligations, or definitions.
          </div>
          <div class="chat-meta">System</div>
        </div>
      `;
      AIDoc.showToast("Conversation cleared.", "info");
    });
  }
});
