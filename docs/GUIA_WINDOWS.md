# Guia para iniciantes — Windows 10 e Windows 11

Este é o tutorial do **Project Structure Mapper** para quem nunca usou um terminal. Você consegue executar a ferramenta **sem digitar comandos**, usando o arquivo **INICIAR_WINDOWS.bat**.

[← Voltar para o README](../README.md)

---

## 1. Instalar o Python

O programa usa **Python 3.8 ou superior**, sem bibliotecas adicionais.

1. Abra [python.org/downloads](https://www.python.org/downloads/).
2. Baixe o instalador do Python 3 para Windows.
3. Siga as etapas de instalação. Se aparecer **Add python.exe to PATH**, marque.
4. Feche terminais que já estavam abertos e abra-os novamente.

**Como testar?** Pressione a tecla Windows, digite **cmd** e abra **Prompt de Comando**. Digite:

~~~bat
py -3 --version
~~~

O terminal deve mostrar uma versão do Python 3.8 ou superior. Se o comando **py** não funcionar, tente:

~~~bat
python --version
~~~

> Python é o interpretador que vai executar o arquivo mapper.py. O arquivo BAT procura uma instalação válida automaticamente.

## 2. Baixar os arquivos certos no GitHub

1. Acesse o [Project Structure Mapper](https://github.com/mateuscengeroff-prog/Project-Structure-Mapper).
2. **Enquanto a versão 2 estiver em PR Draft**, escolha a branch **feat/interactive-mapper-v2** no seletor de branches. A branch main ainda pode conter apenas .gitignore.
3. Clique no botão **Code** e depois em **Download ZIP**.
4. Abra a pasta Downloads e clique em **Extrair tudo** no arquivo baixado.
5. Entre na pasta extraída. Ela precisa ter **mapper.py** e **INICIAR_WINDOWS.bat**.

> Se o repositório estiver privado, o GitHub só permite acesso às contas autorizadas. Não compartilhe seu login.

## 3. Executar com dois cliques (modo mais fácil)

1. Na pasta do Mapper, dê dois cliques em **INICIAR_WINDOWS.bat**.
2. Uma janela preta vai abrir com as opções **1) Mapear um projeto**, **2) Ajuda**, **0) Sair**.
3. Pressione **Enter** para escolher **1**.
4. O programa pergunta **qual pasta analisar**. Cole o caminho (por exemplo: **C:\Projetos\ProjetoExemplo**) ou pressione Enter para tentar abrir uma janela de seleção.
5. Escolha **1 — Público/resumido** ou **2 — Privado/detalhado**.
6. Aceite a pasta padrão de relatórios pressionando Enter, ou escolha outra pasta **fora do projeto**.
7. Confira o resumo, confirme e veja o caminho dos resultados.

**Atalho:** arraste uma pasta do Explorador de Arquivos por cima de **INICIAR_WINDOWS.bat**. O assistente abre com o caminho preenchido.

### Público ou privado?

| Escolha | Quando usar | Atenção |
| --- | --- | --- |
| **1 — Público** | Contagem de arquivos e tecnologias prováveis | Ainda revise antes de compartilhar |
| **2 — Privado** | Estrutura detalhada e nomes de arquivos | Não publique relatórios de projetos internos |

A ferramenta **não faz modificações** na pasta analisada e não envia arquivos pela internet.

## 4. Abrir o CMD na pasta do programa

**CMD**, ou **Prompt de Comando**, é o terminal clássico do Windows 10/11. Serve para executar programas digitando comandos.

Para começar na pasta certa sem decorar caminhos:

1. Abra a pasta do Mapper no **Explorador de Arquivos**.
2. Clique na **barra de endereço**, onde aparece o caminho da pasta.
3. Digite **cmd** e pressione **Enter**.
4. O CMD abrirá **nessa mesma pasta**.

### Comandos prontos para copiar

**Verificar Python:**

~~~bat
py -3 --version
~~~

**Executar o assistente pelo BAT:**

~~~bat
INICIAR_WINDOWS.bat
~~~

**Executar o assistente diretamente pelo Python:**

~~~bat
py -3 mapper.py
~~~

**Gerar relatório público sem abrir o menu:**

~~~bat
py -3 mapper.py "C:\Projetos\ProjetoExemplo" --mode public
~~~

**Gerar relatório privado em outra pasta:**

