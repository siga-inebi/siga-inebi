import { useCallback, useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";

import { documentsService } from "@documents/documentsService.js";
import {
  DOCUMENT_STATUS_LABEL,
  DOCUMENT_STATUS_VARIANT,
  enrolmentsService,
} from "@enrolments/enrolmentsService.js";
import { PAGE_SIZE } from "@academics/academicsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { BooleanCell, CodeCell } from "@ui/table/cells.jsx";

const DOCUMENT_FIELDS = [
  { name: "code", label: "Codigo del requisito", required: true, placeholder: "Ejemplo: DPI" },
  { name: "name", label: "Nombre", required: true, placeholder: "Ejemplo: Copia de DPI" },
  { name: "is_required", label: "Es obligatorio", type: "checkbox" },
  {
    name: "status",
    label: "Estado",
    type: "select",
    options: [
      { value: "pending", label: "Pendiente" },
      { value: "delivered", label: "Entregado" },
    ],
    required: true,
  },
];

const COLUMNS = [
  { key: "code", label: "Codigo", render: (row) => <CodeCell value={row.code} /> },
  { key: "name", label: "Requisito", render: (row) => row.name },
  {
    key: "is_required",
    label: "Obligatorio",
    render: (row) => <BooleanCell value={row.is_required} />,
  },
  {
    key: "status",
    label: "Estado",
    render: (row) => (
      <StatusChip
        label={DOCUMENT_STATUS_LABEL[row.status] ?? row.status}
        variant={DOCUMENT_STATUS_VARIANT[row.status] ?? "neutral"}
      />
    ),
  },
];

/**
 * Requisitos documentales de una matricula y su efecto en la emision oficial.
 *
 * Las dos cosas van juntas en la misma ventana porque son la misma pregunta del
 * usuario: "que le falta a este expediente y ya puedo emitirle constancia".
 * Separarlas obligaria a cruzar dos pantallas para responderla.
 */
export function EnrolmentDocumentsWindow({ enrolment, onClose }) {
  const loadDocuments = useCallback(
    (params) => enrolmentsService.listDocuments(enrolment.public_id, params),
    [enrolment.public_id]
  );
  const list = usePaginatedList(loadDocuments, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [eligibility, setEligibility] = useState(null);
  const [eligibilityError, setEligibilityError] = useState("");
  const [adding, setAdding] = useState(false);

  // La elegibilidad se recalcula cada vez que cambia la lista de requisitos:
  // entregar el ultimo documento pendiente es justo lo que desbloquea la emision.
  useEffect(() => {
    let active = true;
    documentsService
      .issuanceEligibility(enrolment.public_id)
      .then((data) => {
        if (active) {
          setEligibility(data);
          setEligibilityError("");
        }
      })
      .catch((requestError) => {
        if (active) setEligibilityError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [enrolment.public_id, list.items]);

  const handleAdd = async (payload) => {
    await enrolmentsService.addDocument(enrolment.public_id, payload);
    setAdding(false);
    list.refresh();
  };

  return (
    <>
      <FloatingWindow
        description="Requisitos documentales de la matricula y su efecto en la emision de documentos oficiales."
        footer={
          <>
            <Button onClick={onClose} variant="text">
              Cerrar
            </Button>
            <Button
              onClick={() => setAdding(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Agregar requisito
            </Button>
          </>
        }
        onClose={onClose}
        open
        title="Expediente documental"
        width={WINDOW_WIDTH.wide}
      >
        <Stack gap={2.5}>
          {eligibilityError ? (
            <Alert severity="error">{eligibilityError}</Alert>
          ) : eligibility ? (
            <Alert severity={eligibility.eligible ? "success" : "warning"}>
              {eligibility.eligible ? (
                "Esta matricula puede emitir documentos oficiales."
              ) : (
                <>
                  Emision oficial bloqueada por requisitos pendientes:{" "}
                  <Typography component="span" sx={{ fontWeight: 700 }}>
                    {eligibility.blocking_document_codes.join(", ") || "sin detalle"}
                  </Typography>
                </>
              )}
            </Alert>
          ) : null}

          {list.error ? <Alert severity="error">{list.error}</Alert> : null}

          <DataTable
            columns={COLUMNS}
            emptyMessage="Esta matricula no tiene requisitos documentales registrados."
            getRowKey={(row) => row.public_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        </Stack>
      </FloatingWindow>

      {adding ? (
        <EntityFormWindow
          description="El codigo identifica el requisito dentro del expediente; el estado determina si bloquea la emision oficial."
          fields={DOCUMENT_FIELDS}
          initialValues={{ code: "", name: "", is_required: true, status: "pending" }}
          key="add-document"
          onCancel={() => setAdding(false)}
          onSubmit={handleAdd}
          open
          submitLabel="Agregar requisito"
          title="Nuevo requisito documental"
        />
      ) : null}
    </>
  );
}
