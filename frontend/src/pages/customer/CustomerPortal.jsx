import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Home, Package, Plus, User, MessageCircle } from "lucide-react";
import { PortalLayout } from "../../components/PortalLayout";
import Messages from "../../components/Messages";
import CustomerHome from "./CustomerHome";
import MyShipments from "./MyShipments";
import CreateShipment from "./CreateShipment";
import ShipmentDetail from "./ShipmentDetail";
import CustomerProfile from "./CustomerProfile";
import PaymentScreen from "./PaymentScreen";

const NAV = [
  { key: "home", to: "", label: "common.home", icon: Home },
  { key: "shipments", to: "/shipments", label: "nav.myShipments", icon: Package },
  { key: "create", to: "/create", label: "nav.createShipment", icon: Plus },
  { key: "messages", to: "/messages", label: "chat.title", icon: MessageCircle },
  { key: "profile", to: "/profile", label: "common.profile", icon: User },
];

export default function CustomerPortal() {
  return (
    <PortalLayout navItems={NAV} basePath="/customer" title="Customer">
      <Routes>
        <Route index element={<CustomerHome />} />
        <Route path="shipments" element={<MyShipments />} />
        <Route path="create" element={<CreateShipment />} />
        <Route path="shipment/:id" element={<ShipmentDetail />} />
        <Route path="pay/:tripId" element={<PaymentScreen />} />
        <Route path="messages" element={<Messages basePath="/customer" />} />
        <Route path="messages/:cid" element={<Messages basePath="/customer" />} />
        <Route path="profile" element={<CustomerProfile />} />
        <Route path="*" element={<Navigate to="/customer" replace />} />
      </Routes>
    </PortalLayout>
  );
}
