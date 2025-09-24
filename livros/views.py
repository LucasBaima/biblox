from django.shortcuts import render
from django.http import HttpResponse


def pag_inicial(request):
    return HttpResponse("Bem vindo a página inicial da biblox")

# Create your views here.
