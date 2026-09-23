import React, { useState } from "react";
import { toast } from "sonner";
import { User } from "lucide-react";
import { Card, Btn, Field, Input, PageHeader } from "../../components/ui-kit";
import { VerificationBadge } from "../../components/StatusBadge";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";
import api, { apiErr } from "../../lib/api";

export default function DriverProfile() {
  const { t } = useI18n();
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try { const { data } = await api.put("/profile", { name }); setUser(data); toast.success(t("common.success")); }
    catch (e) { toast.error(apiErr(e)); } finally { setSaving(false); }
  };
  // Vehicle type is read from the driver's linked vehicle (user.vehicle), the
  // canonical source used across the system — never duplicated into the profile.
  const vehicle = user?.vehicle || {};
  const rawType = (vehicle.type || vehicle.vehicle_type || "").toString();
  const typeKeyMap = {
    pickup: "shipment.vehiclePickup",
    flatbed: "shipment.vehicleFlatbed",
    container: "shipment.vehicleContainer",
    refrigerated: "shipment.vehicleRefrigerated",
    trailer: "shipment.vehicleTrailer",
  };
  const vehicleTypeLabel = rawType
    ? t(typeKeyMap[rawType.toLowerCase()] || "", rawType)
    : t("common.noVehicle");
  return (
    <div className="max-w-lg">
      <PageHeader title={t("common.profile")} />
      <Card>
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-2xl bg-[#16233A] flex items-center justify-center"><User className="w-8 h-8 text-white" /></div>
          <div>
            <div className="font-bold text-lg text-[#16233A]">{user?.name}</div>
            <div className="text-sm text-slate-400 force-ltr">{user?.phone}</div>
            <div className="mt-1"><VerificationBadge status={user?.verification_status} /></div>
          </div>
        </div>

        <div className="text-xs font-bold uppercase tracking-wide text-slate-400 mb-2">{t("common.personalInfo")}</div>
        <div className="space-y-2 mb-6">
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">{t("auth.phone")}</span>
            <span className="font-medium text-[#16233A] force-ltr" data-testid="driver-profile-phone">{user?.phone || t("common.notProvided")}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">{t("common.email")}</span>
            <span className="font-medium text-[#16233A] force-ltr" data-testid="driver-profile-email">{user?.email || t("common.notProvided")}</span>
          </div>
        </div>

        <div className="text-xs font-bold uppercase tracking-wide text-slate-400 mb-2">{t("common.vehicleInfo")}</div>
        <div className="space-y-2 mb-6">
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">{t("common.vehicleType")}</span>
            <span className="font-medium text-[#16233A]" data-testid="driver-profile-vehicle-type">{vehicleTypeLabel}</span>
          </div>
        </div>

        <Field label={t("auth.name")}><Input data-testid="driver-profile-name" value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Btn variant="accent" onClick={save} disabled={saving} data-testid="save-driver-profile-btn" className="mt-4">{t("common.save")}</Btn>
      </Card>
    </div>
  );
}
