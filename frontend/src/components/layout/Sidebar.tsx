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
    <nav className="flex w-52 shrink-0 flex-col border-r border-slate-200 bg-white py-4">
      {links.map(({ to, key }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            `mx-2 rounded-lg px-4 py-2.5 text-sm font-medium ${
              isActive
                ? "bg-[#1e3a5f] text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`
          }
        >
          {nav[key]}
        </NavLink>
      ))}
    </nav>
  );
}
