from django.urls import path
from . import views


app_name = "livros"    #namespace para que o nome das rotas sejam reconhecidas"


urlpatterns = [
    path("", views.home),
    path("cadastrar/", views.cadastrar_livro, name="cadastrar") #Rota passada para o html dentro da tag
]