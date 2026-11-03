import { useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";

import { academicsService } from "@academics/academicsService.js";
import { SUBJECT_SEARCH } from "@academics/searchOptions.js";
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

import { useGradeOptions } from "../structureOptions.js";
import { AddButton, PlanningOnlyNotice } from "./common.jsx";
import { GeneratePlanWindow } from "./GeneratePlanWindow.jsx";

/**
 * Plan de estudios del ciclo (docs/ux-ui.md S2, N2): qué cursos lleva cada
 * grado en este ciclo. Es lo que exige la activación, y no es lo mismo que
 * "Cursos del nivel" (catálogo del nivel con horas semanales), aunque se
 * puede generar desde ahí.
 */
export function CurriculumPlanTab({ canManage, cycle }) {
  const cycleId = cycle.public_id;
  const isDraft = cycle.status === "draft";
  const canWrite = canManage && isDraft;
  const grades = useGradeOptions();
  const [adding, setAdding] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [busy, setBusy] = useState(false);
  const [rowError, setRowError] = useState("");

  const list = useServerList({
    queryKey: queryKeys.academics.list("curriculum-plans", cycleId),
    fetchPage: (params) =>
      academicsService.listCurriculumPlans({
        ...params,
        academic_cycle_id: cycleId,
      }),
    defaultFilters: { grade_id: "" },
    defaultOrdering: "grade",
    canIncludeInactive: true,
    urlPrefix: "plan_",
  });

  const toggleRequired = async (plan) => {
    setRowError("");
    try {
      await academicsService.updateCurriculumPlan(plan.public_id, {
        is_required: !plan.is_required,
      });
      list.refresh();
    } catch (error) {
      setRowError(error.message);
    }
  };

  const columns = [
    { key: "grade", label: "Grado", render: (row) => row.grade?.name ?? "—" },
    {
      key: "subject",
      label: "Curso",
      render: (row) =>
        row.subject?.code
          ? `${row.subject.name} (${row.subject.code})`
          : (row.subject?.name ?? "—"),
    },
    {
      key: "required",
      label: "Tipo",
      render: (row) => (
        <StatusChip
          label={row.is_required ? "Obligatorio" : "Optativo"}
          variant={row.is_required ? "primary" : "neutral"}
        />
      ),
    },
    {
      key: "state",
      label: "Estado",
      render: (row) =>
        row.is_active ? (
          <StatusChip label="Vigente" variant="success" />
        ) : (
          <StatusChip label="Retirado" variant="neutral" />
        ),
    },
  ];

  const hasFilters = Boolean(list.search || list.filters.grade_id);

  return (
    <>
      <Alert severity="info" sx={{ mb: 2 }}>
        El plan de estudios del ciclo indica qué cursos lleva cada grado en este
        ciclo y es lo que exige la activación. «Cursos del nivel» (en Niveles)
        es el catálogo del nivel con sus horas semanales: sirve de base para
        generar este plan.
      </Alert>
      <PlanningOnlyNotice cycle={cycle} what="el plan de estudios" />
      <ListSection
        action={
          canManage ? (
            <Stack direction="row" gap={1}>
              <Button
                disabled={!isDraft}
                onClick={() => setGenerating(true)}
                size="small"
                variant="outlined"
              >
                Generar desde cursos del nivel
              </Button>
              <AddButton
                disabled={!isDraft}
                hint="El plan solo cambia con el ciclo en borrador."
                label="Agregar curso"
                onClick={() => setAdding(true)}
              />
            </Stack>
          ) : null
        }
        actionError={rowError}
        columns={columns}
        emptyMessage={
          hasFilters
            ? "Sin cursos para los filtros seleccionados."
            : "Este ciclo todavía no tiene plan de estudios."
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
              placeholder="Buscar por curso o grado"
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
                      key: "toggle",
                      label: row.is_required
                        ? "Marcar como optativo"
                        : "Marcar como obligatorio",
                      hidden: !row.is_active,
                      onClick: () => toggleRequired(row),
                    },
                    {
                      key: "remove",
                      label: "Quitar del plan",
                      danger: true,
                      hidden: !row.is_active,
                      onClick: () => {
                        setRowError("");
                        setRemoving(row);
                      },
                    },
                  ]}
                  label={`${row.grade?.name ?? ""} ${row.subject?.name ?? ""}`}
                />
              )
            : undefined
        }
        subtitle="Cursos por grado de este ciclo."
        title="Plan de estudios"
      />

      {adding ? (
        <EntityFormWindow
          description="Agrega un curso al plan de un grado en este ciclo."
          fields={[
            {
              name: "grade_id",
              label: "Grado",
              type: "select",
              required: true,
              options: grades.options,
              loading: grades.loading,
            },
            {
              name: "subject_id",
              label: "Curso",
              type: "search-select",
              required: true,
              search: SUBJECT_SEARCH,
            },
            { name: "is_required", label: "Obligatorio", type: "checkbox" },
          ]}
          initialValues={{
            grade_id: list.filters.grade_id,
            subject_id: "",
            is_required: true,
          }}
          onCancel={() => setAdding(false)}
          onSubmit={async (values) => {
            await academicsService.createCurriculumPlan({
              ...values,
              academic_cycle_id: cycleId,
            });
            setAdding(false);
            list.refresh();
          }}
          open
          submitLabel="Agregar al plan"
          title="Agregar curso al plan"
        />
      ) : null}

      {generating ? (
        <GeneratePlanWindow
          cycleId={cycleId}
          grades={grades.options}
          initialGradeId={list.filters.grade_id}
          onClose={() => {
            setGenerating(false);
            list.refresh();
          }}
        />
      ) : null}

      <ConfirmDialog
        busy={busy}
        confirmColor="error"
        confirmText="Quitar del plan"
        errorText={removing ? rowError || undefined : undefined}
        message={
          removing
            ? `${removing.subject?.name} deja de formar parte del plan de ${removing.grade?.name} en este ciclo. No se borra: queda en el historial.`
            : ""
        }
        onClose={() => {
          if (busy) return;
          setRemoving(null);
          setRowError("");
        }}
        onConfirm={async () => {
          setBusy(true);
          setRowError("");
          try {
            await academicsService.deactivateCurriculumPlan(removing.public_id);
            setRemoving(null);
            list.refresh();
          } catch (error) {
            setRowError(error.message);
          } finally {
            setBusy(false);
          }
        }}
        open={Boolean(removing)}
        title="Quitar curso del plan"
      />
    </>
  );
}
