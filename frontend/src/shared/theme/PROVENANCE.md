# Procedencia del tema

## Que se tomo prestado y que no

De `vantum/design-guidelines/DESIGN.md` (guia de Vantum ST, extraida del CRM Las
Americas) se adopta la **arquitectura**, no la apariencia:

- Tema unico con `createTheme()`, `cssVariables` y `colorSchemes` light/dark.
- Cuatro capas de color: `raw` -> `palette` -> `tokens` -> componentes, con los
  literales confinados a un archivo y la regla aplicada por ESLint.
- Tokens nombrados por rol (`radii`, `shadows`, `fonts`) en vez de valores
  sueltos en los call sites.
- Patron `fillHeight` ("un solo scroll por pantalla") y la cadena flex que lo
  sostiene.
- Contratos de `DataTable`, `StatusChip`, `EmptyState`, wording de estados vacios
  y reglas de formulario (booleano calculado en render, error solo tras
  interaccion, remontaje por `key` al abrir).
- Container/presentational por seccion y arquitectura de carpetas por dominio.

Eso es ingenieria reutilizable. La **identidad visual es propia de SIGA-INEBI** y
divergE a proposito en todo lo que hace reconocible a un producto:

| Decision               | Guia Vantum / CRM                      | SIGA-INEBI                                           |
| ---------------------- | -------------------------------------- | ---------------------------------------------------- |
| Primario               | Azul `#1A73E8` (Google Blue)           | Navy `#1C2B3A` en claro, dorado `#D9BA85` en oscuro  |
| Neutrales              | Gris azulado (`#F4F6FB`)               | Hueso calido (`#FAF8F4`) y carbon calido (`#191714`) |
| Tipografia             | DM Sans, una familia                   | Source Serif 4 en titulos + Public Sans en interfaz  |
| Forma                  | Botones pill `2rem`, cards 12px        | Rectangulos: boton 6px, card 8px, chip 4px           |
| Elevacion              | "Flat 2.0": sombra + anillo en todo    | Sin sombra en lo asentado; solo en lo flotante       |
| Firma de `SectionCard` | Regla superior 2.5px en primario       | Marcador dorado 3px a la izquierda del titulo        |
| Cabecera de tabla      | Banda de fondo gris                    | Sin relleno; regla inferior 2px en color de marca    |
| Overlay por defecto    | Panel lateral (drawer) redimensionable | Ventana modal centrada (`FloatingWindow`)            |

Razon de la divergencia: SIGA-INEBI no es un producto de Vantum ST y no debe
leerse como uno. Copiar la paleta y la firma visual de otro producto es lo que
hace que dos sistemas distintos se confundan; copiar su arquitectura de tokens es
lo que hace que el segundo se construya mas rapido.

## Desviaciones tecnicas respecto de la guia

| Desviacion                      | Razon                                                                                                                                                                  |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| JavaScript en vez de TypeScript | El proyecto es JS. Migrar a TS es un cambio ortogonal y mucho mayor; no entra en una PR de UI. Por eso no existe `augmentation.d.ts`.                                  |
| `palette/brand.js`              | Requisito del equipo: cambiar el look editando variables. La rampa de marca queda aislada en una constante.                                                            |
| `tokens/color.js`               | La guia menciona `(theme.vars \|\| theme).palette` solo para `styleOverrides`. Aqui es regla general y con helper propio, porque el bug aparecio en un `sx` de pagina. |
| Variante de chip `accent`       | Reemplaza a `primariaSoft`, que es una excepcion de dominio del CRM inexistente aqui.                                                                                  |
| Sin `@tanstack/react-virtual`   | La virtualizacion sobre 50 filas todavia no aplica: los listados actuales manejan volumenes chicos. Se agrega cuando un listado real lo pida.                          |
| Sin SWR ni axios                | El proyecto ya tiene un `apiClient` propio sobre `fetch` con CSRF y sesion por cookie. Cambiar la capa de datos no es parte de un refactor de UI.                      |

## Bug encontrado al implementar (documentado para no repetirlo)

Con `cssVariables` activo, leer `theme.palette.X` dentro de un `sx` congela el
color del esquema por defecto. Se detecto porque el item activo del menu lateral
salia en modo oscuro con fondo hueso y texto casi invisible. La correccion es
`tokens/color.js` y la regla esta en `COLORS.md`.
