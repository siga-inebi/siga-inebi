import { useCallback } from "react";
import Typography from "@mui/material/Typography";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { studentsService } from "./studentsService.js";
import { StudentRecordList } from "./StudentRecordList.jsx";

export function StudentGuardianRelations({ studentPublicId }) {
  const load = useCallback(
    ({ page }) =>
      studentsService.listGuardianRelations(studentPublicId, { page }),
    [studentPublicId]
  );
  const list = usePaginatedList(load, { canIncludeInactive: false });

  return (
    <StudentRecordList
      emptyMessage="Sin encargados vinculados"
      list={list}
      renderItem={(relation) => (
        <>
          <Typography fontWeight={600} variant="body2">
            {relation.guardian_detail.person.first_name}{" "}
            {relation.guardian_detail.person.last_name}
          </Typography>
          <Typography color="text.secondary" variant="body2">
            {relation.relationship_label}
            {relation.is_primary ? " · Principal" : ""}
            {relation.ends_at ? " · Finalizado" : ""}
          </Typography>
        </>
      )}
    />
  );
}
