# ----------------------------------------------------
# Conteúdo para o arquivo: core/forms.py
# ----------------------------------------------------
from django import forms
from django.core import validators
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Contrato, Nota, Usuario
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm

class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ['numero', 'empresa', 'valor', 'data_inicio', 'data_termino', 'descricao']
        widgets = {
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o número do contrato'
            }),
            'empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o nome da empresa'
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'data_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'data_termino': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Digite a descrição do contrato'
            })
        }
        labels = {
            'numero': 'Número do Contrato',
            'empresa': 'Empresa',
            'valor': 'Valor',
            'data_inicio': 'Data de Início',
            'data_termino': 'Data de Término',
            'descricao': 'Descrição'
        }

class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ['numero', 'empresa', 'empenho', 'setor', 'data_entrada', 'data_nota', 'data_saida', 'valor', 'observacoes']
        widgets = {
            'data_entrada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_nota': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_saida': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite o número da nota'}),
            'empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite o nome da empresa'}),
            'empenho': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite o número do empenho'}),
            'setor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite o setor'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'numero': 'Número da Nota',
            'empresa': 'Empresa',
            'empenho': 'Empenho',
            'setor': 'Setor',
            'data_entrada': 'Data de Entrada',
            'data_nota': 'Data da Nota',
            'data_saida': 'Data de Saída',
            'valor': 'Valor',
            'observacoes': 'Observações'
        }

class UsuarioForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite o nome'})
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Digite o email'})
    )
    username = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite o nome de usuário'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Digite a senha'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirme a senha'})
    )
    tipo_usuario = forms.ChoiceField(
        choices=Usuario.TIPO_USUARIO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Usuario
        fields = ('first_name', 'email', 'username', 'password1', 'password2', 'tipo_usuario')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        self.fields['username'].help_text = None

class UsuarioUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    tipo_usuario = forms.ChoiceField(
        choices=Usuario.TIPO_USUARIO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Usuario
        fields = ('first_name', 'email', 'username', 'tipo_usuario')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['username'].widget.attrs['readonly'] = True

    def clean_username(self):
        # Se o usuário já existe, retorna o username atual sem validação
        if self.instance and self.instance.pk:
            return self.instance.username
        return self.cleaned_data['username']

class AlterarSenhaForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Senha Atual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha atual'
        })
    )
    new_password1 = forms.CharField(
        label='Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a nova senha'
        })
    )
    new_password2 = forms.CharField(
        label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a nova senha'
        })
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if len(password) < 8:
            raise ValidationError('A senha deve ter pelo menos 8 caracteres.')
        if not any(char.isdigit() for char in password):
            raise ValidationError('A senha deve conter pelo menos um número.')
        if not any(char.isupper() for char in password):
            raise ValidationError('A senha deve conter pelo menos uma letra maiúscula.')
        if not any(char.islower() for char in password):
            raise ValidationError('A senha deve conter pelo menos uma letra minúscula.')
        if not any(not char.isalnum() for char in password):
            raise ValidationError('A senha deve conter pelo menos um caractere especial.')
        return password

class EsqueciSenhaForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite seu email cadastrado'
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            self.user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            raise ValidationError('Não existe usuário cadastrado com este email.')
        return email

class RedefinirSenhaForm(forms.Form):
    new_password1 = forms.CharField(
        label='Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a nova senha'
        })
    )
    new_password2 = forms.CharField(
        label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a nova senha'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2:
            if password1 != password2:
                raise ValidationError('As senhas não conferem.')

            # Validar complexidade da senha
            if len(password1) < 8:
                raise ValidationError('A senha deve ter pelo menos 8 caracteres.')
            if not any(char.isdigit() for char in password1):
                raise ValidationError('A senha deve conter pelo menos um número.')
            if not any(char.isupper() for char in password1):
                raise ValidationError('A senha deve conter pelo menos uma letra maiúscula.')
            if not any(char.islower() for char in password1):
                raise ValidationError('A senha deve conter pelo menos uma letra minúscula.')
            if not any(not char.isalnum() for char in password1):
                raise ValidationError('A senha deve conter pelo menos um caractere especial.')

        return cleaned_data

    def save(self):
        password = self.cleaned_data['new_password1']
        if self.user:
            self.user.set_password(password)
            self.user.save()

