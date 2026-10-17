import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { usePasswordRules } from "@auth/passwordPolicy.js";

/** Lista de requisitos de contraseña tal como los aplica el backend (MC2). */
export function PasswordRules() {
  const { rules } = usePasswordRules();
  if (rules.length === 0) return null;
  return (
    <Box
      aria-label="Requisitos de la contraseña"
      component="section"
      sx={{ color: "text.secondary" }}
    >
      <Typography component="p" sx={{ fontSize: "0.75rem", fontWeight: 600 }}>
        La contraseña debe cumplir:
      </Typography>
      <Box component="ul" sx={{ m: 0, pl: 2.5, fontSize: "0.75rem" }}>
        {rules.map((rule) => (
          <li key={rule}>{rule}</li>
        ))}
      </Box>
    </Box>
  );
}
