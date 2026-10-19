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
 * Cada key empieza por el dominio (`["students", ...]`, `["identity", ...]`):
 * invalidar `["students"]` despues de una escritura alcanza a todo lo que ese
 * dominio muestra (ux-ui 1.2.3). Ninguna key se arma con `fn.name`: en el build
 * de produccion los nombres se minifican y dos catalogos distintos podian
 * compartir cubeta (ux-ui 1.2.4).
 */

/** Nombres explicitos de los catalogos compartidos (ver `academicCatalogs.js`). */
export const CATALOG = Object.freeze({
  cycles: "cycles",
  subjects: "subjects",
  teachers: "teachers",
  students: "students",
  shifts: "shifts",
  grades: "grades",
  sections: "sections",
  enrolments: "enrolments",
  campuses: "campuses",
});

export const queryKeys = {
  catalog: (name, ...params) => ["catalog", name, ...params],
  enrolments: {
    all: ["enrolments"],
    occupancy: (params) => ["enrolments", "occupancy", params],
  },
  /** Busqueda server-side generica, para pickers de cualquier entidad. */
  search: (name, term) => ["search", name, term],
  /** Listado paginado en servidor (`useServerList`). */
  list: (domain, name, params = {}) => [domain, "list", name, params],
  students: {
    all: ["students"],
    list: (params = {}) => ["students", "list", params],
  },
  teachers: {
    all: ["teachers"],
    list: (params = {}) => ["teachers", "list", params],
  },
  guardians: {
    all: ["guardians"],
    list: (params = {}) => ["guardians", "list", params],
  },
  people: {
    all: ["people"],
  },
  academics: {
    all: ["academics"],
    levels: (params = {}) => ["academics", "levels", params],
  },
  reporting: {
    all: ["reporting"],
    alerts: (params = {}) => ["reporting", "alerts", params],
  },
  dashboard: {
    all: ["dashboard"],
    health: () => ["dashboard", "health"],
  },
  identity: {
    all: ["identity"],
    me: () => ["identity", "me"],
    passwordPolicy: () => ["identity", "password-policy"],
    account: (publicId) => ["identity", "account", publicId],
    accountAssignments: (publicId) => [
      "identity",
      "account",
      publicId,
      "assignments",
    ],
    roles: (params = {}) => ["identity", "roles", params],
    roleHolders: (publicId) => ["identity", "roles", publicId, "holders"],
    permissions: () => ["identity", "permissions"],
    permissionHolders: (code) => ["identity", "permissions", code, "holders"],
    expiring: (days) => ["identity", "expiring", days],
    scopeOptions: () => ["identity", "scope-options"],
    usernameSuggestion: (personId) => [
      "identity",
      "username-suggestion",
      personId,
    ],
  },
  audit: {
    all: ["audit"],
  },
  platform: {
    all: ["platform"],
    taskHealth: () => ["platform", "task-health"],
    backupHealth: () => ["platform", "backup-health"],
  },
};
