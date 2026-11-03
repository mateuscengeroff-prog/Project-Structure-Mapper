# Project Structure Mapper

Ferramenta local e gratuita para entender a organização de projetos de código. **Funciona offline, não instala pacotes, não modifica o projeto analisado e não envia arquivos para servidores.**

## Comece em poucos cliques

### Windows (recomendado)

1. Instale o [Python 3](https://www.python.org/downloads/) se ainda não estiver instalado.
2. Baixe este repositório como ZIP e extraia a pasta (ou clone-o).
3. **Clique duas vezes em `INICIAR_WINDOWS.bat`.**
4. No menu que aparecer, escolha **1 — Mapear um projeto**.
5. Cole o caminho da pasta do projeto ou pressione Enter para abrir o seletor de pastas.
6. Escolha entre relatório **público/resumido** e **privado/detalhado**.
7. Pressione Enter para usar a pasta de saída sugerida e confirme a análise.
8. Ao terminar, o assistente oferece abrir a pasta que contém o relatório e o ZIP.

### Linux / macOS

Execute `python3 mapper.py` no terminal para abrir o mesmo assistente interativo (com seletor gráfico se disponível).

### Uso automatizado

```bash
python mapper.py /caminho/do/projeto --mode public
python mapper.py /caminho/do/projeto --mode private --output /caminho/dos/relatorios
python mapper.py --help
```

No Windows, `py -3 mapper.py "C:\\meu-projeto" --mode private` também funciona.

## O que a ferramenta entrega?

- Tecnologias prováveis, identificadas pelos arquivos.
- Inventário por extensão.
- **Modo público (padrão):** resumo sem nomes de projetos, arquivos ou pastas.
- **Modo privado:** árvore de arquivos, páginas, Master Pages, code-behind e referências estáticas.
- Interpretação de controles `<%@ Register %>` e dos registros globais de controles no `Web.config`, sem exportar o conteúdo dele.
- Classificação de caminhos estáticos e caminhos de CSS/JS dependentes da página renderizada.
- Arquivos `relatorio.md`, `estrutura.json` e, no modo privado, `arvore.txt`. Um ZIP reúne esses relatórios.

**O código-fonte, senhas, configurações e dados do projeto não são copiados para o ZIP.** A ferramenta pode ler trechos locais de arquivos de marcação para entender as relações, mas não os exporta.

## Proteção de dados

- Não há telemetria nem conexão com a internet.
- `Web.config` é consultado somente para obter registros de controles; não é exportado.
- Pastas conhecidas de dependências, build e dados são ignoradas.
- Links simbólicos não são percorridos.
- O relatório é salvo **fora** do projeto analisado.
- Relatórios são excluídos do Git por `.gitignore`.

**Importante:** relatórios privados mostram nomes de arquivos e módulos, que podem ser confidenciais. Não os publique sem autorização. Até relatórios públicos precisam ser revisados antes de compartilhar. O modo público reduz exposição de identificadores, mas não garante anonimato absoluto.

## O que o Mapper não faz?

Ele **não** compila, executa, testa a segurança, acessa o banco ou valida o comportamento do sistema. Referências estáticas podem ser ambíguas; um status `contextual` **não significa erro**. Sistemas com roteamento dinâmico ou importações não suportadas precisam de análise complementar.

## Executar os testes

```bash
python -m unittest discover -s tests -v
```

Os testes usam projetos fictícios montados numa pasta temporária. Nenhum projeto corporativo ou arquivo real é necessário.

## Licença e contribuição

Este é o MVP v2. Melhorias futuras: análise adicional de projetos .NET, Python, Node.js, uma visão HTML interativa local e melhor resolução de caminhos de recursos renderizados.

Antes de tornar o repositório público, faça revisão de segurança, execute a suíte de testes e escolha uma licença apropriada.
