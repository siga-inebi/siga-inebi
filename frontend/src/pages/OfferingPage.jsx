import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { CatalogueForm } from "../features/academics/CatalogueForm.jsx";
import { CataloguePager } from "../features/academics/CataloguePager.jsx";
import {
  CatalogueTable,
  StatusBadge,
} from "../features/academics/CatalogueTable.jsx";
import { ConfirmButton } from "../features/academics/ConfirmButton.jsx";
import { CycleStatusBadge } from "../features/academics/CycleStatusBadge.jsx";
import { collectAllPages } from "../features/academics/collectAllPages.js";
import { useCatalogue } from "../features/academics/useCatalogue.js";
import { useTeacherOptions } from "../features/academics/useTeacherOptions.js";
import { academicsService } from "../services/academicsService.js";

const SECTION_COLUMNS = [
  { key: "name", header: "Seccion", render: (row) => row.name },
  {
    key: "capacity",
    header: "Cupo",
    render: (row) =>
      row.capacity || <span className="muted">Sin declarar</span>,
  },
  {
    key: "enrolment_count",
    header: "Matriculados",
    render: (row) => row.enrolment_count,
  },
  {
    key: "available_seats",
    header: "Disponibles",
    render: (row) =>
      row.available_seats === null ? (
        <span className="muted">Sin tope</span>
      ) : (
        row.available_seats
      ),
  },
  {
    key: "assignment_count",
    header: "Cursos cubiertos",
    render: (row) => row.assignment_count,
  },
  {
    key: "is_active",
    header: "Estado",
    render: (row) => <StatusBadge active={row.is_active} />,
  },
];

export function OfferingPage() {
  const { offeringId } = useParams();
  const [offering, setOffering] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    academicsService
      .getOffering(offeringId)
      .then((payload) => {
        if (active) {
          setOffering(payload);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError.message);
        }
      });

    return () => {
      active = false;
    };
  }, [offeringId]);

  if (error) {
    return (
      <section className="catalogue">
        <div className="panel">
          <div className="message message-error" role="alert">
            {error}
          </div>
          <Link className="button secondary" to="/app/ciclos">
            Volver a ciclos
          </Link>
        </div>
      </section>
    );
  }

  if (!offering) {
    return <div className="panel">Cargando oferta...</div>;
  }

  return (
    <section className="catalogue">
      <header className="panel catalogue-header">
        <div>
          <p className="eyebrow">Oferta de grado</p>
          <h1>
            {offering.grade.name} - {offering.shift.name}
          </h1>
          <p className="muted">
            {offering.campus.name} &middot; {offering.academic_cycle.name}{" "}
            <CycleStatusBadge status={offering.academic_cycle.status} />
          </p>
        </div>
        <div className="actions">
          <Link className="button secondary" to="/app/ciclos">
            Volver a ciclos
          </Link>
        </div>
      </header>

      <OfferingSectionsPanel offering={offering} />
    </section>
  );
}

