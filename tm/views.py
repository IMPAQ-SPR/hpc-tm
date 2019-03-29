from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from tm.models import Corpus, Document, Result, ResultTopic, ResultTopicWord, ResultDocumentTopic
from zipfile import ZipFile
from django.conf import settings
from tm.InstanceManager import InstanceManager
import os
import json
import numpy as np
import time
from worker import conn
from rq import Queue
from background_task import background

q = Queue(connection=conn)

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
            result = Result.objects.get(id=result_id)
            if result.corpus.user == request.user:
                topic_dist = []
                topics = ResultTopic.objects.filter(result__id=result_id).order_by('-average_likelihood')
                for topic in topics:
                    td = {}
                    td['id'] = topic.id
                    td['name'] = topic.name
                    td['average_likelihood'] = float(topic.average_likelihood)
                    top_words = ResultTopicWord.objects.filter(topic=topic).order_by('-probability')
                    td['top_words'] = list(top_words.values_list('word', flat=True))
                    td['top_word_values'] = [float(val) * 100 for val in top_words.values_list('probability', flat=True)]
                    top_documents = ResultDocumentTopic.objects.filter(topic=topic).order_by('-probability')[:20]
                    td['top_documents'] = list(top_documents.values_list('document_id', flat=True))
                    topic_dist.append(td)

                documents = Document.objects.filter(corpus=result.corpus)[:50].values_list('id', flat=True)

                return render(request, 'results.html', {'topics': json.dumps(topic_dist), 'documents': list(documents)})

