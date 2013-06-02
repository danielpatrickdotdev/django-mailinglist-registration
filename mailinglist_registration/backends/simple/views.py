from django.conf import settings
from django.core.urlresolvers import reverse_lazy as reverse

from mailinglist_registration.models import Subscriber
from mailinglist_registration import signals
from mailinglist_registration.views import RegistrationView as BaseRegistrationView


class RegistrationView(BaseRegistrationView):
    """
    A registration backend which implements the simplest possible
    workflow: a subscriber supplies an email address and is immediately
    signed up.
    
    """
    success_url = reverse('mailinglist_registration_confirmed')
    
    def register(self, request, **cleaned_data):
        email = cleaned_data['email']
        subscriber = Subscriber.objects.create_subscriber(email)
        signals.subscriber_registered.send(sender=self.__class__,
                                     subscriber=subscriber,
                                     request=request)
        return subscriber

    def registration_allowed(self, request):
        """
        Indicate whether mailinglist registration is currently permitted,
        based on the value of the setting ``MAILINGLIST_REGISTRATION_OPEN``. This
        is determined as follows:

        * If ``MAILINGLIST_REGISTRATION_OPEN`` is not specified in settings, or is
          set to ``True``, registration is permitted.

        * If ``MAILINGLIST_REGISTRATION_OPEN`` is both specified and set to
          ``False``, registration is not permitted.
        
        """
        return getattr(settings, 'MAILINGLIST_REGISTRATION_OPEN', True)

    def get_success_url(self, request, subscriber):
        return self.success_url
