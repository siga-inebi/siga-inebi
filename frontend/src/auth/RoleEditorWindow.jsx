import { useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { groupPermissions } from "@auth/rolesService.js";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

import { slugPreview } from "./roleText.js";

/**
 * Editor de rol (docs/ux-ui.md RO1-RO4).
 *
 * - Permisos agrupados por modulo, con una casilla por grupo y la descripcion
 *   de cada permiso en espanol (RO1, RO2).
 * - El identificador (`slug`) no se escribe: se deriva del nombre y queda fijo
 *   despues de crear el rol (RO3).
 * - Junto al tiempo de inactividad se explica que, con varios roles, gana el
 *   mayor (RO4).
 * - Un rol del sistema se muestra protegido y con el motivo (RO3).
 */
export function RoleEditorWindow({
  canEditSystem,
  onClose,
  onSubmit,
  open,
  permissions,
  role,
}) {
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");
  const [timeout, setTimeoutMinutes] = useState(
    String(role?.session_idle_timeout_minutes ?? 30)
  );
  const [selected, setSelected] = useState(new Set(role?.permissions ?? []));
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const groups = useMemo(() => groupPermissions(permissions), [permissions]);
  const locked = Boolean(role?.is_system) && !canEditSystem;

  const toggle = (code) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });

  const toggleGroup = (group, checked) =>
    setSelected((current) => {
      const next = new Set(current);
      for (const permission of group.permissions) {
        if (checked) next.add(permission.code);
        else next.delete(permission.code);
      }
      return next;
    });

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("Escriba el nombre del rol.");
      return;
    }
    const minutes = Number(timeout);
    if (!Number.isInteger(minutes) || minutes < 1) {
      setError("El tiempo de inactividad debe ser de al menos 1 minuto.");
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim(),
        session_idle_timeout_minutes: minutes,
        permissions: [...selected].sort(),
      });
    } catch (submitError) {
      setError(submitError.message);
      setSubmitting(false);
    }
  };

  return (
    <FloatingWindow
      busy={submitting}
      footer={
        <>
          <Button disabled={submitting} onClick={onClose} variant="text">
            Cancelar
          </Button>
          <Button
            disabled={submitting || locked}
            form="role-editor-form"
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            type="submit"
            variant="contained"
          >
            {role ? "Guardar cambios" : "Crear rol"}
          </Button>
        </>
      }
      onClose={onClose}
      open={open}
      title={role ? `Editar rol «${role.name}»` : "Nuevo rol"}
      width={WINDOW_WIDTH.wide}
    >
      <Stack
        component="form"
        gap={2.5}
        id="role-editor-form"
        noValidate
        onSubmit={submit}
      >
        {locked ? (
          <Alert severity="info" variant="outlined">
            Rol del sistema: lo crea la instalación y protege el acceso de
            administración. Solo un superusuario puede modificarlo, para que
            nadie se quede sin poder administrar cuentas por un cambio aquí.
          </Alert>
        ) : null}
        {error ? (
          <Alert role="alert" severity="error">
            {error}
          </Alert>
        ) : null}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "2fr 1fr" },
            gap: 2,
          }}
        >
          <FormTextField
            disabled={locked || submitting}
            helperText={
              role
                ? `Identificador: ${role.slug} (no cambia).`
                : `Identificador: ${slugPreview(name) || "—"} (se genera del nombre).`
            }
            label="Nombre"
            name="name"
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
          <FormTextField
            disabled={locked || submitting}
            helperText="Si una cuenta tiene varios roles, gana el tiempo MAYOR entre ellos."
            label="Cierre por inactividad (minutos)"
            name="session_idle_timeout_minutes"
            onChange={(event) => setTimeoutMinutes(event.target.value)}
            slotProps={{ htmlInput: { min: 1 } }}
            type="number"
            value={timeout}
          />
        </Box>
        <FormTextField
          disabled={locked || submitting}
          label="Descripción"
          minRows={2}
          multiline
          name="description"
          onChange={(event) => setDescription(event.target.value)}
          value={description}
        />

        <Typography fontWeight={600} variant="subtitle2">
          Permisos ({selected.size} de {permissions.length})
        </Typography>
        <Stack gap={1.5}>
          {groups.map((group) => {
            const chosen = group.permissions.filter((p) =>
              selected.has(p.code)
            ).length;
            return (
              <Box
                component="fieldset"
                key={group.key}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 1,
                  m: 0,
                  px: 2,
                  py: 1,
                }}
              >
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={chosen === group.permissions.length}
                      disabled={locked || submitting}
                      indeterminate={
                        chosen > 0 && chosen < group.permissions.length
                      }
                      onChange={(event) =>
                        toggleGroup(group, event.target.checked)
                      }
                    />
                  }
                  label={
                    <Typography fontWeight={600} variant="body2">
                      {group.label} ({chosen}/{group.permissions.length})
                    </Typography>
                  }
                />
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                    columnGap: 2,
                    pl: 3,
                  }}
                >
                  {group.permissions.map((permission) => (
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selected.has(permission.code)}
                          disabled={locked || submitting}
                          onChange={() => toggle(permission.code)}
                          size="small"
                        />
                      }
                      key={permission.code}
                      label={
                        <Box>
                          <Typography variant="body2">
                            {permission.name}
                          </Typography>
                          <Typography color="text.secondary" variant="caption">
                            {permission.description}
                          </Typography>
                        </Box>
                      }
                      sx={{ alignItems: "flex-start", my: 0.5 }}
                    />
                  ))}
                </Box>
              </Box>
            );
          })}
        </Stack>
      </Stack>
    </FloatingWindow>
  );
}
