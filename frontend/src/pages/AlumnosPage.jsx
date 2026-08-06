import { useEffect, useMemo, useState } from "react";

import { DataTable } from "../components/DataTable.jsx";
import { DetailPanel } from "../components/DetailPanel.jsx";
import { FormModal } from "../components/FormModal.jsx";
import { ImageLightbox } from "../components/ImageLightbox.jsx";
import { ListToolbar } from "../components/ListToolbar.jsx";
import { Pagination } from "../components/Pagination.jsx";
import { studentsService } from "../services/studentsService.js";
import { downloadCsv } from "../utils/csv.js";

const PAGE_SIZE = 5;

const CREATE_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  { name: "email", label: "Correo", type: "email" },
  { name: "phone_number", label: "Telefono" },
  { name: "student_code", label: "Codigo de estudiante", required: true },
  { name: "photo", label: "Foto", type: "file", accept: "image/*" },
];

function fullName(student) {
  return `${student.person.first_name} ${student.person.last_name}`;
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
  { key: "codigo", label: "Codigo", render: (item) => item.student_code },
  { key: "estado", label: "Estado", render: (item) => item.status },
];

export function AlumnosPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [viewingPhoto, setViewingPhoto] = useState(null);

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
  }, [search]);

  const filtered = useMemo(
    () =>
      items.filter((student) =>
        fullName(student).toLowerCase().includes(search.trim().toLowerCase())
      ),
    [items, search]
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
        { label: "Codigo", value: (item) => item.student_code },
        { label: "Estado", value: (item) => item.status },
      ],
      filtered
    );
  };

  const handleCreate = async (values) => {
    const created = await studentsService.create({
      person: {
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
      student_code: values.student_code,
      status: "pre_enrolled",
      photo: values.photo,
    });
    setItems((current) => [...current, created]);
    setCreating(false);
  };

  const handleUpdate = async (values) => {
    const updated = await studentsService.update(editing.id, {
      person: {
        id: editing.person.id,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
      student_code: values.student_code,
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
        <p className="eyebrow">Sistema academico / Alumnos</p>
        <h1>Alumnos</h1>
        <p className="muted">Listado general de estudiantes.</p>
      </header>

      <ListToolbar
        createLabel="+ Agregar nuevo"
        onCreate={() => setCreating(true)}
        onExportCsv={handleExport}
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
            { label: "Codigo de estudiante", value: selected.student_code },
            { label: "Estado", value: selected.status },
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
          title="Agregar alumno"
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
            student_code: editing.student_code,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title="Editar alumno"
        />
      ) : null}
    </section>
  );
}
