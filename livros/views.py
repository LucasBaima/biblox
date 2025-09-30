from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import get_user_model

from .models import CadastroLivroModel, Emprestimo, Reserva


# -----------------------------------
# HOME / CRUD DE LIVROS (História 1)
# -----------------------------------

def home(request):
    user = {"user": "usuário"}
    user["registros"] = CadastroLivroModel.objects.all()
    return render(request, "crud/inicial.html", user)


def cadastrar_livro(request):
    validacao = {}

    if request.method == "POST":
        nome = request.POST.get("nome")
        autor = request.POST.get("autor")
        isbn = request.POST.get("isbn")
        completo = request.POST.get("completo")

        erros = {}
        if not nome:
            erros["nome"] = "O campo name é obrigatório."
        if not autor:
            erros["autor"] = "Campo autor é obrigatório"
        if isbn and len(isbn) != 13:
            erros["isbn"] = "O ISBN deve ter 13 caracteres."

        if erros:
            validacao["erros"] = erros
            validacao["dados"] = request.POST
        else:
            try:
                CadastroLivroModel.objects.create(
                    nome=nome,
                    autor=autor,
                    isbn=isbn,
                    completo=bool(completo),
                )
                return redirect("livros:home1")
            except Exception as e:
                validacao["erro_geral"] = f"Erro ao salvar: {e}"

    return render(request, "crud/cadastrar.html", validacao)


def remover_livro(request: HttpRequest, id):
    livro = get_object_or_404(CadastroLivroModel, id=id)
    livro.delete()
    return redirect("livros:home1")


def editar_livro(request: HttpRequest, id):
    livro_existente = get_object_or_404(CadastroLivroModel, id=id)
    contexto = {"livro_id": id}

    if request.method == "POST":
        nome = request.POST.get("nome")
        autor = request.POST.get("autor")
        isbn = request.POST.get("isbn")
        completo_post = request.POST.get("completo")

        erros = {}
        if not nome:
            erros["nome"] = "O nome é obrigatório."

        if erros:
            contexto["erros"] = erros
            contexto["dados"] = request.POST
        else:
            livro_existente.nome = nome
            livro_existente.autor = autor
            livro_existente.isbn = isbn
            livro_existente.completo = bool(completo_post)
            livro_existente.save()
            return redirect("livros:home1")

    if "dados" not in contexto:
        contexto["dados"] = {
            "nome": livro_existente.nome,
            "autor": livro_existente.autor,
            "isbn": livro_existente.isbn,
            "completo": livro_existente.completo,
        }

    return render(request, "crud/editar.html", contexto)


# -----------------------------------
# EMPRÉSTIMOS / DEVOLUÇÕES (História 2)
# -----------------------------------

def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def emprestimos_list(request):
    qs = (
        Emprestimo.objects
        .select_related("livro", "usuario")
        .order_by("-id")
    )
    return render(request, "emprestimos/list.html", {"emprestimos": qs})


@login_required
@user_passes_test(is_admin)
def registrar_emprestimo(request):
    if request.method == "GET":
        livros = CadastroLivroModel.objects.all().order_by("nome")
        usuarios = get_user_model().objects.filter(is_active=True).order_by("username")
        return render(request, "emprestimos/novo.html", {"livros": livros, "usuarios": usuarios})

    # POST (sem Django Forms): lê campo a campo
    livro_id = request.POST.get("livro_id", "").strip()
    usuario_id = request.POST.get("usuario_id", "").strip()
    data_saida = request.POST.get("data_saida", "").strip()
    data_prevista = request.POST.get("data_prevista_devolucao", "").strip()

    User = get_user_model()
    try:
        usuario = User.objects.get(pk=usuario_id)
    except (User.DoesNotExist, ValueError):
        messages.error(request, "Usuário inexistente")
        return redirect("livros:registrar_emprestimo")

    try:
        livro = CadastroLivroModel.objects.get(pk=livro_id)
    except (CadastroLivroModel.DoesNotExist, ValueError):
        messages.error(request, "Livro inválido")
        return redirect("livros:registrar_emprestimo")

    # BLOQUEIO por reserva 'pronta' (História 3 integração)
    res_pronta = Reserva.objects.filter(livro=livro, status='pronta').order_by('criada_em').first()
    if res_pronta and res_pronta.usuario_id != usuario.id:
        messages.error(request, "Livro reservado para retirada")
        return redirect("livros:registrar_emprestimo")

    # livro não pode estar emprestado
    if getattr(livro, "status", "disponivel") != "disponivel":
        messages.error(request, "Livro indisponível para empréstimo")
        return redirect("livros:registrar_emprestimo")

    # validação das datas
    try:
        y1, m1, d1 = [int(x) for x in data_saida.split("-")]
        y2, m2, d2 = [int(x) for x in data_prevista.split("-")]
        data_saida_dt = timezone.datetime(y1, m1, d1).date()
        data_prevista_dt = timezone.datetime(y2, m2, d2).date()
    except Exception:
        messages.error(request, "Datas inválidas. Use YYYY-MM-DD.")
        return redirect("livros:registrar_emprestimo")

    # cria empréstimo
    try:
        Emprestimo.objects.create(
            livro=livro,
            usuario=usuario,
            data_saida=data_saida_dt,
            data_prevista_devolucao=data_prevista_dt,
        )
    except IntegrityError:
        messages.error(request, "Livro indisponível para empréstimo")
        return redirect("livros:registrar_emprestimo")

    # marca como emprestado
    if hasattr(livro, "status"):
        livro.status = "emprestado"
        livro.save(update_fields=["status"])

    # se havia reserva 'pronta' do MESMO usuário do empréstimo, conclui a reserva
    if res_pronta and res_pronta.usuario_id == usuario.id:
        res_pronta.concluir()

    messages.success(request, "Empréstimo registrado com sucesso")
    return redirect("livros:emprestimos_list")


