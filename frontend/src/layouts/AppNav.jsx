import { useState } from "react";
import { NavLink } from "react-router-dom";

import {
  canViewAlumnos,
  canViewDocentes,
  canViewPadres,
} from "../utils/permissions.js";

const HOME_ITEM = { key: "inicio", label: "Panel principal", path: "/app" };

const LISTADO_ITEMS = [
  {
    key: "alumnos",
    label: "Alumnos",
    path: "/app/alumnos",
    canView: canViewAlumnos,
  },
  {
    key: "docentes",
    label: "Docentes",
    path: "/app/docentes",
    canView: canViewDocentes,
  },
  {
    key: "padres",
    label: "Padres de familia",
    path: "/app/padres-de-familia",
    canView: canViewPadres,
  },
];

function initials(label) {
  return label.replace(/\s+/g, "").slice(0, 2).toUpperCase();
}

function navLinkClassName({ isActive }) {
  return isActive ? "sidebar-link active" : "sidebar-link";
}

function NavItem({ badge, item }) {
  return (
    <NavLink
      aria-label={item.label}
      className={navLinkClassName}
      end={item.path === "/app"}
      title={item.label}
      to={item.path}
    >
      <span className="sidebar-link-icon">{initials(item.label)}</span>
      <span className="sidebar-link-label">{item.label}</span>
      {badge != null ? <span className="sidebar-badge">{badge}</span> : null}
    </NavLink>
  );
}

// `counts` se completa cuando existan los servicios de dominio
// (students/teachers/guardians); mientras tanto no se muestra badge.
export function AppNav({ counts = {}, user }) {
  const [collapsed, setCollapsed] = useState(false);
  const items = LISTADO_ITEMS.filter((item) => item.canView(user));

  return (
    <aside className={collapsed ? "sidebar sidebar-collapsed" : "sidebar"}>
      <button
        aria-label={collapsed ? "Expandir navegacion" : "Colapsar navegacion"}
        className="sidebar-toggle"
        onClick={() => setCollapsed((value) => !value)}
        type="button"
      >
        {collapsed ? "»" : "«"}
      </button>

      <NavItem item={HOME_ITEM} />

      {items.length > 0 ? (
        <>
          <p className="sidebar-title">Listados</p>
          <nav className="sidebar-nav">
            {items.map((item) => (
              <NavItem badge={counts[item.key]} item={item} key={item.key} />
            ))}
          </nav>
        </>
      ) : null}
    </aside>
  );
}
