export const CAMERA_ERROR = Object.freeze({
  insecure: "insecure",
  permissionDenied: "permission-denied",
  unavailable: "unavailable",
  unsupported: "unsupported",
});

export class CameraAccessError extends Error {
  constructor(code, cause) {
    super(code, { cause });
    this.name = "CameraAccessError";
    this.code = code;
  }
}

export const CAMERA_ERROR_MESSAGES = Object.freeze({
  [CAMERA_ERROR.insecure]:
    "La cámara solo está disponible desde una conexión segura (HTTPS).",
  [CAMERA_ERROR.permissionDenied]:
    "No se pudo acceder a la cámara. Habilite el permiso en el navegador y vuelva a intentarlo.",
  [CAMERA_ERROR.unavailable]:
    "No hay una cámara disponible o está siendo usada por otra aplicación.",
  [CAMERA_ERROR.unsupported]:
    "Este navegador no admite el acceso requerido a la cámara.",
});

export function stopCameraStream(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

/** Opens a camera session whose stop method deterministically releases every track. */
export async function createCameraSession() {
  if (globalThis.isSecureContext !== true) {
    throw new CameraAccessError(CAMERA_ERROR.insecure);
  }

  if (!globalThis.navigator?.mediaDevices?.getUserMedia) {
    throw new CameraAccessError(CAMERA_ERROR.unsupported);
  }

  let stream;
  try {
    stream = await globalThis.navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { facingMode: { ideal: "environment" } },
    });

    if (stream.getVideoTracks().length === 0) {
      throw new CameraAccessError(CAMERA_ERROR.unavailable);
    }

    return {
      stream,
      stop: () => stopCameraStream(stream),
    };
  } catch (error) {
    stopCameraStream(stream);
    if (error instanceof CameraAccessError) throw error;

    const code = ["NotAllowedError", "SecurityError"].includes(error?.name)
      ? CAMERA_ERROR.permissionDenied
      : CAMERA_ERROR.unavailable;
    throw new CameraAccessError(code, error);
  }
}
