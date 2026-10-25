import { useState } from "react";

import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";

import { academicsService } from "@academics/academicsService.js";
import { SUBJECT_SEARCH } from "@academics/searchOptions.js";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

const emptyRow = () => ({ subject: null, is_required: true, weekly_hours: 0 });

export function BulkLevelSubjectsWindow({ level, onCancel, onCreated }) {
  const [rows, setRows] = useState([emptyRow()]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const update = (index, values) =>
    setRows((current) =>
      current.map((row, i) => (i === index ? { ...row, ...values } : row))
    );
  const submit = async () => {
    if (rows.some((row) => !row.subject)) {
      setError("Seleccione un curso en cada fila.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await academicsService.linkSubjectsToLevelBatch(level.public_id, {
        subjects: rows.map((row) => ({
          subject_id: row.subject.value,
          is_required: row.is_required,
          weekly_hours: Number(row.weekly_hours || 0),
        })),
      });
      onCreated();
    } catch (requestError) {
      setError(requestError.message);
      setBusy(false);
    }
  };
  return (
    <FloatingWindow
      busy={busy}
      description={`Vincule varios cursos a ${level.name}. Si uno falla, ninguno se guarda.`}
      footer={
        <>
          <Button disabled={busy} onClick={onCancel}>
            Cancelar
          </Button>
          <Button disabled={busy} onClick={submit} variant="contained">
            Vincular {rows.length} cursos
          </Button>
        </>
      }
      onClose={busy ? () => {} : onCancel}
      open
      title="Vincular cursos por lote"
      width={WINDOW_WIDTH.wide}
    >
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      <Stack gap={2}>
        {rows.map((row, index) => (
          <Box
            key={index}
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "2fr 1fr auto" },
              gap: 1.5,
              alignItems: "start",
            }}
          >
            <RemoteSearchSelect
              disabled={busy}
              label="Curso"
              name={`subject-${index}`}
              onChange={() => {}}
              onOptionChange={(subject) => update(index, { subject })}
              search={SUBJECT_SEARCH}
              value={row.subject?.value ?? ""}
            />
            <TextField
              disabled={busy}
              inputProps={{ min: 0 }}
              label="Horas semanales"
              onChange={(event) =>
                update(index, { weekly_hours: event.target.value })
              }
              type="number"
              value={row.weekly_hours}
            />
            <IconButton
              aria-label={`Quitar curso ${index + 1}`}
              disabled={busy || rows.length === 1}
              onClick={() =>
                setRows((current) => current.filter((_, i) => i !== index))
              }
            >
              <DeleteOutlineIcon />
            </IconButton>
          </Box>
        ))}
      </Stack>
      <Button
        disabled={busy}
        onClick={() => setRows((current) => [...current, emptyRow()])}
        startIcon={<AddIcon />}
        sx={{ mt: 2 }}
      >
        Agregar curso
      </Button>
    </FloatingWindow>
  );
}
