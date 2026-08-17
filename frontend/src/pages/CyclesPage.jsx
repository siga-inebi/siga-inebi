import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { CatalogueForm } from "../features/academics/CatalogueForm.jsx";
import { CataloguePager } from "../features/academics/CataloguePager.jsx";
import { CatalogueTable } from "../features/academics/CatalogueTable.jsx";
import { ConfirmButton } from "../features/academics/ConfirmButton.jsx";
import { CycleStatusBadge } from "../features/academics/CycleStatusBadge.jsx";
import { useCatalogue } from "../features/academics/useCatalogue.js";
import { useStructureOptions } from "../features/academics/useStructureOptions.js";
import { useSubjectOptions } from "../features/academics/useSubjectOptions.js";
import { academicsService } from "../services/academicsService.js";

const CYCLE_COLUMNS = [
  { key: "name", header: "Ciclo", render: (row) => row.name },
  { key: "starts_on", header: "Inicio", render: (row) => row.starts_on },
  { key: "ends_on", header: "Fin", render: (row) => row.ends_on },
  {
    key: "offering_count",
    header: "Grados ofertados",
    render: (row) => row.offering_count,
  },
  {
    key: "status",
    header: "Estado",
    render: (row) => <CycleStatusBadge status={row.status} />,
  },
];

