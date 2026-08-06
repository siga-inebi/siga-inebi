export const anaGuardianOption = {
  public_id: "guardian-ana",
  person: { public_id: "person-ana", first_name: "Ana", last_name: "Gomez" },
};

export const carlosGuardianOption = {
  public_id: "guardian-carlos",
  person: {
    public_id: "person-carlos",
    first_name: "Carlos",
    last_name: "Lopez",
  },
};

export const auntContact = {
  public_id: "contact-1",
  student: { public_id: "student-1", student_code: "STU-0001" },
  name: "Maria Perez",
  phone_number: "555-0123",
  relationship_label: "Tia",
  is_active: true,
};

export const inactiveContact = {
  public_id: "contact-2",
  student: { public_id: "student-1", student_code: "STU-0001" },
  name: "Jose Ramirez",
  phone_number: "555-0199",
  relationship_label: "Tio",
  is_active: false,
};

export const primaryRelation = {
  public_id: "relation-1",
  student: { public_id: "student-1", student_code: "STU-0001" },
  guardian: anaGuardianOption,
  relationship_label: "Madre",
  is_primary: true,
  starts_at: "2026-01-01",
  ends_at: null,
};

export const endedRelation = {
  public_id: "relation-2",
  student: { public_id: "student-1", student_code: "STU-0001" },
  guardian: carlosGuardianOption,
  relationship_label: "Padre",
  is_primary: false,
  starts_at: "2025-01-01",
  ends_at: "2025-12-31",
};
