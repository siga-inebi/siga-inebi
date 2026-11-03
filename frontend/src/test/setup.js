import "@testing-library/jest-dom";
import { afterEach, vi } from "vitest";
import { cleanup, configure } from "@testing-library/react";

// Las pestañas se cargan bajo demanda (React.lazy): la primera carga de un
// chunk puede pasar del segundo por omision de findBy/waitFor cuando la suite
// completa corre con cobertura. Solo alarga la espera de lo que tarda en
// aparecer; una afirmacion que no se cumple sigue fallando.
configure({ asyncUtilTimeout: 5000 });

// Keep file previews deterministic even when Vitest exposes Node's native URL.
URL.createObjectURL = () => "blob:mock-url";
URL.revokeObjectURL = () => {};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});
