/**
 * invalidation.js — "Toda mutacion invalida o actualiza lo que muestra"
 * (docs/ux-ui.md 1.2.3).
 *
 * Antes no habia un solo `invalidateQueries` en el frontend: crear un docente y
 * abrir enseguida "Nueva asignacion" no lo mostraba hasta que vencia la cache.
 *
 * La regla se aplica en dos niveles:
 *
 * 1. Global y automatico: `apiClient` emite `siga:mutation` despues de cada
 *    escritura exitosa, y `registerMutationInvalidation` invalida las keys que
 *    esa ruta puede haber cambiado (tabla `MUTATION_RULES`). Ninguna pantalla
 *    tiene que acordarse: escribir ya invalida.
 * 2. Explicito: `useInvalidate()` / `invalidateKeys()` para quien necesita
 *    invalidar algo que no sale de la ruta (o actualizar la cache a mano con
 *    `queryClient.setQueryData`).
 *
 * Invalidar no borra: marca la query como vieja y react-query solo vuelve a
 * pedir las que estan montadas. El costo es una peticion por lista visible.
 */

import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { MUTATION_EVENT } from "./apiClient.js";
import { CATALOG, queryKeys } from "./queryKeys.js";

const catalog = (name) => ["catalog", name];
const search = (name) => ["search", name];

/**
 * Prefijo de ruta -> keys afectadas. Se evaluan TODAS las reglas cuyo prefijo
 * coincide (una ruta de encargados toca tambien a estudiantes). Rutas mas
 * especificas primero solo por legibilidad.
 */
export const MUTATION_RULES = [
  {
    pattern: /^\/students\/records\/[^/]+\/guardians\/link\/?$/,
    keys: [
      queryKeys.guardians.all,
      queryKeys.people.all,
      catalog("guardians"),
      search("guardians"),
      catalog("people"),
      search("people"),
    ],
  },
  {
    prefix: "/students/guardians",
    keys: [
      queryKeys.guardians.all,
      catalog("guardians"),
      search("guardians"),
      queryKeys.dashboard.all,
    ],
  },
  {
    prefix: "/students",
    keys: [
      queryKeys.students.all,
      catalog(CATALOG.students),
      search(CATALOG.students),
      catalog(CATALOG.enrolments),
      queryKeys.dashboard.all,
    ],
  },
  {
    prefix: "/teachers",
    keys: [
      queryKeys.teachers.all,
      catalog(CATALOG.teachers),
      search(CATALOG.teachers),
      queryKeys.dashboard.all,
    ],
  },
  {
    prefix: "/people",
    keys: [queryKeys.people.all, queryKeys.identity.all],
  },
  {
    prefix: "/academics",
    // `["search"]`: los selectores con busqueda de secciones, aulas y cursos
    // llevan el ciclo o la sede en el nombre de la key.
    keys: [queryKeys.academics.all, ["catalog"], ["search"]],
  },
  {
    prefix: "/enrolments",
    keys: [
      ["enrolments"],
      catalog(CATALOG.enrolments),
      catalog(CATALOG.students),
    ],
  },
  { prefix: "/attendance", keys: [["attendance"]] },
  { prefix: "/evaluation", keys: [["evaluation"]] },
  { prefix: "/documents", keys: [["documents"]] },
  { prefix: "/reporting", keys: [queryKeys.reporting.all] },
  { prefix: "/identity", keys: [queryKeys.identity.all] },
  { prefix: "/audit", keys: [queryKeys.audit.all] },
];

/** Escrituras que no cambian datos que alguna pantalla muestre desde cache. */
const IGNORED_PREFIXES = ["/auth/login", "/auth/logout", "/auth/session"];

/**
 * Keys a invalidar despues de escribir en `path`. Devuelve `null` cuando ninguna
 * regla aplica: en ese caso se invalida todo, porque dejar una pantalla con
 * datos viejos es peor que una peticion de mas.
 */
export function keysForMutation(path) {
  const cleanPath = String(path ?? "").split("?")[0];
  if (IGNORED_PREFIXES.some((prefix) => cleanPath.startsWith(prefix))) {
    return [];
  }
  const keys = MUTATION_RULES.filter((rule) =>
    rule.pattern
      ? rule.pattern.test(cleanPath)
      : cleanPath.startsWith(rule.prefix)
  ).flatMap((rule) => rule.keys);
  return keys.length > 0 ? keys : null;
}

/** Invalida cada key (por prefijo). `keys` vacio no hace nada. */
export function invalidateKeys(queryClient, keys) {
  return Promise.all(
    keys.map((queryKey) => queryClient.invalidateQueries({ queryKey }))
  );
}

/** Invalida lo que una escritura en `path` pudo cambiar. */
export function invalidateForMutation(queryClient, path) {
  const keys = keysForMutation(path);
  if (keys === null) {
    return queryClient.invalidateQueries();
  }
  return invalidateKeys(queryClient, keys);
}

/**
 * Conecta los eventos de escritura de `apiClient` con la cache. Se registra una
 * vez, junto al `QueryClient` de la app. Devuelve la funcion para desconectar.
 */
export function registerMutationInvalidation(queryClient, target = window) {
  const handler = (event) => {
    invalidateForMutation(queryClient, event.detail?.path);
  };
  target.addEventListener(MUTATION_EVENT, handler);
  return () => target.removeEventListener(MUTATION_EVENT, handler);
}

/** Hook para invalidar keys explicitas desde un componente. */
export function useInvalidate() {
  const queryClient = useQueryClient();
  return useCallback(
    (...keys) => invalidateKeys(queryClient, keys),
    [queryClient]
  );
}
