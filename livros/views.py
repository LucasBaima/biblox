from django.shortcuts import render
from django.http import HttpResponse


def home(request): 
    user = {
        "user":"usuário"
    }
    return render(request, "crud/inicial.html", user)
  
def cadastrar_livro(request):
    return HttpResponse("Cadastre o seu Livro aqui")
