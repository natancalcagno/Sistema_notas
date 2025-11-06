from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from .models import Contrato, Nota, Usuario

User = get_user_model()
from .logging_config import audit_logger, performance_logger
import logging

logger = logging.getLogger(__name__)


class BaseService:
    """
    Classe base para todos os services
    """
    def __init__(self, user: User = None):
        self.user = user
    
    def _log_action(self, action: str, model: str = None, object_id: str = None, **kwargs):
        """Log de auditoria para ações do service"""
        if self.user:
            audit_logger.log_user_action(
                user_id=self.user.id,
                action=action,
                model=model,
                object_id=object_id,
                **kwargs
            )


class UsuarioService(BaseService):
    """
    Service para gerenciar operações relacionadas a usuários
    """
    
    @transaction.atomic
    def criar_usuario(self, dados: Dict) -> Usuario:
        """
        Criar um novo usuário com validações
        """
        try:
            # Validar dados obrigatórios
            campos_obrigatorios = ['username', 'email', 'first_name', 'last_name']
            for campo in campos_obrigatorios:
                if not dados.get(campo):
                    raise ValidationError(f'Campo {campo} é obrigatório')
            
            # Verificar se username já existe
            if Usuario.objects.filter(username=dados['username']).exists():
                raise ValidationError('Nome de usuário já existe')
            
            # Verificar se email já existe
            if Usuario.objects.filter(email=dados['email']).exists():
                raise ValidationError('Email já está em uso')
            
            # Criar usuário
            usuario = Usuario.objects.create_user(
                username=dados['username'],
                email=dados['email'],
                first_name=dados['first_name'],
                last_name=dados['last_name'],
                password=dados.get('password', 'temp123'),
                is_staff=dados.get('is_staff', False)
            )
            
            self._log_action('create_user', 'User', str(usuario.id))
            return usuario
            
        except Exception as e:
            logger.error(f'Erro ao criar usuário: {str(e)}')
            raise
    
    @transaction.atomic
    def atualizar_usuario(self, usuario_id: int, dados: Dict) -> Usuario:
        """
        Atualizar dados do usuário
        """
        try:
            usuario = Usuario.objects.get(id=usuario_id)
            
            # Verificar permissões
            if not self.user.is_staff and self.user.id != usuario_id:
                raise ValidationError('Sem permissão para editar este usuário')
            
            # Atualizar campos permitidos
            campos_permitidos = ['first_name', 'last_name', 'email']
            if self.user.is_staff:
                campos_permitidos.extend(['is_staff', 'is_active'])
            
            for campo in campos_permitidos:
                if campo in dados:
                    setattr(usuario, campo, dados[campo])
            
            usuario.full_clean()
            usuario.save()
            
            self._log_action('update_user', 'User', str(usuario.id))
            return usuario
            
        except Usuario.DoesNotExist:
            raise ValidationError('Usuário não encontrado')
        except Exception as e:
            logger.error(f'Erro ao atualizar usuário: {str(e)}')
            raise
    
    def listar_usuarios(self, filtros: Dict = None) -> List[Usuario]:
        """
        Listar usuários com filtros
        """
        queryset = Usuario.objects.all()
        
        if filtros:
            if filtros.get('ativo') is not None:
                queryset = queryset.filter(is_active=filtros['ativo'])
            if filtros.get('staff') is not None:
                queryset = queryset.filter(is_staff=filtros['staff'])
            if filtros.get('busca'):
                busca = filtros['busca']
                queryset = queryset.filter(
                    Q(username__icontains=busca) |
                    Q(first_name__icontains=busca) |
                    Q(last_name__icontains=busca) |
                    Q(email__icontains=busca)
                )
        
        return queryset.order_by('first_name', 'last_name')


