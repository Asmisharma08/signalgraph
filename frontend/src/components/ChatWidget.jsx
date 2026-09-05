/**
 * SignalGraph — Chat Widget
 * ===========================
 * Floating explain-only assistant. Answers questions about the
 * tracked companies' prices and why a signal fired, grounded in
 * SignalGraph's own live data. Never gives investment advice — see
 * backend/app/chat/assistant.py for where that's enforced.
 */

import { useState, useRef, useEffect } from 'react';
import { apiFetch } from '../lib/api';

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]); // {role, content}
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, open]);

  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((m) => [...m, { role: 'user', content: text }]);
    setInput('');
    setError('');
    setSending(true);

    try {
      const res = await apiFetch('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error?.message || 'Failed to get a response');
      setMessages((m) => [...m, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="chat-widget">
      {open && (
        <div className="chat-panel">
          <div className="chat-panel-header">
            <span>SignalGraph Assistant</span>
            <button className="chat-close" onClick={() => setOpen(false)}>✕</button>
          </div>

          <div className="chat-disclaimer">
            Explains price moves and signals only — never gives investment advice.
          </div>

          <div className="chat-messages" ref={listRef}>
            {messages.length === 0 && (
              <p className="chat-empty">
                Ask me things like "why did TCS move today?" or "what's happening with Reliance?"
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`chat-bubble chat-bubble-${m.role}`}>
                {m.content}
              </div>
            ))}
            {sending && <div className="chat-bubble chat-bubble-assistant chat-typing">…</div>}
          </div>

          {error && <div className="chat-error">⚠ {error}</div>}

          <form className="chat-input-row" onSubmit={send}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a stock..."
              disabled={sending}
              className="chat-input"
            />
            <button type="submit" disabled={sending || !input.trim()} className="chat-send">
              Send
            </button>
          </form>
        </div>
      )}

      <button className="chat-fab" onClick={() => setOpen((o) => !o)}>
        {open ? '✕' : '💬'}
      </button>
    </div>
  );
}
