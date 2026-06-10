import { useEffect, useState } from "react";
import { Outlet, Navigate } from "react-router-dom";
import { useSession } from "../state/session";
import { TopHeader } from "./TopHeader";
import { IconNav } from "./IconNav";
import { OfflineBanner } from "./OfflineBanner";
import { ToastContainer } from "./Toast";
import { api } from "../lib/api";
import { CommandPalette } from "./CommandPalette";

export function AppShell() {
  const { user, modelProfile, setModelProfile, setAszfVersion, aszfVersion } = useSession();
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    api.health()
      .then((h) => { setAszfVersion(h.aszf_version ?? "—"); setOffline(false); })
      .catch(() => setOffline(true));
  }, [setAszfVersion]);

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="flex flex-col min-h-screen bg-one-canvas">
      <TopHeader
        aszfVersion={aszfVersion}
        modelProfile={modelProfile}
        onProviderChange={setModelProfile}
        offline={offline}
      />
      <OfflineBanner offline={offline} />
      <CommandPalette role={user.role} />
      <div className="flex flex-1 overflow-hidden">
        <IconNav role={user.role} />
        <main className="flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}
