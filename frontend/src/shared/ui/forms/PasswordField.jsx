import { useState } from "react";

import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";

import { FormTextField } from "./FormTextField.jsx";

/**
 * Campo de contraseña con boton para mostrarla u ocultarla (docs/ux-ui.md L6).
 *
 * Mostrar lo escrito evita el error mas comun al activar una cuenta o cambiar
 * la contraseña: un caracter equivocado que no se ve.
 *
 * `errors` (lista de mensajes del backend para este campo) se muestra debajo,
 * uno por linea, en vez de un mensaje generico arriba del formulario (MC2).
 */
export function PasswordField({ errors, helperText, slotProps, ...props }) {
  const [visible, setVisible] = useState(false);
  const messages = (errors ?? []).filter(Boolean);

  return (
    <FormTextField
      {...props}
      error={messages.length > 0 ? messages.join(" ") : props.error}
      helperText={helperText}
      slotProps={{
        ...slotProps,
        input: {
          ...slotProps?.input,
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                aria-label={
                  visible ? "Ocultar contraseña" : "Mostrar contraseña"
                }
                edge="end"
                onClick={() => setVisible((value) => !value)}
                size="small"
              >
                {visible ? (
                  <VisibilityOffOutlinedIcon fontSize="small" />
                ) : (
                  <VisibilityOutlinedIcon fontSize="small" />
                )}
              </IconButton>
            </InputAdornment>
          ),
        },
      }}
      type={visible ? "text" : "password"}
    />
  );
}
