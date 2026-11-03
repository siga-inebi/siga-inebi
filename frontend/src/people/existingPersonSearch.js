import { peopleService } from "./peopleService.js";

const search = {
  name: "registered-people",
  fetchPage: peopleService.listPeople,
  mapResult: (person) => ({
    value: person.public_id,
    person,
    label: [
      `${person.first_name} ${person.last_name}`.trim(),
      person.institutional_identifier || person.email || person.phone_number,
    ]
      .filter(Boolean)
      .join(" · "),
  }),
};

/**
 * Datos de una persona registrada para precargar un formulario de perfil. El
 * CUI y la fecha de nacimiento quedan vacios a proposito: son sensibles y quien
 * captura debe confirmarlos, no heredarlos sin verlos.
 *
 * @param {object} person Persona tal como la devuelve el listado de personas.
 */
export function personFormValues(person) {
  return {
    first_name: person.first_name || "",
    last_name: person.last_name || "",
    cui: "",
    birth_date: "",
    sex: person.sex === "not_specified" ? "" : person.sex || "",
    nationality: person.nationality || "Guatemalteca",
    phone_number: person.phone_number || "",
    email: person.email || "",
    address: person.address || "",
    department: person.department || "",
    municipality: person.municipality || "",
  };
}

export const existingPersonField = {
  name: "person_public_id",
  label: "Persona ya registrada (opcional)",
  type: "search-select",
  help: "Busque por nombre o CUI antes de crear. Al elegirla se cargan sus datos y se completa el mismo registro; confirme el CUI y la fecha de nacimiento.",
  search,
  fills: (option) => (option?.person ? personFormValues(option.person) : null),
  span: "full",
};
