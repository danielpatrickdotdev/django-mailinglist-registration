"""
URLconf for registration and activation, using django-registration's
default backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^mailinglist/', include('mailinglist_registration.backends.default.urls')),

If you'd like to customize registration behavior, feel free to set up
your own URL patterns for these views instead.

"""


from django.conf.urls import patterns
from django.conf.urls import include
from django.conf.urls import url
from django.views.generic.base import TemplateView

from mailinglist_registration.backends.default.views import ActivationView
from mailinglist_registration.backends.default.views import RegistrationView


urlpatterns = patterns('',
                       url(r'^confirm/complete/$',
                           TemplateView.as_view(template_name='mailinglist/activation_complete.html'),
                           name='mailinglist_registration_activation_complete'),
                       # Activation keys get matched by \w+ instead of the more specific
                       # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
                       # that way it can return a sensible "invalid key" message instead of a
                       # confusing 404.
                       url(r'^confirm/(?P<activation_key>\w+)/$',
                           ActivationView.as_view(),
                           name='mailinglist_registration_activate'),
                       url(r'^signup/$',
                           RegistrationView.as_view(),
                           name='mailinglist_registration_register'),
                       url(r'^signup/complete/$',
                           TemplateView.as_view(template_name='mailinglist/registration_complete.html'),
                           name='mailinglist_registration_complete'),
                       url(r'^closed/$',
                           TemplateView.as_view(template_name='mailinglist/registration_closed.html'),
                           name='mailinglist_registration_disallowed'),
                       )
