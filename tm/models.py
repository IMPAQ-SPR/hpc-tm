from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Corpus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=2**7)
    mm_filepath = models.FilePathField('/corpus_files', null=True)
    dictionary_file_path = models.FilePathField('/corpus_files', null=True)

class Document(models.Model):
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)
    text = models.TextField(max_length=2**22)

class Result(models.Model):
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)
    filepath = models.FilePathField('/corpus_files/results_files')
    topic_num = models.PositiveIntegerField()
    name = models.CharField(max_length=2**7)

    METHODS = (
        ('LDA', 'Latent Dirichlet Allocation'),
        ('PA', 'Pachinko'),
        ('CTM', 'Correlated Topic Model')
    )
    method = models.CharField(max_length=3, choices=METHODS)

class ResultTopic(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE)
    name = models.CharField(max_length=2**7)
    average_likelihood = models.DecimalField(max_digits=10, decimal_places=9)

class ResultTopicWord(models.Model):
    topic = models.ForeignKey(ResultTopic, on_delete=models.CASCADE)
    word = models.CharField(max_length=2**7)
    probability = models.DecimalField(max_digits=10, decimal_places=9)

class ResultDocumentTopic(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    topic = models.ForeignKey(ResultTopic, on_delete=models.CASCADE)
    probability = models.DecimalField(max_digits=10, decimal_places=9)