@login_required
@user_passes_test(is_admin)
def registrar_devolucao(request, pk: int):
    emp = get_object_or_404(Emprestimo, pk=pk)

    if request.method == "GET":
        return render(request, "emprestimos/devolver.html", {"emprestimo": emp})

    data_dev = request.POST.get("data_devolucao", "").strip()
    try:
        y, m, d = [int(x) for x in data_dev.split("-")]
        data_dev_dt = timezone.datetime(y, m, d).date()
    except Exception:
        messages.error(request, "Data inválida. Use YYYY-MM-DD.")
        return redirect("livros:registrar_devolucao", pk=emp.pk)

    atraso = emp.registrar_devolucao(data_dev_dt)
    if atraso > 0:
        messages.warning(request, "Devolução em atraso registrada")
    else:
        messages.success(request, "Devolução registrada com sucesso")

    return redirect("livros:emprestimos_list")


# -----------------------------------
# RESERVAS (História 3)
# -----------------------------------

@login_required
def minhas_reservas(request):
    # expira reservas 'pronta' vencidas sempre que entra na tela
    Reserva.expirar_vencidas()
    qs = (Reserva.objects
          .filter(usuario=request.user)
          .select_related('livro')
          .order_by('-criada_em'))
    return render(request, "reservas/minhas.html", {"reservas": qs})


@login_required
def criar_reserva(request, livro_id: int):
    if request.method != "POST":
        messages.error(request, "Operação inválida")
        return redirect("livros:minhas_reservas")

    # atualiza expirações antes de operar
    Reserva.expirar_vencidas()

    # valida livro
    try:
        livro = CadastroLivroModel.objects.get(pk=livro_id)
    except CadastroLivroModel.DoesNotExist:
        messages.error(request, "Livro inválido")
        return redirect("livros:minhas_reservas")

    # Cenário 2: Livro disponível não pode ser reservado
    if livro.status == "disponivel":
        messages.error(request, "Livro disponível para empréstimo imediato")
        return redirect("livros:minhas_reservas")

    # Cenário 3: Reserva duplicada (ativa/pronta)
    existe = Reserva.objects.filter(
        livro=livro, usuario=request.user, status__in=["ativa", "pronta"]
    ).exists()
    if existe:
        messages.error(request, "Reserva já existente para este usuário")
        return redirect("livros:minhas_reservas")

    # Cenário 1: Reserva criada com sucesso
    Reserva.objects.create(livro=livro, usuario=request.user, status="ativa")
    messages.success(request, "Reserva registrada")
    return redirect("livros:minhas_reservas")


@login_required
def cancelar_reserva(request, pk: int):
    if request.method != "POST":
        messages.error(request, "Operação inválida")
        return redirect("livros:minhas_reservas")

    Reserva.expirar_vencidas()

    res = get_object_or_404(Reserva, pk=pk)

    # somente o dono cancela; admin pode tudo
    if (res.usuario_id != request.user.id) and (not request.user.is_staff and not request.user.is_superuser):
        messages.error(request, "Você não pode cancelar esta reserva")
        return redirect("livros:minhas_reservas")

    era_pronta = (res.status == "pronta")
    res.status = "cancelada"
    res.cancelada_em = timezone.now()
    res.save(update_fields=["status", "cancelada_em"])

    # se cancelou uma 'pronta', promove a próxima da fila
    if era_pronta:
        Reserva.promover_primeira(res.livro)

    messages.success(request, "Reserva cancelada")
    return redirect("livros:minhas_reservas")
