import { useCallback } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import {
  useCycleCatalog,
  useGradeCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { EMPTY_ACADEMIC_FILTERS } from "./academicFilters.js";

/** Catálogos pequeños para ciclo/grado; las secciones se consultan por página. */
export function EnrolmentAcademicFilters({ value, onChange }) {
  const cycles = useCycleCatalog();
  const grades = useGradeCatalog();
  return (
    <Stack
      aria-label="Filtros académicos de matrícula"
      direction={{ xs: "column", sm: "row" }}
      flexWrap="wrap"
      gap={1.5}
      role="group"
      sx={{ minWidth: 0 }}
    >
      <FormSelect
        label="Ciclo escolar"
        loading={cycles.loading}
        error={cycles.error}
        options={cycles.options}
        placeholder="Todos los ciclos"
        value={value.academic_cycle_id}
        onChange={(event) =>
          onChange({
            ...EMPTY_ACADEMIC_FILTERS,
            academic_cycle_id: event.target.value,
          })
        }
        sx={{ minWidth: 180 }}
      />
      <FormSelect
        label="Grado"
        loading={grades.loading}
        error={grades.error}
        options={grades.options}
        placeholder="Todos los grados"
        value={value.grade_id}
        onChange={(event) =>
          onChange({ ...value, grade_id: event.target.value, section: null })
        }
        sx={{ minWidth: 180 }}
      />
      <SectionFilter
        key={`${value.academic_cycle_id}:${value.grade_id}`}
        cycleId={value.academic_cycle_id}
        gradeId={value.grade_id}
        selected={value.section}
        onChange={(section) => onChange({ ...value, section })}
      />
    </Stack>
  );
}

const EMPTY_PAGE = () => Promise.resolve({ count: 0, results: [] });

function SectionFilter({ cycleId, gradeId, selected, onChange }) {
  const load = useCallback(
    (params) =>
      academicsService.listSections({
        ...params,
        academic_cycle_id: cycleId,
        grade_id: gradeId || undefined,
      }),
    [cycleId, gradeId]
  );
  const list = usePaginatedList(cycleId ? load : EMPTY_PAGE, {
    canIncludeInactive: false,
  });
  const options = list.items.map((row) => ({
    value: row.public_id,
    label: [row.grade?.name, row.name, row.shift?.name]
      .filter(Boolean)
      .join(" · "),
  }));
  // La selección sigue visible aunque se explore otra página de opciones.
  if (selected && !options.some((option) => option.value === selected.value))
    options.unshift(selected);

  return (
    <Stack gap={0.5} sx={{ minWidth: 220 }}>
      <FormSelect
        disabled={!cycleId || list.loading}
        label="Sección"
        loading={Boolean(cycleId) && list.loading && options.length === 0}
        error={list.error}
        helperText={
          !cycleId
            ? "Elija un ciclo para consultar sus secciones."
            : !list.loading && !list.error && list.count === 0
              ? "No hay secciones activas para estos filtros."
              : list.pageCount > 1
                ? "Si no encuentra la sección, revise las demás páginas."
                : undefined
        }
        options={options}
        placeholder="Todas las secciones"
        value={selected?.value ?? ""}
        onChange={(event) =>
          onChange(
            options.find((option) => option.value === event.target.value) ??
              null
          )
        }
      />
      {cycleId ? (
        <Stack direction="row" alignItems="center" gap={0.5}>
          <Button
            aria-label="Página anterior de secciones"
            disabled={list.loading || list.page <= 1}
            onClick={() => list.goToPage(list.page - 1)}
            size="small"
          >
            Anterior
          </Button>
          <Typography color="text.secondary" variant="caption" role="status">
            {list.loading
              ? "Cargando secciones…"
              : `Página ${list.page} de ${list.pageCount} · ${list.count} ${list.count === 1 ? "sección" : "secciones"}`}
          </Typography>
          <Button
            aria-label="Página siguiente de secciones"
            disabled={list.loading || list.page >= list.pageCount}
            onClick={() => list.goToPage(list.page + 1)}
            size="small"
          >
            Siguiente
          </Button>
          {list.error ? (
            <Button onClick={list.refresh} size="small">
              Reintentar secciones
            </Button>
          ) : null}
        </Stack>
      ) : null}
    </Stack>
  );
}
