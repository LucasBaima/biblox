from django.conf import settings
from django.db import models
from django.utils import timezone

# Modelo já existente, agora com 'status' (necessário para a História 2)
class CadastroLivroModel(models.Model):
    STATUS_CHOICES = (('disponivel', 'Disponível'), ('emprestado', 'Emprestado'))

    nome = models.CharField(max_length=50)
    autor = models.CharField(max_length=50)
    isbn = models.TextField(null=True, blank=True)
    completo = models.BooleanField(default=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')  # NOVO

    def __str__(self):
        return self.nome

# História 2 — Empréstimos/Devoluções
class Emprestimo(models.Model):
    livro = models.ForeignKey(CadastroLivroModel, on_delete=models.PROTECT, related_name='emprestimos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='emprestimos')
    data_saida = models.DateField()
    data_prevista_devolucao = models.DateField()
    data_devolucao = models.DateField(null=True, blank=True)
    dias_atraso = models.IntegerField(default=0)

    class Meta:
        # Impede dois empréstimos ATIVOS (sem devolução) para o mesmo livro
        constraints = [
            models.UniqueConstraint(
                fields=['livro'],
                name='unique_livro_emprestimo_ativo',
                condition=models.Q(data_devolucao__isnull=True),
            )
        ]

    def registrar_devolucao(self, data_devolucao):
        self.data_devolucao = data_devolucao
        atraso = (self.data_devolucao - self.data_prevista_devolucao).days
        self.dias_atraso = atraso if atraso > 0 else 0
        self.save(update_fields=['data_devolucao', 'dias_atraso'])
        self.livro.status = 'disponivel'
        self.livro.save(update_fields=['status'])
        return self.dias_atraso

    

    
