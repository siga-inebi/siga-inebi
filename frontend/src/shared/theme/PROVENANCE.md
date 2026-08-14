# Procedencia del tema

Este tema implementa **`vantum/design-guidelines/DESIGN.md` v1.0.0** (guia de
diseno UI de Vantum ST, extraida del frontend en produccion del CRM Las
Americas). El sistema de referencia en codigo es
`Soporte_vantum/app/frontend/src/theme/`.

## Conformidad

Se implementa tal cual:

- Arquitectura de 4 capas del tema (seccion 4.1) y estructura de archivos.
- Paleta cruda exacta (seccion 4.2) y slots resueltos (seccion 4.3).
- Dark mode con `cssVariables.colorSchemeSelector: "class"`, `colorSchemes`,
  persistencia en `localStorage["mui-mode"]` y script anti-flash (seccion 4.4).
- Tipografia DM Sans, escala en `rem`, pesos y `textTransform: none` (seccion 4.5).
- Radios (seccion 4.6), sombras "Flat 2.0" con anillo hairline (seccion 4.7),
  espaciado base 8px (seccion 4.8).
- `softTone()` y `selectedToneSx()` (seccion 4.9).
- Variantes semanticas de chip (seccion 9).
- Regla ESLint que prohibe literales de color fuera del tema (seccion 4.1),
  aplicada como `error` en `eslint.config.js`.

## Desviaciones deliberadas

| Desviacion                                                | Razon                                                                                                                                                             |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| JavaScript en vez de TypeScript                            | El proyecto es JS. Migrar a TS es un cambio ortogonal y mucho mayor; no entra en una PR de UI. Por eso no existe `augmentation.d.ts`: `theme.tokens` no necesita declararse. |
| `palette/brand.js` (constante `ACTIVE_BRAND`)              | Requisito explicito del equipo: poder cambiar el look tocando variables. La guia fija el azul Vantum; SIGA-INEBI tiene marca propia (navy + dorado). Aislar la rampa permite probar ambas sin tocar componentes. |
| Variante de chip `accent` (dorado) en vez de `primariaSoft` | `primariaSoft` es una excepcion de dominio del CRM que aqui no existe. El dorado si aplica: es el acento de marca del establecimiento.                              |
| Sin `@tanstack/react-virtual`                              | La virtualizacion sobre 50 filas todavia no aplica: los listados actuales paginan del lado del cliente con volumenes chicos. Cuando un listado real pase de 50 filas visibles, se agrega segun la seccion 7. |
| Sin SWR ni axios                                           | El proyecto ya tiene un `apiClient` propio sobre `fetch` con manejo de CSRF y sesion por cookie. Cambiar la capa de datos no es parte de un refactor de UI.        |

## Deudas de la guia que este proyecto NO hereda

Los seis puntos de la seccion 13 ("deudas del proyecto origen") se respetan
desde el dia uno: familia tipografica unica, sin repetir defaults del tema en
`sx`, formateadores sin duplicar, sin shims de compatibilidad.
