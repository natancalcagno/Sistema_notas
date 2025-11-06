from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Nota, Contrato, Usuario
from .cache_utils import CacheManager
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Nota)
def invalidate_nota_cache(sender, instance, created, **kwargs):
    """
    Invalida cache relacionado a notas quando uma nota é criada ou atualizada
    """
    try:
        # Invalidar cache do dashboard
        CacheManager.invalidate_dashboard_cache()
        
        # Invalidar cache de empresas se for uma nova empresa
        if created or hasattr(instance, '_empresa_changed'):
            CacheManager.invalidate_empresas_cache()
        
        # Log da ação
        action = 'criada' if created else 'atualizada'
        logger.info(f'Nota {instance.id} {action}. Cache invalidado.')
        
    except Exception as e:
        logger.error(f'Erro ao invalidar cache após salvar nota: {e}')

@receiver(post_delete, sender=Nota)
def invalidate_nota_cache_on_delete(sender, instance, **kwargs):
    """
    Invalida cache quando uma nota é deletada
    """
    try:
        CacheManager.invalidate_dashboard_cache()
        CacheManager.invalidate_empresas_cache()
        
        logger.info(f'Nota {instance.id} deletada. Cache invalidado.')
        
    except Exception as e:
        logger.error(f'Erro ao invalidar cache após deletar nota: {e}')

@receiver(pre_save, sender=Nota)
def check_empresa_change(sender, instance, **kwargs):
    """
    Verifica se a empresa foi alterada para invalidar cache apropriado
    """
    if instance.pk:
        try:
            old_instance = Nota.objects.get(pk=instance.pk)
            if old_instance.empresa != instance.empresa:
                instance._empresa_changed = True
        except Nota.DoesNotExist:
            pass

@receiver(post_save, sender=Contrato)
def invalidate_contrato_cache(sender, instance, created, **kwargs):
    """
    Invalida cache relacionado a contratos
    """
    try:
        CacheManager.invalidate_contratos_cache()
        
        action = 'criado' if created else 'atualizado'
        logger.info(f'Contrato {instance.id} {action}. Cache invalidado.')
        
    except Exception as e:
        logger.error(f'Erro ao invalidar cache após salvar contrato: {e}')

@receiver(post_delete, sender=Contrato)
def invalidate_contrato_cache_on_delete(sender, instance, **kwargs):
    """
    Invalida cache quando um contrato é deletado
    """
    try:
        CacheManager.invalidate_contratos_cache()
        
        logger.info(f'Contrato {instance.id} deletado. Cache invalidado.')
        
    except Exception as e:
        logger.error(f'Erro ao invalidar cache após deletar contrato: {e}')

@receiver(post_save, sender=Usuario)
def log_usuario_activity(sender, instance, created, **kwargs):
    """
    Log de atividades de usuário
    """
    try:
        action = 'criado' if created else 'atualizado'
        logger.info(f'Usuário {instance.username} {action}.')
        
    except Exception as e:
        logger.error(f'Erro ao registrar atividade do usuário: {e}')

# Signal personalizado para limpeza de cache em horários específicos
from django.core.management.base import BaseCommand
from django.core.cache import cache
from datetime import datetime

class CacheCleaner:
    """
    Utilitário para limpeza automática de cache
    """
    
    @staticmethod
    def clear_expired_cache():
        """
        Limpa cache expirado (pode ser chamado via cron job)
        """
        try:
            # Limpar cache específico baseado em horário
            now = datetime.now()
            
            # Limpar cache de estatísticas a cada hora
            if now.minute == 0:
                cache.delete_pattern('dashboard_stats_*')
                cache.delete_pattern('monthly_stats_*')
                logger.info('Cache de estatísticas limpo automaticamente.')
            
            # Limpar cache de empresas a cada 6 horas
            if now.hour % 6 == 0 and now.minute == 0:
                cache.delete('empresas_list')
                logger.info('Cache de empresas limpo automaticamente.')
                
        except Exception as e:
            logger.error(f'Erro na limpeza automática de cache: {e}')