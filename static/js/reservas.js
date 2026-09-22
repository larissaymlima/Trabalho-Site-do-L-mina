document.addEventListener('DOMContentLoaded', async () => {
  const mensagem = document.querySelector('#reservasMensagem');
  const lista = document.querySelector('#reservasLista');
  const emprestimosMensagem = document.querySelector('#emprestimosMensagem');
  const emprestimosLista = document.querySelector('#emprestimosLista');
  const devolvidosMensagem = document.querySelector('#devolvidosMensagem');
  const devolvidosLista = document.querySelector('#devolvidosLista');
  const avisosLeitor = document.querySelector('#avisosLeitor');

  function escaparHtml(texto) {
    return String(texto ?? '').replace(/[&<>'"]/g, (caractere) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[caractere]));
  }

  function capaDoLivro(capa, idLivro) {
    if (capa) return capa.startsWith('/') ? capa : `/uploads/capas/${capa}`;
    return Number(idLivro) === 2 ? '/static/img/livro2.png' : `/static/img/livro${idLivro}.jpg`;
  }

  function mostrarAviso(texto, tipo = 'erro') {
    avisosLeitor.textContent = texto;
    avisosLeitor.className = `avisos-leitor avisos-leitor--${tipo}`;
    avisosLeitor.hidden = !texto;
  }

  function itemLivro(livro, conteudo) {
    return `<article class="reserva-item"><img class="reserva-item__capa" src="${capaDoLivro(livro.capa, livro.id_livro)}" alt="Capa de ${escaparHtml(livro.titulo)}"><div class="reserva-item__dados"><strong>${escaparHtml(livro.titulo)}</strong><span>${escaparHtml(livro.autor)}</span>${conteudo}</div></article>`;
  }

  async function carregarReservas() {
    const response = await fetch('/reservas', { credentials: 'same-origin' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.mensagem || 'Não foi possível carregar suas reservas.');

    const reservas = data.reservas || [];
    const ativas = reservas.filter((reserva) => ['Pendente', 'Aguardando Retirada'].includes(reserva.status_reserva));
    mensagem.textContent = ativas.length ? '' : 'Você ainda não possui reservas ativas.';
    lista.innerHTML = ativas.map((reserva) => {
      const podeCancelar = ['Pendente', 'Aguardando Retirada'].includes(reserva.status_reserva);
      return itemLivro(reserva, `<small>Status: ${escaparHtml(reserva.status_reserva)}</small>${podeCancelar ? `<button type="button" class="btn btn-sm btn-cancelar-reserva" data-id-reserva="${reserva.id_reserva}">Cancelar</button>` : ''}`);
    }).join('');

    lista.querySelectorAll('.btn-cancelar-reserva').forEach((botao) => {
      botao.addEventListener('click', async () => {
        try {
          const response = await fetch(`/reservas/${botao.dataset.idReserva}`, {
            method: 'DELETE',
            credentials: 'same-origin'
          });
          const data = await response.json();
          if (!response.ok) throw new Error(data.mensagem || 'Não foi possível cancelar a reserva.');
          await carregarReservas();
        } catch (error) {
          mostrarAviso(error.message);
        }
      });
    });
  }

  async function carregarEmprestimos() {
    const response = await fetch('/meus-emprestimos', { credentials: 'same-origin' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.mensagem || 'Não foi possível carregar seus empréstimos.');

    const emprestimos = data.emprestimos || [];
    const ativos = emprestimos.filter((emprestimo) => !emprestimo.data_devolucao_real);
    const devolvidos = emprestimos.filter((emprestimo) => Boolean(emprestimo.data_devolucao_real));
    emprestimosMensagem.textContent = ativos.length ? '' : 'Você não possui empréstimos ativos.';
    emprestimosLista.innerHTML = ativos.map((emprestimo) => {
      const ativo = ['Ativo', 'Atrasado'].includes(emprestimo.status_emprestimo) && !emprestimo.data_devolucao_real;
      const dataDevolucao = emprestimo.data_devolucao_prevista
        ? new Date(emprestimo.data_devolucao_prevista).toLocaleDateString('pt-BR')
        : 'Não informada';
      const acao = ativo
        ? `<button type="button" class="btn btn-sm btn-renovar-emprestimo" data-id-emprestimo="${emprestimo.id_emprestimo}">Prorrogar</button>`
        : '';
      return itemLivro(emprestimo, `<small class="emprestimo-item__data">Devolver até: ${dataDevolucao}</small><small>Status: ${escaparHtml(emprestimo.status_emprestimo)}</small>${acao}`);
    }).join('');
    devolvidosMensagem.textContent = devolvidos.length ? '' : 'Você ainda não devolveu livros.';
    devolvidosLista.innerHTML = devolvidos.map((emprestimo) => {
      const dataDevolucao = new Date(emprestimo.data_devolucao_real).toLocaleDateString('pt-BR');
      return itemLivro(emprestimo, `<small>Devolvido em: ${dataDevolucao}</small>`);
    }).join('');

    emprestimosLista.querySelectorAll('.btn-renovar-emprestimo').forEach((botao) => {
      botao.addEventListener('click', async () => {
        try {
          const response = await fetch(`/emprestimos-renovar/${botao.dataset.idEmprestimo}`, {
            method: 'PUT',
            credentials: 'same-origin'
          });
          const data = await response.json();
          if (!response.ok) throw new Error(data.mensagem || 'Não foi possível prorrogar o empréstimo.');
          await carregarEmprestimos();
        } catch (error) {
          mostrarAviso(error.message);
        }
      });
    });
  }

  try {
    await carregarReservas();
    await carregarEmprestimos();
  } catch (error) {
    mostrarAviso(error.message);
  }
});