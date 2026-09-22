// ==========================================
// INICIALIZAÇÃO E CONTROLE DE ABAS
// ==========================================
const ITENS_POR_PAGINA = 6;
let livrosAtuais = [];
let paginaLivros = 1;
let buscaLivros = '';
let emprestimosAtuais = [];
let paginaEmprestimos = 1;
let podeEditarTudo = false;
let leitoresEmprestimo = [];
const MODO_LIVE_SERVER = /\/(templates|preview)\/index\.html$/i.test(window.location.pathname);

document.addEventListener('DOMContentLoaded', () => {
    if (MODO_LIVE_SERVER) {
        return;
    }
    configurarAcessoGestor();
    carregarEstatisticas();
    carregarEmprestimos();
    carregarFuncionarios();
    carregarCategorias();
    carregarLivros();
    carregarLivrosExcluidos();
    configurarBuscaEmprestimo();
    carregarLeitoresEmprestimo();
});

function configurarBuscaEmprestimo() {
    const leitorNome = document.getElementById('emp-leitor-nome');
    const livroNome = document.getElementById('emp-livro-nome');
    leitorNome?.addEventListener('change', () => {
        const leitor = leitoresEmprestimo.find((item) => `${item.nome} - ${item.email}` === leitorNome.value);
        document.getElementById('emp-leitor-id').value = leitor?.id_leitor || '';
    });
    livroNome?.addEventListener('change', () => {
        const livro = livrosAtuais.find((item) => `${item.titulo} - ${item.autor}` === livroNome.value);
        document.getElementById('emp-livro-id').value = livro?.id_livro || '';
    });
}

async function carregarLeitoresEmprestimo() {
    const resposta = await fetch('/leitores/busca?q=');
    const dados = await resposta.json();
    if (!resposta.ok) return;
    leitoresEmprestimo = dados.leitores || [];
    document.getElementById('emp-leitor-nome').innerHTML = '<option value="">Selecione o leitor</option>' +
        leitoresEmprestimo.map((leitor) => `<option value="${leitor.nome} - ${leitor.email}">${leitor.nome} - ${leitor.email}</option>`).join('');
}

function preencherLivrosEmprestimo() {
    const select = document.getElementById('emp-livro-nome');
    if (!select) return;
    select.innerHTML = '<option value="">Selecione o livro</option>' +
        livrosAtuais.map((livro) => `<option value="${livro.titulo} - ${livro.autor}">${livro.titulo} - ${livro.autor}</option>`).join('');
}

function configurarAcessoGestor() {
    const abaFuncionarios = document.getElementById('aba-funcionarios');
    const areaFuncionarios = document.querySelector('[data-admin-only]');
    const minhasReservasLink = document.getElementById('minhasReservasGestorLink');
    fetch('/me')
        .then(res => {
            if (!res.ok) throw new Error('Sessão expirada.');
            return res.json();
        })
        .then(dados => {
            if (minhasReservasLink) minhasReservasLink.hidden = !dados.usuario;
            if (dados.usuario?.id_cargo !== 1) {
                abaFuncionarios?.remove();
                areaFuncionarios?.remove();
                document.querySelectorAll('[data-readonly-aux]').forEach(campo => {
                    campo.readOnly = true;
                });
            } else {
                podeEditarTudo = true;
                document.querySelectorAll('[data-readonly-aux]').forEach(campo => {
                    campo.readOnly = false;
                });
                document.getElementById('meu-cargo').type = 'number';
                document.getElementById('meu-cargo').value = document.getElementById('meu-cargo').dataset.idCargo;
                document.getElementById('perfil-aviso-permissao')?.classList.add('hidden');
            }
        })
        .catch(() => {
            document.getElementById('perfil-aviso-permissao')?.classList.remove('hidden');
        });
}

function abrirMenuPerfil() {
    document.getElementById('profileDrawer')?.classList.add('profile-drawer--open');
}

function fecharMenuPerfil() {
    document.getElementById('profileDrawer')?.classList.remove('profile-drawer--open');
}

function abrirEdicaoPerfil() {
    const form = document.getElementById('form-meus-dados');
    form.hidden = false;
    form.previousElementSibling.hidden = true;
}

