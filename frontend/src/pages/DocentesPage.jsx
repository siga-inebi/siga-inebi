import { useEffect, useMemo, useState } from "react";

import { DataTable } from "../components/DataTable.jsx";
import { DetailPanel } from "../components/DetailPanel.jsx";
import { FormModal } from "../components/FormModal.jsx";
import { ListToolbar } from "../components/ListToolbar.jsx";
import { Pagination } from "../components/Pagination.jsx";
import { POSITION_OPTIONS } from "../mocks/teachers.js";
import { teachersService } from "../services/teachersService.js";
import { downloadCsv } from "../utils/csv.js";

const PAGE_SIZE = 5;

// Campos y orden segun el mockup "Agregar docente" (tmp/image-3.png): un
// solo campo de nombre completo, no first_name/last_name por separado.
const CREATE_FIELDS = [
  { name: "full_name", label: "Nombres completos", required: true },
  { name: "specialty", label: "Especialidad", required: true },
  {
    name: "position",
    label: "Puesto",
    type: "select",
    options: POSITION_OPTIONS,
    required: true,
  },
  { name: "appointment_date", label: "Fecha de Nombramiento", type: "date" },
  { name: "employee_code", label: "Codigo de Empleado", required: true },
  { name: "phone_number", label: "Numero de Telefono" },
];

function fullName(teacher) {
  return [teacher.first_name, teacher.last_name].filter(Boolean).join(" ");
}

const COLUMNS = [
  { key: "nombre", label: "Nombre", render: fullName },
  { key: "especialidad", label: "Especialidad", render: (item) => item.specialty },
  { key: "puesto", label: "Puesto", render: (item) => item.position },
  {
    key: "codigo",
    label: "Codigo Empleado",
    render: (item) => item.employee_code,
  },
  { key: "telefono", label: "Telefono", render: (item) => item.phone_number },
];

export function DocentesPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [positionFilter, setPositionFilter] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let active = true;
    teachersService
      .list()
      .then((data) => {
        if (active) {
          setItems(data);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setPage(1);
  }, [search, positionFilter]);

  const filtered = useMemo(
    () =>
      items.filter((teacher) => {
        const matchesSearch = fullName(teacher)
          .toLowerCase()
          .includes(search.trim().toLowerCase());
        const matchesPosition =
          !positionFilter || teacher.position === positionFilter;
        return matchesSearch && matchesPosition;
      }),
    [items, search, positionFilter]
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paged = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const handleExport = () => {
    downloadCsv(
      "docentes.csv",
      [
        { label: "Nombre", value: fullName },
        { label: "Especialidad", value: (item) => item.specialty },
        { label: "Puesto", value: (item) => item.position },
        { label: "Codigo Empleado", value: (item) => item.employee_code },
        { label: "Telefono", value: (item) => item.phone_number },
      ],
      filtered
    );
  };

  const handleCreate = async (values) => {
    const { full_name: fullNameInput, ...rest } = values;
    const created = await teachersService.create({
      ...rest,
      first_name: fullNameInput,
      last_name: "",
    });
    setItems((current) => [...current, created]);
    setCreating(false);
  };

  return (
    <section className="list-page">
      <header className="list-page-header">
        <p className="eyebrow">Sistema academico / Docentes y Administrativos</p>
        <h1>Docentes y Administrativos</h1>
        <p className="muted">Listado de personal docente y administrativo.</p>
      </header>

      <ListToolbar
        createLabel="+ Agregar nuevo"
        filterOptions={POSITION_OPTIONS}
        filterValue={positionFilter}
        onCreate={() => setCreating(true)}
        onExportCsv={handleExport}
        onFilterChange={setPositionFilter}
        onSearchChange={setSearch}
        searchValue={search}
      />

      {loading ? <p className="muted">Cargando docentes...</p> : null}
      {error ? <div className="message message-error">{error}</div> : null}

      {!loading && !error ? (
        <>
          <DataTable
            columns={[
              ...COLUMNS,
              {
                key: "detalle",
                label: "Detalle",
                render: (teacher) => (
                  <button
                    className="button secondary"
                    onClick={() => setSelected(teacher)}
                    type="button"
                  >
                    Ver detalle
                  </button>
                ),
              },
            ]}
            emptyMessage="No hay docentes que coincidan con la busqueda."
            rows={paged}
          />
          <Pagination
            onPageChange={setPage}
            page={currentPage}
            pageSize={PAGE_SIZE}
            total={filtered.length}
          />
        </>
      ) : null}

      {selected ? (
        <DetailPanel
          fields={[
            { label: "Nombre completo", value: fullName(selected) },
            { label: "Especialidad", value: selected.specialty },
            { label: "Puesto", value: selected.position },
            { label: "Codigo de Empleado", value: selected.employee_code },
            { label: "Telefono", value: selected.phone_number },
            {
              label: "Fecha de Nombramiento",
              value: selected.appointment_date,
            },
          ]}
          onClose={() => setSelected(null)}
          title={fullName(selected)}
        />
      ) : null}

      {creating ? (
        <FormModal
          fields={CREATE_FIELDS}
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
          title="Agregar docente"
        />
      ) : null}
    </section>
  );
}
