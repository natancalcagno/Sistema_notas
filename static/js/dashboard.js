// Dashboard JavaScript com AJAX e funcionalidades interativas

class DashboardManager {
    constructor() {
        this.currentPage = 1;
        this.currentFilters = {};
        this.isLoading = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
        this.setupAutoRefresh();
    }

    bindEvents() {
        // Filtros
        $('#filter-form').on('submit', (e) => {
            e.preventDefault();
            this.applyFilters();
        });

        $('#clear-filters').on('click', () => {
            this.clearFilters();
        });

        // Refresh manual
        $('#refresh-data').on('click', () => {
            this.refreshData();
        });

        // Select all checkboxes
        $(document).on('change', '#select-all', (e) => {
            $('.nota-checkbox').prop('checked', e.target.checked);
            this.updateProtocolButton();
        });

        // Individual checkboxes
        $(document).on('change', '.nota-checkbox', () => {
            this.updateProtocolButton();
            this.updateSelectAll();
        });

        // Paginação via AJAX
        $(document).on('click', '.page-link[data-page]', (e) => {
            e.preventDefault();
            const page = $(e.target).data('page');
            this.loadPage(page);
        });

        // Auto-filtro em tempo real (com debounce)
        let filterTimeout;
        $('#empenho').on('input', () => {
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(() => {
                this.applyFilters();
            }, 500);
        });

        // Formulário de protocolo
        $('#notas-form').on('submit', (e) => {
            const selectedNotes = $('.nota-checkbox:checked').length;
            if (selectedNotes === 0) {
                e.preventDefault();
                this.showAlert('Selecione pelo menos uma nota para gerar o protocolo.', 'warning');
            }
        });
    }

    loadInitialData() {
        this.loadNotasData(1, {});
    }

    applyFilters() {
        if (this.isLoading) return;

        const filters = {
            empresa: $('#empresa').val(),
            empenho: $('#empenho').val(),
            data_inicio: $('#data_inicio').val(),
            data_fim: $('#data_fim').val()
        };

        // Remove filtros vazios
        Object.keys(filters).forEach(key => {
            if (!filters[key]) delete filters[key];
        });

        this.currentFilters = filters;
        this.loadNotasData(1, filters);
    }

    clearFilters() {
        $('#filter-form')[0].reset();
        this.currentFilters = {};
        this.loadNotasData(1, {});
    }

    loadPage(page) {
        if (this.isLoading) return;
        this.currentPage = page;
        this.loadNotasData(page, this.currentFilters);
    }

    refreshData() {
        this.loadNotasData(this.currentPage, this.currentFilters);
        this.refreshStats();
    }

    loadNotasData(page = 1, filters = {}) {
        if (this.isLoading) return;

        this.showLoading(true);
        this.isLoading = true;

        const params = {
            page: page,
            ajax: 1,
            ...filters
        };

        $.ajax({
            url: window.location.pathname,
            method: 'GET',
            data: params,
            dataType: 'json',
            success: (response) => {
                if (response.success) {
                    this.updateNotasList(response.html);
                    this.updatePagination(response.pagination);
                    this.updateResultsInfo(response.count, response.total);
                } else {
                    this.showAlert('Erro ao carregar dados: ' + (response.error || 'Erro desconhecido'), 'danger');
                }
            },
            error: (xhr, status, error) => {
                console.error('Erro AJAX:', error);
                this.showAlert('Erro de conexão. Tente novamente.', 'danger');
            },
            complete: () => {
                this.showLoading(false);
                this.isLoading = false;
            }
        });
    }

    refreshStats() {
        $.ajax({
            url: '/api/dashboard-stats/',
            method: 'GET',
            dataType: 'json',
            success: (response) => {
                if (response.success) {
                    this.updateStatsCards(response.stats);
                }
            },
            error: (xhr, status, error) => {
                console.error('Erro ao atualizar estatísticas:', error);
            }
        });
    }

