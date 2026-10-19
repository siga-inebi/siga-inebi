import { useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";

import { accountsService } from "@auth/accountsService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { formatDate } from "@shared/utils/format.js";
import { TextLink } from "@ui/display/TextLink.jsx";

const EXPIRING_DAYS = 15;

/** RA5: asignaciones por vencer o vencidas, para que nadie pierda acceso sin aviso. */
export function ExpiringAssignmentsAlert() {
  const [open, setOpen] = useState(false);
  const { data } = useResourceQuery(
    queryKeys.identity.expiring(EXPIRING_DAYS),
    () =>
      accountsService.expiringAssignments({
        days: EXPIRING_DAYS,
        page_size: 100,
      })
  );
  const rows = data?.results ?? [];
  if (rows.length === 0) return null;
  const expired = rows.filter((row) => row.status === "ended").length;
  const upcoming = rows.length - expired;

  return (
    <Alert
      action={
        <Button
          color="inherit"
          onClick={() => setOpen((value) => !value)}
          size="small"
        >
          {open ? "Ocultar" : "Ver detalle"}
        </Button>
      }
      severity="warning"
      variant="outlined"
    >
      {upcoming > 0
        ? `${upcoming} asignación(es) de rol vencen en los próximos ${EXPIRING_DAYS} días. `
        : ""}
      {expired > 0 ? `${expired} venció(eron) en los últimos 30 días.` : ""}
      {open ? (
        <List dense>
          {rows.map((row) => (
            <ListItem disableGutters key={row.assignment}>
              <ListItemText
                primary={
                  <TextLink to={`/app/cuentas/${row.account}`}>
                    {row.person_name || row.username}
                  </TextLink>
                }
                secondary={`${row.role_name} · ${row.status === "ended" ? "venció" : "vence"} el ${formatDate(row.ends_at)}`}
              />
            </ListItem>
          ))}
        </List>
      ) : null}
    </Alert>
  );
}