function OfferingSectionsPanel({ offering }) {
  const loadSections = useCallback(
    (params) =>
      academicsService.listOfferingSections(offering.public_id, params),
    [offering.public_id]
  );
  const catalogue = useCatalogue(loadSections);

  const [editing, setEditing] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [actionError, setActionError] = useState("");

  const closed = offering.academic_cycle.status === "closed";
  const selected =
    catalogue.items.find((section) => section.public_id === selectedId) || null;

  const handleCreate = async (payload) => {
    await academicsService.createSection(offering.public_id, payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateSection(editing.section.public_id, payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleDeactivate = async (section) => {
    setActionError("");
    try {
      await academicsService.deactivateSection(section.public_id);
      if (section.public_id === selectedId) {
        setSelectedId("");
      }
      catalogue.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <>
      <div className="panel">
        <div className="catalogue-toolbar">
          <h2>Secciones</h2>
          <div className="actions">
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
            {closed ? null : (
              <button
                className="button"
                onClick={() => setEditing({ mode: "create" })}
                type="button"
              >
                Nueva seccion
              </button>
            )}
          </div>
        </div>

        {closed ? (
          <p className="muted">
            El ciclo esta cerrado: las secciones ya no se pueden modificar.
          </p>
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

        {editing?.mode === "create" ? (
          <CatalogueForm
            description="El nombre se normaliza a mayusculas. Cupo 0 significa sin tope declarado."
            fields={[
              {
                name: "name",
                label: "Nombre",
                required: true,
                placeholder: "Ejemplo: A",
              },
              { name: "capacity", label: "Cupo", type: "number", min: 0 },
            ]}
            initialValues={{ name: "", capacity: 0 }}
            onCancel={() => setEditing(null)}
            onSubmit={handleCreate}
            submitLabel="Crear seccion"
            title="Nueva seccion"
          />
        ) : null}

        {editing?.mode === "edit" ? (
          <CatalogueForm
            description="El cupo no puede quedar por debajo de los alumnos ya matriculados."
            fields={[
              { name: "name", label: "Nombre", required: true },
              { name: "capacity", label: "Cupo", type: "number", min: 0 },
            ]}
            initialValues={{
              name: editing.section.name,
              capacity: editing.section.capacity,
            }}
            onCancel={() => setEditing(null)}
            onSubmit={handleUpdate}
            submitLabel="Guardar cambios"
            title={`Editar seccion ${editing.section.name}`}
          />
        ) : null}

        <CatalogueTable
          caption="Secciones de la oferta"
          columns={SECTION_COLUMNS}
          emptyMessage="Esta oferta todavia no tiene secciones."
          loading={catalogue.loading}
          renderActions={(section) => (
            <>
              <button
                className="button secondary button-small"
                onClick={() =>
                  setSelectedId(
                    section.public_id === selectedId ? "" : section.public_id
                  )
                }
                type="button"
              >
                {section.public_id === selectedId
                  ? "Ocultar docentes"
                  : "Docentes"}
              </button>
              {closed ? null : (
                <button
                  className="button secondary button-small"
                  onClick={() => setEditing({ mode: "edit", section })}
                  type="button"
                >
                  Editar
                </button>
              )}
              {section.is_active && !closed ? (
                <ConfirmButton
                  confirmLabel="Si, desactivar"
                  label="Desactivar"
                  onConfirm={() => handleDeactivate(section)}
                  question={`Desactivar la seccion ${section.name}?`}
                />
              ) : null}
            </>
          )}
          rowKey={(section) => section.public_id}
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
        <SectionAssignmentsPanel
          key={selected.public_id}
          offering={offering}
          onChanged={catalogue.refresh}
          section={selected}
        />
      ) : null}
    </>
  );
}

const ASSIGNMENT_COLUMNS = [
  { key: "subject", header: "Curso", render: (row) => row.subject.name },
  {
    key: "teacher",
    header: "Docente",
    render: (row) => row.teacher.full_name,
  },
  { key: "starts_on", header: "Desde", render: (row) => row.starts_on },
  {
    key: "ends_on",
    header: "Hasta",
    render: (row) => row.ends_on || <span className="muted">Vigente</span>,
  },
];

/**
 * Docentes a cargo de los cursos de una seccion.
 *
 * El selector de curso ofrece solo lo que el grado estudia en este ciclo, que
 * es exactamente lo que la API acepta: asignar algo fuera del plan se rechaza.
 */
function SectionAssignmentsPanel({ offering, section, onChanged }) {
  const loadAssignments = useCallback(
    (params) =>
      academicsService.listSectionAssignments(section.public_id, params),
    [section.public_id]
  );
  const catalogue = useCatalogue(loadAssignments);
  const { teachers, error: teachersError } = useTeacherOptions();

  const [planned, setPlanned] = useState([]);
  const [planError, setPlanError] = useState("");
  const [creating, setCreating] = useState(false);
  const [actionError, setActionError] = useState("");

  const cycleId = offering.academic_cycle.public_id;
  const gradeId = offering.grade.public_id;
  const closed = offering.academic_cycle.status === "closed";

  useEffect(() => {
    let active = true;
    collectAllPages((page) =>
      academicsService.listCurriculum(cycleId, { page, grade: gradeId })
    )
      .then((entries) => {
        if (active) {
          setPlanned(entries);
        }
      })
      .catch((requestError) => {
        if (active) {
          setPlanError(requestError.message);
        }
      });

    return () => {
      active = false;
    };
  }, [cycleId, gradeId]);

  const coveredIds = new Set(
    catalogue.items
      .filter((assignment) => assignment.is_open)
      .map((assignment) => assignment.subject.public_id)
  );
  const available = planned.filter(
    (entry) => !coveredIds.has(entry.subject.public_id)
  );

  const afterChange = () => {
    setCreating(false);
    catalogue.refresh();
    onChanged();
  };

  const handleAssign = async (payload) => {
    // La fecha es opcional: mandarla vacia haria que el backend la rechace,
    // mientras que omitirla deja que el servicio use la de hoy.
    const body = { ...payload };
    if (!body.starts_on) {
      delete body.starts_on;
    }
    await academicsService.assignTeacher(section.public_id, body);
    afterChange();
  };

  const handleEnd = async (assignment) => {
    setActionError("");
    try {
      await academicsService.endAssignment(assignment.public_id);
      afterChange();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <div className="panel">
      <div className="catalogue-toolbar">
        <h2>Docentes de la seccion {section.name}</h2>
        <div className="actions">
          <label className="field field-inline">
            <input
              checked={catalogue.includeInactive}
              onChange={(event) =>
                catalogue.setIncludeInactive(event.target.checked)
              }
              type="checkbox"
            />
            <span>Ver historial</span>
          </label>
          {closed ? null : (
            <button
              className="button"
              disabled={!available.length}
              onClick={() => setCreating(true)}
              type="button"
            >
              Asignar docente
            </button>
          )}
        </div>
      </div>

      {!planned.length ? (
        <p className="muted">
          El grado {offering.grade.name} todavia no tiene plan de estudios en
          este ciclo. Agrega cursos al plan antes de asignar docentes.
        </p>
      ) : null}
      {planned.length > 0 && !available.length ? (
        <p className="muted">
          Todos los cursos del plan ya tienen docente asignado.
        </p>
      ) : null}

      {catalogue.error ? (
        <div className="message message-error" role="alert">
          {catalogue.error}
        </div>
      ) : null}
      {planError || teachersError ? (
        <div className="message message-error" role="alert">
          {planError || teachersError}
        </div>
      ) : null}
      {actionError ? (
        <div className="message message-error" role="alert">
          {actionError}
        </div>
      ) : null}

      {creating ? (
        <CatalogueForm
          description="Solo se ofrecen los cursos del plan que aun no tienen docente vigente."
          fields={[
            {
              name: "subject_id",
              label: "Curso",
              type: "select",
              required: true,
              options: available.map((entry) => ({
                value: entry.subject.public_id,
                label: `${entry.subject.name} (${entry.subject.code})`,
              })),
            },
            {
              name: "teacher_id",
              label: "Docente",
              type: "select",
              required: true,
              options: teachers.map((person) => ({
                value: person.public_id,
                label: `${person.first_name} ${person.last_name}`.trim(),
              })),
            },
            {
              name: "starts_on",
              label: "Desde",
              type: "date",
              help: "Si se deja vacio, empieza hoy.",
            },
          ]}
          initialValues={{ subject_id: "", teacher_id: "", starts_on: "" }}
          onCancel={() => setCreating(false)}
          onSubmit={handleAssign}
          submitLabel="Asignar"
          title={`Asignar docente en la seccion ${section.name}`}
        />
      ) : null}

      <CatalogueTable
        caption={`Docentes de la seccion ${section.name}`}
        columns={ASSIGNMENT_COLUMNS}
        emptyMessage="Esta seccion todavia no tiene docentes asignados."
        loading={catalogue.loading}
        renderActions={(assignment) =>
          assignment.is_open && !closed ? (
            <ConfirmButton
              confirmLabel="Si, cerrar"
              label="Cerrar"
              onConfirm={() => handleEnd(assignment)}
              question={`Cerrar la asignacion de ${assignment.teacher.full_name}?`}
            />
          ) : null
        }
        rowKey={(assignment) => assignment.public_id}
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
