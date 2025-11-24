from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django import forms
from django.db.models import Q, Count
from django.core.paginator import Paginator

from .models import CadastroLivroModel, Emprestimo, Reserva

from datetime import timedelta, datetime
import csv


# --------- Form para cadastrar/editar livros ---------
class LivroForm(forms.ModelForm):
    class Meta:
        model = CadastroLivroModel
        fields = ["nome", "autor", "completo"]
        labels = {
            "nome": "Nome do livro",
            "autor": "Autor(a)",
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


def usuario_bloqueado(usuario):
    """
    Retorna True se o usuário tiver alguma multa em aberto.
    Critério: existe empréstimo com multa > 0 e multa não paga.
    """
    return Emprestimo.objects.filter(
        usuario=usuario,
        multa_valor__gt=0,
        multa_paga=False
    ).exists()


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

    # Bloqueio por multa pendente
    if usuario_bloqueado(usuario):
        messages.error(request, "Empréstimo bloqueado: pendência de multa.")
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

    # Lógica da multa (História 6)
    if emp.multa_valor > 0:
        messages.warning(
            request,
            f"Multa aplicada por atraso: R$ {emp.multa_valor:.2f}"
        )
    elif atraso > 0:
        messages.warning(request, "Devolução em atraso registrada, sem multa por carência.")
    else:
        messages.success(request, "Devolução registrada com sucesso")

    return redirect("livros:emprestimos_list")


@login_required
@user_passes_test(is_admin)
def quitar_multa(request, pk: int):
    """
    Marca a multa de um empréstimo como quitada.
    Ao quitar, o usuário deixa de ficar bloqueado para novos empréstimos.
    """
    emp = get_object_or_404(Emprestimo, pk=pk)

    emp.quitar_multa()
    messages.success(request, "Multa quitada. Usuário desbloqueado para novos empréstimos.")
    return redirect("livros:emprestimos_list")


# ------------------------ RELATÓRIOS (História 7) -------------------
def _parse_data(data_str):
    """Converte 'YYYY-MM-DD' em date, ou None se vier vazio/errado."""
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").date()
    except Exception:
        return None


def _obter_dados_circulacao(data_inicio, data_fim):
    """
    Função de apoio que monta os dados do relatório de circulação.
    Usada tanto pela tela HTML quanto pelos exports CSV/PDF.
    """
    # Empréstimos no período (pela data de saída)
    emprestimos_qs = Emprestimo.objects.filter(
        data_saida__range=(data_inicio, data_fim)
    ).select_related("livro", "usuario")

    qtd_emprestimos = emprestimos_qs.count()

    # Devoluções no período (data_devolucao preenchida e no range)
    devolucoes_qs = Emprestimo.objects.filter(
        data_devolucao__isnull=False,
        data_devolucao__range=(data_inicio, data_fim),
    ).select_related("livro", "usuario")

    qtd_devolucoes = devolucoes_qs.count()

    # Atrasos no período (entre as devoluções do período)
    qtd_atrasos = sum(1 for e in devolucoes_qs if e.dias_atraso > 0)

    # Reservas criadas no período
    reservas_qs = Reserva.objects.filter(
        criada_em__date__range=(data_inicio, data_fim)
    ).select_related("livro", "usuario")
    qtd_reservas = reservas_qs.count()

    # Top 10 livros mais emprestados no período (usando data_saida)
    top_livros_qs = (
        Emprestimo.objects
        .filter(data_saida__range=(data_inicio, data_fim))
        .values("livro__nome")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    top_livros = [
        {
            "titulo": item["livro__nome"],
            "total": item["total"],
        }
        for item in top_livros_qs
    ]

    tem_dados = any([
        qtd_emprestimos,
        qtd_devolucoes,
        qtd_atrasos,
        qtd_reservas,
        len(top_livros) > 0,
    ])

    return {
        "qtd_emprestimos": qtd_emprestimos,
        "qtd_devolucoes": qtd_devolucoes,
        "qtd_atrasos": qtd_atrasos,
        "qtd_reservas": qtd_reservas,
        "top_livros": top_livros,
        "tem_dados": tem_dados,
    }


@login_required
@user_passes_test(is_admin)
def relatorio_circulacao(request):
    """
    Tela principal do relatório de circulação:
    - filtro por período (data_inicio, data_fim)
    - exibe contagens e top 10 livros
    - exibe mensagens de "nenhum dado" quando for o caso
    """
    data_inicio_str = (request.GET.get("data_inicio") or "").strip()
    data_fim_str = (request.GET.get("data_fim") or "").strip()

    data_inicio = _parse_data(data_inicio_str) if data_inicio_str else None
    data_fim = _parse_data(data_fim_str) if data_fim_str else None

    stats = None
    mensagem_sem_dados = None

    if data_inicio and data_fim:
        if data_inicio > data_fim:
            messages.error(request, "Período inválido: a data inicial é maior que a final.")
        else:
            stats = _obter_dados_circulacao(data_inicio, data_fim)
            if not stats["tem_dados"]:
                mensagem_sem_dados = "Nenhum dado para o período selecionado."
    elif data_inicio_str or data_fim_str:
        messages.error(request, "Informe as duas datas para gerar o relatório.")

    contexto = {
        "data_inicio": data_inicio_str,
        "data_fim": data_fim_str,
        "stats": stats,
        "mensagem_sem_dados": mensagem_sem_dados,
    }
    return render(request, "relatorios/circulacao.html", contexto)


@login_required
@user_passes_test(is_admin)
def exportar_relatorio_csv(request):
    """
    Exporta o relatório de circulação em CSV, mantendo o período informado.
    """
    data_inicio_str = (request.GET.get("data_inicio") or "").strip()
    data_fim_str = (request.GET.get("data_fim") or "").strip()

    data_inicio = _parse_data(data_inicio_str)
    data_fim = _parse_data(data_fim_str)

    if not (data_inicio and data_fim):
        messages.error(request, "Período inválido para exportação.")
        return redirect("/livros/relatorios/circulacao/")


    dados = _obter_dados_circulacao(data_inicio, data_fim)

    filename = f"relatorio_circulacao_{data_inicio_str}_a_{data_fim_str}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Relatório de circulação"])
    writer.writerow([f"Período: {data_inicio_str} a {data_fim_str}"])
    writer.writerow([])

    writer.writerow(["Indicador", "Quantidade"])
    writer.writerow(["Empréstimos", dados["qtd_emprestimos"]])
    writer.writerow(["Devoluções", dados["qtd_devolucoes"]])
    writer.writerow(["Empréstimos em atraso (no período)", dados["qtd_atrasos"]])
    writer.writerow(["Reservas", dados["qtd_reservas"]])

    writer.writerow([])
    writer.writerow(["Top 10 livros mais emprestados"])
    writer.writerow(["Título", "Qtde empréstimos"])

    for item in dados["top_livros"]:
        writer.writerow([item["titulo"], item["total"]])

    return response


