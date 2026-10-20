import { useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import AddIcon from "@mui/icons-material/Add";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";

import { guardiansService } from "@guardians/guardiansService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { downloadCsv } from "@shared/utils/csv.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { ViewDetailButton } from "@ui/table/ViewDetailButton.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { DetailWindow } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

const GUARDIAN_FIELDS = [
  { name: "first_name", label: "Nombres", required: true },
  { name: "last_name", label: "Apellidos", required: true },
  {
    name: "cui",
    label: "CUI",
    required: true,
    help: "13 dígitos, sin guiones.",
  },
  {
    name: "birth_date",
    label: "Fecha de nacimiento",
    type: "date",
    required: true,
  },
  {
    name: "sex",
    label: "Sexo",
    type: "select",
    required: true,
    options: [
      { value: "female", label: "Femenino" },
      { value: "male", label: "Masculino" },
    ],
  },
  { name: "nationality", label: "Nacionalidad", required: true },
  { name: "phone_number", label: "Teléfono", type: "tel", required: true },
  { name: "email", label: "Correo", type: "email" },
  { name: "address", label: "Dirección", required: true, span: "full" },
  { name: "department", label: "Departamento", required: true },
  { name: "municipality", label: "Municipio", required: true },
];

const EMPTY_GUARDIAN = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
  cui: "",
  birth_date: "",
  sex: "",
  nationality: "Guatemalteca",
  address: "",
  department: "",
  municipality: "",
};

const GUARDIAN_EDIT_FIELDS = GUARDIAN_FIELDS.filter(
  (field) => field.name !== "cui" && field.name !== "birth_date"
);

function fullName(guardian) {
  return `${guardian.person.first_name} ${guardian.person.last_name}`.trim();
}

const personPayload = (values) =>
  Object.fromEntries(
    Object.entries({
      first_name: values.first_name,
      last_name: values.last_name,
      cui: values.cui,
      birth_date: values.birth_date,
      sex: values.sex,
      nationality: values.nationality,
      email: values.email,
      phone_number: values.phone_number,
      address: values.address,
      department: values.department,
      municipality: values.municipality,
    }).filter(([, value]) => value !== "" && value != null)
  );

function guardianColumns({ onView }) {
  return [
    { key: "nombre", label: "Nombre completo", render: fullName },
    {
      key: "correo",
      label: "Correo",
      render: (item) =>
        item.person.email || <MutedCell>Sin registrar</MutedCell>,
    },
    {
      key: "telefono",
      label: "Telefono",
      render: (item) =>
        item.person.phone_number || <MutedCell>Sin registrar</MutedCell>,
    },
    {
      key: "detalle",
      label: "Detalle",
      align: "right",
      render: (guardian) => (
        <ViewDetailButton
          label={`Ver detalle de ${fullName(guardian)}`}
          onClick={() => onView(guardian)}
        />
      ),
    },
  ];
}

export function GuardiansPage() {
  // Solo la pagina visible: la busqueda (nombre o CUI) y la paginacion las
  // resuelve el backend, no el navegador.
  const list = useServerList({
    queryKey: queryKeys.guardians.all,
    fetchPage: guardiansService.listPage,
  });

  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");

  // La exportacion si recorre todas las paginas, con la busqueda vigente.
  const handleExport = async () => {
    setExporting(true);
    setExportError("");
    try {
      const rows = await guardiansService.list(list.exportParams);
      downloadCsv(
        "padres-de-familia.csv",
        [
          { label: "Nombre", value: fullName },
          { label: "Correo", value: (item) => item.person.email },
          { label: "Telefono", value: (item) => item.person.phone_number },
        ],
        rows
      );
    } catch (requestError) {
      setExportError(requestError.message);
    } finally {
      setExporting(false);
    }
  };

  const handleCreate = async (values) => {
    await guardiansService.create({
      person: personPayload(values),
    });
    list.refresh();
    setCreating(false);
  };

  const handleUpdate = async (values) => {
    const updated = await guardiansService.update(editing.id, {
      person: {
        public_id: editing.person.public_id,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        phone_number: values.phone_number,
        sex: values.sex,
        nationality: values.nationality,
        address: values.address,
        department: values.department,
        municipality: values.municipality,
      },
    });
    list.refresh();
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
        subtitle={`${list.count} encargados registrados.`}
        title="Padres de familia"
      />

      <SectionCard fillHeight>
        <FilterBar
          actions={
            <Button
              disabled={exporting}
              onClick={handleExport}
              size="small"
              startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              {exporting ? "Exportando…" : "Exportar CSV"}
            </Button>
          }
        >
          <SearchField
            onChange={list.setSearch}
            placeholder="Buscar por nombre o CUI…"
            value={list.search}
          />
        </FilterBar>

        {list.error || exportError ? (
          <Alert
            role="alert"
            severity="error"
            sx={{ mx: { xs: 1.5, md: 2 }, mt: 1.5 }}
          >
            {list.error || exportError}
          </Alert>
        ) : null}

        <SectionTableArea>
          <DataTable
            columns={guardianColumns({ onView: setSelected })}
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

      <DetailWindow
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

      <EntityFormWindow
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
        <EntityFormWindow
          fields={GUARDIAN_EDIT_FIELDS}
          initialValues={{
            first_name: editing.person.first_name,
            last_name: editing.person.last_name,
            sex: editing.person.sex ?? "",
            nationality: editing.person.nationality ?? "",
            email: editing.person.email ?? "",
            phone_number: editing.person.phone_number ?? "",
            address: editing.person.address ?? "",
            department: editing.person.department ?? "",
            municipality: editing.person.municipality ?? "",
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
