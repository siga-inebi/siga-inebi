// Fixture sintetica para "Docentes y Administrativos" mientras el backend
// no expone un endpoint REST de personal. Hoy no existe un modelo dedicado
// de docente/staff: un "docente" es solo `people.Person` referenciado desde
// `academics.TeachingAssignment.teacher`. Campos respaldados por modelo:
// first_name/last_name/phone_number (people.Person). Los siguientes campos
// vienen de los mockups pero AUN NO EXISTEN en ningun modelo del backend:
// specialty, position, employee_code, appointment_date. Se incluyen como
// placeholder explicito (decision registrada al construir esta capa de
// mocks); backend debera modelarlos (posiblemente un nuevo `StaffProfile`
// o similar) antes de que T10 reemplace este mock por el servicio real.
//
// El titulo profesional ("Prof.", "Licda.", "Ing.") que se ve en los
// mockups no tiene campo propio — se guarda como parte de `first_name`
// porque `people.Person` no modela un campo de titulo/prefijo separado.

export const POSITION_OPTIONS = [
  "Docente Titulado",
  "Docente Interino",
  "Orientador/a",
  "Administrativo",
];

export const teachers = [
  {
    id: 1,
    first_name: "Prof. Marvin Estuardo",
    last_name: "Lopez Cifuentes",
    specialty: "Electricidad Industrial",
    position: "Docente Titulado",
    employee_code: "EMP-0142",
    phone_number: "5566-1234",
    appointment_date: "2019-01-15",
  },
  {
    id: 2,
    first_name: "Licda. Elena Marisol",
    last_name: "Perez Ramirez",
    specialty: "Matematica",
    position: "Docente Titulado",
    employee_code: "EMP-0098",
    phone_number: "4477-2211",
    appointment_date: "2016-02-01",
  },
  {
    id: 3,
    first_name: "Ing. Pablo Cesar",
    last_name: "Morales Tzoc",
    specialty: "Mecanica Industrial",
    position: "Docente Interino",
    employee_code: "EMP-0201",
    phone_number: "3322-8899",
    appointment_date: "2025-01-20",
  },
  {
    id: 4,
    first_name: "Licda. Karen Yesenia",
    last_name: "Vasquez Us",
    specialty: "Orientacion Educativa",
    position: "Orientador/a",
    employee_code: "EMP-0176",
    phone_number: "5588-4433",
    appointment_date: "2021-07-05",
  },
  {
    id: 5,
    first_name: "Prof. Wilson Antonio",
    last_name: "Xitumul Coy",
    specialty: "Dibujo Tecnico",
    position: "Docente Titulado",
    employee_code: "EMP-0067",
    phone_number: "4411-9922",
    appointment_date: "2014-01-10",
  },
  {
    id: 6,
    first_name: "Licda. Brenda Sucely",
    last_name: "Garcia Morales",
    specialty: "Comunicacion y Lenguaje",
    position: "Docente Titulado",
    employee_code: "EMP-0113",
    phone_number: "5599-3344",
    appointment_date: "2018-01-08",
  },
  {
    id: 7,
    first_name: "Sr. Byron Ottoniel",
    last_name: "Chavez Us",
    specialty: "Administracion",
    position: "Administrativo",
    employee_code: "EMP-0055",
    phone_number: "4433-2200",
    appointment_date: "2013-03-01",
  },
  {
    id: 8,
    first_name: "Prof. Heidy Roxana",
    last_name: "Sac Tzul",
    specialty: "Ciencias Naturales",
    position: "Docente Interino",
    employee_code: "EMP-0219",
    phone_number: "3311-7788",
    appointment_date: "2025-07-14",
  },
];
