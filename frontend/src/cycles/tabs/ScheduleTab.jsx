import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";

import { academicsService } from "@academics/academicsService.js";
import { WEEKDAYS, blockLabel, formatTime } from "@academics/schedule.js";
import { classroomSearch, sectionLabel } from "@academics/searchOptions.js";
import { WeeklyScheduleGrid } from "@academics/WeeklyScheduleGrid.jsx";
import { cyclesService } from "@cycles/cyclesService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { formatDateTime } from "@shared/utils/format.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import { useShiftOptions } from "../structureOptions.js";

/** Bloques, secciones de un ciclo y sesiones de una sección caben en una página. */
const MAX = 100;

const dayName = (day) => WEEKDAYS.find(([number]) => number === day)?.[1] ?? "";

/** Estado de publicación del horario del ciclo (RF-HOR-009). */
function PublicationBar({ canWrite, cycleId }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const publication = useQuery({
    queryKey: queryKeys.academics.publication(cycleId),
    queryFn: () => cyclesService.schedulePublication(cycleId),
  });
  const published = Boolean(publication.data?.is_published);

  const toggle = async () => {
    setBusy(true);
    setError("");
    try {
      if (published) await cyclesService.unpublishSchedule(cycleId);
      else await cyclesService.publishSchedule(cycleId);
      await publication.refetch();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack gap={1} sx={{ mb: 2 }}>
      <Stack alignItems="center" direction="row" flexWrap="wrap" gap={1.5}>
        <StatusChip
          label={published ? "Horario publicado" : "Horario sin publicar"}
          variant={published ? "success" : "neutral"}
        />
        <Typography color="text.secondary" variant="body2">
          {published
            ? `Publicado el ${formatDateTime(publication.data.published_at)}. Docentes y encargados lo ven en Mi cuenta.`
            : "Mientras no se publique, docentes y encargados no lo ven en Mi cuenta."}
        </Typography>
        {canWrite && !publication.isPending ? (
          <Button
            disabled={busy}
            onClick={toggle}
            size="small"
            variant={published ? "outlined" : "contained"}
          >
            {published ? "Despublicar" : "Publicar horario"}
          </Button>
        ) : null}
      </Stack>
      {error || publication.error ? (
        <Alert severity="error">{error || publication.error.message}</Alert>
      ) : null}
    </Stack>
  );
}

/** Bloques horarios de la jornada: la rejilla que comparten sus secciones. */
function BlocksCard({ blocks, canManage, loading, shiftId }) {
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const remove = async (block) => {
    setError("");
    try {
      await academicsService.deactivateScheduleBlock(block.public_id);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return (
    <SectionCard
      action={
        canManage ? (
          <Button
            onClick={() => setEditing({})}
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="outlined"
          >
            Nuevo bloque
          </Button>
        ) : null
      }
      subtitle="Períodos de la jornada. Son los mismos para todos los ciclos."
      title="Bloques horarios"
    >
      {error ? (
        <Alert severity="error" sx={{ m: 2 }}>
          {error}
        </Alert>
      ) : null}
      <SectionTableArea>
        <DataTable
          columns={[
            {
              key: "number",
              label: "N.º",
              align: "right",
              render: (b) => b.number,
            },
            { key: "name", label: "Nombre", render: (b) => b.name },
            {
              key: "start",
              label: "Inicio",
              render: (b) => formatTime(b.starts_on),
            },
            { key: "end", label: "Fin", render: (b) => formatTime(b.ends_on) },
            ...(canManage
              ? [
                  {
                    key: "actions",
                    label: "Acciones",
                    align: "right",
                    render: (block) => (
                      <RowActionsMenu
                        actions={[
                          {
                            key: "edit",
                            label: "Editar",
                            onClick: () => setEditing(block),
                          },
                          {
                            key: "remove",
                            label: "Desactivar",
                            danger: true,
                            onClick: () => remove(block),
                          },
                        ]}
                        label={block.name}
                      />
                    ),
                  },
                ]
              : []),
          ]}
          emptyMessage="La jornada todavía no tiene bloques horarios."
          getRowKey={(block) => block.public_id}
          loading={loading}
          rows={blocks}
        />
      </SectionTableArea>
      {editing ? (
        <EntityFormWindow
          fields={[
            ...(editing.public_id
              ? []
              : [
                  {
                    name: "number",
                    label: "Número",
                    type: "number",
                    min: 1,
                    required: true,
                    help: "Orden del bloque en el día; no cambia después.",
                  },
                ]),
            {
              name: "name",
              label: "Nombre",
              required: true,
              placeholder: "Bloque 1",
            },
            {
              name: "starts_on",
              label: "Inicio",
              type: "time",
              required: true,
            },
            { name: "ends_on", label: "Fin", type: "time", required: true },
          ]}
          initialValues={
            editing.public_id
              ? {
                  name: editing.name,
                  starts_on: formatTime(editing.starts_on),
                  ends_on: formatTime(editing.ends_on),
                }
              : {
                  number: blocks.length + 1,
                  name: "",
                  starts_on: "",
                  ends_on: "",
                }
          }
          onCancel={() => setEditing(null)}
          onSubmit={async (values) => {
            if (editing.public_id) {
              await academicsService.updateScheduleBlock(
                editing.public_id,
                values
              );
            } else {
              await academicsService.createScheduleBlock(shiftId, values);
            }
            setEditing(null);
          }}
          open
          submitLabel={editing.public_id ? "Guardar cambios" : "Crear bloque"}
          title={
            editing.public_id
              ? `Editar ${editing.name}`
              : "Nuevo bloque horario"
          }
        />
      ) : null}
    </SectionCard>
  );
}

/**
 * Horarios del ciclo (docs/ux-ui.md S3): bloques por jornada, sesiones por
 * sección en una reja semanal, copia del horario de otra sección, carga
 * semanal declarada contra la agendada y publicación del horario.
 */
export function ScheduleTab({ canManage, cycle }) {
  const cycleId = cycle.public_id;
  const canWrite = canManage && cycle.status !== "closed";
  const shifts = useShiftOptions();
  const [params, setParams] = useSearchParams();
  const shiftId = params.get("hor_shift") || shifts.options[0]?.value || "";
  const sectionId = params.get("hor_section") || "";
  const [adding, setAdding] = useState(null);
  const [cloning, setCloning] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [removeError, setRemoveError] = useState("");

  const setParam = (changes) =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        for (const [key, value] of Object.entries(changes)) {
          if (value) next.set(key, value);
          else next.delete(key);
        }
        return next;
      },
      { replace: true }
    );

  const blocks = useQuery({
    queryKey: queryKeys.academics.scheduleBlocks(shiftId),
    queryFn: () =>
      academicsService.listScheduleBlocks(shiftId, { page_size: MAX }),
    enabled: Boolean(shiftId),
  });
  const sections = useQuery({
    queryKey: queryKeys.academics.list("sections", cycleId, "all"),
    queryFn: () =>
      academicsService.listSections({
        academic_cycle_id: cycleId,
        page_size: MAX,
      }),
  });
  const allSections = sections.data?.results ?? [];
  const shiftSections = allSections.filter(
    (section) => section.shift?.public_id === shiftId
  );
  const section = allSections.find((item) => item.public_id === sectionId);

  const sessions = useQuery({
    queryKey: queryKeys.academics.classSessions(sectionId),
    queryFn: () =>
      academicsService.listClassSessions(sectionId, { page_size: MAX }),
    enabled: Boolean(sectionId),
  });
  const weeklyLoad = useQuery({
    queryKey: queryKeys.academics.weeklyLoad(sectionId),
    queryFn: () => academicsService.sectionWeeklyLoad(sectionId),
    enabled: Boolean(sectionId),
  });
  const planSubjects = useQuery({
    queryKey: queryKeys.academics.list(
      "curriculum-plans",
      cycleId,
      section?.grade?.public_id
    ),
    queryFn: () =>
      academicsService.listCurriculumPlans({
        academic_cycle_id: cycleId,
        grade_id: section.grade.public_id,
        page_size: MAX,
      }),
    enabled: Boolean(section?.grade?.public_id),
  });

  const blockRows = blocks.data?.results ?? [];
  const subjectOptions = (planSubjects.data?.results ?? []).map((plan) => ({
    value: plan.subject.public_id,
    label: plan.subject.name,
  }));

  return (
    <Stack gap={2.5}>
      <PublicationBar canWrite={canWrite} cycleId={cycleId} />

      <FilterBar>
        <FilterSelect
          emptyLabel="Elija una jornada"
          label="Jornada"
          loading={shifts.loading}
          onChange={(value) => setParam({ hor_shift: value, hor_section: "" })}
          options={shifts.options}
          value={shiftId}
        />
        <FilterSelect
          emptyLabel="Elija una sección"
          label="Sección"
          loading={sections.isPending}
          onChange={(value) => setParam({ hor_section: value })}
          options={shiftSections.map((item) => ({
            value: item.public_id,
            label: sectionLabel(item),
          }))}
          value={section ? sectionId : ""}
        />
      </FilterBar>

      {shiftId ? (
        <BlocksCard
          blocks={blockRows}
          canManage={canManage}
          loading={blocks.isPending}
          shiftId={shiftId}
        />
      ) : null}

      {!section ? (
        <Typography color="text.secondary" variant="body2">
          Elija una sección para ver y armar su horario semanal.
        </Typography>
      ) : (
        <SectionCard
          action={
            canWrite ? (
              <Button
                onClick={() => setCloning(true)}
                size="small"
                variant="outlined"
              >
                Copiar horario de otra sección
              </Button>
            ) : null
          }
          subtitle="Cada celda es un día y un bloque. El docente sale de la asignación vigente."
          title={`Horario de ${sectionLabel(section)}`}
        >
          <Box sx={{ p: { xs: 1.5, md: 2 } }}>
            {sessions.error || removeError ? (
              <Alert severity="error" sx={{ mb: 2 }}>
                {removeError || sessions.error.message}
              </Alert>
            ) : null}
            {blockRows.length === 0 ? (
              <Alert severity="info">
                Registre los bloques horarios de la jornada para armar el
                horario.
              </Alert>
            ) : (
              <WeeklyScheduleGrid
                blocks={blockRows}
                caption={`Horario de ${sectionLabel(section)}`}
                renderEmpty={
                  canWrite
                    ? (day, block) => (
                        <Tooltip title="Agregar clase">
                          <IconButton
                            aria-label={`Agregar clase el ${dayName(day)} en ${blockLabel(block)}`}
                            onClick={() => setAdding({ day, block })}
                            size="small"
                          >
                            <AddIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )
                    : undefined
                }
                renderSession={(session) => (
                  <Stack alignItems="flex-start" direction="row" gap={0.5}>
                    <Stack sx={{ flex: 1 }}>
                      <Typography
                        sx={{ fontSize: "0.8125rem", fontWeight: 600 }}
                      >
                        {session.subject?.name}
                      </Typography>
                      <Typography
                        color="text.secondary"
                        sx={{ fontSize: "0.75rem" }}
                      >
                        {session.teacher?.name ?? "Sin docente asignado"}
                      </Typography>
                      {session.classroom?.name ? (
                        <Typography
                          color="text.secondary"
                          sx={{ fontSize: "0.75rem" }}
                        >
                          {session.classroom.name}
                        </Typography>
                      ) : null}
                    </Stack>
                    {canWrite ? (
                      <IconButton
                        aria-label={`Quitar ${session.subject?.name} del ${dayName(session.day_of_week)}`}
                        onClick={() => {
                          setRemoveError("");
                          setRemoving(session);
                        }}
                        size="small"
                      >
                        <CloseIcon fontSize="small" />
                      </IconButton>
                    ) : null}
                  </Stack>
                )}
                sessions={sessions.data?.results ?? []}
              />
            )}
          </Box>
        </SectionCard>
      )}

      {section ? (
        <SectionCard
          subtitle="Horas semanales declaradas en Cursos del nivel contra los períodos agendados."
          title="Carga semanal"
        >
          <SectionTableArea>
            <DataTable
              columns={[
                {
                  key: "subject",
                  label: "Curso",
                  render: (row) => row.subject?.name,
                },
                {
                  key: "declared",
                  label: "Horas declaradas",
                  align: "right",
                  render: (row) =>
                    row.declared_weekly_hours ?? (
                      <MutedCell>Sin declarar</MutedCell>
                    ),
                },
                {
                  key: "scheduled",
                  label: "Períodos agendados",
                  align: "right",
                  render: (row) => row.scheduled_periods,
                },
                {
                  key: "matches",
                  label: "Estado",
                  render: (row) =>
                    row.matches == null ? (
                      <StatusChip label="Sin referencia" variant="neutral" />
                    ) : row.matches ? (
                      <StatusChip label="Coincide" variant="success" />
                    ) : (
                      <StatusChip label="No coincide" variant="warning" />
                    ),
                },
              ]}
              emptyMessage="El grado no tiene cursos en el plan de estudios del ciclo."
              getRowKey={(row) => row.subject?.public_id}
              loading={weeklyLoad.isPending}
              rows={weeklyLoad.data ?? []}
            />
          </SectionTableArea>
        </SectionCard>
      ) : null}

      {adding && section ? (
        <EntityFormWindow
          description={`${sectionLabel(section)} · ${dayName(adding.day)} · ${blockLabel(adding.block)}.`}
          fields={[
            {
              name: "subject_id",
              label: "Curso",
              type: "select",
              required: true,
              options: subjectOptions,
              loading: planSubjects.isPending,
              emptyHint:
                "El grado no tiene cursos en el plan de estudios del ciclo.",
            },
            {
              name: "classroom_id",
              label: "Aula (opcional)",
              type: "search-select",
              search: classroomSearch(),
            },
          ]}
          initialValues={{ subject_id: "", classroom_id: "" }}
          onCancel={() => setAdding(null)}
          onSubmit={async (values) => {
            await academicsService.createClassSession(sectionId, {
              subject_id: values.subject_id,
              schedule_block_id: adding.block.public_id,
              day_of_week: adding.day,
              ...(values.classroom_id
                ? { classroom_id: values.classroom_id }
                : null),
            });
            setAdding(null);
          }}
          open
          submitLabel="Agregar clase"
          title="Agregar clase"
        />
      ) : null}

      {cloning && section ? (
        <EntityFormWindow
          description="Copia las clases activas de otra sección del ciclo, bloque por bloque. No copia aulas ni docentes: el docente sale de la asignación de cada sección."
          fields={[
            {
              name: "source_section_id",
              label: "Sección de origen",
              type: "select",
              required: true,
              options: allSections
                .filter((item) => item.public_id !== sectionId)
                .map((item) => ({
                  value: item.public_id,
                  label: sectionLabel(item),
                })),
            },
          ]}
          initialValues={{ source_section_id: "" }}
          onCancel={() => setCloning(false)}
          onSubmit={async ({ source_section_id }) => {
            await academicsService.cloneClassSessions(
              sectionId,
              source_section_id
            );
            setCloning(false);
          }}
          open
          submitLabel="Copiar horario"
          title={`Copiar horario hacia ${sectionLabel(section)}`}
        />
      ) : null}

      <ConfirmDialog
        confirmColor="error"
        confirmText="Quitar clase"
        message={
          removing
            ? `${removing.subject?.name} deja de darse el ${dayName(removing.day_of_week).toLowerCase()} en ${blockLabel(removing.schedule_block)}.`
            : ""
        }
        onClose={() => setRemoving(null)}
        onConfirm={async () => {
          const session = removing;
          setRemoving(null);
          try {
            await academicsService.deactivateClassSession(session.public_id);
          } catch (requestError) {
            setRemoveError(requestError.message);
          }
        }}
        open={Boolean(removing)}
        title="Quitar clase del horario"
      />
    </Stack>
  );
}
