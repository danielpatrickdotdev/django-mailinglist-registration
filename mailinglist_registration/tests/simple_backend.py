from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

from mailinglist_registration.forms import RegistrationForm
from mailinglist_registration.models import Subscriber

class SimpleBackendViewTests(TestCase):
    urls = 'mailinglist_registration.backends.simple.urls'

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
        Registration creates a new subscription.

        """
        resp = self.client.post(reverse('mailinglist_registration_register'),
                                data={'email': 'bob@example.com'})
        
        subscriber = Subscriber.objects.get(email='bob@example.com')
        self.assertEqual(302, resp.status_code)
        #self.failUnless(new_user.get_absolute_url() in resp['Location'])
        
        # New user must be active.
        self.failUnless(subscriber.is_active)
        
    def test_registration_failure(self):
        """
        Registering with invalid data fails.
        
        """
        resp = self.client.post(reverse('mailinglist_registration_register'),
                                data={'email': 'bob@example'})
        self.assertEqual(200, resp.status_code)
        self.failIf(resp.context['form'].is_valid())
