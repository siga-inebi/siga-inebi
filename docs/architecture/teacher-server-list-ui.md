# Listado y catálogo de puestos de Docentes — T2/T4, #632

## Alcance

Docentes y administrativos adopta `useServerList` y `ExportCsvButton` de #630/#651.
Al abrir descarga una página. Busca por nombre/código y combina puesto con actividad en
el servidor. El catálogo único de puestos sale de `Teacher.Position` y alimenta filtro,
alta y edición; se retira `teachersMock.js`. T1 y sus pruebas institucionales se conservan.
T3, Encargados, Personas y Matrículas quedan fuera de esta entrega.

Los PR #652 y #653 son independientes. Se incorporan los mismos ajustes mínimos compartidos
de #653 (retardo cero del buscador, máximo 100 y exportación desactivable) para verificar
esta rama desde `develop`. No se incorporan los cambios propios de Estudiantes.

## Contratos

Se conserva `GET /api/v1/teachers/` y `{count, next, previous, results}`:

| Parámetro | Comportamiento |
| --- | --- |
| `page` | Base uno; valor inicial 1 |
| `page_size` | 25 inicial; selector 10/25/50/100; máximo 100 |
| `search` | Nombre o código tras 300 ms sin nuevas teclas |
| `position` | Valor del catálogo; omitido para todos los puestos |
| `include_inactive` | `true` al activar «Mostrar desactivados» |

La API también busca por CUI, pero esta pantalla no lo anuncia ni expone ese dato.
Se conserva el orden por código; no se agrega ordenación interactiva.

Nuevo `GET /api/v1/teachers/positions/`: arreglo sin paginar de objetos `{value, label}`,
derivado de `Teacher.Position.choices`. Exige sesión con `IsAuthenticated`, rechaza
escrituras y no consulta personas ni docentes. La consulta vive en `queries.py` y la vista
solo serializa. OpenAPI documenta el GET. Publica Docente Titulado, Docente Interino,
Orientador/a y Administrativo; no cambia sus valores ni crea un catálogo editable.

## Navegación, errores y formularios

Página, tamaño, búsqueda, puesto y actividad se conservan en URL; allí la actividad usa
`include_inactive=1`. Cambiar búsqueda/filtros/tamaño vuelve a página uno. «Limpiar» elimina
búsqueda, puesto y actividad, conservando tamaño. El detalle sigue en su ventana existente.
Crear/editar consulta de nuevo la página vigente, sin insertar o reemplazar artificialmente
filas que ya no coincidan con el filtro.

El catálogo se comparte con React Query bajo `teachers/positions`. Mientras carga, alta y
edición no se abren. Si falla o llega vacío, ofrece «Reintentar puestos»; la consulta del
listado continúa disponible. No hay lista fija como respaldo. Un puesto de URL se conserva
visible mientras carga o si deja de estar publicado, sin añadirlo a los formularios; la API
sigue validándolo. Un error de lista ofrece «Reintentar listado» y sustituye la tabla,
sin simular ausencia de docentes.

La ventana documental carga al solicitarla para conservar el presupuesto de ruta;
mantiene sus contratos y permisos. La tabla conserva desplazamiento horizontal en móvil.

## CSV y límites

«Exportar CSV» recorre todas las páginas filtradas de 100 filas desde la primera, con
avance y cancelación. Incluye nombre, especialidad, puesto y código; conserva búsqueda,
puesto y actividad, omite página y tamaño de visualización. No corta a 1.000 ni exporta
filtros anteriores mientras hay texto o consulta pendientes. Usa el escape CSV compartido.
Se prepara en memoria y no es una instantánea transaccional ante cambios concurrentes.
Cancelar detiene el recorrido entre páginas, sin garantizar abortar el HTTP en curso.

## Autorización y trazabilidad

Se conserva la autorización del listado docente: sesión. Su carencia de permisos atómicos
y la de sus escrituras está documentada en #643 y [permisos-en-ui.md](../development/permisos-en-ui.md);
esta entrega no declara resuelta esa brecha ni inventa permisos. El catálogo solo devuelve
opciones estáticas. Documentos conserva permiso y alcance existentes.

No existe un RF específico de búsqueda/puesto docente en el catálogo de requerimientos.
Se trazan T2/T4 y 1.1 en la matriz, sin marcar otros RF/RNF como completados ni cambiar
reglas o contratos de escritura. ADR-0004/0005/0006/0008 revisados; sin nueva decisión.

## Evidencia y reversión

- `backend/tests/api/test_teacher_server_list_ui_contract.py`: catálogo canónico, rechazo
  anónimo/de escritura, 1.001 docentes, máximo 100, filtros antes de paginar, última página,
  actividad optativa y omisión de CUI/nacimiento.
- `backend/tests/api/{test_community_list_filters_api,test_teachers_api}.py`: regresiones
  de búsqueda, validación, actividad, creación y edición.
- `frontend/src/test/DocentesPage.test.jsx`: URL, tamaño/página, filtros, limpieza, CSV de
  1.001 filas, errores/reintentos, catálogo dinámico, edición fuera del filtro y documentos
  bajo demanda; conserva las pruebas de formularios institucionales.
- `frontend/src/test/{moduleServices.test.js,useServerList.test.jsx}`: rutas, parámetros y
  límite de tamaño ante URL manual.

Validación local: 536 pruebas frontend en 67 archivos, 88,24 % de líneas con Vitest 3.2.7;
56 pruebas API en PostgreSQL; 69 pruebas de herramientas y 7 de políticas de GitHub.
ESLint, formato, Ruff, check Django y ausencia de migraciones pendientes en verde.
OpenAPI: cero errores; incluye prueba del arreglo sin paginación y sus avisos preexistentes
en dominios ajenos. Node local 24, Python 3.11 y PostgreSQL 18; CI verifica versiones fijadas.
Build: 227.455/230.000 bytes gzip iniciales, ruta máxima 19.115/20.000 y página fría máxima
246.570/250.000. No se ejecutó Docker localmente.

Chrome real, escritorio 1440×1000 y móvil 390×844: una página y un catálogo al abrir, más
el contador lateral de tamaño 1; página 41/registro 1.001, detalle conserva URL, tamaño 50
reinicia página, filtro Administrativo y actividad optativa, formulario con puestos canónicos.
CSV generado de 1.001 filas/11 páginas: se inspeccionó su Blob; la escritura del archivo por
Chrome no quedó comprobada. La tabla usa su desplazamiento horizontal sin desbordar la página.
Vista local: `http://127.0.0.1:5191/app/docentes?search=TEACH-DEMO&position=Docente+Titulado`.
No se versionan datos, sesiones, capturas ni descargas. Entrega y evidencia CI:
[PR #654](https://github.com/siga-inebi/siga-inebi/pull/654), desde
`feat/632-teacher-server-list` hacia `develop`.

Sin variables nuevas ni migraciones. Revertir el PR restaura la pantalla y retira el endpoint
aditivo; no requiere cambiar datos ni historial.
