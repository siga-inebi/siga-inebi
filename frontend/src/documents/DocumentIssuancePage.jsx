import { useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { documentsService } from "@documents/documentsService.js";
import { downloadBlob } from "@shared/utils/download.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

function ActionCard({ children, description, title }) {
  return (
    <SectionCard title={title} subtitle={description}>
      {children}
    </SectionCard>
  );
}

export function DocumentIssuancePage() {
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [individual, setIndividual] = useState({
    enrolment_id: "",
    document_type: "enrolment_certificate",
  });
  const [batch, setBatch] = useState({
    section_id: "",
    document_type: "Boleta",
  });
  const [receipt, setReceipt] = useState({
    student_id: "",
    guardian_id: "",
    document_type: "",
    folio: "",
    recipient_name: "",
    notes: "",
  });
  const [integrity, setIntegrity] = useState({ public_id: "", file: null });
  const run = async (task, success) => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await task();
      setMessage({
        severity: "success",
        text: typeof success === "function" ? success(result) : success,
      });
      return result;
    } catch (error) {
      setMessage({ severity: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  };
  const issue = async () => {
    const result = await run(
      () =>
        documentsService.issueIndividualDocument(
          individual.enrolment_id,
          individual.document_type
        ),
      "Documento emitido y descargado."
    );
    if (result) downloadBlob(`${individual.document_type}.pdf`, result.blob);
  };
  const historical = async () => {
    const result = await run(
      () => documentsService.historicalCycleReport(individual.enrolment_id),
      "Reporte histórico descargado."
    );
    if (result) downloadBlob("reporte-historico.pdf", result.blob);
  };
  return (
    <>
      <PageHeader
        title="Emisión documental"
        subtitle="Emita, compile, entregue y verifique documentos oficiales desde un solo flujo."
      />
      <Stack gap={2}>
        {message ? (
          <Alert severity={message.severity}>{message.text}</Alert>
        ) : null}
        <Alert severity="info">
          Use los identificadores públicos mostrados en los módulos de
          matrículas, secciones, alumnos y encargados. Cada operación queda
          auditada.
        </Alert>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 6 }}>
            <ActionCard
              title="Emisión individual e histórico"
              description="Constancias, certificados y reporte consolidado por ciclo."
            >
              <Stack gap={2}>
                <FormTextField
                  label="ID de matrícula"
                  value={individual.enrolment_id}
                  onChange={(e) =>
                    setIndividual({
                      ...individual,
                      enrolment_id: e.target.value,
                    })
                  }
                />
                <FormSelect
                  label="Documento"
                  value={individual.document_type}
                  options={[
                    {
                      value: "enrolment_certificate",
                      label: "Constancia de inscripción",
                    },
                    {
                      value: "study_certificate",
                      label: "Certificado de estudios",
                    },
                  ]}
                  onChange={(e) =>
                    setIndividual({
                      ...individual,
                      document_type: e.target.value,
                    })
                  }
                />
                <Stack direction="row" gap={1}>
                  <Button
                    disabled={busy || !individual.enrolment_id}
                    variant="contained"
                    onClick={issue}
                  >
                    Emitir PDF
                  </Button>
                  <Button
                    disabled={busy || !individual.enrolment_id}
                    onClick={historical}
                  >
                    Reporte histórico
                  </Button>
                </Stack>
              </Stack>
            </ActionCard>
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <ActionCard
              title="Compilación por lote"
              description="Prepara documentos de una sección con reintento idempotente."
            >
              <Stack gap={2}>
                <FormTextField
                  label="ID de sección"
                  value={batch.section_id}
                  onChange={(e) =>
                    setBatch({ ...batch, section_id: e.target.value })
                  }
                />
                <FormTextField
                  label="Tipo de documento"
                  value={batch.document_type}
                  onChange={(e) =>
                    setBatch({ ...batch, document_type: e.target.value })
                  }
                />
                <Button
                  disabled={busy || !batch.section_id}
                  variant="contained"
                  onClick={() =>
                    run(
                      () =>
                        documentsService.compileIssuanceBatch({
                          ...batch,
                          client_batch_id: crypto.randomUUID(),
                        }),
                      (result) =>
                        `${result.count} documento(s) compilados${result.replayed ? " (reintento recuperado)" : ""}.`
                    )
                  }
                >
                  Compilar lote
                </Button>
              </Stack>
            </ActionCard>
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <ActionCard
              title="Constancia de entrega"
              description="Registra quién recibió el documento y conserva la evidencia."
            >
              <Stack gap={2}>
                {[
                  "student_id",
                  "guardian_id",
                  "document_type",
                  "folio",
                  "recipient_name",
                  "notes",
                ].map((field) => (
                  <FormTextField
                    key={field}
                    label={
                      {
                        student_id: "ID de alumno",
                        guardian_id: "ID de encargado",
                        document_type: "Tipo de documento",
                        folio: "Folio",
                        recipient_name: "Nombre de quien recibe",
                        notes: "Notas",
                      }[field]
                    }
                    value={receipt[field]}
                    onChange={(e) =>
                      setReceipt({ ...receipt, [field]: e.target.value })
                    }
                  />
                ))}
                <Button
                  disabled={
                    busy ||
                    !receipt.student_id ||
                    !receipt.guardian_id ||
                    !receipt.document_type
                  }
                  variant="contained"
                  onClick={() =>
                    run(
                      () => documentsService.createDeliveryReceipt(receipt),
                      "Entrega registrada."
                    )
                  }
                >
                  Registrar entrega
                </Button>
              </Stack>
            </ActionCard>
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <ActionCard
              title="Integridad del archivo"
              description="Compara un PDF contra el SHA-256 registrado al emitir."
            >
              <Stack gap={2}>
                <FormTextField
                  label="ID de emisión"
                  value={integrity.public_id}
                  onChange={(e) =>
                    setIntegrity({ ...integrity, public_id: e.target.value })
                  }
                />
                <Button component="label" variant="outlined">
                  Seleccionar PDF
                  <input
                    hidden
                    type="file"
                    accept="application/pdf"
                    onChange={(e) =>
                      setIntegrity({ ...integrity, file: e.target.files?.[0] })
                    }
                  />
                </Button>
                {integrity.file ? (
                  <Typography variant="body2">{integrity.file.name}</Typography>
                ) : null}
                <Button
                  disabled={busy || !integrity.public_id || !integrity.file}
                  variant="contained"
                  onClick={() =>
                    run(
                      () =>
                        documentsService.verifyIssuanceFile(
                          integrity.public_id,
                          integrity.file
                        ),
                      (result) =>
                        result.matches
                          ? "El archivo coincide con la emisión."
                          : "El archivo no coincide con la emisión."
                    )
                  }
                >
                  Verificar integridad
                </Button>
              </Stack>
            </ActionCard>
          </Grid>
        </Grid>
      </Stack>
    </>
  );
}
