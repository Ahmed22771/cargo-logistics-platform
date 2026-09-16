import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { LogOut, ShieldCheck } from "lucide-react";
import { CargoLogo } from "../../components/CargoLogo";
import { LanguageSwitcher } from "../../components/LanguageSwitcher";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";

export function AdminLayout({ navItems, children }) {
  const { t, lang } = useI18n();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const doLogout = () => { logout(); navigate("/admin"); };

  return (
    <div className="min-h-screen bg-slate-100 flex" dir={lang === "ar" ? "rtl" : "ltr"}>
      <aside className="w-60 shrink-0 bg-[#16233A] text-white flex flex-col sticky top-0 h-screen">
        <div className="p-4 border-b border-white/10 bg-white/5"><div className="bg-white rounded-lg p-2 inline-block"><CargoLogo size={28} /></div>
          <div className="flex items-center gap-1.5 text-[#F1701E] text-xs font-bold mt-2"><ShieldCheck className="w-3.5 h-3.5" /> {t("admin.commandCenter")}</div></div>
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink key={item.to} to={`/admin${item.to}`} end={item.to === ""} data-testid={`admin-nav-${item.key}`}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${isActive ? "bg-[#F1701E] text-white" : "text-slate-300 hover:bg-white/10"}`}>
              <item.icon className="w-[18px] h-[18px]" /> {t(item.label)}
            </NavLink>
          ))}
        </nav>
        <button onClick={doLogout} data-testid="admin-logout-btn" className="m-3 flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold text-red-300 hover:bg-red-500/10">
          <LogOut className="w-[18px] h-[18px]" /> {t("common.logout")}
        </button>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-20">
          <span className="font-bold text-[#16233A]">{user?.name}</span>
          <LanguageSwitcher />
        </header>
        <main className="flex-1 p-4 md:p-6 overflow-x-auto animate-fade-in">{children}</main>
      </div>
    </div>
  );
}

export function Table({ columns, rows, renderRow, testId, empty }) {
  const { t } = useI18n();
  if (!rows || rows.length === 0) {
    return <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-slate-400" data-testid={`${testId}-empty`}>{empty || t("shipment.noShipments")}</div>;
  }
  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm overflow-x-auto" data-testid={testId}>
      <table className="w-full text-sm text-start">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>{columns.map((c, i) => <th key={i} className="px-4 py-3 text-start font-semibold text-slate-500 whitespace-nowrap">{c}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{rows.map(renderRow)}</tbody>
      </table>
    </div>
  );
}
