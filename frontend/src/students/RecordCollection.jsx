import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

/** Paginación del expediente: nunca transforma error o carga en una lista vacía. */
export function RecordCollection({
  list,
  renderRow,
  emptyMessage,
  busy = false,
}) {
  return (
    <Stack gap={2}>
      {list.error ? (
        <Alert severity="error">
          {list.error}
          <Button disabled={busy} onClick={list.refresh}>
            Reintentar
          </Button>
        </Alert>
      ) : list.loading ? (
        <Typography role="status">Cargando registros…</Typography>
      ) : list.items.length ? (
        list.items.map((row) => (
          <Stack
            key={row.public_id ?? row.id}
            gap={0.5}
            sx={{
              p: 2,
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 1,
            }}
          >
            {renderRow(row)}
          </Stack>
        ))
      ) : (
        <Typography color="text.secondary">{emptyMessage}</Typography>
      )}
      {!list.error && !list.loading ? (
        <Stack
          direction="row"
          gap={1}
          alignItems="center"
          justifyContent="space-between"
        >
          <Button
            disabled={busy || list.page === 1}
            onClick={() => list.goToPage(list.page - 1)}
          >
            Anterior
          </Button>
          <Typography>
            Página {list.page} de {list.pageCount} · {list.count} registros
          </Typography>
          <Button
            disabled={busy || list.page >= list.pageCount}
            onClick={() => list.goToPage(list.page + 1)}
          >
            Siguiente
          </Button>
        </Stack>
      ) : null}
    </Stack>
  );
}
