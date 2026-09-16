import React from "react";
import { MapPin, ArrowLeft } from "lucide-react";
import { useI18n } from "../i18n";

export function RouteDisplay({ pickup, delivery, compact = false }) {
  const { t } = useI18n();
  return (
    <div className={`flex items-stretch gap-3 ${compact ? "" : "py-1"}`} data-testid="route-display">
      <div className="flex flex-col items-center pt-1">
        <MapPin className="w-4 h-4 text-[#F1701E]" />
        <div className="w-px flex-1 my-1 bg-slate-300 border-s border-dashed" style={{ minHeight: compact ? 14 : 22 }} />
        <MapPin className="w-4 h-4 text-[#16233A]" />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        <div>
          <div className="text-[11px] font-bold text-[#F1701E] uppercase tracking-wide">{t("common.from")}</div>
          <div className="text-sm text-slate-700 truncate">{pickup?.address || "—"}</div>
        </div>
        <div>
          <div className="text-[11px] font-bold text-[#16233A] uppercase tracking-wide">{t("common.to")}</div>
          <div className="text-sm text-slate-700 truncate">{delivery?.address || "—"}</div>
        </div>
      </div>
    </div>
  );
}

export function RouteInline({ pickup, delivery }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-2 text-sm text-slate-600" data-testid="route-inline">
      <span className="truncate max-w-[45%]">{pickup?.address || t("common.from")}</span>
      <ArrowLeft className="w-4 h-4 text-[#F1701E] shrink-0 rtl:rotate-0 ltr:rotate-180" />
      <span className="truncate max-w-[45%]">{delivery?.address || t("common.to")}</span>
    </div>
  );
}
