import React, { useEffect, useState, useCallback, useRef } from "react";
import { toast } from "sonner";
import { Search, Pencil, KeyRound, Ban, CheckCircle2, X } from "lucide-react";
import { Table } from "./AdminLayout";
import { Btn, Spinner, PageHeader, Input, Field, Textarea } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const ROLE_CLS = {
  admin: "bg-[#16233A] text-white",
  customer: "bg-blue-50 text-blue-700 border border-blue-200",
  driver: "bg-orange-50 text-orange-700 border border-orange-200",
  provider: "bg-emerald-50 text-emerald-700 border border-emerald-200",
};

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl w-full max-w-md p-6" data-testid="user-modal">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg text-[#16233A]">{title}</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function AdminUsers() {
  const { t, lang } = useI18n();
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(false);
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [roles, setRoles] = useState([]);
  const [edit, setEdit] = useState(null);
  const [pw, setPw] = useState(null);
  const [busy, setBusy] = useState(false);
  const debounce = useRef(null);

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (roleFilter) params.set("role", roleFilter);
    if (statusFilter) params.set("status", statusFilter);
    setError(false);
    api.get(`/admin/users?${params.toString()}`).then(({ data }) => setRows(data)).catch(() => { setRows([]); setError(true); });
  }, [q, roleFilter, statusFilter]);

  useEffect(() => { api.get("/admin/roles").then(({ data }) => setRoles(data)).catch(() => setRoles([])); }, []);
  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(load, 350);
    return () => clearTimeout(debounce.current);
  }, [load]);

  const roleName = (key) => { const r = roles.find((x) => x.key === key); return r ? (lang === "ar" ? r.name_ar : r.name_en) : (key || "Admin"); };
  const roleLabel = { admin: "Admin", customer: t("auth.customer"), driver: t("auth.driver"), provider: t("auth.provider") };
  const fmt = (d) => d ? new Date(d).toLocaleString(lang === "ar" ? "ar-OM" : "en-GB", { dateStyle: "short", timeStyle: "short" }) : t("p11.rbac.never");

  const saveEdit = async () => {
    setBusy(true);
    try {
      const body = { name: edit.name, email: edit.email, phone: edit.phone, notes: edit.notes };
      if (edit.role === "admin") body.admin_role_key = edit.admin_role_key;
      await api.put(`/admin/users/${edit.id}`, body);
      toast.success(t("common.success")); setEdit(null); load();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  const toggleStatus = async (u) => {
    const next = u.status === "disabled" ? "active" : "disabled";
    try { await api.post(`/admin/users/${u.id}/status`, { status: next }); toast.success(t("common.success")); load(); }
    catch (e) { toast.error(apiErr(e)); }
  };
  const savePw = async () => {
    if (!pw.password || pw.password.length < 6) { toast.error(t("p11.rbac.pwHint")); return; }
    setBusy(true);
    try { await api.post(`/admin/users/${pw.id}/reset-password`, { password: pw.password }); toast.success(t("common.success")); setPw(null); }
    catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title={t("nav.users")} />
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
          <input data-testid="users-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("p11.rbac.search")}
            className="w-full bg-white border border-slate-300 rounded-lg ps-9 pe-3 py-2 text-sm outline-none focus:border-[#F1701E]" />
        </div>
        <select data-testid="users-role-filter" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">{t("p11.rbac.allRoles")}</option>
          <option value="admin">Admin</option>
          <option value="customer">{t("auth.customer")}</option>
          <option value="driver">{t("auth.driver")}</option>
          <option value="provider">{t("auth.provider")}</option>
        </select>
        <select data-testid="users-status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">{t("p11.rbac.allStatus")}</option>
          <option value="active">{t("p11.rbac.active")}</option>
          <option value="disabled">{t("p11.rbac.disabled")}</option>
        </select>
      </div>

      {rows === null ? <Spinner label={t("common.loading")} /> : error ? (
        <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-red-500">
          {t("p11.fin.loadError")} <button onClick={load} className="text-[#F1701E] font-semibold ms-2">{t("p11.fin.retry")}</button>
        </div>
      ) : (
        <Table testId="admin-users-table" rows={rows}
          columns={[t("auth.name"), t("p11.rbac.role"), t("common.status"), t("auth.phone"), t("auth.email"), t("p11.rbac.lastLogin"), t("p11.rbac.actions")]}
          renderRow={(u) => (
            <tr key={u.id} data-testid={`admin-user-${u.id}`} className="hover:bg-slate-50">
              <td className="px-4 py-3 font-semibold text-[#16233A]">{u.name}{u.notes ? <span className="block text-[11px] font-normal text-slate-400">{u.notes}</span> : null}</td>
              <td className="px-4 py-3"><span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold ${ROLE_CLS[u.role]}`}>{u.role === "admin" ? roleName(u.admin_role_key) : roleLabel[u.role]}</span></td>
              <td className="px-4 py-3"><span data-testid={`user-status-${u.id}`} className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${u.status === "disabled" ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-700"}`}>{u.status === "disabled" ? t("p11.rbac.disabled") : t("p11.rbac.active")}</span></td>
              <td className="px-4 py-3 font-mono text-xs force-ltr">{u.phone || "\u2014"}</td>
              <td className="px-4 py-3 text-slate-500 force-ltr">{u.email || "\u2014"}</td>
              <td className="px-4 py-3 text-xs text-slate-400">{fmt(u.last_login)}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <button data-testid={`user-edit-${u.id}`} onClick={() => setEdit({ ...u })} title={t("p11.rbac.edit")} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500"><Pencil className="w-4 h-4" /></button>
                  <button data-testid={`user-toggle-${u.id}`} onClick={() => toggleStatus(u)} title={u.status === "disabled" ? t("p11.rbac.enable") : t("p11.rbac.disable")} className={`p-1.5 rounded-lg hover:bg-slate-100 ${u.status === "disabled" ? "text-emerald-600" : "text-red-500"}`}>{u.status === "disabled" ? <CheckCircle2 className="w-4 h-4" /> : <Ban className="w-4 h-4" />}</button>
                  {u.role === "admin" && <button data-testid={`user-reset-${u.id}`} onClick={() => setPw({ id: u.id, password: "" })} title={t("p11.rbac.resetPassword")} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500"><KeyRound className="w-4 h-4" /></button>}
                </div>
              </td>
            </tr>
          )}
        />
      )}

      {edit && (
        <Modal onClose={() => setEdit(null)} title={t("p11.rbac.editUser")}>
          <div className="space-y-4">
            <Field label={t("auth.name")}><Input data-testid="edit-user-name" value={edit.name || ""} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></Field>
            <Field label={t("auth.phone")}><Input data-testid="edit-user-phone" value={edit.phone || ""} onChange={(e) => setEdit({ ...edit, phone: e.target.value })} className="force-ltr" /></Field>
            <Field label={t("auth.email")}><Input data-testid="edit-user-email" value={edit.email || ""} onChange={(e) => setEdit({ ...edit, email: e.target.value })} className="force-ltr" /></Field>
            {edit.role === "admin" && (
              <Field label={t("p11.rbac.role")}>
                <select data-testid="edit-user-role" value={edit.admin_role_key || "manager"} onChange={(e) => setEdit({ ...edit, admin_role_key: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white">
                  {roles.map((r) => <option key={r.key} value={r.key}>{lang === "ar" ? r.name_ar : r.name_en}</option>)}
                </select>
              </Field>
            )}
            <Field label={t("p11.rbac.notes")}><Textarea data-testid="edit-user-notes" rows={2} value={edit.notes || ""} onChange={(e) => setEdit({ ...edit, notes: e.target.value })} /></Field>
            <Btn variant="accent" onClick={saveEdit} disabled={busy} data-testid="edit-user-save" className="w-full">{t("p11.rbac.save")}</Btn>
          </div>
        </Modal>
      )}

      {pw && (
        <Modal onClose={() => setPw(null)} title={t("p11.rbac.resetPassword")}>
          <div className="space-y-4">
            <Field label={t("p11.rbac.newPassword")} hint={t("p11.rbac.pwHint")}><Input type="password" data-testid="reset-pw-input" value={pw.password} onChange={(e) => setPw({ ...pw, password: e.target.value })} className="force-ltr" /></Field>
            <Btn variant="accent" onClick={savePw} disabled={busy} data-testid="reset-pw-save" className="w-full">{t("p11.rbac.save")}</Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}
