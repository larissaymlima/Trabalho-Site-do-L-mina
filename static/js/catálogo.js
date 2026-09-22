document.addEventListener('DOMContentLoaded', () => {
  if (document.body.dataset.pagina !== 'catalogo') return;
  let livros = [];
  const searchInput = document.querySelector('#buscaInput');
  const categorySelect = document.querySelector('#categoriaSelect');
  const availabilitySelect = document.querySelector('#disponibilidadeSelect');
  const tableBody = document.querySelector('#acervoBody');
  const paginationInfo = document.querySelector('#paginationInfo');
  const paginationControls = document.querySelector('#paginationControls');
  const reservasLink = document.querySelector('#minhasReservasLink');
  const detalhes = document.querySelector('#livroDetalhes');
  const fecharDetalhes = document.querySelector('#fecharDetalhesLivro');
  const reservarDetalhes = document.querySelector('#reservarDetalhesLivro');
  const reservaMensagem = document.querySelector('#reservaMensagem');
  const escreverAvaliacao = document.querySelector('#escreverAvaliacao');
  const avaliacaoForm = document.querySelector('#avaliacaoForm');
  const enviarAvaliacao = document.querySelector('#enviarAvaliacao');
  const estrelasNota = [...document.querySelectorAll('.estrela-nota')];
  const avaliacoesMensagem = document.querySelector('#avaliacoesMensagem');
  const avaliacoesLista = document.querySelector('#avaliacoesLista');
  const pageSize = 10;
  let currentPage = 1;
  let livroDetalhado = null;
  let leitorLogado = false;
  let notaSelecionada = 0;

  function mostrarMensagemReserva(texto, tipo = 'sucesso') {
    reservaMensagem.textContent = texto;
    reservaMensagem.className = `avisos-leitor avisos-leitor--${tipo}`;
    reservaMensagem.hidden = false;
  }

  function escaparHtml(valor) {
    return String(valor ?? '').replace(/[&<>'"]/g, (caractere) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[caractere]));
  }

  function normalizarCapa(capa) {
    if (!capa) return '/static/img/livros.jpg';
    return capa.startsWith('/') ? capa : `/uploads/capas/${capa}`;
  }

  function capaDoLivro(livro) {
    if (livro.capa) return normalizarCapa(livro.capa);
    return Number(livro.id_livro) === 2
      ? '/static/img/livro2.png'
      : `/static/img/livro${livro.id_livro}.jpg`;
  }

  function fecharTelaDetalhes() {
    detalhes.hidden = true;
    document.body.classList.remove('detalhes-abertos');
  }

  function abrirTelaDetalhes(livro) {
    livroDetalhado = livro;
    const capa = document.querySelector('#livroDetalhesCapa');
    capa.src = capaDoLivro(livro);
    document.querySelector('#livroDetalhesCapa').alt = `Capa de ${livro.titulo}`;
    capa.onerror = () => {
      capa.onerror = null;
      capa.src = '/static/img/livros.jpg';
    };
    document.querySelector('#livroDetalhesCategoria').textContent = livro.nome_categoria || 'Livro';
    document.querySelector('#livroDetalhesTitulo').textContent = livro.titulo;
    document.querySelector('#livroDetalhesAutor').textContent = `por ${livro.autor}`;
    document.querySelector('#livroDetalhesSinopse').textContent = livro.sinopse || 'Sinopse não informada.';
    document.querySelector('#livroDetalhesAvaliacao').textContent = livro.total_avaliacoes
      ? `Avaliação: ${livro.media_avaliacoes}/5 (${livro.total_avaliacoes} avaliações)`
      : 'Ainda não há avaliações para este livro.';
    const ocupados = Number(livro.exemplares_emprestados || 0) + Number(livro.exemplares_reservados || 0);
    const disponivel = Number(livro.quant_estoque) > ocupados;
    document.querySelector('#livroDetalhesEstoque').textContent = disponivel
      ? `${Number(livro.quant_estoque) - ocupados} exemplar(es) disponível(is)`
      : livro.proxima_devolucao
        ? `Sem exemplares disponíveis. Previsão de devolução: ${String(livro.proxima_devolucao).slice(0, 10)}`
        : 'Sem exemplares disponíveis no momento';
    reservarDetalhes.hidden = !disponivel;
    reservarDetalhes.disabled = false;
    escreverAvaliacao.hidden = !leitorLogado;
    avaliacaoForm.hidden = true;
    reservaMensagem.hidden = true;
    notaSelecionada = 0;
    atualizarEstrelas();
    carregarAvaliacoes(livro.id_livro);
    detalhes.hidden = false;
    document.body.classList.add('detalhes-abertos');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function atualizarEstrelas() {
    estrelasNota.forEach((estrela) => {
      const ativa = Number(estrela.dataset.nota) <= notaSelecionada;
      estrela.classList.toggle('estrela-nota--ativa', ativa);
      estrela.setAttribute('aria-checked', String(Number(estrela.dataset.nota) === notaSelecionada));
    });
  }

  async function carregarAvaliacoes(idLivro) {
    avaliacoesMensagem.textContent = 'Carregando avaliações...';
    avaliacoesLista.innerHTML = '';
    try {
      const response = await fetch(`/livros-avaliacoes/${idLivro}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.mensagem || 'Não foi possível carregar as avaliações.');
      const avaliacoes = data.avaliacoes || [];
      avaliacoesMensagem.textContent = avaliacoes.length ? '' : 'Ainda não há avaliações para este livro.';
      avaliacoesLista.innerHTML = avaliacoes.map((avaliacao) => `
        <article class="avaliacao-item">
          <div class="avaliacao-item__topo"><strong>${escaparHtml(avaliacao.nome_leitor)}</strong><span>${'★'.repeat(Number(avaliacao.nota))}${'☆'.repeat(5 - Number(avaliacao.nota))}</span></div>
          <p>${escaparHtml(avaliacao.comentario || 'Sem comentário.')}</p>
          <small>${escaparHtml(avaliacao.data_avaliacao || '')}</small>
        </article>
      `).join('');
    } catch (error) {
      avaliacoesMensagem.textContent = error.message;
    }
  }

  async function carregarDetalhes(idLivro) {
    try {
      const response = await fetch(`/livros/${idLivro}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.mensagem || 'Não foi possível carregar o livro.');
      abrirTelaDetalhes(data.livro);
    } catch (error) {
      alert(error.message);
    }
  }

  function getFilteredCards() {
    const query = searchInput.value.trim().toLowerCase();
    const category = categorySelect.value;
    const availability = availabilitySelect.value;

    return livros.filter((livro) => {
      const ocupados = Number(livro.exemplares_emprestados || 0) + Number(livro.exemplares_reservados || 0);
      const disponivel = Number(livro.quant_estoque) > ocupados;
      const matchesQuery = !query || `${livro.titulo} ${livro.autor}`.toLowerCase().includes(query);
      const matchesCategory = !category || String(livro.id_categoria) === category;
      const matchesAvailability = !availability || (disponivel ? 'disponivel' : 'indisponivel') === availability;
      return matchesQuery && matchesCategory && matchesAvailability;
    });
  }

  function renderTable(filteredCards) {
    const totalPages = Math.max(1, Math.ceil(filteredCards.length / pageSize));
    currentPage = Math.min(currentPage, totalPages);
    const start = (currentPage - 1) * pageSize;
    const pageLivros = filteredCards.slice(start, start + pageSize);

    tableBody.innerHTML = pageLivros.map((livro) => {
      const disponivel = livro.status_exemplar === 'Disponível';
      const status = disponivel ? 'Disponível' : 'Indisponível';
      const statusClass = disponivel ? 'badge--success' : '';
      const capa = livro.capa
        ? (livro.capa.startsWith('/') ? livro.capa : `/uploads/capas/${livro.capa}`)
        : `/static/img/livro${livro.id_livro}.jpg`;
      return `<article class="book-card">
        <div class="book-card__cover">
          <img src="${capa}" alt="Capa de ${livro.titulo}" onerror="this.onerror=null;this.src='/static/img/livros.jpg';">
        </div>
        <div class="book-card__body">
          <h3 class="book-card__title">${livro.titulo}</h3>
          <p class="book-card__author">${livro.autor}</p>
          <div class="book-card__meta">
            <span class="book-card__category">${livro.nome_categoria}</span>
            <span class="badge ${statusClass}">${status}</span>
          </div>
          <button class="btn btn-sm btn-ver-livro" type="button" data-id-livro="${livro.id_livro}">Ver livro</button>
        </div>
      </article>`;
    }).join('');

    tableBody.querySelectorAll('.btn-ver-livro').forEach((button) => {
      button.addEventListener('click', () => carregarDetalhes(button.dataset.idLivro));
    });

    const first = filteredCards.length ? start + 1 : 0;
    const last = Math.min(start + pageSize, filteredCards.length);
    paginationInfo.textContent = `Mostrando ${first} a ${last} de ${filteredCards.length} resultados`;
    paginationControls.innerHTML = '';

    for (let page = 1; page <= totalPages; page += 1) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `btn btn-sm${page === currentPage ? ' active' : ''}`;
      button.textContent = page;
      button.addEventListener('click', () => {
        currentPage = page;
        renderTable(getFilteredCards());
      });
      paginationControls.appendChild(button);
    }
  }

  function applyFilters() {
    currentPage = 1;
    const filteredCards = getFilteredCards();
    renderTable(filteredCards);
  }

  async function configurarAreaDoLeitor() {
    try {
      const response = await fetch('/me', { credentials: 'same-origin' });
      const data = await response.json();
      if (response.ok && data.usuario) {
        leitorLogado = true;
        reservasLink.hidden = false;
      }
    } catch (error) {
      reservasLink.hidden = true;
    }
  }

  searchInput.addEventListener('input', applyFilters);
  categorySelect.addEventListener('change', applyFilters);
  availabilitySelect.addEventListener('change', applyFilters);
  fecharDetalhes.addEventListener('click', fecharTelaDetalhes);
  estrelasNota.forEach((estrela) => {
    estrela.addEventListener('click', () => {
      notaSelecionada = Number(estrela.dataset.nota);
      atualizarEstrelas();
    });
  });
  escreverAvaliacao.addEventListener('click', () => {
    avaliacaoForm.hidden = !avaliacaoForm.hidden;
  });
  enviarAvaliacao.addEventListener('click', async () => {
    if (!livroDetalhado) return;
    try {
      const response = await fetch(`/livros/${livroDetalhado.id_livro}/avaliacoes`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nota: notaSelecionada,
          comentario: document.querySelector('#avaliacaoComentario').value.trim()
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.mensagem || 'Não foi possível publicar sua avaliação.');
      alert(data.mensagem);
      document.querySelector('#avaliacaoComentario').value = '';
      avaliacaoForm.hidden = true;
      await carregarAvaliacoes(livroDetalhado.id_livro);
    } catch (error) {
      alert(error.message);
    }
  });
  reservarDetalhes.addEventListener('click', async () => {
    if (!livroDetalhado) return;
    if (!leitorLogado) {
      document.dispatchEvent(new CustomEvent('solicitar-login-reserva', {
        detail: { idLivro: livroDetalhado.id_livro, titulo: livroDetalhado.titulo }
      }));
      return;
    }
    try {
      const response = await fetch('/reservas', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id_livro: livroDetalhado.id_livro }) });
      const data = await response.json();
      if (response.status === 401) {
        document.dispatchEvent(new CustomEvent('solicitar-login-reserva', {
          detail: { idLivro: livroDetalhado.id_livro, titulo: livroDetalhado.titulo }
        }));
        return;
      }
      if (!response.ok) throw new Error(data.mensagem || 'Não foi possível reservar o livro.');
      mostrarMensagemReserva(`Livro reservado com sucesso! ${data.mensagem || 'Você pode acompanhar a reserva em Minhas Reservas.'}`);
      reservarDetalhes.disabled = true;
    } catch (error) {
      mostrarMensagemReserva(error.message, 'erro');
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !detalhes.hidden) fecharTelaDetalhes();
  });
  async function carregarCatalogo() {
    try {
      const [livrosResponse, categoriasResponse] = await Promise.all([fetch('/livros'), fetch('/categorias')]);
      const livrosData = await livrosResponse.json();
      const categoriasData = await categoriasResponse.json();
      if (!livrosResponse.ok) throw new Error(livrosData.mensagem || 'Não foi possível carregar os livros.');
      livros = livrosData.livros || [];
      categoriasData.categorias.forEach((categoria) => {
        const option = document.createElement('option');
        option.value = categoria.id_categoria;
        option.textContent = categoria.nome_categoria;
        categorySelect.appendChild(option);
      });
      const categoriaInicial = new URLSearchParams(window.location.search).get('id_categoria');
      if (categoriaInicial && [...categorySelect.options].some((option) => option.value === categoriaInicial)) {
        categorySelect.value = categoriaInicial;
      }
      applyFilters();
    } catch (error) {
      tableBody.innerHTML = `<p class="catalog-error">${error.message}</p>`;
    }
  }

  carregarCatalogo();
  configurarAreaDoLeitor();
});
