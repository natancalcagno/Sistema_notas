import os
import shutil
import zipfile
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management import call_command
from django.core.mail import send_mail
from django.utils import timezone
from pathlib import Path
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """Gerenciador de backup do sistema"""
    
    def __init__(self):
        self.backup_dir = Path(settings.BASE_DIR) / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        # Configurações padrão
        self.max_backups = getattr(settings, 'BACKUP_MAX_FILES', 10)
        self.backup_retention_days = getattr(settings, 'BACKUP_RETENTION_DAYS', 30)
        
    def create_full_backup(self, include_media: bool = True) -> Dict[str, any]:
        """Cria um backup completo do sistema"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'backup_completo_{timestamp}'
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        backup_info = {
            'name': backup_name,
            'timestamp': timestamp,
            'created_at': timezone.now().isoformat(),
            'type': 'full',
            'components': [],
            'size_bytes': 0,
            'success': True,
            'errors': []
        }
        
        try:
            # 1. Backup do banco de dados
            db_backup = self._backup_database(backup_path)
            backup_info['components'].append(db_backup)
            
            # 2. Backup dos arquivos de configuração
            config_backup = self._backup_config_files(backup_path)
            backup_info['components'].append(config_backup)
            
            # 3. Backup dos logs
            logs_backup = self._backup_logs(backup_path)
            backup_info['components'].append(logs_backup)
            
            # 4. Backup dos arquivos de mídia (opcional)
            if include_media:
                media_backup = self._backup_media_files(backup_path)
                backup_info['components'].append(media_backup)
            
            # 5. Backup dos templates customizados
            templates_backup = self._backup_templates(backup_path)
            backup_info['components'].append(templates_backup)
            
            # 6. Backup dos arquivos estáticos customizados
            static_backup = self._backup_static_files(backup_path)
            backup_info['components'].append(static_backup)
            
            # Calcular tamanho total
            backup_info['size_bytes'] = self._calculate_directory_size(backup_path)
            
            # Criar arquivo ZIP
            zip_path = self._create_zip_archive(backup_path, backup_name)
            backup_info['zip_path'] = str(zip_path)
            backup_info['zip_size_bytes'] = zip_path.stat().st_size
            
            # Remover diretório temporário
            shutil.rmtree(backup_path)
            
            # Salvar informações do backup
            self._save_backup_info(backup_info)
            
            logger.info(f'Backup completo criado: {backup_name}')
            
        except Exception as e:
            backup_info['success'] = False
            backup_info['errors'].append(str(e))
            logger.error(f'Erro ao criar backup: {e}')
            
            # Limpar arquivos parciais em caso de erro
            if backup_path.exists():
                shutil.rmtree(backup_path)
        
        return backup_info
    
    def _backup_database(self, backup_path: Path) -> Dict[str, any]:
        """Backup do banco de dados"""
        db_backup_path = backup_path / 'database'
        db_backup_path.mkdir(exist_ok=True)
        
        component_info = {
            'name': 'database',
            'success': True,
            'files': [],
            'errors': []
        }
        
        try:
            # Backup usando dumpdata do Django
            dump_file = db_backup_path / 'data.json'
            
            with open(dump_file, 'w', encoding='utf-8') as f:
                call_command('dumpdata', 
                           '--natural-foreign', 
                           '--natural-primary',
                           '--indent=2',
                           stdout=f)
            
            component_info['files'].append({
                'name': 'data.json',
                'size': dump_file.stat().st_size,
                'path': str(dump_file.relative_to(backup_path))
            })
            
            # Backup das migrações
            migrations_backup = self._backup_migrations(db_backup_path)
            component_info['files'].extend(migrations_backup)
            
        except Exception as e:
            component_info['success'] = False
            component_info['errors'].append(str(e))
            logger.error(f'Erro no backup do banco: {e}')
        
        return component_info
    
    def _backup_migrations(self, db_backup_path: Path) -> List[Dict[str, any]]:
        """Backup dos arquivos de migração"""
        migrations_files = []
        migrations_dir = db_backup_path / 'migrations'
        migrations_dir.mkdir(exist_ok=True)
        
        # Copiar migrações da app core
        core_migrations = Path(settings.BASE_DIR) / 'core' / 'migrations'
        if core_migrations.exists():
            for migration_file in core_migrations.glob('*.py'):
                if migration_file.name != '__init__.py':
                    dest_file = migrations_dir / migration_file.name
                    shutil.copy2(migration_file, dest_file)
                    
                    migrations_files.append({
                        'name': migration_file.name,
                        'size': dest_file.stat().st_size,
                        'path': str(dest_file.relative_to(db_backup_path.parent))
                    })
        
        return migrations_files
    
    def _backup_config_files(self, backup_path: Path) -> Dict[str, any]:
        """Backup dos arquivos de configuração"""
        config_backup_path = backup_path / 'config'
        config_backup_path.mkdir(exist_ok=True)
        
        component_info = {
            'name': 'config',
            'success': True,
            'files': [],
            'errors': []
        }
        
        try:
            config_files = [
                'settings.py',
                'urls.py',
                'wsgi.py',
                'asgi.py',
                'requirements.txt'
            ]
            
            for config_file in config_files:
                source_path = Path(settings.BASE_DIR) / config_file
                if source_path.exists():
                    dest_path = config_backup_path / config_file
                    shutil.copy2(source_path, dest_path)
                    
                    component_info['files'].append({
                        'name': config_file,
                        'size': dest_path.stat().st_size,
                        'path': str(dest_path.relative_to(backup_path))
                    })
            
            # Backup do diretório core
            core_backup_path = config_backup_path / 'core'
            core_source = Path(settings.BASE_DIR) / 'core'
            if core_source.exists():
                shutil.copytree(core_source, core_backup_path, 
                              ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                
                # Contar arquivos copiados
                for file_path in core_backup_path.rglob('*'):
                    if file_path.is_file():
                        component_info['files'].append({
                            'name': file_path.name,
                            'size': file_path.stat().st_size,
                            'path': str(file_path.relative_to(backup_path))
                        })
        
        except Exception as e:
            component_info['success'] = False
            component_info['errors'].append(str(e))
            logger.error(f'Erro no backup de configurações: {e}')
        
        return component_info
    
    def _backup_logs(self, backup_path: Path) -> Dict[str, any]:
        """Backup dos arquivos de log"""
        logs_backup_path = backup_path / 'logs'
        logs_backup_path.mkdir(exist_ok=True)
        
        component_info = {
            'name': 'logs',
            'success': True,
            'files': [],
            'errors': []
        }
        
        try:
            logs_source = Path(settings.BASE_DIR) / 'logs'
            if logs_source.exists():
                for log_file in logs_source.glob('*'):
                    if log_file.is_file():
                        dest_file = logs_backup_path / log_file.name
                        shutil.copy2(log_file, dest_file)
                        
                        component_info['files'].append({
                            'name': log_file.name,
                            'size': dest_file.stat().st_size,
                            'path': str(dest_file.relative_to(backup_path))
                        })
        
        except Exception as e:
            component_info['success'] = False
            component_info['errors'].append(str(e))
            logger.error(f'Erro no backup de logs: {e}')
        
        return component_info
    
    def _backup_media_files(self, backup_path: Path) -> Dict[str, any]:
        """Backup dos arquivos de mídia"""
        media_backup_path = backup_path / 'media'
        
        component_info = {
            'name': 'media',
            'success': True,
            'files': [],
            'errors': []
        }
        
        try:
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists() and any(media_root.iterdir()):
                shutil.copytree(media_root, media_backup_path)
                
                # Contar arquivos copiados
                for file_path in media_backup_path.rglob('*'):
                    if file_path.is_file():
                        component_info['files'].append({
                            'name': file_path.name,
                            'size': file_path.stat().st_size,
                            'path': str(file_path.relative_to(backup_path))
                        })
        
        except Exception as e:
            component_info['success'] = False
            component_info['errors'].append(str(e))
            logger.error(f'Erro no backup de mídia: {e}')
        
        return component_info
    
    def _backup_templates(self, backup_path: Path) -> Dict[str, any]:
        """Backup dos templates"""
        templates_backup_path = backup_path / 'templates'
        
        component_info = {
            'name': 'templates',
            'success': True,
            'files': [],
            'errors': []
        }
        
        try:
            templates_source = Path(settings.BASE_DIR) / 'templates'
            if templates_source.exists():
                shutil.copytree(templates_source, templates_backup_path)
                
                # Contar arquivos copiados
                for file_path in templates_backup_path.rglob('*'):
                    if file_path.is_file():
                        component_info['files'].append({
                            'name': file_path.name,
                            'size': file_path.stat().st_size,
                            'path': str(file_path.relative_to(backup_path))
                        })
        
        except Exception as e:
            component_info['success'] = False
            component_info['errors'].append(str(e))
            logger.error(f'Erro no backup de templates: {e}')
        
        return component_info
    
    def _backup_static_files(self, backup_path: Path) -> Dict[str, any]:
        """Backup dos arquivos estáticos customizados"""
        static_backup_path = backup_path / 'static'
        
        component_info = {
            'name': 'static',
            'success': True,
            'files': [],
            'errors': []
        }
        
        try:
            static_source = Path(settings.BASE_DIR) / 'static'
            if static_source.exists():
                shutil.copytree(static_source, static_backup_path)
                
                # Contar arquivos copiados
                for file_path in static_backup_path.rglob('*'):
                    if file_path.is_file():
                        component_info['files'].append({
                            'name': file_path.name,
                            'size': file_path.stat().st_size,
                            'path': str(file_path.relative_to(backup_path))
                        })
        
        except Exception as e:
            component_info['success'] = False
            component_info['errors'].append(str(e))
            logger.error(f'Erro no backup de arquivos estáticos: {e}')
        
        return component_info
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """Calcula o tamanho total de um diretório"""
        total_size = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def _create_zip_archive(self, source_dir: Path, backup_name: str) -> Path:
        """Cria um arquivo ZIP do backup"""
        zip_path = self.backup_dir / f'{backup_name}.zip'
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    def _save_backup_info(self, backup_info: Dict[str, any]) -> None:
        """Salva informações do backup em arquivo JSON"""
        info_file = self.backup_dir / f"{backup_info['name']}_info.json"
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
    
    def list_backups(self) -> List[Dict[str, any]]:
        """Lista todos os backups disponíveis"""
        backups = []
        
        for info_file in self.backup_dir.glob('*_info.json'):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)
                    
                # Verificar se o arquivo ZIP ainda existe
                if 'zip_path' in backup_info:
                    zip_path = Path(backup_info['zip_path'])
                    backup_info['zip_exists'] = zip_path.exists()
                    if backup_info['zip_exists']:
                        backup_info['zip_size_bytes'] = zip_path.stat().st_size
                
                backups.append(backup_info)
                
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f'Erro ao ler informações do backup {info_file}: {e}')
        
        # Ordenar por data de criação (mais recente primeiro)
        backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return backups
    
    def delete_backup(self, backup_name: str) -> bool:
        """Remove um backup específico"""
        try:
            # Remover arquivo ZIP
            zip_path = self.backup_dir / f'{backup_name}.zip'
            if zip_path.exists():
                zip_path.unlink()
            
            # Remover arquivo de informações
            info_path = self.backup_dir / f'{backup_name}_info.json'
            if info_path.exists():
                info_path.unlink()
            
            logger.info(f'Backup removido: {backup_name}')
            return True
            
        except Exception as e:
            logger.error(f'Erro ao remover backup {backup_name}: {e}')
            return False
    
    def cleanup_old_backups(self) -> Dict[str, any]:
        """Remove backups antigos baseado na configuração de retenção"""
        cleanup_info = {
            'removed_count': 0,
            'removed_backups': [],
            'errors': []
        }
        
        try:
            backups = self.list_backups()
            
            # Remover backups que excedem o número máximo
            if len(backups) > self.max_backups:
                excess_backups = backups[self.max_backups:]
                for backup in excess_backups:
                    if self.delete_backup(backup['name']):
                        cleanup_info['removed_count'] += 1
                        cleanup_info['removed_backups'].append({
                            'name': backup['name'],
                            'reason': 'excess_count'
                        })
            
            # Remover backups mais antigos que o período de retenção
            cutoff_date = timezone.now() - timedelta(days=self.backup_retention_days)
            
            for backup in backups:
                try:
                    backup_date = datetime.fromisoformat(backup['created_at'].replace('Z', '+00:00'))
                    if backup_date < cutoff_date:
                        if self.delete_backup(backup['name']):
                            cleanup_info['removed_count'] += 1
                            cleanup_info['removed_backups'].append({
                                'name': backup['name'],
                                'reason': 'expired'
                            })
                except (ValueError, KeyError) as e:
                    cleanup_info['errors'].append(f'Erro ao processar data do backup {backup.get("name", "unknown")}: {e}')
        
        except Exception as e:
            cleanup_info['errors'].append(str(e))
            logger.error(f'Erro na limpeza de backups: {e}')
        
        return cleanup_info
    
    def restore_backup(self, backup_name: str, restore_path: Optional[Path] = None) -> Dict[str, any]:
        """Restaura um backup (extrai o ZIP para análise)"""
        restore_info = {
            'success': False,
            'backup_name': backup_name,
            'restore_path': None,
            'extracted_files': [],
            'errors': []
        }
        
        try:
            zip_path = self.backup_dir / f'{backup_name}.zip'
            if not zip_path.exists():
                raise FileNotFoundError(f'Backup não encontrado: {backup_name}')
            
            if restore_path is None:
                restore_path = self.backup_dir / f'restore_{backup_name}'
            
            restore_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(restore_path)
                restore_info['extracted_files'] = zipf.namelist()
            
            restore_info['success'] = True
            restore_info['restore_path'] = str(restore_path)
            
            logger.info(f'Backup extraído para: {restore_path}')
            
        except Exception as e:
            restore_info['errors'].append(str(e))
            logger.error(f'Erro ao restaurar backup {backup_name}: {e}')
        
        return restore_info
    
    def get_backup_statistics(self) -> Dict[str, any]:
        """Retorna estatísticas dos backups"""
        backups = self.list_backups()
        
        total_size = sum(backup.get('zip_size_bytes', 0) for backup in backups)
        successful_backups = [b for b in backups if b.get('success', False)]
        failed_backups = [b for b in backups if not b.get('success', True)]
        
        return {
            'total_backups': len(backups),
            'successful_backups': len(successful_backups),
            'failed_backups': len(failed_backups),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_backup': backups[-1]['created_at'] if backups else None,
            'newest_backup': backups[0]['created_at'] if backups else None,
            'backup_directory': str(self.backup_dir)
        }