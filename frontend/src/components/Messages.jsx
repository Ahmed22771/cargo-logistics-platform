import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { MessageCircle, Truck } from "lucide-react";
import { PageHeader, Card, Spinner, EmptyState } from "./ui-kit";
import { ChatWindow } from "./ChatWindow";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../i18n";
import api, { apiErr } from "../lib/api";

// Reusable Messages screens for every portal. The routing shell (list vs.
// detail) is decided by the presence of :cid in the URL, so a single component
// wires up cleanly into any *Portal.
export function MessagesList({ basePath }) {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [convs, setConvs] = useState(null);

  const load = useCallback(() => {
    setConvs(null);
    api.get("/chat/conversations").then(({ data }) => setConvs(data || [])).catch((e) => { toast.error(apiErr(e)); setConvs([]); });
  }, []);
  useEffect(() => { load(); const i = setInterval(load, 15000); return () => clearInterval(i); }, [load]);

  if (convs === null) return <Spinner label={t("common.loading")} />;

  const fmtWhen = (x) => { if (!x) return ""; try { return new Date(x).toLocaleString(lang === "ar" ? "ar-OM" : "en-GB", { dateStyle: "short", timeStyle: "short" }); } catch { return ""; } };

  return (
    <div data-testid="messages-list-page" className="min-w-0">
      <PageHeader title={t("chat.title")} subtitle={t("chat.subtitle")} />
      {convs.length === 0 ? (
        <Card><EmptyState title={t("chat.noThreads")} subtitle={t("chat.noThreadsSub")} /></Card>
      ) : (
        <div className="space-y-2" data-testid="messages-list">
          {convs.map((c) => {
            const unread = c.unread || 0;
            const isMine = c.last_message_sender_id === user?.id;
            return (
              <button key={c.id} data-testid={`conv-row-${c.id}`} onClick={() => navigate(`${basePath}/messages/${c.id}`)}
                className="w-full text-start bg-white border border-slate-200 rounded-xl p-3.5 hover:bg-slate-50 flex items-start gap-3">
                <div className="relative shrink-0">
                  <div className="w-11 h-11 rounded-full bg-[#F1701E]/10 flex items-center justify-center text-[#F1701E]"><MessageCircle className="w-5 h-5" /></div>
                  {unread > 0 && <span data-testid={`conv-unread-${c.id}`} className="absolute -top-1 -end-1 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">{unread}</span>}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="font-bold text-[#16233A] truncate">{c.peer_name || t("chat.conversation")}</span>
                    <span className="text-[11px] text-slate-400 shrink-0">{fmtWhen(c.last_message_at)}</span>
                  </div>
                  <div className="text-[11px] text-slate-500 truncate flex items-center gap-1"><Truck className="w-3 h-3" /> {c.shipment_title || t("chat.tripThread")}</div>
                  <div className={`text-sm truncate mt-0.5 ${unread > 0 ? "font-semibold text-[#16233A]" : "text-slate-500"}`}>
                    {isMine && c.last_message_preview && <span className="text-slate-400">{t("chat.you")}: </span>}
                    {c.last_message_preview || t("chat.noMessagesYet")}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function MessagesThread({ basePath }) {
  const { cid } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [conv, setConv] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get(`/chat/conversations/${cid}`).then(({ data }) => setConv(data)).catch((e) => setErr(apiErr(e)));
  }, [cid]);
  if (err) return <Card><EmptyState title={t("chat.accessDenied")} subtitle={err} /></Card>;
  if (!conv) return <Spinner label={t("common.loading")} />;
  return <ChatWindow conversation={conv} onBack={() => navigate(`${basePath}/messages`)} />;
}

export default function Messages({ basePath }) {
  const { cid } = useParams();
  return cid ? <MessagesThread basePath={basePath} /> : <MessagesList basePath={basePath} />;
}
