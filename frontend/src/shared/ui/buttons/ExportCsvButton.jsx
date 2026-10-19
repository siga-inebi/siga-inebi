import { useRef, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";

import { exportAllToCsv } from "@shared/utils/csvExport.js";

/**
 * Boton "Exportar CSV" con avance y cancelacion (docs/ux-ui.md 1.1).
 *
 * Exporta TODO lo que coincide con los filtros vigentes, no solo la pagina
 * visible: recorre el servidor pagina por pagina y muestra cuantas filas van.
 *
 * @param {object} props
 * @param {Function} props.fetchPage  `listPage` del servicio (acepta parametros).
 * @param {object}  [props.params]    Filtros vigentes.
 * @param {Array}    props.columns    `[{label, value(row)}]`.
 * @param {string}   props.filename
 * @param {string}  [props.label="Exportar CSV"]
 */
export function ExportCsvButton({
  columns,
  disabled = false,
  fetchPage,
  filename,
  label = "Exportar CSV",
  params,
}) {
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState(null);
  const controllerRef = useRef(null);

  const running = progress !== null;

  const start = async () => {
    const controller = new AbortController();
    controllerRef.current = controller;
    setError("");
    setDone(null);
    setProgress({ loaded: 0, total: 0 });
    try {
      const rows = await exportAllToCsv({
        fetchPage,
        params,
        columns,
        filename,
        onProgress: setProgress,
        signal: controller.signal,
      });
      setDone(rows);
    } catch (exportError) {
      if (exportError?.name !== "AbortError") {
        setError(exportError.message);
      }
    } finally {
      setProgress(null);
      controllerRef.current = null;
    }
  };

  const percent =
    progress && progress.total > 0
      ? Math.min(100, Math.round((progress.loaded / progress.total) * 100))
      : 0;

  return (
    <>
      <Button
        disabled={disabled || running}
        onClick={start}
        size="small"
        startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
        variant="outlined"
      >
        {label}
      </Button>
      <Dialog open={running || Boolean(error) || done !== null}>
        <DialogTitle>Exportación CSV</DialogTitle>
        <DialogContent sx={{ minWidth: 320 }}>
          {running ? (
            <>
              <LinearProgress
                aria-label="Avance de la exportación"
                value={percent}
                variant={progress.total > 0 ? "determinate" : "indeterminate"}
              />
              <Typography sx={{ mt: 1.5 }} variant="body2">
                {progress.total > 0
                  ? `${progress.loaded} de ${progress.total} filas`
                  : "Preparando la exportación…"}
              </Typography>
            </>
          ) : null}
          {error ? (
            <Alert role="alert" severity="error">
              {error}
            </Alert>
          ) : null}
          {done !== null ? (
            <Alert severity="success">
              Se exportaron {done} filas, todas las que coinciden con los
              filtros.
            </Alert>
          ) : null}
        </DialogContent>
        <DialogActions>
          {running ? (
            <Button onClick={() => controllerRef.current?.abort()}>
              Cancelar
            </Button>
          ) : (
            <Button
              onClick={() => {
                setError("");
                setDone(null);
              }}
            >
              Cerrar
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </>
  );
}
