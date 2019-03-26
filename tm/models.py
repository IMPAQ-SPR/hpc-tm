from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Corpus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=2**7)

class Document(models.Model):
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)
    text = models.TextField(max_length=2**22)

class Result(models.Model):
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)
    filepath = models.FilePathField('/home/results_files')
    topic_num = models.PositiveIntegerField()
    name = models.CharField(max_length=2**7)

    METHODS = (
        ('LDA', 'Latent Dirichlet Allocation'),
        ('PA', 'Pachinko'),
        ('CTM', 'Correlated Topic Model')
    )
    method = models.CharField(max_length=3, choices=METHODS)