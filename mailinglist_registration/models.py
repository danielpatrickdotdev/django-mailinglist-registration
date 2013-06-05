import datetime
import hashlib
import random
import re

from django.utils import timezone
from django.conf import settings
from django.db import models
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

try:
    from django.utils.timezone import now as datetime_now
except ImportError:
    datetime_now = datetime.datetime.now


SHA1_RE = re.compile('^[a-f0-9]{40}$')


class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_subscriber(self, activation_key):
        """
        Validate an activation key and activate the corresponding
        ``Subscriber`` if valid.
        
        If the key is valid and has not expired, return the ``Subscriber``
        after activating.
        
        If the key is not valid or has expired, return ``False``.
        
        If the key is valid but the ``Subscriber`` is already active,
        return ``False``.
        
        To prevent reactivation of an account which has been
        deactivated by site administrators, the activation key is
        reset to the string constant ``RegistrationProfile.ACTIVATED``
        after successful activation.

        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not profile.activation_key_expired():
                subscriber = profile.subscriber
                subscriber.is_active = True
                subscriber.deactivation_key = profile.activation_key
                subscriber.save()
                profile.activation_key = self.model.ACTIVATED
                profile.save()
                return subscriber
        return False
    
    def create_inactive_subscriber(self, email, site, send_email=True):
        """
        Create a new, inactive ``Subscriber``, generate a
        ``RegistrationProfile`` and email its activation key to the
        ``Subscriber``, returning the new ``Subscriber``.

        By default, an activation email will be sent to the new
        subscriber. To disable this, pass ``send_email=False``.
        
        """
        new_subscriber = Subscriber.objects.create_subscriber(email)
        new_subscriber.is_active = False
        new_subscriber.save()

        registration_profile = self.create_profile(new_subscriber)

        if send_email:
            registration_profile.send_activation_email(site)

        return new_subscriber
    create_inactive_subscriber = transaction.commit_on_success(create_inactive_subscriber)

    def create_profile(self, subscriber):
        """
        Create a ``RegistrationProfile`` for a given
        ``Subscriber``, and return the ``RegistrationProfile``.
        
        The activation key for the ``RegistrationProfile`` will be a
        SHA1 hash, generated from a combination of the ``Subscriber``'s
        email address and a random salt.
        
        """
        salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
        email = subscriber.email
        if isinstance(email, unicode):
            email = email.encode('utf-8')
        activation_key = hashlib.sha1(salt+email).hexdigest()
        return self.create(subscriber=subscriber,
                           activation_key=activation_key)
        
    def delete_expired_subscribers(self):
        """
        Remove expired instances of ``RegistrationProfile`` and their
        associated ``Subscriber``s.
        
        Accounts to be deleted are identified by searching for
        instances of ``RegistrationProfile`` with expired activation
        keys, and then checking to see if their associated ``Subscriber``
        instances have the field ``is_active`` set to ``False``; any
        ``Subscriber`` who is both inactive and has an expired
        activation key will be deleted.
        
        It is recommended that this method be executed regularly as
        part of your routine site maintenance; this application
        provides a custom management command which will call this
        method, accessible as ``manage.py cleanupregistration``.
        
        Regularly clearing out accounts which have never been
        activated alleviates the ocasional need to reset a
        ``RegistrationProfile`` and/or re-send an activation email
        when a subscriber does not receive or does not act upon the
        initial activation email; since the account will be
        deleted, the subscriber will be able to simply re-register
        and receive a new activation key.
        
        If you have a ``Subscriber`` for whom you wish to disable
        their account while keeping it in the database, simply delete
        the associated ``RegistrationProfile``; an inactive
        ``Subscriber`` which does not have an associated
        ``RegistrationProfile`` will not be deleted.
        
        """
        for profile in self.all():
            try:
                if profile.activation_key_expired():
                    subscriber = profile.subscriber
                    if not subscriber.is_active:
                        subscriber.delete()
                        profile.delete()
            except Subscriber.DoesNotExist:
                profile.delete()

class SubscriberManager(models.Manager):

    @classmethod
    def normalize_email(cls, email):
        """
        Normalize the address by lowercasing the domain part of the email
        address.
        """
        email = email or ''
        try:
            email_name, domain_part = email.strip().rsplit('@', 1)
        except ValueError:
            pass
        else:
            email = '@'.join([email_name, domain_part.lower()])
        return email

    def deactivate_subscriber(self, deactivation_key):
        """
        Delete subscriber (and registration profile)

        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(deactivation_key):
            try:
                subscriber = self.get(deactivation_key=deactivation_key)
            except self.model.DoesNotExist:
                return False
            try:
                profile = RegistrationProfile.objects.get(subscriber=subscriber)
            except RegistrationProfile.DoesNotExist:
                pass
            profile.delete()
            subscriber.delete()
            return True
        return False

    def create_subscriber(self, email, **extra_fields):
        """
        Creates and saves a Subscriber with the given email address.
        """
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        subscriber = self.model(email=email, is_active=True,
                                date_joined=now, **extra_fields)
        subscriber.save(using=self._db)
        return subscriber

