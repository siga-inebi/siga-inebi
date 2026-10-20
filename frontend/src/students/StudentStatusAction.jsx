import { useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { formatDateTime } from "@shared/utils/format.js";
import { RecordForm } from "./RecordForm.jsx";
import { studentsService } from "./studentsService.js";
import { STATUS_LABEL } from "./studentPresentation.js";

export function StudentStatusAction({ student, onChanged, onBusy }) {
  const heading = useRef(null);
  const [context, setContext] = useState(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [editing, setEditing] = useState(false);
  const [target, setTarget] = useState(student.status);
  const [confirmation, setConfirmation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  useEffect(() => {
    let active = true;
    studentsService
      .getRecordStatus(student.public_id)
      .then((result) => {
        if (active) {
          setContext(result);
          setError("");
        }
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [student.public_id, student.status, version]);
  useEffect(() => {
    if (editing) heading.current?.focus();
  }, [editing, confirmation]);
  const cancel = () => {
    setEditing(false);
    setConfirmation(null);
    setError("");
  };
  return (
    <Stack gap={2}>
      {success ? <Alert severity="success">{success}</Alert> : null}
      {error ? (
        <Alert severity="error">
          {error}
          <Button onClick={() => setVersion((value) => value + 1)}>
            Reintentar consulta
          </Button>
        </Alert>
      ) : null}
      {context?.last_change ? (
        <Typography color="text.secondary">
          Último cambio manual de estado registrado:{" "}
          {context.last_change.actor_label}
          {" · "}
          {formatDateTime(context.last_change.changed_at)}
          {" · "}
          {STATUS_LABEL[context.last_change.previous_status] ??
            "Sin estado anterior"}
          {" → "}
          {STATUS_LABEL[context.last_change.status] ??
            context.last_change.status}
        </Typography>
      ) : context ? (
        <Typography color="text.secondary">
          Sin cambios manuales de estado registrados.
        </Typography>
      ) : null}
      {!editing &&
        context?.warnings?.map((warning) => (
          <Alert key={warning} severity="warning">
            {warning}
          </Alert>
        ))}
      {!editing && context?.can_change ? (
        <Button
          sx={{ alignSelf: "flex-start" }}
          onClick={() => {
            setEditing(true);
            setTarget(student.status);
            setSuccess("");
          }}
        >
          Cambiar estado
        </Button>
      ) : null}
      {editing && !confirmation ? (
        <Stack gap={2}>
          <Typography component="h2" variant="h6" ref={heading} tabIndex={-1}>
            Cambiar estado del expediente
          </Typography>
          <FormSelect
            label="Nuevo estado"
            value={target}
            disabled={loading}
            options={context.options}
            onChange={(event) => setTarget(event.target.value)}
          />
          <Stack direction="row" gap={1}>
            <Button
              disabled={loading || target === context.status}
              onClick={async () => {
                setLoading(true);
                onBusy?.(true);
                setError("");
                try {
                  const preview = await studentsService.getRecordStatus(
                    student.public_id,
                    { status: target }
                  );
                  setConfirmation({ ...preview, selected: target });
                } catch (err) {
                  setError(err.message);
                } finally {
                  setLoading(false);
                  onBusy?.(false);
                }
              }}
            >
              Revisar cambio
            </Button>
            <Button disabled={loading} onClick={cancel}>
              Cancelar
            </Button>
          </Stack>
        </Stack>
      ) : null}
      {confirmation ? (
        <Stack gap={2}>
          <Typography component="h2" variant="h6" ref={heading} tabIndex={-1}>
            Confirmar cambio de estado
          </Typography>
          <Typography>
            {STATUS_LABEL[confirmation.status]} →{" "}
            {STATUS_LABEL[confirmation.selected]}
          </Typography>
          <Alert severity="info">
            Este cambio afecta el expediente. No crea, retira ni modifica
            matrículas.
          </Alert>
          {confirmation.warnings.map((warning) => (
            <Alert key={warning} severity="warning">
              {warning}
            </Alert>
          ))}
          <RecordForm
            title="Confirmar cambio de estado"
            fields={[]}
            onBusy={onBusy}
            onCancel={cancel}
            submitLabel="Confirmar cambio"
            onSubmit={async () => {
              const result = await studentsService.changeRecordStatus(
                student.public_id,
                {
                  status: confirmation.selected,
                  expected_status: confirmation.status,
                }
              );
              setContext(result);
              setConfirmation(null);
              setEditing(false);
              setSuccess("Estado del expediente actualizado.");
              onChanged(result.status);
            }}
          />
        </Stack>
      ) : null}
    </Stack>
  );
}
