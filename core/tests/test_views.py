from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from core.models import Contrato, Nota

User = get_user_model()


class BaseViewTestCase(TestCase):
    """Classe base para testes de views"""
    
    def setUp(self):
        self.client = Client()
        
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
            descricao='Contrato de teste para views'
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


class LoginViewTestCase(BaseViewTestCase):
    """Testes para LoginView"""
    
    def test_login_view_get(self):
        """Teste GET na view de login"""
        response = self.client.get(reverse('core:login'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')
        self.assertContains(response, 'form')
    
    def test_login_view_post_valid(self):
        """Teste POST válido na view de login"""
        response = self.client.post(reverse('core:login'), {
            'username': 'admin',
            'password': 'testpass123'
        })
        
        self.assertRedirects(response, reverse('core:home'))
    
    def test_login_view_post_invalid(self):
        """Teste POST inválido na view de login"""
        response = self.client.post(reverse('core:login'), {
            'username': 'admin',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Credenciais inválidas')
    
    def test_login_redirect_authenticated_user(self):
        """Teste redirecionamento de usuário já autenticado"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:login'))
        
        self.assertRedirects(response, reverse('core:home'))


class HomeViewTestCase(BaseViewTestCase):
    """Testes para HomeView"""
    
    def test_home_view_requires_login(self):
        """Teste que home requer login"""
        response = self.client.get(reverse('core:home'))
        
        self.assertRedirects(response, f"{reverse('core:login')}?next={reverse('core:home')}")
    
    @patch('core.views.DashboardService')
    def test_home_view_authenticated(self, mock_dashboard_service):
        """Teste home view com usuário autenticado"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_dashboard_service.return_value = mock_service_instance
        mock_service_instance.obter_estatisticas_gerais.return_value = {
            'contratos': {'total': 1, 'ativos': 1},
            'notas': {'total': 1, 'pendentes': 1, 'processadas': 0}
        }
        mock_service_instance.obter_dados_graficos.return_value = {
            'notas_por_mes': [0] * 12,
            'notas_por_setor': [{'setor': 'TI', 'total': 1}]
        }
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
        self.assertIn('estatisticas', response.context)
        self.assertIn('dados_graficos', response.context)
    
    @patch('core.views.DashboardService')
    def test_home_view_service_error(self, mock_dashboard_service):
        """Teste home view com erro no service"""
        # Mock do service com erro
        mock_service_instance = MagicMock()
        mock_dashboard_service.return_value = mock_service_instance
        mock_service_instance.obter_estatisticas_gerais.side_effect = Exception('Erro no service')
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Erro ao carregar dados do dashboard')


class ContratoViewsTestCase(BaseViewTestCase):
    """Testes para views de Contrato"""
    
    def test_contrato_list_requires_login(self):
        """Teste que lista de contratos requer login"""
        response = self.client.get(reverse('core:contrato_list'))
        
        self.assertRedirects(response, f"{reverse('core:login')}?next={reverse('core:contrato_list')}")
    
    def test_contrato_list_authenticated(self):
        """Teste lista de contratos com usuário autenticado"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:contrato_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contratos')
        self.assertContains(response, self.contrato.numero)
        self.assertContains(response, self.contrato.empresa)
    
    def test_contrato_list_with_filters(self):
        """Teste lista de contratos com filtros"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:contrato_list'), {
            'empresa': 'Empresa Teste'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contrato.numero)
    
    def test_contrato_create_get(self):
        """Teste GET na criação de contrato"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:contrato_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Novo Contrato')
        self.assertContains(response, 'form')
    
    @patch('core.views.ContratoService')
    def test_contrato_create_post_valid(self, mock_contrato_service):
        """Teste POST válido na criação de contrato"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_contrato_service.return_value = mock_service_instance
        mock_service_instance.criar_contrato.return_value = self.contrato
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:contrato_create'), {
            'numero': '002/2024',
            'empresa': 'Nova Empresa',
            'valor': '15000.00',
            'data_inicio': date.today().strftime('%Y-%m-%d'),
            'data_termino': (date.today() + timedelta(days=365)).strftime('%Y-%m-%d'),
            'descricao': 'Novo contrato'
        })
        
        self.assertRedirects(response, reverse('core:contrato_list'))
        mock_service_instance.criar_contrato.assert_called_once()
    
    def test_contrato_update_get(self):
        """Teste GET na atualização de contrato"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:contrato_update', args=[self.contrato.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Contrato')
        self.assertContains(response, self.contrato.numero)
    
    @patch('core.views.ContratoService')
    def test_contrato_update_post_valid(self, mock_contrato_service):
        """Teste POST válido na atualização de contrato"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_contrato_service.return_value = mock_service_instance
        mock_service_instance.atualizar_contrato.return_value = self.contrato
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:contrato_update', args=[self.contrato.pk]), {
            'numero': self.contrato.numero,
            'empresa': 'Empresa Atualizada',
            'valor': '12000.00',
            'data_inicio': self.contrato.data_inicio.strftime('%Y-%m-%d'),
            'data_termino': self.contrato.data_termino.strftime('%Y-%m-%d'),
            'descricao': 'Contrato atualizado'
        })
        
        self.assertRedirects(response, reverse('core:contrato_list'))
        mock_service_instance.atualizar_contrato.assert_called_once()
    
    def test_contrato_delete_get(self):
        """Teste GET na deleção de contrato"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:contrato_delete', args=[self.contrato.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar Exclusão')
        self.assertContains(response, self.contrato.numero)
    
    def test_contrato_delete_post(self):
        """Teste POST na deleção de contrato"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:contrato_delete', args=[self.contrato.pk]))
        
        self.assertRedirects(response, reverse('core:contrato_list'))
        self.assertFalse(Contrato.objects.filter(pk=self.contrato.pk).exists())
    
    def test_contrato_access_permission(self):
        """Teste permissão de acesso aos contratos"""
        # Criar contrato de outro usuário
        outro_contrato = Contrato.objects.create(
            numero='999/2024',
            empresa='Empresa Privada',
            valor=Decimal('5000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=180)
        )
        
        # Admin pode ver todos os contratos
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:contrato_list'))
        self.assertContains(response, outro_contrato.numero)
        
        # Usuário regular só vê seus próprios contratos
        self.client.login(username='user', password='testpass123')
        response = self.client.get(reverse('core:contrato_list'))
        self.assertContains(response, outro_contrato.numero)
        self.assertNotContains(response, self.contrato.numero)


class NotaViewsTestCase(BaseViewTestCase):
    """Testes para views de Nota"""
    
    def test_nota_list_requires_login(self):
        """Teste que lista de notas requer login"""
        response = self.client.get(reverse('core:nota_list'))
        
        self.assertRedirects(response, f"{reverse('core:login')}?next={reverse('core:nota_list')}")
    
    def test_nota_list_authenticated(self):
        """Teste lista de notas com usuário autenticado"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:nota_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Notas')
        self.assertContains(response, self.nota.numero)
        self.assertContains(response, self.nota.empresa)
    
    def test_nota_list_with_search(self):
        """Teste lista de notas com busca"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:nota_list'), {
            'busca': 'NF001'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.nota.numero)
    
    def test_nota_create_get(self):
        """Teste GET na criação de nota"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:nota_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nova Nota')
        self.assertContains(response, 'form')
    
    @patch('core.views.NotaService')
    def test_nota_create_post_valid(self, mock_nota_service):
        """Teste POST válido na criação de nota"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_nota_service.return_value = mock_service_instance
        mock_service_instance.criar_nota.return_value = self.nota
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:nota_create'), {
            'numero': 'NF002',
            'empresa': 'Nova Empresa',
            'valor': '2000.00',
            'data_entrada': date.today().strftime('%Y-%m-%d'),
            'data_nota': date.today().strftime('%Y-%m-%d'),
            'setor': 'Financeiro',
            'empenho': 'EMP002',
            'contrato': self.contrato.pk
        })
        
        self.assertRedirects(response, reverse('core:nota_list'))
        mock_service_instance.criar_nota.assert_called_once()
    
    def test_nota_update_get(self):
        """Teste GET na atualização de nota"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:nota_update', args=[self.nota.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Nota')
        self.assertContains(response, self.nota.numero)
    
    @patch('core.views.NotaService')
    def test_nota_update_post_valid(self, mock_nota_service):
        """Teste POST válido na atualização de nota"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_nota_service.return_value = mock_service_instance
        mock_service_instance.atualizar_nota.return_value = self.nota
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:nota_update', args=[self.nota.pk]), {
            'numero': self.nota.numero,
            'empresa': 'Empresa Atualizada',
            'valor': '1500.00',
            'data_entrada': self.nota.data_entrada.strftime('%Y-%m-%d'),
            'data_nota': self.nota.data_nota.strftime('%Y-%m-%d'),
            'setor': 'TI Atualizado',
            'empenho': self.nota.empenho,
            'contrato': self.contrato.pk
        })
        
        self.assertRedirects(response, reverse('core:nota_list'))
        mock_service_instance.atualizar_nota.assert_called_once()
    
    def test_nota_delete_get(self):
        """Teste GET na deleção de nota"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:nota_delete', args=[self.nota.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar Exclusão')
        self.assertContains(response, self.nota.numero)
    
    def test_nota_delete_post(self):
        """Teste POST na deleção de nota"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:nota_delete', args=[self.nota.pk]))
        
        self.assertRedirects(response, reverse('core:nota_list'))
        self.assertFalse(Nota.objects.filter(pk=self.nota.pk).exists())
    
    @patch('core.views.NotaService')
    def test_processar_nota_post(self, mock_nota_service):
        """Teste processamento de nota"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_nota_service.return_value = mock_service_instance
        mock_service_instance.processar_nota.return_value = self.nota
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:processar_nota', args=[self.nota.pk]))
        
        self.assertRedirects(response, reverse('core:nota_list'))
        mock_service_instance.processar_nota.assert_called_once_with(self.nota.pk)


class RelatoriosViewTestCase(BaseViewTestCase):
    """Testes para RelatoriosView"""
    
    def test_relatorios_requires_login(self):
        """Teste que relatórios requer login"""
        response = self.client.get(reverse('core:relatorios'))
        
        self.assertRedirects(response, f"{reverse('core:login')}?next={reverse('core:relatorios')}")
    
    @patch('core.views.RelatorioService')
    def test_relatorios_authenticated(self, mock_relatorio_service):
        """Teste relatórios com usuário autenticado"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_relatorio_service.return_value = mock_service_instance
        mock_service_instance.gerar_relatorio_notas.return_value = {
            'notas': [self.nota],
            'estatisticas': {'total_notas': 1, 'valor_total': 1000.00}
        }
        mock_service_instance.gerar_relatorio_contratos.return_value = {
            'contratos': [self.contrato],
            'estatisticas': {'total_contratos': 1, 'valor_total': 10000.00}
        }
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:relatorios'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Relatórios')
        self.assertIn('relatorio_notas', response.context)
        self.assertIn('relatorio_contratos', response.context)
    
    @patch('core.views.RelatorioService')
    def test_relatorios_with_filters(self, mock_relatorio_service):
        """Teste relatórios com filtros"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_relatorio_service.return_value = mock_service_instance
        mock_service_instance.gerar_relatorio_notas.return_value = {
            'notas': [self.nota],
            'estatisticas': {'total_notas': 1, 'valor_total': 1000.00}
        }
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:relatorios'), {
            'data_inicio': date.today().strftime('%Y-%m-%d'),
            'data_fim': date.today().strftime('%Y-%m-%d'),
            'empresa': 'Empresa Teste'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_service_instance.gerar_relatorio_notas.assert_called_once()


class UsuarioViewsTestCase(BaseViewTestCase):
    """Testes para views de Usuário"""
    
    def test_usuario_list_requires_admin(self):
        """Teste que lista de usuários requer admin"""
        self.client.login(username='user', password='testpass123')
        response = self.client.get(reverse('core:usuario_list'))
        
        self.assertEqual(response.status_code, 403)
    
    def test_usuario_list_admin_access(self):
        """Teste acesso de admin à lista de usuários"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:usuario_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuários')
        self.assertContains(response, self.admin_user.username)
        self.assertContains(response, self.regular_user.username)
    
    def test_usuario_create_requires_admin(self):
        """Teste que criação de usuário requer admin"""
        self.client.login(username='user', password='testpass123')
        response = self.client.get(reverse('core:usuario_create'))
        
        self.assertEqual(response.status_code, 403)
    
    def test_usuario_create_admin_access(self):
        """Teste acesso de admin à criação de usuário"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:usuario_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Novo Usuário')
        self.assertContains(response, 'form')
    
    @patch('core.views.UsuarioService')
    def test_usuario_create_post_valid(self, mock_usuario_service):
        """Teste POST válido na criação de usuário"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_usuario_service.return_value = mock_service_instance
        new_user = User.objects.create_user(
            username='newuser',
            email='newuser@test.com',
            first_name='New',
            last_name='User'
        )
        mock_service_instance.criar_usuario.return_value = new_user
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:usuario_create'), {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123'
        })
        
        self.assertRedirects(response, reverse('core:usuario_list'))
        mock_service_instance.criar_usuario.assert_called_once()
    
    def test_usuario_update_requires_admin(self):
        """Teste que atualização de usuário requer admin"""
        self.client.login(username='user', password='testpass123')
        response = self.client.get(reverse('core:usuario_update', args=[self.regular_user.pk]))
        
        self.assertEqual(response.status_code, 403)
    
    def test_usuario_update_admin_access(self):
        """Teste acesso de admin à atualização de usuário"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:usuario_update', args=[self.regular_user.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Usuário')
        self.assertContains(response, self.regular_user.username)
    
    @patch('core.views.UsuarioService')
    def test_usuario_update_post_valid(self, mock_usuario_service):
        """Teste POST válido na atualização de usuário"""
        # Mock do service
        mock_service_instance = MagicMock()
        mock_usuario_service.return_value = mock_service_instance
        mock_service_instance.atualizar_usuario.return_value = self.regular_user
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('core:usuario_update', args=[self.regular_user.pk]), {
            'username': self.regular_user.username,
            'email': 'updated@test.com',
            'first_name': 'Updated',
            'last_name': 'User'
        })
        
        self.assertRedirects(response, reverse('core:usuario_list'))
        mock_service_instance.atualizar_usuario.assert_called_once()


class ViewPermissionTestCase(BaseViewTestCase):
    """Testes para permissões das views"""
    
    def test_anonymous_user_redirected_to_login(self):
        """Teste que usuário anônimo é redirecionado para login"""
        protected_urls = [
            reverse('core:home'),
            reverse('core:contrato_list'),
            reverse('core:nota_list'),
            reverse('core:relatorios'),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('core:login')}?next={url}")
    
    def test_regular_user_access_restrictions(self):
        """Teste restrições de acesso para usuário regular"""
        self.client.login(username='user', password='testpass123')
        
        # Usuário regular não pode acessar gerenciamento de usuários
        admin_only_urls = [
            reverse('core:usuario_list'),
            reverse('core:usuario_create'),
            reverse('core:usuario_update', args=[self.admin_user.pk]),
        ]
        
        for url in admin_only_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
    
    def test_admin_user_full_access(self):
        """Teste acesso completo para usuário admin"""
        self.client.login(username='admin', password='testpass123')
        
        # Admin pode acessar todas as views
        all_urls = [
            reverse('core:home'),
            reverse('core:contrato_list'),
            reverse('core:nota_list'),
            reverse('core:relatorios'),
            reverse('core:usuario_list'),
            reverse('core:usuario_create'),
        ]
        
        for url in all_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 302])  # 200 OK ou 302 Redirect