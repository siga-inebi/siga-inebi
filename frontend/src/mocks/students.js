// Fixture sintetica para "Alumnos" mientras `apps/students` no expone un
// endpoint REST real (ver config/api/urls.py). Campos respaldados por un
// modelo Django hoy: first_name/last_name/phone_number (people.Person),
// student_code/status (students.Student). Los siguientes campos vienen de
// los mockups pero AUN NO EXISTEN en ningun modelo del backend: gender,
// birth_date, cui, age, clave. Se incluyen como placeholder explicito para
// no bloquear T5 (decision registrada al construir esta capa de mocks);
// backend debera sumarlos a `students.Student`/`people.Person` antes de que
// T10 reemplace este mock por el servicio real, o el equipo debera acordar
// quitarlos de la pantalla.
//
// `section` compone grado + letra de seccion (backend guarda `Grade.name` y
// `Section.name` por separado, sin una etiqueta combinada). El estilo corto
// "1ro"/"2do"/"3ro" sigue el mockup; `seed_demo_data` hoy siembra grados
// como "Basico 1/2/3" con secciones "A"/"B" — la etiqueta cambiara cuando
// se integre el endpoint real.
//
// Mas de fondo: hoy NO existe ninguna relacion Student->Section en el
// backend (`students.Student` no tiene FK a `academics.Section`) — esa
// asignacion es matricula/enrollment-lifecycle, un dominio explicitamente
// fuera de esta entrega (ver plan seccion 3: "Nada de matricula... todavia,
// esos dependen de reglas de negocio que aun no estan definidas
// backend-side"). Por eso la pantalla de Alumnos NO ofrece un formulario
// para asignar seccion al crear un alumno: seria anticipar una regla de
// negocio de matricula que no le corresponde a frontend inventar.

const GRADES = ["1ro", "2do", "3ro"];
const SECTION_LETTERS = ["A", "B", "C"];

export const SECTION_OPTIONS = GRADES.flatMap((grade) =>
  SECTION_LETTERS.map((letter) => `${grade} "${letter}"`)
);

export const students = [
  {
    id: 1,
    first_name: "Maria Jose",
    last_name: "Lopez Garcia",
    gender: "Femenino",
    student_code: "EST-2026-014",
    status: "active",
    section: { grade: "3ro", name: "A" },
    birth_date: "2010-03-14",
    cui: "2451 23456 0101",
    age: 16,
    clave: "01",
  },
  {
    id: 2,
    first_name: "Carlos Enrique",
    last_name: "Ramirez Perez",
    gender: "Masculino",
    student_code: "EST-2026-015",
    status: "active",
    section: { grade: "2do", name: "B" },
    birth_date: "2011-06-02",
    cui: "2451 23457 0102",
    age: 15,
    clave: "02",
  },
  {
    id: 3,
    first_name: "Ana Lucia",
    last_name: "Morales Tzul",
    gender: "Femenino",
    student_code: "EST-2026-016",
    status: "active",
    section: { grade: "3ro", name: "B" },
    birth_date: "2010-09-21",
    cui: "2451 23458 0103",
    age: 16,
    clave: "03",
  },
  {
    id: 4,
    first_name: "Jose Manuel",
    last_name: "Vasquez Coyoy",
    gender: "Masculino",
    student_code: "EST-2026-017",
    status: "active",
    section: { grade: "3ro", name: "A" },
    birth_date: "2010-01-30",
    cui: "2451 23459 0104",
    age: 16,
    clave: "04",
  },
  {
    id: 5,
    first_name: "Gabriela Alejandra",
    last_name: "Xitumul Sac",
    gender: "Femenino",
    student_code: "EST-2026-018",
    status: "active",
    section: { grade: "1ro", name: "C" },
    birth_date: "2012-05-11",
    cui: "2451 23460 0105",
    age: 14,
    clave: "05",
  },
  {
    id: 6,
    first_name: "Diego Alejandro",
    last_name: "Us Batz",
    gender: "Masculino",
    student_code: "EST-2026-019",
    status: "active",
    section: { grade: "2do", name: "A" },
    birth_date: "2011-11-08",
    cui: "2451 23461 0106",
    age: 15,
    clave: "06",
  },
  {
    id: 7,
    first_name: "Yesenia Del Carmen",
    last_name: "Tzoc Ramirez",
    gender: "Femenino",
    student_code: "EST-2026-020",
    status: "pre_enrolled",
    section: { grade: "1ro", name: "A" },
    birth_date: "2012-02-17",
    cui: "2451 23462 0107",
    age: 14,
    clave: "07",
  },
  {
    id: 8,
    first_name: "Luis Fernando",
    last_name: "Coy Xitumul",
    gender: "Masculino",
    student_code: "EST-2026-021",
    status: "active",
    section: { grade: "2do", name: "C" },
    birth_date: "2011-08-25",
    cui: "2451 23463 0108",
    age: 15,
    clave: "08",
  },
];
