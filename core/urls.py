# # ----------------------------------------------------
# # Conteúdo para o arquivo: core/urls.py
# # ----------------------------------------------------
# from django.urls import path
# from .views import (
#     CustomLoginView, ContratoListView, ContratoCreateView, ContratoUpdateView, ContratoDeleteView,
#     NotaListView, NotaCreateView, NotaUpdateView, NotaDeleteView,
#     UserListView, UserCreateView, UserUpdateView, RelatoriosView
# )
# from django.contrib.auth.views import LogoutView

# urlpatterns = [
#     path('login/', CustomLoginView.as_view(), name='login'),
#     path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

#     path('', ContratoListView.as_view(), name='lista_contratos'),
#     path('contratos/', ContratoListView.as_view(), name='lista_contratos'),
#     path('contratos/novo/', ContratoCreateView.as_view(), name='novo_contrato'),
#     path('contratos/editar/<int:pk>/', ContratoUpdateView.as_view(), name='editar_contrato'),
#     path('contratos/excluir/<int:pk>/', ContratoDeleteView.as_view(), name='excluir_contrato'),

#     path('notas/', NotaListView.as_view(), name='lista_notas'),
#     path('notas/nova/', NotaCreateView.as_view(), name='nova_nota'),
#     path('notas/editar/<int:pk>/', NotaUpdateView.as_view(), name='editar_nota'),
#     path('notas/excluir/<int:pk>/', NotaDeleteView.as_view(), name='excluir_nota'),
    
#     path('usuarios/', UserListView.as_view(), name='lista_usuarios'),
#     path('usuarios/novo/', UserCreateView.as_view(), name='novo_usuario'),
#     path('usuarios/editar/<int:pk>/', UserUpdateView.as_view(), name='editar_usuario'),

#     path('relatorios/', RelatoriosView.as_view(), name='relatorios'),
# ]


from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    LoginView, HomeView,
    ContratoListView, ContratoCreateView, ContratoUpdateView, ContratoDeleteView,
    NotaListView, NotaCreateView, NotaUpdateView, NotaDeleteView,
    RelatoriosView, GerarProtocoloView,
    UsuarioListView, UsuarioCreateView, UsuarioUpdateView,
    AlterarSenhaView, EsqueciSenhaView, RedefinirSenhaView
)

urlpatterns = [
    # URLs de Autenticação
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # URL da página inicial
    path('', HomeView.as_view(), name='home'),

    # URLs de Contratos
    path('contratos/', ContratoListView.as_view(), name='lista_contratos'),
    path('contratos/novo/', ContratoCreateView.as_view(), name='novo_contrato'),
    path('contratos/editar/<int:pk>/', ContratoUpdateView.as_view(), name='editar_contrato'),
    path('contratos/excluir/<int:pk>/', ContratoDeleteView.as_view(), name='excluir_contrato'),
    
    # URLs de Notas
    path('notas/', NotaListView.as_view(), name='lista_notas'),
    path('notas/nova/', NotaCreateView.as_view(), name='nova_nota'),
    path('notas/editar/<int:pk>/', NotaUpdateView.as_view(), name='editar_nota'),
    path('notas/excluir/<int:pk>/', NotaDeleteView.as_view(), name='excluir_nota'),
    
    # URLs de Relatórios
    path('relatorios/', RelatoriosView.as_view(), name='relatorios'),
    path('gerar-protocolo/', GerarProtocoloView.as_view(), name='gerar_protocolo'),
    
    # URLs de Usuários
    path('usuarios/', UsuarioListView.as_view(), name='lista_usuarios'),
    path('usuarios/novo/', UsuarioCreateView.as_view(), name='novo_usuario'),
    path('usuarios/editar/<int:pk>/', UsuarioUpdateView.as_view(), name='editar_usuario'),
    
    # URLs de Gerenciamento de Senha
    path('alterar-senha/', AlterarSenhaView.as_view(), name='alterar_senha'),
    path('esqueci-senha/', EsqueciSenhaView.as_view(), name='esqueci_senha'),
    path('redefinir-senha/<str:token>/', RedefinirSenhaView.as_view(), name='redefinir_senha'),
]
