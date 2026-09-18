import React, { useEffect, useState, useCallback, useRef } from "react";
import { toast } from "sonner";
import { Truck, CheckCircle2, ArrowRight, Camera, X, ShieldCheck } from "lucide-react";
import { Card, Spinner, PageHeader, EmptyState, Btn, Field, Textarea } from "../../components/ui-kit";
import { StatusBadge } from "../../components/StatusBadge";
import { RouteDisplay } from "../../components/RouteDisplay";
import { StaticRouteMap } from "../../components/MapPicker";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const FLOW = ["DRIVER_ASSIGNED", "DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED", "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION", "DELIVERED_PENDING_CONFIRMATION"];

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl w-full max-w-md p-6" data-testid="pod-modal">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg text-[#16233A]">{title}</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

export default function ActiveTrip() {
  const { t, isRTL } = useI18n();
  const [trip, setTrip] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pod, setPod] = useState(null); // { photo, notes }
  const fileRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/trips/mine");
      const active = data.find((tr) => !["COMPLETED", "CANCELLED", "DELIVERED", "DISPUTED"].includes(tr.status))
        || data.find((tr) => ["DELIVERED", "COMPLETED", "DISPUTED"].includes(tr.status));
      setTrip(active || null);
    } catch { /* silent */ } finally { setLoaded(true); }
  }, []);
  useEffect(() => { load(); const i = setInterval(load, 12000); return () => clearInterval(i); }, [load]);

  if (!loaded) return <Spinner label={t("common.loading")} />;
  if (!trip) return <div><PageHeader title={t("trip.active")} /><Card><EmptyState icon={Truck} title={t("trip.noActive")} /></Card></div>;

  const idx = FLOW.indexOf(trip.status);
  const nextStatus = idx >= 0 && idx < FLOW.length - 1 ? FLOW[idx + 1] : null;
  const isPodStep = nextStatus === "DELIVERED_PENDING_CONFIRMATION";

  const advanceSimple = async () => {
    if (!nextStatus) return;
    setBusy(true);
    try {
      const loc = trip.delivery_location;
      await api.post(`/trips/${trip.id}/status`, { status: nextStatus, lat: loc?.lat, lng: loc?.lng });
      toast.success(t("common.success")); await load();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  const openPodModal = () => setPod({ photo: "", notes: "" });

  const onPickPhoto = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    if (f.size > 4 * 1024 * 1024) { toast.error(t("p5.pod.tooLarge")); return; }
    const dataUrl = await fileToDataUrl(f);
    setPod((p) => ({ ...(p || {}), photo: dataUrl }));
  };

  const submitPod = async () => {
    if (!pod?.photo) { toast.error(t("p5.pod.photoRequired")); return; }
    setBusy(true);
    try {
      const loc = trip.delivery_location;
      await api.post(`/trips/${trip.id}/status`, {
        status: "DELIVERED_PENDING_CONFIRMATION",
        lat: loc?.lat, lng: loc?.lng,
        pod_photo: pod.photo, pod_notes: pod.notes || "",
      });
      toast.success(t("p5.pod.submitted"));
      setPod(null); await load();
    } catch (e) {
      const c = apiErr(e);
      toast.error(c === "POD_REQUIRED" ? t("p5.pod.photoRequired") : c);
    } finally { setBusy(false); }
  };

  return (
    <div className="max-w-2xl">
      <PageHeader title={t("trip.active")} action={<StatusBadge status={trip.status} />} />
      <Card className="mb-4">
        <h3 className="font-bold text-[#16233A] mb-1">{trip.shipment_title}</h3>
        <p className="text-sm text-slate-400 mb-3">{t("trip.customer")}: {trip.customer_name}</p>
        <StaticRouteMap pickup={trip.pickup_location} delivery={trip.delivery_location} height={220} />
        <div className="mt-4"><RouteDisplay pickup={trip.pickup_location} delivery={trip.delivery_location} /></div>
        <div className="mt-3 text-sm text-slate-500">{t("common.price")}: <span className="font-bold text-[#F1701E]">{trip.price} {t("common.currency")}</span></div>
      </Card>

      <Card>
        <h3 className="font-bold text-[#16233A] mb-4">{t("trip.progress")}</h3>
        <div className="space-y-1 mb-5">
          {FLOW.map((s, i) => (
            <div key={s} className="flex items-center gap-3" data-testid={`trip-step-${s}`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${i <= idx ? "bg-[#F1701E] text-white" : "bg-slate-100 text-slate-300"}`}>
                {i < idx ? <CheckCircle2 className="w-4 h-4" /> : <div className="w-2 h-2 rounded-full bg-current" />}
              </div>
              <span className={`text-sm ${i === idx ? "font-bold text-[#16233A]" : i < idx ? "text-slate-600" : "text-slate-400"}`}>{t(`status.${s}`)}</span>
            </div>
          ))}
        </div>

        {nextStatus && !isPodStep && (
          <Btn variant="accent" onClick={advanceSimple} disabled={busy} data-testid="update-status-btn" className="w-full">
            {t("trip.updateStatus")}: {t(`status.${nextStatus}`)} <ArrowRight className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
          </Btn>
        )}
        {nextStatus && isPodStep && (
          <Btn variant="accent" onClick={openPodModal} disabled={busy} data-testid="open-pod-btn" className="w-full">
            <ShieldCheck className="w-4 h-4" /> {t("p5.pod.submitBtn")}
          </Btn>
        )}
        {!nextStatus && trip.status === "DELIVERED_PENDING_CONFIRMATION" && (
          <div className="text-center text-sm text-slate-500 bg-slate-50 rounded-lg p-3">{t("status.DELIVERED_PENDING_CONFIRMATION")}</div>
        )}
        {!nextStatus && trip.status === "COMPLETED" && (
          <div className="text-center text-sm text-emerald-600 font-semibold flex items-center justify-center gap-1.5"><CheckCircle2 className="w-4 h-4" /> {t("status.COMPLETED")}</div>
        )}
        {trip.status === "DISPUTED" && (
          <div className="text-center text-sm text-red-600 font-semibold bg-red-50 rounded-lg p-3">{t("status.DISPUTED")}</div>
        )}
      </Card>

      {pod && (
        <Modal title={t("p5.pod.title")} onClose={() => setPod(null)}>
          <div className="space-y-3">
            <p className="text-sm text-slate-500">{t("p5.pod.hint")}</p>
            <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPickPhoto} />
            <button onClick={() => fileRef.current?.click()} data-testid="pod-pick-photo"
              className="w-full border-2 border-dashed border-slate-300 rounded-xl p-6 text-center hover:border-[#F1701E] transition-colors">
              {pod.photo ? (
                <img src={pod.photo} alt="POD" className="max-h-40 mx-auto rounded-lg" />
              ) : (
                <div className="flex flex-col items-center gap-2 text-slate-500">
                  <Camera className="w-8 h-8" />
                  <span className="text-sm font-semibold">{t("p5.pod.pickPhoto")}</span>
                  <span className="text-[11px]">{t("p5.pod.pickHint")}</span>
                </div>
              )}
            </button>
            <Field label={t("p5.pod.notes")}>
              <Textarea rows={2} data-testid="pod-notes" placeholder={t("p5.pod.notesPh")}
                value={pod.notes} onChange={(e) => setPod({ ...pod, notes: e.target.value })} />
            </Field>
            <Btn variant="accent" onClick={submitPod} disabled={busy || !pod.photo} data-testid="pod-submit" className="w-full">
              <ShieldCheck className="w-4 h-4" /> {t("p5.pod.confirm")}
            </Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}
