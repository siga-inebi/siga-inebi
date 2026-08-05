// `SECTION_OPTIONS` is still used by PadresPage.jsx's filter dropdown.
// The Alumnos page itself now reads real data from `studentsService`
// (backed by `/api/v1/students/`) instead of a mock array.

const GRADES = ["1ro", "2do", "3ro"];
const SECTION_LETTERS = ["A", "B", "C"];

export const SECTION_OPTIONS = GRADES.flatMap((grade) =>
  SECTION_LETTERS.map((letter) => `${grade} "${letter}"`)
);
