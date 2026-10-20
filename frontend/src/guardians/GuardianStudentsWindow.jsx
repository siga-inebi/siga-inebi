import { useCallback, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import { Link as RouterLink } from "react-router-dom";

import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { RecordCollection } from "@students/RecordCollection.jsx";
import { guardiansService } from "./guardiansService.js";

export function GuardianStudentsWindow({ guardian, onClose }) {
  const queryClient = useQueryClient();
  const [actions, setActions] = useState({});
  const load = useCallback(
    async ({ page }) => {
      const payload = await guardiansService.linkedStudents(guardian.id, {
        page,
      });
      setActions(payload.actions ?? {});
      return payload;
    },
    [guardian.id]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });
  const [linking, setLinking] = useState(false);
  const [student, setStudent] = useState("");
  const [relationship, setRelationship] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const search = useMemo(
    () => ({
      name: `guardian-${guardian.id}-student-candidates`,
      fetchPage: (params) =>
        guardiansService.studentCandidates(guardian.id, params),
      mapResult: (row) => ({
        value: row.public_id,
        label: `${row.full_name} · ${row.student_code}`,
      }),
    }),
    [guardian.id]
  );
  const cancel = () => {
    if (pending.current) return;
    setLinking(false);
    setStudent("");
    setRelationship("");
    setError("");
  };
  const submit = async (event) => {
    event.preventDefault();
    if (pending.current) return;
    if (!student || !relationship.trim()) {
      setError(
        "Seleccione un estudiante y complete el parentesco o responsabilidad."
      );
      return;
    }
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await guardiansService.linkStudent(guardian.id, {
        student_public_id: student,
        relationship_label: relationship.trim(),
      });
    } catch (failure) {
      setError(failure.message);
      pending.current = false;
      setBusy(false);
      return;
    }
    pending.current = false;
    setBusy(false);
    // Each guardian has an isolated picker cache; a saved link changes eligibility.
    void queryClient.invalidateQueries({
      predicate: (query) =>
        query.queryKey[0] === "search" && query.queryKey[1] === search.name,
    });
    cancel();
    setNotice("Estudiante vinculado. El historial se conserva.");
    list.goToPage(1);
    list.refresh();
  };
  return (
    <FloatingWindow
      open
      busy={busy}
      width={WINDOW_WIDTH.medium}
      title={`Estudiantes de ${guardian.person.first_name} ${guardian.person.last_name}`}
      onClose={() => {
        if (!pending.current) onClose();
      }}
      footer={
        <Button disabled={busy} onClick={onClose}>
          Volver al encargado
        </Button>
      }
    >
      <Stack gap={2}>
        <Typography color="text.secondary">
          Relaciones actuales e históricas de estudiantes dentro de su alcance.
          El total corresponde a esas relaciones.
        </Typography>
        {notice ? (
          <Alert role="status" severity="success">
            {notice}
          </Alert>
        ) : null}
        {linking ? (
          <Stack
            component="form"
            onSubmit={submit}
            noValidate
            gap={2}
            aria-label="Vincular estudiante"
          >
            <RemoteSearchSelect
              key={guardian.id}
              label="Estudiante"
              name="student"
              value={student}
              onChange={(event) => setStudent(event.target.value)}
              search={search}
              required
              disabled={busy}
              helperText="Busque por nombre o código. Solo se ofrecen estudiantes que puede consultar y editar."
            />
            <FormTextField
              label="Parentesco o responsabilidad"
              value={relationship}
              onChange={(event) => setRelationship(event.target.value)}
              required
              disabled={busy}
            />
            {error ? <Alert severity="error">{error}</Alert> : null}
            <Stack direction="row" gap={1}>
              <Button disabled={busy} onClick={cancel}>
                Cancelar vínculo
              </Button>
              <Button type="submit" variant="contained" disabled={busy}>
                Vincular estudiante
              </Button>
            </Stack>
          </Stack>
        ) : actions.link_student === true && !list.error && !list.loading ? (
          <Button
            variant="contained"
            onClick={() => {
              setNotice("");
              setLinking(true);
            }}
          >
            Vincular estudiante
          </Button>
        ) : null}
        <RecordCollection
          list={list}
          busy={busy}
          emptyMessage="No hay relaciones con estudiantes dentro de su alcance."
          renderRow={(row) => (
            <Stack gap={0.5}>
              {busy ? (
                <Typography>
                  {row.student.full_name} · {row.student.student_code}
                </Typography>
              ) : (
                <Link
                  component={RouterLink}
                  to={`/app/alumnos/${row.student.public_id}`}
                >
                  {row.student.full_name} · {row.student.student_code}
                </Link>
              )}
              <Typography>
                {row.relationship_label} ·{" "}
                {row.is_primary ? "Principal" : "Secundario"}
              </Typography>
              <Typography color="text.secondary">
                Desde {formatDate(row.starts_at)} ·{" "}
                {row.ends_at
                  ? `Finalizado ${formatDate(row.ends_at)}`
                  : row.is_active
                    ? "Vigente"
                    : "Desactivado"}
              </Typography>
            </Stack>
          )}
        />
      </Stack>
    </FloatingWindow>
  );
}
