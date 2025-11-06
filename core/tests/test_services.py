from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from core.services import (
    ContratoService, NotaService, UsuarioService, 
    DashboardService, RelatorioService
)
from core.models import Contrato, Nota

User = get_user_model()


class BaseServiceTestCase(TestCase):
    """Classe base para testes de services"""
    
    def setUp(self):
        # Criar usuários de teste
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            first_name='Admin',
            last_name='User'
        )
        
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
            is_staff=False,
            first_name='Regular',
            last_name='User'
        )
        
        # Criar contrato de teste
        self.contrato = Contrato.objects.create(
            numero='001/2024',
            empresa='Empresa Teste',
            valor=Decimal('10000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=365),
            descricao='Contrato de teste para services'
        )
        
        # Criar nota de teste
        self.nota = Nota.objects.create(
            numero='NF001',
            empresa='Empresa Teste',
            valor=Decimal('1000.00'),
            data_entrada=date.today(),
            data_nota=date.today(),
            setor='TI',
            empenho='12345',
            contrato=self.contrato
        )


class UsuarioServiceTestCase(BaseServiceTestCase):
    """Testes para UsuarioService"""
    
    def setUp(self):
        super().setUp()
        self.service = UsuarioService(self.admin_user)
    
    def test_criar_usuario_sucesso(self):
        """Teste criação de usuário com sucesso"""
        dados = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123'
        }
        
        usuario = self.service.criar_usuario(dados)
        
        self.assertEqual(usuario.username, 'newuser')
        self.assertEqual(usuario.email, 'newuser@test.com')
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_criar_usuario_username_duplicado(self):
        """Teste criação de usuário com username duplicado"""
        dados = {
            'username': 'admin',  # Username já existe
            'email': 'newadmin@test.com',
            'first_name': 'New',
            'last_name': 'Admin'
        }
        
        with self.assertRaises(ValidationError) as context:
            self.service.criar_usuario(dados)
        
        self.assertIn('Nome de usuário já existe', str(context.exception))
    
    def test_criar_usuario_campos_obrigatorios(self):
        """Teste criação de usuário sem campos obrigatórios"""
        dados = {
            'username': 'incomplete',
            # Faltando email, first_name, last_name
        }
        
        with self.assertRaises(ValidationError) as context:
            self.service.criar_usuario(dados)
        
        self.assertIn('Campo email é obrigatório', str(context.exception))
    
    def test_atualizar_usuario_sucesso(self):
        """Teste atualização de usuário com sucesso"""
        dados = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@test.com'
        }
        
        usuario = self.service.atualizar_usuario(self.regular_user.id, dados)
        
        self.assertEqual(usuario.first_name, 'Updated')
        self.assertEqual(usuario.last_name, 'Name')
        self.assertEqual(usuario.email, 'updated@test.com')
    
    def test_atualizar_usuario_sem_permissao(self):
        """Teste atualização de usuário sem permissão"""
        service = UsuarioService(self.regular_user)  # Usuário não-admin
        dados = {'first_name': 'Hacked'}
        
        with self.assertRaises(ValidationError) as context:
            service.atualizar_usuario(self.admin_user.id, dados)
        
        self.assertIn('Sem permissão', str(context.exception))
    
    def test_listar_usuarios_com_filtros(self):
        """Teste listagem de usuários com filtros"""
        filtros = {'ativo': True, 'staff': True}
        usuarios = self.service.listar_usuarios(filtros)
        
        self.assertIn(self.admin_user, usuarios)
        self.assertNotIn(self.regular_user, usuarios)
    
    def test_listar_usuarios_busca(self):
        """Teste listagem de usuários com busca"""
        filtros = {'busca': 'Admin'}
        usuarios = self.service.listar_usuarios(filtros)
        
        self.assertIn(self.admin_user, usuarios)
        self.assertNotIn(self.regular_user, usuarios)


