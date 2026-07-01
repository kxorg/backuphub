from django.shortcuts import render

def index(request):
    return render(request, "index.html")


def settings(request):
    return render(request, "settings.html")

def servers(request):
    return render(request, "servers.html")

def magazineHub(request):
    return render(request, "magazineHub.html")

def api(request):
    return render(request, "api.html")