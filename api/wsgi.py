"""
WSGI config for rtcapi project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# TODO: when implementing opentelemetry, we need to start with this
# from opentelemetry import trace
# from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor

# from opentelemetry.instrumentation.django import DjangoInstrumentor

# tracer_provider = TracerProvider()
# cloud_trace_exporter = CloudTraceSpanExporter()
# tracer_provider.add_span_processor(
#     # BatchSpanProcessor buffers spans and sends them in batches in a
#     # background thread. The default parameters are sensible, but can be
#     # tweaked to optimize your performance
#     BatchSpanProcessor(cloud_trace_exporter)
# )
# trace.set_tracer_provider(tracer_provider)

# tracer = trace.get_tracer(__name__)

# # DjangoInstrumentor().instrument()
# # end opentelemetry setup

application = get_wsgi_application()
