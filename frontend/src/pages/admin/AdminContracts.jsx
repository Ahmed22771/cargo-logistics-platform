import React, { useEffect, useState } from "react";
import {
  FilePlus2,
  RefreshCw,
  Search,
  MapPin,
  Check,
} from "lucide-react";
import { toast } from "sonner";

import { Btn, Field, Input } from "../../components/ui-kit";
import { MapPicker } from "../../components/MapPicker";
import { useI18n } from "../../i18n";
import api, { apiErr } from "../../lib/api";
import { Table } from "./AdminLayout";

const EMPTY_FORM = {
  title: "",
  description: "",
  contract_number: "",
  customer_id: "",
  customer_name: "",
  competition_mode: "FULL",
  total_units: 1,
  unit_type: "container",
  cargo_type: "",
  vehicle_type: "",
  required_capacity: "",

  pickup_location: null,
  delivery_location: null,

  pickup_date: "",
  pickup_time: "",
  delivery_date: "",
  delivery_time: "",

  fragile: false,
  loading_service: false,
  unloading_service: false,

  target_total_price: "",
  currency: "OMR",
  bidding_deadline: "",
  start_date: "",
  end_date: "",

  special_instructions: "",
  terms: "",
  document_ids: [],
};

export default function AdminContracts() {
  const { t } = useI18n();

  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const statusLabel = (status) =>
    t(`adminContracts.status.${status}`, status || "—");

  const modeLabel = (mode) => {
    if (mode === "SPLIT") {
      return t("adminContracts.modeSplit", mode);
    }

    if (mode === "FULL") {
      return t("adminContracts.modeFull", mode);
    }

    return mode || "—";
  };

  const loadContracts = async () => {
    setLoading(true);

    try {
      const params = statusFilter
        ? { params: { status: statusFilter } }
        : undefined;

      const { data } = await api.get("/admin/contracts", params);
      setContracts(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(
        apiErr(err, t("adminContracts.loadError"))
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContracts();
  }, [statusFilter]);

  const set = (key, value) => {
    setForm((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const resetForm = () => {
    setForm({ ...EMPTY_FORM });
    setShowCreate(false);
  };

  const submitCreate = async (e) => {
    e.preventDefault();

    if (!form.title.trim()) {
      toast.error(
        t("adminContracts.nameRequired")
      );
      return;
    }

    if (
      !Number(form.total_units) ||
      Number(form.total_units) < 1
    ) {
      toast.error(
        t("adminContracts.unitsPositive")
      );
      return;
    }

    if (!form.pickup_location) {
      toast.error(
        t("adminContracts.pickupRequired")
      );
      return;
    }

    if (!form.delivery_location) {
      toast.error(
        t("adminContracts.deliveryRequired")
      );
      return;
    }

    setBusy(true);

    try {
      const payload = {
        ...form,

        total_units: Number(form.total_units),

        target_total_price:
          form.target_total_price === ""
            ? null
            : Number(form.target_total_price),

        customer_id:
          form.customer_id.trim() || null,

        customer_name:
          form.customer_name.trim(),

        contract_number:
          form.contract_number.trim(),
      };

      const { data } = await api.post(
        "/admin/contracts",
        payload
      );

      setContracts((prev) => [
        data,
        ...prev,
      ]);

      toast.success(
        t("adminContracts.createSuccess")
      );

      resetForm();
    } catch (err) {
      toast.error(
        apiErr(
          err,
          t("adminContracts.createError")
        )
      );
    } finally {
      setBusy(false);
    }
  };

  const filteredContracts = contracts.filter(
    (contract) => {
      const q = search.trim().toLowerCase();

      if (!q) return true;

      return (
        String(
          contract.contract_number || ""
        )
          .toLowerCase()
          .includes(q) ||
        String(contract.title || "")
          .toLowerCase()
          .includes(q) ||
        String(contract.customer_name || "")
          .toLowerCase()
          .includes(q)
      );
    }
  );

  const columns = [
    t(
      "adminContracts.contractNumberLabel"
    ),
    t("adminContracts.titleLabel"),
    t("adminContracts.customerLabel"),
    t("adminContracts.typeLabel"),
    t("adminContracts.unitsTable"),
    t("adminContracts.offersLabel"),
    t("adminContracts.statusLabel"),
    t("adminContracts.actionLabel"),
  ];

  const renderRow = (contract) => (
    <tr key={contract.id}>
      <td className="px-4 py-3 font-semibold text-slate-700 whitespace-nowrap">
        {contract.contract_number || "—"}
      </td>

      <td className="px-4 py-3">
        <div className="font-semibold text-slate-800">
          {contract.title || "—"}
        </div>

        {contract.description ? (
          <div className="text-xs text-slate-400 mt-1 line-clamp-2 max-w-xs">
            {contract.description}
          </div>
        ) : null}
      </td>

      <td className="px-4 py-3 text-slate-600">
        {contract.customer_name ||
          t("adminContracts.unlinked")}
      </td>

      <td className="px-4 py-3 text-slate-600">
        {modeLabel(
          contract.competition_mode
        )}
      </td>

      <td className="px-4 py-3 text-slate-600">
        {contract.total_units || 0}{" "}
        {contract.unit_type || ""}
      </td>

      <td className="px-4 py-3 text-slate-600">
        {contract.bid_count || 0}
      </td>

      <td className="px-4 py-3">
        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
          {statusLabel(contract.status)}
        </span>
      </td>

      <td className="px-4 py-3">
        <Btn
          variant="secondary"
          size="sm"
          onClick={() => {
            window.location.href = `/admin/contracts/${contract.id}`;
          }}
        >
          {t("adminContracts.details")}
        </Btn>
      </td>
    </tr>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#16233A]">
            {t("adminContracts.title")}
          </h1>

          <p className="text-sm text-slate-500 mt-1">
            {t(
              "adminContracts.pageSubtitle"
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Btn
            variant="secondary"
            onClick={loadContracts}
            disabled={loading}
            className="inline-flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            {t("adminContracts.refresh")}
          </Btn>

          <Btn
            variant="primary"
            onClick={() =>
              setShowCreate(true)
            }
            className="inline-flex items-center gap-2"
          >
            <FilePlus2 className="w-4 h-4" />
            {t(
              "adminContracts.newContract"
            )}
          </Btn>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Field
            label={t(
              "adminContracts.search"
            )}
          >
            <div className="relative">
              <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />

              <Input
                value={search}
                onChange={(e) =>
                  setSearch(
                    e.target.value
                  )
                }
                placeholder={t(
                  "adminContracts.searchPlaceholder"
                )}
                className="ps-10"
              />
            </div>
          </Field>

          <Field
            label={t(
              "adminContracts.statusLabel"
            )}
          >
            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(
                  e.target.value
                )
              }
              className="w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-[#F1701E]/20"
            >
              <option value="">
                {t(
                  "adminContracts.allStatuses"
                )}
              </option>

              <option value="DRAFT">
                {statusLabel("DRAFT")}
              </option>

              <option value="BIDDING">
                {statusLabel("BIDDING")}
              </option>

              <option value="UNDER_REVIEW">
                {statusLabel(
                  "UNDER_REVIEW"
                )}
              </option>

              <option value="AWARDED">
                {statusLabel("AWARDED")}
              </option>

              <option value="IN_PROGRESS">
                {statusLabel(
                  "IN_PROGRESS"
                )}
              </option>

              <option value="COMPLETED">
                {statusLabel(
                  "COMPLETED"
                )}
              </option>

              <option value="CANCELLED">
                {statusLabel(
                  "CANCELLED"
                )}
              </option>
            </select>
          </Field>

          <div className="flex items-end">
            <div className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-sm w-full">
              <span className="text-slate-500">
                {t(
                  "adminContracts.totalContracts"
                )}
                :
              </span>

              <span className="font-bold text-[#16233A] ms-2">
                {filteredContracts.length}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Contracts Table */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-slate-400">
          {t(
            "adminContracts.loadingList"
          )}
        </div>
      ) : (
        <Table
          columns={columns}
          rows={filteredContracts}
          renderRow={renderRow}
          testId="admin-contracts-table"
          empty={t(
            "adminContracts.emptyList"
          )}
        />
      )}

      {/* Create Contract Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="w-full max-w-5xl max-h-[92vh] overflow-y-auto bg-white rounded-2xl shadow-2xl">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-[#16233A]">
                  {t(
                    "adminContracts.createTitle"
                  )}
                </h2>

                <p className="text-xs text-slate-400 mt-1">
                  {t(
                    "adminContracts.draftNotice"
                  )}
                </p>
              </div>

              <button
                type="button"
                onClick={resetForm}
                className="text-slate-400 hover:text-slate-700 text-sm"
              >
                {t(
                  "adminContracts.close"
                )}
              </button>
            </div>

            <form
              onSubmit={submitCreate}
              className="p-5 space-y-6"
            >
              {/* Basic Data */}
              <div>
                <h3 className="mb-4 text-sm font-bold text-slate-800">
                  {t(
                    "adminContracts.contractData"
                  )}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Field
                    label={t(
                      "adminContracts.contractTitle"
                    )}
                    required
                  >
                    <Input
                      value={form.title}
                      onChange={(e) =>
                        set(
                          "title",
                          e.target.value
                        )
                      }
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.contractNumberLabel"
                    )}
                  >
                    <Input
                      value={
                        form.contract_number
                      }
                      onChange={(e) =>
                        set(
                          "contract_number",
                          e.target.value
                        )
                      }
                      placeholder={t(
                        "adminContracts.contractNumberPlaceholder"
                      )}
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.customerName"
                    )}
                  >
                    <Input
                      value={
                        form.customer_name
                      }
                      onChange={(e) =>
                        set(
                          "customer_name",
                          e.target.value
                        )
                      }
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.customerId"
                    )}
                  >
                    <Input
                      value={
                        form.customer_id
                      }
                      onChange={(e) =>
                        set(
                          "customer_id",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.competitionMethod"
                    )}
                    required
                  >
                    <select
                      value={
                        form.competition_mode
                      }
                      onChange={(e) =>
                        set(
                          "competition_mode",
                          e.target.value
                        )
                      }
                      className="w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm"
                    >
                      <option value="FULL">
                        {t(
                          "adminContracts.modeFull"
                        )}
                      </option>

                      <option value="SPLIT">
                        {t(
                          "adminContracts.modeSplit"
                        )}
                      </option>
                    </select>
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.unitsLabel"
                    )}
                    required
                  >
                    <Input
                      type="number"
                      min="1"
                      value={
                        form.total_units
                      }
                      onChange={(e) =>
                        set(
                          "total_units",
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
                        form.unit_type
                      }
                      onChange={(e) =>
                        set(
                          "unit_type",
                          e.target.value
                        )
                      }
                      placeholder={t(
                        "adminContracts.unitTypePlaceholder"
                      )}
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.shipmentType"
                    )}
                  >
                    <Input
                      value={
                        form.cargo_type
                      }
                      onChange={(e) =>
                        set(
                          "cargo_type",
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
                        form.vehicle_type
                      }
                      onChange={(e) =>
                        set(
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
                        form.required_capacity
                      }
                      onChange={(e) =>
                        set(
                          "required_capacity",
                          e.target.value
                        )
                      }
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.targetContractValue"
                    )}
                  >
                    <Input
                      type="number"
                      min="0"
                      step="0.001"
                      value={
                        form.target_total_price
                      }
                      onChange={(e) =>
                        set(
                          "target_total_price",
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
                        form.currency
                      }
                      onChange={(e) =>
                        set(
                          "currency",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>
                </div>
              </div>

              {/* Pickup / Delivery */}
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <MapPin className="w-5 h-5 text-[#F1701E]" />

                    <h3 className="font-bold text-base text-[#16233A]">
                      {t(
                        "shipment.fromTitle"
                      )}
                    </h3>
                  </div>

                  <MapPicker
                    testIdPrefix="contract-pickup-map"
                    value={
                      form.pickup_location
                    }
                    confirmLabel={t(
                      "shipment.confirmPickup"
                    )}
                    onConfirm={(loc) => {
                      set(
                        "pickup_location",
                        loc
                      );

                      toast.success(
                        t(
                          "shipment.confirmPickup"
                        )
                      );
                    }}
                  />

                  {form.pickup_location && (
                    <div className="text-sm text-emerald-600 font-semibold flex items-center gap-1.5 mt-2">
                      <Check className="w-4 h-4" />

                      {form.pickup_location
                        .address ||
                        t(
                          "p11.map.unnamed"
                        )}
                    </div>
                  )}
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <MapPin className="w-5 h-5 text-[#16233A]" />

                    <h3 className="font-bold text-base text-[#16233A]">
                      {t(
                        "shipment.toTitle"
                      )}
                    </h3>
                  </div>

                  <MapPicker
                    testIdPrefix="contract-delivery-map"
                    value={
                      form.delivery_location
                    }
                    accentConfirm={false}
                    confirmLabel={t(
                      "shipment.confirmDelivery"
                    )}
                    onConfirm={(loc) => {
                      set(
                        "delivery_location",
                        loc
                      );

                      toast.success(
                        t(
                          "shipment.confirmDelivery"
                        )
                      );
                    }}
                  />

                  {form.delivery_location && (
                    <div className="text-sm text-emerald-600 font-semibold flex items-center gap-1.5 mt-2">
                      <Check className="w-4 h-4" />

                      {form.delivery_location
                        .address ||
                        t(
                          "p11.map.unnamed"
                        )}
                    </div>
                  )}
                </div>
              </div>

              {/* Dates */}
              <div>
                <h3 className="mb-4 text-sm font-bold text-slate-800">
                  {t(
                    "adminContracts.executionDates"
                  )}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                  <Field
                    label={t(
                      "adminContracts.pickupDate"
                    )}
                  >
                    <Input
                      type="date"
                      value={
                        form.pickup_date
                      }
                      onChange={(e) =>
                        set(
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
                        form.pickup_time
                      }
                      onChange={(e) =>
                        set(
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
                        form.delivery_date
                      }
                      onChange={(e) =>
                        set(
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
                        form.delivery_time
                      }
                      onChange={(e) =>
                        set(
                          "delivery_time",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.executionStart"
                    )}
                  >
                    <Input
                      type="date"
                      value={
                        form.start_date
                      }
                      onChange={(e) =>
                        set(
                          "start_date",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.executionEnd"
                    )}
                  >
                    <Input
                      type="date"
                      value={
                        form.end_date
                      }
                      onChange={(e) =>
                        set(
                          "end_date",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>

                  <Field
                    label={t(
                      "adminContracts.biddingDeadlineLabel"
                    )}
                  >
                    <Input
                      type="datetime-local"
                      value={
                        form.bidding_deadline
                      }
                      onChange={(e) =>
                        set(
                          "bidding_deadline",
                          e.target.value
                        )
                      }
                      className="force-ltr"
                    />
                  </Field>
                </div>
              </div>

              {/* Text Details */}
              <Field
                label={t(
                  "adminContracts.contractDescription"
                )}
              >
                <textarea
                  value={
                    form.description
                  }
                  onChange={(e) =>
                    set(
                      "description",
                      e.target.value
                    )
                  }
                  rows={4}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#F1701E]/20"
                />
              </Field>

              <Field
                label={t(
                  "adminContracts.specialInstructions"
                )}
              >
                <textarea
                  value={
                    form.special_instructions
                  }
                  onChange={(e) =>
                    set(
                      "special_instructions",
                      e.target.value
                    )
                  }
                  rows={3}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#F1701E]/20"
                />
              </Field>

              <Field
                label={t(
                  "adminContracts.contractTerms"
                )}
              >
                <textarea
                  value={form.terms}
                  onChange={(e) =>
                    set(
                      "terms",
                      e.target.value
                    )
                  }
                  rows={4}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#F1701E]/20"
                />
              </Field>

              {/* Actions */}
              <div className="flex justify-end gap-2 pt-4 border-t border-slate-200">
                <Btn
                  type="button"
                  variant="secondary"
                  onClick={resetForm}
                  disabled={busy}
                >
                  {t(
                    "adminContracts.cancel"
                  )}
                </Btn>

                <Btn
                  type="submit"
                  variant="primary"
                  disabled={busy}
                >
                  {busy
                    ? t(
                        "adminContracts.saving"
                      )
                    : t(
                        "adminContracts.saveDraft"
                      )}
                </Btn>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}