import { Link } from "react-router-dom";

import { useAuth } from "../hooks/useAuth.js";
import logo from "../utils/logo.jpg";
import { AppNav } from "./AppNav.jsx";

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
      <div className="shell-body">
        {isAuthenticated ? <AppNav user={user} /> : null}
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
