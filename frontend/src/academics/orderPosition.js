/**
 * Posicion en el orden pedagogico, como se pregunta en un formulario.
 *
 * El backend recibe `insert_after`: el identificador del hermano al que el
 * registro debe seguir, `null` para el primer lugar, o el campo ausente para el
 * final. Un `<select>` no puede emitir "ausente" ni `null`, asi que los tres
 * estados viajan como texto y se traducen al enviar.
 *
 * Se pregunta la posicion y no el numero de secuencia porque nadie sabe "que
 * numero es Basico": sabe que Basico va despues de Primaria. Y antes, meter uno
 * en el medio obligaba a renumerar a mano todos los de abajo, uno por
 * formulario, contra un constraint que rechaza cualquier estado intermedio.
 */

export const AT_END = "__end__";
export const AT_START = "__start__";

/**
 * Opciones del selector, en el orden en que se van a ver.
 *
 * @param {Array<{public_id:string,name:string,sequence:number}>} siblings
 * @param {string} [excludeId] El registro que se esta moviendo: no puede ir
 *   despues de si mismo.
 */
export function positionOptions(siblings, excludeId) {
  const others = ordered(siblings).filter(
    (item) => item.public_id !== excludeId
  );

  return [
    { value: AT_END, label: "Al final" },
    { value: AT_START, label: "Al inicio" },
    ...others.map((item) => ({
      value: item.public_id,
      label: `Despues de ${item.name}`,
    })),
  ];
}

/**
 * Posicion actual de un registro, para que el selector no mienta al editar.
 *
 * Es "despues del anterior" y no "al final" aunque sea el ultimo: describir la
 * posicion por su vecino de arriba es lo unico que sigue siendo verdad cuando
 * alguien mas agrega un hermano.
 */
export function currentPosition(siblings, id) {
  const rows = ordered(siblings);
  const index = rows.findIndex((item) => item.public_id === id);
  if (index <= 0) {
    return index === 0 ? AT_START : AT_END;
  }
  return rows[index - 1].public_id;
}

/**
 * Traduce el valor del selector a lo que espera la API.
 *
 * Devuelve un objeto para fusionar con el payload: `AT_END` no manda la clave,
 * porque "ausente" es lo que el backend lee como "al final". Mandar `null` ahi
 * lo pondria primero.
 */
export function positionPayload(value) {
  if (!value || value === AT_END) return {};
  return { insert_after: value === AT_START ? null : value };
}

/** Campo de formulario, igual para niveles y grados. */
export function positionField(siblings, excludeId) {
  return {
    name: "insert_after",
    label: "Posicion",
    type: "select",
    options: positionOptions(siblings, excludeId),
    help: "Define el orden pedagogico. Los demas se renumeran solos.",
  };
}

function ordered(siblings) {
  return [...siblings].sort((left, right) => left.sequence - right.sequence);
}
