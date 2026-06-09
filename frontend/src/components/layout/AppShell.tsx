import { Outlet, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { CopilotDrawer } from "../copilot/CopilotDrawer";
import { useCopilot } from "../../context/CopilotContext";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

const pageNames: Record<string, string> = {
  "/": "home",
  "/suppliers": "suppliers",
  "/qualification": "qualification",
  "/review": "review-queue",
  "/policy": "policy",
};

export function AppShell() {
  const location = useLocation();
  const { setPageContext, open } = useCopilot();

  useEffect(() => {
    const base = pageNames[location.pathname] || location.pathname.slice(1);
    setPageContext({ page: base });
  }, [location.pathname, setPageContext]);

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <div className="flex flex-1">
        <Sidebar />
        <main
          className={`flex-1 overflow-y-auto p-6 transition-[margin] ${open ? "mr-96" : ""}`}
        >
          <Outlet />
        </main>
      </div>
      <CopilotDrawer />
    </div>
  );
}
