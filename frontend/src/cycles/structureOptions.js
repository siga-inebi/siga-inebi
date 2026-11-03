import { useQuery } from "@tanstack/react-query";

import { academicsService } from "@academics/academicsService.js";
import { queryKeys } from "@shared/api/queryKeys.js";

/**
 * Opciones pequeñas y acotadas de la institucion para los formularios del
 * ciclo: grados (con su nivel) y jornadas (con su sede).
 *
 * Son catalogos cortos por naturaleza (una decena de grados, dos o tres
 * jornadas), asi que se piden en una sola pagina de 100 en lugar de recorrer
 * paginas con `collectAllPages`.
 */
const MAX = 100;

async function loadGrades() {
  const page = await academicsService.listLevels({
    expand: "grades",
    page_size: MAX,
  });
  return (page.results ?? [])
    .flatMap((level) =>
      (level.grades ?? []).map((grade) => ({
        value: grade.public_id,
        label: level.name ? `${grade.name} · ${level.name}` : grade.name,
        name: grade.name,
        levelId: level.public_id,
        levelName: level.name,
        order: [level.sequence ?? 0, grade.sequence ?? 0],
      }))
    )
    .sort(
      (left, right) =>
        left.order[0] - right.order[0] || left.order[1] - right.order[1]
    );
}

async function loadShifts() {
  const campuses = await academicsService.listCampuses({ page_size: MAX });
  const perCampus = await Promise.all(
    (campuses.results ?? []).map((campus) =>
      academicsService
        .listCampusShifts(campus.public_id, { page_size: MAX })
        .then((page) =>
          (page.results ?? []).map((shift) => ({
            value: shift.public_id,
            label: `${shift.name} · ${campus.name}`,
            name: shift.name,
            campusId: campus.public_id,
          }))
        )
    )
  );
  return perCampus.flat();
}

export function useGradeOptions() {
  const query = useQuery({
    queryKey: queryKeys.academics.grades(),
    queryFn: loadGrades,
  });
  return {
    options: query.data ?? [],
    loading: query.isPending,
    error: query.error?.message ?? "",
  };
}

export function useShiftOptions() {
  const query = useQuery({
    queryKey: queryKeys.academics.shifts(),
    queryFn: loadShifts,
  });
  return {
    options: query.data ?? [],
    loading: query.isPending,
    error: query.error?.message ?? "",
  };
}