function alternarAlteracaoSenha() {
    const camposSenha = document.getElementById('senha-opcional');
    const botao = document.getElementById('btn-alterar-senha');
    camposSenha.hidden = !camposSenha.hidden;
    botao.textContent = camposSenha.hidden ? 'Alterar senha' : 'Cancelar alteração de senha';
    if (camposSenha.hidden) {
        document.getElementById('senha-atual').value = '';
        document.getElementById('nova-senha').value = '';
    }
}

async function salvarMeusDados(event) {
    event.preventDefault();
    const arquivo = document.getElementById('minha-foto').files[0];
    const corpo = {
        email: document.getElementById('meu-email').value.trim().toLowerCase(),
        telefone: document.getElementById('meu-telefone').value.trim()
    };
    if (!document.getElementById('senha-opcional').hidden) {
        corpo.senha_atual = document.getElementById('senha-atual').value;
        corpo.nova_senha = document.getElementById('nova-senha').value;
    }
    if (podeEditarTudo) {
        corpo.nome = document.getElementById('meu-nome').value.trim();
        corpo.id_cargo = document.getElementById('meu-cargo').value;
        corpo.status_funcionario = document.getElementById('meu-status').value.trim();
    }
    const res = await fetch('/funcionarios/me', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo)
    });
    const dados = await res.json();
    const mensagem = document.getElementById('perfil-mensagem');
    mensagem.textContent = dados.mensagem || 'Erro ao atualizar seus dados.';
    mensagem.className = `profile-drawer__message ${res.ok ? 'success' : 'error'}`;
    if (res.ok) {
        document.querySelector('.profile-drawer__user').textContent = document.getElementById('meu-email').value;
        if (arquivo) {
            const dadosFoto = new FormData();
            dadosFoto.append('foto', arquivo);
            const respostaFoto = await fetch('/funcionarios/avatar', { method: 'POST', body: dadosFoto });
            const resultadoFoto = await respostaFoto.json();
            if (!respostaFoto.ok) {
                mensagem.textContent = resultadoFoto.mensagem || 'Não foi possível atualizar a foto.';
                mensagem.className = 'profile-drawer__message error';
            } else {
                document.querySelector('.user-chip img').src = resultadoFoto.foto_perfil;
                mensagem.textContent = 'Seus dados e sua foto foram atualizados com sucesso.';
            }
        }
    }
}

async function sairDoGestor() {
    if (!confirm('Deseja sair da sua conta?')) return;
    await fetch('/logout', { method: 'POST' });
    window.location.href = '/';
}

function abrirAba(evt, abaId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active'));
    
    document.getElementById(abaId).classList.add('active');
    evt.currentTarget.classList.add('active');
}

function abrirAbaPorId(abaId) {
    const botao = [...document.querySelectorAll('.tab-button')]
        .find(item => item.getAttribute('onclick')?.includes(`'${abaId}'`));
    if (botao) botao.click();
}

// ==========================================
// ESTATÍSTICAS / DASHBOARD
// ==========================================
async function carregarEstatisticas() {
    try {
        const res = await fetch('/relatorios/dashboard');
        const dados = await res.json();
        if (!res.ok) throw new Error(dados.mensagem);
        const dashboard = dados.dashboard;
        document.getElementById('total-leitores').innerText = dashboard.total_leitores_ativos;
        document.getElementById('total-emprestimos').innerText = dashboard.emprestimos_ativos;
        document.getElementById('total-funcionarios').innerText = dashboard.total_funcionarios_ativos;
        document.getElementById('total-livros').innerText = dashboard.total_livros_ativos;
        desenharGraficos(dashboard);
    } catch (err) {
        console.error("Erro ao carregar estatísticas:", err);
    }
}

// ==========================================
// GERENCIAMENTO DE FUNCIONÁRIOS (CRUD)
// ==========================================
async function carregarFuncionarios() {
    try {
        const res = await fetch('/funcionarios');
        const dados = await res.json();
        if (!res.ok) throw new Error(dados.mensagem);
        const funcionarios = dados.funcionarios;
        const tbody = document.getElementById('tabela-funcionarios');
        tbody.innerHTML = '';

        funcionarios.forEach(f => {
            tbody.innerHTML += `
                <tr>
                    <td>${f.id_funcionario}</td>
                    <td>${f.nome}</td>
                    <td>${f.nome_cargo}</td>
                    <td>${f.email}</td>
                    <td>${f.telefone}</td>
                    <td>
                        <button class="btn btn-warning" onclick='editarFuncionario(${JSON.stringify(f)})'>Editar</button>
                        <button class="btn btn-danger" onclick="deletarFuncionario(${f.id_funcionario})">Deletar</button>
                    </td>
                </tr>
            `;
        });
    } catch (err) {
        console.error("Erro ao carregar funcionários:", err);
    }
}

