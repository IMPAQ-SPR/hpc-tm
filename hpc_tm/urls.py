"""hpc_tm URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from tm import views

urlpatterns = [
	path('', views.index, name='index'),
    path('login/', views.log_in, name='login'),
    path('logout/', views.log_out, name='logout'),
    path('results/<int:result_id>', views.results, name='results'),
    path('upload_corpus/', views.upload_corpus, name='upload_corpus'),
    path('analyze/', views.analyze, name='analyze'),
    path('document_info/', views.get_document_info, name='get_document_info'),
    path('topic_documents/', views.get_topic_documents, name='get_topic_documents'),
    path('search_keyword/', views.search_keyword, name='search_keyword')
]
