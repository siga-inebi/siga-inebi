import { lazy, Suspense } from "react";

import { PERMISSION } from "@auth/permissions.js";
import {
  attendanceService,
  PERMIT_STATUS_LABEL,
  PERMIT_TYPE_LABEL,
} from "@attendance/attendanceService.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";

import { StudentCell } from "../StudentCell.jsx";
import { studentLabel } from "../studentSearch.js";
import { RequestQueue, StatusCell } from "./RequestQueue.jsx";

const TYPE_OPTIONS = Object.entries(PERMIT_TYPE_LABEL).map(
  ([value, label]) => ({ value, label })
);

/** "07:30:00" → "07:30". */
const shortTime = (value) => (value ? String(value).slice(0, 5) : "");

const typeLabel = (row) =>
  row.permit_type_display ??
  PERMIT_TYPE_LABEL[row.permit_type] ??
  row.permit_type;

// El formulario (y `EntityFormWindow`) se descarga al abrirlo.
const NewPermitWindow = lazy(() =>
  import("./PermitForm.jsx").then((module) => ({
    default: module.NewPermitWindow,
  }))
);

const PERMIT_QUEUE = {
  kind: "permits",
  prefix: "per_",
  title: "Permisos de salida e ingreso",
  subtitle: "Pendientes primero; los que puede revisar y los que solicitó.",
  noun: "permiso",
  theNoun: "el permiso",
  detailTitle: "Permiso",
  newLabel: "Nuevo permiso",
  createdNotice: "Permiso solicitado; queda pendiente de resolver.",
  emptyMessage: "Sin permisos para los filtros seleccionados.",
  statusLabels: PERMIT_STATUS_LABEL,
  requestPermission: PERMISSION.ATTENDANCE_PERMIT_REQUEST,
  resolvePermission: PERMISSION.ATTENDANCE_PERMIT_RESOLVE,
  extraFilters: { permit_type: "" },
  list: (params) => attendanceService.listPermits(params),
  get: (id) => attendanceService.getPermit(id),
  resolve: (id, payload) => attendanceService.resolvePermit(id, payload),
  renderExtraFilters: (list) => (
    <FilterSelect
      emptyLabel="Todos"
      label="Tipo"
      onChange={(value) => list.setFilter("permit_type", value)}
      options={TYPE_OPTIONS}
      value={list.filters.permit_type}
    />
  ),
  columns: [
    {
      key: "student",
      label: "Estudiante",
      render: (row) => <StudentCell student={row.student} />,
    },
    { key: "permit_type", label: "Tipo", render: typeLabel },
    {
      key: "permit_date",
      label: "Fecha",
      render: (row) => formatDate(row.permit_date),
    },
    {
      key: "scheduled_time",
      label: "Hora",
      render: (row) => shortTime(row.scheduled_time),
    },
    { key: "reason", label: "Motivo", render: (row) => row.reason },
    {
      key: "status",
      label: "Estado",
      render: (row) => <StatusCell labels={PERMIT_STATUS_LABEL} row={row} />,
    },
    {
      key: "submitted_at",
      label: "Solicitado",
      render: (row) => formatDateTime(row.submitted_at),
    },
  ],
  detailFields: (row) => [
    { label: "Estudiante", value: studentLabel(row.student) },
    { label: "Tipo", value: typeLabel(row) },
    { label: "Fecha", value: formatDate(row.permit_date) },
    { label: "Hora prevista", value: shortTime(row.scheduled_time) },
    { label: "Motivo", value: row.reason },
    {
      label: "Estado",
      value: <StatusCell labels={PERMIT_STATUS_LABEL} row={row} />,
    },
    {
      label: "Solicitado por",
      value: [row.submitted_by?.name, formatDateTime(row.submitted_at)]
        .filter(Boolean)
        .join(" · "),
    },
    {
      label: "Resuelto por",
      value: row.resolved_by
        ? `${row.resolved_by.name} · ${formatDateTime(row.resolved_at)}`
        : null,
    },
    { label: "Comentario de la resolución", value: row.resolution_comment },
  ],
  renderCreate: (props) => (
    <Suspense fallback={null}>
      <NewPermitWindow {...props} />
    </Suspense>
  ),
};

/** Bandeja de permisos de salida anticipada o ingreso tardío (AS4). */
export function PermitsQueue() {
  return <RequestQueue config={PERMIT_QUEUE} />;
}
