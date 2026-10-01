# Instrucciones: Manual de Usuario en Video

## Objetivo

Produzca un manual audiovisual que enseñe a usar SIGA-INEBI desde cada rol
autorizado, con datos ficticios y sin mostrar configuraciones, datos ni acciones
que el rol no puede realizar.

## Audiencia

- Secretaria y personal administrativo.
- Docentes.
- Encargados o padres de familia.
- Personal de control de ingreso y salida.
- Direccion.
- Administradores funcionales, cuando corresponda.

## Preparacion obligatoria

1. Lea `docs/requirements/functional-scope.md`, el catalogo de requerimientos y
   el glosario antes de redactar los guiones.
2. Use exclusivamente una base de demostracion y cuentas ficticias por rol.
3. No muestre contrasenas, cookies, secretos, datos personales reales ni URLs de
   almacenamiento interno.
4. Valide previamente que el rol mostrado tiene los permisos y el alcance de cada
   accion grabada.

## Estructura del material

Grabe un video por modulo o flujo coherente. Mantenga cada video entre 3 y 8
minutos cuando sea posible. Cada uno debe incluir:

1. Objetivo del flujo.
2. Rol que puede ejecutarlo.
3. Precondiciones necesarias.
4. Demostracion paso a paso.
5. Validaciones, estados y mensajes esperados.
6. Errores comunes o rechazos esperados.
7. Resultado final y accion siguiente.

## Modulos que se deben cubrir

### Acceso y navegacion general

- Inicio y cierre de sesion.
- Tiempo de inactividad y redireccion a login.
- Navegacion, perfil y mensajes de error.
- Restricciones visibles por permiso y alcance.

### Personas y estudiantes

- Registro y consulta de personas.
- Registro, actualizacion y consulta de estudiantes.
- Vinculacion y finalizacion de relaciones con encargados.
- Contactos de emergencia y expediente basico autorizado.

### Estructura academica y ciclos

- Institucion, niveles, grados, secciones, aulas y asignaciones.
- Creacion, apertura, cierre y consulta de ciclos escolares.
- Horarios y sus validaciones relevantes.

### Matriculas

- Matricula, reinscripcion, vigencia, estado e historial.
- Rechazo por matricula activa incompatible.
- Validacion de cupo y documentos pendientes, si el rol tiene acceso.

### Docencia, evaluacion y asistencia

- Consulta de grupos y horarios asignados.
- Registro y correccion autorizada de asistencia o jornada.
- Captura de notas, estados de unidad y consulta de resultados.

### Documentos, credenciales y auditoria

- Carga, consulta e historial autorizado de documentos.
- Vista previa de plantillas y emision cuando aplique.
- Consulta de eventos de auditoria solo para los roles permitidos.

### Administracion funcional

- Cuentas vinculadas a personas.
- Roles, permisos y alcances.
- Configuraciones institucionales disponibles para administracion.

## Criterios de cierre

- Cubra las operaciones principales de cada modulo: crear, consultar, actualizar,
  cambiar estado, cerrar, emitir, exportar o acciones especiales cuando existan.
- No grabe todas las combinaciones de filtros; muestre al menos un uso
  representativo y explique el alcance de los filtros disponibles.
- Incluya evidencia visual de al menos un rechazo de autorizacion, validacion o
  consistencia en los modulos sensibles.
- Entregue una lista de videos con titulo, modulo, rol y duración.
