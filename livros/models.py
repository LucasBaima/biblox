from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

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
# EMPRÉSTIMO (História 2 + História 6)
# ----------------------------
class Emprestimo(models.Model):
    livro = models.ForeignKey(CadastroLivroModel, on_delete=models.PROTECT, related_name='emprestimos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='emprestimos')
    
    # Datas
    data_saida = models.DateField(default=timezone.now)
    data_prevista_devolucao = models.DateField()
    data_devolucao = models.DateField(null=True, blank=True)

    # Renovação
    renovacao_count = models.PositiveSmallIntegerField(default=0)

    # 🔥 Multas
    multa_valor = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    multa_paga = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['livro'],
                name='unique_livro_emprestimo_ativo',
                condition=models.Q(data_devolucao__isnull=True),
            )
        ]

    # ----------------------------
    # PROPRIEDADES
    # ----------------------------
    @property
    def dias_atraso(self):
        hoje = timezone.now().date()

        if self.data_devolucao:
            dias = (self.data_devolucao - self.data_prevista_devolucao).days
        elif self.data_prevista_devolucao < hoje:
            dias = (hoje - self.data_prevista_devolucao).days
        else:
            return 0
        
        return max(0, dias)

    @property
    def is_active(self):
        return self.data_devolucao is None

    # ----------------------------
    # RENOVAÇÃO
    # ----------------------------
    def pode_renovar(self, max_renovacoes=1):
        if not self.is_active:
            return False, "O empréstimo já foi devolvido."
        
        if self.dias_atraso > 0:
            return False, "O empréstimo está atrasado e não pode ser renovado."
        
        if self.renovacao_count >= max_renovacoes:
            return False, f"O limite de {max_renovacoes} renovação(ões) foi atingido."
        
        return True, "Pode ser renovado."

    def aplicar_renovacao(self, periodo_dias=7):
        pode, motivo = self.pode_renovar()
        if not pode:
            raise Exception(f"Não foi possível renovar: {motivo}")

        self.data_prevista_devolucao += timedelta(days=periodo_dias)
        self.renovacao_count += 1
        self.save(update_fields=['data_prevista_devolucao', 'renovacao_count'])
        return self.data_prevista_devolucao

    # ----------------------------
    # MULTAS (História 6)
    # ----------------------------
    def calcular_multa(self, valor_por_dia=2.00, carencia=0):
        """
        Qualquer atraso ≥ 1 dia gera multa.
        carencia=0 garante que seus testes funcionem com 3 dias.
        """

        atraso = self.dias_atraso

        if atraso > carencia:
            dias_cobrados = atraso - carencia
            multa = dias_cobrados * valor_por_dia

            self.multa_valor = multa
            self.multa_paga = False
            self.save(update_fields=['multa_valor', 'multa_paga'])
            return multa

        # sem multa
        self.multa_valor = 0
        self.multa_paga = True
        self.save(update_fields=['multa_valor', 'multa_paga'])
        return 0

    def quitar_multa(self):
        self.multa_paga = True
        self.save(update_fields=['multa_paga'])

    # ----------------------------
    # DEVOLUÇÃO
    # ----------------------------
    def registrar_devolucao(self, data_devolucao):
        from .models import Reserva  

        self.data_devolucao = data_devolucao
        self.save(update_fields=['data_devolucao'])

        # Calcula multa automaticamente
        self.calcular_multa()

        # livro volta a ficar disponível
        self.livro.status = 'disponivel'
        self.livro.save(update_fields=['status'])

        # regras de reserva
        Reserva.expirar_vencidas()
        Reserva.promover_primeira(self.livro)

        return self.dias_atraso


# ----------------------------
# RESERVA (História 3)
# ----------------------------
class Reserva(models.Model):
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
        constraints = [
            models.UniqueConstraint(
                fields=['livro', 'usuario'],
                name='unique_reserva_ativa_por_usuario',
                condition=models.Q(status__in=['ativa', 'pronta']),
            )
        ]

    def __str__(self):
        return f'Reserva {self.pk} - {self.livro} - {self.usuario} ({self.status})'

    @staticmethod
    def _prazo_retirada_dias():
        return 2

    @classmethod
    def primeira_na_fila(cls, livro):
        return cls.objects.filter(livro=livro, status='ativa').order_by('criada_em').first()

    @classmethod
    def promover_primeira(cls, livro):
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
        agora = timezone.now()
        vencidas = list(cls.objects.filter(status='pronta', expira_em__lt=agora))
        for r in vencidas:
            r.status = 'expirada'
            r.expirada_em = agora
            r.save(update_fields=['status', 'expirada_em'])
            cls.promover_primeira(r.livro)

    def cancelar(self):
        self.status = 'cancelada'
        self.cancelada_em = timezone.now()
        self.save(update_fields=['status', 'cancelada_em'])
        if self.status == 'pronta':
            type(self).promover_primeira(self.livro)

    def concluir(self):
        self.status = 'concluida'
        self.concluida_em = timezone.now()
        self.save(update_fields=['status', 'concluida_em'])
