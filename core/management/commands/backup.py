from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.backup_system import BackupManager
from core.logging_config import audit_logger
import json


class Command(BaseCommand):
    help = 'Gerencia backups do sistema'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Ações disponíveis')
        
        # Comando para criar backup
        create_parser = subparsers.add_parser('create', help='Criar novo backup')
        create_parser.add_argument(
            '--no-media',
            action='store_true',
            help='Não incluir arquivos de mídia no backup'
        )
        
        # Comando para listar backups
        list_parser = subparsers.add_parser('list', help='Listar backups existentes')
        list_parser.add_argument(
            '--json',
            action='store_true',
            help='Saída em formato JSON'
        )
        
        # Comando para remover backup
        delete_parser = subparsers.add_parser('delete', help='Remover backup')
        delete_parser.add_argument(
            'backup_name',
            help='Nome do backup a ser removido'
        )
        delete_parser.add_argument(
            '--force',
            action='store_true',
            help='Não pedir confirmação'
        )
        
        # Comando para limpeza automática
        cleanup_parser = subparsers.add_parser('cleanup', help='Limpar backups antigos')
        cleanup_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar o que seria removido sem fazer alterações'
        )
        
        # Comando para restaurar backup
        restore_parser = subparsers.add_parser('restore', help='Extrair backup para análise')
        restore_parser.add_argument(
            'backup_name',
            help='Nome do backup a ser extraído'
        )
        restore_parser.add_argument(
            '--path',
            help='Caminho onde extrair o backup'
        )
        
        # Comando para estatísticas
        stats_parser = subparsers.add_parser('stats', help='Mostrar estatísticas dos backups')
        stats_parser.add_argument(
            '--json',
            action='store_true',
            help='Saída em formato JSON'
        )

    def handle(self, *args, **options):
        action = options.get('action')
        
        if not action:
            self.print_help('manage.py', 'backup')
            return
        
        backup_manager = BackupManager()
        
        try:
            if action == 'create':
                self.handle_create(backup_manager, options)
            elif action == 'list':
                self.handle_list(backup_manager, options)
            elif action == 'delete':
                self.handle_delete(backup_manager, options)
            elif action == 'cleanup':
                self.handle_cleanup(backup_manager, options)
            elif action == 'restore':
                self.handle_restore(backup_manager, options)
            elif action == 'stats':
                self.handle_stats(backup_manager, options)
            else:
                raise CommandError(f'Ação desconhecida: {action}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao executar comando: {e}')
            )
            raise CommandError(str(e))

    def handle_create(self, backup_manager, options):
        """Criar novo backup"""
        include_media = not options.get('no_media', False)
        
        self.stdout.write('Iniciando criação de backup...')
        
        if include_media:
            self.stdout.write('Incluindo arquivos de mídia no backup.')
        else:
            self.stdout.write(
                self.style.WARNING('Arquivos de mídia não serão incluídos.')
            )
        
        backup_info = backup_manager.create_full_backup(include_media=include_media)
        
        if backup_info['success']:
            self.stdout.write(
                self.style.SUCCESS(f'Backup criado com sucesso: {backup_info["name"]}')
            )
            
            # Mostrar estatísticas do backup
            size_mb = backup_info.get('zip_size_bytes', 0) / (1024 * 1024)
            self.stdout.write(f'Tamanho: {size_mb:.2f} MB')
            self.stdout.write(f'Componentes: {len(backup_info["components"])}')
            
            for component in backup_info['components']:
                status = '✓' if component['success'] else '✗'
                file_count = len(component.get('files', []))
                self.stdout.write(f'  {status} {component["name"]}: {file_count} arquivos')
                
                if component.get('errors'):
                    for error in component['errors']:
                        self.stdout.write(
                            self.style.WARNING(f'    Aviso: {error}')
                        )
            
            # Log da operação
            audit_logger.log_user_action(
                user_id=None,
                action='backup_created',
                details={
                    'backup_name': backup_info['name'],
                    'include_media': include_media,
                    'size_bytes': backup_info.get('zip_size_bytes', 0),
                    'components': len(backup_info['components'])
                }
            )
            
        else:
            self.stdout.write(
                self.style.ERROR('Falha na criação do backup!')
            )
            
            for error in backup_info.get('errors', []):
                self.stdout.write(
                    self.style.ERROR(f'Erro: {error}')
                )

    def handle_list(self, backup_manager, options):
        """Listar backups existentes"""
        backups = backup_manager.list_backups()
        
        if options.get('json'):
            self.stdout.write(json.dumps(backups, indent=2, ensure_ascii=False))
            return
        
        if not backups:
            self.stdout.write('Nenhum backup encontrado.')
            return
        
        self.stdout.write(f'Encontrados {len(backups)} backup(s):\n')
        
        for backup in backups:
            status = '✓' if backup.get('success', False) else '✗'
            size_mb = backup.get('zip_size_bytes', 0) / (1024 * 1024)
            zip_exists = '(arquivo existe)' if backup.get('zip_exists', False) else '(arquivo não encontrado)'
            
            self.stdout.write(f'{status} {backup["name"]}')
            self.stdout.write(f'   Data: {backup.get("created_at", "N/A")}')
            self.stdout.write(f'   Tamanho: {size_mb:.2f} MB {zip_exists}')
            self.stdout.write(f'   Componentes: {len(backup.get("components", []))}')
            
            if backup.get('errors'):
                self.stdout.write(
                    self.style.WARNING(f'   Erros: {len(backup["errors"])}')
                )
            
            self.stdout.write('')

    def handle_delete(self, backup_manager, options):
        """Remover backup"""
        backup_name = options['backup_name']
        force = options.get('force', False)
        
        # Verificar se o backup existe
        backups = backup_manager.list_backups()
        backup_exists = any(b['name'] == backup_name for b in backups)
        
        if not backup_exists:
            raise CommandError(f'Backup não encontrado: {backup_name}')
        
        if not force:
            confirm = input(f'Tem certeza que deseja remover o backup "{backup_name}"? (s/N): ')
            if confirm.lower() not in ['s', 'sim', 'y', 'yes']:
                self.stdout.write('Operação cancelada.')
                return
        
        if backup_manager.delete_backup(backup_name):
            self.stdout.write(
                self.style.SUCCESS(f'Backup removido: {backup_name}')
            )
            
            # Log da operação
            audit_logger.log_user_action(
                user_id=None,
                action='backup_deleted',
                details={'backup_name': backup_name}
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'Erro ao remover backup: {backup_name}')
            )

    def handle_cleanup(self, backup_manager, options):
        """Limpar backups antigos"""
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY-RUN: Nenhuma alteração será feita')
            )
        
        self.stdout.write('Iniciando limpeza de backups antigos...')
        
        cleanup_info = backup_manager.cleanup_old_backups()
        
        if cleanup_info['removed_count'] > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Removidos {cleanup_info["removed_count"]} backup(s)'
                )
            )
            
            for removed in cleanup_info['removed_backups']:
                reason_text = {
                    'excess_count': 'excesso de quantidade',
                    'expired': 'expirado'
                }.get(removed['reason'], removed['reason'])
                
                self.stdout.write(f'  - {removed["name"]} ({reason_text})')
        else:
            self.stdout.write('Nenhum backup foi removido.')
        
        if cleanup_info['errors']:
            self.stdout.write(
                self.style.WARNING('Erros durante a limpeza:')
            )
            for error in cleanup_info['errors']:
                self.stdout.write(f'  - {error}')
        
        if not dry_run and cleanup_info['removed_count'] > 0:
            # Log da operação
            audit_logger.log_user_action(
                user_id=None,
                action='backup_cleanup',
                details={
                    'removed_count': cleanup_info['removed_count'],
                    'removed_backups': cleanup_info['removed_backups']
                }
            )

    def handle_restore(self, backup_manager, options):
        """Extrair backup para análise"""
        backup_name = options['backup_name']
        restore_path = options.get('path')
        
        if restore_path:
            from pathlib import Path
            restore_path = Path(restore_path)
        
        self.stdout.write(f'Extraindo backup: {backup_name}')
        
        restore_info = backup_manager.restore_backup(backup_name, restore_path)
        
        if restore_info['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Backup extraído para: {restore_info["restore_path"]}'
                )
            )
            self.stdout.write(
                f'Arquivos extraídos: {len(restore_info["extracted_files"])}'
            )
            
            # Log da operação
            audit_logger.log_user_action(
                user_id=None,
                action='backup_restored',
                details={
                    'backup_name': backup_name,
                    'restore_path': restore_info['restore_path'],
                    'files_count': len(restore_info['extracted_files'])
                }
            )
        else:
            self.stdout.write(
                self.style.ERROR('Erro ao extrair backup!')
            )
            
            for error in restore_info.get('errors', []):
                self.stdout.write(
                    self.style.ERROR(f'Erro: {error}')
                )

    def handle_stats(self, backup_manager, options):
        """Mostrar estatísticas dos backups"""
        stats = backup_manager.get_backup_statistics()
        
        if options.get('json'):
            self.stdout.write(json.dumps(stats, indent=2, ensure_ascii=False))
            return
        
        self.stdout.write('=== Estatísticas de Backup ===')
        self.stdout.write(f'Total de backups: {stats["total_backups"]}')
        self.stdout.write(f'Backups bem-sucedidos: {stats["successful_backups"]}')
        self.stdout.write(f'Backups com falha: {stats["failed_backups"]}')
        self.stdout.write(f'Tamanho total: {stats["total_size_mb"]} MB')
        
        if stats['oldest_backup']:
            self.stdout.write(f'Backup mais antigo: {stats["oldest_backup"]}')
        
        if stats['newest_backup']:
            self.stdout.write(f'Backup mais recente: {stats["newest_backup"]}')
        
        self.stdout.write(f'Diretório de backups: {stats["backup_directory"]}')