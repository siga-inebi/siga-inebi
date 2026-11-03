export const STUDENT_FIELDS = [
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
  {
    name: "student_code",
    label: "Codigo de estudiante",
    help: "Se genera solo. Cambielo si el expediente ya trae uno asignado.",
  },
  {
    name: "photo",
    label: "Foto tamaño cédula (295 × 354 px, máximo 5 MB)",
    type: "file",
    accept: "image/*",
  },
];

/** Estados de expediente del estudiante, tal como los expone el backend. */
export const STATUS_LABEL = {
  pre_enrolled: "Preinscrito",
  active: "Activo",
  inactive: "Inactivo",
  withdrawn: "Retirado",
  transferred: "Trasladado",
  graduated: "Graduado",
};

export const STUDENT_EDIT_FIELDS = STUDENT_FIELDS.filter(
  (field) => field.name !== "cui" && field.name !== "birth_date"
);

/** Estados de expediente del estudiante -> variante semantica de chip. */
export const STATUS_VARIANT = {
  active: "success",
  pre_enrolled: "primary",
  inactive: "neutral",
  withdrawn: "danger",
  transferred: "warning",
  graduated: "purple",
};

export function fullName(student) {
  return `${student.person.first_name} ${student.person.last_name}`.trim();
}

export function personPayload(values) {
  return Object.fromEntries(
    Object.entries({
      first_name: values.first_name,
      last_name: values.last_name,
      cui: values.cui,
      birth_date: values.birth_date,
      sex: values.sex,
      nationality: values.nationality,
      phone_number: values.phone_number,
      email: values.email,
      address: values.address,
      department: values.department,
      municipality: values.municipality,
    }).filter(([, value]) => value !== "" && value != null)
  );
}
