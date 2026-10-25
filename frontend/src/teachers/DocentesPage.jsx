import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import Avatar from "@mui/material/Avatar";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import AddIcon from "@mui/icons-material/Add";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { teachersService } from "@teachers/teachersService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { useServerList } from "@shared/crud/useServerList.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { ExportCsvButton } from "@ui/buttons/ExportCsvButton.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { ViewDetailButton } from "@ui/table/ViewDetailButton.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import {
  EMPTY_TEACHER,
  TEACHER_FIELDS,
  buildTeacherPayload,
  fullName,
} from "./teacherPresentation.js";

/**
 * Listado de docentes y administrativos. El detalle vive en su propia ruta
 * (`/app/docentes/:teacherId`, mismo patron que el expediente del estudiante):
 * aqui solo quedan el alta y la edicion, cada una con un unico modal que ya
 * no se apila sobre otro.
 */
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

  const location = useLocation();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(null);
  // Valores iniciales, no un booleano: ver el comentario homonimo en
  // AlumnosPage. El codigo sugerido se pide al abrir.
  const [creating, setCreating] = useState(null);
  const [personField, setPersonField] = useState(null);

  const handleSelect = (teacher) =>
    navigate(`/app/docentes/${teacher.id}`, {
      state: { teacherListLocation: `/app/docentes${location.search}` },
    });

  const handleCreate = async (values) => {
    await teachersService.create(buildTeacherPayload(values));
    list.refresh();
    setCreating(null);
  };

  const handleUpdate = async (values) => {
    await teachersService.update(editing.id, {
      ...buildTeacherPayload(values),
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
        <Stack direction="row" gap={1} justifyContent="flex-end">
          <ViewDetailButton
            label={`Ver detalle de ${fullName(teacher)}`}
            onClick={() => handleSelect(teacher)}
          />
          <Button
            disabled={!positionsReady}
            onClick={(event) => {
              // La fila tambien escucha el click: sin esto abriria la ficha
              // y el formulario a la vez.
              event.stopPropagation();
              setEditing(teacher);
            }}
            size="small"
            variant="outlined"
          >
            Editar
          </Button>
        </Stack>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Button
            disabled={!positionsReady}
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
              onRowClick={handleSelect}
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
