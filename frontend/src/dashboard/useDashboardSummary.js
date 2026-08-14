import { useEffect, useState } from "react";

import { apiClient } from "@shared/api/apiClient.js";
import { guardiansService } from "@guardians/guardiansService.js";
import { studentsService } from "@students/studentsService.js";
import { teachersService } from "@teachers/teachersService.js";

/**
 * Datos agregados del panel: conteos por dominio y salud del servicio.
 *
 * El panel es la unica pantalla que legitimamente lee de varios dominios a la
 * vez — es su razon de existir. Cada conteo se resuelve por separado y un fallo
 * deja ese indicador en `null` sin tumbar los demas: media pantalla con datos es
 * mejor que una pantalla en blanco porque un endpoint respondio 500.
 */
export function useDashboardSummary() {
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState({ data: null, error: "" });

  useEffect(() => {
    let active = true;

    const sources = [
      ["students", studentsService],
      ["teachers", teachersService],
      ["guardians", guardiansService],
    ];

    Promise.all(
      sources.map(([key, service]) =>
        service
          .list()
          .then((records) => [key, records.length])
          .catch(() => [key, null])
      )
    ).then((entries) => {
      if (!active) return;
      setCounts(Object.fromEntries(entries));
      setLoading(false);
    });

    apiClient
      .get("/health/")
      .then((data) => {
        if (active) setHealth({ data, error: "" });
      })
      .catch((requestError) => {
        if (active) setHealth({ data: null, error: requestError.message });
      });

    return () => {
      active = false;
    };
  }, []);

  return { counts, health, loading };
}
