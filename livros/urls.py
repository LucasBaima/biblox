from django.urls import path
from . import views

app_name = "livros"

urlpatterns = [
    path("", views.home, name="home1"),
    path("cadastrar/", views.cadastrar_livro, name="cadastrar_livro"),
    path("editar/<int:id>/", views.editar_livro, name="editar_livro"),
    path("remover/<int:id>/", views.remover_livro, name="remover_livro"),

    path("emprestimos/", views.emprestimos_list, name="emprestimos_list"),
    path("emprestimos/novo/", views.registrar_emprestimo, name="registrar_emprestimo"),
    path("emprestimos/devolver/<int:pk>/", views.registrar_devolucao, name="registrar_devolucao"),

    path("reservas/", views.minhas_reservas, name="minhas_reservas"),
    path("reservas/criar/<int:livro_id>/", views.criar_reserva, name="criar_reserva"),
    path("reservas/cancelar/<int:pk>/", views.cancelar_reserva, name="cancelar_reserva"),
]
