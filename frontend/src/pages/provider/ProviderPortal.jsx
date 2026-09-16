import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Home, User } from "lucide-react";
import { PortalLayout } from "../../components/PortalLayout";
import ProviderDashboard from "./ProviderDashboard";
import ProviderProfile from "./ProviderProfile";

const NAV = [
  { key: "home", to: "", label: "nav.dashboard", icon: Home },
  { key: "profile", to: "/profile", label: "common.profile", icon: User },
];

export default function ProviderPortal() {
  return (
    <PortalLayout navItems={NAV} basePath="/provider" title="Provider">
      <Routes>
        <Route index element={<ProviderDashboard />} />
        <Route path="profile" element={<ProviderProfile />} />
        <Route path="*" element={<Navigate to="/provider" replace />} />
      </Routes>
    </PortalLayout>
  );
}