class ContratoService(BaseService):
    """
    Service para gerenciar operações relacionadas a contratos
    """
    
    @transaction.atomic
    def criar_contrato(self, dados: Dict) -> Contrato:
        """
        Criar um novo contrato com validações
        """
        try:
            # Validar dados obrigatórios
            campos_obrigatorios = ['numero', 'empresa', 'valor', 'data_inicio', 'data_termino']
            for campo in campos_obrigatorios:
                if not dados.get(campo):
                    raise ValidationError(f'Campo {campo} é obrigatório')
            
            # Verificar se número do contrato já existe
            if Contrato.objects.filter(numero=dados['numero']).exists():
                raise ValidationError('Número do contrato já existe')
            
            # Validar datas
            if dados['data_termino'] <= dados['data_inicio']:
                raise ValidationError('Data de término deve ser posterior à data de início')
            
            # Criar contrato
            contrato = Contrato.objects.create(
                numero=dados['numero'],
                empresa=dados['empresa'],
                valor=dados['valor'],
                data_inicio=dados['data_inicio'],
                data_termino=dados['data_termino'],
                descricao=dados.get('descricao', ''),
                alerta_vencimento=dados.get('alerta_vencimento', 30)
            )
            
            self._log_action('create_contract', 'Contrato', str(contrato.id))
            return contrato
            
        except Exception as e:
            logger.error(f'Erro ao criar contrato: {str(e)}')
            raise
    
    @transaction.atomic
    def atualizar_contrato(self, contrato_id: int, dados: Dict) -> Contrato:
        """
        Atualizar dados do contrato
        """
        try:
            contrato = Contrato.objects.get(id=contrato_id)
            
            # Verificar permissões (removido - sem campo usuario no modelo)
            # if not self.user.is_staff and contrato.usuario != self.user:
            #     raise ValidationError('Sem permissão para editar este contrato')
            
            # Atualizar campos
            campos_permitidos = ['empresa', 'valor', 'data_inicio', 'data_termino', 'descricao', 'alerta_vencimento']
            for campo in campos_permitidos:
                if campo in dados:
                    setattr(contrato, campo, dados[campo])
            
            contrato.full_clean()
            contrato.save()
            
            self._log_action('update_contract', 'Contrato', str(contrato.id))
            return contrato
            
        except Contrato.DoesNotExist:
            raise ValidationError('Contrato não encontrado')
        except Exception as e:
            logger.error(f'Erro ao atualizar contrato: {str(e)}')
            raise
    
    def listar_contratos(self, filtros: Dict = None) -> List[Contrato]:
        """
        Listar contratos com filtros
        """
        from datetime import date
        queryset = Contrato.objects.all()
        
        # Filtrar por usuário se não for admin (removido - sem campo usuario no modelo)
        # if not self.user.is_staff:
        #     queryset = queryset.filter(usuario=self.user)
        
        if filtros:
            if filtros.get('empresa'):
                queryset = queryset.filter(empresa__icontains=filtros['empresa'])
            if filtros.get('numero'):
                queryset = queryset.filter(numero__icontains=filtros['numero'])
            if filtros.get('status'):
                status = filtros['status']
                hoje = date.today()
                if status == 'Vencido':
                    queryset = queryset.extra(
                        where=["(data_termino - %s) < 0"],
                        params=[hoje]
                    )
                elif status == 'Alerta de vencimento':
                    queryset = queryset.extra(
                        where=["(data_termino - %s) <= alerta_vencimento AND (data_termino - %s) >= 0"],
                        params=[hoje, hoje]
                    )
                elif status == 'Ativo':
                    queryset = queryset.extra(
                        where=["(data_termino - %s) > alerta_vencimento"],
                        params=[hoje]
                    )
            if filtros.get('vencendo'):
                data_limite = date.today() + timedelta(days=30)
                queryset = queryset.filter(data_termino__lte=data_limite)
            if filtros.get('data_inicio'):
                queryset = queryset.filter(data_inicio__gte=filtros['data_inicio'])
            if filtros.get('data_termino'):
                queryset = queryset.filter(data_termino__lte=filtros['data_termino'])
        
        return queryset.order_by('-data_inicio')
    
    def obter_estatisticas_contrato(self, contrato_id: int) -> Dict:
        """
        Obter estatísticas de um contrato específico
        """
        try:
            contrato = Contrato.objects.get(id=contrato_id)
            
            # Verificar permissões (removido - sem campo usuario no modelo)
            # if not self.user.is_staff and contrato.usuario != self.user:
            #     raise ValidationError('Sem permissão para deletar este contrato')
            
            notas = Nota.objects.filter(contrato=contrato)
            
            return {
                'total_notas': notas.count(),
                'notas_processadas': notas.filter(data_saida__isnull=False).count(),
                'notas_pendentes': notas.filter(data_saida__isnull=True).count(),
                'valor_total_notas': notas.aggregate(Sum('valor'))['valor__sum'] or 0,
                'tempo_medio_processamento': self._calcular_tempo_medio_processamento(notas)
            }
            
        except Contrato.DoesNotExist:
            raise ValidationError('Contrato não encontrado')
    
    def _calcular_tempo_medio_processamento(self, notas) -> float:
        """
        Calcular tempo médio de processamento das notas
        """
        notas_processadas = notas.filter(data_saida__isnull=False)
        if not notas_processadas.exists():
            return 0
        
        total_dias = sum([
            (nota.data_saida - nota.data_entrada).days 
            for nota in notas_processadas
        ])
        
        return total_dias / notas_processadas.count()


