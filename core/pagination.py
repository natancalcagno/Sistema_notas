from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.template.loader import render_to_string

class AjaxPaginator:
    """
    Paginador customizado com suporte a AJAX para melhor experiência do usuário
    """
    
    def __init__(self, queryset, per_page=10):
        self.queryset = queryset
        self.per_page = per_page
        self.paginator = Paginator(queryset, per_page)
    
    def get_page_data(self, page_number, template_name, context=None):
        """
        Retorna dados da página para requisições AJAX
        """
        try:
            page = self.paginator.page(page_number)
        except PageNotAnInteger:
            page = self.paginator.page(1)
        except EmptyPage:
            page = self.paginator.page(self.paginator.num_pages)
        
        if context is None:
            context = {}
        
        context.update({
            'page_obj': page,
            'paginator': self.paginator,
            'is_paginated': self.paginator.num_pages > 1
        })
        
        html = render_to_string(template_name, context)
        
        return {
            'html': html,
            'has_next': page.has_next(),
            'has_previous': page.has_previous(),
            'page_number': page.number,
            'num_pages': self.paginator.num_pages,
            'count': self.paginator.count
        }

class OptimizedPaginator(Paginator):
    """
    Paginador otimizado que usa count() apenas quando necessário
    """
    
    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True):
        super().__init__(object_list, per_page, orphans, allow_empty_first_page)
        self._count = None
    
    @property
    def count(self):
        """
        Cache do count para evitar múltiplas consultas
        """
        if self._count is None:
            try:
                self._count = self.object_list.count()
            except (AttributeError, TypeError):
                self._count = len(self.object_list)
        return self._count