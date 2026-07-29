import { useEffect, useState } from "react";

import { apiClient } from "../services/apiClient.js";
import { useAuth } from "../hooks/useAuth.js";

export function DashboardPage() {
  const { user } = useAuth();
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiClient
      .get("/health/")
      .then(setHealth)
      .catch((requestError) => setError(requestError.message));
  }, []);

  return (
    <section className="dashboard-grid">
      <div className="panel hero hero-primary">
        <p className="eyebrow">Sesion autenticada</p>
        <h1>Bienvenido, {user?.person?.first_name || user?.username}.</h1>
        <p>
          Tu cuenta institucional ya esta activa en capa base. Desde aqui
          creceran los modulos academicos, administrativos y de control del
          instituto.
        </p>
      </div>
      <div className="panel">
        <h2>Identidad actual</h2>
        <dl className="info-list">
          <div>
            <dt>Usuario</dt>
            <dd>{user?.username}</dd>
          </div>
          <div>
            <dt>Correo</dt>
            <dd>{user?.email || "No definido"}</dd>
          </div>
          <div>
            <dt>Estado</dt>
            <dd>{user?.status}</dd>
          </div>
        </dl>
      </div>
      <div className="panel">
        <h2>Estado del backend</h2>
        {health ? (
          <p className="status-ok">
            {health.service}: {health.status}
          </p>
        ) : null}
        {error ? <p className="status-error">{error}</p> : null}
      </div>
    </section>
  );
}
