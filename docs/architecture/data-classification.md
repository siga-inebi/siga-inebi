# Data Classification

## Niveles

| Nivel | Descripcion | Ejemplos | Controles minimos |
| --- | --- | --- | --- |
| Public | Puede exponerse sin autenticacion controlada | Metadatos minimos de verificacion publica si se habilita | Rate limiting, revelacion minima |
| Internal | Uso interno institucional general | Catalogos no sensibles, estructura academica | Authn, authz basica |
| Restricted | Uso limitado por rol y alcance | Matricula, notas, asistencia, contactos | Authz con alcance, auditoria de escritura |
| Sensitive Special | Datos de alta sensibilidad | Salud, respaldos, documentos privados, lecturas sensibles | Authz reforzada, auditoria de lectura y escritura, minimizacion |

## Clasificacion inicial por conjunto

- Credencial QR: `Restricted`, con QR opaco.
- Fotografia estudiante: `Restricted`.
- Contactos emergencia: `Restricted`.
- Notas de salud: `Sensitive Special`.
- Documentos de expediente: `Sensitive Special` o `Restricted` segun tipo.
- Justificaciones y respaldos: `Sensitive Special`.
- Bitacora y auditoria: `Restricted` o `Sensitive Special` segun contenido.
- Parametros institucionales: `Internal`.

## Reglas

- No usar datos reales en desarrollo.
- Pantalla de escaneo no muestra datos fuera de minima confirmacion permitida.
- Descarga de documentos con enlace corto ligado al portador.
- Politicas de retencion deben documentarse antes de implementar borrados o vencimientos.
