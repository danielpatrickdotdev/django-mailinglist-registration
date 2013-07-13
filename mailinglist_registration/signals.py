from django.dispatch import Signal


# A new subscriber has registered.
subscriber_registered = Signal(providing_args=["subscriber", "request"])

# A subscriber has activated his or her subscription.
subscriber_activated = Signal(providing_args=["subscriber", "request"])

# A subscriber has delete his or her subscription.
subscriber_deactivated = Signal(providing_args=["subscriber", "request"])