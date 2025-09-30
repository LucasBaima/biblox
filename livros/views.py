from django.shortcuts import render, redirect, get_object_or_404
from .models import CadastroLivroModel #-> Importação do modelo
from django.http import HttpRequest



def home(request): 
    user = {
        "user":"usuário"
    }
    
    user['registros'] = CadastroLivroModel.objects.all()    #"Encapsulando a key dentro do dicionário user"
    
    return render(request, "livros/inicial.html", user)




  
def cadastrar_livro(request):
    validacao ={}
    
    
    if request.method == "POST": #extração direta
        nome = request.POST.get('nome')
        autor = request.POST.get('autor')           #cada campo do formulario enviado extraido
        isbn = request.POST.get('isbn')
        completo = request.POST.get('completo')
        # ... extrai todos os outros campos ...

        #  VALIDAÇÃO MANUAL 
        erros = {}
        
        
        if not nome:   
            erros['nome'] = 'O campo name é obrigatório.'
            
        if not autor:
            erros["autor"] = "Campo autor é obrigatório"   
            
            
        if isbn:    
            if len(isbn) != 13: # Exemplo: ISBN deve ter 13 dígitos
                erros['isbn'] = 'O ISBN deve ter 13 caracteres.' #validação 2
        
        
        if erros:
            #  Se houver erros, passa os erros e os dados para o template
            validacao['erros'] = erros
            validacao['dados'] = request.POST # Passa os dados preenchidos para não perdê-los
            
            
            
            
            
        else:
            #  SALVAMENTO MANUAL NO BANCO DE DADOS
            try:
                CadastroLivroModel.objects.create(
                    nome=nome,
                    autor=autor,
                    isbn=isbn,
                    completo=bool(completo), # Conversão de tipo manual
                    
                )
                return redirect("livros:home1") # Redireciona para a home1
            
            except Exception as e:
                # 
                validacao['erro_geral'] = 'Erro de integridade ao salvar no banco.'
            except Exception as e:
                validacao['erro_geral'] = f'Erro desconhecido ao salvar: {e}'
    
    return render(request, 'livros/cadastrar.html', validacao)   #renderizar o conteúdo do arquivo cadastrar.html









def remover_livro(request:HttpRequest, id):
    livro = get_object_or_404(CadastroLivroModel, id=id) #Tentaviva de obter item do banco de dados na tabela do nosso model com o parâmetro passado.. e se n encontrar dará um not found404
    livro.delete()
    return redirect("livros:home1")   #após clicar em remover.. irá pra rota remover e redirecionará rapidamente para cá!home1







def editar_livro(request:HttpRequest, id):
    # 1. Busca o livro existente no banco de dados
    livro_existente = get_object_or_404(CadastroLivroModel, id=id)
    
    contexto = {'livro_id': id}

    if request.method == 'POST':
        
    #   Repetição da lógica de validação para não dá problemas
        nome = request.POST.get('nome')
        autor = request.POST.get('autor')
        isbn = request.POST.get('isbn')
        completo_post = request.POST.get('completo')
        
        # validação dos campos manualmente
        erros = {}
        
        if not nome:
            erros['nome'] = 'O nome é obrigatório.'
        
        
        if erros:
            # Se houver erros, passa os erros e os dados POSTADOS para o template
            contexto['erros'] = erros
            contexto['dados'] = request.POST # Mantém o que o usuário tentou enviar
            
            
        else:
            #  Atualiza o objeto com os novos dados
            livro_existente.nome = nome
            livro_existente.autor = autor
            livro_existente.isbn = isbn
          
            livro_existente.completo = bool(completo_post) 
            
            
            
            
            
            livro_existente.save()
            return redirect("livros:home1") 
            
   
    if 'dados' not in contexto:  #Se dados não existir dentro de contexto
       
        contexto['dados'] = {
            'nome': livro_existente.nome,
            'autor': livro_existente.autor,   #valores originais do modelo(banco de dados) será atribuidos
            'isbn': livro_existente.isbn,
            'completo': livro_existente.completo, }
            
            #agora a chave dados armazena  um dicionário que mapeio o nome dos campos existentes
             
        
    
    return render(request, 'livros/editar.html', contexto) 
    
    
    
def registrar_livro(request, id):
    
    Registro = get_object_or_404(CadastroLivroModel, id=id)
    
    context = {'livro_id': id, 'registro': Registro}
    
    
    
    if request.method == "POST":
        
        data_devolucao = request.POST.get('data_devolucao')
        
        
        
        erros = {}
        
        
        
        if Registro.emprestado == True:
            erros['emprestado'] = f'o Livro "{Registro.nome}" já foi emprestado'
            
        if not erros and not data_devolucao:
            erros['data_devolucao'] = 'A data de devolução é obrigatória.'

        if erros:
            context['erros'] = erros
            context['dados'] = request.POST
            
            return render(request, 'livros/registrarEmprest.html', context)
            
        
            
        Registro.data_devolucao = data_devolucao
        Registro.emprestado = True
        Registro.save()
        return redirect("livros:home1") 
        
    return render(request, 'livros/registrarEmprest.html', context) #caso seja um GET..  apenas apresenta o formulário
        
       
    
        
    
    
    