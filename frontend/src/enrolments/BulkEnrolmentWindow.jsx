import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import {
  sectionsForCycle,
  useCycleCatalog,
  useSectionCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

const EMPTY_LOADER = () => Promise.resolve({ count: 0, results: [] });
const STATUS = {
  ready: "Lista para matricular",
  created: "Creada",
  existing: "Ya registrada",
  error: "No procesada",
};
const label = (student) => `${student.full_name} · ${student.student_code}`;

/** Una lectura paginada de candidatos y un POST por revisión/confirmación. */
export function BulkEnrolmentWindow({ onClose, onCreated }) {
  const cycles = useCycleCatalog();
  const sections = useSectionCatalog();
  const [cycleId, setCycleId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [effectiveOn, setEffectiveOn] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(new Map());
  const [result, setResult] = useState(null);
  const [resultLabels, setResultLabels] = useState(new Map());
  const [reviewed, setReviewed] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const ready = Boolean(cycleId && sectionId && effectiveOn);
  const searchReady = ready && search.trim().length >= 2;
  const load = useCallback(
    (params) =>
      enrolmentsService.listInitialCandidates({
        page: params.page,
        section_id: sectionId,
        search: search.trim(),
      }),
    [sectionId, search]
  );
  const candidates = usePaginatedList(searchReady ? load : EMPTY_LOADER, {
    canIncludeInactive: false,
    pageSize: 25,
  });
  const invalidateReview = () => {
    setReviewed(null);
    setResult(null);
    setError("");
  };
  const changeSelection = (next) => {
    if (next.size > 100) {
      setError("Puede seleccionar hasta 100 estudiantes por lote.");
      return;
    }
    setSelected(next);
    invalidateReview();
  };
  const toggle = (student) => {
    const next = new Map(selected);
    if (next.has(student.public_id)) next.delete(student.public_id);
    else next.set(student.public_id, label(student));
    changeSelection(next);
  };
  const allVisible =
    candidates.items.length > 0 &&
    candidates.items.every((row) => selected.has(row.public_id));
  const toggleVisible = () => {
    const next = new Map(selected);
    for (const row of candidates.items) {
      if (allVisible) next.delete(row.public_id);
      else next.set(row.public_id, label(row));
    }
    changeSelection(next);
  };
  const process = async (confirm) => {
    const payload = confirm
      ? reviewed
      : {
          section_id: sectionId,
          effective_on: effectiveOn,
          student_ids: [...selected.keys()],
        };
    if (!payload || submitting) return;
    setResultLabels(new Map(selected));
    setSubmitting(true);
    setReviewed(null);
    setError("");
    try {
      const response = await enrolmentsService.bulkMatriculate({
        ...payload,
        preview: !confirm,
      });
      setResult(response);
      if (!confirm) setReviewed(payload);
      if (confirm) {
        const failedIds = new Set(
          response.results
            .filter((row) => row.status === "error")
            .map((row) => row.student_id)
        );
        setSelected(
          (current) => new Map([...current].filter(([id]) => failedIds.has(id)))
        );
        candidates.goToPage(1);
        candidates.refresh();
        if (
          response.results.some(
            (row) => row.status === "created" || row.status === "existing"
          )
        )
          onCreated?.();
      }
    } catch (requestError) {
      setResult(null);
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FloatingWindow
      busy={submitting}
      open
      title="Matriculacion por lotes"
      width={WINDOW_WIDTH.wide}
      description="Busque estudiantes sin matrícula activa, seleccione hasta 100 y revise antes de confirmar. Este flujo no cierra matrículas anteriores; para continuarlas use reinscripción."
      onClose={() => {
        if (!submitting) onClose();
      }}
      footer={
        <>
          <Button disabled={submitting} onClick={onClose}>
            Cerrar
          </Button>
          <Button
            disabled={!ready || !selected.size || submitting}
            onClick={() => process(false)}
            variant="outlined"
          >
            Vista previa
          </Button>
          <Button
            disabled={submitting || !reviewed || !result?.succeeded}
            onClick={() => process(true)}
            variant="contained"
          >
            {submitting ? "Procesando…" : "Confirmar matrículas"}
          </Button>
        </>
      }
    >
      <Stack gap={2.5}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" },
            gap: 2,
          }}
        >
          <FormSelect
            disabled={submitting}
            error={cycles.error}
            label="Ciclo escolar"
            loading={cycles.loading}
            options={cycles.options}
            value={cycleId}
            placeholder="Seleccione un ciclo"
            required
            onChange={(event) => {
              setCycleId(event.target.value);
              setSectionId("");
              setSelected(new Map());
              candidates.goToPage(1);
              invalidateReview();
            }}
          />
          <FormSelect
            disabled={!cycleId || submitting}
            error={sections.error}
            label="Seccion"
            loading={sections.loading}
            options={sectionsForCycle(sections.options, cycleId)}
            value={sectionId}
            placeholder="Seleccione una sección"
            required
            onChange={(event) => {
              setSectionId(event.target.value);
              setSelected(new Map());
              candidates.goToPage(1);
              invalidateReview();
            }}
          />
          <FormTextField
            disabled={submitting}
            label="Vigente desde"
            type="date"
            required
            value={effectiveOn}
            slotProps={{ inputLabel: { shrink: true } }}
            onChange={(event) => {
              setEffectiveOn(event.target.value);
              invalidateReview();
            }}
          />
        </Box>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {result ? (
          <Alert severity={result.failed ? "warning" : "success"}>
            <Stack gap={0.5}>
              <span>
                {result.preview ? "Revisión" : "Resultado"}: {result.succeeded}{" "}
                correctas, {result.failed} no procesadas.
              </span>
              {result.results.map((row) => (
                <span key={row.student_id}>
                  {resultLabels.get(row.student_id) ?? row.student_id}:{" "}
                  {STATUS[row.status]}
                  {row.error ? ` — ${row.error}` : ""}
                </span>
              ))}
            </Stack>
          </Alert>
        ) : null}
        <Alert severity="info">
          La revisión no reserva vacantes. El servidor vuelve a validar al
          confirmar y puede aceptar solo parte del lote.
        </Alert>
        {!ready ? (
          <Typography>
            Elija ciclo, sección y fecha para buscar estudiantes.
          </Typography>
        ) : (
          <Stack gap={1.5}>
            <SearchField
              disabled={submitting}
              value={search}
              placeholder="Buscar por nombre o codigo (mínimo 2 letras)…"
              onChange={(value) => {
                setSearch(value);
                candidates.goToPage(1);
                invalidateReview();
              }}
            />
            <Stack direction="row" alignItems="center" flexWrap="wrap" gap={1}>
              <FormControlLabel
                label={`Seleccionar los ${candidates.items.length} visibles`}
                control={
                  <Checkbox
                    disabled={
                      submitting ||
                      candidates.loading ||
                      !searchReady ||
                      !candidates.items.length
                    }
                    checked={allVisible && searchReady}
                    onChange={toggleVisible}
                  />
                }
              />
              <Typography>{selected.size} seleccionados de 100</Typography>
            </Stack>
            {!searchReady ? (
              <Typography>Escriba al menos 2 letras para buscar.</Typography>
            ) : candidates.error ? (
              <Alert severity="error">
                {candidates.error}
                <Button disabled={submitting} onClick={candidates.refresh}>
                  Reintentar búsqueda
                </Button>
              </Alert>
            ) : candidates.loading ? (
              <Typography role="status">Buscando estudiantes…</Typography>
            ) : (
              <>
                {!candidates.items.length ? (
                  <Typography>
                    Ningún estudiante disponible coincide con la búsqueda.
                  </Typography>
                ) : null}
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                    maxHeight: "22rem",
                    overflowY: "auto",
                  }}
                >
                  {candidates.items.map((student) => (
                    <FormControlLabel
                      key={student.public_id}
                      label={label(student)}
                      control={
                        <Checkbox
                          disabled={submitting}
                          checked={selected.has(student.public_id)}
                          onChange={() => toggle(student)}
                        />
                      }
                    />
                  ))}
                </Box>
                <Stack
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                >
                  <Button
                    disabled={submitting || candidates.page === 1}
                    onClick={() => candidates.goToPage(candidates.page - 1)}
                  >
                    Anterior
                  </Button>
                  <Typography>
                    Página {candidates.page} de {candidates.pageCount} ·{" "}
                    {candidates.count} coincidencias
                  </Typography>
                  <Button
                    disabled={
                      submitting || candidates.page >= candidates.pageCount
                    }
                    onClick={() => candidates.goToPage(candidates.page + 1)}
                  >
                    Siguiente
                  </Button>
                </Stack>
              </>
            )}
          </Stack>
        )}
      </Stack>
    </FloatingWindow>
  );
}
