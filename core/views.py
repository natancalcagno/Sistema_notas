from django.shortcuts import render, redirect
from django.views.generic import View, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Contrato, Nota, Usuario
from .forms import ContratoForm, NotaForm, UsuarioForm, UsuarioUpdateForm
from .views_password import AlterarSenhaView, EsqueciSenhaView, RedefinirSenhaView
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse, FileResponse
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import datetime
import io

# Views de Autenticação
class LoginView(LoginView):
    template_name = 'login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('home')

# View da Home
class HomeView(LoginRequiredMixin, ListView):
    model = Nota
    template_name = 'dashboard.html'
    context_object_name = 'notas'
    paginate_by = 10

    def get_queryset(self):
        queryset = Nota.objects.all().order_by('-data_entrada')
        
        # Aplicar filtros
        empresa = self.request.GET.get('empresa')
        empenho = self.request.GET.get('empenho')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')

        if empresa:
            queryset = queryset.filter(empresa__icontains=empresa)
        if empenho:
            queryset = queryset.filter(empenho__icontains=empenho)
        if data_inicio:
            queryset = queryset.filter(data_entrada__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data_entrada__lte=data_fim)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adicionar variáveis dos filtros no contexto
        context['empresa'] = self.request.GET.get('empresa', '')
        context['empenho'] = self.request.GET.get('empenho', '')
        context['data_inicio'] = self.request.GET.get('data_inicio', '')
        context['data_fim'] = self.request.GET.get('data_fim', '')

        # Estatísticas gerais
        context['total_notas'] = Nota.objects.count()
        context['notas_pendentes'] = Nota.objects.filter(data_saida__isnull=True).count()
        context['total_valor'] = Nota.objects.aggregate(total=Sum('valor'))['total'] or 0

        return context

# Views de Contratos
class ContratoListView(LoginRequiredMixin, ListView):
    model = Contrato
    template_name = 'lista_contratos.html'
    context_object_name = 'contratos'
    paginate_by = 10

    def get_queryset(self):
        return Contrato.objects.all().order_by('-data_inicio')

class ContratoCreateView(LoginRequiredMixin, CreateView):
    model = Contrato
    template_name = 'form_contrato.html'
    form_class = ContratoForm
    success_url = reverse_lazy('lista_contratos')

    def form_valid(self, form):
        messages.success(self.request, 'Contrato criado com sucesso!')
        return super().form_valid(form)

class ContratoUpdateView(LoginRequiredMixin, UpdateView):
    model = Contrato
    template_name = 'form_contrato.html'
    form_class = ContratoForm
    success_url = reverse_lazy('lista_contratos')

    def form_valid(self, form):
        messages.success(self.request, 'Contrato atualizado com sucesso!')
        return super().form_valid(form)

class ContratoDeleteView(LoginRequiredMixin, DeleteView):
    model = Contrato
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('lista_contratos')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Contrato excluído com sucesso!')
        return super().delete(request, *args, **kwargs)

# Views de Notas
class NotaListView(LoginRequiredMixin, ListView):
    model = Nota
    template_name = 'lista_notas.html'
    context_object_name = 'notas'
    paginate_by = 10

    def get_queryset(self):
        return Nota.objects.all().order_by('-data_entrada')

class NotaCreateView(LoginRequiredMixin, CreateView):
    model = Nota
    template_name = 'form_nota.html'
    form_class = NotaForm
    success_url = reverse_lazy('lista_notas')

    def form_valid(self, form):
        messages.success(self.request, 'Nota criada com sucesso!')
        return super().form_valid(form)

class NotaUpdateView(LoginRequiredMixin, UpdateView):
    model = Nota
    template_name = 'form_nota.html'
    form_class = NotaForm
    success_url = reverse_lazy('lista_notas')

    def form_valid(self, form):
        messages.success(self.request, 'Nota atualizada com sucesso!')
        return super().form_valid(form)

class NotaDeleteView(LoginRequiredMixin, DeleteView):
    model = Nota
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('lista_notas')

    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            return redirect('lista_notas')
        messages.success(self.request, 'Nota excluída com sucesso!')
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipo_objeto'] = 'nota'
        return context

