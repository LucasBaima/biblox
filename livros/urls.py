from django.urls import path
from . import views

app_name = "livros"

urlpatterns = [
    # Catálogo
    path("", views.catalogo, name="catalogo"),
    path("home/", views.home, name="home1"),

    # CRUD de livros
    path("cadastrar/", views.cadastrar_livro, name="cadastrar_livro"),
    path("editar/<int:id>/", views.editar_livro, name="editar_livro"),
    path("remover/<int:id>/", views.remover_livro, name="remover_livro"),

    # Empréstimos
    path("emprestimos/", views.emprestimos_list, name="emprestimos_list"),
    path("emprestimos/novo/", views.registrar_emprestimo, name="registrar_emprestimo"),
    path("emprestimos/devolver/<int:pk>/", views.registrar_devolucao, name="registrar_devolucao"),
    path("emprestimos/quitar/<int:pk>/", views.quitar_multa, name="quitar_multa"),  # 🔥 NOVA ROTA DA HISTÓRIA 6
    path('emprestimos/meus/', views.minha_area_de_emprestimos, name='minha_area_de_emprestimos'),
    path('emprestimos/<int:emprestimo_id>/renovar/', views.solicitar_renovacao, name='solicitar_renovacao'),

    # Reservas
    path("reservas/", views.minhas_reservas, name="minhas_reservas"),
    path("reservas/criar/<int:livro_id>/", views.criar_reserva, name="criar_reserva"),
    path("reservas/cancelar/<int:pk>/", views.cancelar_reserva, name="cancelar_reserva"),
    # RELATÓRIOS
    path("relatorios/circulacao/", views.relatorio_circulacao, name="relatorio_circulacao"),
    path("relatorios/circulacao/exportar/csv/", views.exportar_relatorio_csv, name="exportar_relatorio_csv"),
    path("relatorios/circulacao/exportar/pdf/", views.exportar_relatorio_pdf, name="exportar_relatorio_pdf"),

]
