import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { academicsService } from "@academics/academicsService.js";
import { sectionLabel } from "@academics/searchOptions.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { todayInputValue } from "@shared/utils/format.js";

/**
 * Datos que comparten las pestañas de Evaluación. Cada lista es de un solo
 * ciclo y acotada: unidades (4–6), secciones del ciclo y subáreas del plan de
 * un grado. Se piden en una página de 100, igual que el horario del ciclo
 * (`ScheduleTab`), y nunca se recorre un padrón completo.
 */
export const OPTIONS_PAGE_SIZE = 100;

export function useCycleUnits(cycleId) {
  return useQuery({
    queryKey: queryKeys.evaluation(cycleId, "units"),
    queryFn: () =>
      evaluationService.listUnits(cycleId, { page_size: OPTIONS_PAGE_SIZE }),
    enabled: Boolean(cycleId),
    select: (page) => page?.results ?? [],
  });
}

export function unitLabel(unit) {
  return unit.number ? `${unit.number}. ${unit.name}` : unit.name;
}

/** Unidad a mostrar sin elección: la que hoy está en captura, o la primera abierta. */
export function defaultUnit(units, today = todayInputValue()) {
  const open = units.filter((unit) => unit.status !== "closed");
  return (
    open.find(
      (unit) => unit.capture_starts_on <= today && today <= unit.capture_ends_on
    ) ??
    open[0] ??
    units[0] ??
    null
  );
}

export function useCycleSections(cycleId) {
  return useQuery({
    queryKey: queryKeys.academics.list("sections", cycleId, "all"),
    queryFn: () =>
      academicsService.listSections({
        academic_cycle_id: cycleId,
        page_size: OPTIONS_PAGE_SIZE,
      }),
    enabled: Boolean(cycleId),
    select: (page) => page?.results ?? [],
  });
}

export function sectionOptions(sections = []) {
  return sections.map((section) => ({
    value: section.public_id,
    label: sectionLabel(section),
  }));
}

/** Subáreas del plan de estudios del ciclo para un grado. */
export function usePlanSubjects(cycleId, gradeId) {
  return useQuery({
    queryKey: queryKeys.academics.list("curriculum-plans", cycleId, gradeId),
    queryFn: () =>
      academicsService.listCurriculumPlans({
        academic_cycle_id: cycleId,
        grade_id: gradeId,
        page_size: OPTIONS_PAGE_SIZE,
      }),
    enabled: Boolean(cycleId && gradeId),
    select: (page) =>
      (page?.results ?? []).map((plan) => ({
        value: plan.subject.public_id,
        label: plan.subject.name,
      })),
  });
}

/**
 * Parámetros de la URL que comparten las pestañas (`unidad`, `seccion`,
 * `subarea`…). Un valor vacío se quita de la URL.
 */
export function useUrlParams() {
  const [params, setParams] = useSearchParams();
  const set = (changes) =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        for (const [key, value] of Object.entries(changes)) {
          if (value) next.set(key, value);
          else next.delete(key);
        }
        return next;
      },
      { replace: true }
    );
  return [params, set];
}

/**
 * Cursos (sección y subárea) que la cuenta puede calificar en el ciclo. El
 * backend decide: dirección ve todos los del plan y un docente solo sus
 * asignaciones, así que la planilla nunca ofrece un curso ajeno.
 */
export function useGradeCourses(cycleId) {
  return useQuery({
    queryKey: queryKeys.evaluation(cycleId, "grade-courses"),
    queryFn: () => evaluationService.listGradeCourses(cycleId),
    enabled: Boolean(cycleId),
  });
}

/** Secciones distintas de los cursos, en el orden que manda el backend. */
export function courseSectionOptions(courses = []) {
  const seen = new Set();
  const options = [];
  for (const course of courses) {
    if (!seen.has(course.section.public_id)) {
      seen.add(course.section.public_id);
      options.push({
        value: course.section.public_id,
        label: course.section.label,
      });
    }
  }
  return options;
}

/** Subáreas de los cursos de una sección. */
export function courseSubjectOptions(courses = [], sectionId) {
  return courses
    .filter((course) => course.section.public_id === sectionId)
    .map((course) => ({
      value: course.subject.public_id,
      label: course.subject.name,
    }));
}
