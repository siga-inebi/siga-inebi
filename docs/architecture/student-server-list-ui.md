# Listado de estudiantes en el servidor — E3/E10, issue #632

## Problema y alcance

El listado descargaba el padrón completo para buscar por nombre y paginar en el navegador.
Ahora adopta `useServerList` y `ExportCsvButton` de #630, integrados en #651: descarga solo
la página visible. La búsqueda por nombre o código y el estado se resuelven antes de paginar.

Esta entrega no migra Docentes, Encargados, Personas ni Matrículas. E8/E9/D5 se entregan
por separado en #652. No cambia reglas de estado, permisos, esquema ni escrituras del dominio.

## Contrato y navegación

Se conserva `GET /api/v1/students/` y el sobre `{count, next, previous, results}`:

| Parámetro | Uso de la pantalla |
| --- | --- |
| `page` | Página base uno; por defecto 1 |
| `page_size` | 25 por defecto; selector 10, 25, 50, 100; máximo 100 |
| `search` | Nombre o código, enviado tras 300 ms sin nuevas teclas |
| `status` | Estado del expediente; omitido para todos |
| `include_inactive` | Solo se envía `true` al activar «Mostrar desactivados» |

La API también admite buscar por CUI; esta pantalla no lo anuncia ni expone ese dato.
Se conserva el orden determinista por código; no se agrega ordenación interactiva.
El total viene de `count`, nunca de la longitud de la página recibida.

El estado se conserva en la URL; allí `include_inactive=1` representa el interruptor.
Buscar, cambiar estado, actividad o tamaño vuelve a la primera página. Abrir un expediente
guarda la URL del listado en el estado de navegación; «Volver a estudiantes» la recupera,
incluso después de cambiar pestañas. Un acceso directo al expediente vuelve al listado base.
Se aceptan únicamente destinos `/app/alumnos` con consulta opcional.

`status=inactive` y la baja lógica `is_active=false` son independientes. Elegir el estado
«Inactivo» no incluye expedientes desactivados automáticamente. El alcance autorizado se
aplica en el servidor tanto a la página como a la exportación.

## Exportación y estados de la interfaz

El CSV comienza solo al pulsar «Exportar CSV» y recorre todas las páginas filtradas de
100 filas desde la primera, sin corte a 1.000. Conserva búsqueda, estado y actividad,
pero no página ni tamaño de visualización. Incluye nombre, código y estado traducido;
usa el escape CSV compartido. Presenta avance, cancelación y errores mediante la base común.
No ofrece una instantánea transaccional: modificaciones concurrentes pueden cambiar el padrón.
Cancelar evita continuar el recorrido o generar el archivo, sin garantizar abortar la petición
HTTP en curso. El archivo completo se prepara en memoria únicamente al exportar.

Durante búsqueda pendiente o consulta se desactiva la exportación para evitar filtros antiguos.
`SearchField` usa `debounceMs=0` para dejar la espera únicamente en `useServerList`;
el modo sin retardo propaga el cambio en el mismo evento y evita perder letras.
El hook limita también tamaños editados manualmente en la URL al máximo real de la API.

Un error sustituye la tabla por un mensaje con «Reintentar», sin simular una lista vacía.
Tras crear se consulta la página con los filtros vigentes, sin insertar artificialmente
un registro que no coincida con ellos.

## Pruebas y revisión

- `frontend/src/test/AlumnosPage.test.jsx`: una petición al abrir, total del servidor,
  URL, paginación, tamaño, búsqueda por código, estado/actividad, error/reintento, alta
  y exportación completa de 1.001 filas filtradas.
- `frontend/src/test/StudentRecordPage.test.jsx`: retorno válido, rechazo de otros destinos
  y conservación al cambiar pestaña.
- `frontend/src/test/useServerList.test.jsx`: tamaño manual 1.000 limitado a 100 sin perder páginas.
- `backend/tests/api/test_student_server_list_ui_contract.py`: 1.001 estudiantes sintéticos,
  filtros antes de paginar, máximo de tamaño, última página, alcance y campos privados omitidos.
- `backend/tests/api/test_community_list_filters_api.py`: contratos de búsqueda/actividad,
  validación y denegación sin permiso o alcance.

Validación local: 536 pruebas frontend en 67 archivos, 88,20 % de líneas con Vitest 3.2.7;
43 pruebas API sobre PostgreSQL aprobadas; 69 pruebas de herramientas de requerimientos/carga
y 7 de políticas de GitHub. ESLint, formato, Ruff del archivo nuevo, comprobaciones Django
y ausencia de migraciones pendientes aprobados. Build: 227.434/230.000 bytes gzip iniciales;
página fría máxima 246.833/250.000. Node local 24, Python 3.11 y PostgreSQL 18;
CI verifica las versiones fijadas por el proyecto. No se ejecutó Docker localmente.

Revisión real en Chrome, 1440×1000 y 390×844: página 41 con el estudiante 1.001,
retorno después de visitar Salud, tamaño 50 con reinicio a página uno, baja lógica optativa
y CSV generado de 1.001 filas mediante 11 páginas filtradas. Se inspeccionó el contenido del
Blob producido por la interfaz; la escritura de la descarga por Chrome no quedó comprobada.
La tabla conserva su desplazamiento horizontal compartido en móvil, sin desbordar la página.
Al abrir se observa una solicitud de la página y otra de tamaño 1 para el contador lateral,
sin recorrido del padrón. Las capturas y logs locales contienen únicamente datos sintéticos;
no se versionan bases, sesiones, archivos descargados ni perfiles de navegador.

Vista de revisión: `http://127.0.0.1:5190/app/alumnos?search=LIST-DEMO&status=active`.
Entrega y evidencia de CI: [PR #653](https://github.com/siga-inebi/siga-inebi/pull/653),
desde `feat/632-student-server-list` hacia `develop`.

No hay migraciones, variables nuevas ni cambios de contratos públicos. Revertir el PR no
requiere modificar datos ni historial. Se conservan los estados globales de RF-EXP-003,
RF-EXP-008 y RF-ALC-001; se agrega evidencia de consumo de sus contratos.
