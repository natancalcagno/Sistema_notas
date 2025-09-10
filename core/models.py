from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
import secrets
from datetime import timedelta

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
    numero = models.CharField(max_length=20, unique=True, default='0000000000') # Número do contrato
    empresa = models.CharField(max_length=200) # Empresa
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Valor do contrato
    data_inicio = models.DateField(default=timezone.now) # Data de início
    data_termino = models.DateField(default=timezone.now) # Data de término
    descricao = models.TextField(default='') # Descrição
    alerta_vencimento = models.IntegerField(default=30) # Alerta de vencimento 30 dias antes
    

    def __str__(self):
        return f'Contrato {self.numero} - {self.empresa}'
    
    class Meta:
        verbose_name_plural = 'Contratos'
        ordering = ['-data_inicio']

class Nota(models.Model):
    data_entrada = models.DateField(default=timezone.now) # Data de entrada
    empenho = models.CharField(max_length=20, null=True, blank=True) # Empenho
    empresa = models.CharField(max_length=200) # Empresa
    setor = models.CharField(max_length=100, default='') # Setor da nota
    numero = models.CharField(max_length=50, unique=True) # Número da nota
    data_nota = models.DateField(default=timezone.now) # Data da nota
    valor = models.DecimalField(max_digits=10, decimal_places=2) # Valor
    data_saida = models.DateField(null=True, blank=True) # Data de saída
    observacoes = models.TextField(null=True, blank=True) # Observações
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Contrato'
    )

    def __str__(self):
        return f'Nota {self.numero} - Empresa {self.empresa}'

    class Meta:
        verbose_name_plural = 'Notas'
        ordering = ['-data_nota']
        
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
    