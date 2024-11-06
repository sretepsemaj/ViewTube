from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to the Viewer Home Page")

def example_view(request):
    return HttpResponse("This is an example view in Viewer")
