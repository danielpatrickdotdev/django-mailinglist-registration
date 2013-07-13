from django.conf import settings
from django.shortcuts import redirect
from django.contrib.sites.models import RequestSite, Site
from django.contrib import messages
from django.views.generic.base import TemplateView
from mailinglist_registration import signals
from mailinglist_registration.models import RegistrationProfile, Subscriber
from mailinglist_registration.views import ActivationView as BaseActivationView
from mailinglist_registration.views import RegistrationView as BaseRegistrationView


class RegistrationView(BaseRegistrationView):

    def register(self, request, **cleaned_data):
        """
        Given an email address, register a new subscriber, which will
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
        In order to keep this backend simple, registration is always open.
        
        """
        return True

    def form_valid(self, request, form):
        new_subscriber = self.register(request, **form.cleaned_data)
        success_url = self.get_success_url(request, new_subscriber)
        messages.info(self.request,"Thanks for signing up to our updates! Please check your emails to confirm your email address.")
        
        # success_url may be a simple string, or a tuple providing the
        # full argument set for redirect(). Attempting to unpack it
        # tells us which one it is.
        try:
            to, args, kwargs = success_url
            return redirect(to, *args, **kwargs)
        except ValueError:
            return redirect(success_url)

class ActivationView(TemplateView):
    """
    Base class for subscriber activation views.
    
    """
    success_url = None
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        activated_subscriber = self.activate(request, *args, **kwargs)
        if activated_subscriber:
            messages.success(request,"Your email address has been confirmed. Thank you for subscribing to our updates!")
            success_url = self.get_success_url(request, activated_subscriber)
            try:
                to, args, kwargs = success_url
                return redirect(to, *args, **kwargs)
            except ValueError:
                return redirect(success_url)
        else:
            messages.error(request,"Hmm. Something went wrong somewhere. Maybe the activation link expired?")
            success_url = self.get_success_url(request, activated_subscriber)
            return redirect(success_url)
    
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
        return self.success_url

class DeRegistrationView(TemplateView):
    success_url = None
    
    def get(self, request, deactivation_key, *args, **kwargs):
        """
        Given an a deactivation key, look up and deactivate the subscriber
        account corresponding to that key (if possible).

        After successful deactivation, the signal
        ``mailinglist_registration.signals.subscriber_deactivated`` will be sent, with the
        email of the deactivated ``Subscriber`` as the keyword argument ``email`` and
        the class of this backend as the sender.
        
        """
        email = Subscriber.objects.deactivate_subscriber(deactivation_key)
        if email:
            signals.subscriber_deactivated.send(sender=self.__class__,
                                        email=email,
                                        request=request)
            messages.info(request,"Your email address has been removed from our mailing list.")
        else:
            messages.error(request,"Are you sure you typed that URL correctly?")
        return redirect(self.success_url)