    updateNotasList(html) {
        $('#notas-list').html(html);
        this.updateProtocolButton();
    }

    updatePagination(paginationHtml) {
        $('#pagination-container').html(paginationHtml);
    }

    updateResultsInfo(count, total) {
        const info = `Mostrando ${count} de ${total} notas`;
        $('#results-info').text(info);
    }

    updateStatsCards(stats) {
        $('#stats-cards .card:nth-child(1) h3').text(stats.total_notas || 0);
        $('#stats-cards .card:nth-child(2) h3').text(`R$ ${(stats.valor_total || 0).toFixed(2)}`);
        $('#stats-cards .card:nth-child(3) h3').text(stats.notas_pendentes || 0);
        $('#stats-cards .card:nth-child(4) h3').text(stats.notas_processadas || 0);
    }

    updateProtocolButton() {
        const selectedCount = $('.nota-checkbox:checked').length;
        const button = $('#gerar-protocolo');
        
        if (selectedCount > 0) {
            button.prop('disabled', false)
                  .html(`<i class="fas fa-file-pdf"></i> Gerar Protocolo (${selectedCount})`);
        } else {
            button.prop('disabled', true)
                  .html('<i class="fas fa-file-pdf"></i> Gerar Protocolo');
        }
    }

    updateSelectAll() {
        const totalCheckboxes = $('.nota-checkbox').length;
        const checkedCheckboxes = $('.nota-checkbox:checked').length;
        
        $('#select-all').prop({
            checked: totalCheckboxes > 0 && checkedCheckboxes === totalCheckboxes,
            indeterminate: checkedCheckboxes > 0 && checkedCheckboxes < totalCheckboxes
        });
    }

    showLoading(show) {
        if (show) {
            $('#loading-overlay').show();
        } else {
            $('#loading-overlay').hide();
        }
    }

    showAlert(message, type = 'info') {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Remove alertas existentes
        $('.alert').remove();
        
        // Adiciona novo alerta
        $('#notas-content').prepend(alertHtml);
        
        // Auto-remove após 5 segundos
        setTimeout(() => {
            $('.alert').fadeOut();
        }, 5000);
    }

    setupAutoRefresh() {
        // Auto-refresh a cada 5 minutos
        setInterval(() => {
            if (!this.isLoading) {
                this.refreshStats();
            }
        }, 300000); // 5 minutos
    }
}

// Utilitários adicionais
class UIUtils {
    static formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }

    static formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR');
    }

    static showConfirmDialog(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }

    static copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copiado para a área de transferência!');
        });
    }

    static showToast(message, type = 'success') {
        // Implementar toast notifications
        const toast = $(`
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `);
        
        $('.toast-container').append(toast);
        new bootstrap.Toast(toast[0]).show();
    }
}

// Inicialização quando o documento estiver pronto
$(document).ready(() => {
    // Verificar se estamos na página do dashboard
    if ($('#notas-content').length > 0) {
        window.dashboardManager = new DashboardManager();
    }

    // Adicionar container para toasts se não existir
    if ($('.toast-container').length === 0) {
        $('body').append('<div class="toast-container position-fixed top-0 end-0 p-3"></div>');
    }

    // Melhorar UX com loading states em botões
    $('form').on('submit', function() {
        const submitBtn = $(this).find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        submitBtn.prop('disabled', true)
                 .html('<i class="fas fa-spinner fa-spin"></i> Processando...');
        
        // Restaurar botão após 3 segundos (fallback)
        setTimeout(() => {
            submitBtn.prop('disabled', false).html(originalText);
        }, 3000);
    });

    // Adicionar tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();

    // Melhorar acessibilidade
    $('input, select, textarea').on('focus', function() {
        $(this).closest('.form-group, .mb-3').addClass('focused');
    }).on('blur', function() {
        $(this).closest('.form-group, .mb-3').removeClass('focused');
    });
});

// Exportar para uso global
window.UIUtils = UIUtils;