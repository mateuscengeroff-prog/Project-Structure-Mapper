#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project Structure Mapper - inventário local de código, sem dependências externas."""
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

VERSION = "2.0.0"

SKIP_DIRS = {
    ".git", ".vs", ".idea", ".venv", "venv", "__pycache__",
    "node_modules", "bin", "obj", ".next", "dist", "build",
    "coverage", ".pytest_cache", "testresults", "app_data",
    "uploads", "storage", "secrets", "backup", "backups", "tmp"
}
EXTENSIONS = {
    ".aspx", ".ascx", ".master", ".cs", ".vb", ".csproj", ".vbproj",
    ".sln", ".slnx", ".css", ".scss", ".js", ".jsx", ".ts", ".tsx",
    ".html", ".htm", ".razor", ".cshtml", ".py", ".go", ".java",
    ".kt", ".php", ".rb", ".rs", ".sql", ".md", ".sh", ".ps1",
}
MANIFESTS = {
    "package.json", "pyproject.toml", "requirements.txt",
    "dockerfile", "makefile", "tsconfig.json", "angular.json",
    "vite.config.js", "vite.config.ts", "go.mod", "cargo.toml",
}
MAX_FILES = 25000
MAX_READ = 1024 * 1024

DIRECTIVE_RE = re.compile(r"<%@\s*(?:Page|Master|Control|Register)\b.*?%>", re.I | re.S)
ATTR_RE = re.compile(r"([\w:-]+)\s*=\s*([\"'])(.*?)\2", re.S)
RESOURCE_RE = re.compile(r"<(?:link|script)\b[^>]*>", re.I | re.S)
CONTROL_RE = re.compile(r"<([A-Za-z][\w-]*):([A-Za-z][\w-]*)\b")
COMMENT_RE = re.compile(r"<%--.*?--%>|<!--.*?-->", re.S)
DYNAMIC_RE = re.compile(r"<%|\$\{|\{\{|\}\}")


def name_allowed(filename: str) -> bool:
    lower = filename.lower()
    if lower.startswith(".env") or lower.startswith("appsettings"):
        return False
    if lower in {"web.config", "web.debug.config", "web.release.config"}:
        return False
    if any(x in lower for x in ("secret", "credential", "password", "token", "privatekey", "apikey", "api_key")):
        return False
    return Path(filename).suffix.lower() in EXTENSIONS or lower in MANIFESTS


def inventory(root: Path):
    files = []
    skipped_dirs = 0
    overflow = 0
    for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
        filtered = []
        for dirname in dirs:
            candidate = Path(current) / dirname
            if dirname.lower() in SKIP_DIRS or candidate.is_symlink():
                skipped_dirs += 1
            else:
                filtered.append(dirname)
        dirs[:] = sorted(filtered, key=str.casefold)
        for name in sorted(names, key=str.casefold):
            candidate = Path(current) / name
            if candidate.is_symlink() or not name_allowed(name):
                continue
            if len(files) >= MAX_FILES:
                overflow += 1
                continue
            files.append(candidate.relative_to(root).as_posix())
    return sorted(files, key=str.casefold), skipped_dirs, overflow


def read_small_text(file: Path):
    try:
        if not file.is_file() or file.stat().st_size > MAX_READ:
            return None
        payload = file.read_bytes()
        for encoding in ("utf-8-sig", "cp1252"):
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                pass
        return None
    except OSError:
        return None


def attributes(tag: str):
    return {key.lower(): value for key, _, value in ATTR_RE.findall(tag)}


def normalize_reference(reference: str, source: str):
    """Retorna caminho relativo à raiz; não tenta acessar caminhos externos."""
    value = reference.strip().replace("\\", "/").split("?", 1)[0].split("#", 1)[0]
    if not value or DYNAMIC_RE.search(value):
        return None
    if re.match(r"(?i)^(https?:|//|data:|javascript:|mailto:|#)", value):
        return None
    if re.match(r"^[a-zA-Z]:/", value):
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


