from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.core.exceptions import ValidationError
import secrets
from datetime import timedelta
from .validators import (
    validate_positive_value, validate_nota_number, 
    validate_empenho_format, validate_empresa_name, validate_cnpj
)
import uuid

class Usuario(AbstractUser):
    ADMIN = 'admin'
    COMUM = 'comum'
    TIPO_USUARIO_CHOICES = [
        (ADMIN, 'Administrador'),
        (COMUM, 'Comum'),
    ]
    tipo_usuario = models.CharField(
        max_length=10,
        choices=TIPO_USUARIO_CHOICES,
        default=COMUM,
        verbose_name='Tipo de Usuário'
    )
    
    # Adicionando related_name para resolver o erro de conflito
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="usuario_set",
        related_query_name="usuario",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="usuario_set",
        related_query_name="usuario",
    )
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        


class Contrato(models.Model):
    numero = models.CharField(
        max_length=50, 
        unique=True, 
        default='0000000000',
        verbose_name='Número do Contrato',
        help_text='Número do contrato',
        db_index=True
    ) # Número do contrato
    empresa = models.CharField(
        max_length=200, 
        verbose_name='Empresa',
        validators=[validate_empresa_name],
        db_index=True
    ) # Empresa
    valor = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.00,
        verbose_name='Valor',
        validators=[validate_positive_value]
    ) # Valor do contrato
    data_inicio = models.DateField(default=timezone.now, verbose_name='Data de Início', db_index=True) # Data de início
    data_termino = models.DateField(default=timezone.now, verbose_name='Data de Término', db_index=True) # Data de término
    descricao = models.TextField(default='', verbose_name='Descrição') # Descrição
    alerta_vencimento = models.IntegerField(default=30) # Alerta de vencimento 30 dias antes
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def dias_para_vencimento(self):
        """Calcula quantos dias faltam para o vencimento do contrato"""
        from datetime import date
        hoje = date.today()
        return (self.data_termino - hoje).days
    
    @property
    def esta_vencendo(self):
        """Verifica se o contrato está próximo do vencimento"""
        return self.dias_para_vencimento <= self.alerta_vencimento
    
    @property
    def status(self):
        """Retorna o status do contrato baseado na data atual"""
        dias_restantes = self.dias_para_vencimento
        
        if dias_restantes < 0:
            return 'Vencido'
        elif dias_restantes <= self.alerta_vencimento:
            return 'Alerta de vencimento'
        else:
            return 'Ativo'

    def clean(self):
        """
        Validação customizada do modelo
        """
        super().clean()
        
        # Validar que data_termino não é anterior a data_inicio
        if self.data_termino and self.data_inicio:
            if self.data_termino < self.data_inicio:
                raise ValidationError({
                    'data_termino': 'Data de término não pode ser anterior à data de início.'
                })
        
        # Validar que o valor é positivo
        if self.valor <= 0:
            raise ValidationError({
                'valor': 'O valor deve ser maior que zero.'
            })
        
        # Validar que a descrição não está vazia
        if not self.descricao or not self.descricao.strip():
            raise ValidationError({
                'descricao': 'This field cannot be blank.'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'Contrato {self.numero} - {self.empresa}'
    
    class Meta:
        verbose_name_plural = 'Contratos'
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['empresa', 'data_inicio']),
            models.Index(fields=['data_termino', 'alerta_vencimento']),
        ]

