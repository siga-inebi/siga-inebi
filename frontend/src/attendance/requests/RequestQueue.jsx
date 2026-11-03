import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import AddIcon from "@mui/icons-material/Add";

import { usePermissions } from "@auth/usePermissions.js";
import { REQUEST_STATUS_VARIANT } from "@attendance/attendanceService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { DetailWindow } from "@ui/layout/DetailWindow.jsx";

import { studentLabel } from "../studentSearch.js";

/** Sin filtro de estado: el backend lista todos si no recibe `status`. */
const ALL = "all";

export function StatusCell({ row, labels }) {
  return (
    <StatusChip
      label={row.status_display ?? labels[row.status] ?? row.status}
      variant={REQUEST_STATUS_VARIANT[row.status] ?? "neutral"}
    />
  );
}

/**
 * Aprobar o rechazar (RF-JUS-004/008). El rechazo exige comentario; al
 * aprobar es opcional. Resuelta, la solicitud queda inmutable.
 */
function ResolutionDialog({ approved, noun, onClose, onConfirm, row }) {
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const confirm = async () => {
    if (!approved && !comment.trim()) {
      setError("Escriba el motivo del rechazo: queda registrado.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await onConfirm(comment.trim());
    } catch (requestError) {
      setError(requestError.message);
      setBusy(false);
    }
  };

  return (
    <Dialog fullWidth maxWidth="sm" onClose={busy ? undefined : onClose} open>
      <DialogTitle>
        {approved ? `Aprobar ${noun}` : `Rechazar ${noun}`}
      </DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }} variant="body2">
          {`${studentLabel(row.student)}. Una vez resuelta no se puede cambiar; una corrección requiere una solicitud nueva.`}
        </DialogContentText>
        {error ? (
          <Alert role="alert" severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <FormTextField
          disabled={busy}
          fullWidth
          label={approved ? "Comentario (opcional)" : "Motivo del rechazo"}
          minRows={2}
          multiline
          name="comment"
          onChange={(event) => setComment(event.target.value)}
          required={!approved}
          value={comment}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button disabled={busy} onClick={onClose} variant="text">
          Cancelar
        </Button>
        <Button
          color={approved ? "primary" : "error"}
          disabled={busy}
          onClick={confirm}
          startIcon={busy ? <CircularProgress size={16} /> : undefined}
          variant="contained"
        >
          {approved ? "Aprobar" : "Rechazar"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/**
 * Bandeja de solicitudes de asistencia (AS3, AS4): listado paginado en el
 * servidor con estado, fechas y búsqueda en la URL (pendientes por omisión),
 * detalle, resolución y alta. Justificaciones y permisos comparten la forma;
 * `config` declara lo propio de cada una.
 *
 * @param {object} props
 * @param {object} props.config
 */
export function RequestQueue({ config }) {
  const { can, user } = usePermissions();
  const canResolve = can(config.resolvePermission);
  const canRequest = can(config.requestPermission);
  const [params, setParams] = useSearchParams();
  const detailParam = `${config.prefix}id`;
  const detailId = params.get(detailParam) ?? "";

  const [creating, setCreating] = useState(false);
  const [resolving, setResolving] = useState(null);
  const [notice, setNotice] = useState("");

  const list = useServerList({
    queryKey: queryKeys.attendance(config.kind, "list"),
    fetchPage: ({ status, ...rest }) =>
      config.list(status === ALL ? rest : { ...rest, status }),
    defaultFilters: {
      status: "pending",
      date_from: "",
      date_to: "",
      ...config.extraFilters,
    },
    urlPrefix: config.prefix,
  });

  const detail = useQuery({
    queryKey: queryKeys.attendance(config.kind, "detail", detailId),
    queryFn: () => config.get(detailId),
    enabled: Boolean(detailId),
  });

  const openDetail = (id) =>
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (id) next.set(detailParam, id);
      else next.delete(detailParam);
      return next;
    });

  const resolve = async (comment) => {
    const { row, approved } = resolving;
    await config.resolve(row.public_id, { approved, comment });
    setResolving(null);
    const who = row.student?.full_name ?? "el estudiante";
    setNotice(
      `${approved ? "Se aprobó" : "Se rechazó"} ${config.theNoun} de ${who}.`
    );
  };

  const resolveActions = (row) => [
    {
      key: "approve",
      label: "Aprobar",
      hidden: !canResolve || row.status !== "pending",
      onClick: () => setResolving({ row, approved: true }),
    },
    {
      key: "reject",
      label: "Rechazar",
      danger: true,
      hidden: !canResolve || row.status !== "pending",
      onClick: () => setResolving({ row, approved: false }),
    },
  ];

  const row = detail.data;

  return (
    <>
      {notice ? (
        <Alert onClose={() => setNotice("")} severity="success" sx={{ mb: 2 }}>
          {notice}
        </Alert>
      ) : null}
      <ListSection
        action={
          canRequest ? (
            <Button
              onClick={() => setCreating(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              {config.newLabel}
            </Button>
          ) : null
        }
        columns={config.columns}
        emptyMessage={config.emptyMessage}
        filters={
          <FilterBar>
            <SearchField
              debounceMs={0}
              onChange={list.setSearch}
              placeholder="Buscar por nombre o código"
              value={list.search}
            />
            <FilterSelect
              label="Estado"
              onChange={(value) => list.setFilter("status", value)}
              options={[
                { value: "pending", label: config.statusLabels.pending },
                { value: "approved", label: config.statusLabels.approved },
                { value: "rejected", label: config.statusLabels.rejected },
                { value: ALL, label: "Todos" },
              ]}
              value={list.filters.status}
            />
            {config.renderExtraFilters?.(list)}
            <DateField
              label="Desde"
              onChange={(event) =>
                list.setFilter("date_from", event.target.value)
              }
              value={list.filters.date_from}
            />
            <DateField
              label="Hasta"
              onChange={(event) =>
                list.setFilter("date_to", event.target.value)
              }
              value={list.filters.date_to}
            />
          </FilterBar>
        }
        getRowKey={(item) => item.public_id}
        list={list}
        onRowClick={(item) => openDetail(item.public_id)}
        renderActions={(item) => (
          <RowActionsMenu
            actions={[
              {
                key: "detail",
                label: "Ver detalle",
                onClick: () => openDetail(item.public_id),
              },
              ...resolveActions(item),
            ]}
            label={item.student?.full_name ?? "estudiante"}
          />
        )}
        showInactiveToggle={false}
        subtitle={config.subtitle}
        title={config.title}
      />

      {detailId ? (
        <DetailWindow
          actions={
            <>
              <Button onClick={() => openDetail("")} variant="text">
                Cerrar
              </Button>
              {row && canResolve && row.status === "pending" ? (
                <>
                  <Button
                    color="error"
                    onClick={() => setResolving({ row, approved: false })}
                    variant="outlined"
                  >
                    Rechazar
                  </Button>
                  <Button
                    onClick={() => setResolving({ row, approved: true })}
                    variant="contained"
                  >
                    Aprobar
                  </Button>
                </>
              ) : null}
            </>
          }
          fields={row ? config.detailFields(row) : []}
          onClose={() => openDetail("")}
          open
          title={config.detailTitle}
        >
          {detail.isPending ? (
            <CircularProgress aria-label="Cargando detalle" size={24} />
          ) : null}
          {detail.error ? (
            <Alert severity="error">{detail.error.message}</Alert>
          ) : null}
          {row ? config.renderDetailExtras?.(row, { user, canResolve }) : null}
        </DetailWindow>
      ) : null}

      {resolving ? (
        <ResolutionDialog
          approved={resolving.approved}
          noun={config.noun}
          onClose={() => setResolving(null)}
          onConfirm={resolve}
          row={resolving.row}
        />
      ) : null}

      {creating
        ? config.renderCreate({
            canResolve,
            onCancel: () => setCreating(false),
            onCreated: (created) => {
              setCreating(false);
              setNotice(config.createdNotice);
              config.onCreated?.(created, openDetail);
            },
          })
        : null}
    </>
  );
}
