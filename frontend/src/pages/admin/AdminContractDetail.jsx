import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock3,
  FileText,
  Building2,
  Package,
  Gavel,
  Plus,
  Pencil,
  Trash2,
  Save,
} from "lucide-react";
import { toast } from "sonner";
import { useParams } from "react-router-dom";

import API, { apiErr } from "../../lib/api";
import { useI18n } from "../../i18n";
import { Btn, Field, Input } from "../../components/ui-kit";

function InfoItem({ label, value, icon: Icon }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-500">
        {Icon && <Icon size={15} />}
        <span>{label}</span>
      </div>

      <div className="break-words text-sm font-semibold text-slate-900">
        {value ?? "-"}
      </div>
    </div>
  );
}

function StatusBadge({ status, label }) {
  const styles = {
    DRAFT: "bg-slate-100 text-slate-700",
    PUBLISHED: "bg-blue-100 text-blue-700",
    BIDDING: "bg-amber-100 text-amber-700",
    UNDER_REVIEW: "bg-purple-100 text-purple-700",
    AWARDED: "bg-emerald-100 text-emerald-700",
    IN_PROGRESS: "bg-cyan-100 text-cyan-700",
    COMPLETED: "bg-green-100 text-green-700",
    CANCELLED: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
        styles[status] || "bg-gray-100 text-gray-700"
      }`}
    >
      {label || status || "-"}
    </span>
  );
}

function BidStatusBadge({ status, label }) {
  const styles = {
    DRAFT: "bg-slate-100 text-slate-700",
    SUBMITTED: "bg-blue-100 text-blue-700",
    UNDER_REVIEW: "bg-purple-100 text-purple-700",
    SHORTLISTED: "bg-amber-100 text-amber-700",
    AWARDED: "bg-emerald-100 text-emerald-700",
    REJECTED: "bg-red-100 text-red-700",
    WITHDRAWN: "bg-gray-100 text-gray-700",
    EXPIRED: "bg-gray-100 text-gray-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
        styles[status] || "bg-gray-100 text-gray-700"
      }`}
    >
      {label || status || "-"}
    </span>
  );
}

function formatDate(value, lang) {
  if (!value) return "-";

  try {
    return new Date(value).toLocaleString(
      lang === "ar" ? "ar" : "en"
    );
  } catch {
    return value;
  }
}

function formatMoney(value, currency, lang) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return String(value);
  }

  return `${number.toLocaleString(
    lang === "ar" ? "ar" : "en-US",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }
  )} ${currency}`;
}

const EMPTY_LOT_FORM = {
  name: "",
  lot_number: "",
  quantity: 1,
  unit_type: "",
  description: "",
  vehicle_type: "",
  required_capacity: "",
  pickup_date: "",
  pickup_time: "",
  delivery_date: "",
  delivery_time: "",
  target_price: "",
  currency: "OMR",
};

