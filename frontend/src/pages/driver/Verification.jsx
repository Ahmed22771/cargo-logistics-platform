import React, { useState } from "react";
import { toast } from "sonner";
import { FileCheck, ShieldCheck, Truck } from "lucide-react";
import { Card, Btn, Field, Input, PageHeader } from "../../components/ui-kit";
import { VerificationBadge } from "../../components/StatusBadge";
import { VerificationBanner } from "./VerificationBanner";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api, { apiErr } from "../../lib/api";

const DOC_TYPES = [
  { type: "driving_license", key: "verification.drivingLicense" },
  { type: "vehicle_registration", key: "verification.vehicleReg" },
  { type: "insurance", key: "verification.insurance" },
];

export default function Verification() {
  const { t } = useI18n();
  const { user, refresh } = useAuth();
  const [docs, setDocs] = useState(() => {
    const existing = {};
    (user?.documents || []).forEach((d) => { existing[d.type] = { reference: d.reference || "", expiry: d.expiry || "" }; });
    return DOC_TYPES.reduce((acc, d) => ({ ...acc, [d.type]: existing[d.type] || { reference: "", expiry: "" } }), {});
  });
  const [vehicle, setVehicle] = useState(user?.vehicle || { type: "flatbed", plate: "", capacity: "", model: "" });
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      const payload = DOC_TYPES.map((d) => ({ type: d.type, reference: docs[d.type].reference, expiry: docs[d.type].expiry }));
      await api.post("/driver/documents", { documents: payload, vehicle });
      await refresh();
      toast.success(t("verification.submitted"));
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  return (
    <div className="max-w-2xl">
      <PageHeader title={t("nav.verification")} action={<VerificationBadge status={user?.verification_status} />} />
      <VerificationBanner />

      <Card className="mb-4">
        <h2 className="font-bold text-[#16233A] mb-4 flex items-center gap-2"><Truck className="w-5 h-5 text-[#F1701E]" /> {t("nav.vehicle")}</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("shipment.vehicleType")}><Input data-testid="veh-type" value={vehicle.type} onChange={(e) => setVehicle({ ...vehicle, type: e.target.value })} /></Field>
          <Field label="Plate"><Input data-testid="veh-plate" value={vehicle.plate} onChange={(e) => setVehicle({ ...vehicle, plate: e.target.value })} className="force-ltr" /></Field>
          <Field label={t("shipment.requiredCapacity")}><Input data-testid="veh-capacity" value={vehicle.capacity} onChange={(e) => setVehicle({ ...vehicle, capacity: e.target.value })} className="force-ltr" /></Field>
          <Field label="Model"><Input data-testid="veh-model" value={vehicle.model} onChange={(e) => setVehicle({ ...vehicle, model: e.target.value })} /></Field>
        </div>
      </Card>

      <Card>
        <h2 className="font-bold text-[#16233A] mb-4 flex items-center gap-2"><FileCheck className="w-5 h-5 text-[#F1701E]" /> {t("nav.documents")}</h2>
        <div className="space-y-5">
          {DOC_TYPES.map((d) => (
            <div key={d.type} className="border border-slate-200 rounded-xl p-4">
              <div className="font-semibold text-slate-700 mb-3">{t(d.key)}</div>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("verification.reference")}><Input data-testid={`doc-ref-${d.type}`} value={docs[d.type].reference} onChange={(e) => setDocs({ ...docs, [d.type]: { ...docs[d.type], reference: e.target.value } })} className="force-ltr" /></Field>
                <Field label={t("verification.expiry")}><Input type="date" data-testid={`doc-exp-${d.type}`} value={docs[d.type].expiry} onChange={(e) => setDocs({ ...docs, [d.type]: { ...docs[d.type], expiry: e.target.value } })} className="force-ltr" /></Field>
              </div>
            </div>
          ))}
        </div>
        <Btn variant="accent" onClick={submit} disabled={busy} data-testid="submit-docs-btn" className="w-full mt-5"><ShieldCheck className="w-4 h-4" /> {t("verification.submitDocs")}</Btn>
      </Card>
    </div>
  );
}
