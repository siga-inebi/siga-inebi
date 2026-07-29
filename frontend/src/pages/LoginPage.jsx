import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

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
    <section className="panel">
      <h1>Iniciar sesion</h1>
      <p>Usa cuenta institucional configurada en ambiente local o por `seed_demo_data`.</p>
      {error ? <div className="message">{error}</div> : null}
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Usuario</span>
          <input
            autoComplete="username"
            name="username"
            onChange={(event) => setForm({ ...form, username: event.target.value })}
            value={form.username}
          />
        </label>
        <label className="field">
          <span>Contrasena</span>
          <input
            autoComplete="current-password"
            name="password"
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            type="password"
            value={form.password}
          />
        </label>
        <button className="button" disabled={loading} type="submit">
          {loading ? "Validando..." : "Entrar"}
        </button>
      </form>
    </section>
  );
}
