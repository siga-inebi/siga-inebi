import { useCallback, useEffect, useId, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import {
  documentsService,
  templateKindOptions,
} from "@documents/documentsService.js";
import { RichTemplateEditor } from "@documents/RichTemplateEditor.jsx";
import {
  emptyRichDocument,
  markersInDocument,
  plainToRich,
  suggestTemplateCode,
} from "@documents/templateContent.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";

const SAMPLE = {
  "student.full_name": "Estudiante de ejemplo",
  "student.code": "EST-DEMO-0001",
  "institution.name": "Institución de ejemplo",
  "institution.short_name": "INEBI",
  "academic.cycle_name": "Ciclo 2026",
  "academic.section_name": "A",
  "enrolment.effective_on": "2026-01-15",
  "document.issue_date": "2026-10-20",
};
const defaults = (template, kinds) => ({
  name: template?.name ?? "",
  code: template?.code ?? "",
  kind: template?.kind ?? kinds[0]?.code ?? "",
  issuance_use: template?.issuance_use ?? "none",
  description: template?.description ?? "",
  content_format: template?.content_format ?? "rich",
  content: template?.content ?? emptyRichDocument(),
  page_size: template?.page_size ?? "letter",
  orientation: template?.orientation ?? "portrait",
  margin_top: template?.margin_top ?? 54,
  margin_right: template?.margin_right ?? 54,
  margin_bottom: template?.margin_bottom ?? 54,
  margin_left: template?.margin_left ?? 54,
  footer_text: template?.footer_text ?? "",
  signature_blocks: template?.signature_blocks ?? [],
});

export function TemplateFormWindow({ template, kinds, onCancel, onSubmit }) {
  const [values, setValues] = useState(() => defaults(template, kinds));
  const [uses, setUses] = useState([]);
  const [tags, setTags] = useState([]);
  const [includeSensitive, setIncludeSensitive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [catalogueError, setCatalogueError] = useState("");
  const [previewError, setPreviewError] = useState("");
  const [preview, setPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmedId, setConfirmedId] = useState("");
  const [codeEdited, setCodeEdited] = useState(Boolean(template));
  const insertTag = useRef(null);
  const formId = useId();
  const loadCatalogs = useCallback(async () => {
    setLoading(true);
    setCatalogueError("");
    try {
      const [nextUses, response] = await Promise.all([
        documentsService.listTemplateIssuanceUses(),
        documentsService.listFieldTags({
          page_size: 100,
          include_sensitive: includeSensitive,
        }),
      ]);
      setUses(nextUses);
      setTags(response.results ?? response);
    } catch (requestError) {
      setCatalogueError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [includeSensitive]);
  useEffect(() => {
    loadCatalogs();
  }, [loadCatalogs]);
  useEffect(() => {
    const timer = setTimeout(async () => {
      setPreviewError("");
      try {
        const draft = {
          content_format: values.content_format,
          content: values.content,
          page_size: values.page_size,
          orientation: values.orientation,
          margin_top: values.margin_top,
          margin_right: values.margin_right,
          margin_bottom: values.margin_bottom,
          margin_left: values.margin_left,
          footer_text: values.footer_text,
          signature_blocks: values.signature_blocks,
        };
        const result = template
          ? await documentsService.previewTemplate(
              template.public_id,
              SAMPLE,
              draft
            )
          : await documentsService.previewTemplateDraft(SAMPLE, draft);
        setPreview(result);
      } catch (requestError) {
        setPreview(null);
        setPreviewError(requestError.message);
      }
    }, 450);
    return () => clearTimeout(timer);
  }, [template, values]);
  const occupant =
    template?.is_active === false
      ? null
      : uses.find((item) => item.code === values.issuance_use)?.active_template;
  const replacing =
    occupant && occupant.public_id !== template?.public_id ? occupant : null;
  const setValue = (name, value) =>
    setValues((current) => ({ ...current, [name]: value }));
  const unknown =
    values.content_format === "rich"
      ? markersInDocument(values.content).filter(
          (marker) => !tags.some((tag) => tag.code === marker)
        )
      : [];
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    if (
      !values.name.trim() ||
      !values.kind ||
      (!template && !values.code.trim())
    )
      return setError("Complete nombre, código y tipo de la plantilla.");
    if (unknown.length)
      return setError(`Etiquetas no autorizadas: ${unknown.join(", ")}.`);
    if (replacing && confirmedId !== replacing.public_id)
      return setError("Confirme el reemplazo indicado.");
    setSubmitting(true);
    const { code, ...editable } = values;
    const payload = template ? editable : { ...editable, code };
    if (replacing) payload.replaces_template_id = confirmedId;
    try {
      await onSubmit(payload);
    } catch (requestError) {
      setError(requestError.message);
      await loadCatalogs();
    } finally {
      setSubmitting(false);
    }
  };
  return (
    <FloatingWindow
      open
      onClose={onCancel}
      title={
        template ? `Editar ${template.name}` : "Nueva plantilla documental"
      }
      description={
        template
          ? "Cada guardado genera una version nueva e inmutable. El encabezado institucional se incorpora automáticamente al emitir."
          : "Editor visual con vista previa real. El encabezado institucional se incorpora automáticamente al emitir."
      }
      width="min(96vw, 1480px)"
      busy={submitting}
      footer={
        <>
          <Button onClick={onCancel}>Cancelar</Button>
          <Button
            variant="contained"
            form={formId}
            type="submit"
            disabled={submitting || loading || Boolean(catalogueError)}
          >
            {template ? "Guardar version" : "Crear plantilla"}
          </Button>
        </>
      }
    >
      <Box component="form" id={formId} onSubmit={handleSubmit}>
        <Stack gap={2}>
          {error ? <Alert severity="error">{error}</Alert> : null}
          {catalogueError ? (
            <Alert
              severity="error"
              action={<Button onClick={loadCatalogs}>Reintentar</Button>}
            >
              {catalogueError}
            </Alert>
          ) : null}
          <Alert severity="info">
            El nombre y logotipo institucional provienen de la configuración
            institucional.
          </Alert>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 2.5 }}>
              <Stack gap={1}>
                <Typography variant="h6">Etiquetas</Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={includeSensitive}
                      onChange={(e) => setIncludeSensitive(e.target.checked)}
                    />
                  }
                  label="Datos sensibles"
                />
                {includeSensitive ? (
                  <Alert severity="warning">
                    Úselos solo cuando el documento los requiera.
                  </Alert>
                ) : null}
                {tags.map((tag) => (
                  <Button
                    key={tag.code}
                    variant="outlined"
                    onClick={() => insertTag.current?.(tag.code)}
                    sx={{ justifyContent: "flex-start" }}
                  >{`{{${tag.code}}}`}</Button>
                ))}
              </Stack>
            </Grid>
            <Grid size={{ xs: 12, lg: 5.5 }}>
              <Stack gap={2}>
                <FormTextField
                  label="Nombre"
                  required
                  value={values.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    setValues((current) => ({
                      ...current,
                      name,
                      ...(!codeEdited
                        ? { code: suggestTemplateCode(name) }
                        : {}),
                    }));
                  }}
                />
                {!template ? (
                  <FormTextField
                    label="Codigo"
                    required
                    value={values.code}
                    helperText="Sugerido desde el nombre; puede ajustarlo antes de crear."
                    onChange={(e) => {
                      setCodeEdited(true);
                      setValue("code", e.target.value.toUpperCase());
                    }}
                  />
                ) : null}
                <Grid container spacing={1}>
                  <Grid size={6}>
                    <FormSelect
                      label="Tipo"
                      options={templateKindOptions(kinds)}
                      value={values.kind}
                      onChange={(e) => setValue("kind", e.target.value)}
                    />
                  </Grid>
                  <Grid size={6}>
                    <FormSelect
                      label="Se usa para"
                      options={[
                        { value: "none", label: "Ninguna" },
                        ...uses.map((item) => ({
                          value: item.code,
                          label: item.label,
                        })),
                      ]}
                      value={values.issuance_use}
                      onChange={(e) => {
                        setValue("issuance_use", e.target.value);
                        setConfirmedId("");
                      }}
                    />
                  </Grid>
                </Grid>
                {replacing ? (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={confirmedId === replacing.public_id}
                        onChange={(e) =>
                          setConfirmedId(
                            e.target.checked ? replacing.public_id : ""
                          )
                        }
                      />
                    }
                    label={`Reemplazar “${replacing.name}” conservando su historial`}
                  />
                ) : null}
                <FormTextField
                  label="Descripción"
                  value={values.description}
                  onChange={(e) => setValue("description", e.target.value)}
                />
                {values.content_format === "plain" ? (
                  <>
                    <Alert
                      severity="info"
                      action={
                        <Button
                          onClick={() =>
                            setValues((current) => ({
                              ...current,
                              content_format: "rich",
                              content: plainToRich(current.content),
                            }))
                          }
                        >
                          Convertir
                        </Button>
                      }
                    >
                      Plantilla histórica en texto plano.
                    </Alert>
                    <FormTextField
                      label="Contenido"
                      multiline
                      minRows={8}
                      value={values.content}
                      onChange={(e) => setValue("content", e.target.value)}
                    />
                  </>
                ) : (
                  <RichTemplateEditor
                    value={values.content}
                    onChange={(content) => setValue("content", content)}
                    insertTag={insertTag}
                  />
                )}
                {unknown.length ? (
                  <Alert severity="error">
                    Etiquetas no autorizadas: {unknown.join(", ")}
                  </Alert>
                ) : null}
                <Grid container spacing={1}>
                  <Grid size={6}>
                    <FormSelect
                      label="Papel"
                      value={values.page_size}
                      options={[
                        { value: "letter", label: "Carta" },
                        { value: "a4", label: "A4" },
                      ]}
                      onChange={(e) => setValue("page_size", e.target.value)}
                    />
                  </Grid>
                  <Grid size={6}>
                    <FormSelect
                      label="Orientación"
                      value={values.orientation}
                      options={[
                        { value: "portrait", label: "Vertical" },
                        { value: "landscape", label: "Horizontal" },
                      ]}
                      onChange={(e) => setValue("orientation", e.target.value)}
                    />
                  </Grid>
                </Grid>
                <Grid container spacing={1}>
                  {["top", "right", "bottom", "left"].map((side) => (
                    <Grid size={3} key={side}>
                      <FormTextField
                        label={`Margen ${side}`}
                        type="number"
                        value={values[`margin_${side}`]}
                        onChange={(e) =>
                          setValue(`margin_${side}`, Number(e.target.value))
                        }
                      />
                    </Grid>
                  ))}
                </Grid>
                <FormTextField
                  label="Pie de página"
                  value={values.footer_text}
                  onChange={(e) => setValue("footer_text", e.target.value)}
                />
                <FormSelect
                  label="Firmas"
                  value={String(values.signature_blocks.length)}
                  options={[
                    { value: "0", label: "Sin firmas" },
                    { value: "1", label: "Una firma" },
                    { value: "2", label: "Dos firmas" },
                  ]}
                  onChange={(e) =>
                    setValue(
                      "signature_blocks",
                      Array.from(
                        { length: Number(e.target.value) },
                        (_, i) =>
                          values.signature_blocks[i] ?? { name: "", title: "" }
                      )
                    )
                  }
                />
                {values.signature_blocks.map((signature, index) => (
                  <Grid container spacing={1} key={index}>
                    <Grid size={6}>
                      <FormTextField
                        label={`Nombre firma ${index + 1}`}
                        value={signature.name}
                        onChange={(e) =>
                          setValue(
                            "signature_blocks",
                            values.signature_blocks.map((item, i) =>
                              i === index
                                ? { ...item, name: e.target.value }
                                : item
                            )
                          )
                        }
                      />
                    </Grid>
                    <Grid size={6}>
                      <FormTextField
                        label="Cargo"
                        value={signature.title}
                        onChange={(e) =>
                          setValue(
                            "signature_blocks",
                            values.signature_blocks.map((item, i) =>
                              i === index
                                ? { ...item, title: e.target.value }
                                : item
                            )
                          )
                        }
                      />
                    </Grid>
                  </Grid>
                ))}
              </Stack>
            </Grid>
            <Grid size={{ xs: 12, lg: 4 }}>
              <Typography variant="h6" mb={1}>
                Vista previa
              </Typography>
              {previewError ? (
                <Alert severity="error">{previewError}</Alert>
              ) : null}
              {preview?.pdf_base64 ? (
                <Box
                  component="iframe"
                  title="Vista previa PDF"
                  src={`data:${preview.content_type};base64,${preview.pdf_base64}`}
                  sx={{
                    border: 1,
                    borderColor: "divider",
                    width: "100%",
                    minHeight: 720,
                  }}
                />
              ) : (
                <Alert severity="info">Generando vista previa…</Alert>
              )}
            </Grid>
          </Grid>
        </Stack>
      </Box>
    </FloatingWindow>
  );
}
