// Fixture sintetica para "Padres de familia / Encargados" mientras el
// backend no expone un endpoint REST para `students.Guardian`. Campos
// respaldados por modelo: first_name/last_name/phone_number
// (people.Person, via Guardian.person). El siguiente campo viene del
// mockup pero AUN NO EXISTE en ningun modelo del backend: occupation
// (`students.Guardian` no tiene mas campos que el `Person` compartido).
// Se incluye como placeholder explicito (decision registrada al construir
// esta capa de mocks); backend debera sumarlo antes de que T10 reemplace
// este mock por el servicio real.
//
// `assigned_students` SI esta respaldado por un modelo real
// (`students.StudentGuardianRelation`: student, relationship_label,
// is_primary). Alumnos ahora usa datos reales via `studentsService`
// (ver plan de integracion), asi que este mock ya no importa
// `./students.js` — mantiene su propia referencia minima de alumnos
// para no acoplar la pantalla de Padres (aun mockeada) a la forma real
// de la API de Alumnos.

const STUDENT_REFS = [
  { id: 1, first_name: "Maria Jose", last_name: "Lopez Garcia", section: { grade: "3ro", name: "A" } },
  { id: 2, first_name: "Carlos Enrique", last_name: "Ramirez Perez", section: { grade: "2do", name: "B" } },
  { id: 3, first_name: "Ana Lucia", last_name: "Morales Tzul", section: { grade: "3ro", name: "B" } },
  { id: 4, first_name: "Jose Manuel", last_name: "Vasquez Coyoy", section: { grade: "3ro", name: "A" } },
  { id: 5, first_name: "Gabriela Alejandra", last_name: "Xitumul Sac", section: { grade: "1ro", name: "C" } },
  { id: 6, first_name: "Diego Alejandro", last_name: "Us Batz", section: { grade: "2do", name: "A" } },
  { id: 7, first_name: "Yesenia Del Carmen", last_name: "Tzoc Ramirez", section: { grade: "1ro", name: "A" } },
  { id: 8, first_name: "Luis Fernando", last_name: "Coy Xitumul", section: { grade: "2do", name: "C" } },
];

function studentRef(id, relationship_label, is_primary = true) {
  const student = STUDENT_REFS.find((item) => item.id === id);
  return {
    student_id: student.id,
    full_name: `${student.first_name} ${student.last_name}`,
    section: student.section,
    relationship_label,
    is_primary,
  };
}

export const guardians = [
  {
    id: 1,
    first_name: "Rosa Elvira",
    last_name: "Garcia Mendez",
    occupation: "Comerciante",
    phone_number: "4512-7890",
    assigned_students: [studentRef(1, "Madre")],
  },
  {
    id: 2,
    first_name: "Marco Tulio",
    last_name: "Ramirez Us",
    occupation: "Agricultor",
    phone_number: "3398-1122",
    assigned_students: [studentRef(2, "Padre")],
  },
  {
    id: 3,
    first_name: "Silvia Patricia",
    last_name: "Tzul Morales",
    occupation: "Maestra",
    phone_number: "5544-9988",
    assigned_students: [studentRef(3, "Madre"), studentRef(5, "Tutora", false)],
  },
  {
    id: 4,
    first_name: "Edwin Fernando",
    last_name: "Vasquez Coy",
    occupation: "Piloto automotriz",
    phone_number: "4021-6677",
    assigned_students: [studentRef(4, "Padre")],
  },
  {
    id: 5,
    first_name: "Lesbia Marisol",
    last_name: "Sac Xitumul",
    occupation: "Comerciante",
    phone_number: "3311-5566",
    assigned_students: [studentRef(5, "Madre")],
  },
  {
    id: 6,
    first_name: "Herbert Noe",
    last_name: "Us Batz",
    occupation: "Albanil",
    phone_number: "3021-4488",
    assigned_students: [studentRef(6, "Padre")],
  },
  {
    id: 7,
    first_name: "Maria Fernanda",
    last_name: "Tzoc Ramirez",
    occupation: "Enfermera",
    phone_number: "5566-7799",
    assigned_students: [studentRef(7, "Madre")],
  },
  {
    id: 8,
    first_name: "Cristian Otoniel",
    last_name: "Coy Xitumul",
    occupation: "Sastre",
    phone_number: "4499-2233",
    assigned_students: [studentRef(8, "Padre")],
  },
];
