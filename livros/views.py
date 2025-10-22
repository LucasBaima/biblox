from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django import forms
from django.db.models import Q
from django.core.paginator import Paginator
from .models import CadastroLivroModel, Emprestimo, Reserva
from datetime import timedelta



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


# --------- Catálogo com busca/filtro/ordenação/paginação ---------
def catalogo(request):
    # 1) Coletar parâmetros
    q = (request.GET.get("q") or "").strip()
    apenas_disponiveis = (request.GET.get("apenas_disponiveis") in ("1", "true", "on"))
    ordenar = request.GET.get("ordenar", "nome_az")  # nome_az|nome_za|autor_az|autor_za
    page = request.GET.get("page")

    # 2) Montar queryset
    qs = CadastroLivroModel.objects.all()

    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(autor__icontains=q))

    if apenas_disponiveis:
        qs = qs.filter(status__iexact="disponivel")

    ordering_map = {
        "nome_az": "nome",
        "nome_za": "-nome",
        "autor_az": "autor",
        "autor_za": "-autor",
    }
    qs = qs.order_by(ordering_map.get(ordenar, "nome"))

    # 3) Paginação
    paginator = Paginator(qs, 20)  # 20 por página
    page_obj = paginator.get_page(page)

    # 4) Preservar filtros na paginação
    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    ctx = {
        "livros": page_obj,                # iterável no template
        "page_obj": page_obj,              # controle de paginação
        "q": q,
        "ordenar": ordenar,
        "apenas_disponiveis": apenas_disponiveis,
        "querystring": querystring,
    }
    return render(request, "livros/lista.html", ctx)


# --------- Home / Dashboard ---------
def homepage(request):
    # números rápidos
    total = CadastroLivroModel.objects.count()
    disponiveis = CadastroLivroModel.objects.filter(status__iexact="disponivel").count()
    emprestados = CadastroLivroModel.objects.filter(status__iexact="emprestado").count()

    # últimos livros cadastrados (5)
    recentes = CadastroLivroModel.objects.order_by("-id")[:5]

    ctx = {
        "total": total,
        "disponiveis": disponiveis,
        "emprestados": emprestados,
        "recentes": recentes,
    }
    return render(request, "home.html", ctx)



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


@login_required
def minha_area_de_emprestimos(request):
    """
    
    """
    emprestimos = Emprestimo.objects.filter(
        usuario=request.user, 
        data_devolucao__isnull=True 
    ).select_related('livro').order_by('data_prevista_devolucao')

    context = {
        "emprestimos_do_usuario": emprestimos,
    }
    return render(request, 'emprestimos/minha_area_de_emprestimos.html', context)




@login_required
def solicitar_renovacao(request, emprestimo_id):
    emprestimo = get_object_or_404(
        Emprestimo, 
        id=emprestimo_id, 
        usuario=request.user,
        data_devolucao__isnull=True 
    )
    
    livro_id = emprestimo.livro.id
    MAX_RENOVACOES = 1

    pode_renovar_modelo, motivo_modelo = emprestimo.pode_renovar(max_renovacoes=MAX_RENOVACOES)
        
    if not pode_renovar_modelo:
        messages.warning(request, motivo_modelo)
        return redirect('livros:minha_area_de_emprestimos')


  
    reserva_em_conflito = Reserva.objects.filter(
        livro=emprestimo.livro,
        status__in=['ativa', 'pronta'],
    ).exclude(usuario=request.user).exists() 
    
    if reserva_em_conflito:
        messages.error(request, f"O livro '{emprestimo.livro}' está reservado por outro usuário. Renovação não permitida.")
        return redirect('livros:minha_area_de_emprestimos')
    
    
    # --- 3. Processamento (POST - Sem usar forms) ---
    if request.method == 'POST':
        livro_id_confirmado = request.POST.get('livro_id_confirmacao')
        
        try:
            livro_id_confirmado = int(livro_id_confirmado)
        except (ValueError, TypeError):
            messages.error(request, "ID do livro inválido. Tente novamente.")
            return redirect('livros:solicitar_renovacao', emprestimo_id=emprestimo.id)

        if livro_id_confirmado == livro_id:
            try:
                nova_data = emprestimo.aplicar_renovacao(periodo_dias=7)
                messages.success(request, f"Renovação aplicada! Nova data: {nova_data.strftime('%d/%m/%Y')}.")
                return redirect('livros:minha_area_de_emprestimos') 
            
            except Exception as e:
                messages.error(request, f"Falha ao renovar: {e}")
                return redirect('livros:solicitar_renovacao', emprestimo_id=emprestimo.id)
        else:
            messages.error(request, "O ID do livro não corresponde.")
    
    # 4. Renderização (GET)
    nova_data_prevista = emprestimo.data_prevista_devolucao + timedelta(days=7) 
    
    context = {
        'emprestimo': emprestimo,
        'livro_id_original': livro_id,
        'nova_data_prevista': nova_data_prevista
    }
    return render(request, 'emprestimos/confirmar_renovacao.html', context)

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from datetime import datetime
from .models import Emprestimo

