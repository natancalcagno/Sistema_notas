from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import TokenRedefinicaoSenha

class Command(BaseCommand):
    help = 'Limpa tokens de redefinição de senha expirados ou utilizados'

    def handle(self, *args, **options):
        # Remove tokens expirados ou já utilizados
        tokens_removidos = TokenRedefinicaoSenha.objects.filter(
            data_expiracao__lt=timezone.now()
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Tokens removidos com sucesso!')
        )