import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { FileCheck, Upload, Car, User, FilePlus } from "lucide-react";
import { Card, Btn, Spinner, PageHeader, Input } from "../../components/ui-kit";
import { VerificationBanner } from "./VerificationBanner";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api, { apiErr } from "../../lib/api";

const DOC_STATUS_CLS = {
  PENDING: "bg-amber-50 text-amber-700 border-amber-200",
  APPROVED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  REJECTED: "bg-red-50 text-red-700 border-red-200",
  EXPIRED: "bg-red-50 text-red-700 border-red-200",
};

function DocCard({ type, existing, onUploaded }) {
  const { t, lang } = useI18n();
  const [reference, setReference] = useState(existing?.reference || "");
  const [expiry, setExpiry] = useState(existing?.expiry || "");
  const [file, setFile] = useState("");
  const [busy, setBusy] = useState(false);

  const pickFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => setFile(r.result);
    r.readAsDataURL(f);
  };
  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/documents", { doc_type_key: type.key, reference, expiry, file: file || existing?.file || "" });
      toast.success(t("verification.submitted")); onUploaded();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  const name = lang === "ar" ? type.name_ar : type.name_en;
  return (
    <div className="border border-slate-200 rounded-xl p-4" data-testid={`doc-card-${type.key}`}>
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="font-semibold text-slate-700 flex items-center gap-2">
          {name}
          {type.required && <span className="text-[10px] font-bold text-[#F1701E] bg-orange-50 border border-orange-200 rounded px-1.5 py-0.5">{t("p11.doc.required")}</span>}
        </div>
        {existing ? <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold border ${DOC_STATUS_CLS[existing.status]}`}>{t(`p11.doc.${existing.status}`)}</span>
          : <span className="text-xs text-slate-400">{t("p11.doc.notUploaded")}</span>}
      </div>
      {existing?.status === "REJECTED" && existing.rejection_reason && (
        <p className="text-xs text-red-600 bg-red-50 rounded p-2 mb-3">{t("p11.doc.rejectionReason")}: {existing.rejection_reason}</p>
      )}
      <div className="grid grid-cols-2 gap-3">
        <Input data-testid={`doc-ref-${type.key}`} placeholder={t("verification.reference")} value={reference} onChange={(e) => setReference(e.target.value)} className="force-ltr" />
        {type.has_expiry && <Input type="date" data-testid={`doc-exp-${type.key}`} value={expiry} onChange={(e) => setExpiry(e.target.value)} className="force-ltr" />}
      </div>
      <label className="flex items-center gap-2 mt-3 text-sm text-slate-500 cursor-pointer hover:text-[#16233A]">
        <Upload className="w-4 h-4" /> {file ? t("p11.doc.uploaded") : t("p11.doc.chooseFile")}
        <input type="file" accept="image/*,application/pdf" className="hidden" data-testid={`doc-file-${type.key}`} onChange={pickFile} />
      </label>
      <Btn variant="accent" onClick={submit} disabled={busy} data-testid={`doc-submit-${type.key}`} className="w-full mt-3">{t("p11.doc.upload")}</Btn>
    </div>
  );
}

export default function DriverDocuments() {
  const { t } = useI18n();
  const { refresh } = useAuth();
  const [types, setTypes] = useState(null);
  const [mine, setMine] = useState([]);

  const load = () => {
    Promise.all([
      api.get("/document-types").then((r) => r.data).catch(() => []),
      api.get("/documents/mine").then((r) => r.data).catch(() => []),
    ]).then(([ty, docs]) => { setTypes(ty); setMine(docs); });
    refresh();
  };
  useEffect(() => { load(); }, []);
  if (types === null) return <Spinner label={t("common.loading")} />;

  const byOwner = (o) => types.filter((ty) => ty.owner_type === o);
  const findDoc = (key) => mine.find((d) => d.doc_type_key === key);

  const groups = [
    { icon: User, title: t("p11.doc.driverDocs"), items: byOwner("driver") },
    { icon: Car, title: t("p11.doc.vehicleDocs"), items: byOwner("vehicle") },
    { icon: FilePlus, title: t("p11.doc.additionalDocs"), items: [...byOwner("provider"), ...byOwner("other")] },
  ];

  return (
    <div className="max-w-2xl">
      <PageHeader title={t("p11.doc.myDocuments")} />
      <VerificationBanner />
      <div className="space-y-6">
        {groups.filter((g) => g.items.length > 0).map((g, gi) => (
          <div key={gi}>
            <h2 className="font-bold text-[#16233A] mb-3 flex items-center gap-2"><g.icon className="w-5 h-5 text-[#F1701E]" /> {g.title}</h2>
            <div className="space-y-3">
              {g.items.map((ty) => <DocCard key={ty.key} type={ty} existing={findDoc(ty.key)} onUploaded={load} />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
