import time
import logging
import uuid
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from .logging_config import performance_logger, audit_logger, security_logger

logger = logging.getLogger('core')

class RateLimitMiddleware:
    """
    Middleware para implementar rate limiting em tentativas de login
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Aplicar rate limiting apenas para tentativas de login
        if request.path == '/login/' and request.method == 'POST':
            if not self.check_rate_limit(request):
                logger.warning(f"Rate limit exceeded for IP: {self.get_client_ip(request)}")
                return HttpResponse(
                    "Muitas tentativas de login. Tente novamente em alguns minutos.",
                    status=429
                )
        
        response = self.get_response(request)
        return response

    def check_rate_limit(self, request):
        """
        Verifica se o IP excedeu o limite de tentativas de login
        """
        ip = self.get_client_ip(request)
        cache_key = f"login_attempts_{ip}"
        
        attempts = cache.get(cache_key, 0)
        max_attempts = getattr(settings, 'RATE_LIMIT_LOGIN_ATTEMPTS', 5)
        window = getattr(settings, 'RATE_LIMIT_LOGIN_WINDOW', 300)
        
        if attempts >= max_attempts:
            return False
        
        # Incrementar contador de tentativas
        cache.set(cache_key, attempts + 1, window)
        return True

    def get_client_ip(self, request):
        """
        Obtém o IP real do cliente considerando proxies
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """
    Middleware para adicionar headers de segurança adicionais
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Adicionar headers de segurança
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


class AuditLogMiddleware:
    """
    Middleware para logging de auditoria
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('audit')

    def __call__(self, request):
        # Gerar ID único para a requisição
        request.request_id = str(uuid.uuid4())
        
        # Log da requisição
        if request.user.is_authenticated:
            self.logger.info(
                f"User {request.user.id} accessed {request.path}",
                extra={
                    'user_id': request.user.id,
                    'path': request.path,
                    'method': request.method,
                    'ip_address': self.get_client_ip(request),
                    'request_id': request.request_id
                }
            )

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PerformanceMiddleware(MiddlewareMixin):
    """
    Middleware para monitoramento de performance
    """
    def process_request(self, request):
        request.start_time = time.time()
        request.request_id = getattr(request, 'request_id', str(uuid.uuid4()))
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            execution_time = time.time() - request.start_time
            
            # Log apenas se a execução demorar mais que 1 segundo ou for uma view importante
            if execution_time > 1.0 or self.is_important_view(request):
                user_id = request.user.id if request.user.is_authenticated else None
                
                performance_logger.log_view_time(
                    view_name=self.get_view_name(request),
                    execution_time=execution_time,
                    user_id=user_id,
                    request_id=getattr(request, 'request_id', None)
                )
            
            # Adicionar header de tempo de resposta
            response['X-Response-Time'] = f"{execution_time:.3f}s"
        
        return response
    
    def is_important_view(self, request):
        """Determina se a view é importante para logging"""
        important_paths = [
            '/core/home/',
            '/core/contratos/',
            '/core/notas/',
            '/core/relatorios/',
        ]
        return any(request.path.startswith(path) for path in important_paths)
    
    def get_view_name(self, request):
        """Obtém o nome da view da requisição"""
        try:
            return request.resolver_match.view_name if request.resolver_match else request.path
        except:
            return request.path


class DatabaseQueryLogMiddleware(MiddlewareMixin):
    """
    Middleware para logging de queries do banco de dados
    """
    def process_request(self, request):
        from django.db import connection
        request.queries_before = len(connection.queries)
    
    def process_response(self, request, response):
        from django.db import connection
        
        if hasattr(request, 'queries_before'):
            queries_count = len(connection.queries) - request.queries_before
            
            # Log se houver muitas queries (possível problema N+1)
            if queries_count > 10:
                user_id = request.user.id if request.user.is_authenticated else None
                
                performance_logger.logger.warning(
                    f"High number of database queries: {queries_count} for {request.path}",
                    extra={
                        'action': 'high_query_count',
                        'query_count': queries_count,
                        'path': request.path,
                        'user_id': user_id,
                        'request_id': getattr(request, 'request_id', None)
                    }
                )
            
            # Adicionar header com número de queries
            response['X-DB-Queries'] = str(queries_count)
        
        return response


class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Middleware para auditoria de segurança
    """
    def process_request(self, request):
        # Detectar tentativas de acesso suspeitas
        self.check_suspicious_patterns(request)
        
        # Verificar rate limiting por IP
        self.check_rate_limiting(request)
    
    def check_suspicious_patterns(self, request):
        """Verifica padrões suspeitos na requisição"""
        suspicious_patterns = [
            'admin', 'phpmyadmin', 'wp-admin', 'wp-login',
            'xmlrpc', '.env', 'config', 'backup'
        ]
        
        path_lower = request.path.lower()
        for pattern in suspicious_patterns:
            if pattern in path_lower:
                security_logger.log_suspicious_activity(
                    description=f"Suspicious path access: {request.path}",
                    ip_address=self.get_client_ip(request),
                    request_id=getattr(request, 'request_id', None)
                )
                break
    
    def check_rate_limiting(self, request):
        """Verifica rate limiting por IP"""
        ip = self.get_client_ip(request)
        cache_key = f"rate_limit_{ip}"
        
        current_requests = cache.get(cache_key, 0)
        if current_requests > 100:  # Mais de 100 requests por minuto
            security_logger.log_rate_limit_exceeded(
                ip_address=ip,
                endpoint=request.path,
                request_id=getattr(request, 'request_id', None)
            )
    
    def get_client_ip(self, request):
        """Obtém o IP real do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware para logging detalhado de requisições
    """
    def process_request(self, request):
        # Log detalhado apenas para usuários autenticados ou requisições importantes
        if request.user.is_authenticated or self.is_important_request(request):
            audit_logger.logger.info(
                f"Request: {request.method} {request.path}",
                extra={
                    'action': 'request_received',
                    'method': request.method,
                    'path': request.path,
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'ip_address': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'request_id': getattr(request, 'request_id', str(uuid.uuid4()))
                }
            )
    
    def process_response(self, request, response):
        # Log da resposta para requisições importantes
        if hasattr(request, 'user') and (request.user.is_authenticated or self.is_important_request(request)):
            audit_logger.logger.info(
                f"Response: {response.status_code} for {request.method} {request.path}",
                extra={
                    'action': 'response_sent',
                    'status_code': response.status_code,
                    'method': request.method,
                    'path': request.path,
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'request_id': getattr(request, 'request_id', None)
                }
            )
        
        return response
    
    def is_important_request(self, request):
        """Determina se a requisição é importante para logging"""
        important_methods = ['POST', 'PUT', 'DELETE']
        return request.method in important_methods
    
    def get_client_ip(self, request):
        """Obtém o IP real do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip