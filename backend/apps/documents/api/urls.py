from django.urls import path

from .views import (
    DocumentDeliveryReceiptCreateView,
    DocumentRecordIntegrityVerifyView,
    DocumentRecordUploadView,
    DocumentRecordVersionCreateView,
    DocumentTemplateDetailView,
    DocumentTemplateListCreateView,
    DocumentTemplatePreviewView,
    DocumentTemplateVersionListView,
    DocumentTypeListView,
    EnrolmentDocumentRecordListView,
    FieldTagListView,
    OfficialDocumentEligibilityView,
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
        "delivery-receipts/",
        DocumentDeliveryReceiptCreateView.as_view(),
        name="document-delivery-receipt-create",
    ),
]
