#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project Structure Mapper - inventário local de código, sem dependências externas.

Garantias de projeto:
- Somente leitura: nenhum arquivo do projeto analisado é criado, alterado ou apagado.
- Sem rede: o módulo não importa bibliotecas de rede e não faz conexões.
- Relatórios são gravados sempre FORA da pasta analisada.
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

VERSION = "2.1.0"
MIN_PYTHON = (3, 8)

SKIP_DIRS = {
    ".git", ".vs", ".idea", ".venv", "venv", "__pycache__",
    "node_modules", "bin", "obj", ".next", "dist", "build",
    "coverage", ".pytest_cache", ".mypy_cache", ".tox", "testresults",
    "app_data", "uploads", "storage", "secrets", "backup", "backups", "tmp",
}
EXTENSIONS = {
    ".aspx", ".ascx", ".master", ".asmx", ".ashx", ".cs", ".vb", ".csproj",
    ".vbproj", ".sln", ".slnx", ".css", ".scss", ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".vue", ".html", ".htm", ".razor", ".cshtml", ".py", ".go",
    ".java", ".kt", ".php", ".rb", ".rs", ".sql", ".md", ".sh", ".ps1",
}
MANIFESTS = {
    "package.json", "pyproject.toml", "requirements.txt", "setup.py",
    "dockerfile", "makefile", "tsconfig.json", "angular.json",
    "vite.config.js", "vite.config.ts", "go.mod", "cargo.toml",
}
SENSITIVE_WORDS = (
    "secret", "credential", "password", "senha", "token", "privatekey",
    "apikey", "api_key",
)
WEB_CONFIG = "web.config"
WEBFORMS_EXT = (".aspx", ".ascx", ".master")
MAX_FILES = 25000
MAX_READ = 1024 * 1024

DIRECTIVE_RE = re.compile(
    r"<%@\s*(?:Page|Master|Control|Register|Reference|MasterType|PreviousPageType)\b.*?%>",
    re.I | re.S,
)
DIRECTIVE_NAME_RE = re.compile(r"<%@\s*(\w+)", re.I)
ATTR_RE = re.compile(r"([\w:-]+)\s*=\s*([\"'])(.*?)\2", re.S)
RESOURCE_RE = re.compile(r"<(?:link|script)\b[^>]*>", re.I | re.S)
CONTROL_RE = re.compile(r"<([A-Za-z][\w-]*):([A-Za-z][\w-]*)\b")
COMMENT_RE = re.compile(r"<%--.*?--%>|<!--.*?-->", re.S)
DYNAMIC_RE = re.compile(r"<%|\$\{|\{\{|\}\}")


# ---------------------------------------------------------------------------
# Inventário (somente leitura)
# ---------------------------------------------------------------------------

def classify_name(filename: str) -> str:
    """'ok' (entra no inventário), 'sensivel' (omitido por segurança) ou 'fora' (não é código)."""
    lower = filename.lower()
    if lower.startswith(".env") or lower.startswith("appsettings"):
        return "sensivel"
    if lower in {WEB_CONFIG, "web.debug.config", "web.release.config"}:
        return "sensivel"
    relevant = Path(lower).suffix in EXTENSIONS or lower in MANIFESTS
    if any(word in lower for word in SENSITIVE_WORDS):
        return "sensivel" if relevant else "fora"
    return "ok" if relevant else "fora"


def name_allowed(filename: str) -> bool:
    return classify_name(filename) == "ok"


