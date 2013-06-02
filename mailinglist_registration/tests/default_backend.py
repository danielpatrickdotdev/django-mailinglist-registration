import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from mailinglist_registration import signals
from mailinglist_registration.admin import RegistrationAdmin
from mailinglist_registration.forms import RegistrationForm
from mailinglist_registration.backends.default.views import RegistrationView
from mailinglist_registration.models import RegistrationProfile, Subscriber

class DefaultBackendViewTests(TestCase):
    """
    Test the default registration backend.

    Running these tests successfully will require two templates to be
    created for the sending of activation emails; details on these
    templates and their contexts may be found in the documentation for
    the default backend.

    """
    urls = 'mailinglist_registration.backends.default.urls'

    def setUp(self):
        """
        Create an instance of the default backend for use in testing,
        and set ``MAILINGLIST_ACTIVATION_DAYS`` if it's not set already.

        """
        self.old_activation = getattr(settings, 'MAILINGLIST_ACTIVATION_DAYS', None)
        if self.old_activation is None:
            settings.MAILINGLIST_ACTIVATION_DAYS = 7 # pragma: no cover

    def tearDown(self):
        """
        Yank ``MAILINGLIST_ACTIVATION_DAYS`` back out if it wasn't
        originally set.

        """
        if self.old_activation is None:
            settings.MAILINGLIST_ACTIVATION_DAYS = self.old_activation # pragma: no cover

    def test_allow(self):
        """
        The setting ``MAILINGLIST_REGISTRATION_OPEN`` appropriately controls
        whether registration is permitted.

        """
        old_allowed = getattr(settings, 'MAILINGLIST_REGISTRATION_OPEN', True)
        settings.MAILINGLIST_REGISTRATION_OPEN = True

        resp = self.client.get(reverse('mailinglist_registration_register'))
        self.assertEqual(200, resp.status_code)

        settings.MAILINGLIST_REGISTRATION_OPEN = False

        # Now all attempts to hit the register view should redirect to
        # the 'registration is closed' message.
        resp = self.client.get(reverse('mailinglist_registration_register'))
        self.assertRedirects(resp, reverse('mailinglist_registration_disallowed'))
        
        resp = self.client.post(reverse('mailinglist_registration_register'),
                                data={'email': 'bob@example.com'})
        self.assertRedirects(resp, reverse('mailinglist_registration_disallowed'))

        settings.MAILINGLIST_REGISTRATION_OPEN = old_allowed

    def test_registration_get(self):
        """
        HTTP ``GET`` to the registration view uses the appropriate
        template and populates a registration form into the context.
        
        """
        resp = self.client.get(reverse('mailinglist_registration_register'))
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp,
                                'mailinglist/registration_form.html')
        self.failUnless(isinstance(resp.context['form'],
                        RegistrationForm))

    def test_registration(self):
        """
        Registration creates a new inactive account and a new profile
        with activation key, populates the correct account data and
        sends an activation email.

        """
        resp = self.client.post(reverse('mailinglist_registration_register'),
                                data={'email': 'bob@example.com'})
        self.assertRedirects(resp, reverse('mailinglist_registration_complete'))

        new_subscriber = Subscriber.objects.get(email='bob@example.com')
        
        self.assertEqual(new_subscriber.email, 'bob@example.com')
        
        # New subscriber must not be active.
        self.failIf(new_subscriber.is_active)
        
        # A registration profile was created, and an activation email
        # was sent.
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_no_sites(self):
        """
        Registration still functions properly when
        ``django.contrib.sites`` is not installed; the fallback will
        be a ``RequestSite`` instance.
        
        """
        Site._meta.installed = False

        resp = self.client.post(reverse('mailinglist_registration_register'),
                                data={'email': 'bob@example.com'})
        self.assertEqual(302, resp.status_code)

        new_subscriber = Subscriber.objects.get(email='bob@example.com')

        self.assertEqual(new_subscriber.email, 'bob@example.com')

        self.failIf(new_subscriber.is_active)
        
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

        Site._meta.installed = True

    def test_registration_failure(self):
        """
        Registering with invalid data fails.
        
        """
        resp = self.client.post(reverse('mailinglist_registration_register'),
                                data={'email': 'bob@example.'})
        self.assertEqual(200, resp.status_code)
        self.failIf(resp.context['form'].is_valid())
        self.assertEqual(0, len(mail.outbox))

    def test_activation(self):
        """
        Activation of an account functions properly.
        
        """
        resp = self.client.post(reverse('mailinglist_registration_register'),
                                data={'email': 'bob@example.com'})

        profile = RegistrationProfile.objects.get(subscriber__email='bob@example.com')

        resp = self.client.get(reverse('mailinglist_registration_activate',
                                       args=(),
                                       kwargs={'activation_key': profile.activation_key}))
        self.assertRedirects(resp, reverse('mailinglist_registration_activation_complete'))

    def test_activation_expired(self):
        """
        An expired account can't be activated.
        
        """
        resp = self.client.post(reverse('mailinglist_registration_register'),
                                data={'email': 'bob@example.com'})

        profile = RegistrationProfile.objects.get(subscriber__email='bob@example.com')
        subscriber = profile.subscriber
        subscriber.date_joined -= datetime.timedelta(days=settings.MAILINGLIST_ACTIVATION_DAYS)
        subscriber.save()

        resp = self.client.get(reverse('mailinglist_registration_activate',
                                       args=(),
                                       kwargs={'activation_key': profile.activation_key}))

        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, 'mailinglist/activate.html')
        self.assertEqual(profile.activation_key,
                         resp.context['activation_key'])