class NotaService(BaseService):
    """
    Service para gerenciar operações relacionadas a notas
    """
    
    @transaction.atomic
    def criar_nota(self, dados: Dict) -> Nota:
        """
        Criar uma nova nota com validações
        """
        try:
            # Validar dados obrigatórios
            campos_obrigatorios = ['numero', 'empresa', 'valor', 'data_entrada', 'setor']
            for campo in campos_obrigatorios:
                if not dados.get(campo):
                    raise ValidationError(f'Campo {campo} é obrigatório')
            
            # Verificar se já existe nota com mesmo número e empresa
            if Nota.objects.filter(
                numero=dados['numero'],
                empresa__iexact=dados['empresa']
            ).exists():
                raise ValidationError(
                    f'Já existe uma nota com o número "{dados["numero"]}" para a empresa "{dados["empresa"]}"'
                )
            
            # Criar nota
            # Definir data de saída automaticamente se não foi informada
            from django.utils import timezone
            data_saida_padrao = dados.get('data_saida') or timezone.now().date()

            nota = Nota.objects.create(
                numero=dados['numero'],
                empresa=dados['empresa'],
                valor=dados['valor'],
                data_entrada=dados['data_entrada'],
                data_nota=dados.get('data_nota', dados['data_entrada']),
                setor=dados['setor'],
                empenho=dados.get('empenho', ''),
                observacoes=dados.get('observacoes', ''),
                contrato_id=dados.get('contrato_id'),
                data_saida=data_saida_padrao
            )
            
            self._log_action('create_note', 'Nota', str(nota.id))
            return nota
            
        except Exception as e:
            logger.error(f'Erro ao criar nota: {str(e)}')
            raise
    
    @transaction.atomic
    def processar_nota(self, nota_id: int, data_saida: date = None) -> Nota:
        """
        Marcar nota como processada
        """
        try:
            nota = Nota.objects.get(id=nota_id)
            
            # Verificar permissões (removido - sem campo usuario no modelo)
            # if not self.user.is_staff and nota.usuario != self.user:
            #     raise ValidationError('Sem permissão para processar esta nota')
            
            if nota.data_saida:
                raise ValidationError('Nota já foi processada')
            
            nota.data_saida = data_saida or date.today()
            nota.save()
            
            self._log_action('process_note', 'Nota', str(nota.id))
            return nota
            
        except Nota.DoesNotExist:
            raise ValidationError('Nota não encontrada')
        except Exception as e:
            logger.error(f'Erro ao processar nota: {str(e)}')
            raise
    
    def listar_notas(self, filtros: Dict = None) -> List[Nota]:
        """
        Listar notas com filtros
        """
        queryset = Nota.objects.select_related('contrato')
        
        # Filtrar por usuário se não for admin (removido - sem campo usuario no modelo)
        # if not self.user.is_staff:
        #     queryset = queryset.filter(usuario=self.user)
        
        if filtros:
            if filtros.get('empresa'):
                queryset = queryset.filter(empresa__icontains=filtros['empresa'])
            if filtros.get('setor'):
                queryset = queryset.filter(setor__icontains=filtros['setor'])

            if filtros.get('data_inicio'):
                queryset = queryset.filter(data_entrada__gte=filtros['data_inicio'])
            if filtros.get('data_fim'):
                queryset = queryset.filter(data_entrada__lte=filtros['data_fim'])
            if filtros.get('contrato_id'):
                queryset = queryset.filter(contrato_id=filtros['contrato_id'])
        
        return queryset.order_by('-data_entrada')


