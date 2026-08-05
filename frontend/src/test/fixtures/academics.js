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
