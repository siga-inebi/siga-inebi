import React from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";

import { SectionCard } from "@ui/layout/SectionCard.jsx";

/**
 * Frontera de error de la aplicacion.
 *
 * Sigue siendo una clase porque React no expone `componentDidCatch` a los
 * hooks; no hay equivalente funcional.
 */
export class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error(error);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <Box role="alert" sx={{ maxWidth: 520, mx: "auto", mt: 6 }}>
        <SectionCard>
          <Stack alignItems="center" gap={1.5} sx={{ px: 3, py: 5 }}>
            <ErrorOutlineIcon sx={{ fontSize: "3rem", color: "error.main" }} />
            <Typography fontWeight={600} variant="h6">
              Error inesperado
            </Typography>
            <Typography
              color="text.secondary"
              sx={{ textAlign: "center" }}
              variant="body2"
            >
              Recarga la pagina o contacta a administracion si el problema
              continua.
            </Typography>
            <Button
              onClick={() => window.location.reload()}
              sx={{ mt: 1 }}
              variant="contained"
            >
              Recargar
            </Button>
          </Stack>
        </SectionCard>
      </Box>
    );
  }
}
