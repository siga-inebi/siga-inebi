ATOMIC_PERMISSIONS = (
    ("auth.login", "Can log in"),
    ("auth.logout", "Can log out"),
    ("account.create", "Can create accounts"),
    ("account.activate", "Can issue account activation challenges"),
    ("account.disable", "Can disable accounts"),
    ("role.assign", "Can assign roles"),
    ("scope.assign", "Can assign scopes"),
    ("student.view_basic", "Can view student basic data"),
    ("student.view_sensitive", "Can view sensitive student data"),
    ("student.edit_basic", "Can edit student basic data"),
    ("enrollment.create", "Can create enrollments"),
    ("enrollment.update", "Can update enrollments"),
    ("attendance.scan", "Can scan attendance credentials"),
    ("attendance.record_entry", "Can record attendance entries"),
    ("attendance.record_exit", "Can record attendance exits"),
    ("attendance.declared_close", "Can perform declared attendance close"),
    ("attendance.record_manual", "Can record attendance manually"),
    ("attendance.justification.request", "Can request attendance justifications"),
    ("attendance.justification.resolve", "Can resolve attendance justifications"),
    ("grade.write", "Can write grades"),
    ("grade.correct", "Can correct grades"),
    ("document.upload", "Can upload documents"),
    ("document.read", "Can read documents"),
    ("document.download", "Can download documents"),
    ("document.issue", "Can issue documents"),
    ("audit.read", "Can read audit events"),
)


def permission_codename(code):
    return code.replace(".", "_")


ATOMIC_PERMISSION_CODENAMES = tuple(permission_codename(code) for code, _name in ATOMIC_PERMISSIONS)
ATOMIC_PERMISSION_CODES_BY_CODENAME = {
    permission_codename(code): code for code, _name in ATOMIC_PERMISSIONS
}
