import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import AddIcon from "@mui/icons-material/Add";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";

import { guardiansService } from "@guardians/guardiansService.js";
import { EntityFormDrawer } from "@shared/crud/EntityFormDrawer.jsx";
import { useLocalList } from "@shared/crud/useLocalList.js";
import { downloadCsv } from "@shared/utils/csv.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { DetailDrawer } from "@ui/layout/DetailDrawer.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

const GUARDIAN_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  { name: "email", label: "Correo (opcional)", type: "email" },
  { name: "phone_number", label: "Telefono (opcional)", type: "tel" },
];

const EMPTY_GUARDIAN = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
};

function fullName(guardian) {
  return `${guardian.person.first_name} ${guardian.person.last_name}`.trim();
}

const COLUMNS = [
  { key: "nombre", label: "Nombre completo", render: fullName },
  {
    key: "correo",
    label: "Correo",
    render: (item) => item.person.email || <MutedCell>Sin registrar</MutedCell>,
  },
  {
    key: "telefono",
    label: "Telefono",
    render: (item) => item.person.phone_number || <MutedCell>Sin registrar</MutedCell>,
  },
];

export function GuardiansPage() {
  const loadGuardians = useCallback(() => guardiansService.list(), []);
  const matches = useCallback(
    (guardian, query) => fullName(guardian).toLowerCase().includes(query),
    []
  );
  const list = useLocalList(loadGuardians, { matches });

  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const handleExport = () => {
    downloadCsv(
      "padres-de-familia.csv",
      [
        { label: "Nombre", value: fullName },
        { label: "Correo", value: (item) => item.person.email },
        { label: "Telefono", value: (item) => item.person.phone_number },
      ],
      list.filtered
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
    list.addItem(created);
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
    list.replaceItem(updated, (item) => item.id === updated.id);
    setSelected(updated);
    setEditing(null);
  };

  return (
    <>
      <PageHeader
        action={
          <Button
            onClick={() => setCreating(true)}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo encargado
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={`${list.filtered.length} de ${list.all.length} encargados registrados.`}
        title="Padres de familia"
      />

      <SectionCard fillHeight>
        <FilterBar
          actions={
            <Button
              onClick={handleExport}
              size="small"
              startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Exportar CSV
            </Button>
          }
        >
          <SearchField
            onChange={list.setSearch}
            placeholder="Buscar por nombre…"
            value={list.search}
          />
        </FilterBar>

        <SectionTableArea>
          <DataTable
            columns={COLUMNS}
            emptyMessage={
              list.search
                ? "Sin resultados para la busqueda."
                : "Todavia no hay encargados registrados."
            }
            fillHeight
            loading={list.loading}
            onRowClick={setSelected}
            pagination={list.pagination}
            rows={list.items}
          />
        </SectionTableArea>
      </SectionCard>

      <DetailDrawer
        actions={
          selected ? (
            <Button onClick={() => setEditing(selected)} variant="contained">
              Editar
            </Button>
          ) : null
        }
        fields={
          selected
            ? [
                { label: "Nombre completo", value: fullName(selected) },
                { label: "Correo", value: selected.person.email },
                { label: "Telefono", value: selected.person.phone_number },
              ]
            : []
        }
        onClose={() => setSelected(null)}
        open={Boolean(selected)}
        title={selected ? fullName(selected) : ""}
      />

      <EntityFormDrawer
        fields={GUARDIAN_FIELDS}
        initialValues={EMPTY_GUARDIAN}
        key={creating ? "create-open" : "create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreate}
        open={creating}
        submitLabel="Crear encargado"
        title="Nuevo encargado"
      />

      {editing ? (
        <EntityFormDrawer
          fields={GUARDIAN_FIELDS}
          initialValues={{
            first_name: editing.person.first_name,
            last_name: editing.person.last_name,
            email: editing.person.email ?? "",
            phone_number: editing.person.phone_number ?? "",
          }}
          key={editing.id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${fullName(editing)}`}
        />
      ) : null}
    </>
  );
}
