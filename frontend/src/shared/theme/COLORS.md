# Sistema de color de SIGA-INEBI

Implementa la seccion 4 de la guia de diseno de Vantum ST
(`vantum/design-guidelines/DESIGN.md`).

## Regla unica

**Ningun archivo fuera de `src/shared/theme/` puede contener un literal de color.**
Ni `#rrggbb`, ni `rgb()`, ni `rgba()`, ni `"white"`. Si necesitas un color:

1. Si ya existe un slot semantico, usalo: `color="error"`, `sx={{ color: "text.secondary" }}`.
2. Si es un estado de dominio, usa `<StatusChip variant="...">` con un mapa en
   `shared/constants/chipMaps.js`.
3. Si necesitas un tono suave, usa `softTone(theme, "success")`.
4. Solo si nada de lo anterior aplica: agrega el hex a `palette/raw.js` con
   nombre, mapealo a un slot en `palette/light.js` y `palette/dark.js`, y
   consumelo por token.

## Como cambiar la marca

Editar una constante en `palette/brand.js`:

```js
export const ACTIVE_BRAND = "vantum"; // -> "inebi"
```

| Marca    | `primary.main` claro | `primary.main` oscuro | Acento  |
| -------- | -------------------- | --------------------- | ------- |
| `vantum` | `#1A73E8`            | `#8AB4F8`             | `#B4894A` |
| `inebi`  | `#1C2B3A`            | `#9FB6CC`             | `#B4894A` |

Eso repinta botones, enlaces, anillo de foco, estados seleccionados, la barra
superior de `SectionCard` y el chip `primary`, en ambos modos, sin tocar ningun
componente. Agregar una marca nueva es agregar una entrada a `BRAND_RAMPS`.

## Slots resueltos

| Slot                 | Claro     | Oscuro    |
| -------------------- | --------- | --------- |
| `secondary.main`     | `#34A853` | `#81C995` |
| `success.main`       | `#34A853` | `#81C995` |
| `error.main`         | `#C5221F` | `#F28B82` |
| `warning.main`       | `#B06000` | `#FFB74D` |
| `background.default` | `#F4F6FB` | `#1A1B1E` |
| `background.paper`   | `#FFFFFF` | `#242628` |
| `divider`            | `#E8EAED` | `#3C4043` |
| `text.primary`       | `#1C2B3A` | `#E3E4E8` |
| `text.secondary`     | `#5F6368` | `#9AA0A6` |

Los slots semanticos declaran **solo `main`**: MUI deriva `light` y `dark`.

## Variantes de chip

`primary`, `success`, `warning`, `danger`, `purple`, `neutral`, `accent`.

El dominio nunca conoce colores, solo nombres de variante. La traduccion
`estado de dominio -> variante` vive en `shared/constants/chipMaps.js`.
