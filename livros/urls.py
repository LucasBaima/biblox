from django.urls import path
from . import views

app_name = "livros"

urlpatterns = [
    # Catálogo (pesquisa + filtro + ordenação + paginação)
    path("", views.catalogo, name="catalogo"),                 # /livros/
    path("home/", views.home, name="home1"),                # mantém sua home antiga

    # CRUD de livros
    path("cadastrar/", views.cadastrar_livro, name="cadastrar_livro"),
    path("editar/<int:id>/", views.editar_livro, name="editar_livro"),
    path("remover/<int:id>/", views.remover_livro, name="remover_livro"),

    # Empréstimos
    path("emprestimos/", views.emprestimos_list, name="emprestimos_list"),
    path("emprestimos/novo/", views.registrar_emprestimo, name="registrar_emprestimo"),
    path("emprestimos/devolver/<int:pk>/", views.registrar_devolucao, name="registrar_devolucao"),
    path('emprestimos/meus/', views.minha_area_de_emprestimos, name='minha_area_de_emprestimos'),
    path('emprestimos/<int:emprestimo_id>/renovar/', views.solicitar_renovacao, name='solicitar_renovacao'),

    # Reservas
    path("reservas/", views.minhas_reservas, name="minhas_reservas"),
    path("reservas/criar/<int:livro_id>/", views.criar_reserva, name="criar_reserva"),
    path("reservas/cancelar/<int:pk>/", views.cancelar_reserva, name="cancelar_reserva"),
]
