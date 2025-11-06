from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy


class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin que requer que o usuário seja um administrador (staff)
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.error(self.request, 'Você precisa fazer login para acessar esta página.')
            return redirect('core:login')
        else:
            messages.error(self.request, 'Você não tem permissão para acessar esta página.')
            return redirect('core:home')


class OwnerRequiredMixin(UserPassesTestMixin):
    """
    Mixin que requer que o usuário seja o proprietário do objeto ou um administrador
    """
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        
        # Administradores podem acessar qualquer objeto
        if self.request.user.is_staff:
            return True
        
        # Verificar se o usuário é o proprietário do objeto
        obj = self.get_object()
        return hasattr(obj, 'usuario') and obj.usuario == self.request.user
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.error(self.request, 'Você precisa fazer login para acessar esta página.')
            return redirect('login')
        else:
            messages.error(self.request, 'Você não tem permissão para acessar este item.')
            return redirect('dashboard')


class AjaxResponseMixin:
    """
    Mixin para lidar com requisições AJAX
    """
    def dispatch(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            self.is_ajax = True
        else:
            self.is_ajax = False
        return super().dispatch(request, *args, **kwargs)


class MessageMixin:
    """
    Mixin para adicionar mensagens de sucesso/erro automaticamente
    """
    success_message = None
    error_message = None
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response
    
    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.error_message:
            messages.error(self.request, self.error_message)
        return response


class FilterMixin:
    """
    Mixin para filtrar objetos por usuário (não-administradores só veem seus próprios objetos)
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Administradores veem todos os objetos
        if self.request.user.is_staff:
            return queryset
        
        # Usuários comuns só veem seus próprios objetos
        if hasattr(queryset.model, 'usuario'):
            return queryset.filter(usuario=self.request.user)
        
        return queryset


class PaginationMixin:
    """
    Mixin para adicionar paginação consistente
    """
    paginate_by = 10
    
    def get_paginate_by(self, queryset):
        # Permitir que o usuário escolha quantos itens por página
        per_page = self.request.GET.get('per_page', self.paginate_by)
        try:
            per_page = int(per_page)
            if per_page > 100:  # Limite máximo
                per_page = 100
            elif per_page < 5:  # Limite mínimo
                per_page = 5
        except (ValueError, TypeError):
            per_page = self.paginate_by
        
        return per_page


class SearchMixin:
    """
    Mixin para adicionar funcionalidade de busca
    """
    search_fields = []
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query and self.search_fields:
            from django.db.models import Q
            search_filter = Q()
            
            for field in self.search_fields:
                search_filter |= Q(**{f'{field}__icontains': search_query})
            
            queryset = queryset.filter(search_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context