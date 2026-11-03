import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";

/**
 * Enlace de texto interno (ruta de la aplicacion).
 *
 * Es un `Link` de react-router con el color del sistema, sin `@mui/material/Link`:
 * cada componente MUI nuevo entra al chunk inicial compartido, y un enlace no lo
 * justifica.
 */
export function TextLink({ children, onClick, sx, to, ...rest }) {
  return (
    <Box
      component={RouterLink}
      onClick={onClick}
      sx={{
        color: "primary.main",
        fontSize: "inherit",
        textDecoration: "underline",
        textUnderlineOffset: "0.15em",
        "&:hover": { textDecorationThickness: "2px" },
        ...sx,
      }}
      to={to}
      {...rest}
    >
      {children}
    </Box>
  );
}
