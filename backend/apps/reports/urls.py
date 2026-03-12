from django.urls import path

from .views import ReportSummaryView

urlpatterns = [
    path("", ReportSummaryView.as_view(), name="report-summary"),
]
