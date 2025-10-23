from django.test import TestCase
from livros.models import CadastroLivroModel, Emprestimo
from datetime import date, timedelta
from django.contrib.auth import get_user_model


class CadastroLivroModelTest(TestCase):
    """Testes para o modelo CadastroLivroModel."""

    def setUp(self):
        # Cria um livro de exemplo antes de cada teste
        self.livro = CadastroLivroModel.objects.create(
            nome="A Revolução dos Bichos",
            autor="George Orwell",
            isbn="1234567890",
            completo=True
        )

    def test_criacao_livro(self):
        """Verifica se o livro foi criado corretamente no banco."""
        self.assertEqual(CadastroLivroModel.objects.count(), 1)
        self.assertEqual(self.livro.nome, "A Revolução dos Bichos")
        self.assertEqual(self.livro.autor, "George Orwell")
        self.assertTrue(self.livro.completo)

    def test_str_retorna_nome(self):
        """Verifica se o método __str__ retorna o nome do livro."""
        self.assertEqual(str(self.livro), "A Revolução dos Bichos")

    def test_status_padrao(self):
        """Verifica se o status padrão é 'disponivel'."""
        self.assertEqual(self.livro.status, "disponivel")