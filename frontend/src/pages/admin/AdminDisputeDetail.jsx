import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Scale, ShieldAlert, ShieldCheck, RotateCcw, Truck, X, AlertTriangle } from "lucide-react";
import { Card, Btn, Spinner, Field, Textarea } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";
import { DisputeStatePill, fmtDate } from "./AdminDisputes";

function Info({ label, children }) {
  return (
    <div className="bg-slate-50 rounded-lg p-2.5 min-w-0">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-semibold text-slate-700 break-words">{children ?? "—"}</div>
    </div>
  );
}

function SectionTitle({ icon: Icon, children }) {
  return <h2 className="font-bold text-[#16233A] mb-4 flex items-center gap-2"><Icon className="w-5 h-5 text-[#F1701E]" /> {children}</h2>;
}

export default function AdminDisputeDetail() {
  const { tripId } = useParams();
  const { t, lang, isRTL } = useI18n();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [perms, setPerms] = useState([]);
  const [providers, setProviders] = useState({});
  const [modal, setModal] = useState(false);
  const [outcome, setOutcome] = useState("RELEASE_TO_DRIVER");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/admin/disputes/${tripId}`);
      setData(data);
    } catch (e) {
      setNotFound(true);
      toast.error(apiErr(e));
    }
  }, [tripId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.get("/admin/me/permissions").then(({ data }) => setPerms(data.permissions || [])).catch(() => setPerms([])); }, []);
  useEffect(() => {
    api.get("/admin/users?role=provider").then(({ data }) => {
      const m = {};
      (data || []).forEach((u) => { m[u.id] = u.company_name || u.name || u.id; });
      setProviders(m);
    }).catch(() => setProviders({}));
  }, []);

  if (notFound) {
    return (
      <Card className="text-center">
        <p className="text-sm text-slate-500 mb-4" data-testid="dispute-not-found">{t("disp.notFound")}</p>
        <Btn variant="secondary" onClick={() => navigate("/admin/disputes")}>{t("disp.back")}</Btn>
      </Card>
    );
  }
  if (!data) return <Spinner label={t("common.loading")} />;

  const { trip, shipment, payment_hold: hold, transactions } = data;
  const dispute = trip.dispute || {};
  const isOpen = trip.status === "DISPUTED";
  const state = isOpen ? "OPEN" : "RESOLVED";
  // Backend remains the enforcement layer (disputes.resolve permission); the
  // button visibility below is only UX, never authorization.
  const canResolve = isOpen && perms.includes("disputes.resolve");
  const amount = Number(trip.price || 0);
  const cur = t("common.currency");
  const providerName = trip.provider_id ? (providers[trip.provider_id] || null) : null;
  const pod = trip.delivery_proof;

  const submitResolve = async () => {
    if (!reason.trim()) { toast.error(t("disp.reasonRequired")); return; }
    setBusy(true);
    try {
      await api.post(`/admin/disputes/${tripId}/resolve`, { outcome, reason });
      toast.success(t("disp.resolvedSuccess"));
      setModal(false);
      setReason("");
      await load();
    } catch (e) {
      const c = apiErr(e);
      if (c === "ALREADY_RESOLVED") {
        toast.error(t("disp.alreadyResolved"));
        setModal(false);
        await load();
      } else {
        toast.error(c);
      }
    } finally { setBusy(false); }
  };

  const txnLabel = (x) => (x.type === "payment_hold" ? t("disp.txn_payment_hold") : t(`p11.fin.txn_${x.type}`));

  return (
    <div className="max-w-4xl mx-auto min-w-0" data-testid="dispute-detail-page">
      <button onClick={() => navigate("/admin/disputes")} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4" data-testid="dispute-back-btn">
        <ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} /> {t("disp.back")}
      </button>

      <div className="flex items-start justify-between gap-3 mb-6 flex-wrap">
        <div className="min-w-0">
          <h1 className="text-2xl font-extrabold tracking-tight text-[#16233A] truncate">{trip.shipment_title || t("disp.title")}</h1>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <DisputeStatePill state={state} />
            <StatusBadge status={trip.status} />
          </div>
        </div>
        {canResolve && (
          <Btn variant="accent" data-testid="resolve-open-btn" onClick={() => setModal(true)}>
            <Scale className="w-4 h-4" /> {t("disp.resolveBtn")}
          </Btn>
        )}
      </div>

      <Card className="mb-4" data-testid="dispute-basic-info">
        <SectionTitle icon={Truck}>{t("disp.basicInfo")}</SectionTitle>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
          <Info label={t("disp.shipmentLabel")}>{shipment?.title || trip.shipment_title}</Info>
          <Info label={t("disp.tripId")}><span className="font-mono text-xs" dir="ltr">{trip.id}</span></Info>
          <Info label={t("disp.customer")}>{trip.customer_name}</Info>
          <Info label={t("disp.driver")}>{trip.driver_name}</Info>
          <Info label={t("disp.provider")}>{providerName || (trip.provider_id ? trip.provider_id : t("disp.noProvider"))}</Info>
          <Info label={t("disp.amount")}><span className="font-mono">{amount.toFixed(3)} {cur}</span></Info>
          <Info label={t("disp.tripStatus")}><StatusBadge status={trip.status} /></Info>
          <Info label={t("disp.shipmentStatus")}>{shipment?.status ? <StatusBadge status={shipment.status} /> : "—"}</Info>
        </div>
      </Card>

      <Card className="mb-4" data-testid="dispute-info-card">
        <SectionTitle icon={ShieldAlert}>{t("disp.disputeInfo")}</SectionTitle>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm mb-3">
          <Info label={t("disp.disputeStatus")}><DisputeStatePill state={state} /></Info>
          <Info label={t("disp.openedAt")}>{fmtDate(dispute.opened_at, lang)}</Info>
          <Info label={t("disp.outcome")}>{dispute.outcome ? t(dispute.outcome === "RELEASE_TO_DRIVER" ? "disp.releaseToDriver" : "disp.fullRefund") : "—"}</Info>
          <Info label={t("disp.resolvedBy")}>{dispute.resolved_by_name || "—"}</Info>
          <Info label={t("disp.resolvedAt")}>{fmtDate(dispute.resolved_at, lang)}</Info>
        </div>
        <div className="border border-red-100 rounded-xl p-3 bg-red-50/50">
          <div className="text-xs text-slate-400 mb-1">{t("disp.reason")}</div>
          <p className="text-sm font-semibold text-red-700">{dispute.reason}</p>
          {dispute.notes && <p className="text-xs text-slate-500 mt-1">{dispute.notes}</p>}
          {dispute.resolution_reason && (
            <p className="text-xs text-slate-600 mt-2 pt-2 border-t border-red-100"><span className="font-semibold">{t("disp.resolutionReason")}:</span> {dispute.resolution_reason}</p>
          )}
        </div>
      </Card>

      <Card className="mb-4" data-testid="dispute-payment-card">
        <SectionTitle icon={Scale}>{t("disp.paymentInfo")}</SectionTitle>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
          <Info label={t("disp.currentPayment")}>{trip.payment_status ? <StatusBadge status={trip.payment_status} /> : "—"}</Info>
          <Info label={t("disp.holdStatus")}>{hold ? <StatusBadge status={hold.status} /> : "—"}</Info>
          <Info label={t("disp.amount")}><span className="font-mono">{Number((hold || {}).amount ?? amount).toFixed(3)} {cur}</span></Info>
        </div>
      </Card>

      {pod?.photo && (
        <Card className="mb-4" data-testid="dispute-pod-card">
          <SectionTitle icon={ShieldCheck}>{t("disp.pod")}</SectionTitle>
          <img src={pod.photo} alt={t("disp.pod")} className="max-h-64 rounded-lg mb-2 mx-auto" />
          {pod.notes && <p className="text-sm text-slate-600">{pod.notes}</p>}
          <p className="text-xs text-slate-400 mt-1">{pod.delivered_by_name || "—"} · {fmtDate(pod.at, lang)}</p>
        </Card>
      )}

      {Array.isArray(transactions) && transactions.length > 0 && (
        <Card className="mb-4" data-testid="dispute-txn-timeline">
          <SectionTitle icon={Scale}>{t("disp.financialEvents")}</SectionTitle>
          <div className="space-y-2">
            {transactions.map((x) => (
              <div key={x.id} className="flex items-center justify-between gap-3 border border-slate-100 rounded-lg px-3 py-2.5 text-sm flex-wrap">
                <div className="min-w-0">
                  <div className="font-semibold text-[#16233A]">{txnLabel(x)}</div>
                  <div className="text-[11px] text-slate-400">{fmtDate(x.created_at, lang)}</div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="font-mono text-xs font-bold">{Number(x.amount || 0).toFixed(3)} {x.currency || cur}</span>
                  {x.status && <StatusBadge status={x.status} />}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {Array.isArray(trip.tracking_events) && trip.tracking_events.length > 0 && (
        <Card data-testid="dispute-trip-events">
          <SectionTitle icon={Truck}>{t("disp.tripEvents")}</SectionTitle>
          <div className="space-y-2">
            {trip.tracking_events.map((ev) => (
              <div key={ev.id} className="flex items-center justify-between gap-3 text-sm">
                <StatusBadge status={ev.status} />
                <span className="text-[11px] text-slate-400">{fmtDate(ev.timestamp, lang)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => !busy && setModal(false)} />
          <div className="relative bg-white rounded-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto" data-testid="resolve-modal">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-lg text-[#16233A]">{t("disp.resolveTitle")}</h2>
              <button onClick={() => !busy && setModal(false)} aria-label={t("common.close")}><X className="w-5 h-5 text-slate-400" /></button>
            </div>
            <div className="space-y-4">
              <Field label={t("disp.decision")} required>
                <div className="space-y-2">
                  {[
                    { key: "RELEASE_TO_DRIVER", icon: Truck, title: t("disp.releaseToDriver"), desc: t("disp.releaseToDriverDesc"), activeCls: "border-[#F1701E] bg-[#F1701E]/5" },
                    { key: "FULL_REFUND", icon: RotateCcw, title: t("disp.fullRefund"), desc: t("disp.fullRefundDesc"), activeCls: "border-red-500 bg-red-50" },
                  ].map((o) => (
                    <button type="button" key={o.key} data-testid={`resolve-opt-${o.key}`} onClick={() => setOutcome(o.key)} disabled={busy}
                      className={`w-full text-start border-2 rounded-xl p-3 transition-colors ${outcome === o.key ? o.activeCls : "border-slate-200 hover:border-slate-300"}`}>
                      <div className="flex items-center gap-2 font-semibold text-[#16233A] text-sm"><o.icon className="w-4 h-4 shrink-0" /> {o.title}</div>
                      <p className="text-xs text-slate-500 mt-1">{o.desc}</p>
                    </button>
                  ))}
                </div>
              </Field>

              <Field label={t("disp.resolutionReason")} required>
                <Textarea rows={3} data-testid="resolve-reason" placeholder={t("disp.resolutionReasonPh")}
                  value={reason} onChange={(e) => setReason(e.target.value)} />
              </Field>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">{t("disp.summaryAmount")}</span>
                  <span className="font-mono font-bold" data-testid="resolve-amount">{amount.toFixed(3)} {cur}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">{t("disp.summaryDecision")}</span>
                  <span className="font-semibold text-[#16233A]" data-testid="resolve-summary-decision">{t(outcome === "RELEASE_TO_DRIVER" ? "disp.releaseToDriver" : "disp.fullRefund")}</span>
                </div>
                <p className="text-[11px] text-amber-700 flex items-center gap-1 pt-1"><AlertTriangle className="w-3.5 h-3.5 shrink-0" /> {t("disp.confirmHint")}</p>
              </div>

              <div className="flex gap-2">
                <Btn variant="secondary" onClick={() => setModal(false)} disabled={busy} data-testid="resolve-cancel" className="flex-1">{t("common.cancel")}</Btn>
                <Btn variant={outcome === "FULL_REFUND" ? "danger" : "accent"} onClick={submitResolve} disabled={busy || !reason.trim()} data-testid="resolve-confirm" className="flex-1">
                  <Scale className="w-4 h-4" /> {t("disp.confirmResolution")}
                </Btn>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
