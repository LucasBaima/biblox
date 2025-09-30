from django.urls import path
from . import views

app_name = "livros"

urlpatterns = [
    # CRUD de livros
    path("", views.home, name="home1"),
    path("cadastrar/", views.cadastrar_livro, name="cadastrar"),
    path("remover/<int:id>", views.remover_livro, name="remover"),
    path("editar/<int:id>", views.editar_livro, name="editar"),

    # Empréstimos / Devoluções (História 2)
    path("emprestimos/", views.emprestimos_list, name="emprestimos_list"),
    path("emprestimos/novo/", views.registrar_emprestimo, name="registrar_emprestimo"),
    path("emprestimos/<int:pk>/devolver/", views.registrar_devolucao, name="registrar_devolucao"),

    # Reservas (História 3)
    path("reservas/minhas/", views.minhas_reservas, name="minhas_reservas"),
    path("reservas/novo/<int:livro_id>/", views.criar_reserva, name="criar_reserva"),
    path("reservas/<int:pk>/cancelar/", views.cancelar_reserva, name="cancelar_reserva"),
]
