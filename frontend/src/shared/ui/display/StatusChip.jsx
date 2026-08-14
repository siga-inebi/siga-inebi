import Chip from "@mui/material/Chip";

/**
 * Unico componente de badge de estado del sistema.
 *
 * La `variant` es semantica, nunca un color: el dominio dice "success" y el
 * tema decide que verde toca en claro y cual en oscuro. Asi, agregar modo
 * oscuro o cambiar la marca no obliga a tocar ni un mapa de dominio.
 *
 * @param {object} props
 * @param {"primary"|"success"|"warning"|"danger"|"purple"|"neutral"|"accent"} [props.variant="neutral"]
 * @param {string} props.label
 * @param {"small"|"medium"} [props.size="small"]
 */
export function StatusChip({ label, size = "small", sx, variant = "neutral", ...rest }) {
  return (
    <Chip
      label={label}
      size={size}
      sx={(theme) => {
        const colors =
          theme.palette.chipVariants[variant] ?? theme.palette.chipVariants.neutral;
        return {
          backgroundColor: colors.bg,
          color: colors.text,
          fontWeight: 500,
          ...sx,
        };
      }}
      {...rest}
    />
  );
}