~~~bat
py -3 mapper.py "C:\Projetos\ProjetoExemplo" --mode private --output "%USERPROFILE%\Documents\RelatoriosMapper"
~~~

**Ver ajuda e argumentos:**

~~~bat
py -3 mapper.py --help
~~~

Substitua **C:\Projetos\ProjetoExemplo** pelo caminho real do projeto. As **aspas** protegem os caminhos que contêm espaços.

### O que cada parte do comando significa?

| Texto do comando | Significado |
| --- | --- |
| **py -3** | Chama o Python 3 instalado |
| **mapper.py** | Nome do programa que queremos executar |
| **"C:\Projetos\ProjetoExemplo"** | Pasta de origem para análise |
| **--mode public** | Relatório público/resumido |
| **--mode private** | Relatório interno/detalhado |
| **--output "..."** | Onde salvar os resultados |
| **--help** | Exibe a ajuda |

Se preferir entrar numa pasta manualmente pelo CMD, use:

~~~bat
cd /d "C:\Caminho\Da\Pasta\Onde\Esta\O\Mapper"
~~~

**Esse caminho é apenas ilustrativo.** Substitua pelo caminho mostrado no seu Explorador. O comando **cd** troca de pasta; **/d** também permite trocar a unidade.

## 5. Encontrar o relatório gerado

A pasta padrão fica em:

~~~text
C:\Users\<seu-usuario>\ProjectStructureReports\
    mapa-publico-AAAAmmdd-HHMMSS\
        relatorio.md
        estrutura.json
        mapa_do_projeto.zip
~~~

Os nomes incluem a data e hora da execução; cada execução cria uma pasta nova. No modo privado, a pasta começa com **mapa-privado-** e inclui também **arvore.txt**.

O programa **não aceita salvar o relatório dentro do próprio projeto**. Essa proteção impede que a análise acrescente novos arquivos ao projeto estudado.

## 6. Solução de problemas

| Sintoma | O que verificar |
| --- | --- |
| **Python 3.8 ou mais novo não foi encontrado** | Instale pelo site oficial, feche o CMD e abra novamente |
| **py não é reconhecido** | Tente **python --version**. Se funcionar, substitua **py -3** por **python** nos comandos |
| **O ZIP só contém .gitignore** | Você baixou a branch main antes da integração; selecione **feat/interactive-mapper-v2** |
| **BAT não abre ou o Windows exibe um alerta** | Confirme a origem e leia o conteúdo do BAT com Bloco de Notas. **Não ignore avisos de segurança automaticamente**, nem execute código não autorizado |
| **A janela para escolher pasta não abre** | Cole o caminho da pasta diretamente no terminal |
| **A pasta tem espaços ou acentos** | Use aspas duplas, por exemplo **"C:\Meus Projetos\Projeto Exemplo"** |
| **A pasta de saída fica DENTRO do projeto** | Escolha outra pasta, como Documentos |
| **Limite de 25000 arquivos atingido** | Selecione uma pasta específica, não o disco inteiro |
| **Nenhum arquivo de código reconhecido** | Confira se escolheu a raiz correta de um projeto de código |
| **Janela do CMD permanece aberta no final** | Isso é normal; o BAT espera uma tecla para fechar, para você conseguir ler as mensagens |

**Não execute como administrador:** a ferramenta não precisa de privilégios elevados.

## 7. Proteção de dados

**Nunca compartilhe relatórios privados de um projeto corporativo sem autorização.** Eles podem revelar nomes de módulos e arquivos internos. O modo público reduz essa exposição, mas também deve ser revisado antes da publicação.

O Mapper não executa o projeto, não valida o banco, não descobre todas as rotas dinâmicas e não substitui uma revisão de segurança.

## 8. Executar os testes (opcional)

Se quiser verificar a suíte automatizada, abra o CMD na pasta do Mapper e digite:

~~~bat
py -3 -m unittest discover -s tests -v
~~~

O [PR da versão 2](https://github.com/mateuscengeroff-prog/Project-Structure-Mapper/pull/1) informa **34 testes aprovados em Linux**, usando projetos fictícios. **Ainda falta validar o BAT e o seletor gráfico num Windows real**.

---

[← README](../README.md) · [PR da versão 2](https://github.com/mateuscengeroff-prog/Project-Structure-Mapper/pull/1)
