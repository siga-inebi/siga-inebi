import { lazy } from "react";

/**
 * Ventanas de las acciones de cuenta que solo se abren con un clic. Se
 * descargan al abrirlas para que el listado y la ficha de cuentas no paguen su
 * peso en la carga inicial (riesgo C, ADR-0011).
 */
export const LazyEntityFormWindow = lazy(() =>
  import("@shared/crud/EntityFormWindow.jsx").then((module) => ({
    default: module.EntityFormWindow,
  }))
);

export const LazySecretHandoverDialog = lazy(() =>
  import("./SecretHandoverDialog.jsx").then((module) => ({
    default: module.SecretHandoverDialog,
  }))
);
