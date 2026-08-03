import { useEffect, useMemo, useState } from "react";

import { DataTable } from "../components/DataTable.jsx";
import { DetailPanel } from "../components/DetailPanel.jsx";
import { FormModal } from "../components/FormModal.jsx";
import { ListToolbar } from "../components/ListToolbar.jsx";
import { Pagination } from "../components/Pagination.jsx";
import { SECTION_OPTIONS } from "../mocks/students.js";
import { guardiansService } from "../services/guardiansService.js";
import { downloadCsv } from "../utils/csv.js";

const PAGE_SIZE = 5;

// El mockup no muestra un modal "Agregar" propio para Padres; se sigue el
// mismo patron que el modal de Docentes (unico modal con diseño real en
// los mockups), usando los campos ya conocidos de esta entidad. No incluye
// "alumnos asignados": esa relacion es matricula (StudentGuardianRelation),
// fuera de alcance de esta entrega (ver src/mocks/students.js).
const CREATE_FIELDS = [
  { name: "full_name", label: "Nombres completos", required: true },
  { name: "occupation", label: "Ocupacion" },
  { name: "phone_number", label: "Telefono" },
];

function fullName(guardian) {
  return [guardian.first_name, guardian.last_name].filter(Boolean).join(" ");
}

function sectionLabel(entry) {
  return `${entry.section.grade} "${entry.section.name}"`;
}

function assignedStudentsSummary(guardian) {
  const count = guardian.assigned_students.length;
  if (count === 0) {
    return "Sin alumnos asignados";
  }
  const sections = guardian.assigned_students.map(sectionLabel).join(", ");
  return `${count} alumno${count === 1 ? "" : "s"} — ${sections}`;
}

const COLUMNS = [
  { key: "nombre", label: "Nombre", render: fullName },
  { key: "ocupacion", label: "Ocupacion", render: (item) => item.occupation },
  { key: "telefono", label: "Telefono", render: (item) => item.phone_number },
  {
    key: "asignados",
    label: "Alumnos asignados",
    render: assignedStudentsSummary,
  },
];

export function PadresPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [sectionFilter, setSectionFilter] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let active = true;
    guardiansService
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
  }, [search, sectionFilter]);

  const filtered = useMemo(
    () =>
      items.filter((guardian) => {
        const matchesSearch = fullName(guardian)
          .toLowerCase()
          .includes(search.trim().toLowerCase());
        const matchesSection =
          !sectionFilter ||
          guardian.assigned_students.some(
            (entry) => sectionLabel(entry) === sectionFilter
          );
        return matchesSearch && matchesSection;
      }),
    [items, search, sectionFilter]
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paged = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const handleExport = () => {
    downloadCsv(
      "padres-de-familia.csv",
      [
        { label: "Nombre", value: fullName },
        { label: "Ocupacion", value: (item) => item.occupation },
        { label: "Telefono", value: (item) => item.phone_number },
        { label: "Alumnos asignados", value: assignedStudentsSummary },
      ],
      filtered
    );
  };

  const handleCreate = async (values) => {
    const { full_name: fullNameInput, ...rest } = values;
    const created = await guardiansService.create({
      ...rest,
      first_name: fullNameInput,
      last_name: "",
      assigned_students: [],
    });
    setItems((current) => [...current, created]);
    setCreating(false);
  };

  return (
    <section className="list-page">
      <header className="list-page-header">
        <p className="eyebrow">Sistema academico / Padres y Encargados</p>
        <h1>Padres y Encargados</h1>
        <p className="muted">Listado de padres y encargados.</p>
      </header>

      <ListToolbar
        createLabel="+ Agregar nuevo"
        filterOptions={SECTION_OPTIONS}
        filterValue={sectionFilter}
        onCreate={() => setCreating(true)}
        onExportCsv={handleExport}
        onFilterChange={setSectionFilter}
        onSearchChange={setSearch}
        searchValue={search}
      />

      {loading ? <p className="muted">Cargando padres de familia...</p> : null}
      {error ? <div className="message message-error">{error}</div> : null}

      {!loading && !error ? (
        <>
          <DataTable
            columns={[
              ...COLUMNS,
              {
                key: "detalle",
                label: "Detalle",
                render: (guardian) => (
                  <button
                    className="button secondary"
                    onClick={() => setSelected(guardian)}
                    type="button"
                  >
                    Ver detalle
                  </button>
                ),
              },
            ]}
            emptyMessage="No hay padres o encargados que coincidan con la busqueda."
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
            { label: "Ocupacion", value: selected.occupation },
            { label: "Telefono", value: selected.phone_number },
            {
              label: "Alumnos asignados",
              value:
                selected.assigned_students.length === 0 ? (
                  "Sin alumnos asignados"
                ) : (
                  <ul className="detail-list">
                    {selected.assigned_students.map((entry) => (
                      <li key={entry.student_id}>
                        {entry.full_name} ({entry.relationship_label},{" "}
                        {sectionLabel(entry)})
                      </li>
                    ))}
                  </ul>
                ),
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
          title="Agregar padre o encargado"
        />
      ) : null}
    </section>
  );
}
