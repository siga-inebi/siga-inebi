import { peopleService } from "./peopleService.js";

const search = {
  name: "registered-people",
  fetchPage: peopleService.listPeople,
  mapResult: (person) => ({
    value: person.public_id,
    label: [
      `${person.first_name} ${person.last_name}`.trim(),
      person.institutional_identifier || person.email || person.phone_number,
    ]
      .filter(Boolean)
      .join(" · "),
  }),
};

export const existingPersonField = {
  name: "person_public_id",
  label: "Persona ya registrada (opcional)",
  type: "search-select",
  help: "Busque por nombre o CUI antes de crear. Al elegirla, se completa el mismo registro; los datos sensibles deben confirmarse.",
  search,
  span: "full",
};
