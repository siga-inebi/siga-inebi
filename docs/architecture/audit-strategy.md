# Audit Strategy

## Objetivo

Garantizar trazabilidad de operaciones sensibles, lecturas sensibles e intentos denegados definidos por RF/RNF.

## Eventos a registrar

- Escrituras en dominios de negocio.
- Cambios de parametros con responsable y vigencia.
- Lecturas sensibles de salud y documentos privados.
- Intentos denegados relevantes.
- Emisiones documentales oficiales.
- Correcciones sobre datos historicos.

## Contenido minimo del asiento

- Actor
- Tipo de actor o atribucion persistente
- Fecha y hora
- Recurso afectado
- Operacion
- Antes y despues cuando aplique
- Alcance evaluado
- Resultado
- Origen tecnico

## Reglas

- Bitacora inmutable.
- Auditoria separada de logs tecnicos efimeros.
- No depender de UI para generar auditoria.
- Correcciones agregan nuevos asientos.

## Consultas

- Acceso restringido por permiso y alcance.
- Exportacion restringida.
- Retencion pendiente de decision institucional.
