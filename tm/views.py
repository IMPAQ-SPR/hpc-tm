from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from models import Corpus, Document, Result

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
    if request.method == 'GET':
        if request.user.is_authenticated:
            corpora = Corpus.objects.filter(user=request.user)
            results = Result.objects.filter(corpus__in=corpora).defer("filepath")

            return render(request, 'index.html', {'corpora': corpora, 'results': results})
	
@login_required(login_url='/login')
def results(request, result_id):
    if request.method == 'GET':
        if request.user.is_authenticated:
            result = Result.objects.get(id=result_id).defer("filepath")
            if result.user == request.user:
                return render(request, 'results.html', {results: result})

def upload_corpus(request):
    if request.method == 'POST':
        pass

def analyze(request):
    if request.method == 'POST':
        pass