async function salvarFuncionario(event) {
    event.preventDefault();
    const id = document.getElementById('func-id').value;
    const nome = document.getElementById('func-nome').value;
    const cargo = document.getElementById('func-cargo').value;
    const email = document.getElementById('func-email').value;
    const telefone = document.getElementById('func-telefone').value.trim();
    const senha = document.getElementById('func-senha').value;

    const url = id ? `/funcionarios/${id}` : '/funcionarios';
    const method = id ? 'PUT' : 'POST';

    const res = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(id ? { nome, telefone, id_cargo: cargo } : { nome, email, telefone, senha, id_cargo: cargo })
    });

    if (res.ok) {
        alert(id ? 'Funcionário atualizado com sucesso!' : 'Funcionário cadastrado com sucesso!');
        limparFormularioFuncionario();
        carregarFuncionarios();
        carregarEstatisticas();
    } else {
        const erro = await res.json();
        alert(erro.mensagem || 'Erro ao processar a requisição.');
    }
}

function editarFuncionario(f) {
    document.getElementById('func-id').value = f.id_funcionario;
    document.getElementById('func-nome').value = f.nome;
    document.getElementById('func-cargo').value = f.id_cargo || '';
    document.getElementById('func-email').value = f.email;
    document.getElementById('func-telefone').value = f.telefone || '';
    document.getElementById('func-senha').required = false;
    document.getElementById('grupo-senha-func').classList.add('hidden');

    document.getElementById('titulo-form-func').innerText = 'Atualizar Funcionário';
    document.getElementById('btn-salvar-func').innerText = 'Atualizar';
    document.getElementById('btn-cancelar-func').classList.remove('hidden');
}

async function deletarFuncionario(id) {
    if (!confirm("Tem certeza que deseja remover este funcionário?")) return;

    const res = await fetch(`/funcionarios/${id}`, { method: 'DELETE' });
    if (res.ok) {
        alert('Funcionário deletado!');
        carregarFuncionarios();
        carregarEstatisticas();
    } else {
        alert('Erro ao deletar funcionário.');
    }
}

function limparFormularioFuncionario() {
    document.getElementById('form-funcionario').reset();
    document.getElementById('func-id').value = '';
    document.getElementById('titulo-form-func').innerText = 'Cadastrar Funcionário';
    document.getElementById('btn-salvar-func').innerText = 'Cadastrar';
    document.getElementById('btn-cancelar-func').classList.add('hidden');
    document.getElementById('grupo-senha-func').classList.remove('hidden');
    document.getElementById('func-senha').required = true;
}

async function carregarCategorias() {
    try {
        const res = await fetch('/categorias');
        const dados = await res.json();
        if (!res.ok) throw new Error(dados.mensagem);
        document.getElementById('livro-categoria').innerHTML = dados.categorias
            .map(categoria => `<option value="${categoria.id_categoria}">${categoria.nome_categoria}</option>`).join('');
    } catch (err) { console.error('Erro ao carregar categorias:', err); }
}

async function carregarLivros() {
    try {
        const res = await fetch('/livros');
        const dados = await res.json();
        if (!res.ok) throw new Error(dados.mensagem);
        livrosAtuais = dados.livros.sort((a, b) => a.id_livro - b.id_livro);
        preencherLivrosEmprestimo();
        renderizarLivros();
    } catch (err) { console.error('Erro ao carregar livros:', err); }
}

async function carregarLivrosExcluidos() {
    try {
        const res = await fetch('/livros-excluidos');
        const dados = await res.json();
        if (!res.ok) throw new Error(dados.mensagem);
        document.getElementById('tabela-livros-excluidos').innerHTML = (dados.livros || []).map((livro) => `
            <tr><td>${livro.id_livro}</td><td>${livro.titulo}</td><td>${livro.autor}</td>
            <td>${livro.nome_categoria}</td><td><button type="button" class="btn-acao btn-acao-restaurar" onclick="restaurarLivro(${livro.id_livro})">Restaurar</button></td></tr>
        `).join('');
    } catch (err) {
        console.error('Erro ao carregar livros excluídos:', err);
    }
}