class Nota(models.Model):
    data_entrada = models.DateField(default=timezone.now, verbose_name='Data de Entrada', db_index=True) # Data de entrada
    empenho = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        verbose_name='Empenho', 
        db_index=True,
        validators=[validate_empenho_format],
        help_text='Apenas números, entre 4 e 10 dígitos'
    ) # Empenho
    empresa = models.CharField(
        max_length=200, 
        verbose_name='Empresa', 
        db_index=True,
        validators=[validate_empresa_name]
    ) # Empresa
    setor = models.CharField(max_length=100, default='', db_index=True) # Setor da nota
    numero = models.CharField(
        max_length=50, 
        verbose_name='Número da Nota',
        validators=[validate_nota_number],
        db_index=True
    ) # Número da nota
    data_nota = models.DateField(default=timezone.now, db_index=True) # Data da nota
    valor = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        verbose_name='Valor',
        validators=[validate_positive_value],
        db_index=True
    ) # Valor
    data_saida = models.DateField(null=True, blank=True, verbose_name='Data de Saída', db_index=True) # Data de saída
    observacoes = models.TextField(null=True, blank=True) # Observações
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Contrato',
        db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def dias_processamento(self):
        """Calcula quantos dias a nota levou/está levando para ser processada"""
        from datetime import date
        data_fim = self.data_saida or date.today()
        return (data_fim - self.data_entrada).days

    def clean(self):
        """
        Validação customizada do modelo
        """
        super().clean()
        
        # Verificar duplicidade de número da nota + empresa
        if self.numero and self.empresa:
            queryset = Nota.objects.filter(
                numero=self.numero,
                empresa__iexact=self.empresa  # Case-insensitive comparison
            )
            # Excluir a própria instância se estiver atualizando
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            
            if queryset.exists():
                raise ValidationError({
                    'numero': f'Já existe uma nota com o número "{self.numero}" para a empresa "{self.empresa}".'
                })
        
        # Validar que data_saida não é anterior a data_entrada
        if self.data_saida and self.data_entrada:
            if self.data_saida < self.data_entrada:
                raise ValidationError({
                    'data_saida': 'Data de saída não pode ser anterior à data de entrada.'
                })
        
        # Validar que o valor é positivo
        if self.valor <= 0:
            raise ValidationError({
                'valor': 'O valor deve ser maior que zero.'
            })
        
        # Validar que a empresa corresponde ao contrato (se aplicável)
        if self.contrato and self.empresa:
            if self.empresa.lower() != self.contrato.empresa.lower():
                raise ValidationError({
                    'empresa': 'A empresa deve corresponder à empresa do contrato selecionado.'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'Nota {self.numero} - Empresa {self.empresa}'

    class Meta:
        verbose_name_plural = 'Notas'
        ordering = ['-data_nota']
        constraints = [
            models.UniqueConstraint(
                fields=['numero', 'empresa'],
                name='unique_numero_empresa'
            )
        ]
        indexes = [
            models.Index(fields=['empresa', 'data_entrada']),
            models.Index(fields=['data_saida', 'data_entrada']),
            models.Index(fields=['contrato', 'data_nota']),
            models.Index(fields=['setor', 'data_entrada']),
        ]
        
class LogEntry(models.Model):
    """
    Modelo para armazenar logs do sistema no banco de dados
    """
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, db_index=True)
    logger = models.CharField(max_length=100, db_index=True)
    message = models.TextField()
    module = models.CharField(max_length=100, blank=True, null=True)
    function = models.CharField(max_length=100, blank=True, null=True)
    line_number = models.IntegerField(blank=True, null=True)
    
    # Campos específicos para auditoria
    user_id = models.IntegerField(blank=True, null=True, db_index=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True, db_index=True)
    action = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    object_id = models.CharField(max_length=100, blank=True, null=True)
    request_id = models.UUIDField(blank=True, null=True, db_index=True)
    
    # Campos para performance
    execution_time = models.FloatField(blank=True, null=True, help_text="Tempo de execução em segundos")
    
    # Campo para exceções
    exception = models.TextField(blank=True, null=True)
    
    # Campos adicionais
    details = models.JSONField(blank=True, null=True, help_text="Detalhes adicionais em formato JSON")
    
    class Meta:
        db_table = 'core_log_entry'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'level']),
            models.Index(fields=['user_id', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['logger', 'level', 'timestamp']),
        ]
        verbose_name = 'Entrada de Log'
        verbose_name_plural = 'Entradas de Log'
    
    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.level} - {self.logger} - {self.message[:50]}..."
    
    @classmethod
    def cleanup_old_logs(cls, days=30):
        """
        Remove logs antigos para manter o banco de dados limpo
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = cls.objects.filter(timestamp__lt=cutoff_date).delete()[0]
        return deleted_count
    
    @classmethod
    def get_stats(cls, days=7):
        """
        Retorna estatísticas dos logs dos últimos dias
        """
        from django.db.models import Count
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        stats = cls.objects.filter(timestamp__gte=cutoff_date).aggregate(
            total_logs=Count('id'),
            error_logs=Count('id', filter=models.Q(level='ERROR')),
            warning_logs=Count('id', filter=models.Q(level='WARNING')),
            info_logs=Count('id', filter=models.Q(level='INFO')),
        )
        
        # Logs por dia
        daily_stats = cls.objects.filter(
            timestamp__gte=cutoff_date
        ).extra(
            select={'day': 'date(timestamp)'}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        stats['daily_logs'] = list(daily_stats)
        
        return stats
        
class Relatorio(models.Model):
    titulo = models.CharField(max_length=200)
    data_geracao = models.DateField(auto_now_add=True)
    conteudo = models.TextField()

    def __str__(self):
        return self.titulo
    
    class Meta:
        verbose_name_plural = 'Relatórios'
        ordering = ['-data_geracao']

class TokenRedefinicaoSenha(models.Model):
    user = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tokens_redefinicao')
    token = models.CharField(max_length=100, unique=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_expiracao = models.DateTimeField()
    usado = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.data_expiracao:
            self.data_expiracao = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_valido(self):
        agora = timezone.now()
        return not self.usado and agora <= self.data_expiracao

    class Meta:
        verbose_name = 'Token de Redefinição de Senha'
        verbose_name_plural = 'Tokens de Redefinição de Senha'
        ordering = ['-data_criacao']
    