@login_required
def emprestimo_detalhe(request, pk):
    """Mostra os detalhes de um empréstimo e o botão de renovação."""
    emprestimo = get_object_or_404(Emprestimo, pk=pk)
    return render(request, "livros/emprestimo_detalhe.html", {"emprestimo": emprestimo})

@login_required
def renovar_emprestimo(request, pk):
    """Tela e ação para renovar um empréstimo."""
    emprestimo = get_object_or_404(Emprestimo, pk=pk)

    # segurança: só o usuário dono ou staff pode renovar
    if not (request.user.is_staff or request.user == emprestimo.usuario):
        messages.error(request, "Você não tem permissão para renovar este empréstimo.")
        return redirect(reverse("emprestimo_detalhe", args=[emprestimo.pk]))

    if request.method == "POST":
        # tenta aplicar a renovação (usa método do model)
        try:
            emprestimo.aplicar_renovacao()
        except Exception as e:
            messages.error(request, str(e))
        else:
            messages.success(request, "Empréstimo renovado com sucesso!")
        return redirect(reverse("emprestimo_detalhe", args=[emprestimo.pk]))

    # se for GET, mostra as infos
    pode, msg = emprestimo.pode_renovar()
    return render(
        request,
        "livros/renovar_emprestimo.html",
        {"emprestimo": emprestimo, "pode": pode, "motivo": msg},
    )

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Emprestimo

@login_required
def solicitar_renovacao(request, emprestimo_id):
    """
    Tela + ação de renovação:
    - GET  -> mostra a confirmação se pode renovar
    - POST -> aplica a renovação chamando Emprestimo.aplicar_renovacao()
    """
    emprestimo = get_object_or_404(Emprestimo, pk=emprestimo_id)

    # Só o dono do empréstimo ou staff pode renovar
    if not (request.user.is_staff or request.user == emprestimo.usuario):
        messages.error(request, "Você não tem permissão para renovar este empréstimo.")
        return redirect(reverse("livros:minha_area_de_emprestimos"))

    if request.method == "POST":
        try:
            # Chama a regra de negócio que já existe no model
            emprestimo.aplicar_renovacao()  # por padrão +7 dias e conta renovação
        except Exception as e:
            messages.error(request, str(e))
        else:
            messages.success(request, "Empréstimo renovado com sucesso!")
        # Para onde voltar depois? Escolhi a sua página "minha área".
        return redirect(reverse("livros:minha_area_de_emprestimos"))

    # GET: mostra se pode renovar e o motivo caso não
    pode, motivo = emprestimo.pode_renovar()
    contexto = {
        "emprestimo": emprestimo,
        "pode": pode,
        "motivo": motivo,
    }
    return render(request, "livros/solicitar_renovacao.html", contexto)
