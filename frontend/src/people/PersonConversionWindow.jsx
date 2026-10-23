import { useQuery } from "@tanstack/react-query";

import { guardiansService } from "@guardians/guardiansService.js";
import { studentsService } from "@students/studentsService.js";
import { teachersService } from "@teachers/teachersService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { personFormValues } from "@people/existingPersonSearch.js";

const PERSON_FIELDS = [
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
];

const PERSON_KEYS = PERSON_FIELDS.map((field) => field.name);
const PROFILE_LABELS = {
  student: "estudiante",
  teacher: "docente",
  guardian: "encargado",
};

export function PersonConversionWindow({
  canCreateStudent = true,
  person,
  onCancel,
  onConverted,
}) {
  const positions = useQuery({
    queryKey: [...queryKeys.teachers.all, "positions"],
    queryFn: teachersService.listPositions,
  });
  const options = Object.entries(PROFILE_LABELS)
    .filter(
      ([key]) =>
        !person.profiles?.[key] && (key !== "student" || canCreateStudent)
    )
    .map(([value, label]) => ({ value, label: `Convertir en ${label}` }));

  const fields = (values) => [
    {
      name: "profile_type",
      label: "Nuevo perfil",
      type: "select",
      required: true,
      options,
    },
    ...PERSON_FIELDS,
    ...(values.profile_type === "teacher"
      ? [
          { name: "specialty", label: "Especialidad", required: true },
          {
            name: "position",
            label: "Puesto",
            type: "select",
            required: true,
            options: positions.data ?? [],
            loading: positions.isPending,
            optionsError: positions.isError
              ? "No se pudo consultar el catálogo de puestos."
              : "",
          },
          {
            name: "appointment_date",
            label: "Fecha de nombramiento",
            type: "date",
          },
        ]
      : []),
  ];

  const submit = async (values) => {
    const personData = Object.fromEntries(
      PERSON_KEYS.map((name) => [name, values[name]]).filter(
        ([, value]) => value !== ""
      )
    );
    const payload = { person_public_id: person.public_id, person: personData };
    if (values.profile_type === "student") {
      await studentsService.create(payload);
    } else if (values.profile_type === "teacher") {
      await teachersService.create({
        ...payload,
        specialty: values.specialty,
        position: values.position,
        appointment_date: values.appointment_date || null,
      });
    } else {
      await guardiansService.create(payload);
    }
    onConverted();
  };

  return (
    <EntityFormWindow
      description="Complete los datos institucionales. Se conservará la misma persona y su cuenta; no se creará un registro duplicado."
      fields={fields}
      initialValues={{
        profile_type: options[0]?.value ?? "",
        ...personFormValues(person),
        specialty: "",
        position: "",
        appointment_date: "",
      }}
      onCancel={onCancel}
      onSubmit={submit}
      open
      submitLabel="Crear perfil"
      title={`Convertir ${person.first_name} ${person.last_name}`}
    />
  );
}
