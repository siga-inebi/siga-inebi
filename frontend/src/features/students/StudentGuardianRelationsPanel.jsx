import { useCallback, useState } from "react";

import { CatalogueForm } from "../catalogue/CatalogueForm.jsx";
import { CataloguePager } from "../catalogue/CataloguePager.jsx";
import { CatalogueTable } from "../catalogue/CatalogueTable.jsx";
import { ConfirmButton } from "../catalogue/ConfirmButton.jsx";
import { useCatalogue } from "../catalogue/useCatalogue.js";
import { studentsService } from "../../services/studentsService.js";
import { useGuardianOptions } from "./useGuardianOptions.js";

const RELATION_COLUMNS = [
  {
    key: "guardian",
    header: "Encargado",
    render: (row) =>
      `${row.guardian.person.first_name} ${row.guardian.person.last_name}`,
  },
  {
    key: "relationship_label",
    header: "Parentesco",
    render: (row) => row.relationship_label,
  },
  {
    key: "is_primary",
    header: "Principal",
    render: (row) => (row.is_primary ? "Si" : "No"),
  },
  {
    key: "status",
    header: "Estado",
    render: (row) => (row.ends_at ? `Finalizada (${row.ends_at})` : "Activa"),
  },
];

/**
 * Relacion estudiante-encargado (RF-EXP-004).
 *
 * Mismo contrato por prop que `EmergencyContactsPanel`. El selector de
 * "vincular encargado existente" sigue el patron de `LevelSubjectsPanel`
 * (opciones disponibles + metadata propia del vinculo), pero a diferencia de
 * ese caso el historial de relaciones ya finalizadas si se puede consultar
 * (`ends_at` cierra la relacion, no la borra), asi que el toggle de
 * "incluir inactivas" queda habilitado.
 */
export function StudentGuardianRelationsPanel({ student, onChanged }) {
  const loadRelations = useCallback(
    (params) =>
      studentsService.listStudentGuardianRelations(student.public_id, params),
    [student.public_id]
  );
  const catalogue = useCatalogue(loadRelations);
  const { guardians, error: guardiansError } = useGuardianOptions();

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  // Solo una relacion abierta bloquea re-vincular al mismo guardian; una que
  // ya finalizo (ends_at) puede volver a vincularse (RF-EXP-004).
  const linkedIds = new Set(
    catalogue.items
      .filter((relation) => !relation.ends_at)
      .map((relation) => relation.guardian.public_id)
  );
  const available = guardians.filter(
    (guardian) => !linkedIds.has(guardian.public_id)
  );

  const notify = () => {
    catalogue.refresh();
    onChanged?.();
  };

  const handleCreate = async (payload) => {
    await studentsService.createStudentGuardianRelation(
      student.public_id,
      payload
    );
    setEditing(null);
    notify();
  };

  const handleUpdate = async (payload) => {
    await studentsService.updateStudentGuardianRelation(
      editing.relation.public_id,
      payload
    );
    setEditing(null);
    notify();
  };

  const handleEnd = async (relation) => {
    setActionError("");
    try {
      await studentsService.endStudentGuardianRelation(relation.public_id);
      notify();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <div className="panel">
      <div className="catalogue-toolbar">
        <h2>Relacion con encargados</h2>
        <div className="actions">
          <label className="field field-inline">
            <input
              checked={catalogue.includeInactive}
              onChange={(event) =>
                catalogue.setIncludeInactive(event.target.checked)
              }
              type="checkbox"
            />
            <span>Mostrar finalizadas</span>
          </label>
          <button
            className="button secondary button-small"
            disabled={!available.length}
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Vincular encargado
          </button>
        </div>
      </div>

      {!available.length && !editing ? (
        <p className="muted">
          No hay encargados activos disponibles para vincular.
        </p>
      ) : null}

      {editing?.mode === "create" ? (
        <CatalogueForm
          fields={[
            {
              name: "guardian_id",
              label: "Encargado",
              type: "select",
              required: true,
              options: available.map((guardian) => ({
                value: guardian.public_id,
                label: `${guardian.person.first_name} ${guardian.person.last_name}`,
              })),
            },
            {
              name: "relationship_label",
              label: "Parentesco",
              required: true,
              placeholder: "Ejemplo: Madre",
            },
            {
              name: "is_primary",
              label: "Encargado principal",
              type: "checkbox",
              help: "Solo puede haber uno activo; marcarlo degrada al anterior.",
            },
          ]}
          initialValues={{
            guardian_id: "",
            relationship_label: "",
            is_primary: false,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          submitLabel="Vincular"
          title="Vincular encargado existente"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          description="El encargado y la fecha de inicio no se editan aqui; use Finalizar para cerrar la relacion."
          fields={[
            { name: "relationship_label", label: "Parentesco", required: true },
            {
              name: "is_primary",
              label: "Encargado principal",
              type: "checkbox",
            },
          ]}
          initialValues={{
            relationship_label: editing.relation.relationship_label,
            is_primary: editing.relation.is_primary,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title="Editar relacion"
        />
      ) : null}

      {catalogue.error ? (
        <div className="message message-error" role="alert">
          {catalogue.error}
        </div>
      ) : null}
      {guardiansError ? (
        <div className="message message-error" role="alert">
          {guardiansError}
        </div>
      ) : null}
      {actionError ? (
        <div className="message message-error" role="alert">
          {actionError}
        </div>
      ) : null}

      <CatalogueTable
        caption="Relacion estudiante-encargado"
        columns={RELATION_COLUMNS}
        emptyMessage="Este estudiante todavia no tiene encargados vinculados."
        loading={catalogue.loading}
        renderActions={(relation) => (
          <>
            <button
              className="button secondary button-small"
              onClick={() => setEditing({ mode: "edit", relation })}
              type="button"
            >
              Editar
            </button>
            {!relation.ends_at ? (
              <ConfirmButton
                confirmLabel="Si, finalizar"
                label="Finalizar"
                onConfirm={() => handleEnd(relation)}
                question={`Finalizar la relacion con ${relation.guardian.person.first_name}?`}
              />
            ) : null}
          </>
        )}
        rowKey={(relation) => relation.public_id}
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
