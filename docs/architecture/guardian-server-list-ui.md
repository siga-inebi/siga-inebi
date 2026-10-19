# Listado paginado de encargados — G2, #632

## Alcance y base

`GuardiansPage` sustituye la descarga inicial del padrón por `useServerList` y
`ExportCsvButton` de #630/#651. La rama parte de `develop` y es independiente de
los PR #652–#655. Incluye los mismos ajustes mínimos compartidos de #653:
buscador síncrono con `debounceMs=0`, máximo de página 100 y exportación desactivable.
No incorpora los cambios propios de Estudiantes o Docentes.

G1 y sus formularios institucionales se conservan. G3 (desactivación) y G4
(estudiantes vinculados en el detalle) quedan pendientes. No hay cambios de dominio,
escrituras, permisos, migraciones ni variables de entorno.

## Contratos y navegación

La pantalla `/app/padres-de-familia` utiliza el contrato existente
`GET /api/v1/students/guardians/`: `{count, next, previous, results}`.

| Parámetro | Comportamiento |
| --- | --- |
| `page` | Base uno, inicial 1 |
| `page_size` | Inicial 25; selector 10/25/50/100; máximo 100 |
| `search` | Búsqueda en el servidor tras 300 ms sin nuevas teclas |
| `include_inactive` | Omitido por defecto; `true` al mostrar desactivados |

Página, tamaño, búsqueda y actividad se conservan en URL. Allí la actividad se
representa con `include_inactive=1`. Cambiar búsqueda, actividad o tamaño vuelve
a página uno; «Limpiar» conserva el tamaño. No se filtra ni pagina de nuevo en el
cliente. Se mantiene el orden de la API: apellido, nombre e identificador.

La API ya busca por nombre y CUI desde #635. La pantalla anuncia nombre y no añade
CUI ni fecha de nacimiento a la tabla, detalle o CSV. Se conserva el identificador
entero del encargado y el UUID de su persona. `guardiansService.list()` sigue
disponible para consumidores existentes; esta pantalla usa `listPage()`.

La columna «Actividad» y el detalle distinguen Activo/Desactivado usando `is_active`.
El detalle existente conserva la URL. Alta y edición vuelven a consultar la página
vigente: no insertan filas locales que puedan incumplir el filtro. Si una edición
vacía la última página y la API devuelve 404, se muestra el error con «Reintentar
listado» y «Volver a primera página», conservando búsqueda, actividad y tamaño.
Los errores no se presentan como listas vacías.

## Exportación y límites

«Exportar CSV» solicita todas las páginas filtradas de 100 filas desde la primera,
solo al pulsarlo, con progreso y cancelación del componente compartido. Exporta
`padres-de-familia.csv` con Nombre, Correo, Teléfono y la nueva columna Actividad.
No queda limitado a la página visible ni a 1.000 filas. Conserva búsqueda/actividad,
omitiendo página y tamaño visibles. Se desactiva durante la espera de búsqueda,
carga o error para evitar exportar filtros anteriores.

Usa el escape CSV compartido. El archivo se prepara en memoria y no representa una
instantánea transaccional ante cambios concurrentes. Cancelar detiene el recorrido
entre páginas; no garantiza abortar la petición en curso. La tabla conserva su
desplazamiento horizontal en móvil.

## Autorización y trazabilidad

Se conserva la autenticación existente de encargados. La brecha de permisos atómicos
para lectura/escritura/exportación está registrada en #643 y en
[permisos-en-ui.md](../development/permisos-en-ui.md); esta entrega no la resuelve.
No se concede ningún permiso nuevo ni se utiliza el permiso de desactivación docente.

Se traza el hallazgo G2 y la adopción de 1.1, sin inventar un RF de paginación de
encargados ni marcar RF/RNF como completados. RF-EXP-004 corresponde a vínculos de
estudiantes y no se implementa aquí. Revisados AGENTS, ADR-0004/0005/0006/0008,
el contrato de listados de comunidad y la guía de permisos; sin nueva decisión.

## Evidencia y reversión

- `backend/tests/api/test_guardian_server_list_ui_contract.py`: padrón sintético de
  1.001 activos, filtro antes de paginar, máximo 100, última página, actividad
  optativa, omisión de datos sensibles y recuperación de página tras editar.
- `backend/tests/api/test_community_list_filters_api.py`: búsqueda, validación,
  actividad, orden estable, sesión y alcance estudiantil conservado.
- `frontend/src/test/GuardiansPage.test.jsx`: URL, tamaño, búsqueda sin perder
  letras, filtros, limpieza, errores/reintentos, página inexistente, CSV de 1.001
  filas/11 páginas y actualización desde servidor tras alta/edición fuera del filtro.
- `frontend/src/test/useServerList.test.jsx`: límite 100 frente a URL manual.

Frontend completo: 534 pruebas aprobadas en 67 archivos; cobertura de líneas
88,21 %. PostgreSQL local: 43 pruebas API aprobadas. Herramientas: 69 pruebas; políticas de
GitHub: 7. ESLint, Ruff y build con presupuesto aprobados. Node local 24, Vitest
3.2.7, Python 3.11 y PostgreSQL 18; CI valida las versiones fijadas por el repo.
No se ejecutó Docker localmente.

Comandos reproducibles desde `frontend/`: `npm run test:coverage -- --maxWorkers=1
--no-file-parallelism`, `npm run lint`, `npm run build` y `npx prettier --check`
sobre los archivos modificados. Desde `backend/`, con PostgreSQL de pruebas:
`python -m pytest tests/api/test_guardian_server_list_ui_contract.py
tests/api/test_community_list_filters_api.py --no-cov --reuse-db -q`.
Ruff verifica el nuevo archivo API. Las pruebas de herramientas y políticas se
ejecutan desde la raíz siguiendo los comandos del workflow de CI.

Build aprobado: 227.415/230.000 bytes gzip iniciales, ruta máxima
19.305/20.000 y página fría máxima 246.720/250.000.

Chrome real en escritorio 1440×1000 y móvil 390×844: una página al abrir (además del
contador lateral), página 41 con registro 1.001, detalle conserva URL, tamaño 50
reinicia página y actividad incluye el registro desactivado. CSV real generado de
1.001 filas en 11 peticiones: se inspeccionó su Blob; no se comprobó la escritura
del archivo por Chrome. Sin desbordamiento horizontal de la página en móvil.
Capturas y logs sintéticos permanecen fuera del repositorio en `tmp/local-runtime/632-g2-*`.

Vista local: `http://127.0.0.1:5193/app/padres-de-familia?search=EncargadoSintetico`.
El entorno usa una base separada de demostración; no modifica las vistas previas
anteriores. Reversión: revertir el commit; no requiere reversión de datos.
