# Generacion de tickets desde el catalogo de requerimientos

Convierte cada requerimiento del catalogo institucional en un issue de GitHub y
devuelve los numeros de issue a la documentacion de trazabilidad.

## Por que existe

`docs/requirements/requirements-catalogue.md` declara 230 requerimientos (195 RF
y 35 RNF) con su columna `Issue relacionado` en `TBD`, y
`docs/requirements/traceability-matrix.md` tiene la columna `Issue` en `TBD`. El
criterio de aceptacion de cada requerimiento solo existe en la matriz de
trazabilidad de `INEBI Fase 2.pdf` (paginas 80-188), fuera de control de
versiones y fuera de cualquier tablero.

`AGENTS.md` regla 10 y `docs/requirements/change-control.md` exigen la relacion
`Requerimiento -> Issue`. Estos scripts la construyen de forma reproducible.

## Autoridad de los datos

Las fuentes se contradicen en algunos puntos, asi que cada campo tiene un dueno
unico y explicito:

| Campo | Fuente autoritativa | Motivo |
| --- | --- | --- |
| Conjunto de IDs validos | catalogo | El PDF asigna un mismo ID a dos requerimientos distintos en 6 casos. |
| Prioridad MoSCoW | catalogo | Dos fichas del PDF tienen la linea `Prioridad` corrupta. |
| Dominio | catalogo | El PDF no lo declara. |
| Criterio de aceptacion, actor, historia de usuario, regla de negocio, modulo | ficha del PDF | No existen en el catalogo. |
| Nombre | ficha del PDF, con el catalogo como respaldo | La ficha conserva los acentos. |
| Comportamiento exigido y escenarios verificables | `docs/requirements/openspec/` | Es la unica fuente con GIVEN/WHEN/THEN. |
| Donde se implementa | `docs/architecture/domain-map.md` y el arbol real del repo | Derivado, no declarado en ningun requerimiento. |

Cuando un ID tiene dos fichas, gana la ficha cuyo nombre coincide con la
descripcion del catalogo; si ninguna coincide, gana la ultima en orden de
documento y el reporte lo marca para revision humana.

## Que lleva cada ticket

Ademas del criterio de aceptacion, cada issue responde **que hay que programar**:

- **Comportamiento exigido y escenarios verificables.** Las specs de capacidad en
  `docs/requirements/openspec/` traen 104 requerimientos con 139 escenarios
  GIVEN/WHEN/THEN. El nombre del archivo mapea a un prefijo RF
  (`identidad-cuentas` = `CTA`, `asistencia-escaneo` = `ASI`, ...) y cada titulo
  `### Requirement:` coincide **exacto** con una descripcion del catalogo: las 104
  resuelven a un unico ID, sin heuristica.
  Los 10 prefijos sin spec (`EST`, `AUL`, `HOR`, `EXP`, `MAT`, `MOV`, `DOC`,
  `ARC`, `PLA`, `EMI`) y los 35 RNF no reciben escenarios inventados: su seccion
  dice explicitamente que hay que derivarlos y escribirlos antes de programar.
- **Capas y rutas concretas.** `models.py`, `services.py`, `api/`, migracion, y si
  la app del dominio todavia no existe, el ticket lo dice y quien lo tome la crea.
- **Archivos de prueba y un caso por escenario.** Deja de decir `TBD`: nombra
  `backend/tests/unit/test_<app>_services.py`, `.../api/test_<app>_api.py`, y el
  test de permisos cuando el dominio es sensible.
- **Documentos de diseno a leer antes de escribir codigo**, por dominio.

Un requerimiento con spec de capacidad **no** lleva `status:blocked` aunque el PDF
no traiga ficha: la spec es un enunciado valido de comportamiento esperable. Solo
quedan bloqueados los que no tienen ni criterio ni spec.

## Uso

**El paso 1 solo hace falta si cambia el PDF.** `docs/requirements/requirements.json`
esta versionado, asi que desde un clon limpio se arranca en el paso 2.

```sh
# 1. (opcional) Re-extraer las fichas del PDF y cruzarlas contra el catalogo.
#    Requiere el PDF en la raiz; no esta en el repositorio.
python3 scripts/requirements/extract-requirements.py

# 2. Renderizar el cuerpo de cada issue
python3 scripts/requirements/render-tickets.py

# 3. Revisar el plan sin tocar GitHub
sh scripts/requirements/create-issues.sh

# 4. Crear los issues
APPLY=true sh scripts/requirements/create-issues.sh

# 5. Devolver los numeros de issue a la documentacion
APPLY=true python3 scripts/requirements/backfill-traceability.py
```

