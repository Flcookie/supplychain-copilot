import { NavLink } from "react-router-dom";
import { useCopilot } from "../../context/CopilotContext";
import { t } from "../../i18n";

const links = [
  { to: "/", key: "home" as const },
  { to: "/suppliers", key: "suppliers" as const },
  { to: "/qualification", key: "qualification" as const },
  { to: "/review", key: "review" as const },
  { to: "/policy", key: "policy" as const },
];

export function Sidebar() {
  const { lang } = useCopilot();
  const nav = t(lang).nav;

  return (
    <aside
      className="flex w-56 shrink-0 flex-col border-r px-0 py-6"
      style={{
        background: "var(--sidebar)",
        borderColor: "#141210",
      }}
    >
      <div className="px-5 pb-8">
        <p
          className="font-serif text-2xl tracking-tight"
          style={{ color: "var(--sidebar-active)" }}
        >
          Ratti
        </p>
        <p className="mt-1 text-[11px] uppercase tracking-[0.14em]" style={{ color: "#8a8278" }}>
          Supplier desk
        </p>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-3">
        {links.map(({ to, key }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "font-medium"
                  : "hover:text-[var(--sidebar-active)]"
              }`
            }
            style={({ isActive }) =>
              isActive
                ? {
                    background: "var(--sidebar-active)",
                    color: "var(--ink)",
                  }
                : { color: "var(--sidebar-text)" }
            }
          >
            {nav[key]}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto border-t px-5 pt-5" style={{ borderColor: "#33302c" }}>
        <p className="text-sm" style={{ color: "var(--sidebar-active)" }}>
          Sarah Chen
        </p>
        <p className="text-xs" style={{ color: "#8a8278" }}>
          Yarn procurement
        </p>
      </div>
    </aside>
  );
}
