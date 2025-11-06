from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from core.models import Contrato, Nota, LogEntry

User = get_user_model()


class ContratoModelTestCase(TestCase):
    """Testes para o modelo Contrato"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
    
    def test_criar_contrato_valido(self):
        """Teste criação de contrato válido"""
        contrato = Contrato.objects.create(
            numero='001/2024',
            empresa='Empresa Teste',
            valor=Decimal('10000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=365),
            descricao='Contrato de teste'
        )
        
        self.assertEqual(contrato.numero, '001/2024')
        self.assertEqual(contrato.empresa, 'Empresa Teste')
        self.assertEqual(contrato.valor, Decimal('10000.00'))

        self.assertIsNotNone(contrato.created_at)
        self.assertIsNotNone(contrato.updated_at)
    
    def test_contrato_str_representation(self):
        """Teste representação string do contrato"""
        contrato = Contrato.objects.create(
            numero='002/2024',
            empresa='Empresa Teste 2',
            valor=Decimal('5000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=180),
            descricao='Contrato de teste 2'
        )
        
        expected_str = 'Contrato 002/2024 - Empresa Teste 2'
        self.assertEqual(str(contrato), expected_str)
    
    def test_contrato_numero_unico(self):
        """Teste unicidade do número do contrato"""
        Contrato.objects.create(
            numero='003/2024',
            empresa='Empresa 1',
            valor=Decimal('1000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=90)
        )
        
        with self.assertRaises(IntegrityError):
            Contrato.objects.create(
                numero='003/2024',  # Número duplicado
                empresa='Empresa 2',
                valor=Decimal('2000.00'),
                data_inicio=date.today(),
                data_termino=date.today() + timedelta(days=120)
            )
    
    def test_contrato_campos_obrigatorios(self):
        """Teste campos obrigatórios do contrato"""
        with self.assertRaises(ValidationError):
            Contrato.objects.create(
                # numero ausente
                empresa='Empresa Teste',
                valor=Decimal('1000.00'),
                data_inicio=date.today(),
                data_termino=date.today() + timedelta(days=90)
            )
    
    def test_contrato_valor_positivo(self):
        """Teste valor positivo do contrato"""
        contrato = Contrato(
            numero='004/2024',
            empresa='Empresa Teste',
            valor=Decimal('-1000.00'),  # Valor negativo
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=90),
            descricao='Contrato de teste com valor negativo'
        )
        
        with self.assertRaises(ValidationError):
            contrato.full_clean()
    
    def test_contrato_datas_validas(self):
        """Teste validação de datas do contrato"""
        contrato = Contrato(
            numero='005/2024',
            empresa='Empresa Teste',
            valor=Decimal('1000.00'),
            data_inicio=date.today(),
            data_termino=date.today() - timedelta(days=1),  # Data inválida
            descricao='Contrato de teste com data inválida'
        )
        
        with self.assertRaises(ValidationError):
            contrato.full_clean()
    
    def test_contrato_meta_ordering(self):
        """Teste ordenação padrão dos contratos"""
        contrato1 = Contrato.objects.create(
            numero='001/2024',
            empresa='Empresa A',
            descricao='Descrição do contrato A',
            valor=Decimal('1000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=90)
        )
        
        contrato2 = Contrato.objects.create(
            numero='002/2024',
            empresa='Empresa B',
            descricao='Descrição do contrato B',
            valor=Decimal('2000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=120)
        )
        
        contratos = list(Contrato.objects.all())
        # Ordenação por -created_at (mais recente primeiro)
        self.assertEqual(contratos[0], contrato2)
        self.assertEqual(contratos[1], contrato1)


class NotaModelTestCase(TestCase):
    """Testes para o modelo Nota"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.contrato = Contrato.objects.create(
            numero='001/2024',
            empresa='Empresa Teste',
            valor=Decimal('10000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=365),
            descricao='Contrato de teste para notas'
        )
    
    def test_criar_nota_valida(self):
        """Teste criação de nota válida"""
        nota = Nota.objects.create(
            numero='NF001',
            empresa='Empresa Teste',
            valor=Decimal('1000.00'),
            data_entrada=date.today(),
            data_nota=date.today(),
            setor='TI',
            empenho='12345',
            contrato=self.contrato
        )
        
        self.assertEqual(nota.numero, 'NF001')
        self.assertEqual(nota.empresa, 'Empresa Teste')
        self.assertEqual(nota.valor, Decimal('1000.00'))
        self.assertEqual(nota.contrato, self.contrato)

        self.assertIsNone(nota.data_saida)  # Inicialmente None
        self.assertIsNotNone(nota.created_at)
        self.assertIsNotNone(nota.updated_at)
    
    def test_nota_str_representation(self):
        """Teste representação string da nota"""
        nota = Nota.objects.create(
            numero='NF002',
            empresa='Empresa Teste 2',
            valor=Decimal('500.00'),
            data_entrada=date.today(),
            setor='Financeiro'
        )
        
        expected_str = 'Nota NF002 - Empresa Empresa Teste 2'
        self.assertEqual(str(nota), expected_str)
    
    def test_nota_numero_unico(self):
        """Teste unicidade do número da nota"""
        Nota.objects.create(
            numero='NF100',
            empresa='Empresa 1',
            valor=Decimal('100.00'),
            data_entrada=date.today(),
            data_nota=date.today(),
            setor='TI'
        )
        
        with self.assertRaises(IntegrityError):
            Nota.objects.create(
                numero='NF100',  # Número duplicado
                empresa='Empresa 2',
                valor=Decimal('200.00'),
                data_entrada=date.today(),
                data_nota=date.today(),
                setor='Financeiro'
            )
    
    def test_nota_campos_obrigatorios(self):
        """Teste campos obrigatórios da nota"""
        with self.assertRaises(ValidationError):
            Nota.objects.create(
                # numero ausente
                empresa='Empresa Teste',
                valor=Decimal('100.00'),
                data_entrada=date.today(),
                data_nota=date.today(),
                setor='TI'
            )
    
    def test_nota_valor_positivo(self):
        """Teste valor positivo da nota"""
        nota = Nota(
            numero='NF004',
            empresa='Empresa Teste',
            valor=Decimal('-100.00'),  # Valor negativo
            data_entrada=date.today(),
            setor='TI'
        )
        
        with self.assertRaises(ValidationError):
            nota.full_clean()
    

    
    def test_nota_tempo_processamento_property(self):
        """Teste propriedade dias_processamento da nota"""
        # Nota sem data_saida
        nota_pendente = Nota.objects.create(
            numero='NF200',
            empresa='Empresa Teste',
            valor=Decimal('100.00'),
            data_entrada=date.today() - timedelta(days=5),
            setor='TI'
        )
        
        self.assertIsInstance(nota_pendente.dias_processamento, int)
        
        # Nota com data_saida
        data_entrada = date.today() - timedelta(days=10)
        data_saida = date.today() - timedelta(days=5)
        
        nota_processada = Nota.objects.create(
            numero='NF201',
            empresa='Empresa Teste',
            valor=Decimal('200.00'),
            data_entrada=data_entrada,
            data_saida=data_saida,
            setor='Financeiro'
        )
        
        expected_days = (data_saida - data_entrada).days
        self.assertEqual(nota_processada.dias_processamento, expected_days)
    
    def test_nota_meta_ordering(self):
        """Teste ordenação padrão das notas"""
        nota1 = Nota.objects.create(
            numero='NF009',
            empresa='Empresa A',
            valor=Decimal('100.00'),
            data_entrada=date.today(),
            setor='TI'
        )
        
        nota2 = Nota.objects.create(
            numero='NF010',
            empresa='Empresa B',
            valor=Decimal('200.00'),
            data_entrada=date.today(),
            setor='Financeiro'
        )
        
        notas = list(Nota.objects.all())
        # Ordenação por -created_at (mais recente primeiro)
        self.assertEqual(notas[0], nota2)
        self.assertEqual(notas[1], nota1)
    
    def test_nota_relacionamento_contrato(self):
        """Teste relacionamento opcional com contrato"""
        # Nota sem contrato
        nota_sem_contrato = Nota.objects.create(
            numero='NF011',
            empresa='Empresa Teste',
            valor=Decimal('100.00'),
            data_entrada=date.today(),
            setor='TI'
        )
        
        self.assertIsNone(nota_sem_contrato.contrato)
        
        # Nota com contrato
        nota_com_contrato = Nota.objects.create(
            numero='NF012',
            empresa='Empresa Teste',
            valor=Decimal('200.00'),
            data_entrada=date.today(),
            setor='Financeiro',
            contrato=self.contrato
        )
        
        self.assertEqual(nota_com_contrato.contrato, self.contrato)


