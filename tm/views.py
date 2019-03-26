from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect

def log_in(request):
    if request.method == 'GET':
        return render(request, 'login.html')

    username = request.POST['username']
    password = request.POST['password']
    next_page = request.GET.get('next', None)
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        if next_page:
            return redirect(next_page)
        else:
            return redirect('/')
    else:
        return render(request, 'login.html')

def log_out(request):
    logout(request)
    return redirect('/login')
	
@login_required(login_url='/login')
def index(request):
	pass
	
@login_required(login_url='/login')
def results(requests):
	pass