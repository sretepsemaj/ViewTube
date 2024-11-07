from django.shortcuts import render

def home(request):
    return render(request, 'home.html')  # This should render the home.html template