export function CyclesPage() {
  const loadCycles = useCallback(
    (params) => academicsService.listCycles(params),
    []
  );
  const catalogue = useCatalogue(loadCycles);
  // Grados y jornadas cuestan varias peticiones anidadas, asi que se leen una
  // vez aqui y se reparten a los dos paneles en vez de una vez por panel.
  const structure = useStructureOptions();

  const [editing, setEditing] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [actionError, setActionError] = useState("");

  const selected =
    catalogue.items.find((cycle) => cycle.public_id === selectedId) || null;

  const handleCreate = async (payload) => {
    await academicsService.createCycle(payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateCycle(editing.cycle.public_id, payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleStatus = async (cycle, status) => {
    setActionError("");
    try {
      await academicsService.changeCycleStatus(cycle.public_id, status);
      catalogue.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <section className="catalogue">
      <header className="panel catalogue-header">
        <div>
          <p className="eyebrow">Ciclo escolar</p>
          <h1>Ciclos, oferta y plan de estudios</h1>
          <p className="muted">
            Cada ciclo arma su propia estructura. Nace en borrador, se activa
            cuando ya oferta al menos un grado, y al cerrarse queda congelado.
          </p>
        </div>
        <div className="actions">
          <button
            className="button"
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Nuevo ciclo
          </button>
        </div>
      </header>

      {editing?.mode === "create" ? (
        <CatalogueForm
          description="El nombre es unico por institucion y la fecha de fin debe ser posterior al inicio."
          fields={[
            {
              name: "name",
              label: "Nombre",
              required: true,
              placeholder: "Ejemplo: Ciclo 2027",
            },
            {
              name: "starts_on",
              label: "Inicio",
              type: "date",
              required: true,
            },
            { name: "ends_on", label: "Fin", type: "date", required: true },
          ]}
          initialValues={{ name: "", starts_on: "", ends_on: "" }}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          submitLabel="Crear ciclo"
          title="Nuevo ciclo escolar"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          fields={[
            { name: "name", label: "Nombre", required: true },
            {
              name: "starts_on",
              label: "Inicio",
              type: "date",
              required: true,
            },
            { name: "ends_on", label: "Fin", type: "date", required: true },
          ]}
          initialValues={{
            name: editing.cycle.name,
            starts_on: editing.cycle.starts_on,
            ends_on: editing.cycle.ends_on,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.cycle.name}`}
        />
      ) : null}

      <div className="panel">
        <div className="catalogue-toolbar">
          <h2>Ciclos registrados</h2>
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
          caption="Ciclos escolares de la institucion"
          columns={CYCLE_COLUMNS}
          emptyMessage="Todavia no hay ciclos registrados."
          loading={catalogue.loading}
          renderActions={(cycle) => (
            <>
              <button
                className="button secondary button-small"
                onClick={() =>
                  setSelectedId(
                    cycle.public_id === selectedId ? "" : cycle.public_id
                  )
                }
                type="button"
              >
                {cycle.public_id === selectedId ? "Ocultar detalle" : "Abrir"}
              </button>
              {cycle.status !== "closed" ? (
                <button
                  className="button secondary button-small"
                  onClick={() => setEditing({ mode: "edit", cycle })}
                  type="button"
                >
                  Editar
                </button>
              ) : null}
              {cycle.status === "draft" ? (
                <button
                  className="button button-small"
                  onClick={() => handleStatus(cycle, "active")}
                  type="button"
                >
                  Activar
                </button>
              ) : null}
              {cycle.status === "active" ? (
                <ConfirmButton
                  confirmLabel="Si, cerrar"
                  label="Cerrar ciclo"
                  onConfirm={() => handleStatus(cycle, "closed")}
                  question={`Cerrar ${cycle.name}? No se puede reabrir.`}
                />
              ) : null}
            </>
          )}
          rowKey={(cycle) => cycle.public_id}
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
        <CycleOfferingsPanel
          cycle={selected}
          key={`offerings-${selected.public_id}`}
          onChanged={catalogue.refresh}
          structure={structure}
        />
      ) : null}

      {selected ? (
        <CycleCurriculumPanel
          cycle={selected}
          key={`curriculum-${selected.public_id}`}
          structure={structure}
        />
      ) : null}
    </section>
  );
}

const OFFERING_COLUMNS = [
  { key: "grade", header: "Grado", render: (row) => row.grade.name },
  { key: "shift", header: "Jornada", render: (row) => row.shift.name },
  { key: "campus", header: "Sede", render: (row) => row.campus.name },
  {
    key: "section_count",
    header: "Secciones",
    render: (row) => row.section_count,
  },
  {
    key: "enrolment_count",
    header: "Matriculados",
    render: (row) => row.enrolment_count,
  },
];

/**
 * Oferta de grados del ciclo. Las secciones viven en su propia pantalla porque
 * cuelgan de una oferta concreta y necesitan sitio para el detalle docente.
 */
function CycleOfferingsPanel({ cycle, onChanged, structure }) {
  const loadOfferings = useCallback(
    (params) => academicsService.listCycleOfferings(cycle.public_id, params),
    [cycle.public_id]
  );
  const catalogue = useCatalogue(loadOfferings);
  const { grades, shifts, error: optionsError } = structure;

  const [creating, setCreating] = useState(false);
  const [actionError, setActionError] = useState("");

  const closed = cycle.status === "closed";

  const handleCreate = async (payload) => {
    await academicsService.createOffering(cycle.public_id, payload);
    setCreating(false);
    catalogue.refresh();
    onChanged();
  };

  const handleWithdraw = async (offering) => {
    setActionError("");
    try {
      await academicsService.withdrawOffering(offering.public_id);
      catalogue.refresh();
      onChanged();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <div className="panel">
      <div className="catalogue-toolbar">
        <h2>Oferta de grados de {cycle.name}</h2>
        <div className="actions">
          <label className="field field-inline">
            <input
              checked={catalogue.includeInactive}
              onChange={(event) =>
                catalogue.setIncludeInactive(event.target.checked)
              }
              type="checkbox"
            />
            <span>Mostrar retiradas</span>
          </label>
          {closed ? null : (
            <button
              className="button"
              onClick={() => setCreating(true)}
              type="button"
            >
              Ofertar grado
            </button>
          )}
        </div>
      </div>

      {closed ? (
        <p className="muted">
          El ciclo esta cerrado: su estructura ya no se puede modificar.
        </p>
      ) : null}

      {catalogue.error ? (
        <div className="message message-error" role="alert">
          {catalogue.error}
        </div>
      ) : null}
      {optionsError ? (
        <div className="message message-error" role="alert">
          {optionsError}
        </div>
      ) : null}
      {actionError ? (
        <div className="message message-error" role="alert">
          {actionError}
        </div>
      ) : null}

      {creating ? (
        <CatalogueForm
          description="Grado y jornada deben estar activos y ser de esta institucion."
          fields={[
            {
              name: "grade_id",
              label: "Grado",
              type: "select",
              required: true,
              options: grades.map((grade) => ({
                value: grade.public_id,
                label: `${grade.name} (${grade.code})`,
              })),
            },
            {
              name: "shift_id",
              label: "Jornada",
              type: "select",
              required: true,
              options: shifts.map((shift) => ({
                value: shift.public_id,
                label: `${shift.name} - ${shift.campusName}`,
              })),
            },
          ]}
          initialValues={{ grade_id: "", shift_id: "" }}
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
          submitLabel="Ofertar"
          title={`Ofertar un grado en ${cycle.name}`}
        />
      ) : null}

      <CatalogueTable
        caption={`Grados ofertados en ${cycle.name}`}
        columns={OFFERING_COLUMNS}
        emptyMessage="Este ciclo todavia no oferta ningun grado."
        loading={catalogue.loading}
        renderActions={(offering) => (
          <>
            <Link
              className="button secondary button-small"
              to={`/app/ofertas/${offering.public_id}`}
            >
              Secciones
            </Link>
            {offering.is_active && !closed ? (
              <ConfirmButton
                confirmLabel="Si, retirar"
                label="Retirar"
                onConfirm={() => handleWithdraw(offering)}
                question={`Retirar ${offering.grade.name} de ${offering.shift.name}?`}
              />
            ) : null}
          </>
        )}
        rowKey={(offering) => offering.public_id}
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

const CURRICULUM_COLUMNS = [
  { key: "grade", header: "Grado", render: (row) => row.grade.name },
  { key: "subject", header: "Curso", render: (row) => row.subject.name },
  {
    key: "code",
    header: "Codigo",
    render: (row) => <code>{row.subject.code}</code>,
  },
  {
    key: "is_required",
    header: "Obligatorio",
    render: (row) => (row.is_required ? "Si" : "Opcional"),
  },
];

/**
 * Plan de estudios del ciclo: que cursos estudia cada grado este ano. Es el
 * plan por ciclo, distinto del catalogo permanente del nivel.
 */
function CycleCurriculumPanel({ cycle, structure }) {
  const [gradeFilter, setGradeFilter] = useState("");

  const loadCurriculum = useCallback(
    (params) =>
      academicsService.listCurriculum(cycle.public_id, {
        ...params,
        grade: gradeFilter,
      }),
    [cycle.public_id, gradeFilter]
  );
  const catalogue = useCatalogue(loadCurriculum, {
    canIncludeInactive: false,
  });
  const { grades, error: gradesError } = structure;
  const { subjects, error: subjectsError } = useSubjectOptions();

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const closed = cycle.status === "closed";

  const handleAdd = async (payload) => {
    await academicsService.addCurriculumEntry(cycle.public_id, payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateCurriculumEntry(
      editing.entry.public_id,
      payload
    );
    setEditing(null);
    catalogue.refresh();
  };

  const handleRemove = async (entry) => {
    setActionError("");
    try {
      await academicsService.removeCurriculumEntry(entry.public_id);
      catalogue.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <div className="panel">
      <div className="catalogue-toolbar">
        <h2>Plan de estudios de {cycle.name}</h2>
        <div className="actions">
          <label className="field field-inline">
            <span>Grado</span>
            <select
              onChange={(event) => setGradeFilter(event.target.value)}
              value={gradeFilter}
            >
              <option value="">Todos</option>
              {grades.map((grade) => (
                <option key={grade.public_id} value={grade.public_id}>
                  {grade.name}
                </option>
              ))}
            </select>
          </label>
          {closed ? null : (
            <button
              className="button"
              onClick={() => setEditing({ mode: "create" })}
              type="button"
            >
              Agregar curso
            </button>
          )}
        </div>
      </div>

      {catalogue.error ? (
        <div className="message message-error" role="alert">
          {catalogue.error}
        </div>
      ) : null}
      {gradesError || subjectsError ? (
        <div className="message message-error" role="alert">
          {gradesError || subjectsError}
        </div>
      ) : null}
      {actionError ? (
        <div className="message message-error" role="alert">
          {actionError}
        </div>
      ) : null}

      {editing?.mode === "create" ? (
        <CatalogueForm
          description="Declara que el grado estudia ese curso durante este ciclo."
          fields={[
            {
              name: "grade_id",
              label: "Grado",
              type: "select",
              required: true,
              options: grades.map((grade) => ({
                value: grade.public_id,
                label: `${grade.name} (${grade.code})`,
              })),
            },
            {
              name: "subject_id",
              label: "Curso",
              type: "select",
              required: true,
              options: subjects
                .filter((subject) => subject.is_active)
                .map((subject) => ({
                  value: subject.public_id,
                  label: `${subject.name} (${subject.code})`,
                })),
            },
            { name: "is_required", label: "Es obligatorio", type: "checkbox" },
          ]}
          initialValues={{ grade_id: "", subject_id: "", is_required: true }}
          onCancel={() => setEditing(null)}
          onSubmit={handleAdd}
          submitLabel="Agregar al plan"
          title={`Agregar un curso al plan de ${cycle.name}`}
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          fields={[
            { name: "is_required", label: "Es obligatorio", type: "checkbox" },
          ]}
          initialValues={{ is_required: editing.entry.is_required }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.entry.subject.name} en ${editing.entry.grade.name}`}
        />
      ) : null}

      <CatalogueTable
        caption={`Plan de estudios de ${cycle.name}`}
        columns={CURRICULUM_COLUMNS}
        emptyMessage="Este ciclo todavia no tiene plan de estudios."
        loading={catalogue.loading}
        renderActions={
          closed
            ? undefined
            : (entry) => (
                <>
                  <button
                    className="button secondary button-small"
                    onClick={() => setEditing({ mode: "edit", entry })}
                    type="button"
                  >
                    Editar
                  </button>
                  <ConfirmButton
                    confirmLabel="Si, quitar"
                    label="Quitar"
                    onConfirm={() => handleRemove(entry)}
                    question={`Quitar ${entry.subject.name} de ${entry.grade.name}?`}
                  />
                </>
              )
        }
        rowKey={(entry) => entry.public_id}
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
