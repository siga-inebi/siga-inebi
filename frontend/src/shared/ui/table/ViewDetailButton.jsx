import Button from "@mui/material/Button";

/**
 * Accion "Ver" de la ultima columna de un listado.
 *
 * Existe aunque la fila entera sea clickeable: una `<tr>` con `onClick` no
 * recibe foco ni responde al teclado, asi que sin este boton el detalle seria
 * inalcanzable para quien navega con tabulador o con lector de pantalla. El
 * click en la fila es el atajo; este boton es el camino accesible.
 *
 * @param {object}   props
 * @param {string}   props.label  Nombre accesible completo ("Ver detalle de Ana Gomez").
 * @param {Function} props.onClick
 */
export function ViewDetailButton({ label, onClick }) {
  return (
    <Button
      aria-label={label}
      onClick={(event) => {
        // La fila tambien escucha el click: sin esto el detalle se abriria dos veces.
        event.stopPropagation();
        onClick(event);
      }}
      size="small"
      variant="outlined"
    >
      Ver
    </Button>
  );
}
