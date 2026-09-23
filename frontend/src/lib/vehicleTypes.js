// Canonical vehicle types for CARGO. The `value` is the stable business key
// stored in the DB (English snake_case); labels are resolved via i18n only, so
// Arabic text never drives business logic. Extend by adding entries here.
export const VEHICLE_TYPES = [
  { value: "pickup", labelKey: "shipment.vehiclePickup" },
  { value: "car", labelKey: "shipment.vehicleCar" },
  { value: "box_truck", labelKey: "shipment.vehicleBoxTruck" },
  { value: "flatbed", labelKey: "shipment.vehicleFlatbed" },
  { value: "refrigerated", labelKey: "shipment.vehicleRefrigerated" },
  { value: "dump_truck", labelKey: "shipment.vehicleDumpTruck" },
  { value: "tanker", labelKey: "shipment.vehicleTanker" },
  { value: "car_carrier", labelKey: "shipment.vehicleCarCarrier" },
  { value: "trailer", labelKey: "shipment.vehicleTrailer" },
  { value: "heavy_truck", labelKey: "shipment.vehicleHeavyTruck" },
  { value: "container", labelKey: "shipment.vehicleContainer" }, // legacy/back-compat
];

const LABEL_BY_VALUE = Object.fromEntries(VEHICLE_TYPES.map((v) => [v.value, v.labelKey]));

// Localized label for a stored vehicle_type value. Falls back to the raw value
// (never crashes) for unknown/legacy values.
export function vehicleTypeLabel(t, value) {
  if (!value) return "—";
  const key = LABEL_BY_VALUE[String(value).toLowerCase()];
  return key ? t(key) : String(value);
}
