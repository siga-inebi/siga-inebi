"""
Generador de recursos sintéticos y locución TTS en español para el Manual de Usuario en Video.
Segmento: Documentos y Auditoría (Fase 7 - SIGA-INEBI).
"""

import os
import hashlib
import json
from gtts import gTTS
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEMO_DIR = os.path.join(BASE_DIR, "docs", "manuals", "recursos-demostracion")
AUDIO_DIR = os.path.join(BASE_DIR, "docs", "manuals", "locucion-documentos-auditoria")

os.makedirs(DEMO_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

SCENES = [
    {
        "id": "escena-01",
        "title": "Presentación del objetivo y roles autorizados",
        "screen_action": "Carátula institucional de SIGA-INEBI con título del video, roles (Secretaría y Auditoría) y advertencia de datos sintéticos de QA.",
        "text": (
            "Bienvenidos al manual de usuario de SIGA-INEBI. En este segmento demostraremos el "
            "ciclo completo de documentos y auditoría: desde la carga, validación, consulta e historial "
            "de versiones, hasta la descarga segura y la verificación de eventos en la bitácora institucional. "
            "Participaremos con dos roles autorizados: primero, el rol de Secretaría de Documentos, "
            "responsable de la gestión documental de expedientes; y posteriormente, el rol de Auditor institucional, "
            "facultado para la supervisión y trazabilidad del sistema."
        )
    },
    {
        "id": "escena-02",
        "title": "Inicio de sesión con cuenta QA ficticia",
        "screen_action": "Pantalla de login en entorno QA. Se ingresa con usuario de secretaría ficticio. Contraseña oculta por asteriscos; no se ven secretos ni cookies.",
        "text": (
            "Para esta demostración utilizaremos un entorno controlado de pruebas de aseguramiento de la calidad, "
            "con credenciales y cuentas estrictamente ficticias. Iniciamos sesión con la cuenta de secretaría técnica "
            "documental. Nótese que el sistema no revela contraseñas, tokens de sesión ni parámetros sensibles en pantalla. "
            "Una vez autenticados, el menú lateral despliega únicamente las opciones autorizadas para este perfil: "
            "Gestión de Matrículas y Expediente Documental."
        )
    },
    {
        "id": "escena-03",
        "title": "Carga de documento PDF sintético válido",
        "screen_action": "Búsqueda del estudiante Ana Demo Sintética (QA-DOC-001). Apertura del expediente documental y selección de constancia-demo.pdf.",
        "text": (
            "Ingresamos al expediente de la estudiante de prueba, Ana Demo Sintética, identificada con el "
            "código de control QA-DOC-001. En la pestaña de Requisitos y Respaldo Documental, seleccionamos "
            "la opción 'Adjuntar respaldo'. Para esta operación, seleccionamos el archivo sintético 'constancia-demo.pdf'. "
            "Este documento contiene únicamente datos ficticios de prueba. Al presionar 'Adjuntar archivo', "
            "el sistema recibe el flujo de datos para su procesamiento inmediato."
        )
    },
    {
        "id": "escena-04",
        "title": "Validación y resultado exitoso",
        "screen_action": "El sistema procesa la carga, muestra barra de progreso y notificación de éxito. El requisito cambia a estado Entregado.",
        "text": (
            "El backend de SIGA-INEBI ejecuta de inmediato las validaciones de seguridad: verifica la firma "
            "MIME real del archivo, calcula su suma de verificación criptográfica SHA-256 para garantizar inmutabilidad, "
            "y almacena el binario en el sistema de almacenamiento externo, manteniendo la base de datos libre de archivos pesados. "
            "Como observamos en pantalla, el sistema confirma la carga exitosa y actualiza el estado del requisito a 'Entregado'."
        )
    },
    {
        "id": "escena-05",
        "title": "Consulta del documento y su historial",
        "screen_action": "Tabla de archivos adjuntos mostrando nombre de archivo, versión v1, estado Vigente y fecha de registro.",
        "text": (
            "En la tabla de archivos adjuntos podemos consultar el registro generado. Vemos el nombre del archivo, "
            "su número de versión uno y su estado como 'Vigente'. Si en el futuro se adjunta una actualización o reemplazo "
            "del documento, el sistema no sobrescribe físicamente el archivo anterior; en su lugar, incrementa la versión a versión dos "
            "y marca la versión previa como histórica, garantizando la trazabilidad histórica completa del expediente de la estudiante."
        )
    },
    {
        "id": "escena-06",
        "title": "Descarga autorizada sin enseñar tokens ni URLs internas",
        "screen_action": "Clic en icono de descarga del documento. El navegador descarga el archivo de forma transparente sin URL de S3 ni tokens en la barra.",
        "text": (
            "Procedemos a realizar la descarga autorizada del documento. Al presionar el botón de descarga, el servidor "
            "valida los permisos del rol y transmite el archivo directamente mediante un flujo seguro. Observen que en ningún "
            "momento se exponen en la interfaz cookies de autenticación, tokens temporales ni rutas físicas de los servidores o almacenamiento interno. "
            "La transferencia se completa de forma transparente y segura."
        )
    },
    {
        "id": "escena-07",
        "title": "Intento de cargar archivo inválido o excedido y rechazo",
        "screen_action": "Intento de adjuntar archivo-invalido.exe y luego archivo-excedido.pdf. Alertas de validación en rojo.",
        "text": (
            "Demostremos ahora los mecanismos de defensa y rechazo del sistema. Intentamos primero adjuntar un archivo "
            "ejecutable, 'archivo-invalido.exe'. El sistema rechaza inmediatamente la carga con un error claro: "
            "'Tipo de archivo no permitido; únicamente se admiten formatos PDF e imágenes autorizadas'. De igual forma, si intentamos "
            "adjuntar 'archivo-excedido.pdf', cuyo tamaño supera la cuota máxima permitida, el sistema bloquea la carga antes de consumir recursos del servidor."
        )
    },
    {
        "id": "escena-08",
        "title": "Cambio a usuario sin alcance e intento de consulta ajena",
        "screen_action": "Cierre de sesión. Login con usuario docente o sin alcance. Intento de acceder al documento del estudiante ajeno.",
        "text": (
            "Ahora cerramos la sesión y cambiamos a un usuario sin alcance sobre este grado o sede institucional. "
            "Al intentar consultar o descargar el expediente de la estudiante QA-DOC-001 mediante su identificador, el sistema aplica la política "
            "de denegación por defecto. La interfaz muestra un mensaje de acceso no autorizado, denegando completamente la visualización "
            "del contenido. Ningún dato sensible es expuesto."
        )
    },
    {
        "id": "escena-09",
        "title": "Demostración de que la operación denegada queda auditada",
        "screen_action": "Explicación en pantalla de la arquitectura de bitácora transversal y captura de intentos 403/401.",
        "text": (
            "Toda operación sensible en SIGA-INEBI, incluyendo tanto las lecturas como los intentos denegados de acceso, "
            "queda registrada de manera inmutable en la bitácora transversal de auditoría. Este registro captura la fecha y hora exacta, "
            "la dirección IP de origen, el identificador del usuario, el recurso solicitado y el motivo del rechazo, "
            "impidiendo cualquier intento de manipulación no advertida."
        )
    },
    {
        "id": "escena-10",
        "title": "Ingreso con rol de auditor autorizado y consulta de bitácora",
        "screen_action": "Inicio de sesión con cuenta de Auditor institucional. Navegación a Bitácora y Eventos. Filtrado del evento denegado y la carga previa.",
        "text": (
            "Iniciamos sesión ahora con una cuenta que posee el rol de Auditor Institucional. Ingresamos al módulo de Bitácora "
            "y Eventos de Auditoría. Aquí podemos filtrar por tipo de evento documental y revisar la bitácora en tiempo real. "
            "En pantalla observamos el evento registrado: la carga exitosa realizada por secretaría y, justo después, el evento de "
            "acceso denegado generado por el usuario sin alcance, con su respectivo código de estado y sello temporal verificado."
        )
    },
    {
        "id": "escena-11",
        "title": "Cierre explicando resultado y siguientes pasos",
        "screen_action": "Resumen visual de los puntos demostrados, créditos institucionales y llamado al siguiente segmento del manual.",
        "text": (
            "Con esto concluimos la demostración del ciclo de documentos y auditoría en SIGA-INEBI. Hemos comprobado la carga válida, "
            "el versionado inmutable, la descarga segura sin fuga de credenciales, el bloqueo de archivos no autorizados y la trazabilidad integral "
            "en la bitácora. Para consultar otros flujos como evaluación o asistencia, continúe con los siguientes módulos de este manual audiovisual. "
            "Muchas gracias."
        )
    }
]

def generate_synthetic_assets():
    print("--- 1. Generando archivos de prueba sintéticos ---")
    pdf_path = os.path.join(DEMO_DIR, "constancia-demo.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "INSTITUTO NACIONAL DE EDUCACIÓN BÁSICA E INTERMEDIA")
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, "SIGA-INEBI — SISTEMA INTEGRAL DE GESTIÓN ACADÉMICA")
    c.line(72, 690, 540, 690)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 650, "CONSTANCIA DOCUMENTAL SINTÉTICA (DEMOSTRACIÓN QA)")
    c.setFont("Helvetica", 11)
    c.drawString(72, 610, "Estudiante: Ana Demo Sintética")
    c.drawString(72, 585, "Código de control: QA-DOC-001")
    c.drawString(72, 560, "Nombre de archivo: constancia-demo.pdf")
    c.drawString(72, 535, "Propósito: Documento sintético para pruebas de aseguramiento de calidad.")
    c.drawString(72, 490, "Este archivo no contiene datos personales reales ni clasificados.")
    c.drawString(72, 470, "Válido exclusivamente para pruebas de carga, consulta y verificación de hash.")
    c.line(72, 440, 540, 440)
    c.save()

    exe_path = os.path.join(DEMO_DIR, "archivo-invalido.exe")
    with open(exe_path, "wb") as f:
        f.write(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00")
        f.write(b"Archivo sintetico no permitido para prueba de validacion MIME en SIGA-INEBI.")

    oversized_path = os.path.join(DEMO_DIR, "archivo-excedido.pdf")
    with open(oversized_path, "wb") as f:
        f.write(b"%PDF-1.4\n%OVERSIZED DEMO FILE FOR QA REJECTION\n")
        chunk = b"A" * (1024 * 1024)
        for _ in range(11):
            f.write(chunk)
        f.write(b"\n%%EOF\n")

    altered_path = os.path.join(DEMO_DIR, "documento-alterado.pdf")
    with open(pdf_path, "rb") as f_orig, open(altered_path, "wb") as f_alt:
        f_alt.write(f_orig.read() + b"\n% ALTERED_BYTE_PAYLOAD_TEST\n")

    print("Archivos sintéticos generados en:", DEMO_DIR)

def generate_tts_audios():
    print("--- 2. Generando locución en español (TTS) ---")
    combined_audio = bytearray()
    results = []

    for idx, scene in enumerate(SCENES, 1):
        filename = f"{scene['id']}.mp3"
        out_path = os.path.join(AUDIO_DIR, filename)
        tts = gTTS(text=scene["text"], lang="es", tld="com.mx", slow=False)
        tts.save(out_path)

        with open(out_path, "rb") as f:
            data = f.read()
            combined_audio.extend(data)
            results.append({
                "scene_num": idx,
                "id": scene["id"],
                "title": scene["title"],
                "filename": filename,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "screen_action": scene["screen_action"]
            })

    master_path = os.path.join(AUDIO_DIR, "audio-completo-documentos-auditoria.mp3")
    with open(master_path, "wb") as f:
        f.write(combined_audio)

    manifest_path = os.path.join(AUDIO_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "master": {
                "filename": "audio-completo-documentos-auditoria.mp3",
                "size_bytes": len(combined_audio),
                "sha256": hashlib.sha256(combined_audio).hexdigest()
            },
            "scenes": results
        }, f, indent=2, ensure_ascii=False)

    print("Audio maestro y manifiesto generados en:", AUDIO_DIR)

if __name__ == "__main__":
    generate_synthetic_assets()
    generate_tts_audios()
