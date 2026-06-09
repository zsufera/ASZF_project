import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { SessionProvider, useSession } from "./state/session";
import { ToastProvider } from "./state/toast";
import { AppShell } from "./components/AppShell";
import { Login } from "./screens/Login";
import { Inbox } from "./screens/Inbox";
import { CaseWorkstation } from "./screens/CaseWorkstation";
import { NewCase } from "./screens/NewCase";
import { Copilot } from "./screens/Copilot";
import { Postal } from "./screens/Postal";
import { Evaluation } from "./screens/Evaluation";
import { Supervisor } from "./screens/Supervisor";
import { Knowledge } from "./screens/Knowledge";

function SupervisorGuard({ children }: { children: React.ReactNode }) {
  const { user } = useSession();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "supervisor") return <Navigate to="/inbox" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/inbox" replace />} />
        <Route path="/inbox" element={<Inbox />} />
        <Route path="/case/:id" element={<CaseWorkstation />} />
        <Route path="/new" element={<NewCase />} />
        <Route path="/copilot" element={<Copilot />} />
        <Route path="/postal" element={<Postal />} />
        <Route path="/eval" element={<Evaluation />} />
        <Route path="/knowledge" element={<Knowledge />} />
        <Route path="/supervisor" element={
          <SupervisorGuard><Supervisor /></SupervisorGuard>
        } />
        <Route path="*" element={<Navigate to="/inbox" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </SessionProvider>
    </BrowserRouter>
  );
}
