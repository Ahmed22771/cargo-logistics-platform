import React from "react";
import { useI18n } from "../i18n";

const STATUS_COLORS = {
  DRAFT: "bg-slate-100 text-slate-600 border-slate-200",
  PUBLISHED: "bg-blue-50 text-blue-700 border-blue-200",
  BIDDING: "bg-blue-50 text-blue-700 border-blue-200",
  DRIVER_SELECTED: "bg-amber-50 text-amber-700 border-amber-200",
  DRIVER_ASSIGNED: "bg-amber-50 text-amber-700 border-amber-200",
  PAYMENT_PENDING: "bg-amber-50 text-amber-700 border-amber-200",
  PAID: "bg-emerald-50 text-emerald-700 border-emerald-200",
  DRIVER_EN_ROUTE: "bg-orange-50 text-orange-700 border-orange-200",
  DRIVER_ARRIVED: "bg-orange-50 text-orange-700 border-orange-200",
  LOADING: "bg-orange-50 text-orange-700 border-orange-200",
  LOADED: "bg-orange-50 text-orange-700 border-orange-200",
  IN_TRANSIT: "bg-orange-50 text-orange-700 border-orange-200",
  NEAR_DESTINATION: "bg-orange-50 text-orange-700 border-orange-200",
  DRIVER_ARRIVED_DESTINATION: "bg-orange-50 text-orange-700 border-orange-200",
  DELIVERED_PENDING_CONFIRMATION: "bg-indigo-50 text-indigo-700 border-indigo-200",
  DELIVERED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  COMPLETED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  CANCELLED: "bg-red-50 text-red-700 border-red-200",
  DISPUTED: "bg-red-50 text-red-700 border-red-200",
  REFUNDED: "bg-slate-100 text-slate-600 border-slate-200",
  HELD: "bg-indigo-50 text-indigo-700 border-indigo-200",
  RELEASED: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const VERIF_COLORS = {
  DRAFT: "bg-slate-100 text-slate-600 border-slate-200",
  PENDING: "bg-amber-50 text-amber-700 border-amber-200",
  UNDER_REVIEW: "bg-blue-50 text-blue-700 border-blue-200",
  APPROVED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  REJECTED: "bg-red-50 text-red-700 border-red-200",
  SUSPENDED: "bg-red-50 text-red-700 border-red-200",
};

export function StatusBadge({ status, testId }) {
  const { t } = useI18n();
  const cls = STATUS_COLORS[status] || "bg-slate-100 text-slate-600 border-slate-200";
  return (
    <span data-testid={testId || `status-${status}`} className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${cls}`}>
      {t(`status.${status}`)}
    </span>
  );
}

export function VerificationBadge({ status, testId }) {
  const { t } = useI18n();
  const cls = VERIF_COLORS[status] || "bg-slate-100 text-slate-600 border-slate-200";
  return (
    <span data-testid={testId || `verif-${status}`} className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${cls}`}>
      {t(`verification.${status}`)}
    </span>
  );
}
