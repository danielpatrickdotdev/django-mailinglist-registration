from django.contrib import admin
from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from mailinglist_registration.models import RegistrationProfile


class RegistrationAdmin(admin.ModelAdmin):
    actions = ['activate_users', 'resend_activation_email']
    list_display = ('subscriber', 'activation_key_expired')
    raw_id_fields = ['subscriber']
    search_fields = ('subscriber_email',)

    def activate_subscribers(self, request, queryset):
        """
        Activates the selected subscribers, if they are not alrady
        activated.
        
        """
        for profile in queryset:
            RegistrationProfile.objects.activate_subscriber(profile.activation_key)
    activate_subscribers.short_description = _("Activate subscribers")

    def resend_activation_email(self, request, queryset):
        """
        Re-sends activation emails for the selected subscribers.

        Note that this will *only* send activation emails for subscribers
        who are eligible to activate; emails will not be sent to subscribers
        whose activation keys have expired or who have already
        activated.
        
        """
        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(request)

        for profile in queryset:
            if not profile.activation_key_expired():
                profile.send_activation_email(site)
    resend_activation_email.short_description = _("Re-send activation emails")


admin.site.register(RegistrationProfile, RegistrationAdmin)