class ContratoServiceTestCase(BaseServiceTestCase):
    """Testes para ContratoService"""
    
    def setUp(self):
        super().setUp()
        self.service = ContratoService(self.admin_user)
    
    def test_criar_contrato_sucesso(self):
        """Teste criação de contrato com sucesso"""
        dados = {
            'numero': '002/2024',
            'empresa': 'Nova Empresa',
            'valor': Decimal('15000.00'),
            'data_inicio': date.today(),
            'data_termino': date.today() + timedelta(days=180),
            'descricao': 'Novo contrato'
        }
        
        contrato = self.service.criar_contrato(dados)
        
        self.assertEqual(contrato.numero, '002/2024')
        self.assertEqual(contrato.empresa, 'Nova Empresa')
        self.assertEqual(contrato.valor, Decimal('15000.00'))
    
    def test_criar_contrato_numero_duplicado(self):
        """Teste criação de contrato com número duplicado"""
        dados = {
            'numero': '001/2024',  # Número já existe
            'empresa': 'Empresa Duplicada',
            'valor': Decimal('5000.00'),
            'data_inicio': date.today(),
            'data_termino': date.today() + timedelta(days=90)
        }
        
        with self.assertRaises(ValidationError) as context:
            self.service.criar_contrato(dados)
        
        self.assertIn('Número do contrato já existe', str(context.exception))
    
    def test_criar_contrato_datas_invalidas(self):
        """Teste criação de contrato com datas inválidas"""
        dados = {
            'numero': '003/2024',
            'empresa': 'Empresa Teste',
            'valor': Decimal('5000.00'),
            'data_inicio': date.today(),
            'data_termino': date.today() - timedelta(days=1)  # Data inválida
        }
        
        with self.assertRaises(ValidationError) as context:
            self.service.criar_contrato(dados)
        
        self.assertIn('Data de término deve ser posterior', str(context.exception))
    
    def test_atualizar_contrato_sucesso(self):
        """Teste atualização de contrato com sucesso"""
        dados = {
            'empresa': 'Empresa Atualizada',
            'valor': Decimal('12000.00')
        }
        
        contrato = self.service.atualizar_contrato(self.contrato.id, dados)
        
        self.assertEqual(contrato.empresa, 'Empresa Atualizada')
        self.assertEqual(contrato.valor, Decimal('12000.00'))
    
    def test_atualizar_contrato_sem_permissao(self):
        """Teste atualização de contrato sem permissão"""
        service = ContratoService(self.regular_user)
        dados = {'empresa': 'Hacked'}
        
        with self.assertRaises(ValidationError) as context:
            service.atualizar_contrato(self.contrato.id, dados)
        
        self.assertIn('Sem permissão', str(context.exception))
    
    def test_listar_contratos_filtros(self):
        """Teste listagem de contratos com filtros"""
        filtros = {'empresa': 'Empresa Teste'}
        contratos = self.service.listar_contratos(filtros)
        
        self.assertIn(self.contrato, contratos)
    
    def test_obter_estatisticas_contrato(self):
        """Teste obtenção de estatísticas do contrato"""
        stats = self.service.obter_estatisticas_contrato(self.contrato.id)
        
        self.assertEqual(stats['total_notas'], 1)
        self.assertEqual(stats['notas_pendentes'], 1)
        self.assertEqual(stats['notas_processadas'], 0)
        self.assertEqual(stats['valor_total_notas'], Decimal('1000.00'))


class NotaServiceTestCase(BaseServiceTestCase):
    """Testes para NotaService"""
    
    def setUp(self):
        super().setUp()
        self.service = NotaService(self.admin_user)
    
    def test_criar_nota_sucesso(self):
        """Teste criação de nota com sucesso"""
        dados = {
            'numero': 'NF002',
            'empresa': 'Empresa Nota',
            'valor': Decimal('2000.00'),
            'data_entrada': date.today(),
            'setor': 'Financeiro',
            'empenho': 'EMP002',
            'contrato_id': self.contrato.id
        }
        
        nota = self.service.criar_nota(dados)
        
        self.assertEqual(nota.numero, 'NF002')
        self.assertEqual(nota.empresa, 'Empresa Nota')
        self.assertEqual(nota.valor, Decimal('2000.00'))
    
    def test_criar_nota_numero_duplicado(self):
        """Teste criação de nota com número duplicado"""
        dados = {
            'numero': 'NF001',  # Número já existe
            'empresa': 'Empresa Duplicada',
            'valor': Decimal('500.00'),
            'data_entrada': date.today(),
            'setor': 'TI'
        }
        
        with self.assertRaises(ValidationError) as context:
            self.service.criar_nota(dados)
        
        self.assertIn('Número da nota já existe', str(context.exception))
    
    def test_processar_nota_sucesso(self):
        """Teste processamento de nota com sucesso"""
        data_saida = date.today()
        nota = self.service.processar_nota(self.nota.id, data_saida)
        
        self.assertEqual(nota.data_saida, data_saida)
    
    def test_processar_nota_ja_processada(self):
        """Teste processamento de nota já processada"""
        # Processar a nota primeiro
        self.nota.data_saida = date.today()
        self.nota.save()
        
        with self.assertRaises(ValidationError) as context:
            self.service.processar_nota(self.nota.id)
        
        self.assertIn('Nota já foi processada', str(context.exception))
    
    def test_listar_notas_filtros(self):
        """Teste listagem de notas com filtros"""
        filtros = {'empresa': 'Empresa Teste'}
        notas = self.service.listar_notas(filtros)
        
        self.assertIn(self.nota, notas)


