/* ==================================================================
   main.js — o JavaScript do sistema
   ==================================================================
   Quase tudo neste projeto e feito no servidor, com Python e Jinja2.
   O JavaScript entra so em tres lugares:

     1. os avisos de carregamento (logo abaixo)
     2. a busca que filtra tabelas sem recarregar a pagina
     3. a conversa com o assistente
   ================================================================== */


/* ==================================================================
   1. AVISOS DE CARREGAMENTO
   ==================================================================
   O problema: quando voce clica num item do menu, o navegador vai
   buscar a pagina nova no servidor. Nesse meio-tempo a tela fica
   parada e parece que o clique nao funcionou.

   A solucao: mostrar tres avisos.

     - uma barra fina correndo no topo
     - uma bolinha girando dentro do que foi clicado
     - um cartao no canto, so se a espera passar de meio segundo

   O DETALHE IMPORTANTE: a barra e o cartao so aparecem depois de um
   atraso. Aqui na sua maquina as paginas abrem em poucos milissegundos;
   sem esse atraso, os avisos apareceriam e sumiriam num piscar, o que
   incomoda mais do que ajuda. Com o atraso, em navegacao rapida nada
   chega a aparecer, e em navegacao lenta o aviso entra na hora certa.
   ================================================================== */

// Quanto esperar antes de mostrar cada aviso (em milissegundos).
const ATRASO_DA_BARRA = 120;   // barra do topo
const ATRASO_DO_CARTAO = 550;  // cartao no canto

let barra = null;
let cartao = null;
let cronometroBarra = null;
let cronometroCartao = null;
let cronometroSeguranca = null;

/** Cria a barra e o cartao na primeira vez que sao necessarios. */
function prepararAvisos() {
  if (!barra) {
    barra = document.createElement('div');
    barra.className = 'barra-carregando';
    document.body.appendChild(barra);
  }
  if (!cartao) {
    cartao = document.createElement('div');
    cartao.className = 'aviso-carregando';
    cartao.innerHTML = '<span class="girando"></span><span>Carregando…</span>';
    document.body.appendChild(cartao);
  }
}

/**
 * Comeca a mostrar que algo esta carregando.
 *
 * @param {HTMLElement} elemento  o botao ou link clicado (opcional)
 */
function iniciarCarregamento(elemento) {
  prepararAvisos();

  // A bolinha no elemento clicado aparece na hora: ela e a resposta
  // imediata ao clique, e nao atrapalha nem se for rapido.
  if (elemento && !elemento.classList.contains('ocupado')) {
    elemento.classList.add('ocupado');
    if (!elemento.querySelector('.girando')) {
      const bolinha = document.createElement('span');
      bolinha.className = 'girando';
      elemento.appendChild(bolinha);
    }
  }

  // A barra e o cartao esperam um pouco antes de aparecer.
  clearTimeout(cronometroBarra);
  clearTimeout(cronometroCartao);

  cronometroBarra = setTimeout(function () {
    barra.classList.remove('completa');
    // Força o navegador a redesenhar antes de animar, senao a barra
    // pularia direto para 90% sem o efeito de corrida.
    void barra.offsetWidth;
    barra.classList.add('ativa');
  }, ATRASO_DA_BARRA);

  cronometroCartao = setTimeout(function () {
    cartao.classList.add('ativo');
  }, ATRASO_DO_CARTAO);

  // Rede de seguranca: se a pagina nao trocar em 20 segundos, algo deu
  // errado. Escondemos os avisos para a tela nao ficar travada para
  // sempre com a bolinha girando.
  clearTimeout(cronometroSeguranca);
  cronometroSeguranca = setTimeout(encerrarCarregamento, 20000);
}

/** Encerra os avisos (usado quando a navegacao nao chega a acontecer). */
function encerrarCarregamento() {
  clearTimeout(cronometroBarra);
  clearTimeout(cronometroCartao);
  clearTimeout(cronometroSeguranca);

  if (cartao) cartao.classList.remove('ativo');

  if (barra && barra.classList.contains('ativa')) {
    barra.classList.remove('ativa');
    barra.classList.add('completa');
    setTimeout(function () { barra.classList.remove('completa'); }, 400);
  }

  document.querySelectorAll('.ocupado').forEach(function (el) {
    el.classList.remove('ocupado');
    const bolinha = el.querySelector('.girando');
    if (bolinha) bolinha.remove();
  });
}

/**
 * Este link deve disparar o aviso de carregamento?
 *
 * Devolve false para os casos em que a pagina NAO vai mudar: downloads,
 * links para outro site, abrir em nova aba, ancoras (#), e os cliques
 * com Ctrl/Shift/Cmd, que o navegador abre em outra aba.
 */
function linkNavegaDeVerdade(link, evento) {
  if (!link || !link.href) return false;
  if (link.hasAttribute('download')) return false;
  if (link.target && link.target !== '_self') return false;
  if (evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey) return false;
  if (evento.button !== 0) return false;  // so o botao esquerdo

  const destino = new URL(link.href, window.location.href);
  if (destino.origin !== window.location.origin) return false;
  if (destino.protocol !== 'http:' && destino.protocol !== 'https:') return false;

  // Ancora na mesma pagina (ex.: href="#topo"): nao recarrega nada.
  if (destino.pathname === window.location.pathname &&
      destino.search === window.location.search &&
      destino.hash) return false;

  return true;
}

