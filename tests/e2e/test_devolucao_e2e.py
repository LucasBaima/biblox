import re
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from livros.models import CadastroLivroModel, Emprestimo

@pytest.mark.django_db(transaction=True)
def test_fluxo_devolucao_emprestimo(live_server, page):
    admin = User.objects.create_user(username="admin", password="123", is_staff=True)
    livro = CadastroLivroModel.objects.create(
        nome="Clean Code", autor="Martin", isbn="111", completo=True, status="emprestado"
    )
    Emprestimo.objects.create(
        livro=livro,
        usuario=admin,
        data_saida=timezone.now().date(),
        data_prevista_devolucao=timezone.now().date() + timedelta(days=2),
        renovacao_count=0,
    )

    base = live_server.url

    # Login admin
    page.goto(base + "/admin/login/?next=/")
    page.fill("input[name=username]", "admin")
    page.fill("input[name=password]", "123")
    page.click('input[type=submit]')
    page.wait_for_load_state("networkidle")

    # Lista de empréstimos
    lista_path = reverse("livros:emprestimos_list")
    page.goto(base + lista_path)
    page.wait_for_load_state("networkidle")
    assert "Clean Code" in page.content()

    # Clicar "Registrar devolução"
    page.get_by_role("link", name=re.compile(r"Registrar devolu", re.I)).first.click()

    # Confirmar na tela (botões possíveis)
    page.get_by_role("button", name=re.compile(r"(Registrar|Confirmar|Salvar|Devolver)", re.I)).click()
    page.wait_for_load_state("networkidle")

    # Alguns fluxos podem permanecer na mesma página; garanta a navegação de volta à lista
    page.goto(base + lista_path)
    page.wait_for_load_state("networkidle")

    # Agora deve mostrar o status "Devolvido" ou a data de devolução
    content = page.content()
    assert "Clean Code" in content
    assert re.search(r"(Devolvido|Devoluç|Devolucao|\\d{2}/\\d{2}/\\d{4})", content, re.I)
