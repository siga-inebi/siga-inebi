import { lazy, Suspense, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import PhotoCameraOutlinedIcon from "@mui/icons-material/PhotoCameraOutlined";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

import { JornadaParametersSection } from "../JornadaParametersSection.jsx";

const CameraPreviewWindow = lazy(() =>
  import("@ui/display/CameraPreviewWindow.jsx").then((module) => ({
    default: module.CameraPreviewWindow,
  }))
);

/**
 * Configuración (AS6): parámetros de jornada (`attendance.jornada.configure`)
 * y la prueba de la cámara del punto de control (`attendance.scan`).
 */
export function SettingsTab() {
  const { can } = usePermissions();
  const [showCamera, setShowCamera] = useState(false);

  return (
    <Stack gap={2}>
      {can(PERMISSION.ATTENDANCE_JORNADA_CONFIGURE) ? (
        <JornadaParametersSection />
      ) : null}
      {can(PERMISSION.ATTENDANCE_SCAN) ? (
        <SectionCard
          action={
            <Button
              onClick={() => setShowCamera(true)}
              startIcon={<PhotoCameraOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Abrir cámara
            </Button>
          }
          title="Cámara del punto de control"
        >
          <Typography
            color="text.secondary"
            sx={{ px: { xs: 2, md: 3 }, py: 2.5 }}
            variant="body2"
          >
            Compruebe que el navegador puede usar la cámara antes de empezar a
            escanear. La vista previa no registra movimientos ni guarda
            imágenes.
          </Typography>
          <Suspense fallback={null}>
            {showCamera ? (
              <CameraPreviewWindow onClose={() => setShowCamera(false)} />
            ) : null}
          </Suspense>
        </SectionCard>
      ) : null}
    </Stack>
  );
}
