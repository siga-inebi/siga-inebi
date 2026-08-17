import { useCallback } from "react";

import { peopleService } from "../../services/peopleService.js";
import { useAllPages } from "./useAllPages.js";

/**
 * Personas que pueden quedar a cargo de un curso.
 *
 * El backend no distingue docentes del resto de las personas: `teacher` apunta
 * a `people.Person` sin ninguna marca de rol. Aqui solo se filtran las activas,
 * que es la unica condicion que la API si valida.
 */
export function useTeacherOptions() {
  const loadPage = useCallback(
    (page) => peopleService.listPeople({ page }),
    []
  );
  const { items, error, loading } = useAllPages(loadPage);

  return {
    teachers: items.filter((person) => person.is_active),
    error,
    loading,
  };
}
