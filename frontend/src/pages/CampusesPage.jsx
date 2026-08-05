import { useCallback, useState } from "react";

import { CatalogueForm } from "../features/academics/CatalogueForm.jsx";
import { CataloguePager } from "../features/academics/CataloguePager.jsx";
import {
  CatalogueTable,
  StatusBadge,
} from "../features/academics/CatalogueTable.jsx";
import { ConfirmButton } from "../features/academics/ConfirmButton.jsx";
import { useCatalogue } from "../features/academics/useCatalogue.js";
import { academicsService } from "../services/academicsService.js";

const CAMPUS_COLUMNS = [
  { key: "name", header: "Sede", render: (row) => row.name },
  { key: "code", header: "Codigo", render: (row) => <code>{row.code}</code> },
  {
    key: "address",
    header: "Direccion",
    render: (row) =>
      row.address || <span className="muted">Sin registrar</span>,
  },
  {
    key: "is_main",
    header: "Principal",
    render: (row) => (row.is_main ? "Si" : "No"),
  },
  { key: "shift_count", header: "Jornadas", render: (row) => row.shift_count },
  {
    key: "is_active",
    header: "Estado",
    render: (row) => <StatusBadge active={row.is_active} />,
  },
];

export function CampusesPage() {
  const loadCampuses = useCallback(
    (params) => academicsService.listCampuses(params),
    []
  );
  const catalogue = useCatalogue(loadCampuses);

  const [editing, setEditing] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [actionError, setActionError] = useState("");

  // La sede seleccionada se re-lee del listado para que no quede desfasada
  // despues de editarla o de recargar la pagina de resultados.
  const selected =
    catalogue.items.find((campus) => campus.public_id === selectedId) || null;

  const handleCreate = async (payload) => {
    await academicsService.createCampus(payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateCampus(editing.campus.public_id, payload);
    setEditing(null);
    catalogue.refresh();
  };

  const handleDeactivate = async (campus) => {
    setActionError("");
    try {
      await academicsService.deactivateCampus(campus.public_id);
      if (campus.public_id === selectedId) {
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
          <p className="eyebrow">Estructura institucional</p>
          <h1>Sedes y jornadas</h1>
          <p className="muted">
            Registra las sedes del establecimiento y las jornadas que atiende
            cada una. Dar de baja una sede la desactiva junto con sus jornadas.
          </p>
        </div>
        <div className="actions">
          <button
            className="button"
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Nueva sede
          </button>
        </div>
      </header>

      {editing?.mode === "create" ? (
        <CatalogueForm
          description="El codigo se normaliza a mayusculas y no se puede cambiar despues."
          fields={[
            {
              name: "name",
              label: "Nombre",
              required: true,
              placeholder: "Ejemplo: Sede Central",
            },
            {
              name: "code",
              label: "Codigo",
              required: true,
              placeholder: "Ejemplo: CENTRAL",
            },
            { name: "address", label: "Direccion" },
            {
              name: "is_main",
              label: "Es la sede principal",
              type: "checkbox",
              help: "Solo puede haber una; marcarla degrada a la anterior.",
            },
          ]}
          initialValues={{ name: "", code: "", address: "", is_main: false }}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          submitLabel="Crear sede"
          title="Nueva sede"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          description={`El codigo ${editing.campus.code} es inmutable.`}
          fields={[
            { name: "name", label: "Nombre", required: true },
            { name: "address", label: "Direccion" },
            {
              name: "is_main",
              label: "Es la sede principal",
              type: "checkbox",
            },
          ]}
          initialValues={{
            name: editing.campus.name,
            address: editing.campus.address || "",
            is_main: editing.campus.is_main,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.campus.name}`}
        />
      ) : null}

      <div className="panel">
        <div className="catalogue-toolbar">
          <h2>Sedes registradas</h2>
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
          caption="Sedes de la institucion"
          columns={CAMPUS_COLUMNS}
          emptyMessage="Todavia no hay sedes registradas."
          loading={catalogue.loading}
          renderActions={(campus) => (
            <>
              <button
                className="button secondary button-small"
                onClick={() =>
                  setSelectedId(
                    campus.public_id === selectedId ? "" : campus.public_id
                  )
                }
                type="button"
              >
                {campus.public_id === selectedId
                  ? "Ocultar jornadas"
                  : "Ver jornadas"}
              </button>
              <button
                className="button secondary button-small"
                onClick={() => setEditing({ mode: "edit", campus })}
                type="button"
              >
                Editar
              </button>
              {campus.is_active ? (
                <ConfirmButton
                  confirmLabel="Si, desactivar"
                  label="Desactivar"
                  onConfirm={() => handleDeactivate(campus)}
                  question={`Desactivar ${campus.name}?`}
                />
              ) : null}
            </>
          )}
          rowKey={(campus) => campus.public_id}
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
        <CampusShiftsPanel
          campus={selected}
          key={selected.public_id}
          onChanged={catalogue.refresh}
        />
      ) : null}
    </section>
  );
}

const SHIFT_COLUMNS = [
  { key: "name", header: "Jornada", render: (row) => row.name },
  { key: "code", header: "Codigo", render: (row) => <code>{row.code}</code> },
  {
    key: "is_active",
    header: "Estado",
    render: (row) => <StatusBadge active={row.is_active} />,
  },
];

/**
 * Jornadas de una sede. Se remonta con `key` al cambiar de sede, de modo que la
 * paginacion y el formulario arrancan limpios.
 */
function CampusShiftsPanel({ campus, onChanged }) {
  const loadShifts = useCallback(
    (params) => academicsService.listCampusShifts(campus.public_id, params),
    [campus.public_id]
  );
  const catalogue = useCatalogue(loadShifts);

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const afterChange = () => {
    setEditing(null);
    catalogue.refresh();
    onChanged();
  };

  const handleCreate = async (payload) => {
    await academicsService.createShift(campus.public_id, payload);
    afterChange();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateShift(editing.shift.public_id, payload);
    afterChange();
  };

  const handleDeactivate = async (shift) => {
    setActionError("");
    try {
      await academicsService.deactivateShift(shift.public_id);
      afterChange();
    } catch (requestError) {
      setActionError(requestError.message);
    }
  };

  return (
    <div className="panel">
      <div className="catalogue-toolbar">
        <h2>Jornadas de {campus.name}</h2>
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
          <button
            className="button"
            onClick={() => setEditing({ mode: "create" })}
            type="button"
          >
            Nueva jornada
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
          description="El codigo es unico dentro de la sede: dos sedes pueden tener MAT."
          fields={[
            {
              name: "name",
              label: "Nombre",
              required: true,
              placeholder: "Ejemplo: Matutina",
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
          submitLabel="Crear jornada"
          title="Nueva jornada"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <CatalogueForm
          description="Solo se puede renombrar; el codigo es inmutable."
          fields={[{ name: "name", label: "Nombre", required: true }]}
          initialValues={{ name: editing.shift.name }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title={`Editar ${editing.shift.name}`}
        />
      ) : null}

      <CatalogueTable
        caption={`Jornadas de ${campus.name}`}
        columns={SHIFT_COLUMNS}
        emptyMessage="Esta sede todavia no tiene jornadas."
        loading={catalogue.loading}
        renderActions={(shift) => (
          <>
            <button
              className="button secondary button-small"
              onClick={() => setEditing({ mode: "edit", shift })}
              type="button"
            >
              Editar
            </button>
            {shift.is_active ? (
              <ConfirmButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(shift)}
                question={`Desactivar ${shift.name}?`}
              />
            ) : null}
          </>
        )}
        rowKey={(shift) => shift.public_id}
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
