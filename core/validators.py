from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, date
import re

def validate_cpf(value):
    """
    Valida CPF brasileiro
    """
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', str(value))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        raise ValidationError('CPF deve ter 11 dígitos.')
    
    # Verifica se não são todos iguais
    if cpf == cpf[0] * 11:
        raise ValidationError('CPF inválido.')
    
    # Calcula primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Calcula segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verifica se os dígitos estão corretos
    if int(cpf[9]) != digito1 or int(cpf[10]) != digito2:
        raise ValidationError('CPF inválido.')

def validate_cnpj(value):
    """
    Valida CNPJ brasileiro
    """
    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', str(value))
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        raise ValidationError('CNPJ deve ter 14 dígitos.')
    
    # Verifica se não são todos iguais
    if cnpj == cnpj[0] * 14:
        raise ValidationError('CNPJ inválido.')
    
    # Calcula primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Calcula segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verifica se os dígitos estão corretos
    if int(cnpj[12]) != digito1 or int(cnpj[13]) != digito2:
        raise ValidationError('CNPJ inválido.')

def validate_positive_value(value):
    """
    Valida se o valor é positivo
    """
    if value <= 0:
        raise ValidationError('O valor deve ser maior que zero.')

def validate_future_date(value):
    """
    Valida se a data não é no passado
    """
    if isinstance(value, datetime):
        value = value.date()
    
    if value < timezone.now().date():
        raise ValidationError('A data não pode ser no passado.')

def validate_business_date(value):
    """
    Valida se a data é um dia útil (segunda a sexta)
    """
    if isinstance(value, datetime):
        value = value.date()
    
    # 0 = segunda, 6 = domingo
    if value.weekday() > 4:  # sábado ou domingo
        raise ValidationError('A data deve ser um dia útil (segunda a sexta).')

def validate_contract_number(value):
    """
    Valida formato do número do contrato
    """
    # Formato esperado: XXXX/YYYY ou similar
    pattern = r'^\d{3,6}/\d{4}$'
    if not re.match(pattern, str(value)):
        raise ValidationError('Número do contrato com formato inválido. Use o formato: XXXX/YYYY (exemplo: 1234/2024)')

def validate_nota_number(value):
    """
    Valida formato do número da nota
    """
    # Aceita números simples ou com formatação
    if not str(value).strip():
        raise ValidationError('Número da nota é obrigatório.')
    
    # Remove espaços e verifica se tem pelo menos 1 caractere
    if len(str(value).strip()) < 1:
        raise ValidationError('Número da nota deve ter pelo menos 1 caractere.')

def validate_empenho_format(value):
    """
    Valida formato do empenho
    """
    # Formato esperado: números com possível formatação
    pattern = r'^\d{4,10}$'
    empenho_clean = re.sub(r'[^0-9]', '', str(value))
    
    if not re.match(pattern, empenho_clean):
        raise ValidationError('Empenho deve conter entre 4 e 10 dígitos.')

def validate_empresa_name(value):
    """
    Valida nome da empresa
    """
    if len(str(value).strip()) < 2:
        raise ValidationError('Nome da empresa deve ter pelo menos 2 caracteres.')
    
    # Verifica se não contém apenas números
    if str(value).strip().isdigit():
        raise ValidationError('Nome da empresa não pode conter apenas números.')

def validate_date_range(data_inicio, data_fim):
    """
    Valida se o range de datas é válido
    """
    if data_inicio and data_fim:
        if isinstance(data_inicio, datetime):
            data_inicio = data_inicio.date()
        if isinstance(data_fim, datetime):
            data_fim = data_fim.date()
            
        if data_inicio > data_fim:
            raise ValidationError('Data de início não pode ser posterior à data de fim.')
        
        # Verifica se o range não é muito grande (ex: mais de 5 anos)
        diff = data_fim - data_inicio
        if diff.days > 1825:  # 5 anos
            raise ValidationError('O período não pode ser superior a 5 anos.')

def validate_file_size(value):
    """
    Valida tamanho do arquivo (máximo 5MB)
    """
    if value.size > 5 * 1024 * 1024:  # 5MB
        raise ValidationError('Arquivo muito grande. Tamanho máximo: 5MB.')

def validate_file_extension(value):
    """
    Valida extensões de arquivo permitidas
    """
    allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
    
    import os
    ext = os.path.splitext(value.name)[1].lower()
    
    if ext not in allowed_extensions:
        raise ValidationError(
            f'Extensão não permitida. Permitidas: {", ".join(allowed_extensions)}'
        )

class DateRangeValidator:
    """
    Validador de classe para ranges de data
    """
    
    def __init__(self, start_field, end_field):
        self.start_field = start_field
        self.end_field = end_field
    
    def __call__(self, attrs):
        start_date = attrs.get(self.start_field)
        end_date = attrs.get(self.end_field)
        
        if start_date and end_date:
            validate_date_range(start_date, end_date)
        
        return attrs