function AwardModal({
  contract,
  bid,
  lot,
  remainingQuantity,
  currency,
  onClose,
  onCompleted,
}) {
  const { t, lang, dir } = useI18n();
  const [quantity, setQuantity] = useState(
    String(
      Math.min(
        Number(bid?.quantity_offered || 0),
        Number(remainingQuantity || bid?.quantity_offered || 0)
      ) || 1
    )
  );
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const offeredQuantity = Number(bid?.quantity_offered || 0);
  const maxQuantity = Math.max(
    0,
    Math.min(offeredQuantity, Number(remainingQuantity || 0))
  );
  const unitPrice = Number(bid?.unit_price || 0);
  const previewTotal =
    Number(quantity) > 0 ? Number(quantity) * unitPrice : 0;

  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;

    const awardedQuantity = Number.parseInt(quantity, 10);

    if (!Number.isInteger(awardedQuantity) || awardedQuantity <= 0) {
      toast.error(
        t(
          "adminContracts.invalidAwardQuantity",
          lang === "ar"
            ? "كمية الترسية يجب أن تكون رقمًا صحيحًا أكبر من صفر."
            : "Award quantity must be a positive whole number."
        )
      );
      return;
    }

    if (awardedQuantity > maxQuantity) {
      toast.error(
        t(
          "adminContracts.awardQuantityExceedsAvailable",
          lang === "ar"
            ? "كمية الترسية تتجاوز الكمية المتاحة أو الكمية التي قدمتها الشركة."
            : "Award quantity exceeds the available quantity or the quantity offered by the provider."
        )
      );
      return;
    }

    setBusy(true);

    try {
      await API.post(`/admin/contracts/${contract.id}/awards`, {
        bid_id: bid.id,
        provider_id: bid.provider_id,
        quantity_awarded: awardedQuantity,
        unit_price: unitPrice,
        notes: notes.trim(),
        status: "AWARDED",
      });

      toast.success(
        t(
          "adminContracts.messages.awardSuccess",
          lang === "ar"
            ? "تمت الترسية بنجاح."
            : "Award completed successfully."
        )
      );

      onCompleted?.();
      onClose();
    } catch (err) {
      console.error("Award contract bid error:", err);
      toast.error(
        apiErr(err) ||
          t("adminContracts.operationFailed")
      );
    } finally {
      setBusy(false);
    }
  };

  if (!bid || !contract) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" dir={dir}>
      <div
        className="absolute inset-0 bg-black/40"
        onClick={() => !busy && onClose()}
      />

      <div className="relative w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              {t(
                "adminContracts.awardTitle",
                lang === "ar" ? "ترسية العرض" : "Award Bid"
              )}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              {bid.company_name || bid.provider_name || bid.provider_id || "-"}
            </p>
          </div>

          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
          >
            <XCircle size={20} />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-5 p-5">
          <div className="grid gap-3 md:grid-cols-2">
            <InfoItem
              label={t(
                "adminContracts.company",
                lang === "ar" ? "شركة النقل" : "Transport Provider"
              )}
              value={bid.company_name || bid.provider_name || bid.provider_id || "-"}
              icon={Building2}
            />

            <InfoItem
              label={t(
                "adminContracts.lot",
                lang === "ar" ? "المنافسة الجزئية" : "Lot"
              )}
              value={lot?.name || lot?.lot_number || t("adminContracts.fullContract")}
              icon={Package}
            />

            <InfoItem
              label={t(
                "adminContracts.bidQuantity",
                lang === "ar" ? "الكمية المقدمة" : "Bid Quantity"
              )}
              value={Number(bid.quantity_offered || 0).toLocaleString(
                lang === "ar" ? "ar" : "en-US"
              )}
              icon={Package}
            />

            <InfoItem
              label={t(
                "adminContracts.unitPrice",
                lang === "ar" ? "سعر الوحدة" : "Unit Price"
              )}
              value={formatMoney(bid.unit_price, currency, lang)}
            />

            <InfoItem
              label={t(
                "adminContracts.remainingAwardQuantity",
                lang === "ar" ? "الكمية المتاحة للترسية" : "Available for Award"
              )}
              value={Number(remainingQuantity || 0).toLocaleString(
                lang === "ar" ? "ar" : "en-US"
              )}
              icon={CheckCircle2}
            />

            <InfoItem
              label={t(
                "adminContracts.bidTotal",
                lang === "ar" ? "إجمالي العرض" : "Bid Total"
              )}
              value={formatMoney(bid.total_price, currency, lang)}
            />
          </div>

          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <Field
              label={t(
                "adminContracts.quantityAwarded",
                lang === "ar" ? "الكمية المراد ترسيتها" : "Quantity to Award"
              )}
              required
            >
              <Input
                type="number"
                min="1"
                max={maxQuantity > 0 ? maxQuantity : undefined}
                step="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="force-ltr"
              />
            </Field>

            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <InfoItem
                label={t(
                  "adminContracts.awardTotal",
                  lang === "ar" ? "إجمالي الترسية" : "Award Total"
                )}
                value={formatMoney(previewTotal, currency, lang)}
              />

              <InfoItem
                label={t(
                  "adminContracts.providerUnitPrice",
                  lang === "ar" ? "سعر الوحدة المعتمد" : "Award Unit Price"
                )}
                value={formatMoney(unitPrice, currency, lang)}
              />
            </div>
          </div>

          <Field
            label={t(
              "adminContracts.awardNotes",
              lang === "ar" ? "ملاحظات الترسية" : "Award Notes"
            )}
          >
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#F1701E]/20"
              placeholder={t(
                "adminContracts.awardNotesPlaceholder",
                lang === "ar"
                  ? "اكتب أي ملاحظات مرتبطة بقرار الترسية..."
                  : "Add any notes related to this award decision..."
              )}
            />
          </Field>

          <div className="flex flex-col-reverse gap-2 border-t border-slate-200 pt-4 sm:flex-row sm:justify-end">
            <Btn
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={busy}
            >
              {t("adminContracts.cancel")}
            </Btn>

            <Btn
              type="submit"
              variant="primary"
              disabled={busy || maxQuantity <= 0}
              className="inline-flex items-center gap-2"
            >
              {busy ? (
                <RefreshCw size={16} className="animate-spin" />
              ) : (
                <CheckCircle2 size={16} />
              )}
              {t(
                "adminContracts.award",
                lang === "ar" ? "تنفيذ الترسية" : "Complete Award"
              )}
            </Btn>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminContractDetail() {
  const { contractId } = useParams();
  const { t, lang, dir } = useI18n();

  const [contract, setContract] = useState(null);
  const [lots, setLots] = useState([]);
  const [bids, setBids] = useState([]);
  const [awards, setAwards] = useState([]);

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [showLotForm, setShowLotForm] = useState(false);
  const [editingLotId, setEditingLotId] = useState(null);
  const [lotBusy, setLotBusy] = useState(false);
  const [lotForm, setLotForm] = useState(EMPTY_LOT_FORM);

  const [awardTarget, setAwardTarget] = useState(null);

  const statusText = (status) =>
    t(`adminContracts.status.${status}`, status || "-");

  const bidStatusText = (status) =>
    t(`adminContracts.bidStatus.${status}`, status || "-");

  const modeValue =
    contract?.competition_mode || contract?.mode || "FULL";

  const modeText = (mode) => {
    if (mode === "SPLIT") {
      return t("adminContracts.modeSplit", mode);
    }

    if (mode === "FULL") {
      return t("adminContracts.modeFull", mode);
    }

    return mode || "-";
  };

  const isSplitContract = modeValue === "SPLIT";

  const totalUnits = Number(
    contract?.total_units ??
      contract?.quantity ??
      contract?.total_quantity ??
      0
  );

  const totalLotQuantity = useMemo(
    () =>
      lots.reduce(
        (sum, lot) =>
          sum + Number(lot.quantity || 0),
        0
      ),
    [lots]
  );

  const remainingLotQuantity = totalUnits - totalLotQuantity;

  const lotsMatchContract =
    !isSplitContract ||
    totalLotQuantity === totalUnits;

  const canEditLots = ["DRAFT", "UNDER_REVIEW"].includes(
    contract?.status
  );

  const loadContract = async () => {
    if (!contractId) {
      setError(t("adminContracts.loadError"));
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await API.get(
        `/admin/contracts/${contractId}`
      );

      const data = response?.data ?? response;
      const contractData = data?.contract || data;

      setContract(contractData);

      if (Array.isArray(data?.bids)) {
        setBids(data.bids);
      } else if (Array.isArray(data?.contract_bids)) {
        setBids(data.contract_bids);
      } else if (Array.isArray(contractData?.bids)) {
        setBids(contractData.bids);
      } else {
        setBids([]);
      }

      if (Array.isArray(data?.awards)) {
        setAwards(data.awards);
      } else if (Array.isArray(data?.contract_awards)) {
        setAwards(data.contract_awards);
      } else if (Array.isArray(contractData?.awards)) {
        setAwards(contractData.awards);
      } else {
        setAwards([]);
      }
    } catch (err) {
      console.error("Load contract error:", err);

      const message =
        apiErr(err) ||
        t("adminContracts.loadError");

      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const loadLots = async () => {
    if (!contractId) return;

    try {
      const response = await API.get(
        `/admin/contracts/${contractId}/lots`
      );

      const data = response?.data ?? response;

      setLots(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Load lots error:", err);

      toast.error(
        apiErr(err) ||
          t("adminContracts.lotsLoadError")
      );

      setLots([]);
    }
  };

  const loadAll = async () => {
    await Promise.all([
      loadContract(),
      loadLots(),
    ]);
  };

  useEffect(() => {
    loadAll();
  }, [contractId]);

  const runAction = async (
    request,
    successMessage
  ) => {
    if (busy) return;

    setBusy(true);

    try {
      await request();

      toast.success(successMessage);

      await loadAll();
    } catch (err) {
      console.error(
        "Contract action error:",
        err
      );

      toast.error(
        apiErr(err) ||
          t("adminContracts.operationFailed")
      );
    } finally {
      setBusy(false);
    }
  };

  const publishContract = () => {
    if (isSplitContract && !lotsMatchContract) {
      toast.error(
        t("adminContracts.quantityMustMatch")
      );
      return;
    }

    runAction(
      () =>
        API.post(
          `/admin/contracts/${contractId}/publish`
        ),
      t(
        "adminContracts.messages.publishSuccess"
      )
    );
  };

  const reviewContract = () =>
    runAction(
      () =>
        API.post(
          `/admin/contracts/${contractId}/review`
        ),
      t(
        "adminContracts.messages.reviewSuccess"
      )
    );

  const cancelContract = () =>
    runAction(
      () =>
        API.post(
          `/admin/contracts/${contractId}/cancel`
        ),
      t(
        "adminContracts.messages.cancelSuccess"
      )
    );

  const reviewBid = (bidId) =>
    runAction(
      () =>
        API.post(
          `/admin/contracts/${contractId}/bids/${bidId}/review`
        ),
      t(
        "adminContracts.messages.bidReviewSuccess"
      )
    );

  const shortlistBid = (bidId) =>
    runAction(
      () =>
        API.post(
          `/admin/contracts/${contractId}/bids/${bidId}/shortlist`
        ),
      t(
        "adminContracts.messages.shortlistSuccess"
      )
    );

  const rejectBid = (bidId) =>
    runAction(
      () =>
        API.post(
          `/admin/contracts/${contractId}/bids/${bidId}/reject`
        ),
      t(
        "adminContracts.messages.rejectSuccess"
      )
    );

  const setLot = (key, value) => {
    setLotForm((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const resetLotForm = () => {
    setLotForm({
      ...EMPTY_LOT_FORM,
      unit_type:
        contract?.unit_type || "",
      vehicle_type:
        contract?.vehicle_type || "",
      required_capacity:
        contract?.required_capacity || "",
      currency:
        contract?.currency || "OMR",
    });

    setEditingLotId(null);
    setShowLotForm(false);
  };

  const openCreateLot = () => {
    setLotForm({
      ...EMPTY_LOT_FORM,
      unit_type:
        contract?.unit_type || "",
      vehicle_type:
        contract?.vehicle_type || "",
      required_capacity:
        contract?.required_capacity || "",
      currency:
        contract?.currency || "OMR",
      quantity:
        remainingLotQuantity > 0
          ? remainingLotQuantity
          : 1,
    });

    setEditingLotId(null);
    setShowLotForm(true);
  };

  const openEditLot = (lot) => {
    setEditingLotId(lot.id);

    setLotForm({
      name: lot.name || "",
      lot_number: lot.lot_number || "",
      quantity: lot.quantity || 1,
      unit_type:
        lot.unit_type ||
        contract?.unit_type ||
        "",
      description: lot.description || "",
      vehicle_type:
        lot.vehicle_type ||
        contract?.vehicle_type ||
        "",
      required_capacity:
        lot.required_capacity ||
        contract?.required_capacity ||
        "",
      pickup_date: lot.pickup_date || "",
      pickup_time: lot.pickup_time || "",
      delivery_date: lot.delivery_date || "",
      delivery_time: lot.delivery_time || "",
      target_price:
        lot.target_price === null ||
        lot.target_price === undefined
          ? ""
          : lot.target_price,
      currency:
        lot.currency ||
        contract?.currency ||
        "OMR",
    });

    setShowLotForm(true);
  };

  const submitLot = async (event) => {
    event.preventDefault();

    if (!lotForm.name.trim()) {
      toast.error(
        t("adminContracts.lotNameRequired")
      );
      return;
    }

    const quantity = Number(lotForm.quantity);

    if (!quantity || quantity < 1) {
      toast.error(
        t("adminContracts.unitsPositive")
      );
      return;
    }

    if (!editingLotId) {
      const remaining =
        totalUnits - totalLotQuantity;

      if (quantity > remaining) {
        toast.error(
          t(
            "adminContracts.lotQuantityExceedsRemaining"
          )
        );
        return;
      }
    } else {
      const currentLot = lots.find(
        (lot) => lot.id === editingLotId
      );

      const otherQuantity =
        totalLotQuantity -
        Number(currentLot?.quantity || 0);

      if (
        otherQuantity + quantity >
        totalUnits
      ) {
        toast.error(
          t(
            "adminContracts.lotQuantityExceedsRemaining"
          )
        );
        return;
      }
    }

    setLotBusy(true);

    try {
      const payload = {
        name: lotForm.name.trim(),
        lot_number:
          lotForm.lot_number.trim(),
        quantity,
        unit_type:
          lotForm.unit_type.trim(),
        description:
          lotForm.description.trim(),
        vehicle_type:
          lotForm.vehicle_type.trim(),
        required_capacity:
          lotForm.required_capacity.trim(),
        pickup_date:
          lotForm.pickup_date,
        pickup_time:
          lotForm.pickup_time,
        delivery_date:
          lotForm.delivery_date,
        delivery_time:
          lotForm.delivery_time,
        target_price:
          lotForm.target_price === ""
            ? null
            : Number(lotForm.target_price),
        currency:
          lotForm.currency.trim() ||
          contract?.currency ||
          "OMR",
      };

      if (editingLotId) {
        await API.put(
          `/admin/contracts/${contractId}/lots/${editingLotId}`,
          payload
        );

        toast.success(
          t("adminContracts.lotUpdated")
        );
      } else {
        await API.post(
          `/admin/contracts/${contractId}/lots`,
          payload
        );

        toast.success(
          t("adminContracts.lotCreated")
        );
      }

      resetLotForm();
      await loadLots();
    } catch (err) {
      console.error(
        "Save contract lot error:",
        err
      );

      toast.error(
        apiErr(err) ||
          t("adminContracts.operationFailed")
      );
    } finally {
      setLotBusy(false);
    }
  };

  const deleteLot = async (lot) => {
    if (
      !window.confirm(
        t("adminContracts.confirmDeleteLot")
      )
    ) {
      return;
    }

    setLotBusy(true);

    try {
      await API.delete(
        `/admin/contracts/${contractId}/lots/${lot.id}`
      );

      toast.success(
        t("adminContracts.lotDeleted")
      );

      await loadLots();
    } catch (err) {
      console.error(
        "Delete contract lot error:",
        err
      );

      toast.error(
        apiErr(err) ||
          t("adminContracts.operationFailed")
      );
    } finally {
      setLotBusy(false);
    }
  };

  const getLotForBid = (bid) => {
    if (!bid?.lot_id) return null;
    return (
      lots.find(
        (lot) => lot.id === bid.lot_id
      ) || null
    );
  };

  const getAwardedQuantityForLot = (lotId) => {
    if (!lotId) return 0;

    return awards.reduce(
      (sum, award) =>
        sum +
        (award.lot_id === lotId &&
        ["AWARDED", "ACCEPTED", "IN_PROGRESS"].includes(award.status)
          ? Number(award.quantity_awarded || 0)
          : 0),
      0
    );
  };

  const getAwardedQuantityForContract = () =>
    awards.reduce(
      (sum, award) =>
        sum +
        (!award.lot_id &&
        ["AWARDED", "ACCEPTED", "IN_PROGRESS"].includes(award.status)
          ? Number(award.quantity_awarded || 0)
          : 0),
      0
    );

  const getRemainingQuantityForBid = (bid) => {
    if (isSplitContract) {
      const lot = getLotForBid(bid);

      if (!lot) return 0;

      return Math.max(
        0,
        Number(lot.quantity || 0) -
          getAwardedQuantityForLot(lot.id)
      );
    }

    return Math.max(
      0,
      totalUnits - getAwardedQuantityForContract()
    );
  };

  const openAward = (bid) => {
    const lot = getLotForBid(bid);
    const remaining =
      getRemainingQuantityForBid(bid);

    if (remaining <= 0) {
      toast.error(
        t(
          "adminContracts.noAwardQuantityAvailable",
          lang === "ar"
            ? "لا توجد كمية متاحة للترسية على هذا العرض."
            : "No quantity is available for award on this bid."
        )
      );
      return;
    }

    setAwardTarget({
      bid,
      lot,
      remaining,
    });
  };

  const closeAward = () => {
    setAwardTarget(null);
  };

  const refreshAfterAward = async () => {
    await loadAll();
  };

  if (loading) {
    return (
      <div
        dir={dir}
        className="flex min-h-[500px] items-center justify-center"
      >
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <RefreshCw
            size={18}
            className="animate-spin"
          />
          {t("adminContracts.loading")}
        </div>
      </div>
    );
  }

  if (error || !contract) {
    return (
      <div
        dir={dir}
        className="rounded-2xl border border-red-200 bg-red-50 p-6"
      >
        <div className="mb-4 flex items-center gap-3">
          <XCircle className="text-red-600" />

          <h2 className="text-lg font-bold text-red-800">
            {t("adminContracts.loadError")}
          </h2>
        </div>

        <p className="mb-5 text-sm text-red-700">
          {error ||
            t("adminContracts.loadError")}
        </p>

        <button
          type="button"
          onClick={loadAll}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          <RefreshCw size={16} />
          {t("adminContracts.retry")}
        </button>
      </div>
    );
  }

  const currency =
    contract.currency || "OMR";

  const targetPrice =
    contract.target_total_price ??
    contract.target_price ??
    contract.total_target_price;

  return (
    <div
      dir={dir}
      className="space-y-6 pb-10"
    >
      {/* Header */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div>
          <button
            type="button"
            onClick={() => {
              window.location.href =
                "/admin/contracts";
            }}
            className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900"
          >
            <ArrowRight size={16} />
            {t("adminContracts.back")}
          </button>

          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">
              {contract.title ||
                contract.name ||
                t("adminContracts.title")}
            </h1>

            <StatusBadge
              status={contract.status}
              label={statusText(
                contract.status
              )}
            />
          </div>

          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-500">
            <span>
              {t(
                "adminContracts.contractNumber"
              )}
              :
              <strong className="mx-1 text-slate-800">
                {contract.contract_number ||
                  "-"}
              </strong>
            </span>

            <span>
              {t("adminContracts.mode")}:
              <strong className="mx-1 text-slate-800">
                {modeText(modeValue)}
              </strong>
            </span>

            <span>
              {t("adminContracts.createdAt")}:
              <strong className="mx-1 text-slate-800">
                {formatDate(
                  contract.created_at,
                  lang
                )}
              </strong>
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {contract.status === "DRAFT" && (
            <button
              type="button"
              disabled={
                busy ||
                (isSplitContract &&
                  !lotsMatchContract)
              }
              onClick={publishContract}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              title={
                isSplitContract &&
                !lotsMatchContract
                  ? t(
                      "adminContracts.quantityMustMatch"
                    )
                  : undefined
              }
            >
              <CheckCircle2 size={16} />
              {t("adminContracts.publish")}
            </button>
          )}

          {contract.status === "PUBLISHED" && (
            <button
              type="button"
              disabled={busy}
              onClick={reviewContract}
              className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 disabled:opacity-50"
            >
              <Clock3 size={16} />
              {t("adminContracts.startReview")}
            </button>
          )}
          {[
            "DRAFT",
            "PUBLISHED",
            "BIDDING",
            "UNDER_REVIEW",
          ].includes(contract.status) && (
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                if (
                  window.confirm(
                    t(
                      "adminContracts.confirmCancel"
                    )
                  )
                ) {
                  cancelContract();
                }
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              <XCircle size={16} />
              {t("adminContracts.cancel")}
            </button>
          )}

          <button
            type="button"
            onClick={loadAll}
            disabled={loading || lotBusy || busy}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={16} />
            {t("adminContracts.refresh")}
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <InfoItem
          label={t(
            "adminContracts.customer"
          )}
          value={
            contract.customer_name ||
            contract.company_name ||
            contract.customer_id ||
            "-"
          }
          icon={Building2}
        />

        <InfoItem
          label={t(
            "adminContracts.totalUnits"
          )}
          value={Number(
            totalUnits
          ).toLocaleString(
            lang === "ar"
              ? "ar"
              : "en-US"
          )}
          icon={Package}
        />

        <InfoItem
          label={t(
            "adminContracts.totalBids"
          )}
          value={`${bids.length} ${t(
            "adminContracts.resultOffer"
          )}`}
          icon={Gavel}
        />

        <InfoItem
          label={t(
            "adminContracts.targetPrice"
          )}
          value={formatMoney(
            targetPrice,
            currency,
            lang
          )}
        />
      </div>

      {/* Contract Data */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-slate-900">
            {t(
              "adminContracts.contractData"
            )}
          </h2>
        </div>

        <div className="grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-3">
          <InfoItem
            label={t(
              "adminContracts.contractNumber"
            )}
            value={
              contract.contract_number
            }
          />

          <InfoItem
            label={t("adminContracts.mode")}
            value={modeText(modeValue)}
          />

          <InfoItem
            label={t(
              "adminContracts.unitType"
            )}
            value={contract.unit_type}
          />

          <InfoItem
            label={t(
              "adminContracts.cargoType"
            )}
            value={contract.cargo_type}
          />

          <InfoItem
            label={t(
              "adminContracts.vehicleType"
            )}
            value={contract.vehicle_type}
          />

          <InfoItem
            label={t(
              "adminContracts.currency"
            )}
            value={currency}
          />

          <InfoItem
            label={t(
              "adminContracts.quantity"
            )}
            value={Number(
              totalUnits
            ).toLocaleString(
              lang === "ar"
                ? "ar"
                : "en-US"
            )}
          />

          <InfoItem
            label={t(
              "adminContracts.biddingDeadline"
            )}
            value={formatDate(
              contract.bidding_deadline ||
                contract.bid_deadline,
              lang
            )}
          />

          <InfoItem
            label={t(
              "adminContracts.startDate"
            )}
            value={formatDate(
              contract.start_date,
              lang
            )}
          />

          <InfoItem
            label={t(
              "adminContracts.endDate"
            )}
            value={formatDate(
              contract.end_date,
              lang
            )}
          />
        </div>

        {(contract.description ||
          contract.special_instructions ||
          contract.terms) && (
          <div className="grid gap-4 border-t border-slate-200 p-5 md:grid-cols-2">
            {contract.description && (
              <div className="rounded-xl bg-slate-50 p-4">
                <div className="mb-2 text-sm font-bold text-slate-800">
                  {t(
                    "adminContracts.description"
                  )}
                </div>

                <p className="whitespace-pre-wrap text-sm leading-7 text-slate-600">
                  {contract.description}
                </p>
              </div>
            )}

            {contract.special_instructions && (
              <div className="rounded-xl bg-slate-50 p-4">
                <div className="mb-2 text-sm font-bold text-slate-800">
                  {t(
                    "adminContracts.instructions"
                  )}
                </div>

                <p className="whitespace-pre-wrap text-sm leading-7 text-slate-600">
                  {
                    contract.special_instructions
                  }
                </p>
              </div>
            )}

            {contract.terms && (
              <div className="rounded-xl bg-slate-50 p-4 md:col-span-2">
                <div className="mb-2 text-sm font-bold text-slate-800">
                  {t(
                    "adminContracts.terms"
                  )}
                </div>

                <p className="whitespace-pre-wrap text-sm leading-7 text-slate-600">
                  {contract.terms}
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Lots */}
      {isSplitContract && (
        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-4 border-b border-slate-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                {t("adminContracts.lots")}
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                {t(
                  "adminContracts.lotManagementHint"
                )}
              </p>
            </div>

            {canEditLots && (
              <Btn
                variant="primary"
                onClick={openCreateLot}
                disabled={
                  lotBusy ||
                  remainingLotQuantity <= 0
                }
                className="inline-flex items-center gap-2"
              >
                <Plus size={16} />
                {t(
                  "adminContracts.addLot"
                )}
              </Btn>
            )}
          </div>

          {/* Quantity status */}
          <div className="grid gap-3 border-b border-slate-200 p-5 md:grid-cols-3">
            <div className="rounded-xl bg-slate-50 p-4">
              <div className="text-xs text-slate-500">
                {t(
                  "adminContracts.totalUnits"
                )}
              </div>

              <div className="mt-1 text-lg font-bold text-slate-900">
                {totalUnits.toLocaleString(
                  lang === "ar"
                    ? "ar"
                    : "en-US"
                )}
              </div>
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <div className="text-xs text-slate-500">
                {t(
                  "adminContracts.totalLotQuantity"
                )}
              </div>

              <div className="mt-1 text-lg font-bold text-slate-900">
                {totalLotQuantity.toLocaleString(
                  lang === "ar"
                    ? "ar"
                    : "en-US"
                )}
              </div>
            </div>

            <div
              className={`rounded-xl p-4 ${
                remainingLotQuantity === 0
                  ? "bg-emerald-50"
                  : remainingLotQuantity > 0
                    ? "bg-amber-50"
                    : "bg-red-50"
              }`}
            >
              <div className="text-xs text-slate-500">
                {t(
                  "adminContracts.remainingQuantity"
                )}
              </div>

              <div
                className={`mt-1 text-lg font-bold ${
                  remainingLotQuantity === 0
                    ? "text-emerald-700"
                    : remainingLotQuantity > 0
                      ? "text-amber-700"
                      : "text-red-700"
                }`}
              >
                {remainingLotQuantity.toLocaleString(
                  lang === "ar"
                    ? "ar"
                    : "en-US"
                )}
              </div>
            </div>
          </div>

          {/* Validation message */}
          {totalLotQuantity !== totalUnits && (
            <div
              className={`mx-5 mt-5 rounded-xl border p-4 text-sm ${
                totalLotQuantity > totalUnits
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-amber-200 bg-amber-50 text-amber-700"
              }`}
            >
              {totalLotQuantity > totalUnits
                ? t(
                    "adminContracts.lotQuantityOverContract"
                  )
                : t(
                    "adminContracts.lotQuantityBelowContract"
                  )}
            </div>
          )}

          {totalLotQuantity === totalUnits &&
            totalUnits > 0 && (
              <div className="mx-5 mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
                {t(
                  "adminContracts.lotQuantityComplete"
                )}
              </div>
            )}

          {/* Lot Form */}
          {showLotForm && (
            <div className="m-5 rounded-2xl border border-slate-200 bg-slate-50">
              <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                <div>
                  <h3 className="font-bold text-slate-900">
                    {editingLotId
                      ? t(
                          "adminContracts.editLot"
                        )
                      : t(
                          "adminContracts.addLot"
                        )}
                  </h3>
                </div>

                <button
                  type="button"
                  onClick={resetLotForm}
                  className="text-sm text-slate-400 hover:text-slate-700"
                >
                  {t(
                    "adminContracts.close"
                  )}
                </button>
              </div>

              <form
                onSubmit={submitLot}
                className="space-y-5 p-5"
              >
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  <Field
                    label={t(
                      "adminContracts.lotName"
                    )}
                    required
                  >
                    <Input
                      value={lotForm.name}
                      onChange={(e) =>
                        setLot(
                          "name",
                          e.target.value
                        )
                      }
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.lotNumber"
                    )}
                  >
                    <Input
                      value={
                        lotForm.lot_number
                      }
                      onChange={(e) =>
                        setLot(
                          "lot_number",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.quantity"
                    )}
                    required
                  >
                    <Input
                      type="number"
                      min="1"
                      value={lotForm.quantity}
                      onChange={(e) =>
                        setLot(
                          "quantity",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.unitType"
                    )}
                  >
                    <Input
                      value={
                        lotForm.unit_type
                      }
                      onChange={(e) =>
                        setLot(
                          "unit_type",
                          e.target.value
                        )
                      }
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.vehicleType"
                    )}
                  >
                    <Input
                      value={
                        lotForm.vehicle_type
                      }
                      onChange={(e) =>
                        setLot(
                          "vehicle_type",
                          e.target.value
                        )
                      }
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.requiredCapacity"
                    )}
                  >
                    <Input
                      value={
                        lotForm.required_capacity
                      }
                      onChange={(e) =>
                        setLot(
                          "required_capacity",
                          e.target.value
                        )
                      }
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.pickupDate"
                    )}
                  >
                    <Input
                      type="date"
                      value={
                        lotForm.pickup_date
                      }
                      onChange={(e) =>
                        setLot(
                          "pickup_date",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.pickupTime"
                    )}
                  >
                    <Input
                      type="time"
                      value={
                        lotForm.pickup_time
                      }
                      onChange={(e) =>
                        setLot(
                          "pickup_time",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.deliveryDate"
                    )}
                  >
                    <Input
                      type="date"
                      value={
                        lotForm.delivery_date
                      }
                      onChange={(e) =>
                        setLot(
                          "delivery_date",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.deliveryTime"
                    )}
                  >
                    <Input
                      type="time"
                      value={
                        lotForm.delivery_time
                      }
                      onChange={(e) =>
                        setLot(
                          "delivery_time",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.targetPrice"
                    )}
                  >
                    <Input
                      type="number"
                      min="0"
                      step="0.001"
                      value={
                        lotForm.target_price
                      }
                      onChange={(e) =>
                        setLot(
                          "target_price",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.currency"
                    )}
                  >
                    <Input
                      value={
                        lotForm.currency
                      }
                      onChange={(e) =>
                        setLot(
                          "currency",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>
                </div>

                <Field
                  label={t(
                    "adminContracts.description"
                  )}
                >
                  <textarea
                    value={
                      lotForm.description
                    }
                    onChange={(e) =>
                      setLot(
                        "description",
                        e.target.value
                      )
                    }
                    rows={4}
                    className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#F1701E]/20"
                  />
                </Field>

                <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
                  <Btn
                    type="button"
                    variant="secondary"
                    onClick={resetLotForm}
                    disabled={lotBusy}
                  >
                    {t(
                      "adminContracts.cancel"
                    )}
                  </Btn>

                  <Btn
                    type="submit"
                    variant="primary"
                    disabled={lotBusy}
                    className="inline-flex items-center gap-2"
                  >
                    {lotBusy ? (
                      <RefreshCw
                        size={16}
                        className="animate-spin"
                      />
                    ) : editingLotId ? (
                      <Save size={16} />
                    ) : (
                      <Plus size={16} />
                    )}

                    {editingLotId
                      ? t(
                          "adminContracts.updateLot"
                        )
                      : t(
                          "adminContracts.saveLot"
                        )}
                  </Btn>
                </div>
              </form>
            </div>
          )}

          {/* Lots Table */}
          {lots.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm text-slate-500">
              {t(
                "adminContracts.noLots"
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-start text-sm">
                <thead className="bg-slate-50 text-xs text-slate-500">
                  <tr>
                    <th className="px-5 py-3">
                      {t(
                        "adminContracts.lotNumber"
                      )}
                    </th>

                    <th className="px-5 py-3">
                      {t(
                        "adminContracts.lotName"
                      )}
                    </th>

                    <th className="px-5 py-3">
                      {t(
                        "adminContracts.quantity"
                      )}
                    </th>

                    <th className="px-5 py-3">
                      {t(
                        "adminContracts.unitType"
                      )}
                    </th>

                    <th className="px-5 py-3">
                      {t(
                        "adminContracts.vehicleType"
                      )}
                    </th>

                    <th className="px-5 py-3">
                      {t(
                        "adminContracts.targetPrice"
                      )}
                    </th>

                    <th className="px-5 py-3">
                      {t(
                        "adminContracts.statusLabel"
                      )}
                    </th>

                    {canEditLots && (
                      <th className="px-5 py-3">
                        {t(
                          "adminContracts.actionLabel"
                        )}
                      </th>
                    )}
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {lots.map((lot) => (
                    <tr key={lot.id}>
                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {lot.lot_number ||
                          "-"}
                      </td>

                      <td className="px-5 py-4 font-semibold text-slate-800">
                        {lot.name ||
                          "-"}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {Number(
                          lot.quantity || 0
                        ).toLocaleString(
                          lang === "ar"
                            ? "ar"
                            : "en-US"
                        )}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {lot.unit_type ||
                          contract.unit_type ||
                          "-"}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {lot.vehicle_type ||
                          contract.vehicle_type ||
                          "-"}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {formatMoney(
                          lot.target_price,
                          lot.currency ||
                            currency,
                          lang
                        )}
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge
                          status={
                            lot.status
                          }
                          label={statusText(
                            lot.status
                          )}
                        />
                      </td>

                      {canEditLots && (
                        <td className="px-5 py-4">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              disabled={
                                lotBusy
                              }
                              onClick={() =>
                                openEditLot(
                                  lot
                                )
                              }
                              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                            >
                              <Pencil
                                size={14}
                              />
                              {t(
                                "adminContracts.editLot"
                              )}
                            </button>

                            <button
                              type="button"
                              disabled={
                                lotBusy
                              }
                              onClick={() =>
                                deleteLot(
                                  lot
                                )
                              }
                              className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                            >
                              <Trash2
                                size={14}
                              />
                              {t(
                                "adminContracts.deleteLot"
                              )}
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Bids */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-slate-900">
            {t(
              "adminContracts.bids"
            )}
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            {t(
              "adminContracts.bidsAdminOnly",
              lang === "ar"
                ? "عروض الشركات مرئية للإدارة فقط."
                : "Provider bids are visible to administrators only."
            )}
          </p>
        </div>

        {bids.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-slate-500">
            {t(
              "adminContracts.noBids"
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-start text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>
                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.company"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.lot"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.quantity"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.unitPrice"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.totalPrice"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.executionDays"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.statusLabel"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.actionLabel"
                    )}
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {bids.map((bid) => {
                  const lot = getLotForBid(bid);
                  const remaining =
                    getRemainingQuantityForBid(bid);
                  const awardAllowed = [
                    "SUBMITTED",
                    "UNDER_REVIEW",
                    "SHORTLISTED",
                  ].includes(bid.status);

                  return (
                    <tr key={bid.id}>
                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {bid.provider_name ||
                          bid.company_name ||
                          bid.provider_id ||
                          "-"}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {lot?.name ||
                          lot?.lot_number ||
                          bid.lot_name ||
                          bid.lot_number ||
                          bid.lot_id ||
                          t(
                            "adminContracts.fullContract"
                          )}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {Number(
                          bid.quantity_offered ||
                            0
                        ).toLocaleString(
                          lang === "ar"
                            ? "ar"
                            : "en-US"
                        )}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {formatMoney(
                          bid.unit_price,
                          currency,
                          lang
                        )}
                      </td>

                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {formatMoney(
                          bid.total_price,
                          currency,
                          lang
                        )}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {bid.execution_days
                          ? `${bid.execution_days} ${t(
                              "adminContracts.days"
                            )}`
                          : "-"}
                      </td>

                      <td className="px-5 py-4">
                        <BidStatusBadge
                          status={
                            bid.status
                          }
                          label={bidStatusText(
                            bid.status
                          )}
                        />
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex flex-wrap gap-2">
                          {bid.status ===
                            "SUBMITTED" && (
                            <button
                              type="button"
                              disabled={
                                busy
                              }
                              onClick={() =>
                                reviewBid(
                                  bid.id
                                )
                              }
                              className="rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-purple-700 disabled:opacity-50"
                            >
                              {t(
                                "adminContracts.review"
                              )}
                            </button>
                          )}

                          {(bid.status ===
                            "SUBMITTED" ||
                            bid.status ===
                              "UNDER_REVIEW") && (
                            <button
                              type="button"
                              disabled={
                                busy
                              }
                              onClick={() =>
                                shortlistBid(
                                  bid.id
                                )
                              }
                              className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50"
                            >
                              {t(
                                "adminContracts.shortlist"
                              )}
                            </button>
                          )}

                          {(bid.status ===
                            "SUBMITTED" ||
                            bid.status ===
                              "UNDER_REVIEW" ||
                            bid.status ===
                              "SHORTLISTED") && (
                            <button
                              type="button"
                              disabled={
                                busy
                              }
                              onClick={() =>
                                rejectBid(
                                  bid.id
                                )
                              }
                              className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                            >
                              {t(
                                "adminContracts.reject"
                              )}
                            </button>
                          )}

                          {awardAllowed &&
                            remaining > 0 && (
                            <button
                              type="button"
                              disabled={
                                busy ||
                                !awardAllowed
                              }
                              onClick={() =>
                                openAward(
                                  bid
                                )
                              }
                              className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              <CheckCircle2
                                size={14}
                              />
                              {t(
                                "adminContracts.award",
                                lang === "ar"
                                  ? "ترسية"
                                  : "Award"
                              )}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Awards */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-slate-900">
            {t(
              "adminContracts.awards"
            )}
          </h2>
        </div>

        {awards.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-slate-500">
            {t(
              "adminContracts.noAwards"
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-start text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>
                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.company"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.lot"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.quantity"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.awardValue"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.statusLabel"
                    )}
                  </th>

                  <th className="px-5 py-3">
                    {t(
                      "adminContracts.date"
                    )}
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {awards.map((award) => {
                  const lot =
                    (award.lot_id
                      ? lots.find(
                          (item) =>
                            item.id === award.lot_id
                        )
                      : null) || null;

                  return (
                    <tr key={award.id}>
                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {award.provider_name ||
                          award.company_name ||
                          award.provider_id ||
                          "-"}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {lot?.name ||
                          lot?.lot_number ||
                          award.lot_name ||
                          award.lot_number ||
                          award.lot_id ||
                          t(
                            "adminContracts.fullContract"
                          )}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {Number(
                          award.quantity_awarded ||
                            0
                        ).toLocaleString(
                          lang === "ar"
                            ? "ar"
                            : "en-US"
                        )}
                      </td>

                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {formatMoney(
                          award.total_price ||
                            award.award_price,
                          award.currency ||
                            currency,
                          lang
                        )}
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge
                          status={
                            award.status
                          }
                          label={statusText(
                            award.status
                          )}
                        />
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {formatDate(
                          award.created_at,
                          lang
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Documents */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <FileText size={19} />
            {t(
              "adminContracts.documents"
            )}
          </h2>
        </div>

        <div className="p-5">
          {Array.isArray(
            contract.document_ids
          ) &&
          contract.document_ids.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {contract.document_ids.map(
                (documentId) => (
                  <div
                    key={documentId}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div className="text-xs text-slate-500">
                      {t(
                        "adminContracts.documentId"
                      )}
                    </div>

                    <div className="mt-1 break-all text-sm font-semibold text-slate-800">
                      {documentId}
                    </div>
                  </div>
                )
              )}
            </div>
          ) : (
            <div className="text-sm text-slate-500">
              {t(
                "adminContracts.noDocuments"
              )}
            </div>
          )}
        </div>
      </section>

      {awardTarget && (
        <AwardModal
          contract={contract}
          bid={awardTarget.bid}
          lot={awardTarget.lot}
          remainingQuantity={awardTarget.remaining}
          currency={
            awardTarget.lot?.currency ||
            currency
          }
          onClose={closeAward}
          onCompleted={refreshAfterAward}
        />
      )}
    </div>
  );
}
