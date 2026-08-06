import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

import { guardiansService } from "../services/guardiansService.js";
import { studentsService } from "../services/studentsService.js";
import { teachersService } from "../services/teachersService.js";
import {
  canViewAlumnos,
  canViewCursos,
  canViewDocentes,
  canViewNiveles,
  canViewPadres,
  canViewSedes,
} from "../utils/permissions.js";

const COUNT_SERVICES = {
  alumnos: studentsService,
  docentes: teachersService,
  padres: guardiansService,
};

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

const CATALOGUE_ITEMS = [
  {
    key: "sedes",
    label: "Sedes",
    path: "/app/sedes",
    canView: canViewSedes,
  },
  {
    key: "niveles",
    label: "Niveles",
    path: "/app/niveles",
    canView: canViewNiveles,
  },
  {
    key: "cursos",
    label: "Cursos",
    path: "/app/cursos",
    canView: canViewCursos,
  },
];

function initials(label) {
  return label.replace(/\s+/g, "").slice(0, 2).toUpperCase();
}

function navLinkClassName({ isActive }) {
  return isActive ? "sidebar-link active" : "sidebar-link";
}

function NavItem({ badge, item, onNavigate }) {
  return (
    <NavLink
      aria-label={item.label}
      className={navLinkClassName}
      end={item.path === "/app"}
      onClick={onNavigate}
      title={item.label}
      to={item.path}
    >
      <span className="sidebar-link-icon">{initials(item.label)}</span>
      <span className="sidebar-link-label">{item.label}</span>
      {badge != null ? <span className="sidebar-badge">{badge}</span> : null}
    </NavLink>
  );
}

export function AppNav({ accountActions, onNavigate, open, user }) {
  const [collapsed, setCollapsed] = useState(false);
  const [counts, setCounts] = useState({});
  const items = LISTADO_ITEMS.filter((item) => item.canView(user));
  const catalogueItems = CATALOGUE_ITEMS.filter((item) => item.canView(user));
  const asideClassName = [
    "sidebar",
    collapsed ? "sidebar-collapsed" : "",
    open ? "sidebar-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  useEffect(() => {
    let active = true;
    Promise.all(
      Object.entries(COUNT_SERVICES).map(([key, service]) =>
        service
          .list()
          .then((records) => [key, records.length])
          .catch(() => [key, null])
      )
    ).then((entries) => {
      if (active) {
        setCounts(Object.fromEntries(entries));
      }
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <aside className={asideClassName}>
      <button
        aria-label={collapsed ? "Expandir navegacion" : "Colapsar navegacion"}
        className="sidebar-toggle"
        onClick={() => setCollapsed((value) => !value)}
        type="button"
      >
        {collapsed ? "»" : "«"}
      </button>

      <NavItem item={HOME_ITEM} onNavigate={onNavigate} />

      {items.length > 0 ? (
        <>
          <p className="sidebar-title">Listados</p>
          <nav aria-label="Listados" className="sidebar-nav">
            {items.map((item) => (
              <NavItem
                badge={counts[item.key]}
                item={item}
                key={item.key}
                onNavigate={onNavigate}
              />
            ))}
          </nav>
        </>
      ) : null}

      {catalogueItems.length > 0 ? (
        <>
          <p className="sidebar-title">Catalogo academico</p>
          <nav aria-label="Catalogo academico" className="sidebar-nav">
            {catalogueItems.map((item) => (
              <NavItem item={item} key={item.key} onNavigate={onNavigate} />
            ))}
          </nav>
        </>
      ) : null}

      {accountActions ? (
        <div className="sidebar-actions">{accountActions}</div>
      ) : null}
    </aside>
  );
}
