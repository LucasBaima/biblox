from django.contrib import admin
from .models import CadastroLivroModel, Emprestimo

@admin.register(CadastroLivroModel)
class CadastroLivroAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "autor", "status", "data_criacao")
    list_filter = ("status",)
    search_fields = ("nome", "autor", "isbn")

@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ("id", "livro", "usuario", "data_saida",
                    "data_prevista_devolucao", "data_devolucao", "dias_atraso")
    search_fields = ("livro__nome", "usuario__username")
    list_filter = ("data_devolucao",)