def inventory(root: Path):
    """Percorre a pasta sem seguir links simbólicos e sem abrir arquivos."""
    files = []
    configs = []
    stats = Counter()
    limit_hit = False
    for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
        filtered = []
        for dirname in dirs:
            candidate = Path(current) / dirname
            if (
                dirname.lower() in SKIP_DIRS
                or candidate.is_symlink()
                or (candidate / "pyvenv.cfg").is_file()  # ambiente virtual Python com outro nome
            ):
                stats["pastas_ignoradas"] += 1
            else:
                filtered.append(dirname)
        dirs[:] = sorted(filtered, key=str.casefold)
        for name in sorted(names, key=str.casefold):
            candidate = Path(current) / name
            if candidate.is_symlink():
                continue
            relative = candidate.relative_to(root).as_posix()
            if name.lower() == WEB_CONFIG:
                configs.append(relative)
            kind = classify_name(name)
            if kind == "sensivel":
                stats["sensiveis"] += 1
                continue
            if kind != "ok":
                continue
            if len(files) >= MAX_FILES:
                limit_hit = True
                break
            files.append(relative)
        if limit_hit:
            break  # Evita varrer um disco inteiro depois de atingir o limite.
    return sorted(files, key=str.casefold), sorted(configs, key=str.casefold), stats, limit_hit


def read_small_text(file: Path):
    try:
        if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_READ:
            return None
        payload = file.read_bytes()
    except OSError:
        return None
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return payload.decode("utf-16")
        except UnicodeDecodeError:
            return None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            pass
    return None


def attributes(tag: str):
    return {key.lower(): value for key, _, value in ATTR_RE.findall(tag)}


def normalize_reference(reference: str, source: str):
    """Retorna caminho relativo à raiz; nunca aponta para fora do projeto."""
    value = reference.strip().replace("\\", "/").split("?", 1)[0].split("#", 1)[0]
    if not value or DYNAMIC_RE.search(value):
        return None
    if re.match(r"(?i)^(https?:|//|data:|javascript:|mailto:|file:|#)", value):
        return None
    if re.match(r"^[a-zA-Z]:", value):
        return None
    if value.startswith("~/"):
        value = value[2:]
    elif value.startswith("/"):
        value = value.lstrip("/")
    else:
        value = posixpath.join(posixpath.dirname(source), value)
    target = posixpath.normpath(value)
    if target in (".", "..") or target.startswith("../"):
        return None
    return target


def global_controls(root: Path, config_paths=None):
    """Lê SOMENTE os registros <controls><add .../> de cada Web.config.

    Retorna {pasta_relativa: {(prefixo, tag): "~/caminho"}}. O conteúdo do
    Web.config nunca é exportado. Aceita "Web.config" em qualquer caixa e
    arquivos em subpastas (que valem para aquela subpasta).
    """
    if config_paths is None:
        config_paths = [
            entry.name for entry in root.iterdir()
            if entry.name.lower() == WEB_CONFIG
        ] if root.is_dir() else []
    scopes = {}
    for config_rel in config_paths:
        config = root / config_rel
        registry = {}
        try:
            if config.is_symlink() or not config.is_file() or config.stat().st_size > MAX_READ:
                continue
            payload = config.read_bytes()
            if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
                continue  # Recusa DTD/entidades (proteção contra XML malicioso).
            tree = ElementTree.fromstring(payload)
        except (OSError, ValueError, ElementTree.ParseError):
            continue
        for parent in tree.iter():
            if not isinstance(parent.tag, str):
                continue
            if parent.tag.rsplit("}", 1)[-1].lower() != "controls":
                continue
            for child in parent:
                if not isinstance(child.tag, str):
                    continue
                if child.tag.rsplit("}", 1)[-1].lower() != "add":
                    continue
                attrs = {key.lower(): val for key, val in child.attrib.items()}
                prefix = attrs.get("tagprefix", "").lower()
                tag = attrs.get("tagname", "").lower()
                target = normalize_reference(attrs.get("src") or "", config_rel)
                if prefix and tag and target:
                    registry[(prefix, tag)] = "~/" + target
        if registry:
            scopes[posixpath.dirname(config_rel)] = registry
    return scopes


def registry_for(source: str, scopes: dict):
    """Combina os Web.config da raiz até a pasta do arquivo (o mais próximo vence)."""
    merged = dict(scopes.get("", {}))
    folder = ""
    for part in posixpath.dirname(source).split("/"):
        if not part:
            continue
        folder = posixpath.join(folder, part) if folder else part
        merged.update(scopes.get(folder, {}))
    return merged


def links_for_file(root: Path, source: str, global_registry: dict, known_files=None):
    text = read_small_text(root / source)
    if not text:
        return []
    text = COMMENT_RE.sub("", text)
    known = known_files or {}
    refs = {}
    local_registry = {}

    def record(kind, raw_reference):
        target = normalize_reference(raw_reference, source)
        if not target:
            return
        contextual = (
            kind in {"css", "javascript"}
            and source.lower().endswith((".ascx", ".master"))
            and not raw_reference.strip().startswith(("~/", "/"))
        )
        found = (root / target).is_file()
        if not found and target.casefold() in known:
            # Windows/IIS não diferenciam maiúsculas: "site.master" == "Site.master".
            target = known[target.casefold()]
            found = True
        status = "contextual" if contextual else ("localizado" if found else "nao_encontrado")
        refs[(kind, target)] = {
            "origem": source, "tipo": kind, "destino": target,
            "status": status,
        }

    for declaration in DIRECTIVE_RE.findall(text):
        attrs = attributes(declaration)
        directive = DIRECTIVE_NAME_RE.match(declaration).group(1).lower()
        if directive == "register":
            prefix = attrs.get("tagprefix", "").lower()
            tag = attrs.get("tagname", "").lower()
            src = attrs.get("src")
            if prefix and tag and src:
                local_registry[(prefix, tag)] = src
                record("registro_controle", src)
            continue
        if directive in {"reference", "mastertype", "previouspagetype"}:
            if attrs.get("virtualpath"):
                record("referencia", attrs["virtualpath"])
            continue
        for key, kind in (
            ("masterpagefile", "masterpage"),
            ("codefile", "codefile"),
            ("codebehind", "codebehind"),
            ("src", "codefile"),
        ):
            if attrs.get(key):
                record(kind, attrs[key])

    for match in RESOURCE_RE.finditer(text):
        tag = match.group(0)
        attrs = attributes(tag)
        if tag.lower().startswith("<link") and attrs.get("href"):
            record("css", attrs["href"])
        elif tag.lower().startswith("<script") and attrs.get("src"):
            record("javascript", attrs["src"])

    for prefix, tag in CONTROL_RE.findall(text):
        key = (prefix.lower(), tag.lower())
        ref = local_registry.get(key) or global_registry.get(key)
        if ref:
            record("uso_controle", ref)

    return list(refs.values())


def detect_tech(files):
    suffix = Counter(Path(file).suffix.lower() or "(sem extensão)" for file in files)
    basenames = {Path(file).name.lower() for file in files}
    tech = []
    if any(suffix[x] for x in WEBFORMS_EXT):
        tech.append("ASP.NET Web Forms")
    if suffix[".cs"] or suffix[".csproj"]:
        tech.append("C# / .NET")
    if suffix[".vb"] or suffix[".vbproj"]:
        tech.append("VB.NET")
    if suffix[".razor"] or suffix[".cshtml"]:
        tech.append("Razor / ASP.NET")
    if suffix[".py"] or basenames & {"pyproject.toml", "requirements.txt"}:
        tech.append("Python")
    if suffix[".js"] or suffix[".jsx"] or suffix[".mjs"] or suffix[".cjs"]:
        tech.append("JavaScript")
    if suffix[".ts"] or suffix[".tsx"]:
        tech.append("TypeScript")
    if "package.json" in basenames:
        tech.append("Node.js (manifesto encontrado)")
    if "go.mod" in basenames:
        tech.append("Go")
    if "cargo.toml" in basenames:
        tech.append("Rust")
    return tech, suffix


def tree_text(files, depth=5, max_lines=4500):
    graph = {}
    for filepath in files:
        node = graph
        for part in filepath.split("/"):
            node = node.setdefault(part, {})
    result = []

    def visit(node, prefix="", level=0):
        items = sorted(node.items(), key=lambda kv: kv[0].casefold())
        for index, (name, children) in enumerate(items):
            if len(result) >= max_lines:
                return
            last = index == len(items) - 1
            label = name + ("/" if children else "")
            if children and level + 1 >= depth:
                label += " (...)"
            result.append(prefix + ("└── " if last else "├── ") + label)
            if children and level + 1 < depth:
                visit(children, prefix + ("    " if last else "│   "), level + 1)

    visit(graph)
    if len(result) >= max_lines:
        result.append("... árvore limitada para manter relatório legível")
    return "\n".join(result) + "\n"


