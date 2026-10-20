import { lazy, Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import AddIcon from "@mui/icons-material/Add";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import { GrantAccessButton } from "@auth/GrantAccessButton.jsx";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { teachersService } from "@teachers/teachersService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { useServerList } from "@shared/crud/useServerList.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { ExportCsvButton } from "@ui/buttons/ExportCsvButton.jsx";
import { formatDate } from "@shared/utils/format.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { ViewDetailButton } from "@ui/table/ViewDetailButton.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { DetailWindow } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

// "Qué imparte" trae el servicio académico: se descarga al abrir la ficha.
const TeacherAssignments = lazy(() =>
  import("@teachers/TeacherAssignments.jsx").then((module) => ({
    default: module.TeacherAssignments,
  }))
);

// Los documentos solo se consultan a demanda: fuera del chunk de la ruta.
const TeacherDocumentsWindow = lazy(() =>
  import("@teachers/TeacherDocumentsWindow.jsx").then((module) => ({
    default: module.TeacherDocumentsWindow,
  }))
);

// La foto ampliada solo se abre a demanda: fuera del chunk de la ruta.
const ImageDialog = lazy(() =>
  import("@ui/display/ImageDialog.jsx").then((module) => ({
    default: module.ImageDialog,
  }))
);

const TeacherDeactivationDialog = lazy(() =>
  import("@teachers/TeacherDeactivationDialog.jsx").then((module) => ({
    default: module.TeacherDeactivationDialog,
  }))
);

const TEACHER_FIELDS = [
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
  { name: "specialty", label: "Especialidad", required: true },
  {
    name: "position",
    label: "Puesto",
    type: "select",
    options: [],
    required: true,
  },
  {
    name: "appointment_date",
    label: "Fecha de nombramiento (opcional)",
    type: "date",
  },
  {
    name: "employee_code",
    label: "Código de empleado",
    help: "Se genera automáticamente. Cámbielo si ya figura en contratos o planilla.",
  },
  { name: "photo", label: "Foto (opcional)", type: "file", accept: "image/*" },
];

function fullName(teacher) {
  return `${teacher.person.first_name} ${teacher.person.last_name}`.trim();
}

const personPayload = (values) => ({
  ...Object.fromEntries(
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
  ),
});

export function DocentesPage() {
  const canSelectPerson = usePermissions().can(PERMISSION.PERSON_EDIT);
  const list = useServerList({
    queryKey: [...queryKeys.teachers.all, "list"],
    fetchPage: teachersService.listPage,
    defaultFilters: { position: "" },
    canIncludeInactive: true,
  });
  const positions = useQuery({
    queryKey: [...queryKeys.teachers.all, "positions"],
    queryFn: teachersService.listPositions,
  });
  const positionOptions = positions.data ?? [];
  // Conserva visible un filtro de URL mientras llega el catálogo o si deja
  // de estar publicado. La API valida el valor; no se ofrece en los formularios.
  const filterPositionOptions =
    list.filters.position &&
    !positionOptions.some((option) => option.value === list.filters.position)
      ? [
          ...positionOptions,
          { value: list.filters.position, label: list.filters.position },
        ]
      : positionOptions;
  const positionsReady =
    !positions.isPending && !positions.isError && positionOptions.length > 0;
  const fields = TEACHER_FIELDS.map((field) =>
    field.name === "position" ? { ...field, options: positionOptions } : field
  );
  const editFields = fields.filter(
    (field) => field.name !== "cui" && field.name !== "birth_date"
  );
  const searchPending = list.search.trim() !== (list.params.search ?? "");
  const updating = list.loading || list.fetching || searchPending;
  const positionLabel = (value) =>
    positionOptions.find((option) => option.value === value)?.label ?? value;

  const [selected, setSelected] = useState(null);
  // "Qué imparte" consulta un listado que exige administrar asignaciones.
  const canSeeAssignments = usePermissions().can(PERMISSION.SCOPE_ASSIGN);
  const [deactivating, setDeactivating] = useState(null);
  const [deactivationNotice, setDeactivationNotice] = useState("");
  const [editing, setEditing] = useState(null);
  // Valores iniciales, no un booleano: ver el comentario homonimo en
  // AlumnosPage. El codigo sugerido se pide al abrir.
  const [creating, setCreating] = useState(null);
  const [personField, setPersonField] = useState(null);
  const [viewingPhoto, setViewingPhoto] = useState(null);
  const [documentsFor, setDocumentsFor] = useState(null);

  const buildPayload = (values) => ({
    ...(values.person_public_id
      ? { person_public_id: values.person_public_id }
      : {}),
    person: personPayload(values),
    employee_code: values.employee_code,
    specialty: values.specialty,
    position: values.position,
    appointment_date: values.appointment_date || null,
    photo: values.photo,
  });

  const handleCreate = async (values) => {
    await teachersService.create(buildPayload(values));
    list.refresh();
    setCreating(null);
  };

  const handleUpdate = async (values) => {
    const updated = await teachersService.update(editing.id, {
      ...buildPayload(values),
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

  const columns = [
    {
      key: "foto",
      label: "Foto",
      render: (teacher) =>
        teacher.photo ? (
          <Avatar
            src={teacher.photo}
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
      key: "especialidad",
      label: "Especialidad",
      render: (item) => item.specialty,
    },
    {
      key: "puesto",
      label: "Puesto",
      render: (item) => (
        <StatusChip label={positionLabel(item.position)} variant="primary" />
      ),
    },
    {
      key: "codigo",
      label: "Código de empleado",
      render: (item) => item.employee_code,
    },
    {
      key: "detalle",
      label: "Detalle",
      align: "right",
      render: (teacher) => (
        <ViewDetailButton
          label={`Ver detalle de ${fullName(teacher)}`}
          onClick={() => setSelected(teacher)}
        />
      ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Button
            disabled={!positionsReady || Boolean(deactivating)}
            onClick={async () => {
              const personModule = canSelectPerson
                ? await import("@people/existingPersonSearch.js")
                : null;
              setPersonField(personModule?.existingPersonField ?? null);
              setCreating({
                ...EMPTY_TEACHER,
                employee_code: await suggestedOrBlank(teachersService.nextCode),
              });
            }}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo registro
          </Button>
        }
        breadcrumb="Comunidad educativa"
        subtitle={
          list.error
            ? "No se pudo consultar el listado."
            : updating
              ? "Consultando personal docente y administrativo\u2026"
              : `${list.count} registros de personal docente y administrativo.`
        }
        title="Docentes y administrativos"
      />

      {deactivationNotice ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          {deactivationNotice}
        </Alert>
      ) : null}
      <SectionCard fillHeight>
        <FilterBar
          actions={
            <ExportCsvButton
              fetchPage={teachersService.listPage}
              params={list.exportParams}
              columns={[
                { label: "Nombre", value: fullName },
                { label: "Especialidad", value: (item) => item.specialty },
                {
                  label: "Puesto",
                  value: (item) => positionLabel(item.position),
                },
                {
                  label: "C\u00f3digo de empleado",
                  value: (item) => item.employee_code,
                },
              ]}
              filename="docentes.csv"
              disabled={updating || Boolean(list.error)}
            />
          }
          onClear={
            list.search || list.filters.position || list.includeInactive
              ? () => {
                  list.setSearch("");
                  list.setFilters({ position: "", include_inactive: "" });
                }
              : undefined
          }
        >
          <SearchField
            debounceMs={0}
            onChange={list.setSearch}
            placeholder="Buscar por nombre, código o CUI…"
            value={list.search}
          />
          <FilterSelect
            label="Filtrar por puesto"
            minWidth={190}
            emptyLabel="Todos los puestos"
            loading={positions.isPending}
            onChange={(value) => list.setFilter("position", value)}
            options={filterPositionOptions}
            value={list.filters.position}
          />
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={list.includeInactive}
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
          </Alert>
        ) : null}

        {!list.error ? (
          <SectionTableArea>
            <DataTable
              columns={columns}
              emptyMessage={
                list.search || list.filters.position || list.includeInactive
                  ? "Sin datos para los filtros seleccionados."
                  : "No hay personal registrado."
              }
              fillHeight
              loading={updating}
              onRowClick={(teacher) => {
                if (!deactivating) setSelected(teacher);
              }}
              pagination={list.pagination}
              rows={list.items}
            />
          </SectionTableArea>
        ) : null}
      </SectionCard>

      {positions.isError ||
      (!positions.isPending && positionOptions.length === 0) ? (
        <Alert severity="error" role="alert" sx={{ mt: 2 }}>
          No se pudo cargar el catálogo de puestos. Reintente para crear o
          editar un registro.
          <Button onClick={() => positions.refetch()}>
            Reintentar puestos
          </Button>
        </Alert>
      ) : null}

      <DetailWindow
        actions={
          selected ? (
            <>
              <GrantAccessButton person={selected.person} size="medium" />
              <Button onClick={() => setDocumentsFor(selected)} variant="text">
                Documentos
              </Button>
              <Button
                disabled={!positionsReady}
                onClick={() => setEditing(selected)}
                variant="contained"
              >
                Editar
              </Button>
              {selected.actions?.deactivate === true ? (
                <Button
                  color="error"
                  onClick={() => {
                    setDeactivating(selected);
                    setSelected(null);
                  }}
                >
                  Desactivar docente
                </Button>
              ) : null}
            </>
          ) : null
        }
        fields={
          selected
            ? [
                { label: "Nombre completo", value: fullName(selected) },
                {
                  label: "Actividad del perfil",
                  value: (
                    <StatusChip
                      label={
                        selected.is_active === false ? "Desactivado" : "Activo"
                      }
                      variant={
                        selected.is_active === false ? "neutral" : "success"
                      }
                    />
                  ),
                },
                { label: "Especialidad", value: selected.specialty },
                {
                  label: "Puesto",
                  value: (
                    <StatusChip
                      label={positionLabel(selected.position)}
                      variant="primary"
                    />
                  ),
                },
                { label: "Código de empleado", value: selected.employee_code },
                {
                  label: "Fecha de nombramiento",
                  value: selected.appointment_date
                    ? formatDate(selected.appointment_date)
                    : null,
                },
                { label: "Correo", value: selected.person.email },
                { label: "Teléfono", value: selected.person.phone_number },
                {
                  label: "Foto",
                  value: selected.photo ? (
                    <ButtonBase
                      onClick={() => setViewingPhoto(selected.photo)}
                      sx={(theme) => ({
                        borderRadius: theme.tokens.radii.chip,
                        mt: 0.5,
                      })}
                    >
                      <Box
                        alt={`Foto de ${fullName(selected)}`}
                        component="img"
                        src={selected.photo}
                        sx={(theme) => ({
                          width: 112,
                          height: 112,
                          objectFit: "cover",
                          borderRadius: theme.tokens.radii.chip,
                          border: "1px solid",
                          borderColor: "divider",
                        })}
                      />
                    </ButtonBase>
                  ) : (
                    <MutedCell>Sin foto</MutedCell>
                  ),
                },
              ]
            : []
        }
        onClose={() => {
          setSelected(null);
          setViewingPhoto(null);
        }}
        open={Boolean(selected)}
        title={selected ? fullName(selected) : ""}
      >
        {selected && canSeeAssignments ? (
          <Suspense fallback={null}>
            <TeacherAssignments
              key={selected.public_id}
              teacherId={selected.public_id}
            />
          </Suspense>
        ) : null}
      </DetailWindow>

      {deactivating ? (
        <Suspense fallback={<p role="status">Preparando confirmación…</p>}>
          <TeacherDeactivationDialog
            teacher={deactivating}
            onCancel={() => {
              setSelected(deactivating);
              setDeactivating(null);
            }}
            onCompleted={() => {
              setDeactivating(null);
              setDeactivationNotice(
                "Docente desactivado. El historial se conserva."
              );
              list.refresh();
            }}
          />
        </Suspense>
      ) : null}

      {documentsFor ? (
        <Suspense fallback={<p role="status">Cargando documentos…</p>}>
          <TeacherDocumentsWindow
            key={documentsFor.public_id}
            onClose={() => setDocumentsFor(null)}
            teacher={documentsFor}
            teacherName={fullName(documentsFor)}
          />
        </Suspense>
      ) : null}

      {viewingPhoto ? (
        <Suspense fallback={null}>
          <ImageDialog
            alt={selected ? fullName(selected) : ""}
            downloadName={viewingPhoto.split("/").pop()}
            onClose={() => setViewingPhoto(null)}
            open
            src={viewingPhoto}
          />
        </Suspense>
      ) : null}

      {creating ? (
        <EntityFormWindow
          description="El código de empleado se genera automáticamente. Complete los datos del registro."
          fields={personField ? [personField, ...fields] : fields}
          initialValues={creating}
          onCancel={() => setCreating(null)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear registro"
          title="Nuevo docente o administrativo"
        />
      ) : null}

      {editing ? (
        <EntityFormWindow
          fields={editFields}
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
            specialty: editing.specialty,
            position: editing.position,
            appointment_date: editing.appointment_date ?? "",
            employee_code: editing.employee_code,
            photo: null,
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

const EMPTY_TEACHER = {
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
  specialty: "",
  position: "",
  appointment_date: "",
  employee_code: "",
  photo: null,
};
