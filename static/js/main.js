/* ==================================================================
   main.js — o pouquinho de JavaScript do sistema
   ==================================================================
   Quase tudo neste projeto e feito no servidor, com Python e Jinja2.
   O JavaScript entra so onde algo precisa acontecer SEM recarregar a
   pagina — por enquanto, apenas a busca da tabela.
   ================================================================== */

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
  const pergunta = campo.value.trim();
  if (!pergunta) return;

  adicionarMensagem(pergunta, 'me');
  campo.value = '';

  // Mensagem provisoria enquanto o servidor responde.
  const aguardando = adicionarMensagem('Consultando o banco…', 'bot');

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
