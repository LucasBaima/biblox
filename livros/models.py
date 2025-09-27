from django.db import models

# Create your models here.. classes que serão traduzidas em modelos no banco de dados
class CadastroLivroModel(models.Model):   
    nome = models.CharField(max_length=50)
    autor = models.CharField(max_length=50)
    isbn = models.TextField(null=True, blank=True)
    completo = models.BooleanField(default=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    
    def __str__(self):
        return self.nome
    
    # -> Se tivermos uma instância dessa classe.. essa funcão vai retornar o nome do livro
    

    
