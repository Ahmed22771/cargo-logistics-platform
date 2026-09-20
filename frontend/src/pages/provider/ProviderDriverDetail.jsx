import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, User, FileText, Truck, Car } from "lucide-react";
import { Card, Spinner, PageHeader } from "../../components/ui-kit";
import { StatusBadge, VerificationBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import api from "../../lib/api";

export default function ProviderDriverDetail() {
  const { id } = useParams();
  const { t } = useI18n();
  const [driver, setDriver] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.get(`/provider/drivers/${id}`).then(({ data }) => setDriver(data)).catch((e) => setError(e?.response?.data?.detail || "error")); }, [id]);
  if (error) return <div className="text-center text-slate-500"><p>{error}</p><Link to="/provider/drivers" className="text-[#F1701E] font-semibold">{t("common.back")}</Link></div>;
  if (!driver) return <Spinner label={t("common.loading")} />;
  return (
    <div className="min-w-0 overflow-x-hidden">
      <Link to="/provider/drivers" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"><ArrowLeft className="w-4 h-4" /> {t("common.back")}</Link>
      <PageHeader title={driver.name || driver.phone} subtitle={<span className="flex items-center gap-1"><User className="w-4 h-4" /> {driver.phone}</span>} action={<VerificationBadge status={driver.verification_status || "DRAFT"} />} />
      <div className="grid gap-4">
        <Card>
          <h3 className="font-bold text-[#16233A] mb-3">{t("provider.driverProfile")}</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><div className="text-slate-400">{t("provider.phone")}</div><div className="font-semibold force-ltr">{driver.phone}</div></div>
            <div><div className="text-slate-400">{t("common.status")}</div><div className="font-semibold">{driver.status || "active"}</div></div>
            <div><div className="text-slate-400">{t("shipment.rating") || "Rating"}</div><div className="font-semibold">{driver.rating || 0} ({driver.rating_count || 0})</div></div>
            <div><div className="text-slate-400">{t("shipment.completedTrips") || "Trips"}</div><div className="font-semibold">{driver.completed_trips || 0}</div></div>
          </div>
        </Card>
        <Card>
          <h3 className="font-bold text-[#16233A] mb-3 flex items-center gap-2"><Car className="w-4 h-4" /> {t("provider.vehicle") || t("nav.vehicle")}</h3>
          {driver.current_vehicle ? (
            <Link to={`/provider/vehicles/${driver.current_vehicle.id}`} className="text-[#F1701E] font-semibold force-ltr">{driver.current_vehicle.plate_number}</Link>
          ) : <p className="text-sm text-slate-500">{t("provider.unassigned")}</p>}
        </Card>
        <Card>
          <h3 className="font-bold text-[#16233A] mb-3 flex items-center gap-2"><FileText className="w-4 h-4" /> {t("provider.viewDocs")}</h3>
          {(driver.documents || []).length === 0 ? <p className="text-sm text-slate-500">{t("common.none")}</p> : (
            <div className="grid gap-2">
              {driver.documents.map((d) => (
                <div key={d.id} className="border border-slate-200 rounded-lg p-3 flex items-center justify-between gap-3">
                  <div className="min-w-0"><div className="font-semibold text-[#16233A] truncate">{d.doc_type_name_ar || d.doc_type_key}</div><div className="text-xs text-slate-400">{d.reference || "\u2014"} \u00b7 {d.expiry || "\u2014"}</div></div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${d.status === "APPROVED" ? "bg-emerald-50 text-emerald-700" : d.status === "REJECTED" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>{d.status}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card>
          <h3 className="font-bold text-[#16233A] mb-3 flex items-center gap-2"><Truck className="w-4 h-4" /> {t("provider.tripHistory")}</h3>
          {(driver.trips || []).length === 0 ? <p className="text-sm text-slate-500">{t("common.none")}</p> : (
            <div className="grid gap-2">
              {driver.trips.map((tr) => (
                <Link key={tr.id} to={`/provider/trips/${tr.id}`} className="border border-slate-200 rounded-lg p-3 hover:border-[#F1701E] transition-colors">
                  <div className="flex items-center justify-between gap-2 min-w-0">
                    <div className="font-semibold text-[#16233A] truncate">{tr.shipment_title || tr.id}</div>
                    <StatusBadge status={tr.status} />
                  </div>
                  <div className="text-xs text-slate-400 mt-1">{tr.created_at ? new Date(tr.created_at).toLocaleDateString() : "\u2014"} \u00b7 {tr.price} {t("common.currency")}</div>
                </Link>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
