import { fireEvent, screen } from "@testing-library/react";

import { selectOption } from "./selectOption.jsx";

export const visibleInstitutionalPerson = {
  sex: "female",
  nationality: "Guatemalteca",
  phone_number: "555-0199",
  address: "1a Calle 2-34 Zona 1",
  department: "Guatemala",
  municipality: "Guatemala",
};

export const institutionalPerson = {
  cui: "1234567890123",
  birth_date: "2000-03-15",
  ...visibleInstitutionalPerson,
};

export async function fillInstitutionalPerson(user) {
  fireEvent.change(screen.getByLabelText(/^CUI/), {
    target: { value: institutionalPerson.cui },
  });
  fireEvent.change(screen.getByLabelText(/^Fecha de nacimiento/), {
    target: { value: institutionalPerson.birth_date },
  });
  await selectOption(user, /^Sexo/, "Femenino");
  fireEvent.change(screen.getByLabelText(/^Teléfono/), {
    target: { value: institutionalPerson.phone_number },
  });
  fireEvent.change(screen.getByLabelText(/^Dirección/), {
    target: { value: institutionalPerson.address },
  });
  fireEvent.change(screen.getByLabelText(/^Departamento/), {
    target: { value: institutionalPerson.department },
  });
  fireEvent.change(screen.getByLabelText(/^Municipio/), {
    target: { value: institutionalPerson.municipality },
  });
}
