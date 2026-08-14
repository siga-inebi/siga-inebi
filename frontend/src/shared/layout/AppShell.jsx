import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Toolbar from "@mui/material/Toolbar";
import Tooltip from "@mui/material/Tooltip";
import KeyboardDoubleArrowLeftIcon from "@mui/icons-material/KeyboardDoubleArrowLeft";
import KeyboardDoubleArrowRightIcon from "@mui/icons-material/KeyboardDoubleArrowRight";
import MenuIcon from "@mui/icons-material/Menu";

import { BrandMark } from "./BrandMark.jsx";
import { ColorModeToggle } from "./ColorModeToggle.jsx";
import { Sidebar, SIDEBAR_COLLAPSED_WIDTH, SIDEBAR_WIDTH } from "./Sidebar.jsx";
import { UserMenu } from "./UserMenu.jsx";

const TOOLBAR_HEIGHT = 52;

/**
 * Shell de la aplicacion privada: barra superior + menu lateral + contenido.
 *
 * Regla estructural del sistema: **un solo scroll por pantalla**. El shell mide
 * `height: 100dvh` con `overflow: hidden` y reparte el alto; lo que scrollea es
 * el contenido (o la tabla, en modo `fillHeight`). Sin esto aparece el doble
 * scroll clasico de back-office, donde la pagina y la tabla se mueven por
 * separado y el usuario nunca sabe cual esta arrastrando.
 *
 * `100dvh` y no `100vh`: en moviles la barra de direcciones del navegador entra
 * y sale, y `vh` mide el viewport sin ella, dejando el footer cortado.
 *
 * @param {object}   props
 * @param {object}   props.user
 * @param {Function} props.onLogout
 * @param {object}  [props.counts]  Conteos por modulo para los badges del menu.
 * @param {ReactNode} props.children
 */
export function AppShell({ children, counts, onLogout, user }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const asideWidth = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH;
  const closeMobile = () => setMobileOpen(false);

  const sidebar = (
    <Sidebar
      collapsed={collapsed}
      counts={counts}
      onNavigate={closeMobile}
      user={user}
    />
  );

  return (
    <Box
      sx={{
        height: "100dvh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
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
        <Toolbar
          sx={{
            minHeight: TOOLBAR_HEIGHT,
            height: TOOLBAR_HEIGHT,
            px: 2,
            gap: 1,
          }}
        >
          <IconButton
            aria-label="Abrir menu"
            edge="start"
            onClick={() => setMobileOpen(true)}
            size="small"
            sx={{ display: { md: "none" }, mr: 0.5 }}
          >
            <MenuIcon fontSize="small" />
          </IconButton>

          <Box
            component={RouterLink}
            sx={{ textDecoration: "none", color: "inherit" }}
            to="/app"
          >
            <BrandMark />
          </Box>

          <Stack direction="row" gap={1} sx={{ ml: "auto" }}>
            <ColorModeToggle />
            <UserMenu onLogout={onLogout} user={user} />
          </Stack>
        </Toolbar>
      </AppBar>

      <Box sx={{ flex: 1, minHeight: 0, display: "flex" }}>
        {/* Menu fijo en md+; en movil es un cajon temporal. */}
        <Box
          component="aside"
          sx={{
            display: { xs: "none", md: "flex" },
            flexDirection: "column",
            width: asideWidth,
            flexShrink: 0,
            borderRight: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
            transition: "width 0.2s ease",
          }}
        >
          <Box sx={{ flex: 1, minHeight: 0 }}>{sidebar}</Box>
          <Box
            sx={{
              p: 1,
              borderTop: "1px solid",
              borderColor: "divider",
              display: "flex",
              justifyContent: collapsed ? "center" : "flex-end",
            }}
          >
            <Tooltip title={collapsed ? "Expandir menu" : "Colapsar menu"}>
              <IconButton
                aria-label={collapsed ? "Expandir menu" : "Colapsar menu"}
                onClick={() => setCollapsed((value) => !value)}
                size="small"
              >
                {collapsed ? (
                  <KeyboardDoubleArrowRightIcon fontSize="small" />
                ) : (
                  <KeyboardDoubleArrowLeftIcon fontSize="small" />
                )}
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <Drawer
          onClose={closeMobile}
          open={mobileOpen}
          slotProps={{ paper: { sx: { width: SIDEBAR_WIDTH } } }}
          sx={{ display: { md: "none" } }}
        >
          <Toolbar
            sx={{ minHeight: TOOLBAR_HEIGHT, height: TOOLBAR_HEIGHT, px: 2 }}
          >
            <BrandMark compact />
          </Toolbar>
          {sidebar}
        </Drawer>

        <Box
          component="main"
          sx={{
            flex: 1,
            minWidth: 0,
            minHeight: 0,
            overflowY: "auto",
            bgcolor: "background.default",
          }}
        >
          <Box
            sx={{
              px: { xs: 1.5, md: 3 },
              py: 3,
              maxWidth: 1440,
              mx: "auto",
              minHeight: "100%",
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            {children}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
