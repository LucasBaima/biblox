# tests/e2e/test_registro_emprestimo_e2e.py
import re
import pytest
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.urls import reverse
from livros.models import CadastroLivroModel

@pytest.mark.django_db(transaction=True)
def test_fluxo_registrar_emprestimo(live_server, page):
    admin = User.objects.create_user(username="admin2", password="123", is_staff=True)
    livro = CadastroLivroModel.objects.create(
        nome="Design Patterns", autor="GoF", isbn="222", completo=True, status="disponivel"
    )

    base = live_server.url

    # Login admin
    page.goto(base + "/admin/login/?next=/")
    page.fill("input[name=username]", "admin2")
    page.fill("input[name=password]", "123")
    page.click('input[type=submit]')
    page.wait_for_load_state("networkidle")

    # Ir para a tela de novo empréstimo
    novo_path = reverse("livros:registrar_emprestimo")
    page.goto(base + novo_path)
    page.wait_for_load_state("networkidle")

    # ---------- Seletores robustos (selects) ----------
    # Livro: #livro, name=livro_id ou name=livro
    livro_select = None
    for sel in ['select#livro', 'select[name="livro_id"]', 'select[name="livro"]']:
        if page.locator(sel).count():
            livro_select = sel
            break
    assert livro_select, "Não encontrei o select do Livro (#livro, name=livro_id, name=livro)."

    # Usuário: #usuario, name=usuario_id ou name=usuario
    user_select = None
    for sel in ['select#usuario', 'select[name="usuario_id"]', 'select[name="usuario"]']:
        if page.locator(sel).count():
            user_select = sel
            break
    assert user_select, "Não encontrei o select do Usuário (#usuario, name=usuario_id, name=usuario)."

    # Selecione por VALUE (id) — mais confiável
    page.select_option(livro_select, value=str(livro.id))
    try:
        page.select_option(user_select, value=str(admin.id))
    except Exception:
        page.select_option(user_select, label=admin.username)

    # ---------- Datas: preenche de forma inteligente ----------
    hoje = date.today()
    prevista = hoje + timedelta(days=7)
    iso_hoje = hoje.isoformat()          # YYYY-MM-DD
    iso_prevista = prevista.isoformat()  # YYYY-MM-DD

    # 1) nomes comuns
    if page.locator('input[name="data_saida"]').count():
        page.fill('input[name="data_saida"]', iso_hoje)
    if page.locator('input[name="data_prevista_devolucao"]').count():
        page.fill('input[name="data_prevista_devolucao"]', iso_prevista)

    # 2) fallback: se não tiver name explícito, preenche todos os type=date
    dates = page.locator('input[type="date"]')
    qtd = dates.count()
    if qtd == 1:
        # se houver só 1 campo, costuma ser a data prevista
        dates.nth(0).fill(iso_prevista)
    elif qtd >= 2:
        # primeiro = saída, segundo = prevista (padrão de muitos forms)
        dates.nth(0).fill(iso_hoje)
        dates.nth(1).fill(iso_prevista)

    page.wait_for_timeout(200)  # pequeno respiro para o navegador aplicar o valor

    # Enviar o formulário
    page.get_by_role("button", name=re.compile(r"(Registrar|Salvar|Criar)", re.I)).click()
    page.wait_for_load_state("networkidle")

    # Se houver erro de validação, mostre um trecho da página para depurar
    if page.locator(".alert.error, .errorlist li, .error, [role='alert']").count():
        raise AssertionError("Formulário de empréstimo apresentou erro.\nTrecho da página:\n" + page.content()[:1200])

    # Verificar na lista
    lista_path = reverse("livros:emprestimos_list")
    page.goto(base + lista_path)
    page.wait_for_load_state("networkidle")
    content = page.content()

    assert "Design Patterns" in content
    assert re.search(r"(Pendente|Emprestad|Empréstim)", content, re.I)
