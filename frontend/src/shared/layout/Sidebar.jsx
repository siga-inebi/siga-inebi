import { NavLink } from "react-router-dom";

import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { HOME_ITEM, prefetchModule, visibleGroups } from "@app/navigation.js";
import { palette } from "@theme/tokens/color.js";

export const SIDEBAR_WIDTH = 232;
export const SIDEBAR_COLLAPSED_WIDTH = 64;

/**
 * Item del menu lateral.
 *
 * El indicador activo es un borde izquierdo de 3px, no un fondo saturado: en un
 * menu de ocho entradas un bloque de color lleno compite con el contenido de la
 * pagina, que es lo que el usuario vino a leer.
 */
function SidebarItem({ badge, collapsed, item, onNavigate }) {
  const Icon = item.icon;

  const content = (
    <ButtonBase
      // El nombre accesible se declara explicito porque colapsado el texto no se
      // renderiza: sin esto el enlace queda anunciado como "link" a secas.
      aria-label={item.label}
      component={NavLink}
      end={item.end}
      onClick={onNavigate}
      onFocus={() => prefetchModule(item)}
      // Precarga el chunk antes del clic: al soltar el mouse la pagina ya esta.
      onPointerEnter={() => prefetchModule(item)}
      sx={(theme) => ({
        display: "flex",
        alignItems: "center",
        justifyContent: collapsed ? "center" : "flex-start",
        gap: 1.5,
        width: "100%",
        minHeight: 44,
        px: collapsed ? 0 : 2,
        borderLeft: "3px solid transparent",
        color: "text.secondary",
        textAlign: "left",
        "&:hover": { bgcolor: palette(theme).surfaces.sunken },
        "&.active": {
          // Marcador dorado: misma firma que el encabezado de seccion, para que
          // "donde estoy" y "que estoy viendo" usen la misma senal.
          borderLeftColor: palette(theme).surfaces.sectionMarker,
          bgcolor: palette(theme).surfaces.sunken,
          color: "text.primary",
          "& .sidebar-label": { fontWeight: 600 },
        },
      })}
      to={item.path}
    >
      <Icon fontSize="small" />
      {collapsed ? null : (
        <>
          <Typography
            className="sidebar-label"
            sx={{ fontSize: "0.8125rem", flex: 1, minWidth: 0 }}
          >
            {item.label}
          </Typography>
          {badge != null ? (
            <Chip
              label={badge}
              size="small"
              sx={{ height: "1.25rem", fontSize: "0.6875rem" }}
            />
          ) : null}
        </>
      )}
    </ButtonBase>
  );

  // Colapsado solo queda el icono, asi que el tooltip pasa a ser la unica forma
  // de saber a donde lleva.
  return collapsed ? (
    <Tooltip placement="right" title={item.label}>
      <Box>{content}</Box>
    </Tooltip>
  ) : (
    content
  );
}

/**
 * Menu lateral de modulos.
 *
 * @param {object}  props
 * @param {boolean} props.collapsed
 * @param {object}  props.counts     Conteos por clave de modulo, para el badge.
 * @param {Function}[props.onNavigate] Cierra el cajon en movil al navegar.
 * @param {object}  props.user
 */
export function Sidebar({ collapsed = false, counts = {}, onNavigate, user }) {
  const groups = visibleGroups(user);

  return (
    <Stack
      sx={{ py: 1.5, height: "100%", overflowY: "auto", overflowX: "hidden" }}
    >
      <SidebarItem
        collapsed={collapsed}
        item={HOME_ITEM}
        onNavigate={onNavigate}
      />

      {/*
        Un <nav> por grupo, cada uno con su propio nombre accesible. Varias
        regiones de navegacion sin distinguir obligan al lector de pantalla a
        anunciarlas todas igual ("navegacion") y el usuario pierde de cual salta
        a cual.
      */}
      {groups.map((group) => (
        <Box
          aria-label={group.label}
          component="nav"
          key={group.key}
          sx={{ mt: 1.5 }}
        >
          {collapsed ? (
            <Box
              sx={{
                borderTop: "1px solid",
                borderColor: "divider",
                mx: 1.5,
                mb: 1,
              }}
            />
          ) : (
            <Typography
              component="p"
              sx={{ px: 2, color: "text.secondary" }}
              variant="overline"
            >
              {group.label}
            </Typography>
          )}
          {group.items.map((item) => (
            <SidebarItem
              badge={item.countable ? counts[item.key] : undefined}
              collapsed={collapsed}
              item={item}
              key={item.key}
              onNavigate={onNavigate}
            />
          ))}
        </Box>
      ))}
    </Stack>
  );
}
