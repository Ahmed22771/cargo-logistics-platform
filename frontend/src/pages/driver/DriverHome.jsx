import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Truck, Package, Star, ClipboardList, Gavel } from "lucide-react";
import { Card, Spinner, PageHeader, Btn } from "../../components/ui-kit";
import { VerificationBadge } from "../../components/StatusBadge";
import { VerificationBanner } from "./VerificationBanner";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";

export default function DriverHome() {
  const { t } = useI18n();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);

  useEffect(() => {
    Promise.all([
      user?.verification_status === "APPROVED" ? api.get("/marketplace/shipments").then((r) => r.data).catch(() => []) : Promise.resolve([]),
      api.get("/driver/bids").then((r) => r.data).catch(() => []),
      api.get("/trips/mine").then((r) => r.data).catch(() => []),
    ]).then(([market, bids, trips]) => setData({ market, bids, trips }));
  }, [user]);

  if (!data) return <Spinner label={t("common.loading")} />;
  const active = data.trips.filter((tr) => !["COMPLETED", "CANCELLED"].includes(tr.status));

  const stats = [
    { label: t("nav.availableShipments"), value: data.market.length, icon: Package, color: "text-[#F1701E] bg-[#F1701E]/10", to: "/driver/available" },
    { label: t("nav.myBids"), value: data.bids.length, icon: Gavel, color: "text-[#16233A] bg-[#16233A]/5", to: "/driver/bids" },
    { label: t("nav.activeTrip"), value: active.length, icon: Truck, color: "text-emerald-600 bg-emerald-50", to: "/driver/trip" },
  ];

  return (
    <div>
      <PageHeader title={`${t("common.welcome")} ${user?.name}`} action={<VerificationBadge status={user?.verification_status} />} />
      <VerificationBanner />
      <div className="grid grid-cols-3 gap-3 md:gap-5 mb-6">
        {stats.map((s, i) => (
          <Card key={i} data-testid={`driver-stat-${i}`} className="!p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(s.to)}>
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${s.color}`}><s.icon className="w-5 h-5" /></div>
            <div className="text-2xl md:text-3xl font-extrabold text-[#16233A]">{s.value}</div>
            <div className="text-xs md:text-sm text-slate-500 mt-1">{s.label}</div>
          </Card>
        ))}
      </div>
      <Card>
        <h2 className="font-bold text-[#16233A] mb-3 flex items-center gap-2"><Star className="w-5 h-5 text-[#F1701E]" /> {t("bid.rating")}</h2>
        <div className="flex items-center gap-6">
          <div><div className="text-3xl font-extrabold text-[#16233A]">{user?.rating || 0}</div><div className="text-xs text-slate-400">{t("bid.rating")} ({user?.rating_count || 0})</div></div>
          <div><div className="text-3xl font-extrabold text-[#16233A]">{user?.completed_trips || 0}</div><div className="text-xs text-slate-400">{t("bid.completedTrips")}</div></div>
          <div className="ms-auto"><Btn variant="outline" data-testid="go-verification-btn" onClick={() => navigate("/driver/verification")}><ClipboardList className="w-4 h-4" /> {t("nav.verification")}</Btn></div>
        </div>
      </Card>
    </div>
  );
}
