from django.conf.urls import include, url
from django.contrib import admin

from drchrono import views

admin.autodiscover()

urlpatterns = [
    url(r'^setup/$', views.SetupView.as_view(), name='setup'),
    url(r'^welcome/$', views.DoctorWelcome.as_view(), name='setup'),

    url(r'^admin/', include(admin.site.urls)),

    url(r'', include('social.apps.django_app.urls', namespace='social')),
]