class DashboardService(BaseService):
    """
    Service para gerar dados do dashboard
    """
    
    def obter_estatisticas_gerais(self) -> Dict:
        """
        Obter estatísticas gerais para o dashboard
        """
        # Filtrar por usuário se não for staff (removido - sem campo usuario no modelo)
        contratos_qs = Contrato.objects.all()
        notas_qs = Nota.objects.all()
        
        # if not self.user.is_staff:
        #     contratos_qs = contratos_qs.filter(usuario=self.user)
        #     notas_qs = notas_qs.filter(usuario=self.user)
        
        # Estatísticas de contratos
        total_contratos = contratos_qs.count()
        contratos_vencendo = contratos_qs.filter(
            data_termino__lte=date.today() + timedelta(days=30)
        ).count()
        
        # Estatísticas de notas
        total_notas = notas_qs.count()
        notas_pendentes = notas_qs.filter(data_saida__isnull=True).count()
        notas_processadas = notas_qs.filter(data_saida__isnull=False).count()
        
        # Valores
        valor_total_contratos = contratos_qs.aggregate(Sum('valor'))['valor__sum'] or 0
        valor_total_notas = notas_qs.aggregate(Sum('valor'))['valor__sum'] or 0
        
        return {
            'contratos': {
                'total': total_contratos,
                'vencendo': contratos_vencendo,
                'valor_total': float(valor_total_contratos)
            },
            'notas': {
                'total': total_notas,
                'pendentes': notas_pendentes,
                'processadas': notas_processadas,
                'valor_total': float(valor_total_notas)
            }
        }
    
    def obter_dados_graficos(self) -> Dict:
        """
        Obter dados para gráficos do dashboard
        """
        # Filtrar por usuário se não for staff
        notas_qs = Nota.objects.all()
        if not self.user.is_staff:
            notas_qs = notas_qs.filter(usuario=self.user)
        
        # Notas por mês (últimos 12 meses)
        hoje = date.today()
        inicio_periodo = hoje.replace(day=1) - timedelta(days=365)
        
        notas_por_mes = []
        for i in range(12):
            mes_inicio = (inicio_periodo + timedelta(days=30*i)).replace(day=1)
            mes_fim = (mes_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            count = notas_qs.filter(
                data_entrada__gte=mes_inicio,
                data_entrada__lte=mes_fim
            ).count()
            
            notas_por_mes.append({
                'mes': mes_inicio.strftime('%Y-%m'),
                'total': count
            })
        
        # Notas por setor
        notas_por_setor = list(
            notas_qs.values('setor')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        
        return {
            'notas_por_mes': notas_por_mes,
            'notas_por_setor': notas_por_setor
        }


class RelatorioService(BaseService):
    """
    Service para gerar relatórios
    """
    
    def gerar_relatorio_contratos(self, filtros: Dict = None) -> Dict:
        """
        Gerar relatório de contratos
        """
        contrato_service = ContratoService(self.user)
        contratos = contrato_service.listar_contratos(filtros)
        
        # Calcular estatísticas
        total_contratos = contratos.count()
        valor_total = contratos.aggregate(Sum('valor'))['valor__sum'] or 0
        valor_medio = contratos.aggregate(Avg('valor'))['valor__avg'] or 0
        
        return {
            'contratos': list(contratos.values()),
            'estatisticas': {
                'total_contratos': total_contratos,
                'valor_total': float(valor_total),
                'valor_medio': float(valor_medio)
            }
        }
    
    def gerar_relatorio_notas(self, filtros: Dict = None) -> Dict:
        """
        Gerar relatório de notas
        """
        nota_service = NotaService(self.user)
        notas = nota_service.listar_notas(filtros)
        
        # Calcular estatísticas
        total_notas = notas.count()
        notas_processadas = notas.filter(data_saida__isnull=False).count()
        notas_pendentes = notas.filter(data_saida__isnull=True).count()
        valor_total = notas.aggregate(Sum('valor'))['valor__sum'] or 0
        
        return {
            'notas': list(notas.values()),
            'estatisticas': {
                'total_notas': total_notas,
                'notas_processadas': notas_processadas,
                'notas_pendentes': notas_pendentes,
                'valor_total': float(valor_total),
                'taxa_processamento': (notas_processadas / total_notas * 100) if total_notas > 0 else 0
            }
        }