async function restaurarLivro(idLivro) {
    const res = await fetch(`/livros/${idLivro}/restaurar`, { method: 'PUT' });
    const dados = await res.json();
    if (!res.ok) return alert(dados.mensagem || 'Não foi possível restaurar o livro.');
    alert(dados.mensagem || 'Livro restaurado com sucesso.');
    carregarLivros();
    carregarLivrosExcluidos();
}

function renderizarLivros() {
    const filtrados = livrosAtuais.filter(livro => {
        const texto = buscaLivros.toLowerCase();
        return !texto || String(livro.id_livro).includes(texto) ||
            livro.titulo.toLowerCase().includes(texto) || livro.autor.toLowerCase().includes(texto);
    });
    const inicio = (paginaLivros - 1) * ITENS_POR_PAGINA;
    const pagina = filtrados.slice(inicio, inicio + ITENS_POR_PAGINA);
    document.getElementById('tabela-livros').innerHTML = pagina.map(livro => `
        <tr><td>${livro.id_livro}</td><td>${livro.titulo}</td><td>${livro.autor}</td>
        <td>${livro.nome_categoria}</td><td>${livro.quant_estoque}</td>
        <td><span class="status ${classeStatus(livro.status_exemplar)}">${livro.status_exemplar}</span></td>
        <td><div class="acoes-livro"><button type="button" class="btn-acao btn-acao-editar" onclick="editarLivro(${livro.id_livro})">Editar</button>
        <button type="button" class="btn-acao btn-acao-excluir" onclick="excluirLivro(${livro.id_livro})">Excluir</button></div></td></tr>
    `).join('');
    renderizarPaginacao('paginacao-livros', filtrados.length, paginaLivros, pagina => {
        paginaLivros = pagina;
        renderizarLivros();
    });
}

function filtrarLivros() {
    buscaLivros = document.getElementById('busca-livros').value.trim();
    paginaLivros = 1;
    renderizarLivros();
}

function abrirCadastroLivro() {
    document.getElementById('form-livro').reset();
    document.getElementById('livro-id').value = '';
    document.getElementById('titulo-cadastro-livro').textContent = 'Cadastrar Livro';
    document.getElementById('btn-salvar-livro').textContent = 'Cadastrar livro';
    document.getElementById('area-acervo').hidden = true;
    document.getElementById('area-cadastro-livro').hidden = false;
}

function editarLivro(idLivro) {
    const livro = livrosAtuais.find((item) => item.id_livro === idLivro);
    if (!livro) return;
    document.getElementById('livro-id').value = livro.id_livro;
    document.getElementById('livro-titulo').value = livro.titulo || '';
    document.getElementById('livro-autor').value = livro.autor || '';
    document.getElementById('livro-ano').value = livro.ano_publicacao || '';
    document.getElementById('livro-estoque').value = livro.quant_estoque || 1;
    document.getElementById('livro-categoria').value = livro.id_categoria || '';
    document.getElementById('livro-estante').value = livro.posicao_estante || '';
    document.getElementById('livro-sinopse').value = livro.sinopse || '';
    document.getElementById('titulo-cadastro-livro').textContent = 'Editar livro';
    document.getElementById('btn-salvar-livro').textContent = 'Salvar alterações';
    document.getElementById('area-acervo').hidden = true;
    document.getElementById('area-cadastro-livro').hidden = false;
}

async function excluirLivro(idLivro) {
    if (!confirm('Deseja excluir este livro? Essa ação não pode ser desfeita.')) return;
    const res = await fetch(`/livros/${idLivro}`, { method: 'DELETE' });
    const dados = await res.json();
    if (!res.ok) return alert(dados.mensagem || 'Não foi possível excluir o livro.');
    alert(dados.mensagem || 'Livro excluído com sucesso.');
    carregarLivros();
    carregarLivrosExcluidos();
    carregarEstatisticas();
}

function voltarAcervo() {
    document.getElementById('area-cadastro-livro').hidden = true;
    document.getElementById('area-acervo').hidden = false;
}

