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
