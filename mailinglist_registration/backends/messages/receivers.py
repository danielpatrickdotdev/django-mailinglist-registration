from django.dispatch import receiver
from django.core.mail import mail_managers
from django.conf import settings
from mailinglist_registration.signals import subscriber_activated
from mailinglist_registration.signals import subscriber_registered
from mailinglist_registration.signals import subscriber_deactivated

@receiver(subscriber_activated)
def subscriber_activated_callback(sender, **kwargs):
    try:
        email = kwargs['subscriber'].email
    except KeyError, e:
        raise KeyError('subscriber_activated signal raised without `subscriber` in kwargs')
    mail_managers('New subscriber', '%s has just subscribed' % email)
                    

@receiver(subscriber_registered)
def subscriber_registered_callback(sender, **kwargs):
    try:
        email = kwargs['subscriber'].email
    except KeyError, e:
        raise KeyError('subscriber_registered signal raised without `subscriber` in kwargs')
    mail_managers('Confirmed subscriber', '%s has just confirmed their subscription' % email)
    

@receiver(subscriber_deactivated)
def subscriber_deactivated_callback(sender, **kwargs):
    try:
        email = kwargs['email']
    except KeyError, e:
        raise KeyError('subscriber_deactivated signal raised without `email` in kwargs')
    mail_managers('Lost subscriber', '%s has just unsubscribed' % email)
    
