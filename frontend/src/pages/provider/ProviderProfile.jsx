import React, { useState } from "react";
import { toast } from "sonner";
import { Building2 } from "lucide-react";
import { Card, Btn, Field, Input, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api, { apiErr } from "../../lib/api";

export default function ProviderProfile() {
  const { t } = useI18n();
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    name: user?.name || "",
    company_name: user?.company_name || "",
    address: user?.address || "",
    email: user?.email || "",
    phone: user?.phone || "",
    cr_number: user?.cr_number || "",
  });
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try { const { data } = await api.put("/profile", form); setUser(data); toast.success(t("common.success")); }
    catch (e) { toast.error(apiErr(e)); } finally { setSaving(false); }
  };
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  return (
    <div className="max-w-lg min-w-0">
      <PageHeader title={t("common.profile")} />
      <Card className="min-w-0">
        <div className="flex items-center gap-4 mb-6 min-w-0">
          <div className="w-16 h-16 shrink-0 rounded-2xl bg-[#16233A] flex items-center justify-center"><Building2 className="w-8 h-8 text-white" /></div>
          <div className="min-w-0"><div className="font-bold text-lg text-[#16233A] truncate">{user?.company_name || user?.name}</div><div className="text-sm text-slate-400 force-ltr truncate">{user?.phone}</div></div>
        </div>
        <div className="space-y-4">
          <Field label={t("provider.companyName")}><Input data-testid="prov-company" value={form.company_name} onChange={set("company_name")} /></Field>
          <Field label={t("auth.name")}><Input data-testid="prov-name" value={form.name} onChange={set("name")} /></Field>
          <Field label={t("provider.address")}><Input data-testid="prov-address" value={form.address} onChange={set("address")} /></Field>
          <Field label={t("provider.email")}><Input data-testid="prov-email" type="email" value={form.email} onChange={set("email")} className="force-ltr" /></Field>
          <Field label={t("provider.phone")}><Input data-testid="prov-phone" type="tel" value={form.phone} onChange={set("phone")} className="force-ltr" /></Field>
          <Field label={t("provider.crNumber")}><Input data-testid="prov-cr" value={form.cr_number} onChange={set("cr_number")} className="force-ltr" /></Field>
          <Btn variant="accent" onClick={save} disabled={saving} data-testid="save-prov-btn">{t("common.save")}</Btn>
        </div>
      </Card>
    </div>
  );
}
