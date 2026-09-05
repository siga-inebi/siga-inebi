from django.urls import path

from .views import (
    DocumentBatchCompileView,
    DocumentDeliveryReceiptCreateView,
    DocumentRecordIntegrityVerifyView,
    DocumentRecordUploadView,
    DocumentRecordVersionCreateView,
    DocumentTemplateDetailView,
    DocumentTemplateListCreateView,
    DocumentTemplatePreviewView,
    DocumentTemplateVersionListView,
    DocumentTypeListView,
    DocumentVerificationView,
    EnrolmentDocumentRecordListView,
    FieldTagListView,
    HistoricalCycleReportView,
    OfficialDocumentEligibilityView,
    ScannedDocumentUploadView,
    StorageConsumptionView,
)

urlpatterns = [
    path(
        "templates/", DocumentTemplateListCreateView.as_view(), name="document-template-list-create"
    ),
    path(
        "templates/<uuid:public_id>/",
        DocumentTemplateDetailView.as_view(),
        name="document-template-detail",
    ),
    path(
        "templates/<uuid:public_id>/versions/",
        DocumentTemplateVersionListView.as_view(),
        name="document-template-version-list",
    ),
    path(
        "templates/<uuid:public_id>/preview/",
        DocumentTemplatePreviewView.as_view(),
        name="document-template-preview",
    ),
    path("records/", DocumentRecordUploadView.as_view(), name="document-record-upload"),
    path("records/scan/", ScannedDocumentUploadView.as_view(), name="document-record-scan"),
    path(
        "storage-consumption/",
        StorageConsumptionView.as_view(),
        name="document-storage-consumption",
    ),
    path(
        "records/<uuid:public_id>/versions/",
        DocumentRecordVersionCreateView.as_view(),
        name="document-record-version-create",
    ),
    path(
        "records/<uuid:public_id>/verify/",
        DocumentRecordIntegrityVerifyView.as_view(),
        name="document-record-integrity-verify",
    ),
    path(
        "enrolments/<uuid:enrolment_id>/records/",
        EnrolmentDocumentRecordListView.as_view(),
        name="enrolment-document-record-list",
    ),
    path("field-tags/", FieldTagListView.as_view(), name="document-field-tag-list"),
    path("types/", DocumentTypeListView.as_view(), name="document-type-list"),
    path(
        "official-issuance/eligibility/",
        OfficialDocumentEligibilityView.as_view(),
        name="document-official-issuance-eligibility",
    ),
    path(
        "historical-cycle-reports/",
        HistoricalCycleReportView.as_view(),
        name="document-historical-cycle-report",
    ),
    path(
        "delivery-receipts/",
        DocumentDeliveryReceiptCreateView.as_view(),
        name="document-delivery-receipt-create",
    ),
    path(
        "official-issuance/batches/",
        DocumentBatchCompileView.as_view(),
        name="document-batch-compile",
    ),
    path(
        "verify/<str:code>/",
        DocumentVerificationView.as_view(),
        name="document-verify",
    ),
]
