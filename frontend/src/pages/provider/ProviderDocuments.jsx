import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { FileText, Upload, X } from "lucide-react";
import { Card, Btn, Field, Input, Spinner, EmptyState, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

function UploadModal({ types, onClose, onSaved }) {
  const { t } = useI18n();
  const [key, setKey] = useState(types[0]?.key || "");
  const [ref, setRef] = useState("");
  const [expiry, setExpiry] = useState("");
  const [file, setFile] = useState("");
  const [busy, setBusy] = useState(false);
  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 4 * 1024 * 1024) return toast.error(t("p5.pod.tooLarge"));
    const r = new FileReader();
    r.onload = () => setFile(r.result);
    r.readAsDataURL(f);
  };
  const submit = async () => {
    if (!key) return toast.error(t("common.required"));
    setBusy(true);
    try {
      await api.post("/documents", { doc_type_key: key, reference: ref, expiry, file });
      toast.success(t("common.success"));
      onSaved && onSaved();
      onClose();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-[#16233A]">{t("provider.uploadDoc")}</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-500" /></button>
        </div>
        <div className="space-y-3">
          <Field label={t("nav.documents")} required>
            <select value={key} onChange={(e) => setKey(e.target.value)} className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#F1701E]">
              {types.map((tt) => <option key={tt.key} value={tt.key}>{tt.name_ar || tt.name_en}</option>)}
            </select>
          </Field>
          <Field label="Reference"><Input value={ref} onChange={(e) => setRef(e.target.value)} /></Field>
          <Field label="Expiry"><Input type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} className="force-ltr" /></Field>
          <Field label={t("provider.uploadDoc")}>
            <input type="file" onChange={onFile} className="block w-full text-sm text-slate-600" />
          </Field>
          <div className="flex gap-2">
            <Btn variant="secondary" onClick={onClose} disabled={busy} className="flex-1 justify-center">{t("common.cancel")}</Btn>
            <Btn variant="accent" onClick={submit} disabled={busy} className="flex-1 justify-center">{t("common.submit")}</Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProviderDocuments() {
  const { t } = useI18n();
  const [docs, setDocs] = useState(null);
  const [types, setTypes] = useState([]);
  const [modal, setModal] = useState(false);
  const load = async () => {
    try {
      const [{ data: mine }, { data: allTypes }] = await Promise.all([api.get("/documents/mine"), api.get("/document-types").catch(() => ({ data: [] }))]);
      setDocs((mine || []).filter((d) => !d.vehicle_id));
      // filter by provider owner_type if present
      setTypes((allTypes || []).filter((t) => !t.owner_type || t.owner_type === "provider"));
    } catch { setDocs([]); }
  };
  useEffect(() => { load(); }, []);
  if (docs === null) return <Spinner label={t("common.loading")} />;
  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader title={t("provider.companyDocs")} action={<Btn variant="accent" onClick={() => setModal(true)} data-testid="upload-doc-btn"><Upload className="w-4 h-4" /> {t("provider.uploadDoc")}</Btn>} />
      {docs.length === 0 ? <Card><EmptyState icon={FileText} title={t("common.none")} /></Card> : (
        <div className="grid gap-3">
          {docs.map((d) => (
            <Card key={d.id} className="min-w-0 overflow-hidden">
              <div className="flex items-center justify-between gap-3 mb-1 min-w-0">
                <div className="font-bold text-[#16233A] truncate">{d.doc_type_name_ar || d.doc_type_key}</div>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${d.status === "APPROVED" ? "bg-emerald-50 text-emerald-700" : d.status === "REJECTED" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>{d.status}</span>
              </div>
              <div className="text-xs text-slate-500">{d.reference || "\u2014"} \u00b7 {d.expiry || "\u2014"}</div>
              {d.rejection_reason && <div className="text-xs text-red-600 mt-1">{d.rejection_reason}</div>}
            </Card>
          ))}
        </div>
      )}
      {modal && <UploadModal types={types.length ? types : [{ key: "cr", name_ar: "السجل التجاري", name_en: "CR" }]} onClose={() => setModal(false)} onSaved={load} />}
    </div>
  );
}
