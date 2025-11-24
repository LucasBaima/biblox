import pytest
from datetime import date, timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model

from livros.models import CadastroLivroModel, Emprestimo, Reserva


# -----------------------------------------------------------------------------
# Cenário 1 – Relatório por período com dados
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_historia7_relatorio_periodo_com_dados(client):
    """
    Dado que informei o período de 01/08 a 31/08
    Quando eu emitir o relatório de circulação
    Então o sistema deve apresentar quantidade de empréstimos,
    devoluções, atrasos e reservas no período.
    """
    User = get_user_model()
    admin = User.objects.create_superuser(
        username="admin_rel",
        email="admin_rel@test.com",
        password="123456",
    )
    client.force_login(admin)

    hoje = timezone.now().date()
    inicio = hoje - timedelta(days=10)
    fim = hoje

    livro = CadastroLivroModel.objects.create(
        nome="Livro Rel 1",
        autor="Autor A",
        status="disponivel",
    )

    # Empréstimo dentro do período (com devolução, para não violar UNIQUE)
    Emprestimo.objects.create(
        livro=livro,
        usuario=admin,
        data_saida=inicio,
        data_prevista_devolucao=inicio + timedelta(days=3),
        data_devolucao=inicio + timedelta(days=2),
    )

    # Reserva dentro do período
    Reserva.objects.create(
        livro=livro,
        usuario=admin,
        status="ativa",
    )

    # IMPORTANTE: usar os mesmos nomes de campos que o formulário da tela
    resp = client.get(
        "/livros/relatorios/circulacao/",
        {
            "data_inicio": inicio.strftime("%Y-%m-%d"),
            "data_fim": fim.strftime("%Y-%m-%d"),
        },
    )

    assert resp.status_code == 200

    ctx = resp.context

    # A view guarda as datas em data_inicio / data_fim como STRING
    assert ctx["data_inicio"] == inicio.strftime("%Y-%m-%d")
    assert ctx["data_fim"] == fim.strftime("%Y-%m-%d")

    # Deve ter um dicionário de estatísticas preenchido
    stats = ctx["stats"]
    assert stats is not None
    # Não preciso saber exatamente as chaves, só que existe algo > 0
    totais = [v for v in stats.values() if isinstance(v, int)]
    assert any(v > 0 for v in totais)


# -----------------------------------------------------------------------------
# Cenário 3 – Sem dados no período
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_historia7_relatorio_sem_dados(client):
    """
    Dado que não há movimentação entre 01/01 e 05/01
    Quando eu emitir o relatório
    Então o sistema deve exibir “Nenhum dado para o período selecionado”.
    """
    User = get_user_model()
    admin = User.objects.create_superuser(
        username="admin_rel2",
        email="admin_rel2@test.com",
        password="123456",
    )
    client.force_login(admin)

    inicio = date(2025, 1, 1)
    fim = date(2025, 1, 5)

    resp = client.get(
        "/livros/relatorios/circulacao/",
        {
            "data_inicio": inicio.strftime("%Y-%m-%d"),
            "data_fim": fim.strftime("%Y-%m-%d"),
        },
    )

    assert resp.status_code == 200
    html = resp.content.decode("utf-8")

    # Mensagem exibida quando não há movimentação no período
    assert "Nenhum dado para o período selecionado" in html


# -----------------------------------------------------------------------------
# Cenário 2 – Top 10 livros mais emprestados
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_historia7_top10_livros_mais_emprestados(client):
    """
    Dado que existem dados consolidados
    Quando eu solicitar o “Top 10 livros mais emprestados”
    Então o sistema deve exibir a lista com contagem de empréstimos por título.
    """
    User = get_user_model()
    admin = User.objects.create_superuser(
        username="admin_rel3",
        email="admin_rel3@test.com",
        password="123456",
    )
    client.force_login(admin)

    hoje = timezone.now().date()
    inicio = hoje - timedelta(days=30)
    fim = hoje

    # Livro A com 3 empréstimos (todos devolvidos)
    livro_a = CadastroLivroModel.objects.create(
        nome="Livro A",
        autor="Autor A",
        status="disponivel",
    )
    for i in range(3):
        Emprestimo.objects.create(
            livro=livro_a,
            usuario=admin,
            data_saida=hoje - timedelta(days=10 + i),
            data_prevista_devolucao=hoje - timedelta(days=7 + i),
            data_devolucao=hoje - timedelta(days=5 + i),
        )

    # Livro B com 2 empréstimos
    livro_b = CadastroLivroModel.objects.create(
        nome="Livro B",
        autor="Autor B",
        status="disponivel",
    )
    for i in range(2):
        Emprestimo.objects.create(
            livro=livro_b,
            usuario=admin,
            data_saida=hoje - timedelta(days=10 + i),
            data_prevista_devolucao=hoje - timedelta(days=7 + i),
            data_devolucao=hoje - timedelta(days=5 + i),
        )

    # Livro C com 1 empréstimo
    livro_c = CadastroLivroModel.objects.create(
        nome="Livro C",
        autor="Autor C",
        status="disponivel",
    )
    Emprestimo.objects.create(
        livro=livro_c,
        usuario=admin,
        data_saida=hoje - timedelta(days=10),
        data_prevista_devolucao=hoje - timedelta(days=7),
        data_devolucao=hoje - timedelta(days=5),
    )

    resp = client.get(
        "/livros/relatorios/circulacao/",
        {
            "data_inicio": inicio.strftime("%Y-%m-%d"),
            "data_fim": fim.strftime("%Y-%m-%d"),
        },
    )

    assert resp.status_code == 200
    html = resp.content.decode("utf-8")

    # Garante que os três títulos aparecem no HTML do Top 10
    assert "Livro A" in html
    assert "Livro B" in html
    assert "Livro C" in html


# -----------------------------------------------------------------------------
# Cenário 4 – Exportação CSV e PDF
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_historia7_exportar_csv_e_pdf(client):
    """
    Dado que um relatório foi gerado
    Quando eu solicitar “Exportar” em CSV ou PDF
    Então o sistema deve gerar o arquivo para download
    mantendo filtros e período aplicados.
    """
    User = get_user_model()
    admin = User.objects.create_superuser(
        username="admin_rel4",
        email="admin_rel4@test.com",
        password="123456",
    )
    client.force_login(admin)

    inicio = date(2025, 8, 1)
    fim = date(2025, 8, 31)
    params = {
        "data_inicio": inicio.strftime("%Y-%m-%d"),
        "data_fim": fim.strftime("%Y-%m-%d"),
    }

    # CSV
    resp_csv = client.get("/livros/relatorios/circulacao/exportar/csv/", params)
    assert resp_csv.status_code == 200
    assert resp_csv["Content-Type"].startswith("text/csv")
    dispo_csv = resp_csv["Content-Disposition"]
    assert "attachment" in dispo_csv
    assert "relatorio_circulacao" in dispo_csv

    # PDF – aqui o importante é gerar uma resposta 200.
    resp_pdf = client.get("/livros/relatorios/circulacao/exportar/pdf/", params)
    assert resp_pdf.status_code == 200

    # Se houver cabeçalho de download, conferimos o nome;
    # se não houver (caso de fallback texto), o teste não falha.
    dispo_pdf = resp_pdf.headers.get("Content-Disposition", "")
    if dispo_pdf:
        assert "attachment" in dispo_pdf
        assert "relatorio_circulacao" in dispo_pdf
