import re
import pytest
from django.contrib.auth.models import User
from django.urls import reverse

@pytest.mark.django_db(transaction=True)
def test_fluxo_cadastrar_livro(live_server, page):
    admin = User.objects.create_user(username="admin3", password="123", is_staff=True)
    base = live_server.url

    # Login admin
    page.goto(base + "/admin/login/?next=/")
    page.fill("input[name=username]", "admin3")
    page.fill("input[name=password]", "123")
    page.click('input[type=submit]')
    page.wait_for_load_state("networkidle")

    # Ir para tela de cadastro
    cadastrar_path = reverse("livros:cadastrar_livro")
    page.goto(base + cadastrar_path)
    page.wait_for_load_state("networkidle")

    # Preencher o formulário usando os rótulos visíveis (get_by_label é mais estável)
    page.get_by_label(re.compile(r"^Nome$", re.I)).fill("Refactoring")
    page.get_by_label(re.compile(r"^Autor$", re.I)).fill("Fowler")

    # ISBN é uma área de texto na sua tela → use o label
    if page.get_by_label(re.compile(r"^ISBN$", re.I)).count():
        page.get_by_label(re.compile(r"^ISBN$", re.I)).fill("333")

    # Checkbox "Edição integral" (opcional)
    if page.get_by_label(re.compile(r"Edição integral", re.I)).count():
        page.get_by_label(re.compile(r"Edição integral", re.I)).check()

    # Salvar
    page.get_by_role("button", name=re.compile(r"(Salvar|Cadastrar|Criar)", re.I)).click()
    page.wait_for_load_state("networkidle")

    # Confirmar que o livro foi cadastrado (na própria tela ou no catálogo)
    content = page.content()
    if "Refactoring" not in content:
        page.goto(base + reverse("livros:catalogo"))
        page.wait_for_load_state("networkidle")
        content = page.content()

    assert "Refactoring" in content
