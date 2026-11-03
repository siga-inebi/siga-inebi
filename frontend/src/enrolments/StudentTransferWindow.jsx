import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import {
  enrolmentsService,
  MOVEMENT_TYPE_LABEL,
} from "@enrolments/enrolmentsService.js";
import { collectAllPages } from "@shared/api/pages.js";
import {
  studentOption,
  useCycleCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { useDependentCatalogOptions } from "@shared/catalogs/useCatalogOptions.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { studentsService } from "@students/studentsService.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";

async function loadTransferSections(cycleId) {
  const rows = await collectAllPages((params) =>
    academicsService.listSections({ ...params, academic_cycle_id: cycleId })
  );
  return rows.map((row) => ({
    value: row.public_id,
    gradeId: row.grade?.public_id,
    shiftId: row.shift?.public_id,
    label: [row.grade?.name, row.name, row.shift?.name]
      .filter(Boolean)
      .join(" · "),
  }));
}

/** Independent transfer UI; write authority remains in enrolments services. */
export function StudentTransferWindow({
  direction,
  enrolment,
  studentLabel,
  enrolmentLabel,
  onClose,
  onChanged,
}) {
  const [student, setStudent] = useState(
    enrolment ? { value: enrolment.student_id, label: studentLabel } : null
  );
  const [tab, setTab] = useState("register");
  const [busy, setBusy] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [token, setToken] = useState(0);
  const incoming = direction === "in";
  const refresh = () => {
    setToken((value) => value + 1);
    onChanged?.();
  };
  const submit = async (payload) => {
    if (incoming) await enrolmentsService.transferIn(payload);
    else await enrolmentsService.transferOut(enrolment.public_id, payload);
    setCompleted(true);
    setTab("history");
    refresh();
  };
  return (
    <FloatingWindow
      open
      busy={busy}
      onClose={() => {
        if (!busy) onClose();
      }}
      width={WINDOW_WIDTH.wide}
      title={incoming ? "Traslado de ingreso" : "Traslado de egreso"}
      description={
        incoming
          ? "Busque un estudiante ya registrado y elija su matrícula de destino."
          : "Registre la salida hacia otra institución desde la matrícula seleccionada."
      }
      footer={
        <Button disabled={busy} onClick={onClose}>
          Cerrar
        </Button>
      }
    >
      <Stack gap={2}>
        {student ? (
          <Typography component="div" variant="subtitle2">
            {student.label}
          </Typography>
        ) : null}
        {enrolmentLabel ? (
          <Typography component="div" color="text.secondary">
            {enrolmentLabel}
          </Typography>
        ) : null}
        {completed ? (
          <Alert severity="success">
            Traslado registrado. El historial conserva la evidencia. Cierre esta
            ventana para iniciar otra operación desde la lista actualizada.
          </Alert>
        ) : null}
        <Tabs value={tab} onChange={(_event, next) => setTab(next)}>
          <Tab
            disabled={busy || completed}
            label="Registrar traslado"
            value="register"
          />
          <Tab disabled={busy || !student} label="Historial" value="history" />
        </Tabs>
        {tab === "register" ? (
          <>
            {incoming && !student ? (
              <TransferStudentPicker onSelect={setStudent} />
            ) : student ? (
              <>
                {incoming ? (
                  <Button disabled={busy} onClick={() => setStudent(null)}>
                    Cambiar estudiante
                  </Button>
                ) : null}
                <TransferForm
                  key={student.value}
                  direction={direction}
                  student={student}
                  onSubmit={submit}
                  onBusyChange={setBusy}
                  onFailure={refresh}
                />
              </>
            ) : null}
          </>
        ) : (
          <TransferHistory
            key={`${student.value}:${token}`}
            studentId={student.value}
          />
        )}
      </Stack>
    </FloatingWindow>
  );
}

function TransferStudentPicker({ onSelect }) {
  const [search, setSearch] = useState("");
  const term = search.trim();
  return (
    <Stack gap={1.5}>
      <SearchField
        placeholder="Buscar estudiante por nombre o código"
        value={search}
        onChange={setSearch}
      />
      {term.length >= 2 ? (
        <TransferStudentPage key={term} search={term} onSelect={onSelect} />
      ) : (
        <Typography>
          Escriba al menos dos caracteres para buscar el expediente existente.
        </Typography>
      )}
    </Stack>
  );
}

function TransferStudentPage({ search, onSelect }) {
  const loader = useCallback(
    ({ page }) => studentsService.listPage({ page, search }),
    [search]
  );
  const list = usePaginatedList(loader, { canIncludeInactive: false });
  return (
    <Stack gap={1}>
      {list.error ? (
        <Alert severity="error">
          {list.error}
          <Button onClick={list.refresh}>Reintentar búsqueda</Button>
        </Alert>
      ) : null}
      <DataTable
        rows={list.items}
        loading={list.loading}
        pagination={list.pagination}
        getRowKey={(row) => row.public_id}
        emptyMessage="No hay expedientes que coincidan con la búsqueda."
        columns={[
          {
            key: "student",
            label: "Estudiante",
            render: (row) => studentOption(row).label,
          },
          {
            key: "select",
            label: "Seleccionar",
            render: (row) => (
              <Button onClick={() => onSelect(studentOption(row))}>
                Seleccionar {row.student_code}
              </Button>
            ),
          },
        ]}
      />
    </Stack>
  );
}

function TransferCycleSelect({ value, disabled, onChange }) {
  const cycles = useCycleCatalog();
  return (
    <FormSelect
      label="Ciclo de destino"
      placeholder="Seleccione un ciclo"
      options={cycles.options}
      loading={cycles.loading}
      error={cycles.error}
      disabled={disabled}
      value={value}
      onChange={(event) =>
        onChange(
          event.target.value,
          cycles.options.find((row) => row.value === event.target.value)?.label
        )
      }
    />
  );
}

function TransferForm({
  direction,
  student,
  onSubmit,
  onBusyChange,
  onFailure,
}) {
  const incoming = direction === "in";
  const [cycleId, setCycleId] = useState("");
  const [cycleLabel, setCycleLabel] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [effectiveOn, setEffectiveOn] = useState("");
  const [reason, setReason] = useState("");
  const [review, setReview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sections = useDependentCatalogOptions(
    loadTransferSections,
    incoming ? cycleId : ""
  );
  const invalidate = () => {
    setReview(null);
    setError("");
  };
  const change = (setter) => (event) => {
    setter(event.target.value);
    invalidate();
  };
  const handleReview = (event) => {
    event.preventDefault();
    if (busy) return;
    setError("");
    if (!effectiveOn) {
      setError("Indique la fecha de vigencia.");
      return;
    }
    const section = sections.options.find((row) => row.value === sectionId);
    if (incoming && (!cycleId || !section?.gradeId || !section?.shiftId)) {
      setError("Seleccione ciclo y sección de destino.");
      return;
    }
    const payload = incoming
      ? {
          student_id: student.value,
          academic_cycle_id: cycleId,
          grade_id: section.gradeId,
          shift_id: section.shiftId,
          section_id: sectionId,
          effective_on: effectiveOn,
        }
      : { effective_on: effectiveOn, reason: reason.trim() };
    setReview({
      payload,
      targetLabel: incoming ? `${cycleLabel} · ${section.label}` : null,
    });
  };
  const confirm = async () => {
    if (busy || !review) return;
    setBusy(true);
    onBusyChange(true);
    setError("");
    try {
      await onSubmit(review.payload);
    } catch (requestError) {
      setError(requestError.message);
      setReview(null);
      onFailure();
    } finally {
      setBusy(false);
      onBusyChange(false);
    }
  };
  return (
    <Box component="form" noValidate onSubmit={handleReview}>
      <Stack gap={2}>
        {incoming ? (
          <>
            <TransferCycleSelect
              value={cycleId}
              disabled={busy}
              onChange={(value, label) => {
                setCycleId(value);
                setCycleLabel(label);
                setSectionId("");
                invalidate();
              }}
            />
            <FormSelect
              label="Sección de destino"
              placeholder="Seleccione una sección"
              options={sections.options}
              loading={sections.loading}
              error={sections.error}
              disabled={busy || !cycleId}
              value={sectionId}
              onChange={change(setSectionId)}
              helperText="El grado y la jornada corresponden a la sección seleccionada."
            />
          </>
        ) : (
          <FormTextField
            label="Motivo del egreso (opcional)"
            multiline
            minRows={2}
            disabled={busy}
            value={reason}
            onChange={change(setReason)}
          />
        )}
        <DateField
          label="Vigente desde"
          disabled={busy}
          value={effectiveOn}
          onChange={change(setEffectiveOn)}
        />
        <Alert severity="warning">
          {incoming
            ? "El ingreso activa el expediente y crea la matrícula de destino, sujeto a cupo y permisos."
            : "El egreso cierra la matrícula y revoca la credencial y el acceso del estudiante. El historial se conserva."}{" "}
          Los traslados con fecha futura aún no están habilitados. Estos
          traslados no admiten anulación.
        </Alert>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {review ? (
          <Stack gap={1}>
            <Typography variant="subtitle2">
              Revise antes de confirmar
            </Typography>
            {review.targetLabel ? (
              <Typography>Destino: {review.targetLabel}</Typography>
            ) : null}
            <Typography>
              Vigencia: {formatDate(review.payload.effective_on)}
            </Typography>
            {review.payload.reason ? (
              <Typography sx={{ whiteSpace: "pre-wrap" }}>
                Motivo: {review.payload.reason}
              </Typography>
            ) : null}
            <Stack direction="row" gap={1}>
              <Button disabled={busy} onClick={() => setReview(null)}>
                Volver a editar
              </Button>
              <Button
                disabled={busy}
                variant="contained"
                color={incoming ? "primary" : "error"}
                onClick={confirm}
              >
                {busy
                  ? "Procesando…"
                  : incoming
                    ? "Confirmar ingreso"
                    : "Confirmar egreso"}
              </Button>
            </Stack>
          </Stack>
        ) : (
          <Button disabled={busy} type="submit" variant="contained">
            Revisar traslado
          </Button>
        )}
      </Stack>
    </Box>
  );
}

function TransferHistory({ studentId }) {
  const loader = useCallback(
    (params) =>
      enrolmentsService.listMovements({ ...params, student_id: studentId }),
    [studentId]
  );
  const list = usePaginatedList(loader, { canIncludeInactive: false });
  return (
    <Stack gap={1}>
      {list.error ? <Alert severity="error">{list.error}</Alert> : null}
      <Button onClick={list.refresh}>Actualizar historial</Button>
      <DataTable
        rows={list.items}
        loading={list.loading}
        pagination={list.pagination}
        getRowKey={(row) => row.public_id}
        emptyMessage="No hay movimientos registrados para este estudiante."
        columns={[
          {
            key: "movement_type",
            label: "Movimiento",
            render: (row) =>
              MOVEMENT_TYPE_LABEL[row.movement_type] ?? row.movement_type,
          },
          {
            key: "effective_on",
            label: "Vigente desde",
            render: (row) => formatDate(row.effective_on),
          },
          {
            key: "created_at",
            label: "Registrado el",
            render: (row) => formatDateTime(row.created_at),
          },
          {
            key: "reason",
            label: "Motivo",
            render: (row) => row.reason || "Sin detalle",
          },
          {
            key: "annulment",
            label: "Corrección",
            render: (row) => row.annulment?.reason || "Sin anulación",
          },
        ]}
      />
    </Stack>
  );
}
