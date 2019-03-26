from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Corpus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class Document(models.Model):
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)
    text = models.TextField(max_length=2**20)

class Result(models.Model):
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)
    filepath = models.FilePathField('/home/results_files')