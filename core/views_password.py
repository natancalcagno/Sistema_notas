from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, View, RedirectView
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from .forms import AlterarSenhaForm, EsqueciSenhaForm, RedefinirSenhaForm
from .models import TokenRedefinicaoSenha

class AlterarSenhaView(LoginRequiredMixin, FormView):
    template_name = 'alterar_senha.html'
    form_class = AlterarSenhaForm
    success_url = reverse_lazy('core:home')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Sua senha foi alterada com sucesso!')
        return super().form_valid(form)

class EsqueciSenhaView(FormView):
    template_name = 'esqueci_senha.html'
    form_class = EsqueciSenhaForm
    success_url = reverse_lazy('core:login')

    def get_success_url(self):
        messages.success(
            self.request,
            'Um email com instruções para redefinir sua senha foi enviado. '
            'Por favor, verifique sua caixa de entrada e spam.'
        )
        return super().get_success_url()

    def form_invalid(self, form):
        print(f"Erros no formulário: {form.errors}")
        return super().form_invalid(form)

    def form_valid(self, form):
        try:
            print("Iniciando processo de recuperação de senha...")
            
            email = form.cleaned_data['email']
            print(f"Email recebido: {email}")
            
            user = form.user
            print(f"Usuário encontrado: {user.username}")

            # Invalida tokens antigos não utilizados
            TokenRedefinicaoSenha.objects.filter(
                user=user,
                usado=False
            ).update(usado=True)
            print("Tokens antigos invalidados")

            # Criar token de redefinição
            token = TokenRedefinicaoSenha.objects.create(user=user)
            print(f"Novo token criado: {token.token}")

            # Gerar link de redefinição
            host = self.request.get_host()
            protocol = 'https' if self.request.is_secure() else 'http'
            reset_url = f"{protocol}://{host}/redefinir-senha/{token.token}/"
            print(f"URL de redefinição: {reset_url}")
            
            mail_subject = 'Redefinição de Senha - Sistema de Notas'
            message = render_to_string('email/redefinir_senha.html', {
                'user': user,
                'reset_url': reset_url,
                'valid_hours': 24  # Tempo de validade do token
            })

            try:
                from django.conf import settings
                print(f"Configurações de email: Backend={settings.EMAIL_BACKEND}")
                
                print("Conteúdo do email que será enviado:")
                print("-" * 50)
                print(f"Assunto: {mail_subject}")
                print(f"Para: {email}")
                print(f"Conteúdo:")
                print(message)
                print("-" * 50)

                # Enviar email usando o método mais simples
                send_mail(
                    subject=mail_subject,
                    message='',  # Versão texto plano (vazia porque usaremos HTML)
                    html_message=message,  # Versão HTML
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                print("Email enviado com sucesso!")
                
            except Exception as e:
                print(f"Erro detalhado ao enviar email: {str(e)}")
                print(f"Tipo do erro: {type(e).__name__}")
                import traceback
                print("Traceback completo:")
                print(traceback.format_exc())
                token.delete()
                print("Token deletado após erro")
                raise

            messages.success(
                self.request, 
                'Um link para redefinição de senha foi enviado para seu email. '
                'Por favor, verifique sua caixa de entrada.'
            )
            return super().form_valid(form)

        except Exception as e:
            messages.error(
                self.request,
                'Ocorreu um erro ao processar sua solicitação. '
                'Por favor, tente novamente mais tarde.'
            )
            return self.form_invalid(form)

class RedefinirSenhaView(FormView):
    template_name = 'redefinir_senha.html'
    form_class = RedefinirSenhaForm
    success_url = reverse_lazy('core:login')

    def form_invalid(self, form):
        print(f"Erros no formulário de redefinição: {form.errors}")
        return super().form_invalid(form)

    def get_token(self):
        return get_object_or_404(
            TokenRedefinicaoSenha, 
            token=self.kwargs['token'],
            usado=False,
            data_expiracao__gt=timezone.now()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            token = self.get_token()
            context['token_valido'] = True
            context['user'] = token.user
        except:
            context['token_valido'] = False
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            token = self.get_token()
            kwargs['user'] = token.user
        except:
            kwargs['user'] = None
        return kwargs

    def form_valid(self, form):
        token = self.get_token()
        form.save()
        
        # Invalidar o token após uso
        token.usado = True
        token.save()

        messages.success(self.request, 'Sua senha foi redefinida com sucesso! Você já pode fazer login com a nova senha.')
        return super().form_valid(form)