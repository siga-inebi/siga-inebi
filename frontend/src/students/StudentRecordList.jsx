import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Pagination from "@mui/material/Pagination";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { MutedCell } from "@ui/table/cells.jsx";

function pageLabel(type, page) {
  if (type === "page") return `Ir a la página ${page}`;
  return type === "next" ? "Página siguiente" : "Página anterior";
}

export function StudentRecordList({ emptyMessage, list, renderItem }) {
  return (
    <Stack aria-busy={list.loading} gap={1}>
      {list.loading ? (
        <Typography role="status" variant="body2">
          Cargando registros…
        </Typography>
      ) : list.error ? (
        <>
          <Alert severity="error">{list.error}</Alert>
          <Button onClick={list.refresh} variant="outlined">
            Reintentar
          </Button>
        </>
      ) : list.items.length ? (
        list.items.map((item) => (
          <Stack key={item.public_id ?? item.id}>{renderItem(item)}</Stack>
        ))
      ) : (
        <MutedCell>{emptyMessage}</MutedCell>
      )}
      {!list.error && list.pageCount > 1 ? (
        <>
          <Typography color="text.secondary" variant="body2">
            Página {list.page} de {list.pageCount} · {list.count} registros
          </Typography>
          <Pagination
            count={list.pageCount}
            disabled={list.loading}
            getItemAriaLabel={pageLabel}
            onChange={(_event, page) => list.goToPage(page)}
            page={list.page}
            size="small"
          />
        </>
      ) : null}
    </Stack>
  );
}
