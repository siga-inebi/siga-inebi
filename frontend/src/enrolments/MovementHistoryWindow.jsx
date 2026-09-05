import { useCallback } from "react";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  MOVEMENT_TYPE_LABEL,
  MOVEMENT_TYPE_VARIANT,
  enrolmentsService,
} from "@enrolments/enrolmentsService.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { MutedCell } from "@ui/table/cells.jsx";

const COLUMNS = [
  {
    key: "movement_type",
    label: "Movimiento",
    render: (row) => (
      <StatusChip
        label={MOVEMENT_TYPE_LABEL[row.movement_type] ?? row.movement_type}
        variant={MOVEMENT_TYPE_VARIANT[row.movement_type] ?? "neutral"}
      />
    ),
  },
  {
    key: "effective_on",
    label: "Vigente desde",
    render: (row) => formatDate(row.effective_on),
  },
  {
    key: "created_at",
    label: "Registrado el",
    render: (row) => formatDateTime(row.created_at),
  },
  {
    key: "reason",
    label: "Motivo",
    render: (row) => row.reason || <MutedCell>Sin detalle</MutedCell>,
  },
  {
    key: "annulment",
    label: "Estado",
    render: (row) =>
      row.annulment ? (
        <StatusChip label="Anulado" variant="neutral" />
      ) : (
        <StatusChip label="Vigente" variant="success" />
      ),
  },
];

/** Consulta de movimientos inmutables del estudiante (RF-MOV-003). */
export function MovementHistoryWindow({ onClose, studentId }) {
  const loadMovements = useCallback(
    (params) =>
      enrolmentsService.listMovements({ ...params, student_id: studentId }),
    [studentId]
  );
  const list = usePaginatedList(loadMovements, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  return (
    <FloatingWindow
      description="La fecha de vigencia representa desde cuando surtio efecto el movimiento; la fecha de registro conserva cuando fue documentado en el sistema."
      footer={null}
      onClose={onClose}
      open
      title="Historial de movimientos"
      width={WINDOW_WIDTH.large}
    >
      <ListSection
        columns={COLUMNS}
        emptyMessage="Este estudiante no tiene movimientos registrados."
        getRowKey={(movement) => movement.public_id}
        list={list}
        showInactiveToggle={false}
        subtitle="Historial institucional inmutable"
        title="Movimientos del estudiante"
      />
    </FloatingWindow>
  );
}
