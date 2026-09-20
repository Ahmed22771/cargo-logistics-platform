import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { LayoutGrid, Package, Gavel, Truck, Users, Car, Wallet, FileText, Building2 } from "lucide-react";
import { PortalLayout } from "../../components/PortalLayout";
import ProviderDashboard from "./ProviderDashboard";
import ProviderAvailable from "./ProviderAvailable";
import ProviderOffers from "./ProviderOffers";
import ProviderTrips from "./ProviderTrips";
import ProviderTripDetail from "./ProviderTripDetail";
import ProviderVehicles from "./ProviderVehicles";
import ProviderVehicleDetail from "./ProviderVehicleDetail";
import ProviderDrivers from "./ProviderDrivers";
import ProviderDriverDetail from "./ProviderDriverDetail";
import ProviderDocuments from "./ProviderDocuments";
import ProviderFinance from "./ProviderFinance";
import ProviderProfile from "./ProviderProfile";

const NAV = [
  { key: "dashboard", to: "", label: "provider.dashboard", icon: LayoutGrid },
  { key: "available", to: "/available", label: "provider.availableShipments", icon: Package },
  { key: "offers", to: "/offers", label: "provider.offers", icon: Gavel },
  { key: "trips", to: "/trips", label: "provider.trips", icon: Truck },
  { key: "vehicles", to: "/vehicles", label: "provider.vehicles", icon: Car },
  { key: "drivers", to: "/drivers", label: "provider.drivers", icon: Users },
  { key: "finance", to: "/finance", label: "provider.finance", icon: Wallet },
  { key: "documents", to: "/documents", label: "provider.companyDocs", icon: FileText },
  { key: "profile", to: "/profile", label: "provider.companyProfile", icon: Building2 },
];

export default function ProviderPortal() {
  return (
    <PortalLayout navItems={NAV} basePath="/provider" title="Company">
      <Routes>
        <Route index element={<ProviderDashboard />} />
        <Route path="available" element={<ProviderAvailable />} />
        <Route path="offers" element={<ProviderOffers />} />
        <Route path="trips" element={<ProviderTrips />} />
        <Route path="trips/:id" element={<ProviderTripDetail />} />
        <Route path="vehicles" element={<ProviderVehicles />} />
        <Route path="vehicles/:id" element={<ProviderVehicleDetail />} />
        <Route path="drivers" element={<ProviderDrivers />} />
        <Route path="drivers/:id" element={<ProviderDriverDetail />} />
        <Route path="documents" element={<ProviderDocuments />} />
        <Route path="finance" element={<ProviderFinance />} />
        <Route path="profile" element={<ProviderProfile />} />
        <Route path="*" element={<Navigate to="/provider" replace />} />
      </Routes>
    </PortalLayout>
  );
}
