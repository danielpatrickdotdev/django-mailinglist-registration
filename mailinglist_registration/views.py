"""
Views which allow subscribers to create and activate accounts.

"""

from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from mailinglist_registration.models import Subscriber
from mailinglist_registration import signals
from mailinglist_registration.forms import RegistrationForm


class _RequestPassingFormView(FormView):
    """
    A version of FormView which passes extra arguments to certain
    methods, notably passing the HTTP request nearly everywhere, to
    enable finer-grained processing.
    
    """
    def get(self, request, *args, **kwargs):
        # Pass request to get_form_class and get_form for per-request
        # form control.
        form_class = self.get_form_class(request)
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        # Pass request to get_form_class and get_form for per-request
        # form control.
        form_class = self.get_form_class(request)
        form = self.get_form(form_class)
        if form.is_valid():
            # Pass request to form_valid.
            return self.form_valid(request, form)
        else:
            return self.form_invalid(form)

    def get_form_class(self, request=None):
        return super(_RequestPassingFormView, self).get_form_class()

    def get_form_kwargs(self, request=None, form_class=None):
        return super(_RequestPassingFormView, self).get_form_kwargs()

    def get_initial(self, request=None):
        return super(_RequestPassingFormView, self).get_initial()

    def get_success_url(self, request=None, subscriber=None):
        # We need to be able to use the request and the new subscriber when
        # constructing success_url.
        return super(_RequestPassingFormView, self).get_success_url()

    def form_valid(self, form, request=None):
        return super(_RequestPassingFormView, self).form_valid(form)

    def form_invalid(self, form, request=None):
        return super(_RequestPassingFormView, self).form_invalid(form)


class RegistrationView(_RequestPassingFormView):
    """
    Base class for subscriber registration views.
    
    """
    disallowed_url = 'mailinglist_registration_disallowed'
    form_class = RegistrationForm
    http_method_names = ['get', 'post', 'head', 'options', 'trace']
    success_url = None
    template_name = 'mailinglist/registration_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Check that subscriber signup is allowed before even bothering to
        dispatch or do other processing.
        
        """
        if not self.registration_allowed(request):
            return redirect(self.disallowed_url)
        return super(RegistrationView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, request, form):
        new_subscriber = self.register(request, **form.cleaned_data)
        success_url = self.get_success_url(request, new_subscriber)
        
        # success_url may be a simple string, or a tuple providing the
        # full argument set for redirect(). Attempting to unpack it
        # tells us which one it is.
        try:
            to, args, kwargs = success_url
            return redirect(to, *args, **kwargs)
        except ValueError:
            return redirect(success_url)

    def registration_allowed(self, request):
        """
        Override this to enable/disable subscriber registration, either
        globally or on a per-request basis.
        
        """
        return True

    def register(self, request, **cleaned_data):
        """
        Implement subscriber-registration logic here. Access to both the
        request and the full cleaned_data of the registration form is
        available here.
        
        """
        raise NotImplementedError
                

class ActivationView(TemplateView):
    """
    Base class for subscriber activation views.
    
    """
    http_method_names = ['get']
    template_name = 'mailinglist/activate.html'

    def get(self, request, *args, **kwargs):
        activated_subscriber = self.activate(request, *args, **kwargs)
        if activated_subscriber:
            signals.subscriber_activated.send(sender=self.__class__,
                                        subscriber=activated_subscriber,
                                        request=request)
            success_url = self.get_success_url(request, activated_subscriber)
            try:
                to, args, kwargs = success_url
                return redirect(to, *args, **kwargs)
            except ValueError:
                return redirect(success_url)
        return super(ActivationView, self).get(request, *args, **kwargs)

    def activate(self, request, *args, **kwargs):
        """
        Implement account-activation logic here.
        
        """
        raise NotImplementedError

    def get_success_url(self, request, subscriber):
        raise NotImplementedError

class DeRegistrationView(TemplateView):
    http_method_names = ['get']
    
    def get(self, request, deactivation_key, *args, **kwargs):
        subscriber = Subscriber.objects.deactivate_subscriber(deactivation_key)
        if subscriber:
            return redirect(success_url)
        return super(DeRegistrationView, self).get(request, *args, **kwargs)
