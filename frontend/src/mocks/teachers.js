// `POSITION_OPTIONS` mirrors `backend.apps.teachers.models.Teacher.Position`
// choices exactly (values used verbatim as both the Django choice value and
// label), so this list drives both the "Puesto" select and filter dropdown
// without needing to be kept in sync separately. DocentesPage now reads real
// data from `teachersService` (backed by `/api/v1/teachers/`).

export const POSITION_OPTIONS = [
  "Docente Titulado",
  "Docente Interino",
  "Orientador/a",
  "Administrativo",
];
