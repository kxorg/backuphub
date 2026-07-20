from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class SearchPageView(LoginRequiredMixin, TemplateView):
    """
    Global search page.
    GET /search/
    """
    template_name = 'search.html'