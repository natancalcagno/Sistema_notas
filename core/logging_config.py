import logging
import logging.handlers
import os
from datetime import datetime
from django.conf import settings
from django.utils import timezone
import json


class JSONFormatter(logging.Formatter):
    """
    Formatador JSON para logs estruturados
    """
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Adicionar informações extras se disponíveis
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'action'):
            log_entry['action'] = record.action
        if hasattr(record, 'model'):
            log_entry['model'] = record.model
        if hasattr(record, 'object_id'):
            log_entry['object_id'] = record.object_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        
        # Adicionar stack trace para erros
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class DatabaseLogHandler(logging.Handler):
    """
    Handler customizado para salvar logs no banco de dados
    """
    def emit(self, record):
        try:
            from .models import LogEntry
            
            log_entry = LogEntry(
                timestamp=timezone.now(),
                level=record.levelname,
                logger=record.name,
                message=record.getMessage(),
                module=record.module,
                function=record.funcName,
                line_number=record.lineno,
                user_id=getattr(record, 'user_id', None),
                ip_address=getattr(record, 'ip_address', None),
                action=getattr(record, 'action', None),
                model=getattr(record, 'model', None),
                object_id=getattr(record, 'object_id', None),
                request_id=getattr(record, 'request_id', None),
                execution_time=getattr(record, 'execution_time', None),
                exception=self.formatException(record.exc_info) if record.exc_info else None
            )
            log_entry.save()
        except Exception:
            # Evitar loops infinitos de logging
            pass


class PerformanceLogger:
    """
    Logger para métricas de performance
    """
    def __init__(self):
        self.logger = logging.getLogger('performance')
    
    def log_query_time(self, query, execution_time, user_id=None):
        """Log tempo de execução de queries"""
        self.logger.info(
            f"Query executed: {query[:100]}...",
            extra={
                'action': 'database_query',
                'execution_time': execution_time,
                'user_id': user_id,
                'query': query
            }
        )
    
    def log_view_time(self, view_name, execution_time, user_id=None, request_id=None):
        """Log tempo de execução de views"""
        self.logger.info(
            f"View {view_name} executed",
            extra={
                'action': 'view_execution',
                'view_name': view_name,
                'execution_time': execution_time,
                'user_id': user_id,
                'request_id': request_id
            }
        )
    
    def log_cache_hit(self, cache_key, hit=True, user_id=None):
        """Log cache hits/misses"""
        status = 'hit' if hit else 'miss'
        self.logger.info(
            f"Cache {status}: {cache_key}",
            extra={
                'action': f'cache_{status}',
                'cache_key': cache_key,
                'user_id': user_id
            }
        )


class AuditLogger:
    """
    Logger para auditoria de ações do usuário
    """
    def __init__(self):
        self.logger = logging.getLogger('audit')
    
    def log_user_action(self, user_id, action, model=None, object_id=None, 
                       ip_address=None, request_id=None, details=None):
        """Log ações do usuário"""
        message = f"User {user_id} performed {action}"
        if model and object_id:
            message += f" on {model} {object_id}"
        
        extra = {
            'user_id': user_id,
            'action': action,
            'ip_address': ip_address,
            'request_id': request_id
        }
        
        if model:
            extra['model'] = model
        if object_id:
            extra['object_id'] = object_id
        if details:
            extra['details'] = details
        
        self.logger.info(message, extra=extra)
    
    def log_login_attempt(self, username, success, ip_address=None, request_id=None):
        """Log tentativas de login"""
        status = 'successful' if success else 'failed'
        self.logger.info(
            f"Login attempt {status} for user {username}",
            extra={
                'action': f'login_{status}',
                'username': username,
                'ip_address': ip_address,
                'request_id': request_id
            }
        )
    
    def log_permission_denied(self, user_id, action, resource=None, ip_address=None):
        """Log tentativas de acesso negado"""
        message = f"Permission denied for user {user_id} on action {action}"
        if resource:
            message += f" for resource {resource}"
        
        self.logger.warning(
            message,
            extra={
                'user_id': user_id,
                'action': 'permission_denied',
                'resource': resource,
                'ip_address': ip_address
            }
        )


