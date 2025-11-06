#!/usr/bin/env python
import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.template.loader import get_template

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sistema_notas.settings')
django.setup()

from core.views import HomeView
from core.services import DashboardService, NotaService
from core.cache_utils import CacheManager

def test_template():
    print("=== Teste do Template Dashboard ===")
    
    # Criar usuário de teste
    User = get_user_model()
    user = User.objects.filter(username='admin').first()
    if not user:
        print("✗ Usuário admin não encontrado")
        return
    
    print(f"✓ Usuário encontrado: {user.username}")
    
    try:
        # Testar serviços individualmente
        dashboard_service = DashboardService(user)
        estatisticas = dashboard_service.obter_estatisticas_gerais()
        print(f"✓ Estatísticas obtidas: {type(estatisticas)}")
        
        graficos = dashboard_service.obter_dados_graficos()
        print(f"✓ Gráficos obtidos: {type(graficos)}")
        
        empresas = CacheManager.get_empresas_list()
        print(f"✓ Empresas obtidas: {len(empresas)} empresas")
        
        nota_service = NotaService(user)
        notas = nota_service.listar_notas()
        print(f"✓ Notas obtidas: {len(notas)} notas")
        
    except Exception as e:
        print(f"✗ Erro nos serviços: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Testar template
        template = get_template('dashboard.html')
        print("✓ Template dashboard.html carregado")
        
        # Criar contexto mínimo
        context = {
            'estatisticas': estatisticas,
            'graficos': graficos,
            'empresas': empresas,
            'notas': notas[:15],  # Primeiras 15 notas
            'user': user
        }
        
        # Tentar renderizar
        html = template.render(context)
        print(f"✓ Template renderizado com sucesso ({len(html)} caracteres)")
        
        # Verificar se contém elementos esperados
        if 'notas-list' in html:
            print("✓ Elemento 'notas-list' encontrado no HTML")
        else:
            print("✗ Elemento 'notas-list' não encontrado no HTML")
            
    except Exception as e:
        print(f"✗ Erro no template: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Testar view diretamente
        factory = RequestFactory()
        request = factory.get('/')
        request.user = user
        
        view = HomeView()
        view.request = request
        
        context_data = view.get_context_data()
        print(f"✓ Contexto da view obtido: {len(context_data)} variáveis")
        print(f"  Variáveis: {list(context_data.keys())}")
        
    except Exception as e:
        print(f"✗ Erro na view: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Teste Concluído ===")

if __name__ == '__main__':
    test_template()