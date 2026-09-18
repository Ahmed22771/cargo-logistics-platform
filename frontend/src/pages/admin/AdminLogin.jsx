import React, { useState } from "react";
import { toast } from "sonner";
import { Lock, ShieldCheck } from "lucide-react";
import { CargoLogo } from "../../components/CargoLogo";
import { LanguageSwitcher } from "../../components/LanguageSwitcher";
import { Btn, Field, Input } from "../../components/ui-kit";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api, { apiErr } from "../../lib/api";

export default function AdminLogin() {
  const { t } = useI18n();
  const { loginWithToken } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/auth/admin/login", { email, password });
      loginWithToken(data.token, data.user);
      toast.success(t("common.welcome"));
    } catch (err) {
      const c = apiErr(err, t("auth.invalidCreds"));
      const map = { ACCOUNT_SUSPENDED: t("p4.user.accountSuspended"), ACCOUNT_DISABLED: t("p4.user.accountDisabled") };
      toast.error(map[c] || c);
    }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-[#0E1726] flex flex-col items-center justify-center px-4" data-testid="admin-login-screen">
      <div className="absolute top-4 end-4"><LanguageSwitcher dark /></div>
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-6">
          <div className="bg-white rounded-2xl p-4 mb-4"><CargoLogo size={40} /></div>
          <div className="flex items-center gap-2 text-[#F1701E] font-bold"><ShieldCheck className="w-5 h-5" /> {t("auth.adminPortal")}</div>
        </div>
        <form onSubmit={submit} className="bg-white rounded-2xl shadow-xl p-6 md:p-8">
          <div className="flex items-center gap-2 text-[#16233A] font-bold text-lg mb-1"><Lock className="w-5 h-5" /> {t("auth.adminLogin")}</div>
          <p className="text-xs text-slate-400 mb-6">{t("auth.secureArea")}</p>
          <div className="space-y-4">
            <Field label={t("auth.email")} required><Input data-testid="admin-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="force-ltr" /></Field>
            <Field label={t("auth.password")} required><Input data-testid="admin-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="force-ltr" /></Field>
            <Btn variant="primary" type="submit" disabled={busy} data-testid="admin-login-btn" className="w-full">{busy ? t("common.loading") : t("auth.adminLogin")}</Btn>
          </div>
        </form>
      </div>
    </div>
  );
}
