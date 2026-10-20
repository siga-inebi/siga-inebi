/** Orden por nombre o código, ascendente y descendente. */
export const NAME_CODE_ORDERING = [
  { value: "name", label: "Nombre (A–Z)" },
  { value: "-name", label: "Nombre (Z–A)" },
  { value: "code", label: "Código (A–Z)" },
  { value: "-code", label: "Código (Z–A)" },
];

/** Niveles y grados: orden pedagógico primero. */
export const SEQUENCE_ORDERING = [
  { value: "sequence", label: "Orden pedagógico" },
  ...NAME_CODE_ORDERING,
];
