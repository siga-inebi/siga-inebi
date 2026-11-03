# Despliegue seguro

## Transporte y cookies

Producción debe ejecutarse con `DJANGO_ENVIRONMENT=production` detrás de un proxy TLS que envíe `X-Forwarded-Proto: https`. Esta configuración activa redirección HTTPS, HSTS y cookies de sesión y CSRF con `Secure`; la cookie de sesión además es `HttpOnly` y `SameSite=Lax`.

No se deben registrar secretos, enlaces de restablecimiento, cookies ni valores de variables de entorno. Los secretos se administran exclusivamente en el proveedor de despliegue. Desarrollo local usa `DJANGO_ENVIRONMENT=development` para permitir HTTP en `localhost`; no es una configuración válida para un ambiente expuesto.

## Cámara

La interfaz rechaza el uso de cámara cuando `isSecureContext` no está disponible. El navegador solo debe solicitar permisos de cámara desde HTTPS o el contexto seguro equivalente de desarrollo local.