class DashboardServiceTestCase(BaseServiceTestCase):
    """Testes para DashboardService"""
    
    def setUp(self):
        super().setUp()
        self.service = DashboardService(self.admin_user)
    
    def test_obter_estatisticas_gerais(self):
        """Teste obtenção de estatísticas gerais"""
        stats = self.service.obter_estatisticas_gerais()
        
        self.assertIn('contratos', stats)
        self.assertIn('notas', stats)
        self.assertEqual(stats['contratos']['total'], 1)
        self.assertEqual(stats['notas']['total'], 1)
        self.assertEqual(stats['notas']['pendentes'], 1)
        self.assertEqual(stats['notas']['processadas'], 0)
    
    def test_obter_dados_graficos(self):
        """Teste obtenção de dados para gráficos"""
        dados = self.service.obter_dados_graficos()
        
        self.assertIn('notas_por_mes', dados)
        self.assertIn('notas_por_setor', dados)
        self.assertEqual(len(dados['notas_por_mes']), 12)
        self.assertTrue(len(dados['notas_por_setor']) >= 1)


class RelatorioServiceTestCase(BaseServiceTestCase):
    """Testes para RelatorioService"""
    
    def setUp(self):
        super().setUp()
        self.service = RelatorioService(self.admin_user)
    
    def test_gerar_relatorio_contratos(self):
        """Teste geração de relatório de contratos"""
        relatorio = self.service.gerar_relatorio_contratos()
        
        self.assertIn('contratos', relatorio)
        self.assertIn('estatisticas', relatorio)
        self.assertEqual(relatorio['estatisticas']['total_contratos'], 1)
        self.assertEqual(relatorio['estatisticas']['valor_total'], float(self.contrato.valor))
    
    def test_gerar_relatorio_notas(self):
        """Teste geração de relatório de notas"""
        relatorio = self.service.gerar_relatorio_notas()
        
        self.assertIn('notas', relatorio)
        self.assertIn('estatisticas', relatorio)
        self.assertEqual(relatorio['estatisticas']['total_notas'], 1)
        self.assertEqual(relatorio['estatisticas']['notas_pendentes'], 1)
        self.assertEqual(relatorio['estatisticas']['notas_processadas'], 0)
        self.assertEqual(relatorio['estatisticas']['valor_total'], float(self.nota.valor))
    
    def test_gerar_relatorio_notas_com_filtros(self):
        """Teste geração de relatório de notas com filtros"""
        filtros = {'empresa': 'Empresa Teste'}
        relatorio = self.service.gerar_relatorio_notas(filtros)
        
        self.assertEqual(len(relatorio['notas']), 1)
        self.assertEqual(relatorio['notas'][0]['empresa'], 'Empresa Teste')


class ServiceIntegrationTestCase(BaseServiceTestCase):
    """Testes de integração entre services"""
    
    def test_workflow_completo(self):
        """Teste workflow completo: criar contrato, criar nota, processar nota"""
        # 1. Criar contrato
        contrato_service = ContratoService(self.admin_user)
        dados_contrato = {
            'numero': '100/2024',
            'empresa': 'Empresa Workflow',
            'valor': Decimal('50000.00'),
            'data_inicio': date.today(),
            'data_termino': date.today() + timedelta(days=365)
        }
        contrato = contrato_service.criar_contrato(dados_contrato)
        
        # 2. Criar nota vinculada ao contrato
        nota_service = NotaService(self.admin_user)
        dados_nota = {
            'numero': 'NF100',
            'empresa': 'Empresa Workflow',
            'valor': Decimal('5000.00'),
            'data_entrada': date.today(),
            'setor': 'Administrativo',
            'contrato_id': contrato.id
        }
        nota = nota_service.criar_nota(dados_nota)
        
        # 3. Processar nota
        nota_processada = nota_service.processar_nota(nota.id)
        
        # 4. Verificar estatísticas
        stats = contrato_service.obter_estatisticas_contrato(contrato.id)
        
        # Verificações
        self.assertEqual(contrato.numero, '100/2024')
        self.assertEqual(nota.contrato, contrato)
        self.assertIsNotNone(nota_processada.data_saida)
        self.assertEqual(stats['total_notas'], 1)
        self.assertEqual(stats['notas_processadas'], 1)
    
    @patch('core.services.audit_logger')
    def test_auditoria_logs(self, mock_audit_logger):
        """Teste se os logs de auditoria são chamados corretamente"""
        contrato_service = ContratoService(self.admin_user)
        dados = {
            'numero': '002/2024',
            'empresa': 'Nova Empresa',
            'valor': Decimal('5000.00'),
            'data_inicio': date.today(),
            'data_termino': date.today() + timedelta(days=180),
            'descricao': 'Novo contrato de teste'
        }
        
        contrato_service.criar_contrato(dados)
        
        # Verificar se o log de auditoria foi chamado
        mock_audit_logger.log_user_action.assert_called_once()
        call_args = mock_audit_logger.log_user_action.call_args
        self.assertEqual(call_args[1]['action'], 'create_contract')
        self.assertEqual(call_args[1]['model'], 'Contrato')
        self.assertEqual(call_args[1]['user_id'], self.admin_user.id)