Para refrescar issues que ya existen tras cambiar una spec o el catalogo:

```sh
APPLY=true sh scripts/requirements/update-issues.sh
```

Para ensayar contra un repositorio desechable antes de tocar el real:

```sh
GITHUB_ORG=<usuario> GITHUB_REPO=<sandbox> APPLY=true \
  sh scripts/github/configure-labels.sh
GITHUB_ORG=<usuario> GITHUB_REPO=<sandbox> GH_ACCOUNT=<usuario> APPLY=true \
  sh scripts/requirements/create-issues.sh
```

## Fijar la cuenta con GH_ACCOUNT

**Usar siempre `GH_ACCOUNT` en corridas largas.** `gh` resuelve la credencial
desde la cuenta *activa* en cada llamada, y una corrida completa son cientos de
llamadas durante 10 a 15 minutos. Un `gh auth switch` en otra terminal a mitad de
camino hace que el resto falle con un error de permisos, y una cuenta no puede
escribir en un repositorio de otra por mas que sea publico: la escritura depende
del dueno, no de la visibilidad.

`GH_ACCOUNT=<cuenta>` resuelve el token una vez y lo exporta como `GH_TOKEN`, que
tiene precedencia sobre la cuenta activa durante toda la corrida.

Ademas, con `APPLY=true` los scripts verifican permiso de escritura **antes** de
la primera llamada y abortan con codigo 1 sin escribir nada si la cuenta activa
solo tiene lectura.

## Entradas

- `INEBI Fase 2.pdf` en la raiz del repositorio, **solo para re-extraer**. No esta versionado: son 21 MB de binario que git no puede diferenciar.
- `docs/requirements/requirements-catalogue.md`.
- `docs/requirements/traceability-matrix.md`.
- `pdftotext` (paquete `poppler-utils`) y `gh` autenticado con scope `repo`.

## Salidas

Versionado:

| Archivo | Contenido |
| --- | --- |
| `docs/requirements/requirements.json` | 230 registros normalizados, uno por requerimiento del catalogo. Es la entrada real del renderizador. |
| `docs/requirements/openspec/*.md` | 13 especificaciones de capacidad: 104 requerimientos con 139 escenarios. |

Efimero, bajo `scripts/requirements/out/`, ignorado por git:

| Archivo | Contenido |
| --- | --- |
| `extraction-report.md` | Requerimientos sin ficha, IDs colisionados y fichas descartadas. **Leerlo antes de crear issues.** |
| `tickets/<ID>.md` | Cuerpo de cada issue. |
| `epics/<clave>.md` | Cuerpo de cada epica. |
| `tickets.tsv`, `epics.tsv` | Indice de creacion: id, titulo, etiquetas, ruta del cuerpo. |
| `created.tsv` | `id`, numero de issue, URL. Se escribe tras cada creacion. |

## Riesgos

- **Volumen.** Una corrida crea 237 issues y por lo tanto 237 notificaciones a
  cada watcher del repositorio. Avisar al equipo antes.
- **Limite de tasa secundario de GitHub.** Hay una espera de `THROTTLE`
  segundos (2 por omision) entre escrituras. Una corrida completa toma entre 10 y
  15 minutos. Bajar el valor puede provocar rechazos.
- **Duplicados.** `create-issues.sh` salta todo id que ya figure en
  `created.tsv`. Borrar ese archivo y volver a correr **crea todo de nuevo**.
- **Requerimientos sin criterio.** 5 requerimientos del catalogo no tienen ficha
  en el PDF; 3 de ellos si tienen spec de capacidad, asi que solo 2 quedan
  `status:blocked` con una nota explicita. No se inventa un criterio para nadie.
- **Estado de implementacion desactualizado.** El catalogo marca los 230 como
  `Not implemented`, pero `develop` ya integro parte del alcance. Los issues
  correspondientes se crean igual y hay que cerrarlos a mano.
- Los scripts que escriben en GitHub son dry-run por omision y exigen
  `APPLY=true`, igual que `scripts/github/`.

## Pruebas

```sh
cd scripts/requirements && python3 -m unittest discover -s . -p 'test_*.py'
```

Solo biblioteca estandar: no requiere el virtualenv del backend.
