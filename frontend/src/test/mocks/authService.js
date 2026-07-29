import { vi } from "vitest";

import { anonymousSession } from "../fixtures/auth";

export const authServiceMock = {
  me: vi.fn().mockResolvedValue(anonymousSession),
  login: vi.fn(),
  logout: vi.fn(),
  csrf: vi.fn(),
};
