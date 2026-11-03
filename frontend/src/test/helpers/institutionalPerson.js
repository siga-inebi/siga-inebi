import { fireEvent, screen, within } from "@testing-library/react";

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

export const editedInstitutionalPerson = {
  sex: "male",
  nationality: "Salvadoreña",
  address: "Calle de prueba 42",
  department: "Quetzaltenango",
  municipality: "Salcaja",
};

export async function editInstitutionalPerson(user) {
  await selectOption(user, /^Sexo/, "Masculino");
  for (const [label, name] of [
    [/^Nacionalidad/, "nationality"],
    [/^Dirección/, "address"],
    [/^Departamento/, "department"],
    [/^Municipio/, "municipality"],
  ]) {
    fireEvent.change(screen.getByLabelText(label), {
      target: { value: editedInstitutionalPerson[name] },
    });
  }
}

/**
 * Llena los datos de persona institucional del formulario de alta.
 *
 * Con `container` (el dialogo del formulario) las etiquetas se buscan solo ahi:
 * `getByLabelText` sobre `screen` recorre tambien la tabla de la pantalla y
 * cuesta diez veces mas por campo, lo que bajo la suite completa en paralelo
 * empuja las pruebas de alta hacia el limite de tiempo.
 *
 * @param {object} user  Instancia de `userEvent.setup()`.
 * @param {HTMLElement} [container] Ambito donde buscar los campos.
 */
export async function fillInstitutionalPerson(user, container) {
  const scope = container ? within(container) : screen;
  const fill = (label, value) =>
    fireEvent.change(scope.getByLabelText(label), { target: { value } });
  fill(/^CUI/, institutionalPerson.cui);
  fill(/^Fecha de nacimiento/, institutionalPerson.birth_date);
  await selectOption(user, /^Sexo/, "Femenino", container);
  fill(/^Teléfono/, institutionalPerson.phone_number);
  fill(/^Dirección/, institutionalPerson.address);
  fill(/^Departamento/, institutionalPerson.department);
  fill(/^Municipio/, institutionalPerson.municipality);
}
