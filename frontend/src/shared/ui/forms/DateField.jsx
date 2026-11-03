import Button from "@mui/material/Button";
import InputAdornment from "@mui/material/InputAdornment";

import { todayInputValue } from "@shared/utils/format.js";
import { FormTextField } from "@ui/forms/FormTextField.jsx";

/**
 * Campo de fecha con atajo "Hoy".
 *
 * Casi toda fecha que se captura en el sistema es la de hoy: el movimiento de
 * asistencia que se acaba de registrar, la matricula que se esta haciendo, la
 * consulta del estado del dia. El selector nativo del navegador abre en el mes
 * corriente pero igual obliga a tres clics, y escribirla a mano en un campo con
 * formato del navegador ("mm/dd/yyyy") es donde aparecen los dedazos que
 * despues nadie encuentra.
 *
 * El boton vive dentro del campo, como adorno final, para que quede claro a QUE
 * fecha aplica cuando hay dos o tres en el mismo formulario.
 *
 * La etiqueta se fuerza arriba desde el principio: un input de fecha SIEMPRE
 * pinta su propio placeholder, y la etiqueta flotante se le encima.
 */
export function DateField({ disabled, onChange, name, value, ...rest }) {
  const today = todayInputValue();
  const isToday = value === today;

  return (
    <FormTextField
      disabled={disabled}
      name={name}
      onChange={onChange}
      slotProps={{
        inputLabel: { shrink: true },
        input: {
          endAdornment: (
            <InputAdornment position="end">
              <Button
                aria-label="Usar la fecha de hoy"
                disabled={disabled || isToday}
                onClick={() => onChange({ target: { name, value: today } })}
                size="small"
                sx={{ minWidth: 0, px: 1 }}
                variant="text"
              >
                Hoy
              </Button>
            </InputAdornment>
          ),
        },
      }}
      type="date"
      value={value ?? ""}
      {...rest}
    />
  );
}
