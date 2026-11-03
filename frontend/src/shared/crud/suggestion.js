/**
 * Valores que el backend sugiere para prellenar un formulario.
 *
 * Los codigos institucionales (estudiante, empleado, sede, nivel, grado) los
 * emite el backend. El formulario los MUESTRA antes de guardar porque un campo
 * que se llena solo en el momento del submit se lee como perdida de datos, y
 * porque siguen siendo editables: un traslado llega con su codigo ya impreso.
 *
 * La sugerencia se pide al abrir el formulario y no mientras esta abierto: asi
 * el valor ya esta en `initialValues` al montar y el campo no cambia solo debajo
 * de quien esta escribiendo.
 */

/**
 * Pide la sugerencia y devuelve texto vacio si no se pudo.
 *
 * Un fallo aca NO puede bloquear el alta: el backend genera el codigo igual
 * cuando el campo llega vacio, asi que lo unico que se pierde es verlo de
 * antemano. Cerrar el formulario por no poder mostrar un valor opcional seria
 * cambiar un inconveniente por un bloqueo.
 */
export async function suggestedOrBlank(load) {
  try {
    return (await load()) ?? "";
  } catch {
    return "";
  }
}
