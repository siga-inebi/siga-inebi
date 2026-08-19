import { useMemo } from "react";

import { academicsService } from "@academics/academicsService.js";
import { CYCLE_STATUS_LABEL, cyclesService } from "@cycles/cyclesService.js";
import { studentsService } from "@students/studentsService.js";
import { teachersService } from "@teachers/teachersService.js";

import { collectAllPages, useCatalogOptions } from "./useCatalogOptions.js";

/**
 * Catalogos que alimentan los selectores de los formularios.
 *
 * Antes cada pantalla pedia el UUID del ciclo, de la seccion, del curso o del
 * docente escrito a mano. Ningun usuario del instituto conoce esos
 * identificadores: viven en la base de datos, no en el mundo. Estos hooks
 * traen el catalogo y devuelven `{value,label}` con el nombre que la persona SI
 * reconoce, dejando el UUID como detalle interno del formulario.
 *
 * Cada `load` se define a nivel de modulo para que sea estable entre renders:
 * `useCatalogOptions` la usa como dependencia de su efecto.
 */

/** Ordena por etiqueta para que el desplegable no cambie de orden entre cargas. */
function byLabel(options) {
  return [...options].sort((left, right) =>
    left.label.localeCompare(right.label, "es")
  );
}

function personName(person) {
  return [person?.first_name, person?.last_name].filter(Boolean).join(" ");
}

async function loadCycles() {
  const cycles = await collectAllPages(cyclesService.list);
  // Los ciclos NO se ordenan por etiqueta: el orden natural es el cronologico
  // inverso, porque el ciclo con el que se trabaja es casi siempre el ultimo.
  return [...cycles]
    .sort((left, right) => right.year - left.year)
    .map((cycle) => ({
      value: cycle.public_id,
      label: `${cycle.name} · ${CYCLE_STATUS_LABEL[cycle.status] ?? cycle.status}`,
    }));
}

async function loadSubjects() {
  const subjects = await collectAllPages(academicsService.listSubjects);
  return byLabel(
    subjects.map((subject) => ({
      value: subject.public_id,
      label: subject.code ? `${subject.name} (${subject.code})` : subject.name,
    }))
  );
}

async function loadTeachers() {
  const teachers = await collectAllPages(teachersService.listPage);
  return byLabel(
    teachers.map((teacher) => ({
      value: teacher.public_id,
      label: [personName(teacher.person), teacher.employee_code]
        .filter(Boolean)
        .join(" · "),
    }))
  );
}

async function loadStudents() {
  const students = await collectAllPages(studentsService.listPage);
  return byLabel(
    students.map((student) => ({
      value: student.public_id,
      label: [personName(student.person), student.student_code]
        .filter(Boolean)
        .join(" · "),
    }))
  );
}

/**
 * Las jornadas se publican colgadas de su sede, no en un listado global; el
 * catalogo las junta recorriendo las sedes. Son pocas por definicion (una
 * matutina y una vespertina en el caso tipico), asi que el costo es despreciable
 * frente a obligar a la persona a memorizar un UUID.
 */
async function loadShifts() {
  const campuses = await collectAllPages(academicsService.listCampuses);
  const perCampus = await Promise.all(
    campuses.map((campus) =>
      collectAllPages((params) =>
        academicsService.listCampusShifts(campus.public_id, params)
      )
    )
  );

  return byLabel(
    perCampus.flat().map((shift) => ({
      value: shift.public_id,
      label: shift.campus?.name
        ? `${shift.name} · ${shift.campus.name}`
        : shift.name,
    }))
  );
}

/** Los grados tambien viven dentro de su nivel; se recorren igual que las jornadas. */
async function loadGrades() {
  const levels = await collectAllPages(academicsService.listLevels);
  const perLevel = await Promise.all(
    levels.map((level) =>
      collectAllPages((params) =>
        academicsService.listLevelGrades(level.public_id, params)
      )
    )
  );

  // Orden pedagogico (Primero, Segundo, Tercero), no alfabetico: "Primero"
  // despues de "Segundo" seria absurdo en un selector de grados.
  return perLevel
    .flat()
    .sort(
      (left, right) =>
        (left.level?.sequence ?? 0) - (right.level?.sequence ?? 0) ||
        (left.sequence ?? 0) - (right.sequence ?? 0)
    )
    .map((grade) => ({
      value: grade.public_id,
      label: grade.level?.name
        ? `${grade.name} · ${grade.level.name}`
        : grade.name,
    }));
}

async function loadSections() {
  const sections = await collectAllPages(academicsService.listSections);
  return sections.map((section) => ({
    value: section.public_id,
    label: [section.grade?.name, section.name].filter(Boolean).join(" "),
    // Se conservan para poder filtrar por ciclo y para derivar grado y jornada
    // sin una segunda peticion.
    cycleId: section.academic_cycle_id,
    gradeId: section.grade?.public_id,
    shiftId: section.shift?.public_id,
    shiftName: section.shift?.name,
  }));
}

export function useCycleCatalog(reloadToken) {
  return useCatalogOptions(loadCycles, reloadToken);
}

export function useSubjectCatalog(reloadToken) {
  return useCatalogOptions(loadSubjects, reloadToken);
}

export function useTeacherCatalog(reloadToken) {
  return useCatalogOptions(loadTeachers, reloadToken);
}

export function useStudentCatalog(reloadToken) {
  return useCatalogOptions(loadStudents, reloadToken);
}

export function useShiftCatalog(reloadToken) {
  return useCatalogOptions(loadShifts, reloadToken);
}

export function useGradeCatalog(reloadToken) {
  return useCatalogOptions(loadGrades, reloadToken);
}

/**
 * Secciones de todos los ciclos.
 *
 * Cada opcion conserva el ciclo, el grado y la jornada de su seccion: con eso
 * la pantalla puede acotar el desplegable al ciclo elegido y derivar grado y
 * jornada sin una segunda peticion ni un campo mas que llenar.
 */
export function useSectionCatalog(reloadToken) {
  const catalog = useCatalogOptions(loadSections, reloadToken);

  const options = useMemo(() => {
    // La jornada entra en la etiqueta solo cuando hay secciones homonimas en
    // jornadas distintas; si no, es ruido en cada linea del desplegable.
    const seen = new Set();
    const duplicated = new Set();
    for (const option of catalog.options) {
      if (seen.has(option.label)) {
        duplicated.add(option.label);
      }
      seen.add(option.label);
    }

    return catalog.options.map((option) =>
      duplicated.has(option.label) && option.shiftName
        ? { ...option, label: `${option.label} · ${option.shiftName}` }
        : option
    );
  }, [catalog.options]);

  return { ...catalog, options };
}

/**
 * Secciones de un ciclo.
 *
 * Sin ciclo elegido se devuelve la lista vacia a proposito: ofrecer secciones
 * de cualquier ciclo llevaria a una combinacion que el backend rechaza recien
 * al guardar, cuando el formulario ya esta lleno.
 */
export function sectionsForCycle(options, cycleId) {
  if (!cycleId) {
    return [];
  }
  return options.filter((option) => option.cycleId === cycleId);
}

/** Indice `value -> label` para pintar un id como el nombre que representa. */
export function labelIndex(options) {
  return new Map(options.map((option) => [option.value, option.label]));
}
