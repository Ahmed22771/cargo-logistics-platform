import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { UserPlus, ShieldCheck, X, Check } from "lucide-react";
import { Table } from "./AdminLayout";
import { Card, Btn, Spinner, PageHeader, Input, Field } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

export default function AdminAccess() {
  const { t, lang } = useI18n();
  const [admins, setAdmins] = useState(null);
  const [roles, setRoles] = useState([]);
  const [permCatalog, setPermCatalog] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", admin_role_key: "operations_manager" });
  const [busy, setBusy] = useState(false);

  const load = () => {
    Promise.all([
      api.get("/admin/admins").then((r) => r.data).catch(() => []),
      api.get("/admin/roles").then((r) => r.data).catch(() => []),
      api.get("/admin/permissions").then((r) => r.data.permissions).catch(() => []),
    ]).then(([a, r, p]) => { setAdmins(a); setRoles(r); setPermCatalog(p); });
  };
  useEffect(() => { load(); }, []);
  if (admins === null) return <Spinner label={t("common.loading")} />;

  const roleName = (key) => { const r = roles.find((x) => x.key === key); return r ? (lang === "ar" ? r.name_ar : r.name_en) : key; };

  const createAdmin = async () => {
    if (!form.name || !form.email || !form.password) { toast.error(t("common.required")); return; }
    setBusy(true);
    try { await api.post("/admin/admins", form); toast.success(t("common.success")); setShowCreate(false); setForm({ name: "", email: "", password: "", admin_role_key: "operations_manager" }); load(); }
    catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };
  const assign = async (id, key) => {
    try { await api.put(`/admin/admins/${id}/role`, { admin_role_key: key }); toast.success(t("common.success")); load(); }
    catch (e) { toast.error(apiErr(e)); }
  };

  return (
    <div>
      <PageHeader title={t("p11.rbac.users")} action={<Btn variant="accent" data-testid="create-admin-btn" onClick={() => setShowCreate(true)}><UserPlus className="w-4 h-4" /> {t("p11.rbac.createAdmin")}</Btn>} />

      <Table testId="admins-table" rows={admins}
        columns={[t("p11.rbac.name"), t("p11.rbac.email"), t("p11.rbac.role"), ""]}
        renderRow={(a) => (
          <tr key={a.id} data-testid={`admin-user-row-${a.id}`} className="hover:bg-slate-50">
            <td className="px-4 py-3 font-semibold text-[#16233A]">{a.name}</td>
            <td className="px-4 py-3 text-slate-500 force-ltr">{a.email}</td>
            <td className="px-4 py-3">
              <select data-testid={`role-select-${a.id}`} value={a.admin_role_key || "super_admin"} onChange={(e) => assign(a.id, e.target.value)}
                className="border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white">
                {roles.map((r) => <option key={r.key} value={r.key}>{lang === "ar" ? r.name_ar : r.name_en}</option>)}
              </select>
            </td>
            <td className="px-4 py-3"><span className="inline-flex items-center gap-1 text-xs text-emerald-600"><ShieldCheck className="w-3.5 h-3.5" /> active</span></td>
          </tr>
        )}
      />

      <h2 className="text-lg font-bold text-[#16233A] mt-8 mb-3">{t("p11.rbac.roles")}</h2>
      <div className="grid md:grid-cols-2 gap-4">
        {roles.map((r) => (
          <Card key={r.key} data-testid={`role-card-${r.key}`} className="!p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="font-bold text-[#16233A]">{lang === "ar" ? r.name_ar : r.name_en}</div>
              <span className="text-xs text-slate-400">{r.permissions.length} {t("p11.rbac.perms")}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {r.permissions.slice(0, 8).map((p) => <span key={p} className="text-[10px] bg-slate-100 text-slate-600 rounded px-1.5 py-0.5 font-mono">{p}</span>)}
              {r.permissions.length > 8 && <span className="text-[10px] text-slate-400">+{r.permissions.length - 8}</span>}
            </div>
          </Card>
        ))}
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => setShowCreate(false)} />
          <div className="relative bg-white rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4"><h2 className="font-bold text-lg text-[#16233A]">{t("p11.rbac.createAdmin")}</h2><button onClick={() => setShowCreate(false)}><X className="w-5 h-5 text-slate-400" /></button></div>
            <div className="space-y-4">
              <Field label={t("p11.rbac.name")} required><Input data-testid="new-admin-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
              <Field label={t("p11.rbac.email")} required><Input data-testid="new-admin-email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="force-ltr" /></Field>
              <Field label={t("p11.rbac.password")} required><Input type="password" data-testid="new-admin-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="force-ltr" /></Field>
              <Field label={t("p11.rbac.role")}>
                <select data-testid="new-admin-role" value={form.admin_role_key} onChange={(e) => setForm({ ...form, admin_role_key: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white">
                  {roles.map((r) => <option key={r.key} value={r.key}>{lang === "ar" ? r.name_ar : r.name_en}</option>)}
                </select>
              </Field>
              <Btn variant="accent" onClick={createAdmin} disabled={busy} data-testid="submit-admin-btn" className="w-full"><Check className="w-4 h-4" /> {t("p11.rbac.create")}</Btn>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
