# Traslados y cierre de implementación de M3 (#632)

## Alcance

Esta entrega conecta traslado de ingreso y de egreso a sus endpoints existentes
(RF-MOV-001), con vigencia explícita e historial paginado (RF-MOV-003). Se revisaron
AGENTS.md, los requerimientos canónicos y ADR-0004/0005/0006/0008. No cambia reglas
de dominio, contratos API, autorizaciones, migraciones ni variables del proyecto.

Junto con [PR #639](https://github.com/siga-inebi/siga-inebi/pull/639), M3 cubre las
cinco operaciones solicitadas. La integración a `develop` y aceptación visual
institucional siguen pendientes hasta que se revisen y fusionen ambas entregas.
No completa el epic #632, la promoción de M4 ni la reorganización integral de 1.5.

| Operación de M3 | Acceso en Matrículas | Evidencia |
| --- | --- | --- |
| Cambio de sección | Fila vigente → Movimientos → Registrar movimiento | PR #639; `enrolmentMovements.test.jsx` |
| Retiro | Fila vigente → Movimientos → Registrar movimiento | PR #639; `enrolmentMovements.test.jsx` |
| Anulación | Historial de movimientos → fila compatible | PR #639; `test_movement_ui_contract.py` |
| Traslado de ingreso | Cabecera → Traslado de ingreso | Esta entrega; `studentTransfers.test.jsx` y `test_student_transfer_ui_contract.py` |
| Traslado de egreso | Fila vigente → Traslado de egreso | Esta entrega; mismas pruebas |

## Recorridos y captura

Ingreso: buscar un estudiante ya registrado por nombre o código, elegirlo,
seleccionar ciclo y sección de destino y capturar vigencia. No exige que tenga
matrícula previa. Para un estudiante aún no registrado, el alta del expediente
corresponde a Estudiantes. La búsqueda se activa desde dos caracteres, usa
`search` y `page` en servidor y permite recorrer las coincidencias; no descarga
el padrón ni corta silenciosamente en la primera página.

Las secciones se consultan por ciclo. Grado y jornada proceden de la sección
seleccionada y viajan como UUID, sin pedir al usuario que traduzca identificadores.
Cambiar el ciclo limpia la sección; cambiar estudiante descarta los datos de
destino anteriores. Ambas acciones y cualquier edición invalidan la revisión.

Egreso: se abre desde una matrícula vigente, conservando el contexto visible de
la fila, y solicita fecha y motivo opcional. La advertencia explica el cierre de
matrícula y los efectos sobre credencial y acceso. El formulario no confunde
egreso (`transferred`) con retiro (`withdrawn`).

Cada formulario requiere **Revisar traslado** y luego **Confirmar ingreso/egreso**,
dentro del mismo diálogo. Se muestra vigencia, destino y motivo cuando aplica.
Durante el envío se bloquean edición, pestañas, cierre y doble confirmación.
Los errores conservan el borrador e invalidan la revisión; no hay reintentos
automáticos de escrituras. Se refrescan las listas y se puede consultar el
historial para comprobar un resultado incierto antes de otra decisión.

Después del éxito se muestra el historial actualizado del estudiante con fechas
de vigencia y registro separadas. Se conserva la evidencia original y las
correcciones existentes. Para otra operación debe abrirse un contexto actualizado.

## Contratos y autorización conservados

- `POST /api/v1/enrolments/transfers/in/`: `student_id`, `academic_cycle_id`,
  `grade_id`, `shift_id`, `section_id`, `effective_on`.
- `POST /api/v1/enrolments/{enrolment_id}/transfer-out/`: `effective_on` y `reason`
  opcional. El identificador de ruta corresponde a la matrícula, no al estudiante.
- Ambos responden con el movimiento registrado; el historial usa
  `GET /api/v1/enrolments/movements/?student_id=...&page=...`.
- Se mantienen `enrollment_update` y sus alcances existentes. El selector utiliza
  la lectura autorizada `student_view_basic` de `/students/`; no agrega accesos
  implícitos para buscar expedientes sin permiso.
- La API conserva la validación de ciclo, estado, vigencia, cupo y duplicados.
  Los traslados con fecha futura se rechazan. Los traslados no admiten anulación
  mientras el dominio no disponga de una reversión segura; la UI lo explica.
- Se conservan auditoría e historial, así como los efectos existentes de cierre
  de permanencia y activación al ingresar. No se añaden datos de otra institución
  ni reglas nuevas de promoción, revocación o restauración de credenciales.

## Verificación reproducible

Datos exclusivamente sintéticos y backend en PostgreSQL:

```powershell
python -m pytest --reuse-db --no-cov -q tests/api/test_student_transfer_ui_contract.py tests/api/test_enrolments_api.py tests/unit/test_enrolments_services.py tests/integration/test_enrolments.py
npm exec vitest -- run src/test/studentTransfers.test.jsx src/test/newModulePages.test.jsx src/test/moduleServices.test.js --maxWorkers=1 --no-file-parallelism
```

API nueva de pruebas: egreso → búsqueda del expediente trasladado → ingreso en
otra sección, con movimientos distintos, fuente histórica intacta y auditoría;
rechazo de fechas futuras sin efectos parciales para ambos sentidos; ingreso
denegado sin permiso/alcance. La regresión existente verifica permanencia,
credenciales, permisos, cupo y conservación de historia.

Frontend: diez casos específicos del flujo, accesos desde la página y rutas de
servicios. Se cubren selección en segunda página, filtros de destino, payload
correcto, revisión invalidada, errores, cierre durante escritura, ausencia de
reintentos automáticos e historial paginado. Las pruebas HTTP no se presentan
como revisión visual automatizada.

## Integración y reversión

Rama creada desde `develop` actualizado (`5f8630d`), con destino `develop`.
Los commits del #639 no se incorporan a este PR. La comprobación conjunta de M3
se realiza en una copia local de revisión que combina ambas entregas; no fusiona
ramas públicas ni modifica `develop`. Los detalles de pruebas y CI se adjuntan al PR.

La infraestructura de listas del #630 y la reorganización de altas de M6 conservan
su alcance. El flujo nuevo reutiliza componentes actuales y no agrega catálogos
globales de personas o estudiantes. El contexto de egreso reutiliza las celdas de
la tabla para conservar compatibilidad con los nombres anidados de M1 (#636).

Reversión: retirar la UI y revertir código, sin migraciones. Conservar matrículas,
movimientos y auditoría ya registrados; no eliminar historia para revertir una
interfaz ni simular anulaciones de traslados que el dominio no permite.
