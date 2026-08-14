import { useEffect, useMemo, useState } from "react";

import { DataTable } from "../components/DataTable.jsx";
import { DetailPanel } from "../components/DetailPanel.jsx";
import { FormModal } from "../components/FormModal.jsx";
import { ListToolbar } from "../components/ListToolbar.jsx";
import { Pagination } from "../components/Pagination.jsx";
import { guardiansService } from "../services/guardiansService.js";
import { downloadCsv } from "../utils/csv.js";

const PAGE_SIZE = 5;

const CREATE_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  { name: "email", label: "Correo", type: "email" },
  { name: "phone_number", label: "Telefono" },
];

function fullName(guardian) {
  return `${guardian.person.first_name} ${guardian.person.last_name}`;
}

const COLUMNS = [
  { key: "nombre", label: "Nombre", render: fullName },
  { key: "correo", label: "Correo", render: (item) => item.person.email },
  {
    key: "telefono",
    label: "Telefono",
    render: (item) => item.person.phone_number,
  },
];

export function GuardiansPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);

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
  }, [search]);

  const filtered = useMemo(
    () =>
      items.filter((guardian) =>
        fullName(guardian).toLowerCase().includes(search.trim().toLowerCase())
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
      "padres-de-familia.csv",
      [
        { label: "Nombre", value: fullName },
        { label: "Correo", value: (item) => item.person.email },
        { label: "Telefono", value: (item) => item.person.phone_number },
      ],
      filtered
    );
  };

  const handleCreate = async (values) => {
    const created = await guardiansService.create({
      person: {
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
    });
    setItems((current) => [...current, created]);
    setCreating(false);
  };

  const handleUpdate = async (values) => {
    const updated = await guardiansService.update(editing.id, {
      person: {
        id: editing.person.id,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
      },
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
        <p className="eyebrow">Sistema academico / Padres y Encargados</p>
        <h1>Padres y Encargados</h1>
        <p className="muted">Listado de padres y encargados.</p>
      </header>

      <ListToolbar
        createLabel="+ Agregar nuevo"
        onCreate={() => setCreating(true)}
        onExportCsv={handleExport}
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
            { label: "Correo", value: selected.person.email },
            { label: "Telefono", value: selected.person.phone_number },
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

      {editing ? (
        <FormModal
          fields={CREATE_FIELDS}
          initialValues={{
            first_name: editing.person.first_name,
            last_name: editing.person.last_name,
            email: editing.person.email,
            phone_number: editing.person.phone_number,
          }}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          submitLabel="Guardar cambios"
          title="Editar padre o encargado"
        />
      ) : null}
    </section>
  );
}