# Views de Relatórios
class RelatoriosView(LoginRequiredMixin, ListView):
    model = Nota
    template_name = 'relatorios.html'
    context_object_name = 'notas'
    paginate_by = 10

    def get_queryset(self):
        queryset = Nota.objects.all().order_by('-data_entrada')
        contrato_id = self.request.GET.get('contrato')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')

        if contrato_id:
            queryset = queryset.filter(contrato=contrato_id)
        if data_inicio:
            queryset = queryset.filter(data_entrada__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data_entrada__lte=data_fim)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contratos'] = Contrato.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        export_type = request.POST.get('export_type')
        queryset = self.get_queryset()

        if export_type == 'pdf':
            # Lógica de exportação para PDF
            buffer = io.BytesIO()
            return FileResponse(buffer, as_attachment=True, filename='relatorio_notas.pdf')
        
        elif export_type == 'excel':
            # Lógica de exportação para Excel
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=relatorio_notas.xlsx'
            return response
        
        elif export_type == 'word':
            # Lógica de exportação para Word
            response = HttpResponse(content_type='application/msword')
            response['Content-Disposition'] = 'attachment; filename=relatorio_notas.doc'
            return response
        
        return redirect('relatorios')

class GerarProtocoloView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notas_ids = request.POST.getlist('notas_selecionadas')
        notas = Nota.objects.filter(id__in=notas_ids).order_by('data_entrada')
        
        if not notas:
            messages.error(request, 'Nenhuma nota selecionada.')
            return redirect('home')

        # Criar documento Word
        doc = Document()
        
        # Configurar margens
        sections = doc.sections
        for section in sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2)
            section.right_margin = Cm(2)

        # Título
        titulo = doc.add_paragraph('PROTOCOLO PARA ENTREGA DE NOTAS FISCAIS\nUNIDADE DE CONTROLE INTERNO')
        titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        titulo.runs[0].bold = True

        # Texto introdutório
        doc.add_paragraph('Atestamos que as respectivas notas foram entregues para Contabilidade nesta presente data, pois encontram APTAS para liquidação, e posterior pagamento.')
        
        # Criar tabela
        table = doc.add_table(rows=1, cols=7)
        table.style = 'Table Grid'

        # Cabeçalho da tabela
        header_cells = table.rows[0].cells
        headers = ['Nº', 'Nº do Empenho', 'Nome da Empresa', 'NF', 'DATA/NF', 'SETOR', 'Valor EM R$']
        for i, text in enumerate(headers):
            header_cells[i].text = text
            header_cells[i].paragraphs[0].runs[0].bold = True

        # Adicionar dados
        for i, nota in enumerate(notas, 1):
            row_cells = table.add_row().cells
            row_cells[0].text = str(i)
            row_cells[1].text = nota.empenho or '-'
            row_cells[2].text = nota.empresa
            row_cells[3].text = str(nota.numero)
            row_cells[4].text = nota.data_entrada.strftime('%d/%m/%Y')
            row_cells[5].text = nota.setor
            row_cells[6].text = f'R$ {nota.valor:,.2f}'.replace(',', '.')

        # Adicionar assinaturas
        doc.add_paragraph('\n\nAtenciosamente,\n\n')
        doc.add_paragraph('_' * 40 + ' ' * 20 + '_' * 40)

        # Salvar documento
        f = io.BytesIO()
        doc.save(f)
        f.seek(0)

        # Gerar nome do arquivo
        data_atual = datetime.now().strftime('%d_%m_%Y')
        filename = f'protocolo_notas_{data_atual}.docx'

        response = HttpResponse(
            f,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response

# Views de Usuário
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.tipo_usuario == 'admin'

class UsuarioListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Usuario
    template_name = 'lista_usuarios.html'
    context_object_name = 'usuarios'
    paginate_by = 10

    def get_queryset(self):
        return Usuario.objects.all().order_by('first_name')

class UsuarioCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Usuario
    template_name = 'form_usuario.html'
    form_class = UsuarioForm
    success_url = reverse_lazy('lista_usuarios')

    def form_valid(self, form):
        messages.success(self.request, 'Usuário criado com sucesso!')
        return super().form_valid(form)

class UsuarioUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Usuario
    template_name = 'form_usuario.html'
    form_class = UsuarioUpdateForm
    success_url = reverse_lazy('lista_usuarios')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Usuário atualizado com sucesso!')
        return super().form_valid(form)