@csrf_protect
def upload_corpus(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            corpus_name = request.POST.get('corpus-name-input')
            corpus = Corpus.objects.create(user=request.user, name=corpus_name)

            files = request.FILES.getlist('corpus-files-input')

            corpus_directory = os.path.join(settings.BASE_DIR, 'corpus_files')
            if not os.path.exists(corpus_directory):
                os.mkdir(corpus_directory)
            
            corpus_directory = os.path.join(corpus_directory, str(corpus.id))
            if not os.path.exists(corpus_directory):
                os.mkdir(corpus_directory)

            corpus_path = os.path.join(corpus_directory, 'corpus.zip')
            with ZipFile(corpus_path, 'x') as corpus_zip:
                for f in files:
                    document_text = f.read()
                    document = Document.objects.create(corpus=corpus, text=document_text)

                    corpus_zip.writestr('{}.txt'.format(document.id), document_text)

            return redirect('/')

@background(schedule=5)
def run_aws_analysis(corpus_id, topic_num, analysis_name):
    print('Starting manager')

    corpus = Corpus.objects.get(id=corpus_id)
    pem_file = os.path.join(settings.BASE_DIR, 'MyKeyPair.pem')
    if not os.path.isfile(pem_file):
        key_pair = os.environ['KEY_PAIR']

        with open(pem_file, 'w') as key_pair_file:
            key_pair_file.write(key_pair)

    manager = InstanceManager('MyKeyPair', pem_file, environment_configuration=True, instance_type='c5.9xlarge')
    print('Creating instances')
    instances = manager.create_instances(wait_for_running=True)
    time.sleep(10)
    print('Connecting to instances')
    manager.connect_to_instances()

    print('Installing dependencies')
    manager.execute_command('pip install python-magic')
    manager.execute_command('pip install spacy')
    manager.execute_command('python -m spacy download en')
    manager.execute_command('pip install gensim')

    corpus_directory = os.path.join(settings.BASE_DIR, 'corpus_files', str(corpus.id))
    print('Uploading necessary files')
    manager.upload_file_to_instance(os.path.join(corpus_directory, 'corpus.zip'), '/home/ubuntu/corpus.zip')
    manager.execute_command('mkdir corpus')
    time.sleep(2)
    manager.execute_command('unzip corpus.zip -d corpus/')
    manager.upload_file_to_instance(os.path.join(settings.BASE_DIR, 'Belair-Text-Experiments.zip'), '/home/ubuntu/Belair-Text-Experiments.zip')
    manager.execute_command('unzip Belair-Text-Experiments.zip')
    time.sleep(2)
    manager.execute_command('mv Belair-Text-Experiments/* /home/ubuntu')
    time.sleep(2)
    manager.execute_command('mv corpora/arxiv/build-corpus.py /home/ubuntu')
    time.sleep(2)
    manager.upload_file_to_instance(os.path.join(settings.BASE_DIR, 'tm', 'ldamulticore.py'), '/home/ubuntu/ldamulticore.py')
    
    print('Creating mm and dictionary files')
    manager.execute_command('python build-corpus.py -p -d 25000 -o /home/ubuntu/corpus /home/ubuntu/corpus')
    print('Running analysis')
    manager.execute_command('export HOSTNAME="ubuntu"; python ldamulticore.py -w 35 -t {} --dict corpus.mm.dictionary.cpickle -n results corpus.mm'.format(topic_num))

    print('Downloading result files')
    manager.download_file_from_instance('/home/ubuntu/corpus.mm', os.path.join(corpus_directory, 'corpus.mm'), instance=instances[0])
    manager.download_file_from_instance('/home/ubuntu/corpus.mm.dictionary.cpickle', os.path.join(corpus_directory, 'corpus.mm.dictionary.cpickle'), instance=instances[0])
    manager.download_file_from_instance('/home/ubuntu/results', os.path.join(corpus_directory, 'results'), instance=instances[0])
    manager.download_file_from_instance('/home/ubuntu/topics.json', os.path.join(corpus_directory, 'topics.json'), instance=instances[0])
    manager.download_file_from_instance('/home/ubuntu/document_topics.npy', os.path.join(corpus_directory, 'document_topics.npy'), instance=instances[0])

    manager.terminate_instances()

    corpus.mm_filepath = os.path.join(str(corpus.id), 'corpus.mm')
    corpus.dictionary_file_path = os.path.join(str(corpus.id), 'corpus.mm.dictionary.cpickle')
    corpus.save()
    result = Result.objects.create(corpus=corpus, topic_num=topic_num, filepath=os.path.join(str(corpus.id), 'results'), name=analysis_name)

    corpus_directory = os.path.join(settings.BASE_DIR, 'corpus_files', str(corpus.id))
    with open(os.path.join(corpus_directory, 'topics.json')) as topics_file:
        topic_words = json.load(topics_file)
    
    documents = Document.objects.filter(corpus=corpus).order_by('id')
    document_topics = np.load(os.path.join(corpus_directory, 'document_topics.npy'))

    for i in range(len(topic_words)):
        topic_name = ', '.join([w[0] for w in topic_words[i]['top_words'][:3]])
        topic = ResultTopic.objects.create(result=result, name=topic_name, average_likelihood=topic_words[i]['average_likelihood'])

        for word in topic_words[i]['top_words']:
            ResultTopicWord.objects.create(topic=topic, word=word[0], probability=word[1])

        for j in range(document_topics.shape[0]):
            if document_topics[j][i] != 0:
                ResultDocumentTopic.objects.create(document=documents[j], topic=topic, probability=document_topics[j][i])

@csrf_protect
def analyze(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            corpus_id = request.POST.get('corpus_id')
            topic_num = request.POST.get('topic_num')
            analysis_name = request.POST.get('analysis_name')
            corpus = Corpus.objects.get(id=corpus_id)

            print('Running analysis on corpus', corpus_id)

            if corpus.user == request.user:
                # q.enqueue(run_aws_analysis, corpus, topic_num)
                run_aws_analysis(corpus_id, topic_num, analysis_name)

                return JsonResponse('Running analysis')

@csrf_protect
def get_document_info(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            document_id = request.POST.get('document_id')
            result_id = request.POST.get('result_id')
            document = Document.objects.get(id=document_id)
            result = Result.objects.get(id=result_id)

            if document.corpus.user == request.user:
                document_dict = {'id': document.id, 'text': document.text[2:-1]}
                print(document.text[:100])

                document_topics = ResultDocumentTopic.objects.filter(document=document, topic__result=result).order_by('-probability')
                document_dict['topics'] = [{'topic_id': dt.topic_id, 'probability': float(dt.probability), 'topic_name': dt.topic.name} for dt in document_topics]

                return JsonResponse(document_dict)

@csrf_protect
def get_topic_documents(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            topic_id = request.POST.get('topic_id')
            topic = ResultTopic.objects.get(id=topic_id)

            if topic.result.corpus.user == request.user:
                documents = list(ResultDocumentTopic.objects.filter(topic=topic).values_list('document_id', flat=True))

                return JsonResponse({'data': documents})

@csrf_protect
def search_keyword(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            result_id = request.POST.get('result_id')
            keyword = request.POST.get('keyword')
            result = Result.objects.get(id=result_id)
            
            if result.corpus.user == request.user:
                documents = list(Document.objects.filter(corpus=result.corpus, text__contains=keyword)[:50].values_list('id', flat=True))

                return JsonResponse({'data': documents})
