from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login



# Create your views here.

def login_view(request):
    
    tex ={}
    
    if request.method == "POST":
            
            username = request.POST.get('username')   #forms.cleaned_gata -> Dicionário que recebe o username
            password = request.POST.get('password')
            usuario = authenticate(request, username=username, password=password) #Authenticate verifica se os values de entrada estão no banco de dados... 
            #se for válido retorna o "objeto" -> usuário, caso contrário none
            
            if usuario is not None:    #verificação se usuario is not none... ou seja se correspondeu
                
                login(request,usuario)
                #-> O login() faz duas coisas cruciais: 1. Ele define a chave da sessão do usuário no banco de dados. 
                # 2. Ele configura um cookie de sessão no navegador do usuário.
                # Este cookie é o que o Django usa em requisições futuras para saber que o usuário está logado!
                
                return redirect('livros:home1')     
              
            else:
        
                tex['erros_login'] = 'nome de usuário ou senha inválidos'
        
                tex['dados'] = {'username': username}
        
    return render(request, 'usuarios/login.html', tex)
            
        
            
        