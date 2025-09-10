from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]


# from django.urls import path, include
# from django.contrib.auth.views import LoginView
# from core import views

# urlpatterns = [
#     # URLs de Autenticação
#     path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    
#     # URL da Home
#     path('', views.HomeView.as_view(), name='home'),
    
#     # URLs de Contrato
#     path('contratos/', views.ContratoListView.as_view(), name='contratos'),
#     path('contratos/novo/', views.ContratoCreateView.as_view(), name='novo_contrato'),
#     path('contratos/editar/<int:pk>/', views.ContratoUpdateView.as_view(), name='editar_contrato'),
#     path('contratos/excluir/<int:pk>/', views.ContratoDeleteView.as_view(), name='excluir_contrato'),
    
#     # URLs de Nota
#     path('notas/', views.NotaListView.as_view(), name='notas'),
#     path('notas/novo/', views.NotaCreateView.as_view(), name='novo_nota'),
#     path('notas/editar/<int:pk>/', views.NotaUpdateView.as_view(), name='editar_nota'),
#     path('notas/excluir/<int:pk>/', views.NotaDeleteView.as_view(), name='excluir_nota'),
    
#     # URLs de Relatório
#     path('relatorios/', views.RelatorioListView.as_view(), name='relatorios'),
#     path('relatorios/novo/', views.RelatorioCreateView.as_view(), name='novo_relatorio'),
#     path('relatorios/editar/<int:pk>/', views.RelatorioUpdateView.as_view(), name='editar_relatorio'),
#     path('relatorios/excluir/<int:pk>/', views.RelatorioDeleteView.as_view(), name='excluir_relatorio'),
#     path('relatorios/<int:pk>/', views.RelatorioView.as_view(), name='ver_relatorio'),
# ]
