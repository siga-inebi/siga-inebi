import { useCallback, useState } from "react";

import { CatalogueForm } from "../features/catalogue/CatalogueForm.jsx";
import { CataloguePager } from "../features/catalogue/CataloguePager.jsx";
import {
  CatalogueTable,
  StatusBadge,
} from "../features/catalogue/CatalogueTable.jsx";
import { ConfirmButton } from "../features/catalogue/ConfirmButton.jsx";
import { useCatalogue } from "../features/catalogue/useCatalogue.js";
import { useSubjectOptions } from "../features/academics/useSubjectOptions.js";
import { academicsService } from "../services/academicsService.js";

const LEVEL_COLUMNS = [
  { key: "sequence", header: "Orden", render: (row) => row.sequence },
  { key: "name", header: "Nivel", render: (row) => row.name },
  { key: "code", header: "Codigo", render: (row) => <code>{row.code}</code> },
  { key: "grade_count", header: "Grados", render: (row) => row.grade_count },
  {
    key: "subject_count",
    header: "Cursos",
    render: (row) => row.subject_count,
  },
  {
    key: "is_active",
    header: "Estado",
    render: (row) => <StatusBadge active={row.is_active} />,
  },
];

export function LevelsPage() {
  const loadLevels = useCallback(
    (params) => academicsService.listLevels(params),
    []
  );
  const catalogue = useCatalogue(loadLevels);

  const [editing, setEditing] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [actionError, setActionError] = useState("");

  const selected =
    catalogue.items.find((level) => level.public_id === selectedId) || null;

  const handleCreate = async (payload) => {
    await academicsService.createLevel(payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateLevel(editing.level.public_id, payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleDeactivate = async (level) => {
    setActionError("");
    try {
      await academicsService.deactivateLevel(level.public_id);
      if (level.public_id === selectedId) {
        setSelectedId("");
      }
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
          <h1>Niveles, grados y plan de estudios</h1>
          <p className="muted">
            Cada nivel ordena su secuencia pedagogica, agrupa sus grados y
            declara los cursos que se imparten en el.
          </p>
        </div>
        <div className="actions">
          <button
            className="button"
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Nuevo nivel
          </button>
        </div>
      </header>

      {editing?.mode === "create" ? (
        <CatalogueForm
          description="La secuencia define el orden pedagogico y es unica por institucion."
          fields={[
            {
              name: "name",
              label: "Nombre",
              required: true,
              placeholder: "Ejemplo: Basico",
            },
            {
              name: "code",
              label: "Codigo",
              required: true,
              placeholder: "Ejemplo: BAS",
            },
            {
              name: "sequence",
              label: "Secuencia",
              type: "number",
              min: 1,
              required: true,
            },
          ]}
          initialValues={{ name: "", code: "", sequence: 1 }}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          submitLabel="Crear nivel"
          title="Nuevo nivel"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          description={`El codigo ${editing.level.code} es inmutable.`}
          fields={[
            { name: "name", label: "Nombre", required: true },
            {
              name: "sequence",
              label: "Secuencia",
              type: "number",
              min: 1,
              required: true,
            },
          ]}
          initialValues={{
            name: editing.level.name,
            sequence: editing.level.sequence,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.level.name}`}
        />
      ) : null}

      <div className="panel">
        <div className="catalogue-toolbar">
          <h2>Niveles registrados</h2>
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
          caption="Niveles de la institucion"
          columns={LEVEL_COLUMNS}
          emptyMessage="Todavia no hay niveles registrados."
          loading={catalogue.loading}
          renderActions={(level) => (
            <>
              <button
                className="button secondary button-small"
                onClick={() =>
                  setSelectedId(
                    level.public_id === selectedId ? "" : level.public_id
                  )
                }
                type="button"
              >
                {level.public_id === selectedId ? "Ocultar detalle" : "Abrir"}
              </button>
              <button
                className="button secondary button-small"
                onClick={() => setEditing({ mode: "edit", level })}
                type="button"
              >
                Editar
              </button>
              {level.is_active ? (
                <ConfirmButton
                  confirmLabel="Si, desactivar"
                  label="Desactivar"
                  onConfirm={() => handleDeactivate(level)}
                  question={`Desactivar ${level.name} y sus grados?`}
                />
              ) : null}
            </>
          )}
          rowKey={(level) => level.public_id}
          rows={catalogue.items}
        />

        <CataloguePager
          count={catalogue.count}
          onChange={catalogue.goToPage}
          page={catalogue.page}
          pageCount={catalogue.pageCount}
        />
      </div>

      {selected ? (
        <LevelGradesPanel
          key={`grades-${selected.public_id}`}
          level={selected}
          onChanged={catalogue.refresh}
        />
      ) : null}

      {selected ? (
        <LevelSubjectsPanel
          key={`subjects-${selected.public_id}`}
          level={selected}
          onChanged={catalogue.refresh}
        />
      ) : null}
    </section>
  );
}

const GRADE_COLUMNS = [
  { key: "sequence", header: "Orden", render: (row) => row.sequence },
  { key: "name", header: "Grado", render: (row) => row.name },
  { key: "code", header: "Codigo", render: (row) => <code>{row.code}</code> },
  {
    key: "is_active",
    header: "Estado",
    render: (row) => <StatusBadge active={row.is_active} />,
  },
];

function LevelGradesPanel({ level, onChanged }) {
  const loadGrades = useCallback(
    (params) => academicsService.listLevelGrades(level.public_id, params),
    [level.public_id]
  );
  const catalogue = useCatalogue(loadGrades);

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const afterChange = () => {
    setEditing(null);
    catalogue.refresh();
    onChanged();
  };

  const handleCreate = async (payload) => {
    await academicsService.createGrade(level.public_id, payload);
    afterChange();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateGrade(editing.grade.public_id, payload);
    afterChange();
  };

  const handleDeactivate = async (grade) => {
    setActionError("");
    try {
      await academicsService.deactivateGrade(grade.public_id);
      afterChange();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <div className="panel">
      <div className="catalogue-toolbar">
        <h2>Grados de {level.name}</h2>
        <div className="actions">
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
          <button
            className="button"
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Nuevo grado
          </button>
        </div>
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

      {editing?.mode === "create" ? (
        <CatalogueForm
          description="El codigo del grado es unico en toda la institucion."
          fields={[
            {
              name: "name",
              label: "Nombre",
              required: true,
              placeholder: "Ejemplo: Primero Basico",
            },
            {
              name: "code",
              label: "Codigo",
              required: true,
              placeholder: "Ejemplo: BAS1",
            },
            {
              name: "sequence",
              label: "Secuencia",
              type: "number",
              min: 1,
              required: true,
            },
          ]}
          initialValues={{ name: "", code: "", sequence: 1 }}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          submitLabel="Crear grado"
          title={`Nuevo grado en ${level.name}`}
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          description="Solo cambian el nombre y el orden; el codigo es inmutable."
          fields={[
            { name: "name", label: "Nombre", required: true },
            {
              name: "sequence",
              label: "Secuencia",
              type: "number",
              min: 1,
              required: true,
            },
          ]}
          initialValues={{
            name: editing.grade.name,
            sequence: editing.grade.sequence,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.grade.name}`}
        />
      ) : null}

      <CatalogueTable
        caption={`Grados de ${level.name}`}
        columns={GRADE_COLUMNS}
        emptyMessage="Este nivel todavia no tiene grados."
        loading={catalogue.loading}
        renderActions={(grade) => (
          <>
            <button
              className="button secondary button-small"
              onClick={() => setEditing({ mode: "edit", grade })}
              type="button"
            >
              Editar
            </button>
            {grade.is_active ? (
              <ConfirmButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(grade)}
                question={`Desactivar ${grade.name}?`}
              />
            ) : null}
          </>
        )}
        rowKey={(grade) => grade.public_id}
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

const LEVEL_SUBJECT_COLUMNS = [
  { key: "subject", header: "Curso", render: (row) => row.subject.name },
  {
    key: "code",
    header: "Codigo",
    render: (row) => <code>{row.subject.code}</code>,
  },
  {
    key: "is_required",
    header: "Obligatorio",
    render: (row) => (row.is_required ? "Si" : "No"),
  },
  {
    key: "weekly_hours",
    header: "Horas semanales",
    render: (row) =>
      row.weekly_hours || <span className="muted">Sin definir</span>,
  },
];

/**
 * Plan de estudios del nivel. El endpoint de vinculos no acepta
 * `include_inactive`: desvincular borra el vinculo, no lo desactiva.
 */
function LevelSubjectsPanel({ level, onChanged }) {
  const loadLevelSubjects = useCallback(
    (params) => academicsService.listLevelSubjects(level.public_id, params),
    [level.public_id]
  );
  const catalogue = useCatalogue(loadLevelSubjects, {
    canIncludeInactive: false,
  });
  const { subjects, error: subjectsError } = useSubjectOptions();

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const linkedIds = new Set(
    catalogue.items.map((link) => link.subject.public_id)
  );
  const available = subjects.filter(
    (subject) => subject.is_active && !linkedIds.has(subject.public_id)
  );

  const afterChange = () => {
    setEditing(null);
    catalogue.refresh();
    onChanged();
  };

  const handleLink = async (payload) => {
    await academicsService.linkSubjectToLevel(level.public_id, payload);
    afterChange();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateLevelSubject(
      level.public_id,
      editing.link.subject.public_id,
      payload
    );
    afterChange();
  };

  const handleUnlink = async (link) => {
    setActionError("");
    try {
      await academicsService.unlinkSubjectFromLevel(
        level.public_id,
        link.subject.public_id
      );
      afterChange();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <div className="panel">
      <div className="catalogue-toolbar">
        <h2>Plan de estudios de {level.name}</h2>
        <button
          className="button"
          disabled={!available.length}
          onClick={() => setEditing({ mode: "create" })}
          type="button"
        >
          Vincular curso
        </button>
      </div>

      {!available.length ? (
        <p className="muted">
          Todos los cursos activos ya estan vinculados a este nivel.
        </p>
      ) : null}

      {catalogue.error ? (
        <div className="message message-error" role="alert">
          {catalogue.error}
        </div>
      ) : null}
      {subjectsError ? (
        <div className="message message-error" role="alert">
          {subjectsError}
        </div>
      ) : null}
      {actionError ? (
        <div className="message message-error" role="alert">
          {actionError}
        </div>
      ) : null}

      {editing?.mode === "create" ? (
        <CatalogueForm
          description="Declara que el curso se imparte en este nivel. 0 horas significa sin definir."
          fields={[
            {
              name: "subject_id",
              label: "Curso",
              type: "select",
              required: true,
              options: available.map((subject) => ({
                value: subject.public_id,
                label: `${subject.name} (${subject.code})`,
              })),
            },
            {
              name: "is_required",
              label: "Es obligatorio",
              type: "checkbox",
            },
            {
              name: "weekly_hours",
              label: "Horas semanales",
              type: "number",
              min: 0,
            },
          ]}
          initialValues={{
            subject_id: "",
            is_required: true,
            weekly_hours: 0,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleLink}
          submitLabel="Vincular"
          title={`Vincular curso a ${level.name}`}
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          fields={[
            {
              name: "is_required",
              label: "Es obligatorio",
              type: "checkbox",
            },
            {
              name: "weekly_hours",
              label: "Horas semanales",
              type: "number",
              min: 0,
            },
          ]}
          initialValues={{
            is_required: editing.link.is_required,
            weekly_hours: editing.link.weekly_hours,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.link.subject.name} en ${level.name}`}
        />
      ) : null}

      <CatalogueTable
        caption={`Cursos vinculados a ${level.name}`}
        columns={LEVEL_SUBJECT_COLUMNS}
        emptyMessage="Este nivel todavia no tiene cursos vinculados."
        loading={catalogue.loading}
        renderActions={(link) => (
          <>
            <button
              className="button secondary button-small"
              onClick={() => setEditing({ mode: "edit", link })}
              type="button"
            >
              Editar
            </button>
            <ConfirmButton
              confirmLabel="Si, desvincular"
              label="Desvincular"
              onConfirm={() => handleUnlink(link)}
              question={`Quitar ${link.subject.name} del plan?`}
            />
          </>
        )}
        rowKey={(link) => link.public_id}
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
