(async function () {
  const me = await AppCommon.initPage();
  if (!me) return;

  const contactEl = document.getElementById('contactSelect');
  const listEl = document.getElementById('messageList');
  const inputEl = document.getElementById('messageInput');

  async function loadContacts() {
    const contacts = await API.getChatContacts();
    contactEl.innerHTML = contacts.map(c => `<option value="${c.id}">${c.full_name || c.username}</option>`).join('');
  }

  async function loadMessages() {
    try {
      AppCommon.setStatus('messageStatus', 'Loading messages...');
      const otherId = contactEl.value;
      if (!otherId) return;
      const messages = await API.getMessages(otherId);
      listEl.innerHTML = messages.map(m => {
        const mine = Number(m.sender_id) === Number(me.id);
        return `<div class="${mine ? 'text-right' : 'text-left'}"><span class="inline-block px-3 py-2 rounded-lg ${mine ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-800'} text-sm mb-2">${m.content}</span></div>`;
      }).join('');
      AppCommon.setStatus('messageStatus', `Loaded ${messages.length} messages`);
    } catch (e) {
      AppCommon.setStatus('messageStatus', `Message error: ${e.message}`, true);
    }
  }

  async function sendMessage() {
    const content = inputEl.value.trim();
    if (!content) return;
    try {
      await API.sendMessage(parseInt(contactEl.value, 10), content);
      inputEl.value = '';
      await loadMessages();
    } catch (e) {
      AppCommon.setStatus('messageStatus', `Send error: ${e.message}`, true);
    }
  }

  await loadContacts();
  await loadMessages();
  contactEl.addEventListener('change', loadMessages);
  document.getElementById('sendBtn').addEventListener('click', sendMessage);
})();
