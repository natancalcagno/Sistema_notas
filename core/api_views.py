from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import HttpResponse
import csv
import json
from io import StringIO

from .models import Contrato, Nota, Usuario
from .serializers import (
    UsuarioSerializer, ContratoSerializer, NotaSerializer,
    ContratoResumoSerializer, NotaResumoSerializer,
    DashboardStatsSerializer, RelatorioSerializer
)
from .cache_utils import CacheManager
from .logging_config import audit_logger, performance_logger
from .pagination import OptimizedPaginator

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    """Paginação padrão para a API"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permissão customizada para permitir apenas ao proprietário editar"""
    
    def has_object_permission(self, request, view, obj):
        # Permissões de leitura para qualquer usuário autenticado
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permissões de escrita apenas para o proprietário
        return obj.usuario == request.user or request.user.is_staff


class UsuarioViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar usuários"""
    
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name', 'date_joined']
    ordering = ['-date_joined']
    
    def perform_create(self, serializer):
        """Log da criação de usuário"""
        user = serializer.save()
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='user_created',
            model='Usuario',
            object_id=user.id,
            details={'username': user.username, 'email': user.email}
        )
    
    def perform_update(self, serializer):
        """Log da atualização de usuário"""
        user = serializer.save()
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='user_updated',
            model='Usuario',
            object_id=user.id,
            details={'username': user.username}
        )
    
    def perform_destroy(self, instance):
        """Log da exclusão de usuário"""
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='user_deleted',
            model='Usuario',
            object_id=instance.id,
            details={'username': instance.username}
        )
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Retorna informações do usuário atual"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        """Alterar senha do usuário"""
        user = self.get_object()
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')
        
        if not password or not confirm_password:
            return Response(
                {'error': 'Password and confirm_password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if password != confirm_password:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(password)
        user.save()
        
        audit_logger.log_user_action(
            user_id=request.user.id,
            action='password_changed',
            model='Usuario',
            object_id=user.id
        )
        
        return Response({'message': 'Password updated successfully'})


class ContratoViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar contratos"""
    
    queryset = Contrato.objects.select_related('usuario').all()
    serializer_class = ContratoSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['empresa', 'ativo', 'usuario']
    search_fields = ['numero', 'empresa', 'cnpj', 'descricao']
    ordering_fields = ['numero', 'empresa', 'valor', 'data_inicio', 'data_fim', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrar contratos baseado no usuário"""
        queryset = super().get_queryset()
        
        # Usuários não-staff só veem seus próprios contratos
        if not self.request.user.is_staff:
            queryset = queryset.filter(usuario=self.request.user)
        
        # Filtros adicionais
        status_filter = self.request.query_params.get('status')
        if status_filter == 'ativo':
            queryset = queryset.filter(ativo=True, data_fim__gte=timezone.now().date())
        elif status_filter == 'vencido':
            queryset = queryset.filter(data_fim__lt=timezone.now().date())
        elif status_filter == 'inativo':
            queryset = queryset.filter(ativo=False)
        
        return queryset
    
    def get_serializer_class(self):
        """Usar serializer resumido para listagem"""
        if self.action == 'list':
            return ContratoResumoSerializer
        return ContratoSerializer
    
    def perform_create(self, serializer):
        """Definir usuário atual como proprietário"""
        contrato = serializer.save(usuario=self.request.user)
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='contrato_created',
            model='Contrato',
            object_id=contrato.id,
            details={'numero': contrato.numero, 'empresa': contrato.empresa}
        )
    
    def perform_update(self, serializer):
        """Log da atualização"""
        contrato = serializer.save()
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='contrato_updated',
            model='Contrato',
            object_id=contrato.id,
            details={'numero': contrato.numero}
        )
    
    def perform_destroy(self, instance):
        """Log da exclusão"""
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='contrato_deleted',
            model='Contrato',
            object_id=instance.id,
            details={'numero': instance.numero}
        )
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def notas(self, request, pk=None):
        """Listar notas de um contrato específico"""
        contrato = self.get_object()
        notas = contrato.notas.all().order_by('-created_at')
        
        page = self.paginate_queryset(notas)
        if page is not None:
            serializer = NotaResumoSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = NotaResumoSerializer(notas, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def estatisticas(self, request, pk=None):
        """Estatísticas de um contrato específico"""
        contrato = self.get_object()
        notas = contrato.notas.all()
        
        stats = {
            'total_notas': notas.count(),
            'valor_total_notas': notas.aggregate(Sum('valor'))['valor__sum'] or 0,
            'media_valor_notas': notas.aggregate(Avg('valor'))['valor__avg'] or 0,
            'notas_pendentes': notas.filter(data_saida__isnull=True).count(),
            'notas_processadas': notas.filter(data_saida__isnull=False).count(),
            'tempo_medio_processamento': self._calcular_tempo_medio_processamento(notas)
        }
        
        return Response(stats)
    
    def _calcular_tempo_medio_processamento(self, notas):
        """Calcula tempo médio de processamento das notas"""
        notas_processadas = notas.filter(data_saida__isnull=False)
        if not notas_processadas.exists():
            return None
        
        total_dias = 0
        count = 0
        
        for nota in notas_processadas:
            dias = (nota.data_saida - nota.data_entrada).days
            total_dias += dias
            count += 1
        
        return round(total_dias / count, 2) if count > 0 else None


class NotaViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar notas"""
    
    queryset = Nota.objects.select_related('contrato', 'usuario').all()
    serializer_class = NotaSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['empresa', 'contrato', 'usuario']
    search_fields = ['numero', 'empresa', 'empenho', 'observacoes']
    ordering_fields = ['numero', 'empresa', 'valor', 'data_entrada', 'data_saida', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrar notas baseado no usuário"""
        queryset = super().get_queryset()
        
        # Usuários não-staff só veem suas próprias notas
        if not self.request.user.is_staff:
            queryset = queryset.filter(usuario=self.request.user)
        
        # Filtros adicionais
        
        # Filtro por período
        data_inicio = self.request.query_params.get('data_inicio')
        data_fim = self.request.query_params.get('data_fim')
        
        if data_inicio:
            try:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                queryset = queryset.filter(data_entrada__gte=data_inicio)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                queryset = queryset.filter(data_entrada__lte=data_fim)
            except ValueError:
                pass
        
        return queryset
    
    def get_serializer_class(self):
        """Usar serializer resumido para listagem"""
        if self.action == 'list':
            return NotaResumoSerializer
        return NotaSerializer
    
    def perform_create(self, serializer):
        """Definir usuário atual como proprietário"""
        nota = serializer.save(usuario=self.request.user)
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='nota_created',
            model='Nota',
            object_id=nota.id,
            details={'numero': nota.numero, 'empresa': nota.empresa}
        )
    
    def perform_update(self, serializer):
        """Log da atualização"""
        nota = serializer.save()
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='nota_updated',
            model='Nota',
            object_id=nota.id,
            details={'numero': nota.numero}
        )
    
    def perform_destroy(self, instance):
        """Log da exclusão"""
        audit_logger.log_user_action(
            user_id=self.request.user.id,
            action='nota_deleted',
            model='Nota',
            object_id=instance.id,
            details={'numero': instance.numero}
        )
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def processar(self, request, pk=None):
        """Marcar nota como processada"""
        nota = self.get_object()
        data_saida = request.data.get('data_saida')
        
        if not data_saida:
            data_saida = timezone.now().date()
        else:
            try:
                data_saida = datetime.strptime(data_saida, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de data inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if data_saida < nota.data_entrada:
            return Response(
                {'error': 'Data de saída não pode ser anterior à data de entrada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        nota.data_saida = data_saida
        nota.save()
        
        audit_logger.log_user_action(
            user_id=request.user.id,
            action='nota_processed',
            model='Nota',
            object_id=nota.id,
            details={'numero': nota.numero, 'data_saida': str(data_saida)}
        )
        
        serializer = self.get_serializer(nota)
        return Response(serializer.data)


class DashboardAPIView(viewsets.GenericViewSet):
    """API para dados do dashboard"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estatísticas gerais do dashboard"""
        # Tentar obter do cache primeiro
        cache_key = f'dashboard_stats_{request.user.id}'
        cached_stats = CacheManager.get_dashboard_stats()
        
        if cached_stats:
            return Response(cached_stats)
        
        # Calcular estatísticas
        start_time = timezone.now()
        
        # Filtrar por usuário se não for staff
        contratos_qs = Contrato.objects.all()
        notas_qs = Nota.objects.all()
        
        if not request.user.is_staff:
            contratos_qs = contratos_qs.filter(usuario=request.user)
            notas_qs = notas_qs.filter(usuario=request.user)
        
        # Estatísticas básicas
        total_contratos = contratos_qs.count()
        contratos_ativos = contratos_qs.filter(
            ativo=True, 
            data_fim__gte=timezone.now().date()
        ).count()
        contratos_vencidos = contratos_qs.filter(
            data_fim__lt=timezone.now().date()
        ).count()
        
        total_notas = notas_qs.count()
        notas_mes_atual = notas_qs.filter(
            data_entrada__month=timezone.now().month,
            data_entrada__year=timezone.now().year
        ).count()
        
        valor_total_contratos = contratos_qs.aggregate(
            Sum('valor')
        )['valor__sum'] or 0
        
        valor_total_notas = notas_qs.aggregate(
            Sum('valor')
        )['valor__sum'] or 0
        
        empresas_ativas = contratos_qs.filter(ativo=True).values('empresa').distinct().count()
        
        # Tempo médio de processamento
        notas_processadas = notas_qs.filter(data_saida__isnull=False)
        media_processamento = None
        
        if notas_processadas.exists():
            total_dias = 0
            count = 0
            for nota in notas_processadas:
                dias = (nota.data_saida - nota.data_entrada).days
                total_dias += dias
                count += 1
            media_processamento = round(total_dias / count, 2) if count > 0 else None
        
        # Dados para gráficos
        notas_por_mes = self._get_notas_por_mes(notas_qs)
        contratos_por_status = {
            'ativos': contratos_ativos,
            'vencidos': contratos_vencidos,
            'inativos': total_contratos - contratos_ativos - contratos_vencidos
        }
        top_empresas = self._get_top_empresas(contratos_qs)
        
        stats = {
            'total_contratos': total_contratos,
            'contratos_ativos': contratos_ativos,
            'contratos_vencidos': contratos_vencidos,
            'total_notas': total_notas,
            'notas_mes_atual': notas_mes_atual,
            'valor_total_contratos': float(valor_total_contratos),
            'valor_total_notas': float(valor_total_notas),
            'empresas_ativas': empresas_ativas,
            'media_processamento_dias': media_processamento,
            'notas_por_mes': notas_por_mes,
            'contratos_por_status': contratos_por_status,
            'top_empresas': top_empresas
        }
        
        # Log de performance
        execution_time = (timezone.now() - start_time).total_seconds()
        performance_logger.log_performance(
            operation='dashboard_stats',
            execution_time=execution_time,
            details={'user_id': request.user.id}
        )
        
        # Cachear resultado se for usuário staff (dados globais)
        if request.user.is_staff:
            CacheManager.cache_dashboard_stats(stats)
        
        return Response(stats)
    
    def _get_notas_por_mes(self, notas_qs):
        """Obter notas por mês dos últimos 12 meses"""
        hoje = timezone.now().date()
        resultado = {}
        
        for i in range(12):
            data = hoje.replace(day=1) - timedelta(days=30 * i)
            mes_key = data.strftime('%Y-%m')
            count = notas_qs.filter(
                data_entrada__year=data.year,
                data_entrada__month=data.month
            ).count()
            resultado[mes_key] = count
        
        return dict(sorted(resultado.items()))
    
    def _get_top_empresas(self, contratos_qs):
        """Obter top 5 empresas por valor de contratos"""
        empresas = contratos_qs.values('empresa').annotate(
            total_valor=Sum('valor'),
            total_contratos=Count('id')
        ).order_by('-total_valor')[:5]
        
        return [
            {
                'empresa': emp['empresa'],
                'valor': float(emp['total_valor']),
                'contratos': emp['total_contratos']
            }
            for emp in empresas
        ]
    
    @action(detail=False, methods=['post'])
    def relatorio(self, request):
        """Gerar relatório customizado"""
        serializer = RelatorioSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        params = serializer.validated_data
        formato = params.get('formato', 'json')
        
        # Construir queryset baseado nos parâmetros
        notas_qs = Nota.objects.select_related('contrato', 'usuario')
        
        if not request.user.is_staff:
            notas_qs = notas_qs.filter(usuario=request.user)
        
        if params.get('data_inicio'):
            notas_qs = notas_qs.filter(data_entrada__gte=params['data_inicio'])
        
        if params.get('data_fim'):
            notas_qs = notas_qs.filter(data_entrada__lte=params['data_fim'])
        
        if params.get('empresa'):
            notas_qs = notas_qs.filter(empresa__icontains=params['empresa'])
        
        if params.get('contrato_id'):
            notas_qs = notas_qs.filter(contrato_id=params['contrato_id'])
        
        # Gerar relatório no formato solicitado
        if formato == 'csv':
            return self._generate_csv_report(notas_qs, params)
        elif formato == 'excel':
            return self._generate_excel_report(notas_qs, params)
        elif formato == 'pdf':
            return self._generate_pdf_report(notas_qs, params)
        else:
            # JSON (padrão)
            if params.get('incluir_detalhes', True):
                serializer = NotaSerializer(notas_qs, many=True)
            else:
                serializer = NotaResumoSerializer(notas_qs, many=True)
            
            return Response({
                'total': notas_qs.count(),
                'parametros': params,
                'dados': serializer.data
            })
    
    def _generate_csv_report(self, queryset, params):
        """Gerar relatório em CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="relatorio_notas.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Número', 'Empresa', 'Valor', 'Data Entrada', 'Data Saída',
            'Empenho', 'Contrato', 'Usuário'
        ])
        
        for nota in queryset:
            writer.writerow([
                nota.numero,
                nota.empresa,
                nota.valor,
                nota.data_entrada,
                nota.data_saida or '',
                nota.empenho,
                nota.contrato.numero,
                nota.usuario.get_full_name()
            ])
        
        return response
    
    def _generate_excel_report(self, queryset, params):
        """Gerar relatório em Excel (placeholder)"""
        # Implementação futura com openpyxl
        return Response(
            {'error': 'Formato Excel não implementado ainda'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )
    
    def _generate_pdf_report(self, queryset, params):
        """Gerar relatório em PDF (placeholder)"""
        # Implementação futura com reportlab
        return Response(
            {'error': 'Formato PDF não implementado ainda'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class EmpresaAutocompleteView(viewsets.GenericViewSet):
    """View para autocomplete de empresas"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """Listar empresas para autocomplete"""
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return Response([])
        
        # Buscar empresas únicas nos contratos
        empresas_contratos = Contrato.objects.filter(
            empresa__icontains=query
        ).values_list('empresa', flat=True).distinct()[:10]
        
        # Buscar empresas únicas nas notas
        empresas_notas = Nota.objects.filter(
            empresa__icontains=query
        ).values_list('empresa', flat=True).distinct()[:10]
        
        # Combinar e remover duplicatas
        empresas = list(set(list(empresas_contratos) + list(empresas_notas)))
        empresas.sort()
        
        # Limitar a 10 resultados
        empresas = empresas[:10]
        
        return Response([
            {'value': empresa, 'label': empresa}
            for empresa in empresas
        ])