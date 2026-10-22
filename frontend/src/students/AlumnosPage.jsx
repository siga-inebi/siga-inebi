import { useLocation, useNavigate } from "react-router-dom";

import { useState } from "react";

import Avatar from "@mui/material/Avatar";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import AddIcon from "@mui/icons-material/Add";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import {
  STUDENT_FIELDS,
  STATUS_LABEL,
  STATUS_VARIANT,
  fullName,
  personPayload,
} from "./studentPresentation.js";

import { studentsService } from "@students/studentsService.js";
import { existingPersonField } from "@people/existingPersonSearch.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { useServerList } from "@shared/crud/useServerList.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { ExportCsvButton } from "@ui/buttons/ExportCsvButton.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { ViewDetailButton } from "@ui/table/ViewDetailButton.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

export function AlumnosPage() {
  const canSelectPerson = usePermissions().can(PERMISSION.PERSON_EDIT);
  const list = useServerList({
    queryKey: [...queryKeys.students.all, "list"],
    fetchPage: studentsService.listPage,
    defaultFilters: { status: "" },
    canIncludeInactive: true,
  });
  const searchPending = list.search.trim() !== (list.params.search ?? "");
  const updating = list.loading || list.fetching || searchPending;
  const location = useLocation();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(null);
  const handleSelect = (student) =>
    navigate(`/app/alumnos/${student.public_id}`, {
      state: { studentListLocation: `/app/alumnos${location.search}` },
    });

  const handleCreate = async (values) => {
    await studentsService.create({
      ...(values.person_public_id
        ? { person_public_id: values.person_public_id }
        : {}),
      person: personPayload(values),
      student_code: values.student_code,
      status: "pre_enrolled",
      photo: values.photo,
    });
    list.refresh();
    setCreating(null);
  };

  const columns = [
    {
      key: "foto",
      label: "Foto",
      render: (student) =>
        student.photo ? (
          <Avatar
            imgProps={{ decoding: "async", loading: "lazy" }}
            src={student.photo}
            sx={{ width: 32, height: 32 }}
            variant="rounded"
          />
        ) : (
          <Avatar sx={{ width: 32, height: 32 }} variant="rounded">
            <PersonOutlineIcon fontSize="small" />
          </Avatar>
        ),
    },
    { key: "nombre", label: "Nombre completo", render: fullName },
    {
      key: "codigo",
      label: "Código",
      render: (student) => student.student_code,
    },
    {
      key: "estado",
      label: "Estado",
      render: (student) => (
        <StatusChip
          label={STATUS_LABEL[student.status] ?? student.status}
          variant={STATUS_VARIANT[student.status] ?? "neutral"}
        />
      ),
    },
    {
      key: "detalle",
      label: "Detalle",
      align: "right",
      render: (student) => (
        <ViewDetailButton
          label={`Ver detalle de ${fullName(student)}`}
          onClick={() => handleSelect(student)}
        />
      ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Button
            onClick={async () =>
              setCreating({
                ...EMPTY_STUDENT,
                student_code: await suggestedOrBlank(studentsService.nextCode),
              })
            }
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo estudiante
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={
          list.error
            ? "No se pudo consultar el listado."
            : updating
              ? "Consultando estudiantes…"
              : `${list.count} estudiantes encontrados dentro de su alcance.`
        }
        title="Estudiantes"
      />

      <SectionCard fillHeight>
        <FilterBar
          actions={
            <ExportCsvButton
              fetchPage={studentsService.listPage}
              params={list.exportParams}
              columns={CSV_COLUMNS}
              filename="alumnos.csv"
              disabled={updating || Boolean(list.error)}
            />
          }
        >
          <SearchField
            debounceMs={0}
            onChange={list.setSearch}
            placeholder="Buscar por nombre, código o CUI…"
            value={list.search}
          />
          <FilterSelect
            label="Estado del expediente"
            emptyLabel="Todos los estados"
            options={STATUS_OPTIONS}
            value={list.filters.status}
            onChange={(value) => list.setFilter("status", value)}
          />
          <FormControlLabel
            control={
              <Switch
                checked={list.includeInactive}
                onChange={(event) =>
                  list.setIncludeInactive(event.target.checked)
                }
                size="small"
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
            <Button onClick={list.refresh}>Reintentar</Button>
          </Alert>
        ) : null}

        {!list.error ? (
          <SectionTableArea>
            <DataTable
              columns={columns}
              emptyMessage={
                list.search || list.filters.status || list.includeInactive
                  ? "Sin estudiantes para los filtros seleccionados."
                  : "No hay estudiantes registrados."
              }
              fillHeight
              loading={updating}
              onRowClick={handleSelect}
              pagination={list.pagination}
              rows={list.items}
            />
          </SectionTableArea>
        ) : null}
      </SectionCard>

      {creating ? (
        <EntityFormWindow
          description="El codigo se emite solo; el resto es lo que hay que capturar."
          fields={
            canSelectPerson
              ? [existingPersonField, ...STUDENT_FIELDS]
              : STUDENT_FIELDS
          }
          initialValues={creating}
          onCancel={() => setCreating(null)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear estudiante"
          title="Nuevo estudiante"
        />
      ) : null}
    </>
  );
}

const EMPTY_STUDENT = {
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
  student_code: "",
  photo: null,
};

const STATUS_OPTIONS = Object.entries(STATUS_LABEL).map(([value, label]) => ({
  value,
  label,
}));
const CSV_COLUMNS = [
  { label: "Nombre", value: fullName },
  { label: "Código", value: (item) => item.student_code },
  {
    label: "Estado",
    value: (item) => STATUS_LABEL[item.status] ?? item.status,
  },
];