// --- Liga tudo assim que a pagina termina de carregar ---
document.addEventListener('DOMContentLoaded', function () {

  // Cliques em links.
  document.addEventListener('click', function (evento) {
    const link = evento.target.closest('a');
    if (linkNavegaDeVerdade(link, evento)) {
      iniciarCarregamento(link);
    }
  });

  // Envio de formularios (login, filtros, botoes de acao).
  document.addEventListener('submit', function (evento) {
    // defaultPrevented = alguem ja tratou este envio por JavaScript
    // (e o caso da conversa do assistente), entao a pagina nao muda.
    if (evento.defaultPrevented) return;

    const formulario = evento.target;
    const botao = formulario.querySelector('button[type="submit"], button:not([type])');
    iniciarCarregamento(botao || null);
  });
});

// Ao voltar pelo botao "voltar" do navegador, a pagina pode vir da
// memoria com os avisos ainda ligados. Este trecho limpa tudo.
window.addEventListener('pageshow', function (evento) {
  if (evento.persisted) encerrarCarregamento();
});

/**
 * Filtra as linhas de uma tabela conforme o que a pessoa digita.
 *
 * @param {HTMLInputElement} campo   o campo de busca
 * @param {string} idDaTabela        o id da <table> a ser filtrada
 *
 * Usado assim no HTML:
 *   <input oninput="filtrarTabela(this, 'tabelaApolices')">
 */
function filtrarTabela(campo, idDaTabela) {
  // toLowerCase deixa tudo minusculo, para a busca nao diferenciar
  // maiusculas de minusculas ("MARCOS" acha "Marcos").
  const procurado = campo.value.toLowerCase().trim();

  const tabela = document.getElementById(idDaTabela);
  if (!tabela) return;

  const linhas = tabela.querySelectorAll('tbody tr');
  let encontradas = 0;

  linhas.forEach(function (linha) {
    // Pula a linha de "nenhum resultado", se ela existir.
    if (linha.dataset.semResultado === 'sim') return;

    const texto = linha.innerText.toLowerCase();
    const combina = texto.includes(procurado);

    // display 'none' esconde a linha; '' devolve ao normal.
    linha.style.display = combina ? '' : 'none';
    if (combina) encontradas++;
  });

  mostrarAvisoSemResultado(tabela, encontradas === 0, procurado);
}

/* ==================================================================
   ASSISTENTE
   ==================================================================
   Envia a pergunta ao servidor e escreve a resposta na conversa,
   sem recarregar a pagina.
   ================================================================== */

/** Chamado quando a pessoa clica em uma pergunta pronta. */
function perguntar(texto) {
  document.getElementById('campoPergunta').value = texto;
  enviarPergunta();
}

/** Chamado ao enviar o formulario da conversa. */
async function enviarPergunta(evento) {
  // preventDefault impede a pagina de recarregar ao enviar o formulario
  if (evento) evento.preventDefault();

  const campo = document.getElementById('campoPergunta');
  const botao = document.getElementById('botaoEnviar');
  const pergunta = campo.value.trim();
  if (!pergunta) return;

  adicionarMensagem(pergunta, 'me');
  campo.value = '';

  // Trava o campo enquanto espera, para nao enviar duas perguntas juntas.
  campo.disabled = true;
  if (botao) { botao.disabled = true; botao.innerText = 'Pensando…'; }

  // Bolinhas animadas enquanto o assistente responde.
  const aguardando = adicionarMensagem(
    '<span class="digitando"><span></span><span></span><span></span></span>',
    'bot'
  );

  try {
    // FormData monta o envio no mesmo formato de um formulario comum.
    const dados = new FormData();
    dados.append('pergunta', pergunta);

    const resposta = await fetch('/assistente/perguntar', {
      method: 'POST',
      body: dados,
    });

    const json = await resposta.json();
    aguardando.innerHTML = json.resposta;
  } catch (erro) {
    aguardando.innerHTML =
      'Não consegui falar com o servidor. Ele ainda está rodando?';
  } finally {
    campo.disabled = false;
    if (botao) { botao.disabled = false; botao.innerText = 'Enviar'; }
    campo.focus();
  }

  rolarParaOFim();
}

/** Cria um balao de mensagem e devolve o elemento criado. */
function adicionarMensagem(texto, quem) {
  const area = document.getElementById('mensagens');
  const balao = document.createElement('div');
  balao.className = 'msg ' + quem;
  balao.innerHTML = texto;
  area.appendChild(balao);
  rolarParaOFim();
  return balao;
}

/** Desce a conversa até a última mensagem. */
function rolarParaOFim() {
  const area = document.getElementById('mensagens');
  if (area) area.scrollTop = area.scrollHeight;
}

/**
 * Mostra ou esconde a linha "nenhum resultado encontrado".
 * A linha e criada na hora, na primeira vez que precisa aparecer.
 */
function mostrarAvisoSemResultado(tabela, precisaMostrar, procurado) {
  const corpo = tabela.querySelector('tbody');
  let aviso = corpo.querySelector('tr[data-sem-resultado="sim"]');

  if (precisaMostrar) {
    if (!aviso) {
      const colunas = tabela.querySelectorAll('thead th').length;
      aviso = document.createElement('tr');
      aviso.dataset.semResultado = 'sim';
      aviso.innerHTML = '<td colspan="' + colunas + '" class="vazio"></td>';
      corpo.appendChild(aviso);
    }
    aviso.querySelector('td').innerText =
      'Nenhum resultado para "' + procurado + '".';
    aviso.style.display = '';
  } else if (aviso) {
    aviso.style.display = 'none';
  }
}
