import { useState } from "react";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Divider from "@mui/material/Divider";
import ListItemIcon from "@mui/material/ListItemIcon";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import LockResetIcon from "@mui/icons-material/LockReset";
import LogoutIcon from "@mui/icons-material/Logout";

import { ChangePasswordWindow } from "@auth/ChangePasswordWindow.jsx";
import { formatFullName } from "@shared/utils/format.js";

/** Iniciales para el avatar cuando no hay foto. */
function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

/**
 * Identidad de la sesion y cierre de sesion.
 *
 * @param {object}   props
 * @param {object}   props.user
 * @param {Function} props.onLogout
 */
export function UserMenu({ onLogout, user }) {
  const [anchor, setAnchor] = useState(null);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const displayName =
    formatFullName(user?.person) !== "—"
      ? formatFullName(user.person)
      : (user?.username ?? "Sesion");

  return (
    <>
      <ButtonBase
        aria-haspopup="menu"
        aria-label="Cuenta"
        onClick={(event) => setAnchor(event.currentTarget)}
        sx={(theme) => ({
          gap: 1,
          px: 1,
          py: 0.5,
          borderRadius: theme.tokens.radii.input,
          "&:hover": { bgcolor: "action.hover" },
        })}
      >
        <Avatar
          sx={{
            width: 28,
            height: 28,
            fontSize: "0.75rem",
            bgcolor: "primary.main",
            color: "primary.contrastText",
          }}
        >
          {initials(displayName)}
        </Avatar>
        <Typography
          sx={{
            fontSize: "0.8125rem",
            fontWeight: 500,
            display: { xs: "none", md: "block" },
          }}
        >
          {displayName}
        </Typography>
      </ButtonBase>

      <Menu
        anchorEl={anchor}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        onClose={() => setAnchor(null)}
        open={Boolean(anchor)}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
      >
        <Box sx={{ px: 2, py: 1.5, minWidth: 200 }}>
          <Typography sx={{ fontSize: "0.875rem", fontWeight: 600 }}>
            {displayName}
          </Typography>
          <Stack gap={0.25} sx={{ mt: 0.25 }}>
            <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
              {user?.username}
            </Typography>
            {user?.email ? (
              <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
                {user.email}
              </Typography>
            ) : null}
          </Stack>
        </Box>
        <Divider />
        <MenuItem
          onClick={() => {
            setAnchor(null);
            setChangePasswordOpen(true);
          }}
        >
          <ListItemIcon>
            <LockResetIcon fontSize="small" />
          </ListItemIcon>
          Cambiar contrasena
        </MenuItem>
        <MenuItem
          onClick={() => {
            setAnchor(null);
            onLogout();
          }}
        >
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          Cerrar sesion
        </MenuItem>
      </Menu>

      <ChangePasswordWindow
        onClose={() => setChangePasswordOpen(false)}
        open={changePasswordOpen}
      />
    </>
  );
}
