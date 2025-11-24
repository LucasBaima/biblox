import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from livros.models import CadastroLivroModel, Emprestimo


@pytest.mark.django_db
def test_historia6_multa_aplicada_e_bloqueio(client):
    """
    Cenário principal da História 6:
    - Devolução em atraso gera multa
    - Usuário com multa em aberto fica bloqueado para novos empréstimos
    """
    User = get_user_model()

    # Admin (vai ser também o "leitor" para simplificar)
    admin = User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="123456",
    )
    client.force_login(admin)

    # Livro já emprestado
    hoje = timezone.now().date()
    livro = CadastroLivroModel.objects.create(
        nome="Livro Multa",
        autor="Autor X",
        status="emprestado",
    )

    # Empréstimo com data prevista já vencida
    emprestimo = Emprestimo.objects.create(
        livro=livro,
        usuario=admin,
        data_saida=hoje - timedelta(days=10),
        data_prevista_devolucao=hoje - timedelta(days=5),
    )

    # --- Devolução em atraso ---
    resp_dev = client.post(
        reverse("livros:registrar_devolucao", args=[emprestimo.pk]),
        {"data_devolucao": hoje.strftime("%Y-%m-%d")},
        follow=True,
    )

    emprestimo.refresh_from_db()

    # Deve ter atraso e multa em aberto
    assert emprestimo.dias_atraso > 0
    assert emprestimo.multa_valor > 0
    assert emprestimo.multa_paga is False
    assert "Multa aplicada por atraso" in resp_dev.content.decode()

    # --- Tenta fazer um novo empréstimo: deve bloquear ---
    novo_livro = CadastroLivroModel.objects.create(
        nome="Livro 2",
        autor="Autor Y",
        status="disponivel",
    )

    resp_emp = client.post(
        reverse("livros:registrar_emprestimo"),
        {
            "livro_id": str(novo_livro.id),
            "usuario_id": str(admin.id),
            "data_saida": hoje.strftime("%Y-%m-%d"),
            "data_prevista_devolucao": (hoje + timedelta(days=7)).strftime("%Y-%m-%d"),
        },
        follow=True,
    )

    # Mensagem de bloqueio por multa
    assert "Empréstimo bloqueado: pendência de multa." in resp_emp.content.decode()


@pytest.mark.django_db
def test_historia6_quitar_multa_desbloqueia(client):
    """
    Cenário complementar:
    - Quitar multa libera o usuário para novos empréstimos
    """
    User = get_user_model()
    admin = User.objects.create_superuser(
        username="admin2",
        email="admin2@test.com",
        password="123456",
    )
    client.force_login(admin)

    hoje = timezone.now().date()

    livro = CadastroLivroModel.objects.create(
        nome="Livro Multa 2",
        autor="Autor Z",
        status="emprestado",
    )

    # Empréstimo já com multa cadastrada manualmente
    emprestimo = Emprestimo.objects.create(
        livro=livro,
        usuario=admin,
        data_saida=hoje - timedelta(days=10),
        data_prevista_devolucao=hoje - timedelta(days=5),
        data_devolucao=hoje,
        multa_valor=10,
        multa_paga=False,
    )

    # Quita multa
    resp_quitar = client.get(
        reverse("livros:quitar_multa", args=[emprestimo.pk]),
        follow=True,
    )
    emprestimo.refresh_from_db()

    assert emprestimo.multa_paga is True
    assert "Multa quitada. Usuário desbloqueado para novos empréstimos." in resp_quitar.content.decode()
