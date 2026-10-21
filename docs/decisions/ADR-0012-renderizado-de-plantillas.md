# ADR-0012: contenido estructurado y motor PDF de plantillas

## Estado y alcance

Aceptada para la base D4.1 de RF-PLA-009. Esta decisión cubre el formato persistido,
la configuración de página, el historial y el motor compartido de PDF. El editor visual
de D4.2 queda fuera de esta entrega y RF-PLA-009 permanece en progreso hasta incorporarlo.

## Contexto

Las plantillas almacenaban únicamente texto plano y la vista previa devolvía ese texto.
La emisión individual construía el PDF con un ensamblador propio, de modo que una vista
previa con formato no podía garantizar el mismo resultado que el documento emitido.
Cada versión histórica debe conservar también el diseño con el que fue creada.

## Decisión

- `content_format` distingue `plain` y `rich`. El formato `plain` conserva el contrato
  anterior; `rich` usa JSON estructurado versión 1 almacenado de forma canónica.
- El esquema cerrado permite párrafos, títulos de niveles 1 a 3, alineación y texto con
  negrita, cursiva o subrayado. Los marcadores continúan limitados al catálogo autorizado.
- La plantilla y cada versión guardan tamaño (`letter`, `legal`, `a4`), orientación,
  márgenes en puntos, texto de pie y hasta dos bloques de firma.
- ReportLab 5.0.1 y Platypus son el único motor de composición. La vista previa y la
  emisión individual llaman a `render_template_pdf`; por ello aplican las mismas reglas.
- La vista previa puede recibir contenido y configuración de borrador. Devuelve el PDF
  en base64 y no guarda una versión ni emite un documento.

## Razones

ReportLab ofrece composición paginada, párrafos con formato y tamaños de página desde
Python sin requerir un navegador o binarios del sistema. Eso mantiene el despliegue del
backend reproducible y evita dos implementaciones con resultados distintos. El JSON
cerrado permite validar y evolucionar el contenido sin aceptar HTML arbitrario.

## Compatibilidad, seguridad e historial

Las plantillas existentes reciben `plain`, Carta vertical, márgenes de 54 puntos, pie
vacío y ninguna firma; su contenido no se reescribe. Los campos nuevos se copian a cada
versión inmutable. El API continúa aceptando y devolviendo una cadena para `plain`; para
`rich` recibe y devuelve el objeto JSON. Los nodos, marcas, alineaciones, márgenes y
firmas fuera del contrato se rechazan antes de escribir.

El PDF base64 de vista previa es efímero. Mantiene la autorización institucional y la
auditoría de lectura existente. No se evalúa código, HTML libre ni expresiones dentro de
los marcadores. La emisión conserva folio, verificación, checksum y referencia a versión.

## Consecuencias

El backend y el visor ya soportan PDF real y borradores sin guardar. El formulario actual
sigue creando y editando contenido `plain`; D4.2 incorporará los controles de edición
enriquecida y configuración de página. Tablas, imágenes dentro del cuerpo y saltos de
página manuales no forman parte del esquema versión 1.

## Evidencia

- `backend/tests/unit/test_rich_template_rendering.py`
- `backend/tests/api/test_documents_api.py`
- `backend/tests/unit/test_documents_individual_issuance.py`
- `frontend/src/test/newModulePages.test.jsx`
