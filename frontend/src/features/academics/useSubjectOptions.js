import { useCallback } from "react";

import { academicsService } from "../../services/academicsService.js";
import { useAllPages } from "./useAllPages.js";

/**
 * Cursos disponibles para vincular a un nivel o para planificar en un grado.
 * `token` fuerza la relectura despues de crear un curso.
 */
export function useSubjectOptions(token = 0) {
  const loadPage = useCallback(
    (page) => academicsService.listSubjects({ page }),
    []
  );
  const { items, error, loading } = useAllPages(loadPage, token);

  return { subjects: items, error, loading };
}
