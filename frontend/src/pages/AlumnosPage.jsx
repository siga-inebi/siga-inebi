import { useEffect, useMemo, useState } from "react";

import { DataTable } from "../components/DataTable.jsx";
import { DetailPanel } from "../components/DetailPanel.jsx";
import { FormModal } from "../components/FormModal.jsx";
import { ListToolbar } from "../components/ListToolbar.jsx";
import { Pagination } from "../components/Pagination.jsx";
import { SECTION_OPTIONS } from "../mocks/students.js";
import { studentsService } from "../services/studentsService.js";
import { downloadCsv } from "../utils/csv.js";

const PAGE_SIZE = 5;

const CREATE_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  {
    name: "gender",
    label: "Genero",
    type: "select",
    options: ["Femenino", "Masculino"],
    required: true,
  },
  { name: "student_code", label: "Codigo de estudiante", required: true },
  { name: "birth_date", label: "Fecha de nacimiento", type: "date" },
  { name: "cui", label: "CUI" },
  { name: "age", label: "Edad", type: "number" },
  { name: "clave", label: "Clave" },
];

function fullName(student) {
  return `${student.first_name} ${student.last_name}`;
}

function sectionLabel(student) {
  return student.section
    ? `${student.section.grade} "${student.section.name}"`
    : "Sin matricular";
}

const COLUMNS = [
  { key: "nombre", label: "Nombre", render: fullName },
  { key: "genero", label: "Genero", render: (item) => item.gender },
  { key: "codigo", label: "Codigo", render: (item) => item.student_code },
  { key: "seccion", label: "Seccion", render: sectionLabel },
  { key: "edad", label: "Edad", render: (item) => item.age },
];

export function AlumnosPage() {
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
    studentsService
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
      items.filter((student) => {
        const matchesSearch = fullName(student)
          .toLowerCase()
          .includes(search.trim().toLowerCase());
        const matchesSection =
          !sectionFilter || sectionLabel(student) === sectionFilter;
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
      "alumnos.csv",
      [
        { label: "Nombre", value: fullName },
        { label: "Genero", value: (item) => item.gender },
        { label: "Codigo", value: (item) => item.student_code },
        { label: "Seccion", value: sectionLabel },
        { label: "Edad", value: (item) => item.age },
      ],
      filtered
    );
  };

  const handleCreate = async (values) => {
    const created = await studentsService.create({
      ...values,
      age: values.age ? Number(values.age) : null,
      status: "pre_enrolled",
      section: null,
    });
    setItems((current) => [...current, created]);
    setCreating(false);
  };

  return (
    <section className="list-page">
      <header className="list-page-header">
        <p className="eyebrow">Sistema academico / Alumnos</p>
        <h1>Alumnos</h1>
        <p className="muted">Listado general de estudiantes.</p>
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

      {loading ? <p className="muted">Cargando alumnos...</p> : null}
      {error ? <div className="message message-error">{error}</div> : null}

      {!loading && !error ? (
        <>
          <DataTable
            columns={[
              ...COLUMNS,
              {
                key: "detalle",
                label: "Detalle",
                render: (student) => (
                  <button
                    className="button secondary"
                    onClick={() => setSelected(student)}
                    type="button"
                  >
                    Ver detalle
                  </button>
                ),
              },
            ]}
            emptyMessage="No hay alumnos que coincidan con la busqueda."
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
            { label: "Genero", value: selected.gender },
            { label: "Nombre completo", value: fullName(selected) },
            { label: "Fecha de nacimiento", value: selected.birth_date },
            { label: "CUI", value: selected.cui },
            { label: "Edad", value: selected.age },
            { label: "Codigo de estudiante", value: selected.student_code },
            { label: "Seccion", value: sectionLabel(selected) },
            { label: "Clave", value: selected.clave },
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
          title="Agregar alumno"
        />
      ) : null}
    </section>
  );
}
