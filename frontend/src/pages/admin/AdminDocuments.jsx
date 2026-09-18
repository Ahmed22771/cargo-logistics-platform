import React, { useEffect, useState, useCallback, useMemo } from "react";
import { toast } from "sonner";
import { Search, Check, X, FileText, ExternalLink, Ban } from "lucide-react";
import { Table } from "./AdminLayout";
import { Card, Btn, Spinner, PageHeader, Field, Textarea } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const STATUS_CLS = {
  PENDING: "bg-amber-50 text-amber-700 border border-amber-200",
  APPROVED: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  REJECTED: "bg-red-50 text-red-700 border border-red-200",
};
const FLAG_CLS = {
  OK: "text-slate-400",
  EXPIRING: "text-amber-600",
  EXPIRED: "text-red-600",
};

function Modal({ title, onClose, children, wide }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className={`relative bg-white rounded-2xl w-full ${wide ? "max-w-2xl" : "max-w-md"} p-6`} data-testid="doc-review-modal">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg text-[#16233A]">{title}</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function AdminDocuments() {
  const { t, lang } = useI18n();
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(false);
  const [q, setQ] = useState("");
  const [ownerType, setOwnerType] = useState(""); // driver | vehicle | provider | ""
  const [statusFilter, setStatusFilter] = useState("");
  const [docTypeFilter, setDocTypeFilter] = useState("");
  const [docTypes, setDocTypes] = useState([]);
  const [perms, setPerms] = useState([]);
  const [review, setReview] = useState(null); // {doc, action, reason, notes}
  const [busy, setBusy] = useState(false);

  const canReview = perms.includes("documents.review");

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (ownerType) params.set("owner_type", ownerType);
    if (docTypeFilter) params.set("doc_type", docTypeFilter);
    if (["PENDING", "APPROVED", "REJECTED"].includes(statusFilter)) params.set("status", statusFilter);
    if (statusFilter === "EXPIRING" || statusFilter === "EXPIRED") params.set("expiring", "true");
    setError(false);
    api.get(`/admin/documents?${params.toString()}`).then(({ data }) => {
      let list = data;
      if (statusFilter === "EXPIRED") list = list.filter((d) => d.expiry_flag === "EXPIRED");
      if (statusFilter === "EXPIRING") list = list.filter((d) => d.expiry_flag === "EXPIRING");
      setRows(list);
    }).catch(() => { setRows([]); setError(true); });
  }, [q, ownerType, statusFilter, docTypeFilter]);

  useEffect(() => {
    api.get("/admin/me/permissions").then(({ data }) => setPerms(data.permissions || [])).catch(() => setPerms([]));
    api.get("/document-types").then(({ data }) => setDocTypes(data)).catch(() => setDocTypes([]));
  }, []);

  useEffect(() => {
    const h = setTimeout(load, 250);
    return () => clearTimeout(h);
  }, [load]);

  const fmt = (d) => d ? new Date(d).toLocaleString(lang === "ar" ? "ar-OM" : "en-GB", { dateStyle: "short", timeStyle: "short" }) : "—";
  const typeLabel = (d) => lang === "ar" ? (d.doc_type_name_ar || d.doc_type_key) : (d.doc_type_name_en || d.doc_type_key);
  const ownerTypeLabel = (v) => v === "vehicle" ? t("p4.docs.typeVehicle") : v === "provider" ? t("p4.docs.typeProvider") : t("p4.docs.typeDriver");

  const openReview = (doc, action) => {
    setReview({ doc, action, reason: "", notes: "" });
  };

  const submitReview = async () => {
    if (!review) return;
    if (review.action === "reject" && !(review.reason || "").trim()) {
      toast.error(t("p4.docs.rejectionReasonRequired"));
      return;
    }
    setBusy(true);
    try {
      await api.post(`/admin/documents/${review.doc.id}/review`, {
        action: review.action,
        reason: review.reason || "",
        notes: review.notes || "",
      });
      toast.success(t("common.success"));
      setReview(null);
      load();
    } catch (e) {
      toast.error(apiErr(e));
    } finally { setBusy(false); }
  };

  const filteredDocTypes = useMemo(() => {
    if (!ownerType) return docTypes;
    return docTypes.filter((dt) => dt.owner_type === ownerType);
  }, [docTypes, ownerType]);

  return (
    <div>
      <PageHeader title={t("p4.docs.pageTitle")} />

      {/* Tabs by owner_type */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {[
          { key: "", label: t("p4.docs.allTab") },
          { key: "driver", label: t("p4.docs.driverTab") },
          { key: "vehicle", label: t("p4.docs.vehicleTab") },
          { key: "provider", label: t("p4.docs.providerTab") },
        ].map((tab) => (
          <button key={tab.key} data-testid={`docs-tab-${tab.key || "all"}`} onClick={() => setOwnerType(tab.key)}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${ownerType === tab.key ? "bg-[#16233A] text-white" : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
          <input data-testid="docs-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("p4.docs.search")}
            className="w-full bg-white border border-slate-300 rounded-lg ps-9 pe-3 py-2 text-sm outline-none focus:border-[#F1701E]" />
        </div>
        <select data-testid="docs-status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">{t("p4.docs.allStatus")}</option>
          <option value="PENDING">{t("p4.docs.statusPending")}</option>
          <option value="APPROVED">{t("p4.docs.statusApproved")}</option>
          <option value="REJECTED">{t("p4.docs.statusRejected")}</option>
          <option value="EXPIRING">{t("p4.docs.statusExpiring")}</option>
          <option value="EXPIRED">{t("p4.docs.statusExpired")}</option>
        </select>
        <select data-testid="docs-type-filter" value={docTypeFilter} onChange={(e) => setDocTypeFilter(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">{t("p4.docs.allTypes")}</option>
          {filteredDocTypes.map((dt) => (
            <option key={dt.key} value={dt.key}>{lang === "ar" ? dt.name_ar : dt.name_en}</option>
          ))}
        </select>
      </div>

      {!canReview && (
        <Card className="!p-3 mb-3 bg-amber-50 border-amber-200">
          <div className="flex items-center gap-2 text-sm text-amber-800"><Ban className="w-4 h-4" /> {t("p4.docs.noPermReview")}</div>
        </Card>
      )}

      {rows === null ? <Spinner label={t("common.loading")} /> : error ? (
        <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-red-500">
          {t("p4.docs.loadError")} <button onClick={load} className="text-[#F1701E] font-semibold ms-2">{t("common.retry")}</button>
        </div>
      ) : (
        <Table testId="admin-docs-table" rows={rows}
          empty={t("p4.docs.noDocs")}
          columns={[t("p4.docs.filterOwnerType"), t("p4.docs.filterType"), t("docadmin.owner"), t("p4.docs.reference"), t("p4.docs.expiry"), t("common.status"), t("p4.docs.uploaded"), ""]}
          renderRow={(d) => (
            <tr key={d.id} data-testid={`doc-row-${d.id}`} className="hover:bg-slate-50">
              <td className="px-4 py-3">
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${d.owner_type === "vehicle" ? "bg-blue-50 text-blue-700 border border-blue-200" : d.owner_type === "provider" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-orange-50 text-orange-700 border border-orange-200"}`}>
                  {ownerTypeLabel(d.owner_type)}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-700">{typeLabel(d)}</td>
              <td className="px-4 py-3 font-semibold text-[#16233A]">{d.owner_name || "—"}</td>
              <td className="px-4 py-3 font-mono text-xs force-ltr">{d.reference || "—"}</td>
              <td className={`px-4 py-3 text-xs force-ltr ${FLAG_CLS[d.expiry_flag] || ""}`}>
                {d.expiry || "—"} {d.expiry_flag === "EXPIRED" ? `· ${t("p4.docs.statusExpired")}` : d.expiry_flag === "EXPIRING" ? `· ${t("p4.docs.statusExpiring")}` : ""}
              </td>
              <td className="px-4 py-3">
                <span data-testid={`doc-status-${d.id}`} className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_CLS[d.status] || "bg-slate-100 text-slate-500"}`}>{t(`p4.docs.status${d.status === "PENDING" ? "Pending" : d.status === "APPROVED" ? "Approved" : d.status === "REJECTED" ? "Rejected" : d.status}`)}</span>
              </td>
              <td className="px-4 py-3 text-xs text-slate-400">{fmt(d.uploaded_at)}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <button data-testid={`doc-view-${d.id}`} onClick={() => openReview(d, "view")}
                    title={t("p4.docs.view")} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500"><FileText className="w-4 h-4" /></button>
                  {canReview && d.status === "PENDING" && (
                    <>
                      <button data-testid={`doc-approve-${d.id}`} onClick={() => openReview(d, "approve")}
                        title={t("p4.docs.approve")} className="p-1.5 rounded-lg hover:bg-emerald-50 text-emerald-600"><Check className="w-4 h-4" /></button>
                      <button data-testid={`doc-reject-${d.id}`} onClick={() => openReview(d, "reject")}
                        title={t("p4.docs.reject")} className="p-1.5 rounded-lg hover:bg-red-50 text-red-600"><X className="w-4 h-4" /></button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          )}
        />
      )}

      {review && (
        <Modal wide onClose={() => setReview(null)}
          title={review.action === "approve" ? t("p4.docs.approve") : review.action === "reject" ? t("p4.docs.reject") : t("p4.docs.reviewTitle")}>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-slate-50 rounded-lg p-3"><div className="text-xs text-slate-400">{t("p4.docs.filterOwnerType")}</div><div className="font-semibold text-slate-700">{ownerTypeLabel(review.doc.owner_type)}</div></div>
              <div className="bg-slate-50 rounded-lg p-3"><div className="text-xs text-slate-400">{t("p4.docs.filterType")}</div><div className="font-semibold text-slate-700">{typeLabel(review.doc)}</div></div>
              <div className="bg-slate-50 rounded-lg p-3"><div className="text-xs text-slate-400">{t("docadmin.owner")}</div><div className="font-semibold text-slate-700">{review.doc.owner_name || "—"}</div></div>
              <div className="bg-slate-50 rounded-lg p-3"><div className="text-xs text-slate-400">{t("p4.docs.reference")}</div><div className="font-semibold force-ltr">{review.doc.reference || "—"}</div></div>
              <div className="bg-slate-50 rounded-lg p-3"><div className="text-xs text-slate-400">{t("p4.docs.expiry")}</div><div className="font-semibold force-ltr">{review.doc.expiry || "—"}</div></div>
              <div className="bg-slate-50 rounded-lg p-3"><div className="text-xs text-slate-400">{t("common.status")}</div><div className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_CLS[review.doc.status] || ""}`}>{review.doc.status}</div></div>
            </div>

            {review.doc.file ? (
              <a href={review.doc.file} target="_blank" rel="noreferrer"
                 className="inline-flex items-center gap-2 text-sm text-[#F1701E] font-semibold hover:underline">
                <ExternalLink className="w-4 h-4" /> {t("p4.docs.openFile")}
              </a>
            ) : (
              <p className="text-xs text-slate-400">{t("p4.docs.noFile")}</p>
            )}

            {review.doc.reviewed_at && (
              <div className="text-xs text-slate-500 border-t border-slate-100 pt-3">
                <div>{t("p4.docs.reviewedBy")}: <span className="font-semibold text-slate-700">{review.doc.reviewed_by || "—"}</span></div>
                <div>{t("p4.docs.reviewedAt")}: {fmt(review.doc.reviewed_at)}</div>
                {review.doc.rejection_reason && <div className="text-red-600 mt-1">{t("p4.docs.rejectionReason")}: {review.doc.rejection_reason}</div>}
                {review.doc.notes && <div className="mt-1">{review.doc.notes}</div>}
              </div>
            )}

            {canReview && review.action !== "view" && (
              <>
                {review.action === "reject" && (
                  <Field label={t("p4.docs.rejectionReason")} required>
                    <Textarea rows={2} data-testid="doc-reject-reason" value={review.reason}
                      onChange={(e) => setReview({ ...review, reason: e.target.value })} />
                  </Field>
                )}
                <Field label={t("p4.docs.reviewerNotes")}>
                  <Textarea rows={2} data-testid="doc-review-notes" value={review.notes}
                    onChange={(e) => setReview({ ...review, notes: e.target.value })} />
                </Field>
                <Btn variant={review.action === "approve" ? "accent" : "danger"} onClick={submitReview}
                  disabled={busy} data-testid="doc-review-submit" className="w-full">
                  {review.action === "approve" ? t("p4.docs.approve") : t("p4.docs.reject")}
                </Btn>
              </>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
