from django.test import TestCase
from django.urls import reverse

# Verifique se o caminho de importação (livros.models) está correto
from livros.models import CadastroLivroModel 


class HomeViewTest(TestCase):

    def setUp(self):
        # Cria alguns livros no banco de teste
        self.livro1 = CadastroLivroModel.objects.create(
            nome="Dom Casmurro", 
            autor="Machado de Assis"
        )
        self.livro2 = CadastroLivroModel.objects.create(
            nome="1984", 
            autor="George Orwell"
        )

    def test_status_code_ok(self):
        url = reverse("livros:home1") # usa o nome da URL que você colocou no redirect()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_template_usado(self):
        url = reverse("livros:home1")
        response = self.client.get(url)
        self.assertTemplateUsed(response, "crud/inicial.html")

    def test_livros_aparecem_no_contexto(self):
        url = reverse("livros:home1")
        response = self.client.get(url)
        
        registros = response.context["registros"]
        
        self.assertIn(self.livro1, registros)
        self.assertIn(self.livro2, registros)