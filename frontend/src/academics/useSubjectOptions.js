import { useEffect, useState } from "react";

import { academicsService } from "@academics/academicsService.js";

// Tope de seguridad: el selector nunca deberia recorrer mas paginas que estas.
const MAX_PAGES = 40;

/**
 * Cursos activos disponibles para vincular a un nivel.
 *
 * Recorre todas las paginas: un selector que solo ofreciera la primera pagina
 * ocultaria cursos existentes sin avisar. `token` fuerza la relectura despues
 * de crear un curso.
 */
export function useSubjectOptions(token = 0) {
  const [subjects, setSubjects] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    const collect = async () => {
      const collected = [];

      for (let page = 1; page <= MAX_PAGES; page += 1) {
        const payload = await academicsService.listSubjects({ page });
        collected.push(...(payload?.results || []));
        if (!payload?.next) {
          break;
        }
      }

      return collected;
    };

    collect()
      .then((collected) => {
        if (active) {
          setSubjects(collected);
        }
      })
      .catch((requestError) => {
        if (active) {
          setSubjects([]);
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

  return { subjects, error, loading };
}
