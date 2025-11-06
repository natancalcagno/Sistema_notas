from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Contrato, Nota
from .validators import (
    validate_cpf, validate_cnpj, validate_positive_value,
    validate_contract_number, validate_nota_number
)

User = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Usuario"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'date_joined', 'last_login',
            'password', 'confirm_password'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }
    
    def validate(self, attrs):
        """Validação customizada"""
        if 'password' in attrs and 'confirm_password' in attrs:
            if attrs['password'] != attrs['confirm_password']:
                raise serializers.ValidationError({
                    'confirm_password': 'As senhas não coincidem.'
                })
        return attrs
    
    def create(self, validated_data):
        """Criar novo usuário"""
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        return user
    
    def update(self, instance, validated_data):
        """Atualizar usuário existente"""
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class ContratoSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Contrato"""
    
    # Campos calculados
    dias_restantes = serializers.ReadOnlyField()
    valor_formatado = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    # Campos de relacionamento
    usuario_nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = Contrato
        fields = [
            'id', 'numero', 'empresa', 'cnpj', 'valor', 'valor_formatado',
            'data_inicio', 'data_fim', 'descricao', 'ativo', 'status_display',
            'dias_restantes', 'created_at', 'updated_at',
            'usuario', 'usuario_nome'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_valor_formatado(self, obj):
        """Retorna o valor formatado em reais"""
        return f"R$ {obj.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    def get_status_display(self, obj):
        """Retorna o status do contrato"""
        if not obj.ativo:
            return 'Inativo'
        
        from django.utils import timezone
        if obj.data_fim < timezone.now().date():
            return 'Vencido'
        elif obj.dias_restantes <= 30:
            return 'Próximo ao vencimento'
        else:
            return 'Ativo'
    
    def validate_numero(self, value):
        """Validar número do contrato"""
        validate_contract_number(value)
        return value
    
    def validate_cnpj(self, value):
        """Validar CNPJ"""
        validate_cnpj(value)
        return value
    
    def validate_valor(self, value):
        """Validar valor"""
        validate_positive_value(value)
        return value
    
    def validate(self, attrs):
        """Validação customizada"""
        if 'data_inicio' in attrs and 'data_fim' in attrs:
            if attrs['data_fim'] <= attrs['data_inicio']:
                raise serializers.ValidationError({
                    'data_fim': 'A data de fim deve ser posterior à data de início.'
                })
        return attrs


class NotaSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Nota"""
    
    # Campos de relacionamento
    contrato_numero = serializers.CharField(source='contrato.numero', read_only=True)
    contrato_empresa = serializers.CharField(source='contrato.empresa', read_only=True)
    usuario_nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    # Campos calculados
    valor_formatado = serializers.SerializerMethodField()
    dias_processamento = serializers.SerializerMethodField()
    
    class Meta:
        model = Nota
        fields = [
            'id', 'numero', 'empresa', 'valor', 'valor_formatado',
            'data_entrada', 'data_saida', 'dias_processamento',
            'empenho', 'observacoes', 'created_at', 'updated_at',
            'contrato', 'contrato_numero', 'contrato_empresa',
            'usuario', 'usuario_nome'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_valor_formatado(self, obj):
        """Retorna o valor formatado em reais"""
        return f"R$ {obj.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    def get_dias_processamento(self, obj):
        """Calcula os dias de processamento"""
        if obj.data_saida:
            return (obj.data_saida - obj.data_entrada).days
        return None
    
    def validate_numero(self, value):
        """Validar número da nota"""
        validate_nota_number(value)
        return value
    
    def validate_valor(self, value):
        """Validar valor"""
        validate_positive_value(value)
        return value
    
    def validate(self, attrs):
        """Validação customizada"""
        # Validar datas
        if 'data_entrada' in attrs and 'data_saida' in attrs:
            if attrs['data_saida'] and attrs['data_saida'] < attrs['data_entrada']:
                raise serializers.ValidationError({
                    'data_saida': 'A data de saída deve ser posterior à data de entrada.'
                })
        
        # Validar empresa do contrato
        if 'contrato' in attrs and 'empresa' in attrs:
            if attrs['empresa'] != attrs['contrato'].empresa:
                raise serializers.ValidationError({
                    'empresa': 'A empresa deve ser a mesma do contrato selecionado.'
                })
        
        return attrs


class ContratoResumoSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem de contratos"""
    
    valor_formatado = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    notas_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contrato
        fields = [
            'id', 'numero', 'empresa', 'valor_formatado',
            'data_inicio', 'data_fim', 'status_display',
            'notas_count', 'ativo'
        ]
    
    def get_valor_formatado(self, obj):
        return f"R$ {obj.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    def get_status_display(self, obj):
        if not obj.ativo:
            return 'Inativo'
        
        from django.utils import timezone
        if obj.data_fim < timezone.now().date():
            return 'Vencido'
        elif obj.dias_restantes <= 30:
            return 'Próximo ao vencimento'
        else:
            return 'Ativo'
    
    def get_notas_count(self, obj):
        """Retorna o número de notas do contrato"""
        return obj.notas.count()


class NotaResumoSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem de notas"""
    
    contrato_numero = serializers.CharField(source='contrato.numero', read_only=True)
    valor_formatado = serializers.SerializerMethodField()
    
    class Meta:
        model = Nota
        fields = [
            'id', 'numero', 'empresa', 'valor_formatado',
            'data_entrada', 'data_saida', 'contrato_numero'
        ]
    
    def get_valor_formatado(self, obj):
        return f"R$ {obj.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer para estatísticas do dashboard"""
    
    total_contratos = serializers.IntegerField()
    contratos_ativos = serializers.IntegerField()
    contratos_vencidos = serializers.IntegerField()
    total_notas = serializers.IntegerField()
    notas_mes_atual = serializers.IntegerField()
    valor_total_contratos = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_total_notas = serializers.DecimalField(max_digits=15, decimal_places=2)
    empresas_ativas = serializers.IntegerField()
    media_processamento_dias = serializers.FloatField(allow_null=True)
    
    # Dados para gráficos
    notas_por_mes = serializers.DictField(child=serializers.IntegerField())
    contratos_por_status = serializers.DictField(child=serializers.IntegerField())
    top_empresas = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )


class RelatorioSerializer(serializers.Serializer):
    """Serializer para parâmetros de relatórios"""
    
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)
    empresa = serializers.CharField(required=False, allow_blank=True)
    contrato_id = serializers.IntegerField(required=False)
    formato = serializers.ChoiceField(
        choices=['json', 'csv', 'excel', 'pdf'],
        default='json'
    )
    incluir_detalhes = serializers.BooleanField(default=True)
    
    def validate(self, attrs):
        """Validação customizada"""
        if 'data_inicio' in attrs and 'data_fim' in attrs:
            if attrs['data_fim'] < attrs['data_inicio']:
                raise serializers.ValidationError({
                    'data_fim': 'A data de fim deve ser posterior à data de início.'
                })
        return attrs