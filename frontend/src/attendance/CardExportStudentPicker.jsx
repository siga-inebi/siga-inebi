import { useCallback, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { CARD_EXPORT_LIMIT } from "@attendance/cardExport.js";
import { studentsService } from "@students/studentsService.js";
import { fullName } from "@students/studentPresentation.js";

import { collectAllPages } from "@shared/api/pages.js";
import {
  sectionsForCycle,
  useCycleCatalog,
  useGradeCatalog,
  useSectionCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

const COLUMNS = [
  { key: "nombre", label: "Nombre completo", render: fullName },
  {
    key: "codigo",
    label: "Código",
    render: (student) => student.student_code,
  },
];

const NO_FILTERS = { level: "", grade: "", section: "", search: "" };

const limitMessage = (total) =>
  `No se agregó: serían ${total} estudiantes y el máximo por exportación es ${CARD_EXPORT_LIMIT}.`;

/**
 * Paso 1 de la exportación de carnés: buscar y elegir estudiantes.
 *
 * Nivel → grado → sección se filtran en cascada con los catálogos de siempre;
 * las secciones son las del ciclo activo. El backend filtra por matrícula
 * ACTIVA y dentro del alcance de quien consulta, así que la lista nunca
 * ofrece a alguien que luego no pueda ver.
 *
 * La selección vive en el diálogo y no en la página visible: sobrevive a
 * cambiar de filtro o de página.
 *
 * @param {object}   props
 * @param {string[]} props.selectedIds `public_id` elegidos.
 * @param {Function} props.onSelectionChange Recibe el arreglo nuevo.
 */
export function CardExportStudentPicker({ onSelectionChange, selectedIds }) {
  const cycles = useCycleCatalog();
  const grades = useGradeCatalog();
  const sections = useSectionCatalog();
  const [filters, setFilters] = useState(NO_FILTERS);
  const [notice, setNotice] = useState("");
  const [collecting, setCollecting] = useState(false);

  const activeCycleId = cycles.options.find(
    (cycle) => cycle.status === "active"
  )?.value;

  // Los niveles salen de los grados (ya traen su nivel): sin otra petición.
  const levelOptions = useMemo(() => {
    const seen = new Map();
    for (const grade of grades.options) {
      if (grade.levelId && !seen.has(grade.levelId)) {
        seen.set(grade.levelId, {
          value: grade.levelId,
          label: grade.levelName,
        });
      }
    }
    return [...seen.values()];
  }, [grades.options]);
  const gradeOptions = filters.level
    ? grades.options.filter((grade) => grade.levelId === filters.level)
    : grades.options;
  const gradeIds = new Set(gradeOptions.map((grade) => grade.value));
  const sectionOptions = sectionsForCycle(
    sections.options,
    activeCycleId
  ).filter((section) =>
    filters.grade
      ? section.gradeId === filters.grade
      : !filters.level || gradeIds.has(section.gradeId)
  );

  const query = useMemo(
    () => ({
      level: filters.level,
      grade: filters.grade,
      section: filters.section,
      search: filters.search.trim(),
    }),
    [filters]
  );
  const loader = useCallback(
    (params) => studentsService.listPage({ page: params.page, ...query }),
    [query]
  );
  const list = usePaginatedList(loader, { canIncludeInactive: false });

  // Elegir un nivel limpia grado y sección; elegir un grado limpia la sección.
  const setFilter = (name, value) => {
    setFilters((current) => ({
      ...current,
      [name]: value,
      ...(name === "level" ? { grade: "", section: "" } : {}),
      ...(name === "grade" ? { section: "" } : {}),
    }));
    setNotice("");
    list.goToPage(1);
  };

  const changeSelection = (next) => {
    if (next.length > CARD_EXPORT_LIMIT) {
      setNotice(limitMessage(next.length));
      return;
    }
    setNotice("");
    onSelectionChange(next);
  };

  const selectAllFiltered = async () => {
    setCollecting(true);
    setNotice("");
    try {
      const rows = await collectAllPages((page) =>
        studentsService.listPage({ ...query, ...page })
      );
      const next = [
        ...new Set([...selectedIds, ...rows.map((row) => row.public_id)]),
      ];
      changeSelection(next);
    } catch (requestError) {
      setNotice(requestError.message);
    } finally {
      setCollecting(false);
    }
  };
  const filterTooBig = list.count > CARD_EXPORT_LIMIT;
  const catalogError = cycles.error || grades.error || sections.error;

  return (
    <Stack gap={1.5}>
      <Stack direction={{ xs: "column", sm: "row" }} flexWrap="wrap" gap={1}>
        <FilterSelect
          emptyLabel="Todos los niveles"
          label="Nivel"
          loading={grades.loading}
          onChange={(value) => setFilter("level", value)}
          options={levelOptions}
          value={filters.level}
        />
        <FilterSelect
          emptyLabel="Todos los grados"
          label="Grado"
          loading={grades.loading}
          onChange={(value) => setFilter("grade", value)}
          options={gradeOptions}
          value={filters.grade}
        />
        <FilterSelect
          emptyLabel="Todas las secciones"
          label="Sección"
          loading={sections.loading || cycles.loading}
          onChange={(value) => setFilter("section", value)}
          options={sectionOptions}
          value={filters.section}
        />
        <SearchField
          onChange={(value) => setFilter("search", value)}
          placeholder="Buscar por nombre o código…"
          value={filters.search}
        />
      </Stack>
      {catalogError ? (
        <Alert severity="warning">
          No se pudieron cargar los filtros académicos: {catalogError}
        </Alert>
      ) : null}

      <Stack
        alignItems={{ xs: "stretch", sm: "center" }}
        direction={{ xs: "column", sm: "row" }}
        gap={1}
      >
        <Typography role="status" variant="body2">
          {selectedIds.length} seleccionados (máximo {CARD_EXPORT_LIMIT}).
        </Typography>
        <Stack
          direction="row"
          flexWrap="wrap"
          gap={1}
          sx={{ ml: { sm: "auto" } }}
        >
          <Button
            disabled={collecting || list.loading || !list.count || filterTooBig}
            onClick={selectAllFiltered}
            size="small"
          >
            {collecting
              ? "Seleccionando…"
              : `Seleccionar los ${list.count} del filtro`}
          </Button>
          <Button
            disabled={!selectedIds.length}
            onClick={() => changeSelection([])}
            size="small"
          >
            Quitar selección
          </Button>
        </Stack>
      </Stack>
      {filterTooBig ? (
        <Typography color="text.secondary" variant="caption">
          El filtro tiene {list.count} estudiantes: acótelo a{" "}
          {CARD_EXPORT_LIMIT} o menos para seleccionarlos todos a la vez.
        </Typography>
      ) : null}
      {notice ? (
        <Alert onClose={() => setNotice("")} role="alert" severity="warning">
          {notice}
        </Alert>
      ) : null}

      {list.error ? (
        <Alert role="alert" severity="error">
          {list.error}
          <Button onClick={list.refresh}>Reintentar</Button>
        </Alert>
      ) : (
        <DataTable
          columns={COLUMNS}
          emptyMessage="Ningún estudiante coincide con los filtros."
          getRowId={(student) => student.public_id}
          getRowLabel={(student) => `Seleccionar a ${fullName(student)}`}
          loading={list.loading}
          onSelectionChange={changeSelection}
          pagination={list.pagination}
          rows={list.items}
          selectable
          selectedIds={selectedIds}
        />
      )}
    </Stack>
  );
}
