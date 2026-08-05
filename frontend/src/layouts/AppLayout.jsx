import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../hooks/useAuth.js";
import { MODULE_NAV } from "../routes/moduleNav.js";
import logo from "../utils/logo.jpg";

export function AppLayout({ children }) {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <img alt="Logo de INEBI Salcaja" className="brand-logo" src={logo} />
          <div>
            <strong>SIGA-INEBI</strong>
            <span>Instituto Nacional de Educacion Basica de Salcaja</span>
          </div>
        </Link>
        <nav className="actions">
          <Link className="button secondary" to="/">
            Inicio
          </Link>
          {isAuthenticated ? (
            <>
              <span className="user-chip">
                {user?.person?.first_name || user?.username}
              </span>
              <button className="button" onClick={logout} type="button">
                Cerrar sesion
              </button>
            </>
          ) : (
            <Link className="button" to="/login">
              Iniciar sesion
            </Link>
          )}
        </nav>
      </header>
      {isAuthenticated ? (
        <nav aria-label="Modulos" className="module-nav">
          {MODULE_NAV.map((item) => (
            <NavLink
              className={({ isActive }) =>
                isActive ? "module-link is-active" : "module-link"
              }
              end={item.end}
              key={item.to}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      ) : null}
      <main className="content">{children}</main>
    </div>
  );
}
