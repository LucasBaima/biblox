# tests/e2e/test_renovacao_e2e.py
import re
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from livros.models import CadastroLivroModel, Emprestimo

# Transação real: LiveServer + Playwright
@pytest.mark.django_db(transaction=True)
def test_fluxo_renovacao_emprestimo(live_server, page):
    """
    Fluxo:
      1) cria user+livro+emprestimo
      2) login no /admin
      3) vai para lista de empréstimos (reverse('livros:emprestimos_list'))
      4) clica em 'Renovar' e confirma
      5) confere mensagem de sucesso
    """

    # 1) dados de teste
    usuario = User.objects.create_user(
        username="testeadmin", password="123", is_staff=True
    )
    livro = CadastroLivroModel.objects.create(
        nome="Algoritmos Biblox", autor="Cormen", isbn="123", completo=True, status="emprestado"
    )
    Emprestimo.objects.create(
        livro=livro,
        usuario=usuario,
        data_saida=timezone.now().date(),
        data_prevista_devolucao=timezone.now().date() + timedelta(days=3),
        renovacao_count=0,
    )

    base = live_server.url  # ex.: http://127.0.0.1:8081

    # 2) login no admin
    page.goto(base + "/admin/login/?next=/")
    page.fill("input[name=username]", "testeadmin")
    page.fill("input[name=password]", "123")
    page.click('input[type=submit]')
    page.wait_for_load_state("networkidle")

    # 3) ir para a lista de empréstimos usando reverse (evita hardcode de /emprestimos/ vs /livros/emprestimos/)
    lista_path = reverse("livros:emprestimos_list")  # ex.: "/livros/emprestimos/" ou "/emprestimos/"
    page.goto(base + lista_path)
    page.wait_for_load_state("networkidle")

    # Garante que o item está na página
    assert "Algoritmos Biblox" in page.content()

    # 4) clicar "Renovar"
    page.get_by_role("link", name=re.compile(r"Renovar", re.I)).first.click()

    # 5) confirmar
    page.get_by_role("button", name=re.compile(r"Confirmar", re.I)).click()

    # 6) checar mensagem de sucesso
    page.wait_for_load_state("networkidle")
    assert "Empréstimo renovado com sucesso" in page.content()
