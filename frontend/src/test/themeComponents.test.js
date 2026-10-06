import { describe, expect, it } from "vitest";

import { MuiTooltip } from "@theme/components/MuiSurfaces.js";

describe("MuiTooltip", () => {
  it("usa el color de superficie como texto sobre el fondo de texto", () => {
    const theme = {
      vars: {
        palette: {
          background: { paper: "var(--mui-palette-background-paper)" },
          text: { primary: "var(--mui-palette-text-primary)" },
        },
      },
    };

    const styles = MuiTooltip.styleOverrides.tooltip({ theme });

    expect(styles).toMatchObject({
      backgroundColor: "var(--mui-palette-text-primary)",
      color: "var(--mui-palette-background-paper)",
    });
  });
});
