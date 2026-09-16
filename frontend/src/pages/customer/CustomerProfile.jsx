import React, { useState } from "react";
import { toast } from "sonner";
import { User } from "lucide-react";
import { Card, Btn, Field, Input, PageHeader } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api, { apiErr } from "../../lib/api";

export default function CustomerProfile() {
  const { t } = useI18n();
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try { const { data } = await api.put("/profile", { name, email }); setUser(data); toast.success(t("common.success")); }
    catch (e) { toast.error(apiErr(e)); } finally { setSaving(false); }
  };

  return (
    <div className="max-w-lg">
      <PageHeader title={t("common.profile")} />
      <Card>
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-2xl bg-[#16233A] flex items-center justify-center"><User className="w-8 h-8 text-white" /></div>
          <div><div className="font-bold text-lg text-[#16233A]">{user?.name}</div><div className="text-sm text-slate-400 force-ltr">{user?.phone}</div></div>
        </div>
        <div className="space-y-4">
          <Field label={t("auth.name")}><Input data-testid="profile-name" value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label={t("auth.email")}><Input data-testid="profile-email" value={email} onChange={(e) => setEmail(e.target.value)} className="force-ltr" /></Field>
          <Btn variant="accent" onClick={save} disabled={saving} data-testid="save-profile-btn">{t("common.save")}</Btn>
        </div>
      </Card>
    </div>
  );
}
