import { useCallback, useState } from "react";

import { CatalogueForm } from "../features/catalogue/CatalogueForm.jsx";
import { CataloguePager } from "../features/catalogue/CataloguePager.jsx";
import {
  CatalogueTable,
  StatusBadge,
} from "../features/catalogue/CatalogueTable.jsx";
import { ConfirmButton } from "../features/catalogue/ConfirmButton.jsx";
import { useCatalogue } from "../features/catalogue/useCatalogue.js";
import { academicsService } from "../services/academicsService.js";

const SUBJECT_COLUMNS = [
  { key: "name", header: "Curso", render: (row) => row.name },
  { key: "code", header: "Codigo", render: (row) => <code>{row.code}</code> },
  {
    key: "levels",
    header: "Se imparte en",
    render: (row) =>
      row.levels?.length ? (
        row.levels.map((level) => level.name).join(", ")
      ) : (
        <span className="muted">Sin vincular</span>
      ),
  },
  {
    key: "is_active",
    header: "Estado",
    render: (row) => <StatusBadge active={row.is_active} />,
  },
];

export function SubjectsPage() {
  const loadSubjects = useCallback(
    (params) => academicsService.listSubjects(params),
    []
  );
  const catalogue = useCatalogue(loadSubjects);

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const handleCreate = async (payload) => {
    await academicsService.createSubject(payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateSubject(editing.subject.public_id, payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleDeactivate = async (subject) => {
    setActionError("");
    try {
      await academicsService.deactivateSubject(subject.public_id);
      catalogue.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <section className="catalogue">
      <header className="panel catalogue-header">
        <div>
          <p className="eyebrow">Estructura academica</p>
          <h1>Cursos</h1>
          <p className="muted">
            Catalogo de cursos de la institucion. Los niveles en los que se
            imparte cada uno se declaran desde el plan de estudios del nivel.
          </p>
        </div>
        <div className="actions">
          <button
            className="button"
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Nuevo curso
          </button>
        </div>
      </header>

      {editing?.mode === "create" ? (
        <CatalogueForm
          description="El codigo es unico por institucion y no se puede cambiar despues."
          fields={[
            {
              name: "name",
              label: "Nombre",
              required: true,
              placeholder: "Ejemplo: Matematica",
            },
            {
              name: "code",
              label: "Codigo",
              required: true,
              placeholder: "Ejemplo: MAT",
            },
          ]}
          initialValues={{ name: "", code: "" }}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          submitLabel="Crear curso"
          title="Nuevo curso"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          description={`El codigo ${editing.subject.code} es inmutable.`}
          fields={[{ name: "name", label: "Nombre", required: true }]}
          initialValues={{ name: editing.subject.name }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.subject.name}`}
        />
      ) : null}

      <div className="panel">
        <div className="catalogue-toolbar">
          <h2>Cursos registrados</h2>
          <label className="field field-inline">
            <input
              checked={catalogue.includeInactive}
              onChange={(event) =>
                catalogue.setIncludeInactive(event.target.checked)
              }
              type="checkbox"
            />
            <span>Mostrar desactivados</span>
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
          caption="Cursos de la institucion"
          columns={SUBJECT_COLUMNS}
          emptyMessage="Todavia no hay cursos registrados."
          loading={catalogue.loading}
          renderActions={(subject) => (
            <>
              <button
                className="button secondary button-small"
                onClick={() => setEditing({ mode: "edit", subject })}
                type="button"
              >
                Editar
              </button>
              {subject.is_active ? (
                <ConfirmButton
                  confirmLabel="Si, desactivar"
                  label="Desactivar"
                  onConfirm={() => handleDeactivate(subject)}
                  question={`Desactivar ${subject.name}?`}
                />
              ) : null}
            </>
          )}
          rowKey={(subject) => subject.public_id}
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
