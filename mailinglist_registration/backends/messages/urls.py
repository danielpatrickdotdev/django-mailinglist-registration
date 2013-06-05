from django.conf.urls import patterns, include, url
from django.conf import settings
from mailinglist_registration.backends.messages.views import RegistrationView, ActivationView, DeRegistrationView

urlpatterns = patterns('',
    url(r'^$', RegistrationView.as_view(template_name='index.html', success_url='/'),
        name="index"),
    url(r'^confirm/(?P<activation_key>\w+)/$',
        ActivationView.as_view(success_url='/'),
        name="mailinglist_registration_activate"),
    url(r'^unsubscribe/(?P<deactivation_key>\w+)/$',
        DeRegistrationView.as_view(success_url='/'),
        name="mailinglist_registration_deregister")
)