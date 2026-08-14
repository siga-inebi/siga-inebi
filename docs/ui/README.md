# Capturas de la interfaz

Capturas tomadas con Playwright contra el entorno de desarrollo
(`docker compose up`), con la cuenta demo y los datos de `seed_demo_data`.

- `before/` — la interfaz anterior al refactor de UI.
- `after/` — la interfaz con el sistema de diseno de SIGA-INEBI.

Los conteos en cero y los 403 que aparecen en algunas pantallas son datos y
permisos reales del entorno demo, no fallos de la interfaz: la cuenta demo no
tiene los permisos atomicos de `jornada-parameters` ni de `reporting/*`, y las
pantallas muestran ese error en vez de una tabla vacia.

## Como regenerarlas

Con el entorno arriba y sesion iniciada como `admin`:

```
docs/ui/after/01-login.png            /login
docs/ui/after/02-panel.png            /app
docs/ui/after/03-cursos.png           /app/cursos
docs/ui/after/04-niveles.png          /app/niveles
docs/ui/after/05-sedes.png            /app/sedes
docs/ui/after/06-personas.png         /app/personas
docs/ui/after/07-ciclos.png           /app/ciclos
docs/ui/after/08-matriculas.png       /app/matriculas
docs/ui/after/09-asistencia.png       /app/asistencia
docs/ui/after/10-evaluacion.png       /app/evaluacion
docs/ui/after/11-plantillas.png       /app/plantillas
docs/ui/after/12-alertas.png          /app/alertas
docs/ui/after/13-asignaciones.png     /app/asignaciones
docs/ui/after/14-estudiantes.png      /app/alumnos
docs/ui/after/15-modal-formulario.png /app/ciclos con la ventana de alta abierta
docs/ui/after/16-oscuro-niveles.png   /app/niveles en modo oscuro
docs/ui/after/17-oscuro-panel.png     /app en modo oscuro
docs/ui/after/18-movil-cursos.png     /app/cursos a 390x844
```

Viewport 1440x900 salvo la captura movil. El modo se fuerza escribiendo
`localStorage["mui-mode"]` antes de recargar.
