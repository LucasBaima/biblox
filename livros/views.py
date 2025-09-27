from django.shortcuts import render, redirect
from .forms import CadastroForm #-> Importação do nosso formulário
from django.http import HttpRequest


def home(request): 
    user = {
        "user":"usuário"
    }
    return render(request, "crud/inicial.html", user)
  
def cadastrar_livro(request:HttpRequest):
    if request.method == "POST":
        formular = CadastroForm(request.POST) #Criando uma instância do nosso formulário que contenha as informações que enviamos p ele
        if formular.is_valid():
            formular.save()  #Salvar as informações no banco de dados
            return redirect("livros:home1") #redirecionamento para a rota home
    
    formulario = {
        "form":CadastroForm   #passando o formulario diretamente pro html
    }
    return render(request, 'crud/cadastrar.html', formulario)   #renderizar o conteúdo do arquivo cadastrar.html