class Subscriber(models.Model):
    email = models.EmailField(_('email address'), max_length=254, blank=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    
    is_active = models.BooleanField(_('active'), default=True,
        help_text=_('Designates whether this subscriber should receive '
                    'emails. Unselect this instead of deleting accounts.'))
    deactivation_key = models.CharField(_('deactivation key'), max_length=40)
    
    objects = SubscriberManager()
    
    def __str__(self):
        return self.email
    
    def email_subscriber(self, subject, message, from_email=None):
        """
        Sends an email to this Subscriber.
        """
        send_mail(subject, message, from_email, [self.email])

class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during
    mailinglist registration.
    
    Generally, you will not want to interact directly with instances
    of this model; the provided manager includes methods
    for creating and activating new accounts, as well as for cleaning
    out accounts which have never been activated.
    
    This model's sole purpose is to store data temporarily during
    account registration and activation.
    
    """
    ACTIVATED = u"ALREADY_ACTIVATED"
    
    subscriber = models.ForeignKey(Subscriber, unique=True, verbose_name=_('subscriber'))
    activation_key = models.CharField(_('activation key'), max_length=40)
    
    objects = RegistrationManager()
    
    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')
    
    def __unicode__(self):
        return u"Registration information for %s" % self.subscriber
    
    def activation_key_expired(self):
        """
        Determine whether this ``RegistrationProfile``'s activation
        key has expired, returning a boolean -- ``True`` if the key
        has expired.
        
        Key expiration is determined by a two-step process:
        
        1. If the email address has already activated, the key will have
           been reset to the string constant ``ACTIVATED``. Re-activating
           is not permitted, and so this method returns ``True`` in
           this case.

        2. Otherwise, the date the email address was signed up is
           incremented by the number of days specified in the setting
           ``MAILINGLIST_ACTIVATION_DAYS`` (which should be the number of
           days after signup during which a subscriber is allowed to
           activate their account); if the result is less than or
           equal to the current date, the key has expired and this
           method returns ``True``.
        
        """
        expiration_date = datetime.timedelta(days=settings.MAILINGLIST_ACTIVATION_DAYS)
        return self.activation_key == self.ACTIVATED or \
               (self.subscriber.date_joined + expiration_date <= datetime_now())
    activation_key_expired.boolean = True

    def send_activation_email(self, site):
        """
        Send an activation email to the subscriber associated with this
        ``RegistrationProfile``.
        
        The activation email will make use of two templates:

        ``mailinglist/activation_email_subject.txt``
            This template will be used for the subject line of the
            email. Because it is used as the subject line of an email,
            this template's output **must** be only a single line of
            text; output longer than one line will be forcibly joined
            into only a single line.

        ``mailinglist/activation_email.txt``
            This template will be used for the body of the email.

        These templates will each receive the following context
        variables:

        ``activation_key``
            The activation key for the new account.

        ``expiration_days``
            The number of days remaining during which the account may
            be activated.

        ``site``
            An object representing the site on which the subscriber
            registered; depending on whether ``django.contrib.sites``
            is installed, this may be an instance of either
            ``django.contrib.sites.models.Site`` (if the sites
            application is installed) or
            ``django.contrib.sites.models.RequestSite`` (if
            not). Consult the documentation for the Django sites
            framework for details regarding these objects' interfaces.

        """
        ctx_dict = {'activation_key': self.activation_key,
                    'expiration_days': settings.MAILINGLIST_ACTIVATION_DAYS,
                    'site': site}
        subject = render_to_string('mailinglist/activation_email_subject.txt',
                                   ctx_dict)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        
        message = render_to_string('mailinglist/activation_email.txt',
                                   ctx_dict)
        
        self.subscriber.email_subscriber(subject, message, settings.DEFAULT_FROM_EMAIL)
    
