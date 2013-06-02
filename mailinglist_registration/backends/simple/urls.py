"""
URLconf for registration and activation, using django-registration's
one-step backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^mailinglist/', include('mailinglist_registration.backends.simple.urls')),

If you'd like to customize registration behavior, feel free to set up
your own URL patterns for these views instead.

"""

from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url
from django.views.generic.base import TemplateView

from mailinglist_registration.backends.simple.views import RegistrationView


urlpatterns = patterns('',
                       url(r'^register/$',
                           RegistrationView.as_view(),
                           name='mailinglist_registration_register'),
                       url(r'^register/closed/$',
                           TemplateView.as_view(template_name='mailinglist/registration_closed.html'),
                           name='mailinglist_registration_disallowed'),
                       url(r'^confirmed/$', TemplateView.as_view(template_name='mailinglist/registration_complete.html'),
                           name='mailinglist_registration_confirmed'),
                       )
