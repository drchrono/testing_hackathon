from django.conf.urls import include, url
from django.contrib import admin

from drchrono import views

admin.autodiscover()

urlpatterns = [
    url(r'^setup/$', views.SetupView.as_view(), name='setup'),
    url(r'^welcome/$', views.DoctorWelcome.as_view(), name='welcome'),
    url(r'^toggle-timer/$', views.VisitTimerView.as_view(), name='timer'),
    url(r'^check-in/$', views.CheckInView.as_view(), name='check-in'),
    url(r'^demographics/$', views.DemographicView.as_view(), name='demographics'),
    url(r'^finished/$', views.KioskEndView.as_view(), name='kiosk-end'),
    url(r'^admin/', admin.site.urls),
    url(r'', include('social.apps.django_app.urls', namespace='social')),
]
