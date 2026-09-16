import React from "react";
import { AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import { useI18n } from "../../i18n";
import { useAuth } from "../../context/AuthContext";

export function VerificationBanner() {
  const { t } = useI18n();
  const { user } = useAuth();
  const status = user?.verification_status;
  if (status === "APPROVED") {
    return (
      <div data-testid="verif-banner-approved" className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl p-4 mb-5">
        <CheckCircle2 className="w-5 h-5 shrink-0" /><span className="text-sm font-medium">{t("verification.approvedBanner")}</span>
      </div>
    );
  }
  if (["PENDING", "UNDER_REVIEW"].includes(status)) {
    return (
      <div data-testid="verif-banner-pending" className="flex items-center gap-3 bg-blue-50 border border-blue-200 text-blue-800 rounded-xl p-4 mb-5">
        <Clock className="w-5 h-5 shrink-0" /><span className="text-sm font-medium">{t("verification.pendingBanner")}</span>
      </div>
    );
  }
  return (
    <div data-testid="verif-banner-blocked" className="flex items-center gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-4 mb-5">
      <AlertTriangle className="w-5 h-5 shrink-0" /><span className="text-sm font-medium">{t("verification.notApprovedBanner")}</span>
    </div>
  );
}
