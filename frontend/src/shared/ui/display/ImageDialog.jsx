import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import CloseIcon from "@mui/icons-material/Close";
import DownloadIcon from "@mui/icons-material/FileDownloadOutlined";

/**
 * Visor de imagen a pantalla grande (fotografia de expediente).
 *
 * @param {object}   props
 * @param {boolean}  props.open
 * @param {string}   props.src
 * @param {string}  [props.alt]
 * @param {string}  [props.downloadName]
 * @param {Function} props.onClose
 */
export function ImageDialog({ alt = "", downloadName, onClose, open, src }) {
  return (
    <Dialog maxWidth="md" onClose={onClose} open={open}>
      <Stack
        direction="row"
        gap={1}
        justifyContent="flex-end"
        sx={{ p: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
      >
        <Button
          component="a"
          download={downloadName || "foto"}
          href={src}
          size="small"
          startIcon={<DownloadIcon fontSize="small" />}
          variant="text"
        >
          Descargar
        </Button>
        <IconButton aria-label="Cerrar imagen" onClick={onClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>
      <Box
        alt={alt}
        component="img"
        src={src}
        sx={{
          display: "block",
          maxWidth: "100%",
          maxHeight: "75dvh",
          objectFit: "contain",
          bgcolor: "background.default",
        }}
      />
    </Dialog>
  );
}
