/** Envuelve resultados con la forma paginada que devuelve DRF. */
export function paginated(results, { count, next = null } = {}) {
  return {
    count: count ?? results.length,
    next,
    previous: null,
    results,
  };
}

export const centralCampus = {
  public_id: "campus-central",
  name: "Sede Central",
  code: "CENTRAL",
  address: "Zona 1, Salcaja",
  is_main: true,
  is_active: true,
  shift_count: 2,
};

export const annexCampus = {
  public_id: "campus-anexo",
  name: "Sede Anexo",
  code: "ANEXO",
  address: "",
  is_main: false,
  is_active: false,
  shift_count: 0,
};

export const morningShift = {
  public_id: "shift-mat",
  name: "Matutina",
  code: "MAT",
  is_active: true,
  campus: { public_id: centralCampus.public_id, name: "Sede Central" },
};

export const basicLevel = {
  public_id: "level-basico",
  name: "Basico",
  code: "BAS",
  sequence: 3,
  is_active: true,
  grade_count: 3,
  subject_count: 1,
};

export const firstGrade = {
  public_id: "grade-bas1",
  name: "Primero Basico",
  code: "BAS1",
  sequence: 1,
  is_active: true,
  level: { public_id: basicLevel.public_id, name: "Basico" },
};

export const mathSubject = {
  public_id: "subject-mat",
  name: "Matematica",
  code: "MAT",
  is_active: true,
  levels: [{ public_id: basicLevel.public_id, name: "Basico" }],
};

export const artSubject = {
  public_id: "subject-art",
  name: "Artes Plasticas",
  code: "ART",
  is_active: true,
  levels: [],
};

// --------------------------------------------------------------------------- //
// estructura del ciclo
// --------------------------------------------------------------------------- //

export const draftCycle = {
  public_id: "cycle-2027",
  name: "Ciclo 2027",
  starts_on: "2027-01-15",
  ends_on: "2027-11-30",
  status: "draft",
  is_active: true,
  offering_count: 0,
};

export const activeCycle = {
  public_id: "cycle-2026",
  name: "Ciclo 2026",
  starts_on: "2026-01-15",
  ends_on: "2026-11-30",
  status: "active",
  is_active: true,
  offering_count: 1,
};

export const closedCycle = {
  public_id: "cycle-2025",
  name: "Ciclo 2025",
  starts_on: "2025-01-15",
  ends_on: "2025-11-30",
  status: "closed",
  is_active: true,
  offering_count: 3,
};

const cycleRef = {
  public_id: activeCycle.public_id,
  name: activeCycle.name,
  status: activeCycle.status,
};

const gradeRef = {
  public_id: firstGrade.public_id,
  name: firstGrade.name,
  code: firstGrade.code,
  sequence: 1,
};

export const basicOffering = {
  public_id: "offering-bas1-mat",
  academic_cycle: cycleRef,
  grade: gradeRef,
  shift: { public_id: morningShift.public_id, name: "Matutina", code: "MAT" },
  campus: {
    public_id: centralCampus.public_id,
    name: "Sede Central",
    code: "CENTRAL",
  },
  is_active: true,
  section_count: 1,
  enrolment_count: 12,
};

export const sectionA = {
  public_id: "section-a",
  name: "A",
  capacity: 35,
  is_active: true,
  offering: {
    public_id: basicOffering.public_id,
    academic_cycle: cycleRef,
    grade: gradeRef,
    shift: basicOffering.shift,
  },
  enrolment_count: 12,
  available_seats: 23,
  assignment_count: 1,
};

export const uncappedSection = {
  ...sectionA,
  public_id: "section-b",
  name: "B",
  capacity: 0,
  enrolment_count: 0,
  available_seats: null,
  assignment_count: 0,
};

export const mathPlanEntry = {
  public_id: "plan-bas1-mat",
  academic_cycle: cycleRef,
  grade: gradeRef,
  subject: {
    public_id: mathSubject.public_id,
    name: "Matematica",
    code: "MAT",
  },
  is_required: true,
};

export const artPlanEntry = {
  public_id: "plan-bas1-art",
  academic_cycle: cycleRef,
  grade: gradeRef,
  subject: {
    public_id: artSubject.public_id,
    name: "Artes Plasticas",
    code: "ART",
  },
  is_required: false,
};

export const openAssignment = {
  public_id: "assignment-mat",
  academic_cycle: cycleRef,
  subject: mathPlanEntry.subject,
  teacher: { public_id: "person-ana", full_name: "Ana Lopez" },
  starts_on: "2026-01-20",
  ends_on: null,
  is_open: true,
};

export const closedAssignment = {
  ...openAssignment,
  public_id: "assignment-mat-old",
  teacher: { public_id: "person-luis", full_name: "Luis Perez" },
  ends_on: "2026-01-19",
  is_open: false,
};

export const anaPerson = {
  public_id: "person-ana",
  first_name: "Ana",
  last_name: "Lopez",
  is_active: true,
};

export const inactivePerson = {
  public_id: "person-baja",
  first_name: "Persona",
  last_name: "Inactiva",
  is_active: false,
};

export const mathLink = {
  public_id: "link-bas-mat",
  level: { public_id: basicLevel.public_id, name: "Basico" },
  subject: {
    public_id: mathSubject.public_id,
    name: "Matematica",
    code: "MAT",
  },
  is_required: true,
  weekly_hours: 5,
};
