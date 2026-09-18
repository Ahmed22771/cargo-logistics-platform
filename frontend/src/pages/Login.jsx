import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Package, Truck, Building2, ArrowLeft, Phone, ShieldCheck } from "lucide-react";
import { CargoLogo } from "../components/CargoLogo";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { Btn, Field, Input } from "../components/ui-kit";
import { useI18n } from "../i18n";
import { useAuth } from "../context/AuthContext";
import api, { apiErr } from "../lib/api";

const ROLES = [
  { key: "customer", icon: Package },
  { key: "driver", icon: Truck },
  { key: "provider", icon: Building2 },
];

export default function Login() {
  const { t, isRTL } = useI18n();
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [role, setRole] = useState(params.get("role") || "");
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [step, setStep] = useState("phone"); // phone | otp
  const [code, setCode] = useState("");
  const [demoCode, setDemoCode] = useState("");
  const [loading, setLoading] = useState(false);

  const sendOtp = async (e) => {
    e.preventDefault();
    if (!phone.trim()) return;
    setLoading(true);
    try {
      const { data } = await api.post("/auth/otp/request", { phone, role, name });
      setDemoCode(data.demo_code);
      setStep("otp");
      toast.success(t("auth.otpSent"));
    } catch (err) {
      toast.error(apiErr(err));
    } finally { setLoading(false); }
  };

  const verify = async (e) => {
    e.preventDefault();
    if (!code.trim()) return;
    setLoading(true);
    try {
      const { data } = await api.post("/auth/otp/verify", { phone, role, name, code });
      loginWithToken(data.token, data.user);
      toast.success(`${t("common.welcome")} ${data.user.name}`);
      navigate(`/${role}`);
    } catch (err) {
      const c = apiErr(err);
      const map = { ACCOUNT_SUSPENDED: t("p4.user.accountSuspended"), ACCOUNT_DISABLED: t("p4.user.accountDisabled") };
      toast.error(map[c] || c);
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="border-b border-slate-100 bg-white">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <button onClick={() => navigate("/")} data-testid="login-logo-home"><CargoLogo size={36} /></button>
          <LanguageSwitcher />
        </div>
      </header>

      <div className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 md:p-8 animate-fade-in">
            {!role ? (
              <>
                <h1 className="text-xl font-bold text-[#16233A] text-center">{t("auth.selectRole")}</h1>
                <div className="space-y-3 mt-6">
                  {ROLES.map((r) => (
                    <button key={r.key} data-testid={`role-${r.key}`} onClick={() => setRole(r.key)}
                      className="w-full flex items-center gap-4 p-4 rounded-xl border border-slate-200 hover:border-[#F1701E] hover:bg-orange-50/40 transition-all text-start">
                      <div className="w-11 h-11 rounded-xl bg-[#16233A] flex items-center justify-center"><r.icon className="w-5 h-5 text-white" /></div>
                      <span className="font-semibold text-[#16233A]">{t(`auth.${r.key}`)}</span>
                      <ArrowLeft className={`w-4 h-4 text-slate-300 ms-auto ${isRTL ? "" : "rotate-180"}`} />
                    </button>
                  ))}
                </div>
              </>
            ) : step === "phone" ? (
              <form onSubmit={sendOtp}>
                <div className="flex items-center gap-2 text-sm text-[#F1701E] font-semibold mb-1">
                  {React.createElement(ROLES.find((r) => r.key === role).icon, { className: "w-4 h-4" })}
                  {t(`auth.${role}`)}
                </div>
                <h1 className="text-xl font-bold text-[#16233A]">{t("common.login")}</h1>
                <p className="text-sm text-slate-500 mt-1 mb-6">{t("auth.phoneHint")}</p>
                <div className="space-y-4">
                  <Field label={t("auth.name")} hint={t("common.optional")}>
                    <Input data-testid="login-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder={t("auth.name")} />
                  </Field>
                  <Field label={t("auth.phone")} required>
                    <div className="relative">
                      <Phone className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />
                      <Input data-testid="login-phone-input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+96890000001" className="ps-9 force-ltr" />
                    </div>
                  </Field>
                  <Btn variant="accent" type="submit" disabled={loading} data-testid="send-otp-btn" className="w-full">
                    {loading ? t("common.loading") : t("auth.sendOtp")}
                  </Btn>
                  <button type="button" onClick={() => { setRole(""); }} className="w-full text-sm text-slate-400 hover:text-slate-600">{t("common.back")}</button>
                </div>
              </form>
            ) : (
              <form onSubmit={verify}>
                <h1 className="text-xl font-bold text-[#16233A]">{t("auth.enterOtp")}</h1>
                <p className="text-sm text-slate-500 mt-1 mb-4 force-ltr text-start">{phone}</p>
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-5 text-sm text-orange-800" data-testid="demo-otp-hint">
                  <span className="font-semibold">{t("auth.demoNote")}</span> <span className="font-mono font-bold text-lg">{demoCode}</span>
                </div>
                <Field label={t("auth.enterOtp")} required>
                  <Input data-testid="otp-input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="000000" maxLength={6} className="force-ltr text-center tracking-[0.5em] text-lg font-mono" />
                </Field>
                <Btn variant="accent" type="submit" disabled={loading} data-testid="verify-otp-btn" className="w-full mt-4">
                  {loading ? t("common.loading") : t("auth.verify")}
                </Btn>
                <button type="button" onClick={() => setStep("phone")} className="w-full text-sm text-slate-400 hover:text-slate-600 mt-3">{t("auth.changePhone")}</button>
              </form>
            )}
          </div>
          <div className="flex items-center justify-center gap-2 mt-5 text-xs text-slate-400">
            <ShieldCheck className="w-4 h-4" /> {isRTL ? "دخول آمن عبر رمز التحقق" : "Secure OTP sign-in"}
          </div>
        </div>
      </div>
    </div>
  );
}
