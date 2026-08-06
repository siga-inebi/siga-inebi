import { useCallback, useState } from "react";

import { CatalogueForm } from "../catalogue/CatalogueForm.jsx";
import { CataloguePager } from "../catalogue/CataloguePager.jsx";
import { CatalogueTable, StatusBadge } from "../catalogue/CatalogueTable.jsx";
import { ConfirmButton } from "../catalogue/ConfirmButton.jsx";
import { useCatalogue } from "../catalogue/useCatalogue.js";
import { studentsService } from "../../services/studentsService.js";

const CONTACT_FIELDS = [
  { name: "name", label: "Nombre", required: true },
  { name: "phone_number", label: "Telefono", required: true },
  { name: "relationship_label", label: "Parentesco", required: true },
];

const CONTACT_COLUMNS = [
  { key: "name", header: "Nombre", render: (row) => row.name },
  {
    key: "phone_number",
    header: "Telefono",
    render: (row) => row.phone_number,
  },
  {
    key: "relationship_label",
    header: "Parentesco",
    render: (row) => row.relationship_label,
  },
  {
    key: "is_active",
    header: "Estado",
    render: (row) => <StatusBadge active={row.is_active} />,
  },
];

/**
 * Contactos de emergencia de un estudiante (RF-EXP-005).
 *
 * Recibe el estudiante por prop en vez de leerlo de una ruta propia --
 * mismo contrato que `CampusShiftsPanel` en `pages/CampusesPage.jsx` -- para
 * poder montarse dentro de cualquier pagina que ya tenga el estudiante
 * resuelto. `onChanged` es opcional: lo llama un padre que necesite
 * refrescar, por ejemplo, un contador de contactos en su propio listado.
 */
export function EmergencyContactsPanel({ student, onChanged }) {
  const loadContacts = useCallback(
    (params) =>
      studentsService.listEmergencyContacts(student.public_id, params),
    [student.public_id]
  );
  const catalogue = useCatalogue(loadContacts);

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const notify = () => {
    catalogue.refresh();
    onChanged?.();
  };

  const handleCreate = async (payload) => {
    await studentsService.createEmergencyContact(student.public_id, payload);
    setEditing(null);
    notify();
  };

  const handleUpdate = async (payload) => {
    await studentsService.updateEmergencyContact(
      editing.contact.public_id,
      payload
    );
    setEditing(null);
    notify();
  };

  const handleDeactivate = async (contact) => {
    setActionError("");
    try {
      await studentsService.deactivateEmergencyContact(contact.public_id);
      notify();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <div className="panel">
      <div className="catalogue-toolbar">
        <h2>Contactos de emergencia</h2>
        <div className="actions">
          <label className="field field-inline">
            <input
              checked={catalogue.includeInactive}
              onChange={(event) =>
                catalogue.setIncludeInactive(event.target.checked)
              }
              type="checkbox"
            />
            <span>Mostrar quitados</span>
          </label>
          <button
            className="button secondary button-small"
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Nuevo contacto
          </button>
        </div>
      </div>

      {editing?.mode === "create" ? (
        <CatalogueForm
          fields={CONTACT_FIELDS}
          initialValues={{ name: "", phone_number: "", relationship_label: "" }}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          submitLabel="Agregar contacto"
          title="Nuevo contacto de emergencia"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          fields={CONTACT_FIELDS}
          initialValues={{
            name: editing.contact.name,
            phone_number: editing.contact.phone_number,
            relationship_label: editing.contact.relationship_label,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.contact.name}`}
        />
      ) : null}

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
        caption="Contactos de emergencia del estudiante"
        columns={CONTACT_COLUMNS}
        emptyMessage="Este estudiante todavia no tiene contactos de emergencia."
        loading={catalogue.loading}
        renderActions={(contact) => (
          <>
            <button
              className="button secondary button-small"
              onClick={() => setEditing({ mode: "edit", contact })}
              type="button"
            >
              Editar
            </button>
            {contact.is_active ? (
              <ConfirmButton
                confirmLabel="Si, quitar"
                label="Quitar"
                onConfirm={() => handleDeactivate(contact)}
                question={`Quitar a ${contact.name} de los contactos?`}
              />
            ) : null}
          </>
        )}
        rowKey={(contact) => contact.public_id}
        rows={catalogue.items}
      />

      <CataloguePager
        count={catalogue.count}
        onChange={catalogue.goToPage}
        page={catalogue.page}
        pageCount={catalogue.pageCount}
      />
    </div>
  );
}
