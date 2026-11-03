import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { documentsService } from "@documents/documentsService.js";

export function DocumentVerificationPage() {
  const { code } = useParams();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    documentsService
      .verifyPublicCode(code)
      .then(setResult)
      .catch((requestError) => setError(requestError.message));
  }, [code]);
  return (
    <Stack gap={2} sx={{ maxWidth: 680, mx: "auto", py: 6 }}>
      <Typography variant="h4">Verificación de documento</Typography>
      {!result && !error ? <CircularProgress /> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}
      {result ? (
        <Alert severity={result.valid ? "success" : "warning"}>
          {result.valid
            ? "Documento oficial válido"
            : "No se pudo validar el documento"}
          {result.folio ? ` · Folio ${result.folio}` : ""}
        </Alert>
      ) : null}
    </Stack>
  );
}
