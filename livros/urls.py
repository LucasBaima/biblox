from django.urls import path
from . import views


app_name = "livros"    #namespace para que o nome das rotas sejam reconhecidas"


urlpatterns = [
    path("", views.home, name="home1"),
    path("cadastrar/", views.cadastrar_livro, name="cadastrar"), #Rota passada para o html dentro da tag
    path("remover/<int:id>", views.remover_livro, name="remover"),   #<int:id>  Informar qual item queremos remover .. id -> campo no banco de dados que representa o item
    path("editar/<int:id>", views.editar_livro, name="editar"),
    path("registrar/<int:id>", views.registrar_livro, name="registrar_livro") 
]

