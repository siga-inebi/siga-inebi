export const TEACHER_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  {
    name: "cui",
    label: "CUI",
    required: true,
    help: "13 dígitos, sin guiones.",
  },
  {
    name: "birth_date",
    label: "Fecha de nacimiento",
    type: "date",
    required: true,
  },
  {
    name: "sex",
    label: "Sexo",
    type: "select",
    required: true,
    options: [
      { value: "female", label: "Femenino" },
      { value: "male", label: "Masculino" },
    ],
  },
  { name: "nationality", label: "Nacionalidad", required: true },
  { name: "phone_number", label: "Teléfono", type: "tel", required: true },
  { name: "email", label: "Correo", type: "email" },
  { name: "address", label: "Dirección", required: true, span: "full" },
  { name: "department", label: "Departamento", required: true },
  { name: "municipality", label: "Municipio", required: true },
  { name: "specialty", label: "Especialidad", required: true },
  {
    name: "position",
    label: "Puesto",
    type: "select",
    options: [],
    required: true,
  },
  {
    name: "appointment_date",
    label: "Fecha de nombramiento (opcional)",
    type: "date",
  },
  {
    name: "employee_code",
    label: "Código de empleado",
    help: "Se genera automáticamente. Cámbielo si ya figura en contratos o planilla.",
  },
  { name: "photo", label: "Foto (opcional)", type: "file", accept: "image/*" },
];

// CUI y fecha de nacimiento no se corrigen despues del alta: identifican a la
// persona ante otras instituciones.
export const TEACHER_EDIT_FIELDS = TEACHER_FIELDS.filter(
  (field) => field.name !== "cui" && field.name !== "birth_date"
);

export function fullName(teacher) {
  return `${teacher.person.first_name} ${teacher.person.last_name}`.trim();
}

const personPayload = (values) => ({
  ...Object.fromEntries(
    Object.entries({
      first_name: values.first_name,
      last_name: values.last_name,
      cui: values.cui,
      birth_date: values.birth_date,
      sex: values.sex,
      nationality: values.nationality,
      email: values.email,
      phone_number: values.phone_number,
      address: values.address,
      department: values.department,
      municipality: values.municipality,
    }).filter(([, value]) => value !== "" && value != null)
  ),
});

/** Cuerpo comun de alta y edicion del perfil docente. */
export const buildTeacherPayload = (values) => ({
  ...(values.person_public_id
    ? { person_public_id: values.person_public_id }
    : {}),
  person: personPayload(values),
  employee_code: values.employee_code,
  specialty: values.specialty,
  position: values.position,
  appointment_date: values.appointment_date || null,
  photo: values.photo,
});

export const EMPTY_TEACHER = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
  cui: "",
  birth_date: "",
  sex: "",
  nationality: "Guatemalteca",
  address: "",
  department: "",
  municipality: "",
  specialty: "",
  position: "",
  appointment_date: "",
  employee_code: "",
  photo: null,
};
