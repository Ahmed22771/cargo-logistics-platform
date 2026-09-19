import React, { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { LogOut, Menu, ShieldCheck, X } from "lucide-react";
import { CargoLogo } from "../../components/CargoLogo";
import { LanguageSwitcher } from "../../components/LanguageSwitcher";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";

export function AdminLayout({ navItems, children }) {
  const { t, lang } = useI18n();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isRTL = lang === "ar";
  const drawerSide = isRTL ? "right-0" : "left-0";
  const closedTransform = isRTL ? "translate-x-full" : "-translate-x-full";
  const doLogout = () => { logout(); navigate("/admin"); setMobileMenuOpen(false); };

  useEffect(() => { setMobileMenuOpen(false); }, [location.pathname]);

  return (
    <div className="min-h-screen bg-slate-100 flex relative" dir={isRTL ? "rtl" : "ltr"}>
      {mobileMenuOpen && <button aria-label={t("common.close")} data-testid="admin-mobile-overlay" className="fixed inset-0 z-30 bg-black/45 md:hidden" onClick={() => setMobileMenuOpen(false)} />}
      <aside className={`fixed inset-y-0 ${drawerSide} z-40 w-60 shrink-0 bg-[#16233A] text-white flex flex-col shadow-2xl transition-transform duration-200 ease-out ${mobileMenuOpen ? "translate-x-0" : closedTransform} md:static md:z-auto md:translate-x-0 md:shadow-none`}>
        <div className="p-4 border-b border-white/10 bg-white/5">
          <div className="flex items-start justify-between gap-3">
            <div className="bg-white rounded-lg p-2 inline-block"><CargoLogo size={28} /></div>
            <button onClick={() => setMobileMenuOpen(false)} aria-label={t("common.close")} data-testid="admin-mobile-close" className="md:hidden rounded-lg p-2 text-slate-300 hover:bg-white/10">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="flex items-center gap-1.5 text-[#F1701E] text-xs font-bold mt-2"><ShieldCheck className="w-3.5 h-3.5" /> {t("admin.commandCenter")}</div>
        </div>
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink key={item.to} to={`/admin${item.to}`} end={item.to === ""} data-testid={`admin-nav-${item.key}`} onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${isActive ? "bg-[#F1701E] text-white" : "text-slate-300 hover:bg-white/10"}`}>
              <item.icon className="w-[18px] h-[18px]" /> {t(item.label)}
            </NavLink>
          ))}
        </nav>
        <button onClick={doLogout} data-testid="admin-logout-btn" className="m-3 flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold text-red-300 hover:bg-red-500/10">
          <LogOut className="w-[18px] h-[18px]" /> {t("common.logout")}
        </button>
      </aside>
      <div className="flex-1 flex flex-col min-w-0 w-full">
        <header className="bg-white border-b border-slate-200 px-4 md:px-6 py-3 flex items-center justify-between sticky top-0 z-20">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setMobileMenuOpen(true)} aria-label={t("admin.menu")} data-testid="admin-mobile-menu" className="md:hidden shrink-0 rounded-lg p-2 text-[#16233A] hover:bg-slate-100">
              <Menu className="w-5 h-5" />
            </button>
            <span className="font-bold text-[#16233A] truncate">{user?.name}</span>
          </div>
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