async function salvarLivro(event) {
    event.preventDefault();
    const body = {
        titulo: document.getElementById('livro-titulo').value.trim(),
        autor: document.getElementById('livro-autor').value.trim(),
        ano_publicacao: document.getElementById('livro-ano').value || null,
        quant_estoque: document.getElementById('livro-estoque').value,
        id_categoria: document.getElementById('livro-categoria').value,
        posicao_estante: document.getElementById('livro-estante').value.trim(),
        sinopse: document.getElementById('livro-sinopse').value.trim()
    };
    const idLivro = document.getElementById('livro-id').value;
    const res = await fetch(idLivro ? `/livros/${idLivro}` : '/livros', { method: idLivro ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const dados = await res.json();
    if (!res.ok) return alert(dados.mensagem || 'Erro ao cadastrar livro.');
    alert(dados.mensagem);
    document.getElementById('form-livro').reset();
    document.getElementById('livro-id').value = '';
    document.getElementById('titulo-cadastro-livro').textContent = 'Cadastrar Livro';
    document.getElementById('btn-salvar-livro').textContent = 'Cadastrar livro';
    carregarLivros();
    carregarEstatisticas();
    voltarAcervo();
}

// ==========================================
// EMPRÉSTIMOS E DEVOLUÇÕES
// ==========================================
function mostrarOperacao(operacao) {
    document.getElementById('operacao-escolha').hidden = true;
    document.getElementById('secao-registrar').hidden = operacao !== 'registrar';
    document.getElementById('secao-devolver').hidden = operacao !== 'devolver';
}

function voltarEscolha() {
    document.getElementById('operacao-escolha').hidden = false;
    document.getElementById('secao-registrar').hidden = true;
    document.getElementById('secao-devolver').hidden = true;
}

async function carregarEmprestimos() {
    try {
        const res = await fetch('/emprestimos');
        const dados = await res.json();
        if (!res.ok) throw new Error(dados.mensagem);
        emprestimosAtuais = dados.emprestimos;
        renderizarEmprestimos();
    } catch (err) {
        console.error("Erro ao carregar empréstimos:", err);
    }
}

function filtrarEmprestimos() {
    paginaEmprestimos = 1;
    renderizarEmprestimos();
}

function renderizarEmprestimos() {
    const busca = document.getElementById('busca-emprestimos')?.value.trim().toLowerCase() || '';
    const filtrados = emprestimosAtuais.filter(e =>
        !busca || e.titulo.toLowerCase().includes(busca) || e.nome_leitor.toLowerCase().includes(busca)
    );
    const inicio = (paginaEmprestimos - 1) * ITENS_POR_PAGINA;
    const pagina = filtrados.slice(inicio, inicio + ITENS_POR_PAGINA);
    const tbody = document.getElementById('tabela-emprestimos');
    tbody.innerHTML = '';

    pagina.forEach(e => {
            const statusEmprestimo = e.status_emprestimo === 'Ativo' ? 'A vencer' : e.status_emprestimo;
            const classeStatusAtual = classeStatus(e.status_emprestimo);
            const botaoDevolucao = e.status_emprestimo === 'Ativo' 
                ? `<button class="btn btn-warning" onclick="devolverLivro(${e.id_emprestimo})">Devolver</button>`
                : 'Concluído';

            tbody.innerHTML += `
                <tr>
                    <td>${e.id_emprestimo}</td>
                    <td>${e.nome_leitor}</td>
                    <td>${e.titulo}</td>
                    <td>${new Date(e.data_emprestimo).toLocaleDateString()}</td>
                    <td><span class="status ${classeStatusAtual}">${statusEmprestimo}</span></td>
                    <td>${botaoDevolucao}</td>
                </tr>
            `;
    });
    renderizarPaginacao('paginacao-emprestimos', filtrados.length, paginaEmprestimos, paginaSelecionada => {
        paginaEmprestimos = paginaSelecionada;
        renderizarEmprestimos();
    });
}

function classeStatus(status) {
    const statusNormalizado = String(status || '').toLowerCase();
    if (statusNormalizado.includes('atras') || statusNormalizado.includes('indispon')) return 'status-vermelho';
    if (statusNormalizado.includes('ativo') || statusNormalizado.includes('vencer') || statusNormalizado.includes('dispon')) return 'status-verde';
    return 'status-neutro';
}

function renderizarPaginacao(elementoId, total, paginaAtual, aoMudarPagina) {
    const totalPaginas = Math.ceil(total / ITENS_POR_PAGINA);
    const elemento = document.getElementById(elementoId);
    if (totalPaginas <= 1) {
        elemento.innerHTML = '';
        return;
    }
    elemento.innerHTML = Array.from({ length: totalPaginas }, (_, indice) => {
        const pagina = indice + 1;
        return `<button type="button" class="pagina-btn ${pagina === paginaAtual ? 'active' : ''}" data-pagina="${pagina}">${pagina}</button>`;
    }).join('');
    elemento.querySelectorAll('.pagina-btn').forEach(botao => {
        botao.addEventListener('click', () => aoMudarPagina(Number(botao.dataset.pagina)));
    });
}

async function salvarEmprestimo(event) {
    event.preventDefault();
    const leitorTexto = document.getElementById('emp-leitor-nome').value;
    const livroTexto = document.getElementById('emp-livro-nome').value;
    const leitorSelecionado = leitoresEmprestimo.find((item) => `${item.nome} - ${item.email}` === leitorTexto);
    const livroSelecionado = livrosAtuais.find((item) => `${item.titulo} - ${item.autor}` === livroTexto);
    const leitor_id = leitorSelecionado?.id_leitor || document.getElementById('emp-leitor-id').value;
    const livro_id = livroSelecionado?.id_livro || document.getElementById('emp-livro-id').value;

    if (!leitor_id || !livro_id) {
        alert('Selecione um leitor e um livro pelos nomes sugeridos.');
        return;
    }

    const res = await fetch('/emprestimos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_leitor: leitor_id, id_livro: livro_id })
    });

    if (res.ok) {
        alert('Empréstimo cadastrado com sucesso!');
        document.getElementById('form-emprestimo').reset();
        carregarEmprestimos();
        carregarEstatisticas();
    } else {
        const erro = await res.json();
        alert(erro.mensagem || 'Erro ao registrar empréstimo.');
    }
}

async function devolverLivro(id) {
    const res = await fetch(`/emprestimos/${id}/devolver`, { method: 'PUT' });
    if (res.ok) {
        alert('Devolução registrada com sucesso!');
        carregarEmprestimos();
        carregarEstatisticas();
    } else {
        const erro = await res.json();
        alert(erro.mensagem || 'Erro ao registrar devolução.');
    }
}

function desenharGraficos(dashboard) {
    const vazio = document.getElementById('grafico-vazio');
    const canvasStatus = document.getElementById('grafico-status');
    const canvasResumo = document.getElementById('grafico-resumo');
    const totalStatus = dashboard.emprestimos_a_vencer + dashboard.emprestimos_atrasados;
    if (!totalStatus && !dashboard.total_livros_ativos) {
        canvasStatus.classList.add('hidden');
        canvasResumo.classList.add('hidden');
        vazio.classList.remove('hidden');
        return;
    }
    vazio.classList.add('hidden');
    canvasStatus.classList.remove('hidden');
    canvasResumo.classList.remove('hidden');
    if (window.graficoStatus) window.graficoStatus.destroy();
    window.graficoStatus = new Chart(canvasStatus, {
        type: 'bar',
        data: {
            labels: ['A vencer', 'Atrasados'],
            datasets: [{
                label: 'Livros',
                data: [dashboard.emprestimos_a_vencer, dashboard.emprestimos_atrasados],
                backgroundColor: ['#8FA7C2', '#6f5e5c'],
                borderRadius: 8,
                borderSkipped: false,
                barPercentage: 0.55,
                categoryPercentage: 0.7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: 'rgba(111, 94, 92, 0.12)' } }
            }
        }
    });
    if (window.graficoResumo) window.graficoResumo.destroy();
    window.graficoResumo = new Chart(canvasResumo, {
        type: 'doughnut',
        data: {
            labels: ['Livros no acervo', 'Empréstimos'],
            datasets: [{ data: [dashboard.total_livros_ativos, dashboard.emprestimos_ativos], backgroundColor: ['#8FA7C2', '#6f5e5c'] }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
    });
}