class SecurityLogger:
    """
    Logger para eventos de segurança
    """
    def __init__(self):
        self.logger = logging.getLogger('security')
    
    def log_suspicious_activity(self, description, user_id=None, ip_address=None, 
                              request_id=None, severity='medium'):
        """Log atividades suspeitas"""
        level = logging.WARNING if severity == 'medium' else logging.ERROR
        
        self.logger.log(
            level,
            f"Suspicious activity detected: {description}",
            extra={
                'action': 'suspicious_activity',
                'user_id': user_id,
                'ip_address': ip_address,
                'request_id': request_id,
                'severity': severity
            }
        )
    
    def log_rate_limit_exceeded(self, ip_address, endpoint, request_id=None):
        """Log quando rate limit é excedido"""
        self.logger.warning(
            f"Rate limit exceeded for IP {ip_address} on endpoint {endpoint}",
            extra={
                'action': 'rate_limit_exceeded',
                'ip_address': ip_address,
                'endpoint': endpoint,
                'request_id': request_id
            }
        )
    
    def log_csrf_failure(self, ip_address, user_id=None, request_id=None):
        """Log falhas de CSRF"""
        self.logger.error(
            f"CSRF failure from IP {ip_address}",
            extra={
                'action': 'csrf_failure',
                'ip_address': ip_address,
                'user_id': user_id,
                'request_id': request_id
            }
        )


def setup_logging(base_dir=None):
    """
    Configurar sistema de logging
    """
    # Criar diretório de logs se não existir
    # Determinar BASE_DIR sem depender do ciclo de import do Django
    if base_dir is None:
        try:
            # Quando settings já estiverem prontos
            base_dir = settings.BASE_DIR
        except Exception:
            # Fallback para raiz do projeto (um nível acima de 'core')
            from pathlib import Path
            base_dir = str(Path(__file__).resolve().parents[1])
    # Detectar ambiente Vercel (serverless, filesystem read-only)
    is_vercel = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') is not None

    # Em Vercel, evitar escrita em disco; usar apenas console
    if is_vercel:
        handlers = {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
                'level': 'INFO'
            }
        }
        loggers = {
            'django': { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
            'core':   { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
            'audit':  { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
            'performance': { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
            'security': { 'handlers': ['console'], 'level': 'WARNING', 'propagate': False },
        }
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': { '()': JSONFormatter },
                'console': { 'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s' }
            },
            'handlers': handlers,
            'loggers': loggers,
            'root': { 'level': 'INFO', 'handlers': ['console'] }
        }

    # Ambiente local/servidor tradicional: preparar diretório de logs
    log_dir = os.path.join(base_dir, 'logs')
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        # Se não conseguir criar, rebaixa para console-only
        handlers = {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
                'level': 'INFO'
            }
        }
        loggers = {
            'django': { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
            'core':   { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
            'audit':  { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
            'performance': { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
            'security': { 'handlers': ['console'], 'level': 'WARNING', 'propagate': False },
        }
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': { '()': JSONFormatter },
                'console': { 'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s' }
            },
            'handlers': handlers,
            'loggers': loggers,
            'root': { 'level': 'INFO', 'handlers': ['console'] }
        }
    
    # Configurar handlers (com arquivo) para ambientes com disco gravável
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'level': 'INFO'
        },
        'file_json': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_dir, 'sistema_notas.json'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
            'level': 'INFO'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_dir, 'errors.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 3,
            'formatter': 'console',
            'level': 'ERROR'
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_dir, 'audit.json'),
            'maxBytes': 20 * 1024 * 1024,  # 20MB
            'backupCount': 10,
            'formatter': 'json',
            'level': 'INFO'
        },
        'performance_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_dir, 'performance.json'),
            'maxBytes': 15 * 1024 * 1024,  # 15MB
            'backupCount': 7,
            'formatter': 'json',
            'level': 'INFO'
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_dir, 'security.json'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
            'level': 'WARNING'
        }
    }
    
    # Configurar loggers
    loggers = {
        'django': {
            'handlers': ['console', 'file_json', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'core': {
            'handlers': ['console', 'file_json', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'audit': {
            'handlers': ['audit_file', 'console'],
            'level': 'INFO',
            'propagate': False
        },
        'performance': {
            'handlers': ['performance_file'],
            'level': 'INFO',
            'propagate': False
        },
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False
        }
    }
    
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': JSONFormatter
            },
            'console': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        },
        'handlers': handlers,
        'loggers': loggers,
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file_json']
        }
    }


# Instâncias globais dos loggers
performance_logger = PerformanceLogger()
audit_logger = AuditLogger()
security_logger = SecurityLogger()