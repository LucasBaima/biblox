import re
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from livros.models import CadastroLivroModel

@pytest.mark.django_db(transaction=True)
def test_pesquisa_e_filtro_de_livros(live_server, page):
    """
    Testa a busca no catálogo tentando automaticamente seletores comuns de campo de pesquisa.
    """
    # Dados
    admin = User.objects.create_user(username="pesquisador", password="123", is_staff=True)
    CadastroLivroModel.objects.create(nome="Python para Todos", autor="Mark Lutz", completo=True)
    CadastroLivroModel.objects.create(nome="Java Essencial", autor="Deitel", completo=True)

    base = live_server.url

    # Login (rápido via admin)
    page.goto(base + "/admin/login/?next=/")
    page.fill("input[name=username]", "pesquisador")
    page.fill("input[name=password]", "123")
    page.click('input[type=submit]')
    page.wait_for_load_state("networkidle")

    # Acessar catálogo
    catalogo_path = reverse("livros:catalogo")
    page.goto(base + catalogo_path)
    page.wait_for_load_state("networkidle")

    # ---------- Seleção robusta do campo de busca ----------
    # Tentamos em ordem: placeholder, type=search, name=q, name=search, id=busca, input[type=text]
    candidatos = [
        '[placeholder*="esquis"]',      # "Pesquisar..." / "Pesquisa" (case-insensitive via * e acentos variam)
        'input[type="search"]',
        'input[name="q"]',
        'input[name="search"]',
        '#busca',
        '#search',
        'input[type="text"]',
        'input[name="termo"]',
    ]

    campo = None
    for sel in candidatos:
        if page.locator(sel).count():
            campo = sel
            break

    assert campo is not None, "Não encontrei o campo de busca no catálogo. Ajuste o seletor no teste."

    # Digitar termo e enviar
    page.fill(campo, "Python")
    # Se tiver botão de buscar, tentamos clicar; senão, usamos Enter
    if page.get_by_role("button", name=re.compile(r"(Buscar|Pesquisar|Filtrar|OK)", re.I)).count():
        page.get_by_role("button", name=re.compile(r"(Buscar|Pesquisar|Filtrar|OK)", re.I)).click()
    else:
        page.keyboard.press("Enter")

    page.wait_for_timeout(800)

    # Conferir resultado: deve aparecer Python e não Java
    content = page.content()
    assert "Python para Todos" in content
    assert "Java Essencial" not in content

    # (Opcional) se existir filtro por status
    if page.locator("select[name='status']").count():
        page.select_option("select[name='status']", "disponivel")
        page.wait_for_timeout(500)
        assert "Python para Todos" in page.content()
