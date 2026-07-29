import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth.js";
import logo from "../utils/logo.jpg";

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  if (isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.username.trim() || !form.password) {
      setError("Ingrese usuario y contrasena.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await login(form);
      navigate(location.state?.from?.pathname || "/app", { replace: true });
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="auth-shell">
      <div className="panel auth-panel auth-panel-brand">
        <img alt="Logo de INEBI Salcaja" className="auth-logo" src={logo} />
        <p className="eyebrow">Acceso institucional</p>
        <h1>SIGA-INEBI</h1>
        <p>
          Plataforma base para gestionar usuarios, estudiantes, matricula,
          estructura academica y trazabilidad operativa del establecimiento.
        </p>
        <ul className="auth-highlights">
          <li>Sesion segura por cookies y CSRF</li>
          <li>Acceso controlado por rol y alcance</li>
          <li>Base lista para crecimiento modular</li>
        </ul>
      </div>

      <section className="panel auth-panel auth-panel-form">
        <p className="eyebrow">Bienvenido</p>
        <h2>Iniciar sesion</h2>
        <p className="muted">
          Usa cuenta institucional creada por `seed_demo_data` o configurada en
          tu entorno local.
        </p>
        {error ? <div className="message message-error">{error}</div> : null}
        <form className="form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Usuario institucional</span>
            <input
              autoComplete="username"
              name="username"
              onChange={(event) =>
                setForm({ ...form, username: event.target.value })
              }
              placeholder="Ejemplo: admin"
              value={form.username}
            />
          </label>
          <label className="field">
            <span>Contrasena</span>
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) =>
                setForm({ ...form, password: event.target.value })
              }
              placeholder="Ingrese su contrasena"
              type="password"
              value={form.password}
            />
          </label>
          <button className="button button-block" disabled={loading} type="submit">
            {loading ? "Validando acceso..." : "Entrar al sistema"}
          </button>
        </form>
      </section>
    </section>
  );
}
