from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django import forms

from .models import CadastroLivroModel, Emprestimo, Reserva


# --------- Form para cadastrar/editar livros ---------
class LivroForm(forms.ModelForm):
    class Meta:
        model = CadastroLivroModel
        fields = ["nome", "autor", "isbn", "completo"]
        labels = {
            "nome": "Nome do livro",
            "autor": "Autor(a)",
            "isbn": "ISBN (13 dígitos)",
            "completo": "Edição integral (obra completa)",
        }


# ------------------ CRUD de Livros -------------------
def home(request):
    ctx = {"registros": CadastroLivroModel.objects.all()}
    return render(request, "crud/inicial.html", ctx)

def cadastrar_livro(request):
    if request.method == "POST":
        form = LivroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("livros:home1")
    else:
        form = LivroForm()
    return render(request, "crud/cadastrar.html", {"form": form})

def remover_livro(request: HttpRequest, id):
    livro = get_object_or_404(CadastroLivroModel, id=id)
    livro.delete()
    return redirect("livros:home1")

def editar_livro(request: HttpRequest, id):
    livro_existente = get_object_or_404(CadastroLivroModel, id=id)
    if request.method == "POST":
        form = LivroForm(request.POST, instance=livro_existente)
        if form.is_valid():
            form.save()
            return redirect("livros:home1")
    else:
        form = LivroForm(instance=livro_existente)
    return render(request, "crud/editar.html", {"form": form, "livro_id": id})


# ------------- Empréstimos / Devoluções -------------
def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def emprestimos_list(request):
    qs = Emprestimo.objects.select_related("livro", "usuario").order_by("-id")
    return render(request, "emprestimos/list.html", {"emprestimos": qs})

@login_required
@user_passes_test(is_admin)
def registrar_emprestimo(request):
    if request.method == "GET":
        livros = CadastroLivroModel.objects.all().order_by("nome")
        usuarios = get_user_model().objects.filter(is_active=True).order_by("username")
        return render(request, "emprestimos/novo.html", {"livros": livros, "usuarios": usuarios})

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

    res_pronta = Reserva.objects.filter(livro=livro, status='pronta').order_by('criada_em').first()
    if res_pronta and res_pronta.usuario_id != usuario.id:
        messages.error(request, "Livro reservado para retirada")
        return redirect("livros:registrar_emprestimo")

    if getattr(livro, "status", "disponivel") != "disponivel":
        messages.error(request, "Livro indisponível para empréstimo")
        return redirect("livros:registrar_emprestimo")

    try:
        y1, m1, d1 = [int(x) for x in data_saida.split("-")]
        y2, m2, d2 = [int(x) for x in data_prevista.split("-")]
        data_saida_dt = timezone.datetime(y1, m1, d1).date()
        data_prevista_dt = timezone.datetime(y2, m2, d2).date()
    except Exception:
        messages.error(request, "Datas inválidas. Use YYYY-MM-DD.")
        return redirect("livros:registrar_emprestimo")

    try:
        Emprestimo.objects.create(
            livro=livro, usuario=usuario,
            data_saida=data_saida_dt, data_prevista_devolucao=data_prevista_dt
        )
    except IntegrityError:
        messages.error(request, "Livro indisponível para empréstimo")
        return redirect("livros:registrar_emprestimo")

    if hasattr(livro, "status"):
        livro.status = "emprestado"
        livro.save(update_fields=["status"])

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


# ------------------------ Reservas -------------------
@login_required
def minhas_reservas(request):
    Reserva.expirar_vencidas()
    qs = Reserva.objects.filter(usuario=request.user).select_related('livro').order_by('-criada_em')
    return render(request, "reservas/minhas.html", {"reservas": qs})

@login_required
def criar_reserva(request, livro_id: int):
    if request.method != "POST":
        messages.error(request, "Operação inválida")
        return redirect("livros:minhas_reservas")

    Reserva.expirar_vencidas()

    try:
        livro = CadastroLivroModel.objects.get(pk=livro_id)
    except CadastroLivroModel.DoesNotExist:
        messages.error(request, "Livro inválido")
        return redirect("livros:minhas_reservas")

    if getattr(livro, "status", "disponivel") == "disponivel":
        messages.error(request, "Livro disponível para empréstimo imediato")
        return redirect("livros:minhas_reservas")

    existe = Reserva.objects.filter(
        livro=livro, usuario=request.user, status__in=["ativa", "pronta"]
    ).exists()
    if existe:
        messages.error(request, "Reserva já existente para este usuário")
        return redirect("livros:minhas_reservas")

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

    if (res.usuario_id != request.user.id) and (not request.user.is_staff and not request.user.is_superuser):
        messages.error(request, "Você não pode cancelar esta reserva")
        return redirect("livros:minhas_reservas")

    era_pronta = (res.status == "pronta")
    res.status = "cancelada"
    res.cancelada_em = timezone.now()
    res.save(update_fields=["status", "cancelada_em"])

    if era_pronta:
        Reserva.promover_primeira(res.livro)

    messages.success(request, "Reserva cancelada")
    return redirect("livros:minhas_reservas")
