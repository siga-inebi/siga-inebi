# Frontend de SIGA-INEBI

React 19 + Vite + JavaScript, con Material UI 7 sobre un tema propio.

## Como esta organizado

Primero el dominio, despues el tipo de archivo. Nunca al reves.

```
src/
  app/          App.jsx · main.jsx · routes.jsx · navigation.js
  shared/       theme · ui · layout · crud · api · utils · constants · assets
  <dominio>/    pagina(s) · servicio · hooks propios
```

Los dominios espejan las apps de Django del backend, asi que una funcionalidad
se busca en el mismo nombre a los dos lados: `auth`, `dashboard`, `people`,
`students`, `teachers`, `guardians`, `academics`, `cycles`, `enrolments`,
`attendance`, `evaluation`, `documents`, `reporting`.

Cada dominio es autonomo. Dos personas trabajando en modulos distintos no tocan
las mismas carpetas, que es de donde salian los conflictos de merge.

**Que entra en `shared/`:** solo lo que (1) no pertenece al negocio de un
dominio, (2) ya lo usan varios, y (3) tiene sentido fuera del contexto de una
pantalla. Algo que solo usa un modulo se queda en ese modulo, aunque "podria"
reutilizarse algun dia.

`app/` es la raiz de composicion y el unico lugar autorizado a conocer todos los
dominios a la vez.

## Alias de import

Definidos en `vite.config.js`. Un import se lee como una direccion del sistema y
no como una ruta relativa que cambia cada vez que un archivo se mueve:

```js
import { DataTable } from "@ui/table/DataTable.jsx";
import { studentsService } from "@students/studentsService.js";
```

`@app @shared @ui @layout @theme` mas uno por dominio.

## Registro de navegacion

`app/navigation.js` es la unica fuente de verdad de tres cosas: los items del
menu lateral, las rutas perezosas y los accesos rapidos del panel. Agregar un
modulo es agregar una entrada ahi.

Su campo `load` es la misma funcion de `import()` que consume `React.lazy` en
`routes.jsx`, asi que el prefetch al pasar el mouse por un item del menu calienta
exactamente el chunk que la ruta va a pedir. Cada pantalla viaja en su propio
chunk (2-10 kB); MUI va en un chunk de vendor que sobrevive a los despliegues.

## Tema y estilos

Todo el estilo vive en `shared/theme/` y en objetos `sx`. Hay un solo CSS global
(`app/App.css`) con la caja raiz del documento y nada mas.

- Como cambiar colores, forma o tipografia: `shared/theme/COLORS.md`.
- De donde viene el sistema y en que diverge a proposito:
  `shared/theme/PROVENANCE.md`.

Dos reglas que ESLint o el modo oscuro rompen si se ignoran:

1. **Ningun literal de color fuera de `shared/theme/`.** Es un `error` de lint.
2. **Nunca `theme.palette` a secas dentro de `sx`.** Con variables CSS activas
   devuelve el esquema por defecto y congela el color claro en modo oscuro. Se
   usa una ruta en texto (`sx={{ color: "text.secondary" }}`) o el helper
   `palette(theme)` de `shared/theme/tokens/color.js`.

## Piezas reutilizables

`shared/ui/` — `SectionCard`, `PageHeader`, `DataTable`, `StatusChip`,
`StatCard`, `QuickActionCard`, `EmptyState`, `FloatingWindow`, `DetailWindow`,
`ConfirmDialog`, `SearchField`, `FilterBar`, `FilterSelect`, `FormTextField`,
`FormSelect`, `ActionIconButton`, `ConfirmActionButton`, `ViewDetailButton`.

`shared/crud/` — el kit de listado y CRUD que usan todas las pantallas:

| Pieza                | Para que                                                       |
| -------------------- | -------------------------------------------------------------- |
| `usePaginatedList`   | Listados que el backend pagina (`{count, results}`).           |
| `useLocalList`       | Listados que llegan completos y se filtran en memoria.         |
| `ListSection`        | Card + filtros + errores + tabla paginada.                     |
| `EntityFormWindow`   | Formulario en ventana modal, descrito por campos declarativos.  |

Un formulario se declara, no se escribe a mano:

```jsx
const FIELDS = [
  { name: "name", label: "Nombre", required: true },
  { name: "kind", label: "Tipo", type: "select", options: KIND_OPTIONS },
  { name: "photo", label: "Foto (opcional)", type: "file", accept: "image/*" },
];
```

Tipos soportados: texto, `number`, `email`, `tel`, `date`, `select`, `checkbox`
y `file` con vista previa. `span: "full"` fuerza el ancho completo de la reja.

## Comandos

```bash
npm run dev            # servidor de desarrollo (o docker compose up)
npm run lint           # ESLint, sin advertencias toleradas en CI
npm run test           # Vitest + Testing Library
npm run test:coverage  # con umbrales de cobertura
npm run build          # build de produccion con chunks separados
```

En Docker: `docker compose exec frontend npm run <script>`.

## Convenciones de UI

- **Interfaz en espanol**, sin datos reales.
- Overlay unico: **ventana modal centrada** (`FloatingWindow`), no panel lateral.
- Un solo scroll por pantalla: `fillHeight` reparte el alto hasta la tabla.
- El error de un envio **no cierra** la ventana: se pierde lo escrito.
- Toda accion destructiva pasa por `ConfirmActionButton`.
- Todo `IconButton` sin texto lleva `aria-label` o `Tooltip`.
- Un boton que no hace nada no se dibuja: si el backend no expone el contrato,
  el control no existe todavia (ver el comentario de "mantener sesion iniciada"
  en `auth/LoginPage.jsx`).

## Estado de los datos

`students`, `teachers` y `guardians` consumen endpoints reales pero traen el
listado completo y paginan en el cliente (ver el TODO en `studentsService.js`).
Cuando el backend exponga paginacion para esos recursos, esas pantallas pasan de
`useLocalList` a `usePaginatedList`.

Algunos endpoints (`jornada-parameters`, `reporting/*`) exigen permisos atomicos
que la cuenta demo no tiene: responden 403 y la pantalla muestra el error en vez
de una tabla vacia. Es comportamiento correcto del backend, no un fallo de UI.
