from django.core.cache import cache
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Nota, Contrato

class CacheManager:
    """
    Gerenciador de cache para otimizar consultas frequentes
    """
    
    # Tempos de cache em segundos
    CACHE_TIMEOUT_SHORT = 300  # 5 minutos
    CACHE_TIMEOUT_MEDIUM = 900  # 15 minutos
    CACHE_TIMEOUT_LONG = 3600  # 1 hora
    
    @staticmethod
    def get_dashboard_stats(user_id=None):
        """
        Cache das estatísticas do dashboard
        """
        cache_key = f'dashboard_stats_{user_id or "all"}'
        stats = cache.get(cache_key)
        
        if stats is None:
            queryset = Nota.objects.select_related('contrato')
            
            stats = {
                'total_notas': queryset.count(),
                'valor_total': queryset.aggregate(total=Sum('valor'))['total'] or 0,
                'notas_pendentes': queryset.filter(data_saida__isnull=True).count(),
                'notas_processadas': queryset.filter(data_saida__isnull=False).count(),
            }
            
            # Cache por 5 minutos
            cache.set(cache_key, stats, CacheManager.CACHE_TIMEOUT_SHORT)
        
        return stats
    
    @staticmethod
    def get_contratos_ativos():
        """
        Cache dos contratos ativos
        """
        cache_key = 'contratos_ativos'
        contratos = cache.get(cache_key)
        
        if contratos is None:
            hoje = timezone.now().date()
            contratos = list(
                Contrato.objects.filter(
                    Q(data_fim__gte=hoje) | Q(data_fim__isnull=True)
                ).values('id', 'numero', 'empresa')
            )
            
            # Cache por 15 minutos
            cache.set(cache_key, contratos, CacheManager.CACHE_TIMEOUT_MEDIUM)
        
        return contratos
    
    @staticmethod
    def get_empresas_list():
        """
        Cache da lista de empresas únicas
        """
        cache_key = 'empresas_list'
        empresas = cache.get(cache_key)
        
        if empresas is None:
            empresas = list(
                Nota.objects.values_list('empresa', flat=True)
                .distinct()
                .order_by('empresa')
            )
            
            # Cache por 1 hora
            cache.set(cache_key, empresas, CacheManager.CACHE_TIMEOUT_LONG)
        
        return empresas
    
    @staticmethod
    def get_monthly_stats(year=None, month=None):
        """
        Cache das estatísticas mensais
        """
        if not year or not month:
            now = timezone.now()
            year = now.year
            month = now.month
        
        cache_key = f'monthly_stats_{year}_{month}'
        stats = cache.get(cache_key)
        
        if stats is None:
            queryset = Nota.objects.filter(
                data_entrada__year=year,
                data_entrada__month=month
            ).select_related('contrato')
            
            stats = {
                'total_mes': queryset.count(),
                'valor_mes': queryset.aggregate(total=Sum('valor'))['total'] or 0,
                'processadas_mes': queryset.filter(data_saida__isnull=False).count(),
                'pendentes_mes': queryset.filter(data_saida__isnull=True).count(),
            }
            
            # Cache por 15 minutos
            cache.set(cache_key, stats, CacheManager.CACHE_TIMEOUT_MEDIUM)
        
        return stats
    
    @staticmethod
    def invalidate_dashboard_cache(user_id=None):
        """
        Invalida o cache do dashboard
        """
        cache_key = f'dashboard_stats_{user_id or "all"}'
        cache.delete(cache_key)
    
    @staticmethod
    def invalidate_contratos_cache():
        """
        Invalida o cache de contratos
        """
        cache.delete('contratos_ativos')
    
    @staticmethod
    def invalidate_empresas_cache():
        """
        Invalida o cache de empresas
        """
        cache.delete('empresas_list')
    
    @staticmethod
    def invalidate_all_cache():
        """
        Invalida todo o cache relacionado ao sistema
        """
        cache.clear()

# Decorador para cache de views
def cache_view(timeout=300):
    """
    Decorador para cachear views
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Gerar chave única baseada na URL e parâmetros
            cache_key = f'view_{request.path}_{hash(str(request.GET))}'
            
            # Tentar obter do cache
            response = cache.get(cache_key)
            
            if response is None:
                # Executar view e cachear resultado
                response = view_func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator