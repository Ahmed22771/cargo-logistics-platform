import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Truck, Package, Container, Boxes, Zap, ArrowLeft, CheckCircle2, ShieldCheck, Users, Building2, Phone, Mail, MapPin } from "lucide-react";
import { CargoLogo } from "../components/CargoLogo";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { Btn } from "../components/ui-kit";
import { useI18n } from "../i18n";

export default function Landing() {
  const { t, isRTL } = useI18n();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const services = [
    { icon: Truck, title: t("landing.svcLand"), desc: t("landing.svcLandDesc") },
    { icon: Container, title: t("landing.svcContainer"), desc: t("landing.svcContainerDesc") },
    { icon: Boxes, title: t("landing.svcFlatbed"), desc: t("landing.svcFlatbedDesc") },
    { icon: Zap, title: t("landing.svcExpress"), desc: t("landing.svcExpressDesc") },
  ];
  const steps = [
    { n: "1", icon: Package, title: t("landing.step1Title"), desc: t("landing.step1Desc") },
    { n: "2", icon: Users, title: t("landing.step2Title"), desc: t("landing.step2Desc") },
    { n: "3", icon: Truck, title: t("landing.step3Title"), desc: t("landing.step3Desc") },
  ];
  const who = [
    { icon: Package, title: t("landing.customerCard"), desc: t("landing.customerCardDesc"), to: "/login?role=customer" },
    { icon: Truck, title: t("landing.driverCard"), desc: t("landing.driverCardDesc"), to: "/login?role=driver" },
    { icon: Building2, title: t("landing.providerCard"), desc: t("landing.providerCardDesc"), to: "/login?role=provider" },
  ];

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <CargoLogo size={38} />
          <nav className="hidden md:flex items-center gap-7 text-sm font-semibold text-slate-600">
            <a href="#how" className="hover:text-[#16233A]">{t("nav.howItWorks")}</a>
            <a href="#services" className="hover:text-[#16233A]">{t("nav.services")}</a>
            <a href="#who" className="hover:text-[#16233A]">{t("nav.about")}</a>
            <a href="#contact" className="hover:text-[#16233A]">{t("nav.contact")}</a>
          </nav>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <Btn data-testid="header-login-btn" onClick={() => navigate("/login")} className="hidden sm:inline-flex">{t("common.login")}</Btn>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden bg-[#16233A] text-white">
        <div
          className="absolute inset-0 opacity-20"
          style={{ backgroundImage: "url('https://images.pexels.com/photos/30484147/pexels-photo-30484147.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')", backgroundSize: "cover", backgroundPosition: "center" }}
        />
        <div className="absolute inset-0" style={{ background: "linear-gradient(90deg, #16233A 30%, rgba(22,35,58,0.85))" }} />
        <div className="relative max-w-6xl mx-auto px-4 py-16 md:py-24">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 bg-white/10 border border-white/15 rounded-full px-3 py-1 text-xs font-semibold mb-5">
              <MapPin className="w-3.5 h-3.5 text-[#F1701E]" /> سلطنة عُمان · Oman
            </span>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-tight">{t("landing.heroTitle")}</h1>
            <p className="text-base md:text-lg text-slate-300 mt-5 leading-relaxed">{t("landing.heroSub")}</p>
            <div className="flex flex-wrap gap-3 mt-8">
              <Btn variant="accent" data-testid="hero-cta-primary" onClick={() => navigate("/login?role=customer")} className="text-base py-3 px-6">
                {t("landing.ctaPrimary")} <ArrowLeft className={`w-4 h-4 ${isRTL ? "" : "rotate-180"}`} />
              </Btn>
              <Btn variant="secondary" data-testid="hero-cta-secondary" onClick={() => document.getElementById("how")?.scrollIntoView({ behavior: "smooth" })} className="text-base py-3 px-6 bg-white/10 text-white hover:bg-white/20">
                {t("landing.ctaSecondary")}
              </Btn>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-12 max-w-lg">
              {[["12,400+", t("landing.statShipments")], ["850+", t("landing.statDrivers")], ["< 30m", t("landing.statResponse")]].map(([v, l], i) => (
                <div key={i}>
                  <div className="text-2xl md:text-3xl font-extrabold text-[#F1701E]">{v}</div>
                  <div className="text-xs text-slate-300 mt-1">{l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* How */}
      <section id="how" className="max-w-6xl mx-auto px-4 py-16 md:py-20">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-[#16233A]">{t("landing.howTitle")}</h2>
          <p className="text-slate-500 mt-2">{t("landing.howSub")}</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((s) => (
            <div key={s.n} className="relative bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
              <div className="absolute -top-3 end-6 w-9 h-9 bg-[#F1701E] text-white rounded-lg font-extrabold flex items-center justify-center">{s.n}</div>
              <div className="w-12 h-12 rounded-xl bg-[#16233A]/5 flex items-center justify-center mb-4"><s.icon className="w-6 h-6 text-[#16233A]" /></div>
              <h3 className="font-bold text-lg text-[#16233A]">{s.title}</h3>
              <p className="text-sm text-slate-500 mt-2 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Services */}
      <section id="services" className="bg-slate-50 border-y border-slate-100">
        <div className="max-w-6xl mx-auto px-4 py-16 md:py-20">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#16233A]">{t("landing.servicesTitle")}</h2>
            <p className="text-slate-500 mt-2">{t("landing.servicesSub")}</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {services.map((s, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="w-12 h-12 rounded-xl bg-[#F1701E]/10 flex items-center justify-center mb-4"><s.icon className="w-6 h-6 text-[#F1701E]" /></div>
                <h3 className="font-bold text-[#16233A]">{s.title}</h3>
                <p className="text-sm text-slate-500 mt-2 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Who */}
      <section id="who" className="max-w-6xl mx-auto px-4 py-16 md:py-20">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-[#16233A]">{t("landing.whoTitle")}</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {who.map((w, i) => (
            <button key={i} data-testid={`who-card-${i}`} onClick={() => navigate(w.to)} className="text-start bg-white border border-slate-200 rounded-xl p-7 shadow-sm hover:shadow-md hover:border-[#F1701E]/40 transition-all group">
              <div className="w-14 h-14 rounded-2xl bg-[#16233A] flex items-center justify-center mb-5"><w.icon className="w-7 h-7 text-white" /></div>
              <h3 className="font-bold text-lg text-[#16233A]">{w.title}</h3>
              <p className="text-sm text-slate-500 mt-2 leading-relaxed">{w.desc}</p>
              <span className="inline-flex items-center gap-1.5 mt-4 text-sm font-semibold text-[#F1701E]">
                {t("common.login")} <ArrowLeft className={`w-4 h-4 group-hover:${isRTL ? "-translate-x-1" : "translate-x-1"} transition-transform ${isRTL ? "" : "rotate-180"}`} />
              </span>
            </button>
          ))}
        </div>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-500">
          {[["مركبات موثقة", "Verified fleet", ShieldCheck], ["سائقون معتمدون", "Approved drivers", CheckCircle2], ["تغطية كامل السلطنة", "Nationwide coverage", MapPin]].map(([ar, en, Ic], i) => (
            <div key={i} className="flex items-center gap-2"><Ic className="w-4 h-4 text-[#F1701E]" /> {isRTL ? ar : en}</div>
          ))}
        </div>
      </section>

      {/* Contact / Footer */}
      <footer id="contact" className="bg-[#16233A] text-white">
        <div className="max-w-6xl mx-auto px-4 py-14">
          <div className="grid md:grid-cols-2 gap-10">
            <div>
              <CargoLogo size={40} dark />
              <p className="text-slate-300 mt-4 max-w-md leading-relaxed">{t("landing.heroSub")}</p>
              <p className="text-[#F1701E] font-semibold mt-3">نقل ذكي.. يصل بثقة</p>
            </div>
            <div>
              <h3 className="font-bold text-lg mb-4">{t("landing.contactTitle")}</h3>
              <div className="space-y-3 text-sm text-slate-300">
                <div className="flex items-center gap-3"><Phone className="w-4 h-4 text-[#F1701E]" /> <span className="force-ltr">+968 2400 0000</span></div>
                <div className="flex items-center gap-3"><Mail className="w-4 h-4 text-[#F1701E]" /> support@cargo.om</div>
                <div className="flex items-center gap-3"><MapPin className="w-4 h-4 text-[#F1701E]" /> {isRTL ? "مسقط، سلطنة عُمان" : "Muscat, Oman"}</div>
              </div>
            </div>
          </div>
          <div className="border-t border-white/10 mt-10 pt-6 text-center text-sm text-slate-400">
            © {new Date().getFullYear()} CARGO كارجو — {t("landing.footerRights")}
          </div>
        </div>
      </footer>
    </div>
  );
}
