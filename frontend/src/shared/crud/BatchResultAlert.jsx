import Alert from "@mui/material/Alert";
import Stack from "@mui/material/Stack";

/**
 * Resumen de una carga por lotes: cuantas entraron y que paso con las demas.
 *
 * La severidad sale de si hubo fallos, no de si hubo exitos: un lote con
 * cincuenta creadas y una rechazada NO es un exito, porque queda una fila que
 * alguien tiene que atender. Pintarlo en verde es como se pierde.
 *
 * Cada fallo se lista con su motivo. Un "3 de 60 fallaron" sin decir cuales
 * obliga a comparar el listado entero a mano para encontrarlas.
 *
 * @param {{created: Array, failed: Array<{label: string, message: string}>}} result
 * @param {string} noun          Singular de lo que se creo ("matricula").
 * @param {string} [nounPlural]  Plural, si no es `noun + "s"`.
 */
export function BatchResultAlert({ result, noun, nounPlural }) {
  if (!result) return null;

  const total = result.created.length;
  const plural = nounPlural ?? `${noun}s`;

  return (
    <Alert severity={result.failed.length > 0 ? "warning" : "success"}>
      <Stack gap={0.5}>
        <span>
          {total} {total === 1 ? noun : plural} creada
          {total === 1 ? "" : "s"}.
        </span>
        {result.failed.map((failure) => (
          <span key={failure.label}>
            {failure.label}: {failure.message}
          </span>
        ))}
      </Stack>
    </Alert>
  );
}
