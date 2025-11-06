#!/usr/bin/env python
import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sistema_notas.settings')
django.setup()

from core.models import Usuario, Nota, Contrato
from decimal import Decimal
from datetime import date, timedelta

def test_dashboard_notas():
    print("=== Teste do Dashboard - Exibição de Notas ===")
    
    # Criar cliente de teste
    client = Client()
    
    # Criar usuário admin se não existir
    User = get_user_model()
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✓ Usuário admin encontrado: {admin_user.username}")
    except User.DoesNotExist:
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        print(f"✓ Usuário admin criado: {admin_user.username}")
    
    # Fazer login
    login_success = client.login(username='admin', password='admin123')
    if login_success:
        print("✓ Login realizado com sucesso")
    else:
        print("✗ Falha no login")
        return
    
    # Verificar se existem notas
    total_notas = Nota.objects.count()
    print(f"✓ Total de notas no banco: {total_notas}")
    
    # Se não há notas, criar algumas para teste
    if total_notas == 0:
        print("Criando notas de teste...")
        
        # Criar contrato primeiro
        contrato = Contrato.objects.create(
            numero='001/2024',
            empresa='Empresa Teste',
            valor=Decimal('10000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=365)
        )
        
        # Criar algumas notas
        for i in range(5):
            Nota.objects.create(
                numero=f'NF{i+1:03d}',
                empresa=f'Empresa {i+1}',
                valor=Decimal(f'{(i+1)*1000}.00'),
                data_entrada=date.today() - timedelta(days=i),
                data_nota=date.today() - timedelta(days=i),
                setor='Teste',
                empenho=f'EMP{i+1:03d}',
                contrato=contrato
            )
        
        print(f"✓ Criadas {Nota.objects.count()} notas de teste")
    
    # Testar acesso ao dashboard
    print("\n--- Testando Dashboard ---")
    
    # Acessar o dashboard usando RequestFactory para preservar contexto
    from django.test import RequestFactory
    from core.views import HomeView
    
    factory = RequestFactory()
    request = factory.get('/')
    request.user = admin_user
    
    # Adicionar session e messages
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.messages.middleware import MessageMiddleware
    
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    middleware = MessageMiddleware(lambda x: None)
    middleware.process_request(request)
    
    # Testar a view diretamente
    view = HomeView.as_view()
    response = view(request)
    print(f"✓ Dashboard carregado com sucesso (status: {response.status_code})")
    
    # Testar contexto através da view
    view_instance = HomeView()
    view_instance.request = request
    context = view_instance.get_context_data()
    
    print(f"✓ Contexto encontrado com {len(context)} variáveis")
    print(f"Variáveis disponíveis: {list(context.keys())}")
    
    # Verificar se o contexto contém as notas
    if 'notas' in context:
        notas_context = context['notas']
        print(f"✓ Notas encontradas no contexto: {len(notas_context)}")
        
        # Listar algumas notas
        for i, nota in enumerate(notas_context[:3]):
            print(f"  - Nota {i+1}: {nota.numero} - {nota.empresa} - R$ {nota.valor}")
    else:
        print("✗ Variável 'notas' não encontrada no contexto")
    
    # Verificar estatísticas
    if 'estatisticas' in context:
        stats = context['estatisticas']
        print(f"✓ Estatísticas encontradas:")
        if 'notas' in stats:
            print(f"  - Total: {stats['notas'].get('total', 0)}")
            print(f"  - Pendentes: {stats['notas'].get('pendentes', 0)}")
            print(f"  - Processadas: {stats['notas'].get('processadas', 0)}")
            print(f"  - Valor Total: R$ {stats['notas'].get('valor_total', 0)}")
    else:
        print("✗ Estatísticas não encontradas no contexto")
    
    # Testar também com o client normal para verificar HTML
    response = client.get('/')
    print(f"\n✓ Teste com Client normal (status: {response.status_code})")
    
    # Verificar se o HTML contém as notas
    content = response.content.decode('utf-8')
    if 'notas-list' in content:
        print("✓ Elemento 'notas-list' encontrado no HTML")
    else:
        print("✗ Elemento 'notas-list' não encontrado no HTML")
    
    # Testar requisição AJAX
    print("\n--- Testando Requisição AJAX ---")
    ajax_response = client.get(reverse('core:home'), {'ajax': '1'})
    
    if ajax_response.status_code == 200:
        print(f"✓ Requisição AJAX bem-sucedida (status: {ajax_response.status_code})")
        
        try:
            ajax_data = json.loads(ajax_response.content.decode('utf-8'))
            if ajax_data.get('success'):
                print(f"✓ Resposta AJAX válida")
                print(f"  - Total de notas: {ajax_data.get('total', 0)}")
                print(f"  - Notas na página: {ajax_data.get('count', 0)}")
                
                if ajax_data.get('html'):
                    print("✓ HTML das notas retornado")
                else:
                    print("✗ HTML das notas não retornado")
            else:
                print(f"✗ Erro na resposta AJAX: {ajax_data.get('error', 'Erro desconhecido')}")
        except json.JSONDecodeError:
            print("✗ Resposta AJAX não é um JSON válido")
            print(f"Conteúdo: {ajax_response.content.decode('utf-8')[:200]}...")
    else:
        print(f"✗ Erro na requisição AJAX (status: {ajax_response.status_code})")
    
    print("\n=== Teste Concluído ===")

if __name__ == '__main__':
    test_dashboard_notas()