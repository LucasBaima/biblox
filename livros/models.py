from django.conf import settings
from django.db import models
from django.utils import timezone

# ----------------------------
# LIVRO
# ----------------------------
class CadastroLivroModel(models.Model):
    STATUS_CHOICES = (('disponivel', 'Disponível'), ('emprestado', 'Emprestado'))

    nome = models.CharField(max_length=50)
    autor = models.CharField(max_length=50)
    isbn = models.TextField(null=True, blank=True)
    completo = models.BooleanField(default=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')

    def __str__(self):
        return self.nome


# ----------------------------
# EMPRÉSTIMO (História 2)
# ----------------------------
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
        from .models import Reserva  # import tardio para evitar ciclos
        self.data_devolucao = data_devolucao
        atraso = (self.data_devolucao - self.data_prevista_devolucao).days
        self.dias_atraso = atraso if atraso > 0 else 0
        self.save(update_fields=['data_devolucao', 'dias_atraso'])

        # livro volta a ficar "disponível"
        self.livro.status = 'disponivel'
        self.livro.save(update_fields=['status'])

        # após devolução: expira reservas vencidas e promove a primeira da fila
        Reserva.expirar_vencidas()
        Reserva.promover_primeira(self.livro)
        return self.dias_atraso


# ----------------------------
# RESERVA (História 3)
# ----------------------------
class Reserva(models.Model):
    """
    Fila de reservas por livro.
    status:
      - 'ativa'   : na fila aguardando devolução
      - 'pronta'  : disponível para retirada (primeiro da fila)
      - 'cancelada'
      - 'expirada'
      - 'concluida' : reserva usada para efetivar um empréstimo
    """
    STATUS_CHOICES = (
        ('ativa', 'Ativa'),
        ('pronta', 'Disponível para retirada'),
        ('cancelada', 'Cancelada'),
        ('expirada', 'Expirada'),
        ('concluida', 'Concluída'),
    )

    livro = models.ForeignKey(CadastroLivroModel, on_delete=models.PROTECT, related_name='reservas')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativa')

    criada_em = models.DateTimeField(auto_now_add=True)
    pronta_em = models.DateTimeField(null=True, blank=True)
    expira_em = models.DateTimeField(null=True, blank=True)
    cancelada_em = models.DateTimeField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    expirada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['criada_em']
        # Evita reservas duplicadas do MESMO usuário para o MESMO livro,
        # enquanto estiver 'ativa' ou 'pronta'
        constraints = [
            models.UniqueConstraint(
                fields=['livro', 'usuario'],
                name='unique_reserva_ativa_por_usuario',
                condition=models.Q(status__in=['ativa', 'pronta']),
            )
        ]

    def __str__(self):
        return f'Reserva {self.pk} - {self.livro} - {self.usuario} ({self.status})'

    # ---------- Regras de negócio auxiliares ----------

    @staticmethod
    def _prazo_retirada_dias():
        # você pode mover isso para settings.py como RESERVA_PRAZO_RETIRADA_DIAS
        return 2  # ex.: 2 dias para retirada

    @classmethod
    def primeira_na_fila(cls, livro):
        return cls.objects.filter(livro=livro, status='ativa').order_by('criada_em').first()

    @classmethod
    def promover_primeira(cls, livro):
        """
        Marca a primeira 'ativa' como 'pronta' (disponível para retirada) e
        define prazo de expiração.
        Retorna a reserva promovida ou None.
        """
        res = cls.primeira_na_fila(livro)
        if not res:
            return None
        agora = timezone.now()
        res.status = 'pronta'
        res.pronta_em = agora
        res.expira_em = agora + timezone.timedelta(days=cls._prazo_retirada_dias())
        res.save(update_fields=['status', 'pronta_em', 'expira_em'])
        return res

    @classmethod
    def expirar_vencidas(cls):
        """
        Expira todas as reservas 'pronta' cujo prazo passou.
        Após expirar, tenta promover a próxima da fila daquele livro.
        """
        agora = timezone.now()
        vencidas = list(cls.objects.filter(status='pronta', expira_em__lt=agora))
        for r in vencidas:
            r.status = 'expirada'
            r.expirada_em = agora
            r.save(update_fields=['status', 'expirada_em'])
            # promove a próxima da fila para esse mesmo livro
            cls.promover_primeira(r.livro)

    def cancelar(self):
        self.status = 'cancelada'
        self.cancelada_em = timezone.now()
        self.save(update_fields=['status', 'cancelada_em'])
        # se a cancelada era 'pronta', promove próxima
        if self.status == 'pronta':
            type(self).promover_primeira(self.livro)

    def concluir(self):
        """Quando a reserva é efetivamente usada em um empréstimo."""
        self.status = 'concluida'
        self.concluida_em = timezone.now()
        self.save(update_fields=['status', 'concluida_em'])
