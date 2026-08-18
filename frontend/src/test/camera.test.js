import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  CAMERA_ERROR,
  CameraAccessError,
  createCameraSession,
} from "@shared/platform/camera.js";

function cameraStream() {
  const videoTrack = { stop: vi.fn() };
  const audioTrack = { stop: vi.fn() };
  return {
    stream: {
      getTracks: () => [videoTrack, audioTrack],
      getVideoTracks: () => [videoTrack],
    },
    videoTrack,
    audioTrack,
  };
}

describe("camera session", () => {
  beforeEach(() => {
    vi.stubGlobal("isSecureContext", true);
  });

  test("prefers the rear camera and stops every track", async () => {
    const { stream, videoTrack, audioTrack } = cameraStream();
    const getUserMedia = vi.fn().mockResolvedValue(stream);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });

    const session = await createCameraSession();

    expect(getUserMedia).toHaveBeenCalledWith({
      audio: false,
      video: { facingMode: { ideal: "environment" } },
    });
    session.stop();
    expect(videoTrack.stop).toHaveBeenCalledOnce();
    expect(audioTrack.stop).toHaveBeenCalledOnce();
  });

  test.each([
    [false, undefined, CAMERA_ERROR.insecure],
    [true, {}, CAMERA_ERROR.unsupported],
  ])("classifies context/API support", async (secure, mediaDevices, code) => {
    vi.stubGlobal("isSecureContext", secure);
    vi.stubGlobal("navigator", { mediaDevices });

    await expect(createCameraSession()).rejects.toMatchObject({
      name: "CameraAccessError",
      code,
    });
  });

  test("classifies a rejected permission", async () => {
    const denied = new DOMException("denied", "NotAllowedError");
    vi.stubGlobal("navigator", {
      mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(denied) },
    });

    await expect(createCameraSession()).rejects.toEqual(
      expect.objectContaining({
        code: CAMERA_ERROR.permissionDenied,
        cause: denied,
      })
    );
  });

  test("stops a stream that contains no video track", async () => {
    const track = { stop: vi.fn() };
    const stream = {
      getTracks: () => [track],
      getVideoTracks: () => [],
    };
    vi.stubGlobal("navigator", {
      mediaDevices: { getUserMedia: vi.fn().mockResolvedValue(stream) },
    });

    await expect(createCameraSession()).rejects.toEqual(
      new CameraAccessError(CAMERA_ERROR.unavailable)
    );
    expect(track.stop).toHaveBeenCalledOnce();
  });
});
