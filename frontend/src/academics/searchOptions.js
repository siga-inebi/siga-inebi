import { academicsService } from "@academics/academicsService.js";
import { teachersService } from "@teachers/teachersService.js";
import { CATALOG } from "@shared/api/queryKeys.js";

/**
 * Configuraciones de `search-select` (docs/ux-ui.md 1.3) para la estructura
 * academica. Cada una pide al backend `?search=` con lo que la persona escribe:
 * ningun selector descarga el padron completo.
 *
 * Se declaran una vez aqui para que la matriz de asignaciones, "Asignar por
 * lotes" y los formularios de secciones etiqueten igual al mismo docente, aula
 * o curso.
 */

function personName(person) {
  return [person?.first_name, person?.last_name].filter(Boolean).join(" ");
}

/** Docente como opcion: `value` es el `public_id` del perfil Teacher. */
export function teacherOption(teacher) {
  return {
    value: teacher.public_id,
    label: [personName(teacher.person), teacher.employee_code]
      .filter(Boolean)
      .join(" · "),
  };
}

export const TEACHER_SEARCH = Object.freeze({
  name: CATALOG.teachers,
  fetchPage: (params) => teachersService.listPage(params),
  mapResult: teacherOption,
});

export const SUBJECT_SEARCH = Object.freeze({
  name: CATALOG.subjects,
  fetchPage: (params) => academicsService.listSubjects(params),
  mapResult: (subject) => ({
    value: subject.public_id,
    label: subject.code ? `${subject.name} (${subject.code})` : subject.name,
  }),
});

/** Aulas, opcionalmente acotadas a una sede. */
export function classroomSearch(campusId) {
  return {
    name: campusId ? `classrooms:${campusId}` : "classrooms",
    fetchPage: (params) =>
      academicsService.listClassrooms(
        campusId ? { ...params, campus_id: campusId } : params
      ),
    mapResult: (room) => ({
      value: room.public_id,
      label: room.code ? `${room.name} (${room.code})` : room.name,
    }),
  };
}

/** Secciones de un ciclo, etiquetadas "Grado Seccion · Jornada". */
export function sectionLabel(section) {
  const grade = section.grade?.name ?? section.grade_name;
  const shift = section.shift?.name;
  return [[grade, section.name].filter(Boolean).join(" "), shift]
    .filter(Boolean)
    .join(" · ");
}

export function sectionSearch(cycleId) {
  return {
    name: `sections:${cycleId}`,
    fetchPage: (params) =>
      academicsService.listSections({
        ...params,
        academic_cycle_id: cycleId,
      }),
    mapResult: (section) => ({
      value: section.public_id,
      label: sectionLabel(section),
    }),
  };
}