def global_controls(root: Path):
    """Lê apenas caminhos de controles registrados; nunca exporta Web.config."""
    result = {}
    config = root / "Web.config"
    try:
        if not config.is_file() or config.stat().st_size > MAX_READ:
            return result
        payload = config.read_bytes()
        if b"<!DOCTYPE" in payload.upper():
            return result
        tree = ElementTree.fromstring(payload)
        for parent in tree.iter():
            if parent.tag.rsplit("}", 1)[-1].lower() != "controls":
                continue
            for child in parent:
                if child.tag.rsplit("}", 1)[-1].lower() != "add":
                    continue
                attrs = {key.lower(): val for key, val in child.attrib.items()}
                prefix = attrs.get("tagprefix", "").lower()
                tag = attrs.get("tagname", "").lower()
                src = attrs.get("src")
                if prefix and tag and src:
                    result[(prefix, tag)] = src
    except (OSError, ValueError, ElementTree.ParseError):
        return {}
    return result


def links_for_file(root: Path, source: str, global_registry: dict):
    text = read_small_text(root / source)
    if not text:
        return []
    text = COMMENT_RE.sub("", text)
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
        status = "contextual" if contextual else ("localizado" if found else "nao_encontrado")
        refs[(kind, target)] = {
            "origem": source, "tipo": kind, "destino": target,
            "status": status,
        }

    for declaration in DIRECTIVE_RE.findall(text):
        attrs = attributes(declaration)
        if re.match(r"<%@\s*Register\b", declaration, re.I):
            prefix = attrs.get("tagprefix", "").lower()
            tag = attrs.get("tagname", "").lower()
            src = attrs.get("src")
            if prefix and tag and src:
                local_registry[(prefix, tag)] = src
                record("registro_controle", src)
            continue
        for key, kind in (
            ("masterpagefile", "masterpage"),
            ("codefile", "codefile"),
            ("codebehind", "codebehind"),
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
    suffix = Counter(Path(file).suffix.lower() for file in files)
    basenames = {Path(file).name.lower() for file in files}
    tech = []
    if any(suffix[x] for x in (".aspx", ".ascx", ".master")):
        tech.append("ASP.NET Web Forms")
    if suffix[".cs"] or suffix[".csproj"]:
        tech.append("C# / .NET")
    if suffix[".razor"] or suffix[".cshtml"]:
        tech.append("Razor / ASP.NET")
    if suffix[".py"]:
        tech.append("Python")
    if suffix[".js"] or suffix[".jsx"]:
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
        for index, (name, children) in enumerate(sorted(node.items(), key=lambda kv: kv[0].casefold())):
            if len(result) >= max_lines:
                return
            last = index == len(node) - 1
            result.append(prefix + ("└── " if last else "├── ") + name)
            if children and level + 1 < depth:
                visit(children, prefix + ("    " if last else "│   "), level + 1)

    visit(graph)
    if len(result) >= max_lines:
        result.append("... árvore limitada para manter relatório legível")
    return "\n".join(result) + "\n"


def scan(root: Path, mode: str):
    files, skipped, overflow = inventory(root)
    tech, suffix = detect_tech(files)
    common = {
        "versao_formato": 2,
        "modo": mode,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "tecnologias": tech,
        "arquivos_indexados": len(files),
        "arquivos_acima_do_limite": overflow,
        "pastas_ignoradas": skipped,
        "tipos_de_arquivo": dict(sorted(suffix.items())),
    }
    if mode == "public":
        # Intencionalmente não publica nomes de arquivos, diretórios ou projetos.
        return common

    registry = global_controls(root)
    relations = []
    for file in files:
        if file.lower().endswith((".aspx", ".ascx", ".master")):
            relations.extend(links_for_file(root, file, registry))

    relations.sort(key=lambda r: (r["origem"].casefold(), r["tipo"], r["destino"].casefold()))
    status = Counter(r["status"] for r in relations)
    master_pages = Counter(r["destino"] for r in relations if r["tipo"] == "masterpage")
    common.update({
        "nome_projeto": root.name,
        "arquivos": files,
        "relacoes": relations,
        "referencias_por_status": dict(status),
        "masterpages_utilizadas": dict(master_pages),
        "observacao": (
            "As relações são estimativas estáticas; recursos relativos dentro de "
            "Master Pages e controles podem depender da URL da página renderizada."
        ),
    })
    return common


def markdown_report(result: dict):
    lines = [
        "# Project Structure Mapper",
        "",
        f"- Modo: **{result['modo']}**",
        f"- Arquivos indexados: **{result['arquivos_indexados']}**",
        f"- Pastas ignoradas: **{result['pastas_ignoradas']}**",
        f"- Excedentes: **{result['arquivos_acima_do_limite']}**",
        "",
        "## Tecnologias prováveis",
    ]
    lines += ["- " + tech for tech in result["tecnologias"]] or ["- Nenhuma identificada"]
    lines += ["", "## Tipos de arquivo"]
    lines += [f"- {ext}: {count}" for ext, count in result["tipos_de_arquivo"].items()]
    if result["modo"] == "private":
        lines += [
            "", f"## Projeto: {result['nome_projeto']}",
            "", "## Uso de Master Pages",
        ]
        lines += [
            f"- {name}: {count} página(s)"
            for name, count in sorted(result["masterpages_utilizadas"].items(), key=lambda x: -x[1])
        ] or ["- Nenhuma referência"]
        lines += ["", "## Referências por status"]
        lines += [
            f"- {status}: {count}"
            for status, count in sorted(result["referencias_por_status"].items())
        ]
        lines += ["", "## Algumas relações estáticas"]
        for item in result["relacoes"][:100]:
            lines.append(
                f"- {item['origem']} -> {item['destino']} "
                f"({item['tipo']}; {item['status']})"
            )
        lines += [
            "", "A lista completa está em estrutura.json.",
            "Status contextual não é erro: o caminho pode ser resolvido pela URL no navegador."
        ]
    else:
        lines += [
            "", "## Proteção de privacidade",
            "Este relatório omite nomes de projetos, pastas, arquivos e dependências.",
            "Não garante anonimato absoluto; revise o documento antes de publicar."
        ]
    lines += [
        "", "## Limitações",
        "- Não executa o projeto, não acessa bancos e não verifica integrações em tempo real.",
        "- Não encontra referências montadas dinamicamente nem todas as chamadas entre classes.",
        "- Referências estáticas não equivalem a dependências comprovadas em execução.",
        "- Nenhum código-fonte é incluído neste relatório.",
    ]
    return "\n".join(lines) + "\n"


def generate(root: Path, mode: str, output: Path):
    root = root.expanduser().resolve()
    output = output.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("A pasta do projeto não existe.")
    if output == root or root in output.parents:
        raise ValueError("Escolha uma pasta de saída FORA do projeto analisado.")

    print("\n[1/3] Lendo estrutura (sem alterar o projeto)...")
    report = scan(root, mode)
    print("[2/3] Organizando as informações...")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = output / ("mapa-publico-" if mode == "public" else "mapa-privado-") / stamp
    folder.mkdir(parents=True, exist_ok=True)
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
    print("[3/3] Gerando ZIP...")
    archive = folder / "mapa_do_projeto.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(folder / name, arcname=name)
    print(f"\n✓ Concluído! {report['arquivos_indexados']} arquivos indexados.")
    if mode == "private":
        print(f"✓ {len(report['relacoes'])} referências estáticas registradas.")
    print("✓ O código do projeto NÃO foi copiado para o ZIP.")
    print(f"\nRelatório: {folder}")
    print(f"ZIP: {archive}")
    print("\nATENÇÃO: revise o relatório antes de compartilhar.")
    if mode == "private":
        print("PRIVADO: pode conter nomes internos de arquivos, pastas e módulos.")
    return folder


def choose_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        window = tk.Tk()
        window.withdraw()
        selected = filedialog.askdirectory(title="Selecione a pasta do projeto")
        window.destroy()
        return selected
    except (ImportError, OSError, RuntimeError, tk.TclError) if "tk" in locals() else (ImportError, OSError, RuntimeError):
        return ""


def wizard():
    print("\n" + "=" * 58)
    print("   PROJECT STRUCTURE MAPPER  v" + VERSION)
    print("   Descubra a estrutura de qualquer projeto em poucos passos")
    print("=" * 58)
    print("1) Mapear um projeto")
    print("2) O que essa ferramenta faz?")
    print("0) Sair")
    while True:
        answer = input("\nEscolha [1]: ").strip() or "1"
        if answer == "0":
            return 0
        if answer == "2":
            print("\nAnalisa nomes de arquivos, tecnologias e referências estáticas.")
            print("Não executa o projeto, não altera código e não envia nada pela internet.")
            print("Você escolhe entre um relatório público resumido e um privado detalhado.")
            continue
        if answer == "1":
            break
        print("Digite 1, 2 ou 0.")

    print("\nPASSO 1/3 — Qual projeto vamos analisar?")
    project = input("Cole o caminho da pasta ou pressione Enter para procurar: ").strip().strip('\"').strip("'")
    if not project:
        project = choose_folder()
    while not project or not Path(project).expanduser().exists():
        project = input("Pasta não encontrada. Cole o caminho correto (ou 0 para sair): ").strip().strip('\"').strip("'")
        if project == "0":
            return 0

    path = Path(project).expanduser()
    if path.is_file():
        path = path.parent

    print("\nPASSO 2/3 — Qual relatório você quer?")
    print("1) Público/resumido: só números e tecnologias (mais seguro)")
    print("2) Privado/detalhado: nomes de arquivos, árvore e referências")
    choice = input("Escolha [1]: ").strip() or "1"
    while choice not in {"1", "2"}:
        choice = input("Digite 1 ou 2: ").strip()
    mode = "public" if choice == "1" else "private"

    print("\nPASSO 3/3 — Vamos salvar o relatório fora do projeto.")
    default = Path.home() / "ProjectStructureReports"
    answer = input(f"Pasta de saída [Enter para {default}]: ").strip().strip('\"').strip("'")
    output = Path(answer) if answer else default

    print("\nResumo: leitura local, nenhuma mudança no projeto e nenhuma conexão de rede.")
    if mode == "private":
        print("AVISO: nomes internos podem ser confidenciais. Não publique esse ZIP no GitHub.")
    if input("Iniciar análise? [S/n]: ").strip().lower() not in {"", "s", "sim", "y", "yes"}:
        print("Cancelado sem alterações.")
        return 0

    folder = generate(path, mode, output)
    if os.name == "nt" and input("\nAbrir pasta de resultados? [S/n]: ").strip().lower() in {"", "s", "sim"}:
        os.startfile(str(folder))
    print("\nPronto! Execute novamente para mapear outro projeto.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mapeador local de estrutura de projetos. Sem argumentos, abre um assistente."
    )
    parser.add_argument("project", nargs="?", help="Pasta do projeto (opcional: abre assistente)")
    parser.add_argument("--mode", choices=("public", "private"), default=None)
    parser.add_argument("--output", default=str(Path.home() / "ProjectStructureReports"))
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)

    try:
        if args.project:
            project = Path(args.project).expanduser()
            if project.is_file():
                project = project.parent
            generate(project, args.mode or "public", Path(args.output))
            return 0
        if not sys.stdin.isatty():
            parser.print_help()
            return 2
        return wizard()
    except (ValueError, OSError, KeyboardInterrupt, EOFError) as exc:
        print(f"\nNão foi possível concluir: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
