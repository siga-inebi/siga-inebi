/**
 * Fabrica unica de query keys para react-query.
 *
 * Una key armada a mano en cada call site (`["students", params]` aqui,
 * `["students-list", params]` alla) fragmenta la cache sin que nadie lo note:
 * dos componentes que piden exactamente lo mismo terminan en cubetas
 * distintas y la peticion se duplica de todas formas. Centralizarla aqui es
 * lo que hace que "misma peticion, misma key" sea una garantia y no una
 * convencion que hay que recordar.
 *
 * Cada rama es una funcion, no un array literal: agregar un parametro nuevo
 * a una peticion no debe obligar a tocar todos los call sites existentes.
 */
export const queryKeys = {
  catalog: (name, reloadToken = 0) => ["catalog", name, reloadToken],
  /** Busqueda server-side generica, para pickers de cualquier entidad. */
  search: (name, term) => ["search", name, term],
  students: {
    list: (params = {}) => ["students", "list", params],
  },
  teachers: {
    list: (params = {}) => ["teachers", "list", params],
  },
  guardians: {
    list: (params = {}) => ["guardians", "list", params],
  },
  academics: {
    levels: (params = {}) => ["academics", "levels", params],
  },
  reporting: {
    alerts: (params = {}) => ["reporting", "alerts", params],
  },
};
