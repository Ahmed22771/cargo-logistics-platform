import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Home, Package, Gavel, Truck, ShieldCheck, FileText } from "lucide-react";
import { PortalLayout } from "../../components/PortalLayout";
import DriverHome from "./DriverHome";
import AvailableShipments from "./AvailableShipments";
import MyBids from "./MyBids";
import ActiveTrip from "./ActiveTrip";
import TripHistory from "./TripHistory";
import Verification from "./Verification";
import DriverDocuments from "./DriverDocuments";
import DriverProfile from "./DriverProfile";

const NAV = [
  { key: "home", to: "", label: "common.home", icon: Home },
  { key: "available", to: "/available", label: "nav.availableShipments", icon: Package },
  { key: "bids", to: "/bids", label: "nav.myBids", icon: Gavel },
  { key: "trip", to: "/trip", label: "nav.activeTrip", icon: Truck },
  { key: "documents", to: "/documents", label: "nav.documents", icon: FileText },
  { key: "verification", to: "/verification", label: "nav.verification", icon: ShieldCheck },
];

export default function DriverPortal() {
  return (
    <PortalLayout navItems={NAV} basePath="/driver" title="Driver">
      <Routes>
        <Route index element={<DriverHome />} />
        <Route path="available" element={<AvailableShipments />} />
        <Route path="bids" element={<MyBids />} />
        <Route path="trip" element={<ActiveTrip />} />
        <Route path="history" element={<TripHistory />} />
        <Route path="verification" element={<Verification />} />
        <Route path="documents" element={<DriverDocuments />} />
        <Route path="profile" element={<DriverProfile />} />
        <Route path="*" element={<Navigate to="/driver" replace />} />
      </Routes>
    </PortalLayout>
  );
}
