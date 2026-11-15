"""HTTP routes for the Course Tuition Center MIS."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.common.views import HealthView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', HealthView.as_view(), name='health'),
    path('api/auth/', include('apps.accounts.auth_urls')),
    path('api/profile/', include('apps.accounts.profile_urls')),
    path('api/users/', include('apps.accounts.urls')),
    path('api/contracts/', include('apps.accounts.contract_urls')),
    path('api/centers/', include('apps.centers.urls')),
    path('api/settings/', include('apps.centers.settings_urls')),
    path('api/courses/', include('apps.courses.urls')),
    path('api/classes/', include('apps.classes.urls')),
    path('api/enrollments/', include('apps.enrollments.urls')),
    path('api/attendance/', include('apps.attendance.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/', include('apps.common.governance_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Course Tuition Center MIS'
admin.site.site_title = 'Tuition MIS'
