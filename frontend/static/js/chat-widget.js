(() => {
  const launcher = document.getElementById('chatLauncher');
  const panel = document.getElementById('chatWindow');
  if (!launcher || !panel) return;

  const box = document.getElementById('chatMessages');
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const send = document.getElementById('chatSend');
  const storageKey = `lotus-ai-chat-v1-${panel.dataset.userId}`;
  let history = [];

  try {
    const stored = JSON.parse(sessionStorage.getItem(storageKey) || '[]');
    if (Array.isArray(stored)) {
      history = stored.filter(item => ['user', 'assistant'].includes(item.role) && typeof item.content === 'string').slice(-12);
    }
  } catch (_) {
    sessionStorage.removeItem(storageKey);
  }

  function save() {
    sessionStorage.setItem(storageKey, JSON.stringify(history.slice(-12)));
  }

  function setOpen(open) {
    panel.hidden = !open;
    launcher.setAttribute('aria-expanded', String(open));
    launcher.setAttribute('aria-label', open ? 'Đóng chatbot AI' : 'Mở chatbot AI');
    if (open) {
      input.focus();
      box.scrollTop = box.scrollHeight;
    } else {
      launcher.focus();
    }
  }

  function bubble(role, content, typing = false) {
    const row = document.createElement('div');
    row.className = `chat-message ${role}`;
    const avatar = document.createElement('span');
    avatar.className = 'chat-avatar';
    if (role === 'assistant') avatar.innerHTML = '<i class="bi bi-stars"></i>';
    else avatar.textContent = panel.dataset.userInitial;
    const message = document.createElement('div');
    message.className = 'chat-bubble';
    if (typing) {
      message.classList.add('chat-typing');
      message.innerHTML = '<span></span><span></span><span></span>';
    } else message.textContent = content;
    row.append(avatar, message);
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
    return row;
  }

  function render() {
    box.replaceChildren();
    if (!history.length) bubble('assistant', 'Xin chào! Tôi có thể tra cứu phòng, giá, dịch vụ và hướng dẫn quy trình trên hệ thống.');
    history.forEach(item => bubble(item.role, item.content));
  }

  async function sendMessage(text) {
    const content = text.trim();
    if (!content || send.disabled) return;
    history.push({role: 'user', content});
    history = history.slice(-12);
    save();
    render();
    input.value = '';
    send.disabled = true;
    input.disabled = true;
    const typing = bubble('assistant', '', true);
    try {
      const response = await apiRequest('/api/ai/chat', {method: 'POST', body: JSON.stringify({messages: history})});
      typing.remove();
      history.push({role: 'assistant', content: response.content});
      history = history.slice(-12);
      save();
      render();
    } catch (error) {
      typing.remove();
      bubble('assistant', error.message);
      showToast(error.message, false);
    } finally {
      send.disabled = false;
      input.disabled = false;
      if (!panel.hidden) input.focus();
    }
  }

  launcher.addEventListener('click', () => setOpen(panel.hidden));
  document.getElementById('closeChat').addEventListener('click', () => setOpen(false));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !panel.hidden) setOpen(false);
  });
  form.addEventListener('submit', event => { event.preventDefault(); sendMessage(input.value); });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
  });
  panel.querySelectorAll('[data-chat-suggestion]').forEach(button => {
    button.addEventListener('click', () => sendMessage(button.dataset.chatSuggestion));
  });
  document.getElementById('clearChat').addEventListener('click', () => {
    history = [];
    sessionStorage.removeItem(storageKey);
    render();
    input.focus();
    showToast('Đã xóa hội thoại');
  });
  render();
})();
