<div align="center">

# Project Structure Mapper

### Entenda a estrutura de projetos de código, sem abrir arquivo por arquivo.

**Mapeador local, gratuito e guiado em português — Python, Node.js e ASP.NET Web Forms.**

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=flat-square)
![Offline](https://img.shields.io/badge/Execu%C3%A7%C3%A3o-Offline-257B57?style=flat-square)
![Sem pacotes](https://img.shields.io/badge/Pacotes%20extras-Zero-555?style=flat-square)
![Somente leitura](https://img.shields.io/badge/Projeto%20analisado-Somente%20leitura-257B57?style=flat-square)

**[Instalar e começar](#comece-aqui-windows-10-e-11) · [Comandos CMD](#uso-pelo-cmd-prompt-de-comando) · [Relatórios](#resultados-gerados) · [Ajuda para iniciantes](docs/GUIA_WINDOWS.md)**

</div>

---

## O que é?

Recebeu um projeto grande e não sabe por onde começar? O **Project Structure Mapper** cria um mapa do repositório para ajudar a identificar tecnologias, pastas, arquivos e relações estáticas.

| Perfil | O que você consegue fazer |
| --- | --- |
| **Iniciante** | Usar um menu passo a passo, sem precisar aprender CMD |
| **Desenvolvedor** | Enxergar a estrutura rapidamente |
| **Legado ASP.NET** | Relacionar páginas, Master Pages, controles e arquivos declarados |
| **Equipe técnica** | Gerar relatórios locais sem copiar o código-fonte |

> **Privacidade primeiro:** a ferramenta lê os arquivos localmente, não altera a pasta analisada e não envia o projeto para a internet. O relatório é salvo em outra pasta. Ainda assim, revise qualquer resultado antes de compartilhar.

## Comece aqui: Windows 10 e 11

**Requisito:** Python 3.8 ou mais recente. **Não precisa instalar Git, Visual Studio ou bibliotecas Python adicionais.**

1. **Instale o Python:** [python.org/downloads](https://www.python.org/downloads/). Marque **Add python.exe to PATH** caso essa opção apareça no instalador.
2. **Baixe os arquivos do projeto:** no GitHub, clique em **Code → Download ZIP** e extraia o ZIP. É preciso extrair antes de executar.
3. **Abra a pasta extraída** e confirme que existem os arquivos **INICIAR_WINDOWS.bat** e **mapper.py**.
4. **Dê dois cliques em INICIAR_WINDOWS.bat**. Uma janela do Prompt de Comando vai abrir.
5. Escolha **1 — Mapear um projeto** (ou pressione Enter).
6. Cole o caminho da pasta que quer analisar, ou pressione Enter para tentar abrir a janela de seleção.
7. Escolha **1 — Público/resumido** ou **2 — Privado/detalhado**.
8. Pressione Enter para usar a pasta de saída padrão ou escolha outra **fora da pasta analisada**.
9. Confira o resumo, confirme e, ao concluir, abra a pasta dos resultados.

**Atalho:** arraste a pasta do projeto **sobre o INICIAR_WINDOWS.bat**. O assistente recebe o caminho automaticamente.

> **Versão em desenvolvimento:** enquanto o [PR #1 da v2](https://github.com/mateuscengeroff-prog/Project-Structure-Mapper/pull/1) estiver em Draft, a branch **main** pode conter apenas o arquivo .gitignore. Nesse caso, antes do **Code → Download ZIP**, selecione **feat/interactive-mapper-v2** no seletor de branches do GitHub. O arquivo BAT ainda **não foi testado num Windows físico**.

<details>
<summary><strong>Como reconhecer a pasta correta depois da extração?</strong></summary>

~~~text
Project-Structure-Mapper/
├── INICIAR_WINDOWS.bat   ← dois cliques
├── mapper.py              ← programa Python
├── README.md              ← este guia
└── tests/
    └── test_mapper.py
~~~

Se só apareceu .gitignore, você baixou a branch main antes da integração da versão 2.

</details>

## Uso pelo CMD (Prompt de Comando)

**CMD** é o terminal clássico do Windows 10 e 11. O aplicativo **não exige que você saiba usá-lo**, mas aqui estão os comandos para executar e entender.

1. No **Explorador de Arquivos**, entre na pasta que contém **mapper.py**.
2. Clique na barra de endereço dessa pasta, digite **cmd** e pressione **Enter**.
3. Na janela que abrir, digite um dos comandos a seguir.

**Verificar se o Python está instalado:**

~~~bat
py -3 --version
~~~

**Abrir o assistente pelo terminal:**

~~~bat
INICIAR_WINDOWS.bat
~~~

Ou, diretamente pelo Python:

~~~bat
py -3 mapper.py
~~~

**Mapear um projeto de exemplo no modo público (sem menu):**

~~~bat
py -3 mapper.py "C:\Projetos\MeuProjeto" --mode public
~~~

**Gerar relatório detalhado em uma pasta separada:**

~~~bat
py -3 mapper.py "C:\Projetos\MeuProjeto" --mode private --output "%USERPROFILE%\Documents\RelatoriosMapper"
~~~

**Mostrar ajuda:**

~~~bat
py -3 mapper.py --help
~~~

Substitua **C:\Projetos\MeuProjeto** pelo caminho real da pasta a analisar. Use **aspas** para caminhos com espaços.

Se **py** não for reconhecido, tente **python --version**. Caso funcione, use **python** no lugar de **py -3**.

**[Tutorial completo: CMD, download, pasta de saída e resolução de erros](docs/GUIA_WINDOWS.md)**

## Resultados gerados

A cada execução, é criada uma **nova pasta de saída**. Os relatórios não ficam dentro do projeto analisado.

| Arquivo | Público | Privado | Conteúdo |
| --- | :---: | :---: | --- |
| **relatorio.md** | ✓ | ✓ | Resumo para leitura |
| **estrutura.json** | ✓ | ✓ | Dados estruturados |
| **arvore.txt** | — | ✓ | Árvore de pastas e arquivos |
| **mapa_do_projeto.zip** | ✓ | ✓ | Pacote dos relatórios, sem código-fonte |

~~~mermaid
flowchart LR
    A["Projeto local<br/>somente leitura"] --> B["Project Structure Mapper"]
    B --> C["Resumo público"]
    B --> D["Relatório privado"]
    C --> E["Pasta de saída<br/>+ ZIP"]
    D --> E
~~~

- **Modo público (padrão):** estatísticas e tecnologias prováveis, sem nomes de projeto, pastas ou arquivos.
- **Modo privado:** inclui a estrutura interna, árvore e referências de arquivos; **somente para uso autorizado**.

### O que reconhece?

- **ASP.NET Web Forms:** páginas .aspx, controles .ascx, Master Pages .master, diretivas Page, Master, Control, Register, Reference e MasterType; registros de controles de Web.config na raiz e subpastas.
- **Python:** arquivos .py e sinais de projeto como pyproject.toml e requirements.txt.
- **Node.js / TypeScript:** arquivos package.json, JavaScript, TypeScript e TSX.
- **Referências estáticas:** os estados **localizado**, **nao_encontrado** e **contextual** (o último não significa necessariamente erro).

## Segurança e limitações

- Usa apenas a **biblioteca padrão do Python**, sem instalar pacotes extras.
- Não modifica, executa, compila ou copia o código do projeto analisado.
- Não envia telemetria nem acessa a rede durante o mapeamento.
- Recusa saída dentro do projeto e não percorre links simbólicos.
- Ignora arquivos e pastas sensíveis ou gerados. Em Web Forms, lê apenas registros estáticos de controles do Web.config, **sem exportar o conteúdo do arquivo**.
- **Não** verifica a qualidade do software, o banco de dados, a segurança real nem referências geradas dinamicamente.

> **Projetos corporativos:** não coloque arquivos internos, relatórios privados, credenciais ou dados de clientes neste repositório. Mesmo um relatório público precisa de revisão antes de ser divulgado.

## Testes e status de validação

O [PR Draft #1](https://github.com/mateuscengeroff-prog/Project-Structure-Mapper/pull/1) registra **34 testes automatizados aprovados em Linux** com Python 3.8, 3.11, 3.12 e 3.13.

Para rodar os testes localmente:

~~~bat
py -3 -m unittest discover -s tests -v
~~~

**Ainda não homologado em Windows real:** duplo clique no BAT, arrastar e soltar, seleção gráfica de pasta e abertura da pasta de resultados. Não confundir testes executados em Linux com validação no Windows.

## Dúvidas e soluções

Consulte **[Guia para iniciantes — Windows 10/11](docs/GUIA_WINDOWS.md#solução-de-problemas)** para Python não reconhecido, aviso do Windows, janela de seleção ausente, caminhos com espaços e relatórios recusados.

## Arquivos do projeto

~~~text
INICIAR_WINDOWS.bat     Inicializador no Windows
mapper.py               Mapeador e assistente interativo
tests/test_mapper.py    Testes automatizados
docs/GUIA_WINDOWS.md    Tutorial de instalação e CMD
README.md               Esta apresentação
~~~

## Licença e contribuições

Este repositório está em desenvolvimento. **Ainda não há licença de código aberto definida**; não presuma autorização de redistribuição ou uso comercial. Antes de torná-lo público, escolha uma licença e revise a segurança dos arquivos e relatórios.

<div align="center">

**Um mapa mais claro do projeto, sem tocar no seu código.**

[Voltar ao início](#project-structure-mapper)

</div>
