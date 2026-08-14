import { Link as RouterLink } from "react-router-dom";

import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Toolbar from "@mui/material/Toolbar";

import { BrandMark } from "./BrandMark.jsx";
import { ColorModeToggle } from "./ColorModeToggle.jsx";

/**
 * Shell de las rutas publicas (portada).
 *
 * Deliberadamente mas ligero que `AppShell`: sin menu de modulos, porque sin
 * sesion no hay modulos que mostrar y un menu vacio solo confunde.
 */
export function PublicShell({ children }) {
  return (
    <Box sx={{ minHeight: "100dvh", display: "flex", flexDirection: "column" }}>
      <AppBar
        elevation={0}
        position="sticky"
        sx={{
          bgcolor: "background.paper",
          color: "text.primary",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Toolbar sx={{ minHeight: 52, height: 52, px: 2, gap: 1 }}>
          <Box
            component={RouterLink}
            sx={{ textDecoration: "none", color: "inherit" }}
            to="/"
          >
            <BrandMark />
          </Box>
          <Box
            sx={{ ml: "auto", display: "flex", gap: 1, alignItems: "center" }}
          >
            <ColorModeToggle />
            <Button component={RouterLink} to="/login" variant="contained">
              Iniciar sesion
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      <Box
        component="main"
        sx={{
          flex: 1,
          bgcolor: "background.default",
          px: { xs: 1.5, md: 3 },
          py: 4,
        }}
      >
        <Box sx={{ maxWidth: 1080, mx: "auto" }}>{children}</Box>
      </Box>
    </Box>
  );
}
