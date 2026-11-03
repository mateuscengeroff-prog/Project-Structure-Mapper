# Project Structure Mapper

Ferramenta local e gratuita para entender a organização de projetos de código.
**Funciona offline, não instala pacotes, não modifica o projeto analisado e não envia nada para a internet.**

## Comece em poucos cliques (Windows)

1. Instale o [Python 3](https://www.python.org/downloads/) (versão 3.8 ou mais nova).
   Na primeira tela do instalador, marque **"Add python.exe to PATH"**.
2. Baixe este repositório como ZIP (botão **Code → Download ZIP**) e extraia a pasta.
3. **Clique duas vezes em `INICIAR_WINDOWS.bat`.**
4. No menu, escolha **1 — Mapear um projeto** (ou só pressione Enter).
5. Cole o caminho da pasta do projeto ou pressione Enter para abrir a janela de seleção.
   Dica: clique com o botão direito na pasta e use **"Copiar como caminho"**; as aspas são aceitas.
6. Escolha o tipo de relatório: **1 — público/resumido** ou **2 — privado/detalhado**.
7. Pressione Enter para salvar em `C:\Users\<seu-usuário>\ProjectStructureReports` (ou digite outra pasta fora do projeto).
8. Confira o resumo e pressione Enter para iniciar.
9. Ao terminar, o assistente oferece abrir a pasta com o relatório e o ZIP.

**Atalho:** você também pode **arrastar a pasta do projeto para cima do `INICIAR_WINDOWS.bat`**. O assistente abre com a pasta já escolhida.

### Linux / macOS

Execute `python3 mapper.py` no terminal para abrir o mesmo assistente (com seletor gráfico, se disponível).

### Uso automatizado (linha de comando)

```bash
python mapper.py /caminho/do/projeto                      # relatório público
python mapper.py /caminho/do/projeto --mode private --output /caminho/dos/relatorios
python mapper.py --assistente /caminho/do/projeto         # assistente com a pasta já escolhida
python mapper.py --help
```

No Windows, `py -3 mapper.py "C:\meu-projeto" --mode private` também funciona.
Códigos de saída: `0` sucesso, `1` erro (mensagem explica o motivo), `2` assistente sem terminal interativo.

## O que a ferramenta entrega?

Cada execução cria uma pasta nova, por exemplo `ProjectStructureReports\mapa-publico-20260101-153000\`, com:

| Arquivo | Público | Privado | Conteúdo |
|---|---|---|---|
| `relatorio.md` | ✓ | ✓ | Resumo legível |
| `estrutura.json` | ✓ | ✓ | Mesmos dados em formato estruturado |
| `arvore.txt` | – | ✓ | Árvore de pastas e arquivos |
| `mapa_do_projeto.zip` | ✓ | ✓ | Os arquivos acima, juntos |

- **Modo público (padrão):** tecnologias prováveis e contagem por tipo de arquivo. **Sem** nome do projeto, de pastas ou de arquivos.
- **Modo privado:** inclui árvore de arquivos e, em ASP.NET Web Forms, páginas, Master Pages, code-behind, controles e referências CSS/JS.

### ASP.NET Web Forms

- Lê diretivas `<%@ Page %>`, `<%@ Master %>`, `<%@ Control %>`, `<%@ Register %>`, `<%@ Reference %>` e `<%@ MasterType %>` em `.aspx`, `.master` e `.ascx`.
- Lê os registros globais `<pages><controls><add tagPrefix tagName src/>` de **cada** `Web.config` (inclusive `web.config` minúsculo e em subpastas, que valem só para a própria subpasta). Nada mais do `Web.config` é lido para o relatório, e ele nunca é exportado.
- Compara caminhos sem diferenciar maiúsculas/minúsculas, como o Windows/IIS (`~/site.master` encontra `Site.master`).
- Aceita arquivos em UTF-8, UTF-16 (padrão antigo do Visual Studio) e Windows-1252.

Status das referências:

- `localizado`: o arquivo existe no projeto.
- `nao_encontrado`: o caminho estático não existe no projeto (pode ser erro ou arquivo gerado no build).
- `contextual`: CSS/JS relativo dentro de `.master`/`.ascx`; depende da URL da página renderizada. **Não é erro.**

### Python e Node.js

Identifica tecnologias pelos arquivos (`.py`, `pyproject.toml`, `requirements.txt`, `package.json`, `.ts`, `.tsx`...) e ignora `.venv`, `venv`, qualquer ambiente virtual com `pyvenv.cfg`, `__pycache__`, `node_modules`, `dist`, `build` e `.next`.

## Proteção de dados

- **Somente leitura:** a ferramenta não cria, altera nem apaga nada no projeto analisado (há teste automatizado comparando o conteúdo antes e depois).
- **Sem rede:** não há telemetria; o código não importa bibliotecas de rede (há teste que bloqueia conexões durante a execução).
- **Relatório fora do projeto:** a ferramenta se recusa a salvar dentro da pasta analisada.
- **Arquivos sensíveis omitidos:** `.env*`, `appsettings*`, `Web.config` e arquivos com `secret`, `senha`, `password`, `token`, `credential` ou `apikey` no nome não entram no inventário. O relatório informa apenas **quantos** foram omitidos.
- **O código-fonte não é copiado.** Arquivos de marcação são lidos localmente só para encontrar relações.
- Links simbólicos não são percorridos; `Web.config` com `DOCTYPE`/entidades é ignorado.
- Pastas `ProjectStructureReports/` e relatórios soltos estão no `.gitignore`.

**Importante:** relatórios privados mostram nomes de arquivos e módulos, que podem ser confidenciais. Não os publique sem autorização. O modo público reduz a exposição, mas revise-o antes de compartilhar.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "Python 3.8 ou mais novo não foi encontrado" | Instale o Python pelo site oficial marcando "Add python.exe to PATH" e abra o `.bat` de novo. |
| O Windows mostra "O Windows protegeu o computador" | Clique em **Mais informações → Executar assim mesmo**. O `.bat` só chama o `mapper.py` desta pasta. |
| A janela de seleção de pasta não aparece | Ela pode abrir atrás de outras janelas; ou cole o caminho da pasta diretamente. |
| "A pasta de saída fica DENTRO do projeto" | Escolha outra pasta, como Documentos. É uma proteção para não alterar o projeto. |
| "Limite de 25000 arquivos atingido" | Escolha uma pasta mais específica (não o disco inteiro). |
| "Nenhum arquivo de código reconhecido" | Confira se escolheu a pasta raiz do projeto. |

## O que o Mapper não faz?

Ele **não** compila, executa, testa a segurança, acessa bancos ou valida o comportamento do sistema. Referências montadas dinamicamente (`<%= ResolveUrl(...) %>`, rotas, imports em tempo de execução) não são detectadas. Um status `contextual` não significa erro.

## Executar os testes

```bash
python -m unittest discover -s tests -v
```

Os testes criam projetos **fictícios** (ASP.NET Web Forms, Python e Node.js) numa pasta temporária. Nenhum projeto real é necessário.

Situação da validação:

- Suíte automatizada executada em Linux com Python 3.8, 3.11, 3.12 e 3.13.
- Assistente interativo testado em terminal real (pseudo-terminal Linux) e por testes automatizados.
- **Ainda não executado em Windows real:** o duplo clique no `INICIAR_WINDOWS.bat`, o arrastar-e-soltar, a janela de seleção de pasta e o "Abrir pasta" no Explorer. Roteiro para validar:
  1. Rodar `py -3 -m unittest discover -s tests -v` no Prompt de Comando.
  2. Clicar duas vezes no `.bat` e mapear um projeto fictício nos dois modos.
  3. Arrastar uma pasta para cima do `.bat`.
  4. Testar uma pasta com espaços e acentos no nome.

## Licença e contribuição

MVP v2. Ideias futuras: visão HTML local, análise de `.csproj`/imports Python/Node e resolução de rotas.

Antes de tornar o repositório público, faça revisão de segurança, execute a suíte de testes e escolha uma licença apropriada.
