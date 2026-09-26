import React, { useEffect, useMemo, useState } from "react";
import {
  Building2,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Edit3,
  FileText,
  Gavel,
  Hash,
  Package,
  RefreshCw,
  Search,
  Send,
  Truck,
  User,
  Wallet,
  X,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import {
  Card,
  Btn,
  Field,
  Input,
  Textarea,
  Spinner,
  EmptyState,
  PageHeader,
} from "../../components/ui-kit";

import { RouteInline } from "../../components/RouteDisplay";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";

const ACTIVE_BID_STATUSES = new Set([
  "SUBMITTED",
  "UNDER_REVIEW",
  "SHORTLISTED",
  "AWARDED",
]);

const WITHDRAWABLE_BID_STATUSES = new Set([
  "SUBMITTED",
  "UNDER_REVIEW",
  "SHORTLISTED",
]);

const OPEN_CONTRACT_STATUSES = new Set([
  "PUBLISHED",
  "BIDDING",
]);

function bidKey(contractId, lotId) {
  return `${contractId}::${lotId || "FULL"}`;
}

function formatMoney(value, currency = "OMR") {
  if (value == null || value === "") return "—";

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return `${value} ${currency}`;
  }

  return `${number.toFixed(3)} ${currency}`;
}

function formatNumber(value) {
  if (value == null || value === "") return "—";

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return String(value);
  }

  return number.toLocaleString();
}

function StatusPill({ status, label }) {
  let className =
    "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold";

  if (
    status === "AWARDED" ||
    status === "COMPLETED"
  ) {
    className +=
      " bg-emerald-50 text-emerald-700 border border-emerald-200";
  } else if (
    status === "REJECTED" ||
    status === "CANCELLED" ||
    status === "EXPIRED" ||
    status === "WITHDRAWN"
  ) {
    className +=
      " bg-red-50 text-red-700 border border-red-200";
  } else if (
    status === "UNDER_REVIEW" ||
    status === "SHORTLISTED" ||
    status === "BIDDING"
  ) {
    className +=
      " bg-amber-50 text-amber-700 border border-amber-200";
  } else {
    className +=
      " bg-slate-50 text-slate-700 border border-slate-200";
  }

  return (
    <span className={className}>
      {label || status}
    </span>
  );
}

function InfoItem({ icon: Icon, label, value, className = "" }) {
  return (
    <div
      className={`rounded-lg border border-slate-100 bg-slate-50/70 p-3 ${className}`}
    >
      <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
        {Icon ? <Icon className="w-3.5 h-3.5 shrink-0" /> : null}
        <span>{label}</span>
      </div>

      <div className="text-sm font-semibold text-[#16233A] break-words">
        {value ?? "—"}
      </div>
    </div>
  );
}

