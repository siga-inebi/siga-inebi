import { Link } from "react-router-dom";

import { useAuth } from "../hooks/useAuth.js";

export function AppLayout({ children }) {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">SIGA-INEBI</div>
        <nav className="actions">
          <Link className="button secondary" to="/">
            Inicio
          </Link>
          {isAuthenticated ? (
            <>
              <span>{user?.username}</span>
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
      <main className="content">{children}</main>
    </div>
  );
}
