import React, { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Bell, LogOut, Menu, X } from "lucide-react";
import { CargoLogo } from "./CargoLogo";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { useAuth } from "../context/AuthContext";
import { useI18n } from "../i18n";
import api from "../lib/api";

export function PortalLayout({ navItems, basePath, title, children }) {
  const { user, logout } = useAuth();
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifs, setNotifs] = useState([]);

  const loadNotifs = async () => {
    try { const { data } = await api.get("/notifications"); setNotifs(data); } catch {}
  };
  useEffect(() => { loadNotifs(); const i = setInterval(loadNotifs, 15000); return () => clearInterval(i); }, []);
  const unread = notifs.filter((n) => !n.read).length;

  const resolveLink = (n) => {
    const m = n.meta || {};
    const et = n.entity_type || m.entity_type;
    const shipmentId = m.shipment_id;
    if (basePath === "/customer") {
      if (shipmentId) return `/customer/shipment/${shipmentId}`;
      return "/customer";
    }
    if (basePath === "/driver") {
      if (et === "trip" || n.type === "bid_accepted" || n.type === "trip_update") return "/driver/trip";
      if (et === "verification" || n.type === "verification") return "/driver/verification";
      if (et === "document" || n.type === "document") return "/driver/documents";
      return "/driver";
    }
    if (basePath === "/provider") return "/provider";
    return basePath;
  };

  const openNotification = async (n) => {
    if (!n.read) {
      try { await api.post(`/notifications/${n.id}/read`); } catch {}
    }
    setNotifOpen(false);
    loadNotifs();
    navigate(resolveLink(n));
  };

  const doLogout = () => { logout(); navigate("/"); };

  const SideNav = ({ onNavigate }) => (
    <nav className="flex flex-col gap-1" data-testid="portal-sidebar-nav">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={`${basePath}${item.to}`}
          end={item.to === ""}
          onClick={onNavigate}
          data-testid={`nav-${item.key}`}
          className={({ isActive }) =>
            `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-semibold transition-colors ${
              isActive ? "bg-[#16233A] text-white" : "text-slate-600 hover:bg-slate-100"
            }`
          }
        >
          <item.icon className="w-[18px] h-[18px] shrink-0" />
          <span className="truncate">{t(item.label)}</span>
        </NavLink>
      ))}
    </nav>
  );

  // mobile bottom nav uses first 5 items
  const bottomItems = navItems.slice(0, 5);

  return (
    <div className="min-h-screen bg-slate-50 flex" dir={lang === "ar" ? "rtl" : "ltr"}>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 shrink-0 flex-col border-e border-slate-200 bg-white p-4 sticky top-0 h-screen">
        <div className="px-2 py-3"><CargoLogo size={34} /></div>
        <div className="text-xs font-bold uppercase tracking-wider text-slate-400 px-3 mt-2 mb-2">{title}</div>
        <div className="flex-1 overflow-y-auto"><SideNav /></div>
        <button onClick={doLogout} data-testid="logout-btn" className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-semibold text-red-600 hover:bg-red-50 mt-2">
          <LogOut className="w-[18px] h-[18px]" /> {t("common.logout")}
        </button>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-slate-200">
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <div className="flex items-center gap-2">
              <button className="lg:hidden p-2 -ms-2" onClick={() => setMobileOpen(true)} data-testid="mobile-menu-btn">
                <Menu className="w-5 h-5 text-slate-700" />
              </button>
              <div className="lg:hidden"><CargoLogo size={30} showText={false} /></div>
              <span className="font-bold text-[#16233A] hidden sm:block">{t("common.welcome")}, {user?.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <LanguageSwitcher />
              <div className="relative">
                <button onClick={() => setNotifOpen((v) => !v)} data-testid="notifications-btn" className="relative p-2 rounded-lg hover:bg-slate-100">
                  <Bell className="w-5 h-5 text-slate-700" />
                  {unread > 0 && <span data-testid="notif-count" className="absolute top-1 end-1 min-w-[16px] h-4 px-1 bg-[#F1701E] text-white text-[10px] font-bold rounded-full flex items-center justify-center">{unread}</span>}
                </button>
                {notifOpen && (
                  <div className="absolute end-0 mt-2 w-80 max-w-[90vw] bg-white border border-slate-200 rounded-xl shadow-lg z-50 max-h-96 overflow-auto" data-testid="notif-dropdown">
                    <div className="px-4 py-3 border-b font-bold text-[#16233A]">{t("common.notifications")}</div>
                    {notifs.length === 0 ? (
                      <div className="px-4 py-8 text-center text-sm text-slate-400">{t("common.none")}</div>
                    ) : notifs.map((n) => (
                      <button key={n.id} data-testid={`notif-item-${n.id}`} onClick={() => openNotification(n)} className={`w-full text-start px-4 py-3 border-b last:border-0 hover:bg-slate-50 ${!n.read ? "bg-orange-50/40" : ""}`}>
                        <div className="text-sm font-semibold text-slate-800">{lang === "ar" ? n.title_ar : n.title_en}</div>
                        {(n.body_ar || n.body_en) && <div className="text-xs text-slate-500 mt-0.5">{lang === "ar" ? n.body_ar : n.body_en}</div>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6 pb-24 lg:pb-6 max-w-6xl w-full mx-auto">{children}</main>

        {/* Mobile bottom nav */}
        <nav className="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-white border-t border-slate-200 flex" data-testid="mobile-bottom-nav">
          {bottomItems.map((item) => (
            <NavLink
              key={item.to}
              to={`${basePath}${item.to}`}
              end={item.to === ""}
              data-testid={`bottomnav-${item.key}`}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] font-semibold ${isActive ? "text-[#F1701E]" : "text-slate-500"}`
              }
            >
              <item.icon className="w-5 h-5" />
              <span className="truncate max-w-full px-0.5">{t(item.label)}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 start-0 w-72 bg-white p-4 flex flex-col shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <CargoLogo size={32} />
              <button onClick={() => setMobileOpen(false)}><X className="w-5 h-5 text-slate-600" /></button>
            </div>
            <div className="flex-1 overflow-y-auto"><SideNav onNavigate={() => setMobileOpen(false)} /></div>
            <button onClick={doLogout} className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-semibold text-red-600 hover:bg-red-50 mt-2">
              <LogOut className="w-[18px] h-[18px]" /> {t("common.logout")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
