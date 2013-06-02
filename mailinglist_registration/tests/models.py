import datetime
import re

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.core import management
from django.test import TestCase
from django.utils.hashcompat import sha_constructor

from mailinglist_registration.models import RegistrationProfile
from mailinglist_registration.models import Subscriber

class RegistrationModelTests(TestCase):
    """
    Test the model and manager used in the default backend.
    
    """
    subscriber_info = {'email': 'alice@example.com'}
    
    def setUp(self):
        self.old_activation = getattr(settings, 'MAILINGLIST_ACTIVATION_DAYS', None)
        settings.MAILINGLIST_ACTIVATION_DAYS = 7

    def tearDown(self):
        settings.MAILINGLIST_ACTIVATION_DAYS = self.old_activation

    def test_profile_creation(self):
        """
        Creating a registration profile for a subscriber populates the
        profile with the correct subscriber and a SHA1 hash to use as
        activation key.
        
        """
        new_subscriber = Subscriber.objects.create_subscriber(**self.subscriber_info)
        profile = RegistrationProfile.objects.create_profile(new_subscriber)

        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(profile.subscriber.id, new_subscriber.id)
        self.failUnless(re.match('^[a-f0-9]{40}$', profile.activation_key))
        self.assertEqual(unicode(profile),
                         "Registration information for alice@example.com")

    def test_activation_email(self):
        """
        ``RegistrationProfile.send_activation_email`` sends an
        email.
        
        """
        new_subscriber = Subscriber.objects.create_subscriber(**self.subscriber_info)
        profile = RegistrationProfile.objects.create_profile(new_subscriber)
        profile.send_activation_email(Site.objects.get_current())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.subscriber_info['email']])

    def test_subscriber_creation(self):
        """
        Creating a new subscriber populates the correct data, and sets the
        subscriber's account inactive.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        self.assertEqual(new_subscriber.email, 'alice@example.com')
        self.failIf(new_subscriber.is_active)

    def test_subscriber_creation_email(self):
        """
        By default, creating a new subscriber sends an activation email.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        self.assertEqual(len(mail.outbox), 1)

    def test_subscriber_creation_no_email(self):
        """
        Passing ``send_email=False`` when creating a new subscriber will not
        send an activation email.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    send_email=False,
                                                                    **self.subscriber_info)
        self.assertEqual(len(mail.outbox), 0)

    def test_unexpired_account(self):
        """
        ``RegistrationProfile.activation_key_expired()`` is ``False``
        within the activation window.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        profile = RegistrationProfile.objects.get(subscriber=new_subscriber)
        self.failIf(profile.activation_key_expired())

    def test_expired_account(self):
        """
        ``RegistrationProfile.activation_key_expired()`` is ``True``
        outside the activation window.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        new_subscriber.date_joined -= datetime.timedelta(days=settings.MAILINGLIST_ACTIVATION_DAYS + 1)
        new_subscriber.save()
        profile = RegistrationProfile.objects.get(subscriber=new_subscriber)
        self.failUnless(profile.activation_key_expired())

    def test_valid_activation(self):
        """
        Activating a subscriber within the permitted window makes the
        account active, and resets the activation key.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        profile = RegistrationProfile.objects.get(subscriber=new_subscriber)
        activated = RegistrationProfile.objects.activate_subscriber(profile.activation_key)

        self.failUnless(isinstance(activated, Subscriber))
        self.assertEqual(activated.id, new_subscriber.id)
        self.failUnless(activated.is_active)

        profile = RegistrationProfile.objects.get(subscriber=new_subscriber)
        self.assertEqual(profile.activation_key, RegistrationProfile.ACTIVATED)

    def test_expired_activation(self):
        """
        Attempting to activate outside the permitted window does not
        activate the account.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        new_subscriber.date_joined -= datetime.timedelta(days=settings.MAILINGLIST_ACTIVATION_DAYS + 1)
        new_subscriber.save()

        profile = RegistrationProfile.objects.get(subscriber=new_subscriber)
        activated = RegistrationProfile.objects.activate_subscriber(profile.activation_key)

        self.failIf(isinstance(activated, Subscriber))
        self.failIf(activated)

        new_subscriber = Subscriber.objects.get(email='alice@example.com')
        self.failIf(new_subscriber.is_active)

        profile = RegistrationProfile.objects.get(subscriber=new_subscriber)
        self.assertNotEqual(profile.activation_key, RegistrationProfile.ACTIVATED)

    def test_activation_invalid_key(self):
        """
        Attempting to activate with a key which is not a SHA1 hash
        fails.
        
        """
        self.failIf(RegistrationProfile.objects.activate_subscriber('foo'))

    def test_activation_already_activated(self):
        """
        Attempting to re-activate an already-activated account fails.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        profile = RegistrationProfile.objects.get(subscriber=new_subscriber)
        RegistrationProfile.objects.activate_subscriber(profile.activation_key)

        profile = RegistrationProfile.objects.get(subscriber=new_subscriber)
        self.failIf(RegistrationProfile.objects.activate_subscriber(profile.activation_key))

    def test_activation_nonexistent_key(self):
        """
        Attempting to activate with a non-existent key (i.e., one not
        associated with any account) fails.
        
        """
        # Due to the way activation keys are constructed during
        # registration, this will never be a valid key.
        invalid_key = sha_constructor('foo').hexdigest()
        self.failIf(RegistrationProfile.objects.activate_subscriber(invalid_key))

    def test_expired_subscriber_deletion(self):
        """
        ``RegistrationProfile.objects.delete_expired_subscribers()`` only
        deletes inactive subscribers whose activation window has expired.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        expired_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                        email='bob@example.com')
        expired_subscriber.date_joined -= datetime.timedelta(days=settings.MAILINGLIST_ACTIVATION_DAYS + 1)
        expired_subscriber.save()

        RegistrationProfile.objects.delete_expired_subscribers()
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertRaises(Subscriber.DoesNotExist, Subscriber.objects.get, email='bob@example.com')

    def test_management_command(self):
        """
        The ``cleanupregistration`` management command properly
        deletes expired accounts.
        
        """
        new_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                    **self.subscriber_info)
        expired_subscriber = RegistrationProfile.objects.create_inactive_subscriber(site=Site.objects.get_current(),
                                                                        email='bob@example.com')
        expired_subscriber.date_joined -= datetime.timedelta(days=settings.MAILINGLIST_ACTIVATION_DAYS + 1)
        expired_subscriber.save()

        management.call_command('cleanupregistration')
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertRaises(Subscriber.DoesNotExist, Subscriber.objects.get, email='bob@example.com')
