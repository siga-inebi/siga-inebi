import { lazy, Suspense, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import AddIcon from "@mui/icons-material/Add";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";

import { guardiansService } from "@guardians/guardiansService.js";
import { existingPersonField } from "@people/existingPersonSearch.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { ExportCsvButton } from "@ui/buttons/ExportCsvButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { ViewDetailButton } from "@ui/table/ViewDetailButton.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

const GuardianDeactivationDialog = lazy(() =>
  import("@guardians/GuardianDeactivationDialog.jsx").then((module) => ({
    default: module.GuardianDeactivationDialog,
  }))
);

const GuardianWindow = lazy(() =>
  import("./GuardianWindow.jsx").then((module) => ({
    default: module.GuardianWindow,
  }))
);

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
      label: "Teléfono",
      render: (item) =>
        item.person.phone_number || <MutedCell>Sin registrar</MutedCell>,
    },
    {
      key: "actividad",
      label: "Actividad",
      render: (guardian) => (
        <StatusChip
          label={activityLabel(guardian)}
          variant={guardian.is_active === false ? "neutral" : "success"}
        />
      ),
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
  const canSelectPerson = usePermissions().can(PERMISSION.PERSON_EDIT);
  const list = useServerList({
    queryKey: [...queryKeys.guardians.all, "list"],
    fetchPage: guardiansService.listPage,
    canIncludeInactive: true,
  });
  const updating =
    list.loading ||
    list.fetching ||
    list.search.trim() !== (list.params.search ?? "");

  const [selected, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);
  const [deactivating, setDeactivating] = useState(null);
  const [deactivationNotice, setDeactivationNotice] = useState("");

  const handleCreate = async (values) => {
    await guardiansService.create({
      ...(values.person_public_id
        ? { person_public_id: values.person_public_id }
        : {}),
      person: personPayload(values),
    });
    list.refresh();
    setCreating(false);
  };

  const handleUpdate = async (values) => {
    const updated = await guardiansService.update(selected.id, {
      person: {
        public_id: selected.person.public_id,
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
  };

  return (
    <>
      <PageHeader
        action={
          <Button
            disabled={Boolean(deactivating)}
            onClick={() => setCreating(true)}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo encargado
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={
          list.error
            ? "No se pudo consultar el listado."
            : updating
              ? "Consultando encargados\u2026"
              : `${list.count} encargados encontrados.`
        }
        title="Padres de familia"
      />

      {deactivationNotice ? (
        <Alert role="status" severity="success" sx={{ mb: 2 }}>
          {deactivationNotice}
        </Alert>
      ) : null}

      <SectionCard fillHeight>
        <FilterBar
          actions={
            <ExportCsvButton
              fetchPage={guardiansService.listPage}
              params={list.exportParams}
              filename="padres-de-familia.csv"
              columns={CSV_COLUMNS}
              disabled={updating || Boolean(list.error)}
            />
          }
          onClear={
            list.search || list.includeInactive
              ? () => {
                  list.setSearch("");
                  list.setIncludeInactive(false);
                }
              : undefined
          }
        >
          <SearchField
            debounceMs={0}
            onChange={list.setSearch}
            placeholder="Buscar por nombre o CUI…"
            value={list.search}
          />
          <FormControlLabel
            control={
              <Switch
                checked={list.includeInactive}
                size="small"
                onChange={(event) =>
                  list.setIncludeInactive(event.target.checked)
                }
              />
            }
            label="Mostrar desactivados"
          />
        </FilterBar>

        {list.error ? (
          <Alert
            role="alert"
            severity="error"
            sx={{ mx: { xs: 1.5, md: 2 }, mt: 1.5 }}
          >
            {list.error}
            <Button onClick={list.refresh}>Reintentar listado</Button>
            {list.page > 1 ? (
              <Button onClick={() => list.goToPage(1)}>
                Volver a primera página
              </Button>
            ) : null}
          </Alert>
        ) : null}

        {!list.error ? (
          <SectionTableArea>
            <DataTable
              columns={guardianColumns({ onView: setSelected })}
              emptyMessage={
                list.search || list.includeInactive
                  ? "Sin encargados para los filtros seleccionados."
                  : "No hay encargados registrados."
              }
              fillHeight
              loading={updating}
              onRowClick={(guardian) => {
                if (!deactivating) setSelected(guardian);
              }}
              pagination={list.pagination}
              rows={list.items}
            />
          </SectionTableArea>
        ) : null}
      </SectionCard>

      {selected ? (
        <Suspense fallback={<p role="status">Preparando encargado…</p>}>
          <GuardianWindow
            editFields={GUARDIAN_EDIT_FIELDS}
            editValues={guardianEditValues}
            fields={[
              { label: "Nombre completo", value: fullName(selected) },
              { label: "Correo", value: selected.person.email },
              { label: "Teléfono", value: selected.person.phone_number },
              { label: "Actividad", value: activityLabel(selected) },
            ]}
            guardian={selected}
            key={selected.id}
            onClose={() => setSelected(null)}
            onDeactivate={
              selected.is_active && selected.actions?.deactivate === true
                ? () => {
                    setDeactivating(selected);
                    setSelected(null);
                  }
                : undefined
            }
            onSave={handleUpdate}
            title={fullName(selected)}
          />
        </Suspense>
      ) : null}

      {deactivating ? (
        <Suspense fallback={<p role="status">Preparando confirmación…</p>}>
          <GuardianDeactivationDialog
            guardian={deactivating}
            onCancel={() => {
              setSelected(deactivating);
              setDeactivating(null);
            }}
            onCompleted={() => {
              setDeactivating(null);
              setDeactivationNotice(
                "Encargado desactivado. El historial se conserva."
              );
              list.refresh();
            }}
          />
        </Suspense>
      ) : null}

      <EntityFormWindow
        fields={
          canSelectPerson
            ? [existingPersonField, ...GUARDIAN_FIELDS]
            : GUARDIAN_FIELDS
        }
        initialValues={EMPTY_GUARDIAN}
        key={creating ? "create-open" : "create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreate}
        open={creating}
        submitLabel="Crear encargado"
        title="Nuevo encargado"
      />
    </>
  );
}

const guardianEditValues = (guardian) => ({
  first_name: guardian.person.first_name,
  last_name: guardian.person.last_name,
  sex: guardian.person.sex ?? "",
  nationality: guardian.person.nationality ?? "",
  email: guardian.person.email ?? "",
  phone_number: guardian.person.phone_number ?? "",
  address: guardian.person.address ?? "",
  department: guardian.person.department ?? "",
  municipality: guardian.person.municipality ?? "",
});

const activityLabel = (guardian) =>
  guardian.is_active === false ? "Desactivado" : "Activo";
const CSV_COLUMNS = [
  { label: "Nombre", value: fullName },
  { label: "Correo", value: (item) => item.person.email },
  { label: "Tel\u00e9fono", value: (item) => item.person.phone_number },
  { label: "Actividad", value: activityLabel },
];
