import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Send, MessageCircle, ArrowLeft } from "lucide-react";
import { Card, Spinner, EmptyState } from "./ui-kit";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../i18n";
import api, { apiErr } from "../lib/api";

// Presentational chat window. It knows NOTHING about business logic — authorization,
// participant resolution, notifications and state transitions are all backend
// concerns exposed through /chat/* endpoints. Poll interval is transport-agnostic
// so the same UI works unchanged if /chat/* is later served over websockets.
export function ChatWindow({ conversation, onBack, embedded = false, height = "h-[70vh]" }) {
  const { t, lang, isRTL } = useI18n();
  const { user } = useAuth();
  const [messages, setMessages] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);
  const lastAtRef = useRef(null);
  const bottomRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }));
  }, []);

  const loadInitial = useCallback(async () => {
    if (!conversation?.id) return;
    try {
      const { data } = await api.get(`/chat/conversations/${conversation.id}/messages`);
      setMessages(data || []);
      if (data && data.length > 0) lastAtRef.current = data[data.length - 1].created_at;
      api.post(`/chat/conversations/${conversation.id}/read`).catch(() => {});
      scrollToBottom();
    } catch (e) { toast.error(apiErr(e)); setMessages([]); }
  }, [conversation?.id, scrollToBottom]);

  const pollDelta = useCallback(async () => {
    if (!conversation?.id || !lastAtRef.current) return;
    try {
      const { data } = await api.get(`/chat/conversations/${conversation.id}/messages`, { params: { after: lastAtRef.current } });
      if (Array.isArray(data) && data.length > 0) {
        setMessages((prev) => [...(prev || []), ...data]);
        lastAtRef.current = data[data.length - 1].created_at;
        api.post(`/chat/conversations/${conversation.id}/read`).catch(() => {});
        scrollToBottom();
      }
    } catch { /* ignored */ }
  }, [conversation?.id, scrollToBottom]);

  useEffect(() => { loadInitial(); }, [loadInitial]);
  useEffect(() => {
    if (!conversation?.id) return;
    const i = setInterval(pollDelta, 5000);
    return () => clearInterval(i);
  }, [conversation?.id, pollDelta]);

  const send = async () => {
    const val = text.trim();
    if (!val || busy) return;
    setBusy(true);
    setText("");
    try {
      const { data: msg } = await api.post(`/chat/conversations/${conversation.id}/messages`, { text: val });
      setMessages((prev) => [...(prev || []), msg]);
      lastAtRef.current = msg.created_at;
      scrollToBottom();
    } catch (e) { toast.error(apiErr(e)); setText(val); } finally { setBusy(false); }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const peers = useMemo(() => (conversation?.participants || []).filter((p) => p.user_id !== user?.id), [conversation, user]);
  const peerLabel = peers.map((p) => p.name).join(" · ") || t("chat.conversation");
  const roleLabel = peers.length === 1 ? t(`auth.${peers[0].role}`) : "";

  const fmtTime = (x) => { try { return new Date(x).toLocaleTimeString(lang === "ar" ? "ar-OM" : "en-GB", { hour: "2-digit", minute: "2-digit" }); } catch { return ""; } };

  return (
    <div className={`flex flex-col ${height} bg-white ${embedded ? "" : "border border-slate-200 rounded-2xl"} overflow-hidden min-w-0`} data-testid="chat-window">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-200 bg-slate-50/60 shrink-0">
        {onBack && (
          <button onClick={onBack} className="p-1.5 -ms-1 rounded-lg hover:bg-slate-200" data-testid="chat-back-btn" aria-label={t("common.back")}>
            <ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} />
          </button>
        )}
        <MessageCircle className="w-5 h-5 text-[#F1701E] shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="font-bold text-[#16233A] truncate" data-testid="chat-peer-name">{peerLabel}</div>
          <div className="text-[11px] text-slate-400 truncate">
            {roleLabel && <span className="me-1">{roleLabel} ·</span>}
            {conversation?.shipment_title || t("chat.tripThread")}
          </div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-2 bg-slate-50/30" data-testid="chat-messages">
        {messages === null ? (
          <Spinner label={t("common.loading")} />
        ) : messages.length === 0 ? (
          <EmptyState title={t("chat.empty")} subtitle={t("chat.emptySub")} />
        ) : (
          messages.map((m) => {
            const mine = m.sender_id === user?.id;
            return (
              <div key={m.id} data-testid={`chat-msg-${m.id}`} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm shadow-sm ${mine ? "bg-[#F1701E] text-white" : "bg-white border border-slate-200 text-slate-800"}`}>
                  {!mine && <div className="text-[10px] font-bold opacity-70 mb-0.5">{m.sender_name}</div>}
                  <div className="whitespace-pre-wrap break-words">{m.text}</div>
                  <div className={`text-[10px] mt-1 ${mine ? "text-white/70" : "text-slate-400"}`}>{fmtTime(m.created_at)}</div>
                </div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="border-t border-slate-200 p-2 flex items-end gap-2 bg-white shrink-0">
        <textarea data-testid="chat-input" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey}
          rows={1} maxLength={4000} placeholder={t("chat.placeholder")}
          className="flex-1 resize-none border border-slate-300 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-[#F1701E]/30 focus:border-[#F1701E] max-h-32" />
        <button type="submit" data-testid="chat-send-btn" disabled={busy || !text.trim()}
          className="h-10 w-10 shrink-0 flex items-center justify-center rounded-xl bg-[#F1701E] text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#d95f0f]"
          aria-label={t("chat.send")}>
          <Send className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
        </button>
      </form>
    </div>
  );
}

// Convenience button used inside Shipment/Trip/Dispute detail pages. Resolves
// (or creates idempotently) the trip-scoped conversation via /chat/conversations/context,
// then navigates the caller to the appropriate messages route. It NEVER creates
// duplicate conversations for the same trip.
export function ChatContextButton({ tripId, shipmentId, basePath, label, disabled, className, testId = "open-chat-btn" }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const go = async () => {
    if (busy || disabled) return;
    setBusy(true);
    try {
      const { data } = await api.post("/chat/conversations/context", { trip_id: tripId, shipment_id: shipmentId });
      window.location.assign(`${basePath}/messages/${data.id}`);
    } catch (e) {
      const c = apiErr(e);
      if (c === "CHAT_NOT_AVAILABLE_BEFORE_TRIP") toast.error(t("chat.notAvailableYet"));
      else toast.error(c);
    } finally { setBusy(false); }
  };
  return (
    <button type="button" onClick={go} disabled={busy || disabled} data-testid={testId}
      className={className || "inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold bg-white border border-slate-200 text-[#16233A] hover:bg-slate-50 disabled:opacity-50"}>
      <MessageCircle className="w-4 h-4" /> {label || t("chat.open")}
    </button>
  );
}
