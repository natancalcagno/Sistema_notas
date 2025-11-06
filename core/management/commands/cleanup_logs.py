from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os
import glob
from core.models import LogEntry
from core.logging_config import audit_logger


class Command(BaseCommand):
    help = 'Limpa logs antigos do sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Número de dias para manter os logs (padrão: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa sem fazer alterações, apenas mostra o que seria removido'
        )
        parser.add_argument(
            '--files-only',
            action='store_true',
            help='Remove apenas arquivos de log, não registros do banco'
        )
        parser.add_argument(
            '--db-only',
            action='store_true',
            help='Remove apenas registros do banco, não arquivos de log'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        files_only = options['files_only']
        db_only = options['db_only']
        
        self.stdout.write(
            self.style.SUCCESS(f'Iniciando limpeza de logs com mais de {days} dias...')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY-RUN: Nenhuma alteração será feita')
            )
        
        total_removed = 0
        
        # Limpar registros do banco de dados
        if not files_only:
            db_removed = self.cleanup_database_logs(days, dry_run)
            total_removed += db_removed
        
        # Limpar arquivos de log
        if not db_only:
            files_removed = self.cleanup_log_files(days, dry_run)
            total_removed += files_removed
        
        if not dry_run:
            # Log da operação de limpeza
            audit_logger.log_user_action(
                user_id=None,
                action='log_cleanup',
                details={
                    'days_kept': days,
                    'total_removed': total_removed,
                    'files_only': files_only,
                    'db_only': db_only
                }
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Limpeza concluída. Total de itens removidos: {total_removed}'
            )
        )

    def cleanup_database_logs(self, days, dry_run):
        """Remove logs antigos do banco de dados"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Contar registros que serão removidos
        old_logs = LogEntry.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        
        if count == 0:
            self.stdout.write('Nenhum log antigo encontrado no banco de dados.')
            return 0
        
        self.stdout.write(
            f'Encontrados {count} registros de log no banco com mais de {days} dias.'
        )
        
        if not dry_run:
            # Remover em lotes para evitar problemas de memória
            batch_size = 1000
            removed = 0
            
            while True:
                batch_ids = list(
                    old_logs.values_list('id', flat=True)[:batch_size]
                )
                if not batch_ids:
                    break
                
                batch_count = LogEntry.objects.filter(id__in=batch_ids).delete()[0]
                removed += batch_count
                
                self.stdout.write(f'Removidos {removed}/{count} registros...')
            
            self.stdout.write(
                self.style.SUCCESS(f'Removidos {removed} registros do banco de dados.')
            )
            return removed
        else:
            self.stdout.write(
                self.style.WARNING(f'[DRY-RUN] Seriam removidos {count} registros do banco.')
            )
            return 0

    def cleanup_log_files(self, days, dry_run):
        """Remove arquivos de log antigos"""
        from django.conf import settings
        
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        
        if not os.path.exists(log_dir):
            self.stdout.write('Diretório de logs não encontrado.')
            return 0
        
        cutoff_time = timezone.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Padrões de arquivos de log para verificar
        log_patterns = [
            '*.log',
            '*.log.*',
            '*.json',
            '*.json.*'
        ]
        
        removed_files = 0
        
        for pattern in log_patterns:
            files = glob.glob(os.path.join(log_dir, pattern))
            
            for file_path in files:
                try:
                    # Verificar se o arquivo é mais antigo que o cutoff
                    file_mtime = os.path.getmtime(file_path)
                    
                    if file_mtime < cutoff_timestamp:
                        file_size = os.path.getsize(file_path)
                        
                        if dry_run:
                            self.stdout.write(
                                f'[DRY-RUN] Removeria: {file_path} '
                                f'({self.format_size(file_size)})'
                            )
                        else:
                            os.remove(file_path)
                            self.stdout.write(
                                f'Removido: {file_path} ({self.format_size(file_size)})'
                            )
                        
                        removed_files += 1
                
                except (OSError, IOError) as e:
                    self.stdout.write(
                        self.style.ERROR(f'Erro ao processar {file_path}: {e}')
                    )
        
        if removed_files == 0:
            self.stdout.write('Nenhum arquivo de log antigo encontrado.')
        else:
            action = 'Seriam removidos' if dry_run else 'Removidos'
            self.stdout.write(
                self.style.SUCCESS(f'{action} {removed_files} arquivos de log.')
            )
        
        return removed_files

    def format_size(self, size_bytes):
        """Formata o tamanho do arquivo em formato legível"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"