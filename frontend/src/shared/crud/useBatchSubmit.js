import { useCallback, useState } from "react";

/**
 * Alta de varios registros, uno por peticion, con resumen de lo que fallo.
 *
 * El backend no publica endpoints de lote, asi que las pantallas de carga
 * masiva (matriculacion por lotes, asignacion docente por lotes, clonado de
 * asignaciones) mandan una peticion por item. Las tres implementaban el mismo
 * bucle a mano: acumular creados, acumular fallidos, y armar el mismo Alert.
 *
 * Dos decisiones que no son obvias y por eso viven aca una sola vez:
 *
 * - **Que una falle no cancela las demas.** Cortar en el primer error dejaria
 *   la mitad del lote cargada sin decir cual mitad, y quien captura tendria que
 *   adivinar por donde retomar. Se intentan todas y el resumen dice exactamente
 *   cuales quedaron pendientes y por que.
 * - **Secuencial y no en paralelo.** Un `Promise.all` sobre sesenta altas
 *   dispara sesenta peticiones simultaneas contra reglas que compiten por el
 *   mismo cupo de seccion; en serie, el guard de cupo del backend ve un estado
 *   consistente y el rechazo cae en el item que sobra, no en uno al azar.
 *
 * @param {(item: any) => Promise<any>} createOne
 *   Da de alta UN item. Recibe el item tal cual entro en `run`.
 * @param {(item: any) => string} describe
 *   Etiqueta legible del item, para el resumen de fallos. Sin esto el resumen
 *   diria "no se pudo crear <uuid>", que no le sirve a nadie.
 */
export function useBatchSubmit(createOne, describe) {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const run = useCallback(
    async (items) => {
      setSubmitting(true);
      setResult(null);

      const created = [];
      const failed = [];

      for (const item of items) {
        try {
          await createOne(item);
          created.push(item);
        } catch (error) {
          failed.push({ label: describe(item), message: error.message });
        }
      }

      setSubmitting(false);
      const summary = { created, failed };
      setResult(summary);
      // Se devuelve ademas de guardarse en el estado: quien llama necesita saber
      // que se creo para refrescar su tabla sin esperar un render.
      return summary;
    },
    [createOne, describe]
  );

  const reset = useCallback(() => setResult(null), []);

  return { run, reset, submitting, result };
}
