import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../hooks/useAuth.js";
import logo from "../utils/logo.jpg";
import { AppNav } from "./AppNav.jsx";

export function AppLayout({ children }) {
  const { isAuthenticated, logout, user } = useAuth();
  const [navOpen, setNavOpen] = useState(false);

  const closeNav = () => setNavOpen(false);

  const accountActions = (
    <div className="actions action-group-links">
      <Link className="button secondary" onClick={closeNav} to="/">
        Inicio
      </Link>
      {isAuthenticated ? (
        <>
          <span className="user-chip">
            {user?.person?.first_name || user?.username}
          </span>
          <button
            className="button"
            onClick={() => {
              closeNav();
              logout();
            }}
            type="button"
          >
            Cerrar sesion
          </button>
        </>
      ) : (
        <Link className="button" onClick={closeNav} to="/login">
          Iniciar sesion
        </Link>
      )}
    </div>
  );

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
        <div
          className={
            isAuthenticated ? "action-group has-drawer" : "action-group"
          }
        >
          <button
            aria-expanded={navOpen}
            aria-label={navOpen ? "Cerrar menu" : "Abrir menu"}
            className="action-group-toggle"
            onClick={() => setNavOpen((value) => !value)}
            type="button"
          >
            <span className="action-group-toggle-bar" />
            <span className="action-group-toggle-bar" />
            <span className="action-group-toggle-bar" />
          </button>
          {navOpen ? (
            <div className="action-group-menu">{accountActions}</div>
          ) : null}
        </div>
      </header>
      <div className="shell-body">
        {isAuthenticated ? (
          <AppNav
            accountActions={accountActions}
            onNavigate={closeNav}
            open={navOpen}
            user={user}
          />
        ) : null}
        <main className="content">
          <div className="content-inner">{children}</div>
        </main>
      </div>
      {navOpen ? (
        <button
          aria-label="Cerrar menu"
          className={
            isAuthenticated
              ? "nav-backdrop nav-backdrop-drawer"
              : "nav-backdrop"
          }
          onClick={closeNav}
          type="button"
        />
      ) : null}
    </div>
  );
}