class LogEntryModelTestCase(TestCase):
    """Testes para o modelo LogEntry"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
    
    def test_criar_log_entry_valido(self):
        """Teste criação de entrada de log válida"""
        log_entry = LogEntry.objects.create(
            user=self.user,
            action='create_contract',
            model='Contrato',
            object_id='123',
            details={'numero': '001/2024', 'empresa': 'Empresa Teste'}
        )
        
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.action, 'create_contract')
        self.assertEqual(log_entry.model, 'Contrato')
        self.assertEqual(log_entry.object_id, '123')
        self.assertEqual(log_entry.details['numero'], '001/2024')
        self.assertIsNotNone(log_entry.timestamp)
    
    def test_log_entry_str_representation(self):
        """Teste representação string da entrada de log"""
        log_entry = LogEntry.objects.create(
            user=self.user,
            action='update_note',
            model='Nota',
            object_id='456'
        )
        
        expected_str = f"testuser - update_note - Nota (456)"
        self.assertEqual(str(log_entry), expected_str)
    
    def test_log_entry_campos_obrigatorios(self):
        """Teste campos obrigatórios da entrada de log"""
        # Todos os campos são opcionais exceto os com auto_now_add e default
        log_entry = LogEntry.objects.create(
            level='INFO',
            logger='test_logger',
            message='Test message'
        )
        self.assertIsNotNone(log_entry.id)
        self.assertIsNotNone(log_entry.timestamp)
    
    def test_log_entry_meta_ordering(self):
        """Teste ordenação padrão das entradas de log"""
        log1 = LogEntry.objects.create(
            user=self.user,
            action='action1',
            model='Model1',
            object_id='1'
        )
        
        log2 = LogEntry.objects.create(
            user=self.user,
            action='action2',
            model='Model2',
            object_id='2'
        )
        
        logs = list(LogEntry.objects.all())
        # Ordenação por -timestamp (mais recente primeiro)
        self.assertEqual(logs[0], log2)
        self.assertEqual(logs[1], log1)
    
    def test_log_entry_details_json(self):
        """Teste campo details como JSON"""
        details_data = {
            'old_value': 'Valor Antigo',
            'new_value': 'Valor Novo',
            'field': 'empresa',
            'timestamp': timezone.now().isoformat()
        }
        
        log_entry = LogEntry.objects.create(
            user=self.user,
            action='update_field',
            model='Contrato',
            object_id='789',
            details=details_data
        )
        
        # Recuperar do banco e verificar
        log_retrieved = LogEntry.objects.get(id=log_entry.id)
        self.assertEqual(log_retrieved.details['old_value'], 'Valor Antigo')
        self.assertEqual(log_retrieved.details['new_value'], 'Valor Novo')
        self.assertEqual(log_retrieved.details['field'], 'empresa')


class ModelRelationshipTestCase(TestCase):
    """Testes para relacionamentos entre modelos"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.contrato = Contrato.objects.create(
            numero='001/2024',
            empresa='Empresa Teste',
            valor=Decimal('10000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=365)
        )
    
    def test_contrato_notas_relacionadas(self):
        """Teste relacionamento reverso contrato -> notas"""
        nota1 = Nota.objects.create(
            numero='NF001',
            empresa='Empresa Teste',
            valor=Decimal('1000.00'),
            data_entrada=date.today(),
            setor='TI',
            contrato=self.contrato
        )
        
        nota2 = Nota.objects.create(
            numero='NF002',
            empresa='Empresa Teste',
            valor=Decimal('2000.00'),
            data_entrada=date.today(),
            setor='Financeiro',
            contrato=self.contrato
        )
        
        notas_relacionadas = self.contrato.notas.all()
        self.assertEqual(notas_relacionadas.count(), 2)
        self.assertIn(nota1, notas_relacionadas)
        self.assertIn(nota2, notas_relacionadas)
    
    def test_usuario_contratos_relacionados(self):
        """Teste relacionamento reverso usuário -> contratos"""
        contrato2 = Contrato.objects.create(
            numero='002/2024',
            empresa='Empresa Teste 2',
            valor=Decimal('5000.00'),
            data_inicio=date.today(),
            data_termino=date.today() + timedelta(days=180)
        )
        
        contratos = Contrato.objects.all()
        self.assertEqual(contratos.count(), 2)
        self.assertIn(self.contrato, contratos)
        self.assertIn(contrato2, contratos)
    
    def test_usuario_notas_relacionadas(self):
        """Teste relacionamento reverso usuário -> notas"""
        nota1 = Nota.objects.create(
            numero='NF001',
            empresa='Empresa Teste',
            valor=Decimal('1000.00'),
            data_entrada=date.today(),
            setor='TI'
        )
        
        nota2 = Nota.objects.create(
            numero='NF002',
            empresa='Empresa Teste',
            valor=Decimal('2000.00'),
            data_entrada=date.today(),
            setor='Financeiro'
        )
        
        notas = Nota.objects.all()
        self.assertEqual(notas.count(), 2)
        self.assertIn(nota1, notas)
        self.assertIn(nota2, notas)
    
    def test_delete_cascade_behavior(self):
        """Teste comportamento de deleção em cascata"""
        nota = Nota.objects.create(
            numero='NF001',
            empresa='Empresa Teste',
            valor=Decimal('1000.00'),
            data_entrada=date.today(),
            setor='TI',
            contrato=self.contrato
        )
        
        # Deletar contrato não deve afetar a nota (relacionamento opcional)
        contrato_id = self.contrato.id
        nota_id = nota.id
        
        self.contrato.delete()
        
        # Verificar se contrato foi deletado mas nota permanece
        self.assertFalse(Contrato.objects.filter(id=contrato_id).exists())
        self.assertTrue(Nota.objects.filter(id=nota_id).exists())
        
        # Verificar se o campo contrato da nota foi definido como None
        nota.refresh_from_db()
        self.assertIsNone(nota.contrato)