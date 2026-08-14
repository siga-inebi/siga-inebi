import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";

/**
 * Boton de icono para columnas de acciones y encabezados.
 *
 * El `<span>` alrededor del boton no es decorativo: un elemento deshabilitado
 * no emite eventos de mouse, asi que sin el envoltorio el tooltip nunca
 * aparece justo cuando mas hace falta (explicar por que la accion no procede).
 *
 * @param {object}   props
 * @param {string}   props.label   Sirve de tooltip y de aria-label.
 * @param {ReactNode} props.children Icono.
 */
export function ActionIconButton({ children, disabled, label, onClick, ...rest }) {
  return (
    <Tooltip title={label}>
      <span>
        <IconButton
          aria-label={label}
          disabled={disabled}
          onClick={(event) => {
            // La fila puede tener onRowClick: sin esto, tocar "Eliminar"
            // tambien abriria el detalle detras del dialogo.
            event.stopPropagation();
            onClick?.(event);
          }}
          size="small"
          sx={{ width: "2.25rem", height: "2.25rem" }}
          {...rest}
        >
          {children}
        </IconButton>
      </span>
    </Tooltip>
  );
}
