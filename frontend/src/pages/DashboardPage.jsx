import { useEffect, useState } from "react";

import { apiClient } from "../services/apiClient";

export function DashboardPage() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiClient
      .get("/health/")
      .then(setHealth)
      .catch((requestError) => setError(requestError.message));
  }, []);

  return (
    <section className="grid">
      <div className="panel">
        <h1>Sesion autenticada</h1>
        <p>Espacio inicial reservado para panel privado.</p>
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
