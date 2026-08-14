import { useCallback, useState } from "react";

import { CatalogueForm } from "../features/catalogue/CatalogueForm.jsx";
import { CataloguePager } from "../features/catalogue/CataloguePager.jsx";
import {
  CatalogueTable,
  StatusBadge,
} from "../features/catalogue/CatalogueTable.jsx";
import { ConfirmButton } from "../features/catalogue/ConfirmButton.jsx";
import { useCatalogue } from "../features/catalogue/useCatalogue.js";
import { peopleService } from "../services/peopleService.js";

// Person has no immutable field (unlike Subject/Level/Campus, which keep
// their code fixed after creation), so create and edit share the same set.
const PERSON_FIELDS = [
  {
    name: "first_name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Ana",
  },
  {
    name: "last_name",
    label: "Apellido",
    required: true,
    placeholder: "Ejemplo: Gomez",
  },
  {
    name: "email",
    label: "Correo electronico",
    placeholder: "correo@ejemplo.com",
  },
  {
    name: "phone_number",
    label: "Telefono",
    placeholder: "Ejemplo: 50212345678",
  },
  {
    name: "institutional_identifier",
    label: "Identificador institucional",
    help: "Codigo interno opcional.",
  },
];

const EMPTY_VALUES = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
  institutional_identifier: "",
};

const PERSON_COLUMNS = [
  {
    key: "name",
    header: "Nombre",
    render: (row) => `${row.first_name} ${row.last_name}`.trim(),
  },
  {
    key: "email",
    header: "Correo",
    render: (row) => row.email || <span className="muted">Sin registrar</span>,
  },
  {
    key: "phone_number",
    header: "Telefono",
    render: (row) =>
      row.phone_number || <span className="muted">Sin registrar</span>,
  },
  {
    key: "institutional_identifier",
    header: "Identificador",
    render: (row) =>
      row.institutional_identifier || (
        <span className="muted">Sin registrar</span>
      ),
  },
  {
    key: "is_active",
    header: "Estado",
    render: (row) => <StatusBadge active={row.is_active} />,
  },
];

/**
 * Registro base de personas institucionales (people-registry).
 *
 * Sostiene otros expedientes (cuentas, estudiantes, encargados) que ya
 * referencian una `Person` por `public_id`, pero no reemplaza ninguno de
 * ellos: no hay ningun RF que pida esta pantalla especificamente, es
 * infraestructura de apoyo para poder administrar el registro que esos
 * flujos ya dan por existente.
 */
export function PersonasPage() {
  const loadPeople = useCallback(
    (params) => peopleService.listPeople(params),
    []
  );
  const catalogue = useCatalogue(loadPeople);

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const handleCreate = async (payload) => {
    await peopleService.createPerson(payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleUpdate = async (payload) => {
    await peopleService.updatePerson(editing.person.public_id, payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleDeactivate = async (person) => {
    setActionError("");
    try {
      await peopleService.deactivatePerson(person.public_id);
      catalogue.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <section className="catalogue">
      <header className="panel catalogue-header">
        <div>
          <p className="eyebrow">Identidad institucional</p>
          <h1>Personas</h1>
          <p className="muted">
            Registro base de personas institucionales. Da soporte a cuentas,
            estudiantes y encargados; no reemplaza esos expedientes.
          </p>
        </div>
        <div className="actions">
          <button
            className="button"
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Nueva persona
          </button>
        </div>
      </header>

      {editing?.mode === "create" ? (
        <CatalogueForm
          fields={PERSON_FIELDS}
          initialValues={EMPTY_VALUES}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          submitLabel="Crear persona"
          title="Nueva persona"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          fields={PERSON_FIELDS}
          initialValues={{
            first_name: editing.person.first_name,
            last_name: editing.person.last_name,
            email: editing.person.email || "",
            phone_number: editing.person.phone_number || "",
            institutional_identifier:
              editing.person.institutional_identifier || "",
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.person.first_name} ${editing.person.last_name}`}
        />
      ) : null}

      <div className="panel">
        <div className="catalogue-toolbar">
          <h2>Personas registradas</h2>
          <label className="field field-inline">
            <input
              checked={catalogue.includeInactive}
              onChange={(event) =>
                catalogue.setIncludeInactive(event.target.checked)
              }
              type="checkbox"
            />
            <span>Mostrar desactivadas</span>
          </label>
        </div>

        {catalogue.error ? (
          <div className="message message-error" role="alert">
            {catalogue.error}
          </div>
        ) : null}
        {actionError ? (
          <div className="message message-error" role="alert">
            {actionError}
          </div>
        ) : null}

        <CatalogueTable
          caption="Personas institucionales"
          columns={PERSON_COLUMNS}
          emptyMessage="Todavia no hay personas registradas."
          loading={catalogue.loading}
          renderActions={(person) => (
            <>
              <button
                className="button secondary button-small"
                onClick={() => setEditing({ mode: "edit", person })}
                type="button"
              >
                Editar
              </button>
              {person.is_active ? (
                <ConfirmButton
                  confirmLabel="Si, desactivar"
                  label="Desactivar"
                  onConfirm={() => handleDeactivate(person)}
                  question={`Desactivar a ${person.first_name} ${person.last_name}?`}
                />
              ) : null}
            </>
          )}
          rowKey={(person) => person.public_id}
          rows={catalogue.items}
        />

        <CataloguePager
          count={catalogue.count}
          onChange={catalogue.goToPage}
          page={catalogue.page}
          pageCount={catalogue.pageCount}
        />
      </div>
    </section>
  );
}
