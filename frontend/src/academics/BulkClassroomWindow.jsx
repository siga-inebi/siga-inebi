import { useId, useState } from "react";

import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";

import { academicsService } from "@academics/academicsService.js";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

const CAMPUS_SEARCH = {
  name: "campuses",
  fetchPage: (params) => academicsService.listCampuses(params),
  mapResult: (campus) => ({
    value: campus.public_id,
    label: `${campus.name} (${campus.code})`,
  }),
};
const emptyRow = () => ({ name: "", code: "", location: "", capacity: 0 });

/** Alta atómica de varias aulas bajo una única sede. */
export function BulkClassroomWindow({ onCancel, onCreated }) {
  const formId = useId();
  const [campusId, setCampusId] = useState("");
  const [rows, setRows] = useState([emptyRow()]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const updateRow = (index, field, value) =>
    setRows((current) =>
      current.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [field]: value } : row
      )
    );

  const submit = async (event) => {
    event.preventDefault();
    if (!campusId) {
      setError("Seleccione la sede para todas las aulas.");
      return;
    }
    if (rows.some((row) => !row.name.trim() || !row.code.trim())) {
      setError("Cada aula necesita nombre y código.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await academicsService.createClassroomsBatch({
        campus_id: campusId,
        classrooms: rows.map((row) => ({
          ...row,
          capacity: Number(row.capacity || 0),
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
      description="Elija una sede y registre todas sus aulas. Si una fila no es válida, el lote completo no se guarda."
      footer={
        <>
          <Button disabled={busy} onClick={onCancel}>
            Cancelar
          </Button>
          <Button
            disabled={busy}
            form={formId}
            type="submit"
            variant="contained"
          >
            Crear {rows.length === 1 ? "aula" : `${rows.length} aulas`}
          </Button>
        </>
      }
      onClose={busy ? () => {} : onCancel}
      open
      title="Crear aulas por lote"
      width={WINDOW_WIDTH.wide}
    >
      <Box component="form" id={formId} noValidate onSubmit={submit}>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <RemoteSearchSelect
          disabled={busy}
          helperText="Todas las aulas de este lote pertenecen a esta sede."
          label="Sede"
          name="campus_id"
          onChange={(event) => setCampusId(event.target.value)}
          required
          search={CAMPUS_SEARCH}
          value={campusId}
        />
        <Stack gap={2} sx={{ mt: 3 }}>
          {rows.map((row, index) => (
            <Box
              key={index}
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  md: "1fr 1fr 1.5fr 0.7fr auto",
                },
                gap: 1.5,
                alignItems: "start",
              }}
            >
              <TextField
                disabled={busy}
                label="Nombre"
                onChange={(event) =>
                  updateRow(index, "name", event.target.value)
                }
                required
                value={row.name}
              />
              <TextField
                disabled={busy}
                label="Código"
                onChange={(event) =>
                  updateRow(index, "code", event.target.value)
                }
                required
                value={row.code}
              />
              <TextField
                disabled={busy}
                label="Ubicación"
                onChange={(event) =>
                  updateRow(index, "location", event.target.value)
                }
                value={row.location}
              />
              <TextField
                disabled={busy}
                inputProps={{ min: 0 }}
                label="Capacidad"
                onChange={(event) =>
                  updateRow(index, "capacity", event.target.value)
                }
                type="number"
                value={row.capacity}
              />
              <IconButton
                aria-label={`Quitar aula ${index + 1}`}
                disabled={busy || rows.length === 1}
                onClick={() =>
                  setRows((current) =>
                    current.filter((_, rowIndex) => rowIndex !== index)
                  )
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
          Agregar aula
        </Button>
      </Box>
    </FloatingWindow>
  );
}
