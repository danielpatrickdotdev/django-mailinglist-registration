from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site

from mailinglist_registration import signals
from mailinglist_registration.models import RegistrationProfile
from mailinglist_registration.views import ActivationView as BaseActivationView
from mailinglist_registration.views import RegistrationView as BaseRegistrationView


class RegistrationView(BaseRegistrationView):
    """
    A registration backend which follows a simple workflow:

    1. Subscriber signs up, inactive subscription is created.

    2. Email is sent to subscriber with activation link.

    3. Subscriber clicks activation link, account is now active.

    Using this backend requires that

    * ``mailinglist_registration`` be listed in the ``INSTALLED_APPS`` setting
      (since this backend makes use of models defined in this
      application).

    * The setting ``MAILINGLIST_ACTIVATION_DAYS`` be supplied, specifying
      (as an integer) the number of days from registration during
      which a subscriber may activate their account (after that period
      expires, activation will be disallowed).

    * The creation of the templates
      ``mailinglist/activation_email_subject.txt`` and
      ``mailinglist/activation_email.txt``, which will be used for
      the activation email. See the notes for this backends
      ``register`` method for details regarding these templates.

    Additionally, registration can be temporarily closed by adding the
    setting ``REGISTRATION_OPEN`` and setting it to
    ``False``. Omitting this setting, or setting it to ``True``, will
    be interpreted as meaning that registration is currently open and
    permitted.

    Internally, this is accomplished via storing an activation key in
    an instance of ``mailinglist_registration.models.RegistrationProfile``. See
    that model and its custom manager for full documentation of its
    fields and supported operations.
    
    """
    def register(self, request, **cleaned_data):
        """
        Given an email addressregister a new subscriber, which will
        initially be inactive.

        Along with the new ``Subscriber`` object, a new
        ``mailinglist_registration.models.RegistrationProfile`` will be created,
        tied to that ``Subscriber``, containing the activation key which
        will be used for this account.

        An email will be sent to the supplied email address; this
        email should contain an activation link. The email will be
        rendered using two templates. See the documentation for
        ``RegistrationProfile.send_activation_email()`` for
        information about these templates and the contexts provided to
        them.

        After the ``Subscriber`` and ``RegistrationProfile`` are created and
        the activation email is sent, the signal
        ``mailinglist_registration.signals.subscriber_registered`` will
        be sent, with the new ``Subscriber`` as the keyword argument
        ``subscriber`` and the class of this backend as the sender.

        """
        email = cleaned_data['email']
        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(request)
        subscriber = RegistrationProfile.objects.create_inactive_subscriber(email, site)
        signals.subscriber_registered.send(sender=self.__class__,
                                     subscriber=subscriber,
                                     request=request)
        return subscriber

    def registration_allowed(self, request):
        """
        Indicate whether account registration is currently permitted,
        based on the value of the setting ``MAILINGLIST_REGISTRATION_OPEN``. This
        is determined as follows:

        * If ``MAILINGLIST_REGISTRATION_OPEN`` is not specified in settings, or is
          set to ``True``, registration is permitted.

        * If ``MAILINGLIST_REGISTRATION_OPEN`` is both specified and set to
          ``False``, registration is not permitted.
        
        """
        return getattr(settings, 'MAILINGLIST_REGISTRATION_OPEN', True)

    def get_success_url(self, request, subscriber):
        """
        Return the name of the URL to redirect to after successful
        subscriber registration.
        
        """
        return ('mailinglist_registration_complete', (), {})


class ActivationView(BaseActivationView):
    def activate(self, request, activation_key):
        """
        Given an an activation key, look up and activate the subscriber
        account corresponding to that key (if possible).

        After successful activation, the signal
        ``mailinglist_registration.signals.subscriber_activated`` will be sent, with the
        newly activated ``Subscriber`` as the keyword argument ``subscriber`` and
        the class of this backend as the sender.
        
        """
        activated_subscriber = RegistrationProfile.objects.activate_subscriber(activation_key)
        if activated_subscriber:
            signals.subscriber_activated.send(sender=self.__class__,
                                        subscriber=activated_subscriber,
                                        request=request)
        return activated_subscriber

    def get_success_url(self, request, subscriber):
        return ('mailinglist_registration_activation_complete', (), {})
