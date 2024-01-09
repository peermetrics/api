from django.http import HttpResponse

from .generic_view import GenericView

class TeapotView(GenericView):

    def get(cls, request):
        return HttpResponse(content="I'm a teapot")