def scan(root: Path, mode: str):
    files, configs, stats, limit_hit = inventory(root)
    tech, suffix = detect_tech(files)
    common = {
        "versao_formato": 2,
        "modo": mode,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "tecnologias": tech,
        "arquivos_indexados": len(files),
        "limite_atingido": limit_hit,
        "arquivos_sensiveis_omitidos": stats["sensiveis"],
        "pastas_ignoradas": stats["pastas_ignoradas"],
        "tipos_de_arquivo": dict(sorted(suffix.items())),
    }
    if mode == "public":
        # Intencionalmente não publica nomes de arquivos, diretórios ou projetos.
        return common

    scopes = global_controls(root, configs)
    known = {name.casefold(): name for name in files}
    relations = []
    for file in files:
        if file.lower().endswith(WEBFORMS_EXT):
            relations.extend(links_for_file(root, file, registry_for(file, scopes), known))

    relations.sort(key=lambda r: (r["origem"].casefold(), r["tipo"], r["destino"].casefold()))
    status = Counter(r["status"] for r in relations)
    master_pages = Counter(r["destino"] for r in relations if r["tipo"] == "masterpage")
    common.update({
        "nome_projeto": root.name,
        "arquivos": files,
        "relacoes": relations,
        "referencias_por_status": dict(sorted(status.items())),
        "masterpages_utilizadas": dict(master_pages),
        "observacao": (
            "As relações são estimativas estáticas; recursos relativos dentro de "
            "Master Pages e controles podem depender da URL da página renderizada."
        ),
    })
    return common


# ---------------------------------------------------------------------------
# Relatórios
# ---------------------------------------------------------------------------

def markdown_report(result: dict):
    lines = [
        "# Project Structure Mapper",
        "",
        f"- Modo: **{'público/resumido' if result['modo'] == 'public' else 'privado/detalhado'}**",
        f"- Arquivos indexados: **{result['arquivos_indexados']}**",
        f"- Pastas ignoradas (dependências, build, dados): **{result['pastas_ignoradas']}**",
        f"- Arquivos sensíveis omitidos (.env, Web.config, senhas...): "
        f"**{result['arquivos_sensiveis_omitidos']}**",
    ]
    if result["limite_atingido"]:
        lines.append(
            f"- **Atenção:** limite de {MAX_FILES} arquivos atingido; o relatório está incompleto."
        )
    lines += ["", "## Tecnologias prováveis"]
    lines += ["- " + tech for tech in result["tecnologias"]] or ["- Nenhuma identificada"]
    lines += ["", "## Tipos de arquivo"]
    lines += [f"- {ext}: {count}" for ext, count in result["tipos_de_arquivo"].items()] or [
        "- Nenhum arquivo de código reconhecido"
    ]
    if result["modo"] == "private":
        lines += ["", f"## Projeto: {result['nome_projeto']}"]
        if result["relacoes"]:
            lines += ["", "## Uso de Master Pages"]
            lines += [
                f"- {name}: {count} página(s)"
                for name, count in sorted(
                    result["masterpages_utilizadas"].items(), key=lambda x: (-x[1], x[0])
                )
            ] or ["- Nenhuma referência"]
            lines += ["", "## Referências por status"]
            lines += [
                f"- {status}: {count}"
                for status, count in result["referencias_por_status"].items()
            ]
            lines += ["", "## Algumas relações estáticas"]
            for item in result["relacoes"][:100]:
                lines.append(
                    f"- {item['origem']} -> {item['destino']} "
                    f"({item['tipo']}; {item['status']})"
                )
            lines += [
                "", "A lista completa está em estrutura.json.",
                "Status `contextual` não é erro: o caminho pode ser resolvido pela URL no navegador.",
            ]
        lines += ["", "A árvore de arquivos está em arvore.txt."]
    else:
        lines += [
            "", "## Proteção de privacidade",
            "Este relatório omite nomes de projetos, pastas, arquivos e dependências.",
            "Não garante anonimato absoluto; revise o documento antes de publicar.",
        ]
    lines += [
        "", "## Limitações",
        "- Não executa o projeto, não acessa bancos e não verifica integrações em tempo real.",
        "- Não encontra referências montadas dinamicamente nem todas as chamadas entre classes.",
        "- Referências estáticas não equivalem a dependências comprovadas em execução.",
        "- Nenhum código-fonte é incluído neste relatório.",
    ]
    return "\n".join(lines) + "\n"