function BidModal({
  target,
  existingBid,
  onClose,
  onSaved,
}) {
  const { t, lang } = useI18n();

  const text = (key, ar, en) =>
    t(key, lang === "ar" ? ar : en);

  const [quantity, setQuantity] = useState(
    existingBid?.quantity_offered != null
      ? String(existingBid.quantity_offered)
      : ""
  );

  const [unitPrice, setUnitPrice] = useState(
    existingBid?.unit_price != null
      ? String(existingBid.unit_price)
      : ""
  );

  const [executionDays, setExecutionDays] = useState(
    existingBid?.execution_days != null
      ? String(existingBid.execution_days)
      : ""
  );

  const [availableVehicles, setAvailableVehicles] = useState(
    existingBid?.available_vehicles != null
      ? String(existingBid.available_vehicles)
      : ""
  );

  const [notes, setNotes] = useState(
    existingBid?.notes || ""
  );

  const [busy, setBusy] = useState(false);

  const contract = target?.contract;
  const lot = target?.lot || null;

  if (!contract) {
    return null;
  }

  const isEdit = Boolean(existingBid);

  const quantityLimit = lot
    ? Number(lot.quantity || 0)
    : Number(contract.total_units || 0);

  const currency =
    lot?.currency ||
    contract.currency ||
    "OMR";

  const totalPrice =
    Number(quantity) > 0 &&
    Number(unitPrice) > 0
      ? Number(quantity) * Number(unitPrice)
      : 0;

  const submit = async () => {
    if (busy) return;

    const q = Number.parseInt(quantity, 10);
    const price = Number(unitPrice);
    const days =
      executionDays.trim() === ""
        ? null
        : Number.parseInt(executionDays, 10);

    const vehicles =
      availableVehicles.trim() === ""
        ? null
        : Number.parseInt(availableVehicles, 10);

    if (!Number.isInteger(q) || q <= 0) {
      toast.error(
        text(
          "providerContracts.invalidQuantity",
          "الكمية يجب أن تكون رقمًا صحيحًا أكبر من صفر.",
          "Quantity must be a positive whole number."
        )
      );
      return;
    }

    if (
      Number.isFinite(quantityLimit) &&
      quantityLimit > 0 &&
      q > quantityLimit
    ) {
      toast.error(
        text(
          "providerContracts.quantityExceeds",
          "الكمية المطلوبة في العرض تتجاوز الكمية المتاحة.",
          "The offered quantity exceeds the available quantity."
        )
      );
      return;
    }

    if (!Number.isFinite(price) || price <= 0) {
      toast.error(
        t("pay.priceInvalid")
      );
      return;
    }

    if (
      days !== null &&
      (!Number.isInteger(days) || days < 1)
    ) {
      toast.error(
        text(
          "providerContracts.executionDaysInvalid",
          "مدة التنفيذ يجب أن تكون عددًا صحيحًا أكبر من صفر.",
          "Execution days must be a positive whole number."
        )
      );
      return;
    }

    if (
      vehicles !== null &&
      (!Number.isInteger(vehicles) || vehicles < 0)
    ) {
      toast.error(
        text(
          "providerContracts.vehicleCountInvalid",
          "عدد المركبات يجب أن يكون صفرًا أو أكثر.",
          "Available vehicles must be zero or more."
        )
      );
      return;
    }

    const payload = {
      lot_id: lot?.id || null,
      quantity_offered: q,
      unit_price: price,
      execution_days: days,
      available_vehicles: vehicles,
      notes: notes.trim(),
      document_ids: existingBid?.document_ids || [],
    };

    setBusy(true);

    try {
      if (isEdit) {
        await api.put(
          `/provider/contract-bids/${existingBid.id}`,
          payload
        );

        toast.success(
          text(
            "providerContracts.bidUpdated",
            "تم تحديث العرض بنجاح.",
            "Bid updated successfully."
          )
        );
      } else {
        await api.post(
          `/provider/contracts/${contract.id}/bids`,
          payload
        );

        toast.success(
          text(
            "providerContracts.bidSubmitted",
            "تم تقديم العرض بنجاح.",
            "Bid submitted successfully."
          )
        );
      }

      onSaved?.();
      onClose();
    } catch (error) {
      toast.error(apiErr(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={() => !busy && onClose()}
      />

      <div className="relative bg-white rounded-2xl w-full max-w-2xl max-h-[92vh] overflow-y-auto shadow-2xl">
        <div className="sticky top-0 z-10 bg-white border-b border-slate-100 px-5 py-4 flex items-center justify-between">
          <div className="min-w-0">
            <h3 className="font-bold text-[#16233A] truncate">
              {isEdit
                ? text(
                    "providerContracts.editBid",
                    "تعديل العرض",
                    "Edit Bid"
                  )
                : text(
                    "providerContracts.submitBid",
                    "تقديم عرض",
                    "Submit Bid"
                  )}
            </h3>

            <div className="text-xs text-slate-500 mt-1 truncate">
              {lot?.name || contract.title}
            </div>
          </div>

          <button
            type="button"
            onClick={() => !busy && onClose()}
            className="rounded-lg p-2 hover:bg-slate-100"
            aria-label={text(
              "common.cancel",
              "إلغاء",
              "Cancel"
            )}
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <InfoItem
              icon={FileText}
              label={text(
                "providerContracts.contract",
                "العقد",
                "Contract"
              )}
              value={contract.title}
            />

            <InfoItem
              icon={Package}
              label={
                lot
                  ? text(
                      "providerContracts.lot",
                      "المنافسة الجزئية",
                      "Lot"
                    )
                  : text(
                      "providerContracts.scope",
                      "نطاق المنافسة",
                      "Competition Scope"
                    )
              }
              value={
                lot
                  ? lot.name
                  : text(
                      "providerContracts.wholeContract",
                      "العقد بالكامل",
                      "Whole Contract"
                    )
              }
            />

            <InfoItem
              icon={Package}
              label={text(
                "adminContracts.unitsLabel",
                "عدد الوحدات",
                "Units"
              )}
              value={formatNumber(
                lot?.quantity ?? contract.total_units
              )}
            />

            <InfoItem
              icon={Wallet}
              label={text(
                "adminContracts.targetContractValue",
                "القيمة المستهدفة",
                "Target Value"
              )}
              value={formatMoney(
                lot?.target_price ?? contract.target_total_price,
                currency
              )}
            />
          </div>

          <div className="rounded-xl border border-orange-100 bg-orange-50/60 p-4">
            <div className="text-sm font-semibold text-[#16233A] mb-3">
              {text(
                "providerContracts.offerDetails",
                "بيانات العرض",
                "Bid Details"
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field
                label={text(
                  "providerContracts.quantityOffered",
                  "الكمية التي تستطيع تنفيذها",
                  "Quantity You Can Execute"
                )}
                required
              >
                <Input
                  type="number"
                  min="1"
                  step="1"
                  value={quantity}
                  onChange={(e) =>
                    setQuantity(e.target.value)
                  }
                  className="force-ltr"
                  placeholder="1"
                />
              </Field>

              <Field
                label={t("provider.bidPrice")}
                required
              >
                <Input
                  type="number"
                  min="0"
                  step="0.001"
                  value={unitPrice}
                  onChange={(e) =>
                    setUnitPrice(e.target.value)
                  }
                  className="force-ltr"
                  placeholder="0.000"
                />
              </Field>

              <Field
                label={text(
                  "providerContracts.totalOffer",
                  "إجمالي العرض",
                  "Total Offer"
                )}
              >
                <div className="w-full bg-slate-100 text-[#16233A] border border-slate-200 rounded-lg px-3 py-2.5 text-sm font-bold force-ltr">
                  {totalPrice > 0
                    ? formatMoney(totalPrice, currency)
                    : "—"}
                </div>
              </Field>

              <Field
                label={text(
                  "providerContracts.executionDays",
                  "مدة التنفيذ بالأيام",
                  "Execution Days"
                )}
              >
                <Input
                  type="number"
                  min="1"
                  step="1"
                  value={executionDays}
                  onChange={(e) =>
                    setExecutionDays(e.target.value)
                  }
                  className="force-ltr"
                  placeholder="—"
                />
              </Field>

              <Field
                label={text(
                  "providerContracts.availableVehicles",
                  "المركبات المتاحة",
                  "Available Vehicles"
                )}
              >
                <Input
                  type="number"
                  min="0"
                  step="1"
                  value={availableVehicles}
                  onChange={(e) =>
                    setAvailableVehicles(e.target.value)
                  }
                  className="force-ltr"
                  placeholder="—"
                />
              </Field>

              <Field
                label={text(
                  "providerContracts.quantityLimit",
                  "الحد الأقصى للكمية",
                  "Maximum Quantity"
                )}
              >
                <div className="w-full bg-slate-100 text-slate-700 border border-slate-200 rounded-lg px-3 py-2.5 text-sm force-ltr">
                  {formatNumber(quantityLimit)}
                </div>
              </Field>
            </div>

            <div className="mt-4">
              <Field label={t("provider.bidNote")}>
                <Textarea
                  rows={4}
                  value={notes}
                  onChange={(e) =>
                    setNotes(e.target.value)
                  }
                  placeholder={text(
                    "providerContracts.notesPlaceholder",
                    "أضف أي ملاحظات مرتبطة بالعرض...",
                    "Add any notes related to your bid..."
                  )}
                />
              </Field>
            </div>
          </div>

          <div className="flex flex-col-reverse sm:flex-row gap-2">
            <Btn
              variant="secondary"
              onClick={onClose}
              disabled={busy}
              className="flex-1 justify-center"
            >
              {t("common.cancel")}
            </Btn>

            <Btn
              variant="accent"
              onClick={submit}
              disabled={busy}
              className="flex-1 justify-center"
            >
              {busy ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}

              {busy
                ? t("common.loading")
                : isEdit
                ? text(
                    "providerContracts.saveBid",
                    "حفظ التعديل",
                    "Save Changes"
                  )
                : text(
                    "providerContracts.submitBid",
                    "تقديم العرض",
                    "Submit Bid"
                  )}
            </Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

function ContractCard({
  contract,
  myBidMap,
  onBid,
  onEditBid,
  onWithdrawBid,
}) {
  const { t, lang } = useI18n();

  const text = (key, ar, en) =>
    t(key, lang === "ar" ? ar : en);

  const isSplit =
    contract.competition_mode === "SPLIT";

  const lots = Array.isArray(contract.lots)
    ? contract.lots
    : [];

  const contractBid = myBidMap.get(
    bidKey(contract.id, null)
  );

  const currency =
    contract.currency || "OMR";

  return (
    <Card
      className="min-w-0 overflow-hidden"
      data-testid={`provider-contract-${contract.id}`}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 text-slate-600 px-2.5 py-1 text-xs font-semibold">
                <Hash className="w-3.5 h-3.5" />
                {contract.contract_number ||
                  text(
                    "providerContracts.noContractNumber",
                    "بدون رقم",
                    "No number"
                  )}
              </span>

              <StatusPill
                status={contract.status}
                label={t(
                  `adminContracts.status.${contract.status}`,
                  contract.status
                )}
              />
            </div>

            <h3 className="font-bold text-[#16233A] text-base sm:text-lg break-words">
              {contract.title}
            </h3>

            {contract.customer_name && (
              <div className="flex items-center gap-2 text-sm text-slate-500 mt-1">
                <Building2 className="w-4 h-4 shrink-0" />
                <span>{contract.customer_name}</span>
              </div>
            )}
          </div>

          <div className="shrink-0">
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-orange-200 bg-orange-50 text-[#F1701E] px-3 py-2 text-xs font-bold">
              <Gavel className="w-4 h-4" />
              {isSplit
                ? text(
                    "providerContracts.splitCompetition",
                    "منافسة مقسمة",
                    "Split Competition"
                  )
                : text(
                    "providerContracts.fullCompetition",
                    "منافسة على كامل العقد",
                    "Full Contract Competition"
                  )}
            </span>
          </div>
        </div>

        {contract.description && (
          <p className="text-sm text-slate-500 line-clamp-3">
            {contract.description}
          </p>
        )}

        <RouteInline
          pickup={contract.pickup_location}
          delivery={contract.delivery_location}
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <InfoItem
            icon={Package}
            label={t("adminContracts.unitsLabel")}
            value={formatNumber(contract.total_units)}
          />

          <InfoItem
            icon={Truck}
            label={t("adminContracts.unitTypePlaceholder")}
            value={contract.unit_type || "—"}
          />

          <InfoItem
            icon={Truck}
            label={t("adminContracts.shipmentType")}
            value={contract.cargo_type || "—"}
          />

          <InfoItem
            icon={Wallet}
            label={t("adminContracts.targetContractValue")}
            value={formatMoney(
              contract.target_total_price,
              currency
            )}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <InfoItem
            icon={CalendarDays}
            label={t("adminContracts.executionDates")}
            value={
              contract.start_date ||
              contract.end_date
                ? `${contract.start_date || "—"} → ${
                    contract.end_date || "—"
                  }`
                : "—"
            }
          />

          <InfoItem
            icon={Clock3}
            label={t(
              "adminContracts.biddingDeadlineLabel"
            )}
            value={contract.bidding_deadline || "—"}
          />
        </div>

        {!isSplit ? (
          <div className="rounded-xl border border-slate-100 p-4 bg-white">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <div className="text-sm font-bold text-[#16233A]">
                  {text(
                    "providerContracts.wholeContract",
                    "العقد بالكامل",
                    "Whole Contract"
                  )}
                </div>

                <div className="text-xs text-slate-500 mt-1">
                  {text(
                    "providerContracts.submitWholeHint",
                    "يمكن للشركة تقديم عرض لتنفيذ الكمية المطلوبة من العقد.",
                    "Your company can submit a bid for the required contract quantity."
                  )}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {contractBid ? (
                  <>
                    <StatusPill
                      status={contractBid.status}
                      label={t(
                        `adminContracts.bidStatus.${contractBid.status}`,
                        contractBid.status
                      )}
                    />

                    {contractBid.status === "SUBMITTED" && (
                      <Btn
                        variant="secondary"
                        onClick={() =>
                          onEditBid(
                            contract,
                            null,
                            contractBid
                          )
                        }
                      >
                        <Edit3 className="w-4 h-4" />
                        {text(
                          "providerContracts.edit",
                          "تعديل",
                          "Edit"
                        )}
                      </Btn>
                    )}

                    {WITHDRAWABLE_BID_STATUSES.has(
                      contractBid.status
                    ) && (
                      <Btn
                        variant="secondary"
                        onClick={() =>
                          onWithdrawBid(contractBid)
                        }
                      >
                        <XCircle className="w-4 h-4" />
                        {text(
                          "providerContracts.withdraw",
                          "سحب العرض",
                          "Withdraw"
                        )}
                      </Btn>
                    )}
                  </>
                ) : (
                  <Btn
                    variant="accent"
                    onClick={() =>
                      onBid(contract, null)
                    }
                    data-testid={`provider-contract-bid-${contract.id}`}
                  >
                    <Gavel className="w-4 h-4" />
                    {text(
                      "providerContracts.submitBid",
                      "تقديم عرض",
                      "Submit Bid"
                    )}
                  </Btn>
                )}
              </div>
            </div>

            {contractBid && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
                <InfoItem
                  icon={Package}
                  label={text(
                    "providerContracts.offeredQuantity",
                    "الكمية المعروضة",
                    "Offered Quantity"
                  )}
                  value={formatNumber(
                    contractBid.quantity_offered
                  )}
                />

                <InfoItem
                  icon={Wallet}
                  label={t("provider.bidPrice")}
                  value={formatMoney(
                    contractBid.unit_price,
                    currency
                  )}
                />

                <InfoItem
                  icon={Wallet}
                  label={text(
                    "providerContracts.totalOffer",
                    "إجمالي العرض",
                    "Total Offer"
                  )}
                  value={formatMoney(
                    contractBid.total_price,
                    currency
                  )}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Gavel className="w-4 h-4 text-[#F1701E]" />
                <h4 className="font-bold text-[#16233A]">
                  {text(
                    "providerContracts.availableLots",
                    "المنافسات الجزئية المتاحة",
                    "Available Lots"
                  )}
                </h4>
              </div>

              <span className="text-xs text-slate-500">
                {lots.length}{" "}
                {text(
                  "providerContracts.lotsCount",
                  "منافسة",
                  "lots"
                )}
              </span>
            </div>

            {lots.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 p-5 text-center text-sm text-slate-500">
                {text(
                  "providerContracts.noLots",
                  "لا توجد منافسات جزئية متاحة حاليًا.",
                  "No available lots at the moment."
                )}
              </div>
            ) : (
              lots.map((lot) => {
                const existingBid =
                  myBidMap.get(
                    bidKey(contract.id, lot.id)
                  );

                const lotCurrency =
                  lot.currency ||
                  currency;

                return (
                  <div
                    key={lot.id}
                    className="rounded-xl border border-slate-200 bg-slate-50/50 p-4"
                    data-testid={`provider-contract-lot-${lot.id}`}
                  >
                    <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className="inline-flex items-center gap-1 rounded-full bg-white border border-slate-200 text-slate-600 px-2 py-1 text-xs font-semibold">
                            <Hash className="w-3.5 h-3.5" />
                            {lot.lot_number ||
                              text(
                                "providerContracts.lot",
                                "Lot",
                                "Lot"
                              )}
                          </span>

                          <StatusPill
                            status={lot.status}
                            label={
                              t(
                                `adminContracts.status.${lot.status}`,
                                lot.status
                              )
                            }
                          />
                        </div>

                        <h5 className="font-bold text-[#16233A]">
                          {lot.name}
                        </h5>

                        {lot.description && (
                          <p className="text-sm text-slate-500 mt-1 line-clamp-2">
                            {lot.description}
                          </p>
                        )}

                        <div className="mt-3">
                          <RouteInline
                            pickup={
                              lot.pickup_location ||
                              contract.pickup_location
                            }
                            delivery={
                              lot.delivery_location ||
                              contract.delivery_location
                            }
                          />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-3">
                          <InfoItem
                            icon={Package}
                            label={text(
                              "providerContracts.lotQuantity",
                              "الكمية",
                              "Quantity"
                            )}
                            value={formatNumber(
                              lot.quantity
                            )}
                          />

                          <InfoItem
                            icon={Truck}
                            label={text(
                              "providerContracts.vehicleType",
                              "نوع المركبة",
                              "Vehicle Type"
                            )}
                            value={
                              lot.vehicle_type ||
                              contract.vehicle_type ||
                              "—"
                            }
                          />

                          <InfoItem
                            icon={Package}
                            label={t(
                              "adminContracts.requiredCapacity"
                            )}
                            value={
                              lot.required_capacity ||
                              contract.required_capacity ||
                              "—"
                            }
                          />

                          <InfoItem
                            icon={Wallet}
                            label={text(
                              "providerContracts.targetLotPrice",
                              "السعر المستهدف",
                              "Target Price"
                            )}
                            value={formatMoney(
                              lot.target_price,
                              lotCurrency
                            )}
                          />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                          <InfoItem
                            icon={CalendarDays}
                            label={text(
                              "providerContracts.pickupDate",
                              "الاستلام",
                              "Pickup"
                            )}
                            value={
                              lot.pickup_date ||
                              contract.pickup_date ||
                              "—"
                            }
                          />

                          <InfoItem
                            icon={CalendarDays}
                            label={text(
                              "providerContracts.deliveryDate",
                              "التسليم",
                              "Delivery"
                            )}
                            value={
                              lot.delivery_date ||
                              contract.delivery_date ||
                              "—"
                            }
                          />
                        </div>
                      </div>

                      <div className="lg:w-56 shrink-0">
                        {existingBid ? (
                          <div className="rounded-xl bg-white border border-slate-200 p-3 space-y-3">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-xs text-slate-500">
                                {text(
                                  "providerContracts.myBid",
                                  "عرضي",
                                  "My Bid"
                                )}
                              </span>

                              <StatusPill
                                status={existingBid.status}
                                label={t(
                                  `adminContracts.bidStatus.${existingBid.status}`,
                                  existingBid.status
                                )}
                              />
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                              <InfoItem
                                label={text(
                                  "providerContracts.offeredQuantity",
                                  "الكمية",
                                  "Qty"
                                )}
                                value={formatNumber(
                                  existingBid.quantity_offered
                                )}
                              />

                              <InfoItem
                                label={t("provider.bidPrice")}
                                value={formatMoney(
                                  existingBid.unit_price,
                                  lotCurrency
                                )}
                              />
                            </div>

                            <div className="flex flex-col gap-2">
                              {existingBid.status ===
                                "SUBMITTED" && (
                                <Btn
                                  variant="secondary"
                                  onClick={() =>
                                    onEditBid(
                                      contract,
                                      lot,
                                      existingBid
                                    )
                                  }
                                  className="w-full justify-center"
                                >
                                  <Edit3 className="w-4 h-4" />
                                  {text(
                                    "providerContracts.edit",
                                    "تعديل",
                                    "Edit"
                                  )}
                                </Btn>
                              )}

                              {WITHDRAWABLE_BID_STATUSES.has(
                                existingBid.status
                              ) && (
                                <Btn
                                  variant="secondary"
                                  onClick={() =>
                                    onWithdrawBid(
                                      existingBid
                                    )
                                  }
                                  className="w-full justify-center"
                                >
                                  <XCircle className="w-4 h-4" />
                                  {text(
                                    "providerContracts.withdraw",
                                    "سحب العرض",
                                    "Withdraw"
                                  )}
                                </Btn>
                              )}

                              {!ACTIVE_BID_STATUSES.has(
                                existingBid.status
                              ) &&
                                existingBid.status !==
                                  "WITHDRAWN" && (
                                  <Btn
                                    variant="accent"
                                    onClick={() =>
                                      onBid(
                                        contract,
                                        lot
                                      )
                                    }
                                    className="w-full justify-center"
                                  >
                                    <Gavel className="w-4 h-4" />
                                    {text(
                                      "providerContracts.submitNewBid",
                                      "تقديم عرض جديد",
                                      "Submit New Bid"
                                    )}
                                  </Btn>
                                )}
                            </div>
                          </div>
                        ) : (
                          <Btn
                            variant="accent"
                            onClick={() =>
                              onBid(
                                contract,
                                lot
                              )
                            }
                            className="w-full justify-center"
                            data-testid={`provider-lot-bid-${lot.id}`}
                          >
                            <Gavel className="w-4 h-4" />
                            {text(
                              "providerContracts.submitBid",
                              "تقديم عرض",
                              "Submit Bid"
                            )}
                          </Btn>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

function MyBidCard({
  bid,
  onEdit,
  onWithdraw,
}) {
  const { t, lang } = useI18n();

  const text = (key, ar, en) =>
    t(key, lang === "ar" ? ar : en);

  const contract =
    bid.contract || null;

  const lot =
    bid.lot || null;

  const currency =
    lot?.currency ||
    contract?.currency ||
    "OMR";

  return (
    <Card
      className="min-w-0 overflow-hidden"
      data-testid={`provider-my-contract-bid-${bid.id}`}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 text-slate-600 px-2.5 py-1 text-xs font-semibold">
                <Gavel className="w-3.5 h-3.5" />
                {t(
                  `adminContracts.bidStatus.${bid.status}`,
                  bid.status
                )}
              </span>

              {lot && (
                <span className="inline-flex items-center gap-1 rounded-full bg-orange-50 text-orange-700 border border-orange-200 px-2.5 py-1 text-xs font-semibold">
                  {lot.name}
                </span>
              )}
            </div>

            <h3 className="font-bold text-[#16233A] break-words">
              {contract?.title ||
                text(
                  "providerContracts.contractUnavailable",
                  "العقد غير متاح",
                  "Contract unavailable"
                )}
            </h3>

            {contract?.contract_number && (
              <div className="text-xs text-slate-500 mt-1">
                {contract.contract_number}
              </div>
            )}
          </div>

          <StatusPill
            status={bid.status}
            label={t(
              `adminContracts.bidStatus.${bid.status}`,
              bid.status
            )}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <InfoItem
            icon={Package}
            label={text(
              "providerContracts.offeredQuantity",
              "الكمية المعروضة",
              "Offered Quantity"
            )}
            value={formatNumber(
              bid.quantity_offered
            )}
          />

          <InfoItem
            icon={Wallet}
            label={t("provider.bidPrice")}
            value={formatMoney(
              bid.unit_price,
              currency
            )}
          />

          <InfoItem
            icon={Wallet}
            label={text(
              "providerContracts.totalOffer",
              "إجمالي العرض",
              "Total Offer"
            )}
            value={formatMoney(
              bid.total_price,
              currency
            )}
          />

          <InfoItem
            icon={Clock3}
            label={text(
              "providerContracts.executionDays",
              "مدة التنفيذ",
              "Execution Days"
            )}
            value={
              bid.execution_days != null
                ? `${bid.execution_days}`
                : "—"
            }
          />
        </div>

        {bid.notes && (
          <div className="rounded-lg bg-slate-50 border border-slate-100 p-3 text-sm text-slate-600">
            {bid.notes}
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {bid.status === "SUBMITTED" && (
            <Btn
              variant="secondary"
              onClick={() => onEdit(bid)}
            >
              <Edit3 className="w-4 h-4" />
              {text(
                "providerContracts.edit",
                "تعديل",
                "Edit"
              )}
            </Btn>
          )}

          {WITHDRAWABLE_BID_STATUSES.has(
            bid.status
          ) && (
            <Btn
              variant="secondary"
              onClick={() => onWithdraw(bid)}
            >
              <XCircle className="w-4 h-4" />
              {text(
                "providerContracts.withdraw",
                "سحب العرض",
                "Withdraw"
              )}
            </Btn>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function ProviderContracts() {
  const { t, lang } = useI18n();

  const text = (key, ar, en) =>
    t(key, lang === "ar" ? ar : en);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [contracts, setContracts] = useState([]);
  const [myBids, setMyBids] = useState([]);

  const [query, setQuery] = useState("");
  const [tab, setTab] = useState("open");

  const [modalTarget, setModalTarget] =
    useState(null);

  const [editingBid, setEditingBid] =
    useState(null);

  const load = async (silent = false) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const [
        contractsResponse,
        bidsResponse,
      ] = await Promise.all([
        api.get("/provider/contracts"),
        api.get("/provider/contract-bids"),
      ]);

      setContracts(
        Array.isArray(contractsResponse.data)
          ? contractsResponse.data
          : []
      );

      setMyBids(
        Array.isArray(bidsResponse.data)
          ? bidsResponse.data
          : []
      );
    } catch (error) {
      toast.error(apiErr(error));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const myBidMap = useMemo(() => {
    const map = new Map();

    for (const bid of myBids) {
      map.set(
        bidKey(
          bid.contract_id,
          bid.lot_id
        ),
        bid
      );
    }

    return map;
  }, [myBids]);

  const filteredContracts = useMemo(() => {
    const q = query.trim().toLowerCase();

    return contracts.filter((contract) => {
      if (
        !OPEN_CONTRACT_STATUSES.has(
          contract.status
        )
      ) {
        return false;
      }

      if (!q) return true;

      const searchable = [
        contract.title,
        contract.contract_number,
        contract.customer_name,
        contract.customer_id,
        contract.unit_type,
        contract.cargo_type,
        contract.vehicle_type,
        ...(Array.isArray(contract.lots)
          ? contract.lots.flatMap((lot) => [
              lot.name,
              lot.lot_number,
              lot.vehicle_type,
              lot.unit_type,
            ])
          : []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchable.includes(q);
    });
  }, [contracts, query]);

  const openBid = (
    contract,
    lot = null
  ) => {
    setEditingBid(null);

    setModalTarget({
      contract,
      lot,
    });
  };

  const openEditBid = (
    contract,
    lot,
    bid
  ) => {
    setEditingBid(bid);

    setModalTarget({
      contract,
      lot,
    });
  };

  const closeModal = () => {
    setModalTarget(null);
    setEditingBid(null);
  };

  const refreshAfterBid = async () => {
    await load(true);
  };

  const getTargetForBid = (bid) => {
    let contract = bid.contract;

    if (!contract) {
      contract = contracts.find(
        (item) =>
          item.id === bid.contract_id
      );
    }

    if (!contract) {
      return null;
    }

    let lot = bid.lot || null;

    if (!lot && bid.lot_id) {
      lot =
        (contract.lots || []).find(
          (item) =>
            item.id === bid.lot_id
        ) || null;
    }

    return {
      contract,
      lot,
    };
  };

  const withdrawBid = async (bid) => {
    const confirmed = window.confirm(
      text(
        "providerContracts.confirmWithdraw",
        "هل أنت متأكد من سحب هذا العرض؟",
        "Are you sure you want to withdraw this bid?"
      )
    );

    if (!confirmed) return;

    try {
      await api.post(
        `/provider/contract-bids/${bid.id}/withdraw`
      );

      toast.success(
        text(
          "providerContracts.bidWithdrawn",
          "تم سحب العرض.",
          "Bid withdrawn."
        )
      );

      await load(true);
    } catch (error) {
      toast.error(apiErr(error));
    }
  };

  if (loading) {
    return (
      <Spinner
        label={t("common.loading")}
      />
    );
  }

  return (
    <div className="min-w-0 overflow-x-hidden">
      <PageHeader
        title={t("adminContracts.title")}
      />

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-5">
        <div className="text-sm text-slate-500">
          {text(
            "providerContracts.subtitle",
            "اطّلع على العقود والمنافسات المنشورة وقدّم عروض شركتك مباشرة.",
            "View published contracts and competitions and submit your company's bids."
          )}
        </div>

        <Btn
          variant="secondary"
          onClick={() => load(true)}
          disabled={refreshing}
        >
          <RefreshCw
            className={`w-4 h-4 ${
              refreshing
                ? "animate-spin"
                : ""
            }`}
          />

          {text(
            "adminContracts.refresh",
            "تحديث",
            "Refresh"
          )}
        </Btn>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
        <InfoItem
          icon={Gavel}
          label={text(
            "providerContracts.openCompetitions",
            "المنافسات المفتوحة",
            "Open Competitions"
          )}
          value={filteredContracts.length}
        />

        <InfoItem
          icon={Send}
          label={text(
            "providerContracts.myBidsCount",
            "إجمالي عروضي",
            "My Bids"
          )}
          value={myBids.length}
        />

        <InfoItem
          icon={CheckCircle2}
          label={text(
            "providerContracts.activeBids",
            "العروض النشطة",
            "Active Bids"
          )}
          value={
            myBids.filter((bid) =>
              ACTIVE_BID_STATUSES.has(
                bid.status
              )
            ).length
          }
        />
      </div>

      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <button
          type="button"
          onClick={() => setTab("open")}
          className={`flex-1 rounded-xl px-4 py-3 text-sm font-bold transition ${
            tab === "open"
              ? "bg-[#16233A] text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          {text(
            "providerContracts.openCompetitions",
            "العقود والمنافسات المفتوحة",
            "Open Contracts & Competitions"
          )}
        </button>

        <button
          type="button"
          onClick={() => setTab("bids")}
          className={`flex-1 rounded-xl px-4 py-3 text-sm font-bold transition ${
            tab === "bids"
              ? "bg-[#16233A] text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          {text(
            "providerContracts.myBids",
            "عروضي",
            "My Bids"
          )}
        </button>
      </div>

      {tab === "open" ? (
        <>
          <div className="mb-4 relative">
            <Search className="absolute top-1/2 -translate-y-1/2 start-3 w-4 h-4 text-slate-400" />

            <Input
              value={query}
              onChange={(e) =>
                setQuery(e.target.value)
              }
              placeholder={text(
                "providerContracts.searchPlaceholder",
                "ابحث برقم العقد أو الاسم أو الشركة أو نوع الشحنة أو المنافسة...",
                "Search by contract number, title, company, cargo type, or lot..."
              )}
              className="ps-9"
              data-testid="provider-contracts-search"
            />
          </div>

          {filteredContracts.length === 0 ? (
            <Card>
              <EmptyState
                icon={Gavel}
                title={text(
                  "providerContracts.empty",
                  "لا توجد عقود أو منافسات متاحة حاليًا.",
                  "No contracts or competitions are currently available."
                )}
              />
            </Card>
          ) : (
            <div className="grid gap-4">
              {filteredContracts.map(
                (contract) => (
                  <ContractCard
                    key={contract.id}
                    contract={contract}
                    myBidMap={myBidMap}
                    onBid={openBid}
                    onEditBid={
                      openEditBid
                    }
                    onWithdrawBid={
                      withdrawBid
                    }
                  />
                )
              )}
            </div>
          )}
        </>
      ) : (
        <div className="grid gap-4">
          {myBids.length === 0 ? (
            <Card>
              <EmptyState
                icon={Send}
                title={text(
                  "providerContracts.noBids",
                  "لم تقدم شركتك أي عروض على العقود حتى الآن.",
                  "Your company has not submitted any contract bids yet."
                )}
              />
            </Card>
          ) : (
            myBids.map((bid) => {
              const target =
                getTargetForBid(bid);

              return (
                <MyBidCard
                  key={bid.id}
                  bid={bid}
                  onEdit={() => {
                    if (!target) {
                      toast.error(
                        text(
                          "providerContracts.contractUnavailable",
                          "تعذر العثور على بيانات العقد المرتبط بالعرض.",
                          "The contract linked to this bid is unavailable."
                        )
                      );
                      return;
                    }

                    openEditBid(
                      target.contract,
                      target.lot,
                      bid
                    );
                  }}
                  onWithdraw={
                    withdrawBid
                  }
                />
              );
            })
          )}
        </div>
      )}

      {modalTarget && (
        <BidModal
          target={modalTarget}
          existingBid={editingBid}
          onClose={closeModal}
          onSaved={refreshAfterBid}
        />
      )}
    </div>
  );
}