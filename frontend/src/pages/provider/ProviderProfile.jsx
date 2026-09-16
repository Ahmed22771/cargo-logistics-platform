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
  const [form, setForm] = useState({ name: user?.name || "", company_name: user?.company_name || "", cr_number: user?.cr_number || "" });
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try { const { data } = await api.put("/profile", form); setUser(data); toast.success(t("common.success")); }
    catch (e) { toast.error(apiErr(e)); } finally { setSaving(false); }
  };
  return (
    <div className="max-w-lg">
      <PageHeader title={t("common.profile")} />
      <Card>
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-2xl bg-[#16233A] flex items-center justify-center"><Building2 className="w-8 h-8 text-white" /></div>
          <div><div className="font-bold text-lg text-[#16233A]">{user?.company_name || user?.name}</div><div className="text-sm text-slate-400 force-ltr">{user?.phone}</div></div>
        </div>
        <div className="space-y-4">
          <Field label={t("auth.name")}><Input data-testid="prov-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Company"><Input data-testid="prov-company" value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} /></Field>
          <Field label="CR Number"><Input data-testid="prov-cr" value={form.cr_number} onChange={(e) => setForm({ ...form, cr_number: e.target.value })} className="force-ltr" /></Field>
          <Btn variant="accent" onClick={save} disabled={saving} data-testid="save-prov-btn">{t("common.save")}</Btn>
        </div>
      </Card>
    </div>
  );
}
