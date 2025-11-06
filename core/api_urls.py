from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
# from rest_framework.documentation import include_docs_urls
# from rest_framework.schemas import get_schema_view
from django.views.generic import TemplateView

from .api_views import (
    UsuarioViewSet, ContratoViewSet, NotaViewSet, DashboardAPIView, EmpresaAutocompleteView
)

# Configurar router para ViewSets
router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'contratos', ContratoViewSet, basename='contrato')
router.register(r'notas', NotaViewSet, basename='nota')

# Schema da API
# schema_view = get_schema_view(
#     title='Sistema de Notas API',
#     description='API REST para o Sistema de Gerenciamento de Notas e Contratos',
#     version='1.0.0',
#     public=True,
# )

urlpatterns = [
    # Endpoints da API
    path('', include(router.urls)),
    
    # Autocomplete endpoints
    path('empresas/autocomplete/', EmpresaAutocompleteView.as_view({'get': 'list'}), name='empresa_autocomplete'),
    
    # Dashboard endpoint
    path('dashboard/', DashboardAPIView.as_view({'get': 'stats'}), name='dashboard_api'),
    
    # Autenticação
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # Documentação (temporariamente desabilitada - requer coreapi)
    # path('docs/', include_docs_urls(title='Sistema de Notas API')),
    # path('schema/', schema_view, name='openapi-schema'),
    # path('redoc/', TemplateView.as_view(
    #     template_name='redoc.html',
    #     extra_context={'schema_url': 'openapi-schema'}
    # ), name='redoc'),
    
    # Endpoints customizados adicionais
    path('health/', include([
        path('', lambda request: JsonResponse({'status': 'ok', 'timestamp': timezone.now().isoformat()})),
        path('db/', lambda request: JsonResponse({
            'status': 'ok' if connection.ensure_connection() is None else 'error',
            'timestamp': timezone.now().isoformat()
        })),
    ])),
]

# Importações necessárias para os endpoints de health
from django.http import JsonResponse
from django.utils import timezone
from django.db import connection