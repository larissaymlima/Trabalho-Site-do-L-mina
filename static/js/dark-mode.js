/**
 * Dark Mode + Micro-Animações + Atalhos de Teclado
 */

/**
 * Gerenciador de Dark Mode
 */
class GerenciadorDarkMode {
    constructor() {
        document.cookie = 'tema=; Max-Age=0; path=/';
        this.preferenciaCookie = this.obterPreferencia();
        this.aplicarTema();
        this.configurarEventos();
    }

    obterPreferencia() {
        // Tentar obter do cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [chave, valor] = cookie.trim().split('=');
            if (chave === 'lumina_tema') {
                return valor === 'dark' ? 'dark' : 'light';
            }
        }
        
        return 'light';
    }

    salvarPreferencia(tema) {
        // Salvar em cookie (7 dias)
        const dataExpiracao = new Date();
        dataExpiracao.setTime(dataExpiracao.getTime() + 7 * 24 * 60 * 60 * 1000);
        const expires = `expires=${dataExpiracao.toUTCString()}`;
        document.cookie = `lumina_tema=${tema}; ${expires}; path=/`;
    }

    aplicarTema() {
        const html = document.documentElement;
        const botao = document.getElementById('btn-dark-mode');
        
        if (this.preferenciaCookie === 'dark') {
            html.classList.add('dark-mode');
            if (botao) {
                botao.innerHTML = '☀️';
                botao.setAttribute('aria-label', 'Modo claro');
            }
        } else {
            html.classList.remove('dark-mode');
            if (botao) {
                botao.innerHTML = '🌙';
                botao.setAttribute('aria-label', 'Modo escuro');
            }
        }
    }

    alternarTema() {
        this.preferenciaCookie = this.preferenciaCookie === 'dark' ? 'light' : 'dark';
        this.salvarPreferencia(this.preferenciaCookie);
        this.aplicarTema();
    }

    configurarEventos() {
        const botao = document.getElementById('btn-dark-mode');
        if (botao) {
            botao.addEventListener('click', () => this.alternarTema());
        }

    }
}

/**
 * Micro-Animações para Botões
 */
function inicializarMicroAnimacoes() {
    const style = document.createElement('style');
    style.textContent = `
        .btn {
            position: relative;
            overflow: hidden;
            transform-origin: center;
            transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .btn:active {
            transform: scale(0.98);
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            transform: translate(-50%, -50%);
            pointer-events: none;
        }

        .btn:active::before {
            animation: ripple 0.6s ease-out;
        }

        @keyframes ripple {
            to {
                width: 300px;
                height: 300px;
                opacity: 0;
            }
        }

        /* Pulse suave no hover */
        .btn:hover {
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
        }

        /* Dark mode */
        .dark-mode .btn:hover {
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.1);
        }
    `;
    document.head.appendChild(style);
}

/**
 * Atalhos de Teclado
 */
function inicializarAtalhos() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+K / Cmd+K: Focar em busca
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const campoBusca = document.querySelector('#buscaInput, input[placeholder*="uscador"], input[placeholder*="esquise"]');
            if (campoBusca) {
                campoBusca.focus();
                campoBusca.select();
            }
        }

        // Escape: Fechar modais abertos
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal-livro--aberto');
            if (modal) {
                fecharModalLivro?.();
            }

            const authModal = document.getElementById('modal-auth');
            if (authModal?.style.display === 'flex') {
                closeModal?.();
            }

            const confirmModal = document.getElementById('modal-confirmacao');
            if (confirmModal?.classList.contains('modal-confirmacao--visivel')) {
                confirmModal.classList.remove('modal-confirmacao--visivel');
            }
        }

        // Alt+R: Ir para reservas (se usuário autenticado)
        if ((e.altKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            const linkReservas = document.querySelector('#minhasReservasLink');
            if (linkReservas) {
                linkReservas.click();
            }
        }

        // Alt+G: Ir para gestor (se admin)
        if ((e.altKey || e.metaKey) && e.key === 'g') {
            e.preventDefault();
            window.location.href = '/gestor';
        }

        // Alt+H: Ir para home
        if ((e.altKey || e.metaKey) && e.key === 'h') {
            e.preventDefault();
            window.location.href = '/';
        }
    });
}

/**
 * Animação de entrada suave
 */
function animarEntrada() {
    const elementos = document.querySelectorAll('[data-animar]');
    
    const observador = new IntersectionObserver((entradas) => {
        entradas.forEach(entrada => {
            if (entrada.isIntersecting) {
                entrada.target.classList.add('entrada-animada');
                observador.unobserve(entrada.target);
            }
        });
    }, { threshold: 0.1 });

    elementos.forEach(el => observador.observe(el));
}

/**
 * Inicializar tudo
 */
document.addEventListener('DOMContentLoaded', () => {
    // Dark mode
    new GerenciadorDarkMode();
    
    // Micro-animações
    inicializarMicroAnimacoes();
    
    // Atalhos de teclado
    inicializarAtalhos();
    
    // Animações de entrada
    animarEntrada();
});
