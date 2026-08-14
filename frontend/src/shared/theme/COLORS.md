# Sistema de color y forma de SIGA-INEBI

## Regla unica

**Ningun archivo fuera de `src/shared/theme/` puede contener un literal de color.**
Ni `#rrggbb`, ni `rgb()`, ni `rgba()`, ni `"white"`. La regla la aplica ESLint
como error. Si necesitas un color:

1. Si ya existe un slot semantico, usalo: `color="error"`, `sx={{ color: "text.secondary" }}`.
2. Si es un estado de dominio, usa `<StatusChip variant="...">` con un mapa en
   `shared/constants/chipMaps.js`.
3. Si necesitas un tono suave, usa `softTone(theme, "success")`.
4. Solo si nada de lo anterior aplica: agrega el hex a `palette/raw.js` con
   nombre, mapealo a un slot en `palette/light.js` y `palette/dark.js`, y
   consumelo por token.

## Regla dos: nunca `theme.palette` a secas dentro de `sx`

Con `cssVariables` activo, `theme.palette.X` devuelve el valor del esquema **por
defecto**, no del activo, y Emotion lo hornea en la clase CSS. Un `sx` que lee
`theme.palette.surfaces.sunken` pinta el color claro tambien en modo oscuro.

```js
// MAL: se congela en claro
sx={(theme) => ({ bgcolor: theme.palette.surfaces.sunken })}

// BIEN: ruta en texto, MUI la resuelve por variable
sx={{ bgcolor: "background.paper" }}

// BIEN: helper que lee theme.vars
import { palette } from "@theme/tokens/color.js";
sx={(theme) => ({ bgcolor: palette(theme).surfaces.sunken })}

// BIEN: color con transparencia (alpha() no sirve sobre var(--...))
import { toneAlpha } from "@theme/tokens/color.js";
sx={(theme) => ({ bgcolor: toneAlpha(theme, "primary", 0.12) })}
```

## Identidad

Navy y dorado del establecimiento sobre neutrales **calidos**. El primario
cambia de portador entre modos a proposito: navy sobre hueso en claro, dorado
sobre carbon en oscuro (ver `palette/brand.js` para el razonamiento).

| Slot                 | Claro                | Oscuro               |
| -------------------- | -------------------- | -------------------- |
| `primary.main`       | `#1C2B3A` navy       | `#D9BA85` dorado     |
| `secondary.main`     | `#B4894A` dorado     | `#D9BA85`            |
| `success.main`       | `#1F7A4C`            | `#7FC79E`            |
| `error.main`         | `#B3261E`            | `#F0B0AB`            |
| `warning.main`       | `#9A6700`            | `#E8B14C`            |
| `background.default` | `#FAF8F4` hueso      | `#191714` carbon     |
| `background.paper`   | `#FFFFFF`            | `#221F1B`            |
| `divider`            | `#E6E1D6`            | `#3B362F`            |
| `text.primary`       | `#1C2B3A`            | `#EFEAE1`            |
| `text.secondary`     | `#57514A`            | `#ABA398`            |

Cambiar la identidad completa es una constante: `ACTIVE_BRAND` en
`palette/brand.js`. Agregar una identidad nueva es agregar una entrada a
`BRAND_RAMPS`.

## Lenguaje visual

Tres decisiones que definen el sistema, todas expresadas en tokens:

1. **Angulos casi rectos** (`tokens/radii.js`): boton e input 6px, chip 4px,
   card 8px, ventana 10px. Sin capsulas.
2. **Lo asentado no tiene sombra** (`tokens/shadows.js`): cards y secciones se
   separan con borde hairline y espacio. La sombra queda solo para lo que flota
   de verdad: ventanas modales, menus y popovers.
3. **Dos familias con roles fijos** (`tokens/typography.js`): Source Serif 4 en
   titulos, Public Sans en interfaz, IBM Plex Mono en codigos. Ningun componente
   declara `fontFamily` propio: pide `theme.tokens.fonts.display` o hereda.

**Firma visual:** marcador dorado de 3px a la **izquierda** del titulo de
seccion (`SectionCard`), del acceso rapido (`QuickActionCard`) y del item activo
del menu lateral. El acento va donde esta la informacion, no en el marco.

## Overlays

El overlay del sistema es **ventana modal centrada** (`FloatingWindow`), no panel
lateral: formularios de alta y edicion, detalle de entidad y confirmaciones.
Anatomia fija: cabecera, cuerpo con scroll propio, pie con acciones a la derecha
(orden `Cancelar` -> accion).

## Variantes de chip

`primary`, `success`, `warning`, `danger`, `purple`, `neutral`, `accent`.

El dominio nunca conoce colores, solo nombres de variante. La traduccion
`estado de dominio -> variante` vive en `shared/constants/chipMaps.js`.
