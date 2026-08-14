import { useColorScheme } from "@mui/material/styles";
import Tooltip from "@mui/material/Tooltip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import SettingsBrightnessIcon from "@mui/icons-material/SettingsBrightness";

const MODES = [
  { value: "light", label: "Claro", Icon: LightModeIcon },
  { value: "dark", label: "Oscuro", Icon: DarkModeIcon },
  { value: "system", label: "Sistema", Icon: SettingsBrightnessIcon },
];

/**
 * Selector de apariencia.
 *
 * La persistencia la gestiona MUI en `localStorage["mui-mode"]` a traves de
 * `useColorScheme()`; este componente no escribe esa clave a mano. El script
 * anti-flash de `index.html` la lee antes de la primera pintura.
 */
export function ColorModeToggle() {
  const { mode, setMode } = useColorScheme();

  // En el primer render del servidor/hidratacion `mode` viene undefined; hasta
  // que resuelve, no hay nada que marcar como seleccionado.
  if (!mode) return null;

  return (
    <ToggleButtonGroup
      aria-label="Apariencia"
      exclusive
      onChange={(_event, next) => {
        if (next) setMode(next);
      }}
      size="small"
      value={mode}
    >
      {MODES.map(({ Icon, label, value }) => (
        <Tooltip key={value} title={label}>
          <ToggleButton aria-label={label} value={value}>
            <Icon fontSize="small" />
          </ToggleButton>
        </Tooltip>
      ))}
    </ToggleButtonGroup>
  );
}
