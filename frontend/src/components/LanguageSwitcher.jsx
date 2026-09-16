import React from "react";
import { useI18n } from "../i18n";
import { Globe } from "lucide-react";

export function LanguageSwitcher({ dark = false }) {
  const { lang, setLang } = useI18n();
  return (
    <div
      className={`inline-flex items-center rounded-lg border overflow-hidden text-sm font-semibold ${
        dark ? "border-white/20" : "border-slate-200"
      }`}
      data-testid="language-switcher"
    >
      <Globe className={`w-4 h-4 mx-2 ${dark ? "text-white/70" : "text-slate-400"}`} />
      <button
        data-testid="lang-switcher-ar"
        onClick={() => setLang("ar")}
        className={`px-3 py-1.5 transition-colors ${
          lang === "ar" ? "bg-[#F1701E] text-white" : dark ? "text-white/80 hover:bg-white/10" : "text-slate-600 hover:bg-slate-50"
        }`}
      >
        عربي
      </button>
      <button
        data-testid="lang-switcher-en"
        onClick={() => setLang("en")}
        className={`px-3 py-1.5 transition-colors ${
          lang === "en" ? "bg-[#F1701E] text-white" : dark ? "text-white/80 hover:bg-white/10" : "text-slate-600 hover:bg-slate-50"
        }`}
      >
        EN
      </button>
    </div>
  );
}
