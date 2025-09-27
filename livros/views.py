from django.shortcuts import render, redirect
from .models import CadastroLivroModel #-> Importação do modelo



def home(request): 
    user = {
        "user":"usuário"
    }
    
    user['registros'] = CadastroLivroModel.objects.all()    #"Encapsulando a key dentro do dicionário user"
    
    return render(request, "crud/inicial.html", user)




  
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
            validacao['nome'] = 'O campo name é obrigatório.'
        if len(isbn) != 13: # Exemplo: ISBN deve ter 13 dígitos
            validacao['isbn'] = 'O ISBN deve ter 13 caracteres.' #validação 2
        
        
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
                # Lidar com erros de banco de dados
                validacao['erro_geral'] = f'Erro ao salvar: {e}'
    
    return render(request, 'crud/cadastrar.html', validacao)   #renderizar o conteúdo do arquivo cadastrar.html
