import { Outlet, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { CopilotDrawer } from "../copilot/CopilotDrawer";
import { useCopilot } from "../../context/CopilotContext";
import { Sidebar } from "./Sidebar";
import type { PageContext } from "../../types/api";

function resolvePage(pathname: string): Pick<PageContext, "page"> {
  if (pathname === "/") return { page: "home" };
  if (pathname.startsWith("/suppliers/")) return { page: "supplier-detail" };
  if (pathname === "/suppliers") return { page: "suppliers" };
  if (pathname === "/qualification") return { page: "qualification" };
  if (pathname === "/review") return { page: "review-queue" };
  if (pathname === "/policy") return { page: "policy" };
  return { page: pathname.slice(1) || "home" };
}

export function AppShell() {
  const location = useLocation();
  const { setPageContext, open } = useCopilot();

  useEffect(() => {
    const { page } = resolvePage(location.pathname);
    setPageContext((prev) => {
      const next: PageContext = { ...prev, page };
      if (page !== "supplier-detail") {
        delete next.supplierId;
        delete next.supplierName;
      }
      if (page !== "review-queue") {
        delete next.reviewTaskId;
      }
      if (page !== "qualification") {
        delete next.extraPrefix;
      }
      return next;
    });
  }, [location.pathname, setPageContext]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main
        className={`flex-1 overflow-y-auto px-8 py-7 transition-[margin] ${open ? "mr-[26rem]" : ""}`}
        style={{ background: "var(--paper)" }}
      >
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
      <CopilotDrawer />
    </div>
  );
}
