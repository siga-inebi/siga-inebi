import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import { collectAllPages } from "@shared/api/pages.js";
import { useCycleCatalog } from "@shared/catalogs/academicCatalogs.js";
import { useDependentCatalogOptions } from "@shared/catalogs/useCatalogOptions.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";

async function loadCycleSections(cycleId) {
  const rows = await collectAllPages((params) =>
    academicsService.listSections({ ...params, academic_cycle_id: cycleId })
  );
  return rows.map((row) => ({
    value: row.public_id,
    label: [row.grade?.name, row.name, row.shift?.name]
      .filter(Boolean)
      .join(" · "),
  }));
}

const candidateLabel = (row) =>
  `${row.first_name} ${row.last_name} · ${row.student_code}`;
const RESULT_LABEL = {
  ready: "Lista para reinscribir",
  created: "Reinscrita",
  existing: "Ya registrada en destino",
  error: "No procesada",
};

/** Source enrolments are paged remotely; the server owns all eligibility rules. */
export function BulkReenrolmentWindow({ onClose, onCreated }) {
  const cycles = useCycleCatalog();
  const [sourceCycle, setSourceCycle] = useState("");
  const [targetCycle, setTargetCycle] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [effectiveOn, setEffectiveOn] = useState("");
  const [selected, setSelected] = useState(new Map());
  const [result, setResult] = useState(null);
  const [reviewedPayload, setReviewedPayload] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sections = useDependentCatalogOptions(loadCycleSections, targetCycle);

  const invalidateReview = () => {
    setResult(null);
    setReviewedPayload(null);
    setError("");
  };
  const changeSelection = (next) => {
    setSelected(next);
    invalidateReview();
  };
  const process = async (confirm) => {
    const payload = confirm
      ? reviewedPayload
      : {
          effective_on: effectiveOn,
          items: [...selected.keys()].map((id) => ({
            source_enrolment_id: id,
            target_section_id: sectionId,
          })),
        };
    setBusy(true);
    setError("");
    setReviewedPayload(null);
    try {
      const response = await enrolmentsService.bulkReenrol({
        ...payload,
        preview: !confirm,
      });
      setResult(response);
      if (!confirm) setReviewedPayload(payload);
      if (confirm && response.results.some((row) => row.status === "created"))
        onCreated?.();
    } catch (requestError) {
      setResult(null);
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <FloatingWindow
      open
      busy={busy}
      onClose={() => {
        if (!busy) onClose();
      }}
      width={WINDOW_WIDTH.wide}
      title="Reinscripción por lotes"
      description="Seleccione matrículas de origen y una sección del ciclo siguiente. Revise el lote antes de confirmar."
      footer={
        <>
          <Button disabled={busy} onClick={onClose}>
            Cerrar
          </Button>
          <Button
            disabled={busy || !selected.size || !sectionId || !effectiveOn}
            onClick={() => process(false)}
            variant="outlined"
          >
            Vista previa
          </Button>
          <Button
            disabled={busy || !reviewedPayload || !result?.succeeded}
            onClick={() => process(true)}
            variant="contained"
          >
            Confirmar reinscripción
          </Button>
        </>
      }
    >
      <Stack gap={2}>
        <Stack direction={{ xs: "column", md: "row" }} gap={2}>
          <FormSelect
            fullWidth
            disabled={busy}
            label="Ciclo de origen"
            options={cycles.options}
            loading={cycles.loading}
            error={cycles.error}
            value={sourceCycle}
            placeholder="Seleccione un ciclo"
            onChange={(event) => {
              setSourceCycle(event.target.value);
              changeSelection(new Map());
            }}
          />
          <FormSelect
            fullWidth
            disabled={busy}
            label="Ciclo de destino"
            options={cycles.options}
            loading={cycles.loading}
            error={cycles.error}
            value={targetCycle}
            placeholder="Seleccione un ciclo"
            onChange={(event) => {
              setTargetCycle(event.target.value);
              setSectionId("");
              invalidateReview();
            }}
          />
        </Stack>
        <Stack direction={{ xs: "column", md: "row" }} gap={2}>
          <FormSelect
            fullWidth
            disabled={busy || !targetCycle}
            label="Sección de destino"
            options={sections.options}
            loading={sections.loading}
            error={sections.error}
            value={sectionId}
            placeholder="Seleccione una sección"
            onChange={(event) => {
              setSectionId(event.target.value);
              invalidateReview();
            }}
          />
          <FormTextField
            fullWidth
            disabled={busy}
            label="Vigente desde"
            type="date"
            slotProps={{ inputLabel: { shrink: true } }}
            value={effectiveOn}
            onChange={(event) => {
              setEffectiveOn(event.target.value);
              invalidateReview();
            }}
          />
        </Stack>
        <Alert severity="info">
          El servidor valida alcance, ciclo, vigencia y cupo. La vista previa no
          reserva plazas. El resultado puede ser parcial; no decide promoción ni
          repitencia.
        </Alert>
        {sourceCycle ? (
          <CandidatePicker
            key={sourceCycle}
            sourceCycle={sourceCycle}
            selected={selected}
            onSelection={changeSelection}
            busy={busy}
          />
        ) : (
          <Typography>
            Elija el ciclo de origen para consultar candidatos.
          </Typography>
        )}
        <Typography>
          {selected.size} matrículas seleccionadas entre todas las páginas.
        </Typography>
        <Button
          disabled={busy || !selected.size}
          onClick={() => changeSelection(new Map())}
        >
          Limpiar selección
        </Button>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {result ? (
          <Stack gap={1}>
            <Alert severity={result.failed ? "warning" : "success"}>
              {result.preview ? "Vista previa" : "Resultado"}:{" "}
              {result.succeeded} sin errores, {result.failed} con errores de{" "}
              {result.total}.{" "}
              {result.preview
                ? "Confirme para procesar las matrículas seleccionadas."
                : "Puede revisar otra vez y reintentar; las matrículas ya registradas no se duplican."}
            </Alert>
            <DataTable
              rows={result.results}
              getRowKey={(row) => row.source_enrolment_id}
              columns={[
                {
                  key: "student",
                  label: "Estudiante",
                  render: (row) =>
                    selected.get(row.source_enrolment_id) ??
                    "Matrícula seleccionada",
                },
                {
                  key: "status",
                  label: "Estado",
                  render: (row) => RESULT_LABEL[row.status] ?? row.status,
                },
                {
                  key: "error",
                  label: "Detalle",
                  render: (row) => row.error || "Sin errores",
                },
              ]}
            />
          </Stack>
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}

function CandidatePicker({ sourceCycle, selected, onSelection, busy }) {
  const [search, setSearch] = useState("");
  return (
    <Stack gap={1.5}>
      <SearchField
        disabled={busy}
        placeholder="Buscar estudiante por nombre o código"
        value={search}
        onChange={setSearch}
      />
      <CandidatePage
        key={search}
        sourceCycle={sourceCycle}
        search={search}
        selected={selected}
        onSelection={onSelection}
        busy={busy}
      />
    </Stack>
  );
}

function CandidatePage({ sourceCycle, search, selected, onSelection, busy }) {
  const loader = useCallback(
    (params) =>
      enrolmentsService.listReenrolmentCandidates({
        page: params.page,
        academic_cycle_id: sourceCycle,
        search,
      }),
    [sourceCycle, search]
  );
  const list = usePaginatedList(loader, { canIncludeInactive: false });
  const allSelected =
    list.items.length > 0 &&
    list.items.every((row) => selected.has(row.public_id));
  const toggleVisible = () => {
    const next = new Map(selected);
    for (const row of list.items) {
      if (allSelected) next.delete(row.public_id);
      else next.set(row.public_id, candidateLabel(row));
    }
    onSelection(next);
  };
  return (
    <Stack gap={1}>
      {list.error ? (
        <Alert severity="error">
          {list.error}
          <Button onClick={list.refresh}>Reintentar consulta</Button>
        </Alert>
      ) : null}
      <FormControlLabel
        label="Seleccionar página visible"
        control={
          <Checkbox
            disabled={busy || list.loading || !list.items.length}
            checked={allSelected}
            onChange={toggleVisible}
          />
        }
      />
      <DataTable
        rows={list.loading ? [] : list.items}
        loading={list.loading}
        pagination={list.pagination}
        getRowKey={(row) => row.public_id}
        emptyMessage="No hay candidatos para esta consulta."
        columns={[
          {
            key: "selected",
            label: "Selección",
            render: (row) => (
              <Checkbox
                disabled={busy}
                checked={selected.has(row.public_id)}
                inputProps={{ "aria-label": candidateLabel(row) }}
                onChange={() => {
                  const next = new Map(selected);
                  if (next.has(row.public_id)) next.delete(row.public_id);
                  else next.set(row.public_id, candidateLabel(row));
                  onSelection(next);
                }}
              />
            ),
          },
          { key: "student", label: "Estudiante", render: candidateLabel },
          {
            key: "section",
            label: "Origen",
            render: (row) => `${row.grade_name} · ${row.section_name}`,
          },
        ]}
      />
    </Stack>
  );
}
