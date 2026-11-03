import { useCallback, useContext, useEffect, useMemo, useState } from "react";

import { AuthContext } from "@auth/context.js";

/** Prefijo de las claves en localStorage. */
export const DRAFT_PREFIX = "siga:draft";

/**
 * Campos que NUNCA se guardan en un borrador, por nombre: contraseñas, codigos
 * de activacion y cualquier token. Un borrador vive en el navegador y puede
 * quedar en una computadora compartida.
 */
const SECRET_FIELD =
  /pass(word)?|contrase|activation|token|secret|code_activation/i;

function storage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function read(key) {
  try {
    const raw = storage()?.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    storage()?.setItem(key, JSON.stringify(value));
  } catch {
    // Sin almacenamiento (modo privado, cuota llena) el formulario sigue
    // funcionando; solo no hay borrador.
  }
}

function remove(key) {
  try {
    storage()?.removeItem(key);
  } catch {
    // Igual que arriba.
  }
}

/** Valores serializables y sin secretos. */
export function sanitizeDraft(values, secretFields = []) {
  return Object.fromEntries(
    Object.entries(values ?? {}).filter(
      ([name, value]) =>
        !secretFields.includes(name) &&
        !SECRET_FIELD.test(name) &&
        !(typeof File !== "undefined" && value instanceof File)
    )
  );
}

/**
 * Borrador local de un formulario (riesgo D, ADR-0011).
 *
 * Guarda los valores en `localStorage` con clave por formulario Y por cuenta
 * (`siga:draft:<cuenta>:<formulario>`), para que otra persona en la misma
 * computadora no vea el borrador ajeno. Ofrece recuperarlo al abrir, y se borra
 * al guardar con exito o al cancelar confirmando que se descartan los cambios.
 * Todo acceso al almacenamiento va en try/catch.
 *
 * Es opcional: `EntityFormWindow` lo activa con `draftKey`; sin esa prop las
 * pantallas no cambian.
 *
 * @param {string|null} formKey  Identificador estable del formulario; `null` desactiva.
 * @param {object} values        Valores actuales.
 * @param {{enabled?: boolean, secretFields?: string[]}} [options]
 */
export function useFormDraft(
  formKey,
  values,
  { enabled = true, secretFields = [] } = {}
) {
  const userId = useContext(AuthContext)?.user?.public_id ?? "anonimo";
  const key =
    formKey && enabled ? `${DRAFT_PREFIX}:${userId}:${formKey}` : null;
  const [saved] = useState(() => (key ? read(key) : null));
  const [offer, setOffer] = useState(Boolean(saved));
  const secretsKey = secretFields.join("|");

  const sanitized = useMemo(
    () => sanitizeDraft(values, secretsKey ? secretsKey.split("|") : []),
    [values, secretsKey]
  );

  useEffect(() => {
    // Mientras se ofrece el borrador anterior no se pisa con el formulario vacio.
    if (!key || offer) return;
    write(key, { savedAt: new Date().toISOString(), values: sanitized });
  }, [key, offer, sanitized]);

  const clear = useCallback(() => {
    if (key) remove(key);
    setOffer(false);
  }, [key]);

  const dismiss = useCallback(() => {
    clear();
  }, [clear]);

  const accept = useCallback(() => {
    setOffer(false);
    return saved?.values ?? null;
  }, [saved]);

  return {
    /** Borrador encontrado al abrir, si la persona todavia no decidio. */
    pending: offer ? saved : null,
    accept,
    dismiss,
    clear,
  };
}
