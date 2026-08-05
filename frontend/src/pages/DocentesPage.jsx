import { useEffect, useMemo, useState } from "react";

import { DataTable } from "../components/DataTable.jsx";
import { DetailPanel } from "../components/DetailPanel.jsx";
import { FormModal } from "../components/FormModal.jsx";
import { ImageLightbox } from "../components/ImageLightbox.jsx";
import { ListToolbar } from "../components/ListToolbar.jsx";
import { Pagination } from "../components/Pagination.jsx";
import { POSITION_OPTIONS } from "../mocks/teachers.js";
import { teachersService } from "../services/teachersService.js";
import { downloadCsv } from "../utils/csv.js";

const PAGE_SIZE = 5;

const CREATE_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  { name: "email", label: "Correo", type: "email" },
  { name: "phone_number", label: "Telefono" },
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
  { name: "photo", label: "Foto", type: "file", accept: "image/*" },
];

function fullName(teacher) {
  return `${teacher.person.first_name} ${teacher.person.last_name}`;
}

const COLUMNS = [
  {
    key: "foto",
    label: "Foto",
    render: (item) =>
      item.photo ? (
        <img alt="" className="avatar-thumb" src={item.photo} />
      ) : (
        "Sin foto"
      ),
  },
  { key: "nombre", label: "Nombre", render: fullName },
  { key: "especialidad", label: "Especialidad", render: (item) => item.specialty },
  { key: "puesto", label: "Puesto", render: (item) => item.position },
  {
    key: "codigo",
    label: "Codigo Empleado",
    render: (item) => item.employee_code,
  },
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
  const [editing, setEditing] = useState(null);
  const [viewingPhoto, setViewingPhoto] = useState(null);

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
      ],
      filtered
    );
  };

  const handleCreate = async (values) => {
    const created = await teachersService.create({
      person: {
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
      employee_code: values.employee_code,
      specialty: values.specialty,
      position: values.position,
      appointment_date: values.appointment_date || null,
      photo: values.photo,
    });
    setItems((current) => [...current, created]);
    setCreating(false);
  };

  const handleUpdate = async (values) => {
    const updated = await teachersService.update(editing.id, {
      person: {
        id: editing.person.id,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
      employee_code: values.employee_code,
      specialty: values.specialty,
      position: values.position,
      appointment_date: values.appointment_date || null,
      photo: values.photo,
    });
    setItems((current) =>
      current.map((item) => (item.id === updated.id ? updated : item))
    );
    setSelected(updated);
    setEditing(null);
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
          actions={
            <button
              className="button secondary"
              onClick={() => setEditing(selected)}
              type="button"
            >
              Editar
            </button>
          }
          fields={[
            { label: "Nombre completo", value: fullName(selected) },
            { label: "Especialidad", value: selected.specialty },
            { label: "Puesto", value: selected.position },
            { label: "Codigo de Empleado", value: selected.employee_code },
            {
              label: "Fecha de Nombramiento",
              value: selected.appointment_date,
            },
            { label: "Correo", value: selected.person.email },
            { label: "Telefono", value: selected.person.phone_number },
            {
              label: "Foto",
              value: selected.photo ? (
                <button
                  className="photo-preview-trigger"
                  onClick={() => setViewingPhoto(selected.photo)}
                  type="button"
                >
                  <img alt="" className="avatar-preview" src={selected.photo} />
                </button>
              ) : (
                "Sin foto"
              ),
            },
          ]}
          onClose={() => {
            setSelected(null);
            setViewingPhoto(null);
          }}
          title={fullName(selected)}
        />
      ) : null}

      {viewingPhoto ? (
        <ImageLightbox
          alt={fullName(selected)}
          downloadName={viewingPhoto.split("/").pop()}
          onClose={() => setViewingPhoto(null)}
          src={viewingPhoto}
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

      {editing ? (
        <FormModal
          fields={CREATE_FIELDS}
          initialValues={{
            first_name: editing.person.first_name,
            last_name: editing.person.last_name,
            email: editing.person.email,
            phone_number: editing.person.phone_number,
            specialty: editing.specialty,
            position: editing.position,
            appointment_date: editing.appointment_date,
            employee_code: editing.employee_code,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title="Editar docente"
        />
      ) : null}
    </section>
  );
}
