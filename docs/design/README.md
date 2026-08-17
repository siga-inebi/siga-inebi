# Diseno de Interfaz y Navegacion

Bloque de diseno de SIGA-INEBI: como se ve y como se navega el sistema desde el
punto de vista del usuario. Es la capa previa a la implementacion completa.

## Entregables

| Entregable | Archivo | Que contiene |
| --- | --- | --- |
| Documento para la institucion | [SIGA-INEBI-Diseno-de-interfaz-y-navegacion.docx](SIGA-INEBI-Diseno-de-interfaz-y-navegacion.docx) | Documento Word de 39 paginas que reune todo el bloque, con capturas del prototipo. Es el entregable presentable |
| Wireframes | [wireframes.md](wireframes.md) | Estructura funcional de las 12 pantallas principales, con estados y reglas |
| Mapa de navegacion | [navigation-map.md](navigation-map.md) | Rutas, flujo de entrada, saltos entre modulos y visibilidad por rol |
| Prototipo navegable | [prototipo-siga.html](prototipo-siga.html) | Recorrido completo del sistema con selector de rol |
| Guia de validacion | [prototype-validation.md](prototype-validation.md) | Guion de sesion, recorridos, preguntas y checklist para validar con la institucion |
| Bitacora de observaciones | [validation-observations.md](validation-observations.md) | Registro de observaciones, cambios aplicados y confirmacion por rol |

## Como abrir el prototipo

Abrir `prototipo-siga.html` con doble clic en cualquier navegador. Es un archivo
unico, sin dependencias, sin instalacion y sin conexion a internet.

En la barra negra superior:

- **Ver como** cambia el rol activo. La barra lateral, los botones y los datos se
  recortan segun el rol. Es la forma rapida de comprobar la matriz de accesos.
- **Mapa de navegacion** abre la vista de diseno con todas las pantallas y su
  ruta real en la aplicacion.
- **Reiniciar** vuelve al login y limpia el estado.

Los datos son ficticios. Ninguna accion guarda informacion.

## Recorrido sugerido para una demostracion

1. Login, ingresando como `Administrativo`.
2. Panel, accesos rapidos y pendientes.
3. Estudiantes, busqueda y expediente por pestanas.
4. Matriculas, asistente completo de cuatro pasos.
5. Cambiar a `Docente` y observar como se reduce el menu y el panel.
6. Cambiar a `Encargado` y ver el portal de consulta.
7. Cambiar a `Admin`, abrir Usuarios y la matriz de accesos.
8. Probar `Acceso denegado` abriendo Usuarios con un rol sin permiso.

## Alcance de este bloque

Incluye estructura de pantallas, navegacion, visibilidad por rol y estados de la
interfaz. No incluye diseno visual final, comportamiento real contra la API ni
implementacion de modulos.

Las rutas marcadas como propuesta en el mapa de navegacion aun no existen en
`frontend/src/routes/AppRoutes.jsx`. Las que ya existen se respetan sin cambiar
su URL.

## Documentos relacionados

- Roles, permisos y alcances: [authorization model](../architecture/authorization-model.md)
- Dominios del sistema: [domain map](../architecture/domain-map.md)
- Entidades base: [initial data model](../architecture/initial-data-model.md)
- Alcance funcional: [functional scope](../requirements/functional-scope.md)
- Terminologia: [glossary](../requirements/glossary.md)
- Decisiones pendientes: [pending decisions](../decisions/pending-decisions.md)

## Estado

| Entregable | Estado |
| --- | --- |
| Wireframes | Listo para validar |
| Mapa de navegacion | Listo para validar |
| Prototipo navegable | Listo para validar |
| Validacion con la institucion | Pendiente de agendar |
| Diseno visual final | Fuera de este bloque |
