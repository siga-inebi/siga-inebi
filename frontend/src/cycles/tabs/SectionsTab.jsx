import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { academicsService } from "@academics/academicsService.js";
import { classroomSearch } from "@academics/searchOptions.js";
import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import { useGradeOptions, useShiftOptions } from "../structureOptions.js";
import { AddButton, PlanningOnlyNotice } from "./common.jsx";

function capacityText(capacity) {
  return capacity ? String(capacity) : "Sin límite";
}

/** Quita el aula vacía: el backend espera un identificador o nada. */
function sectionPayload(values) {
  const payload = { ...values };
  if (!payload.default_classroom_id) delete payload.default_classroom_id;
  return payload;
}

/**
 * Secciones del ciclo (docs/ux-ui.md S1, S5): alta, edición y baja mientras el
 * ciclo está en borrador; con el ciclo activo, consulta con su ocupación.
 */
export function SectionsTab({ canManage, cycle }) {
  const cycleId = cycle.public_id;
  const isDraft = cycle.status === "draft";
  const isActive = cycle.status === "active";
  const canWrite = canManage && isDraft;
  const grades = useGradeOptions();
  const shifts = useShiftOptions();
  const [editing, setEditing] = useState(null);
  const [removing, setRemoving] = useState(null);
  const [removeError, setRemoveError] = useState("");
  const [removeBusy, setRemoveBusy] = useState(false);

  const list = useServerList({
    queryKey: queryKeys.academics.list("sections", cycleId),
    fetchPage: (params) =>
      academicsService.listSections({ ...params, academic_cycle_id: cycleId }),
    defaultFilters: { grade_id: "" },
    canIncludeInactive: true,
    urlPrefix: "sec_",
  });

  const occupancy = useQuery({
    queryKey: queryKeys.enrolments.occupancy({
      academic_cycle_id: cycleId,
      page_size: 100,
    }),
    queryFn: () =>
      enrolmentsService.listSectionOccupancy({
        academic_cycle_id: cycleId,
        page_size: 100,
      }),
    enabled: isActive,
  });
  const occupancyById = new Map(
    (occupancy.data?.results ?? []).map((row) => [row.public_id, row])
  );

  const columns = [
    { key: "grade", label: "Grado", render: (row) => row.grade?.name ?? "—" },
    { key: "name", label: "Sección", render: (row) => row.name },
    { key: "shift", label: "Jornada", render: (row) => row.shift?.name ?? "—" },
    {
      key: "capacity",
      label: "Cupo",
      align: "right",
      render: (row) => capacityText(row.capacity),
    },
    ...(isActive
      ? [
          {
            key: "occupancy",
            label: "Matriculados",
            align: "right",
            render: (row) => {
              const data = occupancyById.get(row.public_id);
              if (!data) return <MutedCell>—</MutedCell>;
              return data.available_seats == null
                ? String(data.occupied_seats)
                : `${data.occupied_seats} (${data.available_seats} libres)`;
            },
          },
        ]
      : []),
    {
      key: "classroom",
      label: "Aula habitual",
      render: (row) =>
        row.default_classroom?.name ?? <MutedCell>Sin aula</MutedCell>,
    },
    {
      key: "state",
      label: "Estado",
      render: (row) =>
        !row.is_active ? (
          <StatusChip label="Desactivada" variant="neutral" />
        ) : row.capacity_warning ? (
          <StatusChip
            label="Aula con menos cupo"
            title={row.capacity_warning.detail}
            variant="warning"
          />
        ) : (
          <StatusChip label="Activa" variant="success" />
        ),
    },
  ];

  const shiftCampus = (shiftId) =>
    shifts.options.find((shift) => shift.value === shiftId)?.campusId;

  const createFields = (values) => [
    {
      name: "grade_id",
      label: "Grado",
      type: "select",
      required: true,
      options: grades.options,
      loading: grades.loading,
      emptyHint: "Registre grados en Niveles.",
    },
    {
      name: "shift_id",
      label: "Jornada",
      type: "select",
      required: true,
      options: shifts.options,
      loading: shifts.loading,
      emptyHint: "Registre jornadas en Sedes.",
      resets: ["default_classroom_id"],
    },
    { name: "name", label: "Nombre", required: true, placeholder: "A" },
    {
      name: "capacity",
      label: "Cupo",
      type: "number",
      min: 0,
      help: "0 significa sin límite.",
    },
    {
      name: "default_classroom_id",
      label: "Aula habitual (opcional)",
      type: "search-select",
      span: "full",
      search: classroomSearch(shiftCampus(values.shift_id)),
      help: "Debe ser de la misma sede que la jornada.",
    },
  ];

  const editFields = (section) => [
    { name: "name", label: "Nombre", required: true },
    {
      name: "capacity",
      label: "Cupo",
      type: "number",
      min: 0,
      help: "0 significa sin límite.",
    },
    {
      name: "default_classroom_id",
      label: "Aula habitual (opcional)",
      type: "search-select",
      span: "full",
      search: classroomSearch(),
      initialOption: section.default_classroom
        ? {
            value: section.default_classroom.public_id,
            label: section.default_classroom.name,
          }
        : undefined,
    },
  ];

  const hasFilters = Boolean(list.search || list.filters.grade_id);

  return (
    <>
      <PlanningOnlyNotice cycle={cycle} what="la lista de secciones" />
      <ListSection
        action={
          canManage ? (
            <AddButton
              disabled={!isDraft}
              hint="Las secciones solo se crean con el ciclo en borrador."
              label="Nueva sección"
              onClick={() => setEditing({})}
            />
          ) : null
        }
        actionError={removeError && !removing ? removeError : ""}
        columns={columns}
        emptyMessage={
          hasFilters
            ? "Sin secciones para los filtros seleccionados."
            : "Este ciclo todavía no tiene secciones."
        }
        filters={
          <FilterBar
            onClear={
              hasFilters
                ? () => {
                    list.setSearch("");
                    list.setFilters({ grade_id: "" });
                  }
                : undefined
            }
          >
            <SearchField
              debounceMs={0}
              onChange={list.setSearch}
              placeholder="Buscar por sección o grado"
              value={list.search}
            />
            <FilterSelect
              emptyLabel="Todos los grados"
              label="Grado"
              loading={grades.loading}
              onChange={(value) => list.setFilter("grade_id", value)}
              options={grades.options}
              value={list.filters.grade_id}
            />
          </FilterBar>
        }
        getRowKey={(row) => row.public_id}
        list={list}
        renderActions={
          canWrite
            ? (row) => (
                <RowActionsMenu
                  actions={[
                    {
                      key: "edit",
                      label: "Editar",
                      onClick: () => setEditing(row),
                    },
                    {
                      key: "remove",
                      label: "Desactivar",
                      danger: true,
                      hidden: !row.is_active,
                      onClick: () => {
                        setRemoveError("");
                        setRemoving(row);
                      },
                    },
                  ]}
                  label={`${row.grade?.name ?? ""} ${row.name}`}
                />
              )
            : undefined
        }
        subtitle="Grupos de cada grado y jornada. Sin secciones el ciclo no se puede activar."
        title="Secciones del ciclo"
      />

      {editing ? (
        <EntityFormWindow
          description={
            editing.public_id
              ? "El grado y la jornada no cambian; para eso cree otra sección."
              : "La sección pertenece a un grado y una jornada de este ciclo."
          }
          fields={
            editing.public_id
              ? editFields(editing)
              : (values) => createFields(values)
          }
          initialValues={
            editing.public_id
              ? {
                  name: editing.name,
                  capacity: editing.capacity ?? 0,
                  default_classroom_id: editing.default_classroom_id ?? "",
                }
              : {
                  grade_id: "",
                  shift_id: "",
                  name: "",
                  capacity: 0,
                  default_classroom_id: "",
                }
          }
          onCancel={() => setEditing(null)}
          onSubmit={async (values) => {
            if (editing.public_id) {
              await academicsService.updateSection(
                editing.public_id,
                sectionPayload(values)
              );
            } else {
              await academicsService.createSection({
                ...sectionPayload(values),
                academic_cycle_id: cycleId,
              });
            }
            setEditing(null);
            list.refresh();
          }}
          open
          submitLabel={editing.public_id ? "Guardar cambios" : "Crear sección"}
          title={
            editing.public_id
              ? `Editar sección ${editing.grade?.name ?? ""} ${editing.name}`
              : "Nueva sección"
          }
        />
      ) : null}

      <ConfirmDialog
        busy={removeBusy}
        confirmColor="error"
        confirmText="Desactivar"
        errorText={removeError || undefined}
        message={
          removing
            ? `La sección ${removing.grade?.name ?? ""} ${removing.name} deja de ofrecerse en el ciclo. No se borra: queda en el historial. No procede si tiene matrículas activas.`
            : ""
        }
        onClose={() => {
          if (removeBusy) return;
          setRemoving(null);
          setRemoveError("");
        }}
        onConfirm={async () => {
          setRemoveBusy(true);
          setRemoveError("");
          try {
            await academicsService.deactivateSection(removing.public_id);
            setRemoving(null);
            list.refresh();
          } catch (error) {
            setRemoveError(error.message);
          } finally {
            setRemoveBusy(false);
          }
        }}
        open={Boolean(removing)}
        title="Desactivar sección"
      />
    </>
  );
}