def is_inside(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def check_output(root: Path, output: Path):
    if is_inside(output, root):
        raise ValueError(
            "A pasta de saída fica DENTRO do projeto analisado. "
            "Escolha outra pasta (ex.: Documentos) para não alterar o projeto."
        )


def unique_folder(base: Path, prefix: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = base / f"{prefix}{stamp}"
    counter = 2
    while candidate.exists():
        candidate = base / f"{prefix}{stamp}-{counter}"
        counter += 1
    return candidate


def generate(root: Path, mode: str, output: Path, quiet: bool = False):
    say = (lambda *_: None) if quiet else print
    if mode not in {"public", "private"}:
        raise ValueError("Modo inválido: use 'public' ou 'private'.")
    root = Path(root).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"A pasta do projeto não foi encontrada: {root}")
    check_output(root, output)

    say("\n[1/3] Lendo a estrutura (o projeto NÃO é alterado)...")
    report = scan(root, mode)
    say("[2/3] Organizando as informações...")
    output.mkdir(parents=True, exist_ok=True)
    folder = unique_folder(output, "mapa-publico-" if mode == "public" else "mapa-privado-")
    folder.mkdir(parents=True)
    (folder / "relatorio.md").write_text(markdown_report(report), encoding="utf-8")
    (folder / "estrutura.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    names = ["relatorio.md", "estrutura.json"]
    if mode == "private":
        (folder / "arvore.txt").write_text(
            root.name + "/\n" + tree_text(report["arquivos"]), encoding="utf-8"
        )
        names.append("arvore.txt")
    say("[3/3] Gerando o ZIP...")
    archive = folder / "mapa_do_projeto.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(folder / name, arcname=name)

    say(f"\n✓ Concluído! {report['arquivos_indexados']} arquivo(s) indexado(s).")
    if mode == "private":
        say(f"✓ {len(report['relacoes'])} referência(s) estática(s) registrada(s).")
    if report["arquivos_sensiveis_omitidos"]:
        say(f"✓ {report['arquivos_sensiveis_omitidos']} arquivo(s) sensível(is) omitido(s) por segurança.")
    say("✓ O código do projeto NÃO foi copiado para o ZIP.")
    if report["arquivos_indexados"] == 0:
        say("\n! Nenhum arquivo de código reconhecido. Confira se escolheu a pasta certa.")
    if report["limite_atingido"]:
        say(f"\n! Limite de {MAX_FILES} arquivos atingido: escolha uma pasta mais específica.")
    say(f"\nRelatórios em: {folder}")
    say(f"ZIP:           {archive}")
    say("\nATENÇÃO: revise o relatório antes de compartilhar.")
    if mode == "private":
        say("PRIVADO: contém nomes internos de arquivos e pastas. Não publique na internet.")
    return folder


# ---------------------------------------------------------------------------
# Assistente interativo
# ---------------------------------------------------------------------------

def clean_path_input(text: str) -> str:
    """Remove espaços e aspas que o Windows adiciona ao 'Copiar como caminho'."""
    return text.strip().strip('"').strip("'").strip()


def choose_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        window = tk.Tk()
        window.withdraw()
        try:
            window.attributes("-topmost", True)  # Evita a janela abrir escondida atrás do console.
        except Exception:
            pass
        selected = filedialog.askdirectory(title="Selecione a pasta do projeto", parent=window)
        window.destroy()
        return selected or ""
    except Exception:  # Seletor gráfico é opcional: volta ao caminho digitado.
        return ""


def looks_too_broad(path: Path) -> bool:
    resolved = path.resolve()
    return resolved == Path(resolved.anchor) or resolved == Path.home().resolve()


def ask_project(prefilled=None):
    if prefilled:
        project = clean_path_input(prefilled)
        print(f"\nPasta recebida: {project}")
    else:
        print("\nPASSO 1/3 — Qual projeto vamos analisar?")
        print("Dica: no Windows, clique com o botão direito na pasta e use 'Copiar como caminho'.")
        project = clean_path_input(
            input("Cole o caminho da pasta ou pressione Enter para procurar: ")
        )
        if not project:
            print("Abrindo a janela de seleção de pasta...")
            project = choose_folder()
            if not project:
                print("Nenhuma pasta selecionada pela janela.")
    while True:
        if project == "0":
            return None
        path = Path(project).expanduser() if project else None
        if path is not None and path.is_file():
            path = path.parent
        if path is not None and path.is_dir():
            if looks_too_broad(path):
                print(f"\n! '{path}' é uma pasta muito ampla (disco ou pasta do usuário).")
                if not confirm("Analisar mesmo assim? Pode demorar bastante", default=False):
                    project = clean_path_input(input("Cole outra pasta (ou 0 para sair): "))
                    continue
            return path
        message = "Pasta não encontrada. Cole o caminho correto" if project else "Cole o caminho da pasta"
        project = clean_path_input(input(message + " (ou 0 para sair): "))


def ask_mode():
    print("\nPASSO 2/3 — Qual relatório você quer?")
    print("1) Público/resumido: só números e tecnologias, sem nomes (mais seguro)")
    print("2) Privado/detalhado: nomes de arquivos, árvore e referências (uso interno)")
    choice = input("Escolha 1 ou 2 [Enter = 1]: ").strip() or "1"
    while choice not in {"1", "2"}:
        choice = input("Opção inválida. Digite 1 ou 2: ").strip()
    return "public" if choice == "1" else "private"


def ask_output(project: Path):
    print("\nPASSO 3/3 — Onde salvar o relatório? (sempre FORA do projeto)")
    default = Path.home() / "ProjectStructureReports"
    root = project.resolve()
    while True:
        if is_inside(default.resolve(), root):
            default = root.parent / "ProjectStructureReports"
        answer = clean_path_input(input(f"Pasta de saída [Enter = {default}]: "))
        output = Path(answer).expanduser() if answer else default
        if is_inside(output.resolve(), root):
            print("Essa pasta fica dentro do projeto. Escolha outra para não alterá-lo.")
            continue
        return output


def confirm(question: str, default: bool = True) -> bool:
    hint = "[S/n]" if default else "[s/N]"
    answer = input(f"{question}? {hint}: ").strip().lower()
    if not answer:
        return default
    return answer in {"s", "sim", "y", "yes"}


def open_folder(folder: Path):
    try:
        if os.name == "nt":
            os.startfile(str(folder))  # noqa: S606 - abre o Explorer local
            return True
    except OSError:
        pass
    return False


def show_help():
    print("\nO QUE O MAPPER FAZ")
    print("- Lista os arquivos de código e identifica as tecnologias usadas.")
    print("- Em projetos ASP.NET Web Forms, mostra páginas, Master Pages e controles.")
    print("\nO QUE ELE NÃO FAZ")
    print("- Não executa nem altera o projeto. Não envia nada pela internet.")
    print("- Não copia código, senhas ou configurações para o relatório.")
    print("\nTIPOS DE RELATÓRIO")
    print("- Público: só contagens e tecnologias. Pode ser compartilhado após revisão.")
    print("- Privado: inclui nomes de arquivos. Use apenas internamente.")


def wizard(prefilled=None):
    print("\n" + "=" * 60)
    print("   PROJECT STRUCTURE MAPPER  v" + VERSION)
    print("   Entenda a estrutura de um projeto em 3 passos")
    print("=" * 60)
    if not prefilled:
        while True:
            print("\n1) Mapear um projeto")
            print("2) O que essa ferramenta faz?")
            print("0) Sair")
            answer = input("Escolha uma opção [Enter = 1]: ").strip() or "1"
            if answer == "0":
                print("Até mais!")
                return 0
            if answer == "2":
                show_help()
                continue
            if answer == "1":
                break
            print("Opção inválida. Digite 1, 2 ou 0.")

    while True:
        project = ask_project(prefilled)
        prefilled = None
        if project is None:
            print("Saindo sem alterações.")
            return 0
        mode = ask_mode()
        output = ask_output(project)

        print("\nRESUMO")
        print(f"- Projeto:   {project}")
        print(f"- Relatório: {'público/resumido' if mode == 'public' else 'privado/detalhado'}")
        print(f"- Salvar em: {output}")
        print("- Leitura local: nada no projeto é alterado e nada é enviado pela internet.")
        if mode == "private":
            print("AVISO: nomes internos podem ser confidenciais. Não publique esse ZIP.")
        if not confirm("Iniciar análise"):
            print("Cancelado sem alterações.")
        else:
            folder = generate(project, mode, output)
            if os.name == "nt" and confirm("\nAbrir a pasta com os resultados"):
                if not open_folder(folder):
                    print(f"Não consegui abrir automaticamente. Abra manualmente: {folder}")
        if not confirm("\nMapear outro projeto", default=False):
            print("\nPronto! Pode fechar esta janela.")
            return 0


# ---------------------------------------------------------------------------
# Linha de comando
# ---------------------------------------------------------------------------

def friendly_error(exc: BaseException) -> str:
    if isinstance(exc, KeyboardInterrupt):
        return "Cancelado pelo usuário. Nada foi alterado no projeto."
    if isinstance(exc, EOFError):
        return "Entrada encerrada antes do fim. Execute novamente."
    if isinstance(exc, PermissionError):
        return (
            f"Sem permissão para acessar '{exc.filename}'. "
            "Escolha outra pasta de saída (ex.: Documentos) ou verifique as permissões."
        )
    if isinstance(exc, FileNotFoundError):
        return f"Caminho não encontrado: '{exc.filename}'."
    if isinstance(exc, OSError):
        return f"Erro do sistema ao ler/gravar arquivos: {exc.strerror or exc}"
    return str(exc)


def configure_console():
    """Evita travar em consoles Windows antigos que não exibem ✓ ou └──."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    configure_console()
    if sys.version_info < MIN_PYTHON:
        print(
            "Este programa precisa do Python %d.%d ou mais novo. "
            "Baixe em https://www.python.org/downloads/" % MIN_PYTHON,
            file=sys.stderr,
        )
        return 1
    parser = argparse.ArgumentParser(
        description=(
            "Mapeador local de estrutura de projetos. "
            "Sem argumentos, abre um assistente passo a passo."
        )
    )
    parser.add_argument("project", nargs="?", help="Pasta do projeto (opcional: abre o assistente)")
    parser.add_argument(
        "--mode", choices=("public", "private"), default=None,
        help="public = resumo sem nomes (padrão); private = detalhado, uso interno",
    )
    parser.add_argument(
        "--output", default=str(Path.home() / "ProjectStructureReports"),
        help="Pasta onde os relatórios serão salvos (precisa ficar fora do projeto)",
    )
    parser.add_argument(
        "--assistente", action="store_true",
        help="Abre o assistente interativo (usado pelo INICIAR_WINDOWS.bat)",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)

    try:
        if args.assistente or not args.project:
            if not sys.stdin.isatty():
                parser.print_help()
                return 2
            return wizard(args.project)
        project = Path(args.project).expanduser()
        if project.is_file():
            project = project.parent
        generate(project, args.mode or "public", Path(args.output))
        return 0
    except (ValueError, OSError, KeyboardInterrupt, EOFError) as exc:
        print(f"\nNão foi possível concluir: {friendly_error(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