@login_required
@user_passes_test(is_admin)
def exportar_relatorio_pdf(request):
    """
    Exporta o relatório de circulação em PDF (simples), mantendo o período.
    Requer a biblioteca 'reportlab':
        pip install reportlab
    """
    data_inicio_str = (request.GET.get("data_inicio") or "").strip()
    data_fim_str = (request.GET.get("data_fim") or "").strip()

    data_inicio = _parse_data(data_inicio_str)
    data_fim = _parse_data(data_fim_str)

    if not (data_inicio and data_fim):
        messages.error(request, "Período inválido para exportação.")
        return redirect("/livros/relatorios/circulacao/")


    dados = _obter_dados_circulacao(data_inicio, data_fim)

    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        return HttpResponse(
            "Biblioteca 'reportlab' não instalada. Rode: pip install reportlab",
            content_type="text/plain",
        )

    filename = f"relatorio_circulacao_{data_inicio_str}_a_{data_fim_str}.pdf"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response)
    y = 800

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Relatório de circulação")
    y -= 20
    p.setFont("Helvetica", 11)
    p.drawString(50, y, f"Período: {data_inicio_str} a {data_fim_str}")
    y -= 30

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Indicadores")
    y -= 18
    p.setFont("Helvetica", 11)
    p.drawString(60, y, f"Empréstimos: {dados['qtd_emprestimos']}")
    y -= 16
    p.drawString(60, y, f"Devoluções: {dados['qtd_devolucoes']}")
    y -= 16
    p.drawString(60, y, f"Empréstimos em atraso (no período): {dados['qtd_atrasos']}")
    y -= 16
    p.drawString(60, y, f"Reservas: {dados['qtd_reservas']}")
    y -= 30

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Top 10 livros mais emprestados")
    y -= 18
    p.setFont("Helvetica", 11)
    if not dados["top_livros"]:
        p.drawString(60, y, "Nenhum livro emprestado no período.")
        y -= 16
    else:
        for item in dados["top_livros"]:
            p.drawString(60, y, f"{item['titulo']} - {item['total']} empréstimo(s)")
            y -= 16
            if y < 50:
                p.showPage()
                y = 800
                p.setFont("Helvetica", 11)

    p.showPage()
    p.save()
    return response


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


# ------------------------ Área do usuário (empréstimos) -------------------
@login_required
def minha_area_de_emprestimos(request):
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
    """
    Tela de confirmação + gravação da renovação de um empréstimo.
    Regras:
    - Somente staff ou o próprio usuário podem renovar.
    - Não pode renovar se já devolvido.
    - Não pode renovar se estiver em atraso.
    - Limite de 1 renovação.
    """

    emprestimo = get_object_or_404(Emprestimo, id=emprestimo_id)

    # --- Permissão ---
    if not (request.user.is_staff or request.user == emprestimo.usuario):
        messages.error(request, "Você não tem permissão para renovar este empréstimo.")
        return redirect("livros:emprestimos_list")

    # --- Já devolvido ---
    if emprestimo.data_devolucao:
        messages.error(request, "Não é possível renovar um empréstimo já devolvido.")
        return redirect("livros:emprestimos_list")

    # --- Em atraso ---
    if emprestimo.dias_atraso > 0:
        messages.error(request, "Não é possível renovar empréstimo em atraso.")
        return redirect("livros:emprestimos_list")

    # --- Limite de renovações ---
    if (emprestimo.renovacao_count or 0) >= 1:
        messages.error(request, "Limite de 1 renovação já foi utilizado.")
        return redirect("livros:emprestimos_list")

    # Nova data sugerida (ex.: +7 dias)
    nova_data_prevista = emprestimo.data_prevista_devolucao + timedelta(days=7)

    # --- Salvar renovação ---
    if request.method == "POST":
        emprestimo.data_prevista_devolucao = nova_data_prevista
        emprestimo.renovacao_count = (emprestimo.renovacao_count or 0) + 1
        emprestimo.save()

        messages.success(request, "Renovação aplicada com sucesso!")
        return redirect("livros:emprestimos_list")

    # --- Renderizar tela de confirmação ---
    return render(
        request,
        "emprestimos/confirmar_renovacao.html",
        {
            "emprestimo": emprestimo,
            "nova_data_prevista": nova_data_prevista
        }
    )

