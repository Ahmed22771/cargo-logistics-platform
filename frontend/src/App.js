import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import CustomerPortal from "./pages/customer/CustomerPortal";
import DriverPortal from "./pages/driver/DriverPortal";
import ProviderPortal from "./pages/provider/ProviderPortal";
import AdminPortal from "./pages/admin/AdminPortal";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/customer/*" element={<ProtectedRoute roles={["customer"]}><CustomerPortal /></ProtectedRoute>} />
          <Route path="/driver/*" element={<ProtectedRoute roles={["driver"]}><DriverPortal /></ProtectedRoute>} />
          <Route path="/provider/*" element={<ProtectedRoute roles={["provider"]}><ProviderPortal /></ProtectedRoute>} />
          <Route path="/admin/*" element={<AdminPortal />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors closeButton />
    </div>
  );
}

export default App;
