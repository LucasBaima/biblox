from django.urls import path
from . import views

app_name = "livros"

urlpatterns = [
    path("", views.home, name="home1"),
    path("cadastrar/", views.cadastrar_livro, name="cadastrar"),
    path("remover/<int:id>", views.remover_livro, name="remover"),
    path("editar/<int:id>", views.editar_livro, name="editar"),
    path("emprestimos/", views.emprestimos_list, name="emprestimos_list"),
    path("emprestimos/novo/", views.registrar_emprestimo, name="registrar_emprestimo"),
    path("emprestimos/<int:pk>/devolver/", views.registrar_devolucao, name="registrar_devolucao"),
]
