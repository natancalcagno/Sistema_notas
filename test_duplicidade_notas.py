#!/usr/bin/env python
"""
Teste para verificar a validação de duplicidade de notas
baseada no número da nota + empresa
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sistema_notas.settings')
django.setup()

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from core.models import Nota, Contrato
from core.services import NotaService
from core.forms import NotaForm

User = get_user_model()

def test_duplicidade_notas():
    print("=== Teste de Validação de Duplicidade de Notas ===")
    
    # Limpar dados de teste anteriores
    Nota.objects.filter(numero__startswith='TEST').delete()
    Contrato.objects.filter(numero__startswith='0001').delete()
    
    # Criar usuário de teste
    try:
        user = User.objects.get(username='test_user')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='test_user',
            email='test@test.com',
            password='testpass123'
        )
    
    # Criar contrato de teste
    contrato = Contrato.objects.create(
        numero='0001/2024',
        empresa='Empresa Teste',
        valor=Decimal('10000.00'),
        data_inicio=date.today(),
        data_termino=date.today() + timedelta(days=365),
        descricao='Contrato de teste para validação de duplicidade'
    )
    
    print("✓ Dados de teste criados")
    
    # Teste 1: Criar primeira nota
    print("\n--- Teste 1: Criar primeira nota ---")
    try:
        nota1 = Nota.objects.create(
            numero='TEST001',
            empresa='Empresa A',
            valor=Decimal('1000.00'),
            data_entrada=date.today(),
            setor='TI'
            # Não vinculando contrato para evitar validação de empresa
        )
        print(f"✓ Primeira nota criada: {nota1}")
    except Exception as e:
        print(f"✗ Erro ao criar primeira nota: {e}")
        return
    
    # Teste 2: Tentar criar nota duplicada (mesmo número + mesma empresa)
    print("\n--- Teste 2: Tentar criar nota duplicada (mesmo número + mesma empresa) ---")
    try:
        nota2 = Nota(
            numero='TEST001',  # Mesmo número
            empresa='Empresa A',  # Mesma empresa
            valor=Decimal('2000.00'),
            data_entrada=date.today(),
            setor='Financeiro'
        )
        nota2.full_clean()  # Isso deve gerar ValidationError
        nota2.save()
        print("✗ ERRO: Nota duplicada foi criada quando não deveria!")
    except ValidationError as e:
        print(f"✓ Validação funcionou: {e}")
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")
    
    # Teste 3: Criar nota com mesmo número mas empresa diferente (deve funcionar)
    print("\n--- Teste 3: Criar nota com mesmo número mas empresa diferente ---")
    try:
        nota3 = Nota.objects.create(
            numero='TEST001',  # Mesmo número
            empresa='Empresa B',  # Empresa diferente
            valor=Decimal('1500.00'),
            data_entrada=date.today(),
            setor='RH'
        )
        print(f"✓ Nota com empresa diferente criada: {nota3}")
    except Exception as e:
        print(f"✗ Erro ao criar nota com empresa diferente: {e}")
    
    # Teste 4: Criar nota com número diferente mas mesma empresa (deve funcionar)
    print("\n--- Teste 4: Criar nota com número diferente mas mesma empresa ---")
    try:
        nota4 = Nota.objects.create(
            numero='TEST002',  # Número diferente
            empresa='Empresa A',  # Mesma empresa
            valor=Decimal('800.00'),
            data_entrada=date.today(),
            setor='Marketing'
        )
        print(f"✓ Nota com número diferente criada: {nota4}")
    except Exception as e:
        print(f"✗ Erro ao criar nota com número diferente: {e}")
    
    # Teste 5: Testar case-insensitive (empresa com case diferente)
    print("\n--- Teste 5: Testar validação case-insensitive ---")
    try:
        nota5 = Nota(
            numero='TEST001',  # Mesmo número
            empresa='EMPRESA A',  # Mesma empresa mas em maiúscula
            valor=Decimal('3000.00'),
            data_entrada=date.today(),
            setor='Vendas'
        )
        nota5.full_clean()  # Isso deve gerar ValidationError
        nota5.save()
        print("✗ ERRO: Validação case-insensitive falhou!")
    except ValidationError as e:
        print(f"✓ Validação case-insensitive funcionou: {e}")
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")
    
    # Teste 6: Testar NotaService
    print("\n--- Teste 6: Testar NotaService ---")
    service = NotaService(user)
    try:
        dados = {
            'numero': 'TEST001',  # Número já existe para Empresa A
            'empresa': 'Empresa A',
            'valor': Decimal('4000.00'),
            'data_entrada': date.today(),
            'setor': 'Administrativo'
        }
        nota_service = service.criar_nota(dados)
        print("✗ ERRO: NotaService permitiu criar nota duplicada!")
    except ValidationError as e:
        print(f"✓ NotaService validação funcionou: {e}")
    except Exception as e:
        print(f"✗ Erro inesperado no NotaService: {e}")
    
    # Teste 7: Testar formulário
    print("\n--- Teste 7: Testar NotaForm ---")
    form_data = {
        'numero': 'TEST001',  # Número já existe para Empresa A
        'empresa': 'Empresa A',
        'valor': '5000.00',
        'data_entrada': date.today().strftime('%Y-%m-%d'),
        'data_nota': date.today().strftime('%Y-%m-%d'),
        'setor': 'Jurídico'
    }
    form = NotaForm(data=form_data)
    if form.is_valid():
        print("✗ ERRO: Formulário validou dados duplicados!")
    else:
        print(f"✓ Formulário rejeitou dados duplicados: {form.errors}")
    
    # Teste 8: Testar edição de nota existente (deve permitir)
    print("\n--- Teste 8: Testar edição de nota existente ---")
    try:
        # Editar a primeira nota criada
        nota1.valor = Decimal('1200.00')
        nota1.setor = 'TI Atualizado'
        nota1.full_clean()  # Não deve gerar erro
        nota1.save()
        print("✓ Edição de nota existente funcionou")
    except Exception as e:
        print(f"✗ Erro ao editar nota existente: {e}")
    
    # Resumo dos testes
    print("\n=== Resumo dos Testes ===")
    total_notas = Nota.objects.filter(numero__startswith='TEST').count()
    print(f"Total de notas de teste criadas: {total_notas}")
    
    for nota in Nota.objects.filter(numero__startswith='TEST'):
        print(f"- {nota.numero} | {nota.empresa} | R$ {nota.valor}")
    
    # Limpar dados de teste
    print("\n--- Limpando dados de teste ---")
    Nota.objects.filter(numero__startswith='TEST').delete()
    Contrato.objects.filter(numero__startswith='0001').delete()
    User.objects.filter(username='test_user').delete()
    print("✓ Dados de teste removidos")
    
    print("\n=== Teste de Duplicidade Concluído ===")

if __name__ == '__main__':
    test_duplicidade_notas()