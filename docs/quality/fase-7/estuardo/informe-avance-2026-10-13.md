# Avance de Estuardo â€” alcance vigente

**Fecha de actualizaciÃ³n:** 13 de octubre de 2026
**Rama local evaluada:** `develop`
**SHA de evaluaciÃ³n D2:** `5ed5fd24d02f494053c53dbbbafe50a8412534e5`

La autorizaciÃ³n de Pablo comunicada por Estuardo retira D1, D3 y D4 de sus responsabilidades actuales de evaluaciÃ³n. El acuerdo estÃ¡ registrado en [ajuste de alcance](ajuste-alcance.md). Permanecen D2, D5, la documentaciÃ³n propia y la revisiÃ³n cruzada; no se atribuyen estos resultados a un despliegue QA.

## Lo completado con evidencia

- Se repitieron en el SHA indicado 196 pruebas de evaluaciÃ³n/reportes, 43 de integraciÃ³n acadÃ©mica/documental y 4 pruebas de regresiÃ³n frontend de INC-008: **243 aprobadas, 0 fallidas**. Las corridas backend emitieron cuatro advertencias Django cada una y 448 pruebas quedaron deseleccionadas en la selecciÃ³n de integraciÃ³n. El detalle y los comandos estÃ¡n en [D2](d2-evaluacion-integracion.md).
- Se registraron los escenarios ejecutados de la sesiÃ³n documental/API/auditorÃ­a de RoÃ­ en [su UAT parcial](uat-roi-documentos-api-auditoria.md). El SHA servido por QA no quedÃ³ verificado en el registro y hay escenarios bloqueados.
- La revisiÃ³n inicial de `roi-cierre.md` y el Manual 07 quedÃ³ como **Requiere cambios** en el [PR #591](https://github.com/siga-inebi/siga-inebi/pull/591). El PR sigue en el SHA revisado; la re-revisiÃ³n depende de que RoÃ­ publique cambios.

## Pendientes que siguen dentro del alcance

1. Pablo debe confirmar la regla aplicable a pesos; el catÃ¡logo indica que las ponderaciones son configurables, pero no fija el criterio institucional de cÃ¡lculo.
2. Completar la revisiÃ³n D2 de JosuÃ© y RoÃ­, y resolver QA4-PDF-01 con una comprobaciÃ³n de descarga y legibilidad de la boleta.
3. Registrar el SHA del candidato final desplegado y repetir en Ã©l las pruebas afectadas. El SHA local de D2 no identifica por sÃ­ mismo el candidato QA final.
4. Consolidar con Emilio el manual de usuario en video existente que Estuardo confirmÃ³ tener. Su ubicaciÃ³n y checksum, tÃ­tulos/mÃ³dulos/roles/duraciÃ³n y revisiÃ³n siguen pendientes de registro en [seguimiento de manuales](../seguimiento-manuales.md).
5. Re-revisar el PR #591 tras las correcciones de RoÃ­. Para completar el UAT documental separado, quedan bloqueadas la consulta denegada, la auditorÃ­a de denegaciÃ³n y las tres descargas con token; la carga vÃ¡lida estÃ¡ observada hasta verificar versiÃ³n/metadatos.

La lista anterior no vuelve a introducir D1, D3 o D4 como tareas de evaluaciÃ³n de Estuardo. El plan general de Fase 7 conserva criterios de salida compartidos; cualquier retiro global requiere actualizar esos criterios mediante la coordinaciÃ³n de calidad.
