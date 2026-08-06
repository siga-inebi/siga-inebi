import { useEffect, useState } from "react";

import { studentsService } from "../../services/studentsService.js";

/**
 * Guardianes activos, para poblar el selector de "vincular encargado
 * existente" en `StudentGuardianRelationsPanel`.
 *
 * A diferencia de `useSubjectOptions.js` (features/academics/), no hace
 * falta recorrer paginas: `GuardianOptionListView` responde el arreglo
 * completo sin paginar (`pagination_class = None`).
 *
 * `token` fuerza una relectura tras vincular un guardian nuevo, si el
 * llamador lo necesita; por defecto no hace falta pasarlo.
 */
export function useGuardianOptions(token = 0) {
  const [guardians, setGuardians] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    studentsService
      .listGuardianOptions()
      .then((results) => {
        if (active) {
          setGuardians(results || []);
        }
      })
      .catch((requestError) => {
        if (active) {
          setGuardians([]);
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [token]);

  return { guardians, error, loading };
}
