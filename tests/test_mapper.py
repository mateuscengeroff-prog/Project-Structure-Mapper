"""Testes do Project Structure Mapper.

Todos os projetos usados aqui são FICTÍCIOS e criados numa pasta temporária.
"""
import ast
import contextlib
import hashlib
import io
import json
import os
import re
import socket
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mapper  # noqa: E402
from mapper import generate, normalize_reference, scan, tree_text  # noqa: E402


def write(path: Path, text: str, encoding="utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)


def snapshot(folder: Path):
    """Fotografia do projeto: caminho -> (tamanho, mtime, sha256)."""
    result = {}
    for current, dirs, names in os.walk(folder):
        for name in dirs + names:
            path = Path(current) / name
            rel = path.relative_to(folder).as_posix()
            if path.is_file():
                data = path.read_bytes()
                stat = path.stat()
                result[rel] = (stat.st_size, stat.st_mtime_ns, hashlib.sha256(data).hexdigest())
            else:
                result[rel] = "dir"
    return result


def zip_text(folder: Path):
    with zipfile.ZipFile(folder / "mapa_do_projeto.zip") as archive:
        names = set(archive.namelist())
        text = "\n".join(archive.read(name).decode("utf-8") for name in names)
    return names, text


def build_webforms(base: Path) -> Path:
    project = base / "DemoPortal"
    write(project / ".git" / "internal.cs", "ignored")
    write(project / ".env", "SECRET=DO_NOT_EXPORT")
    write(
        project / "Web.config",
        '<configuration><system.web><pages><controls>'
        '<add tagPrefix="ui" tagName="Header" src="~/components/Header.ascx" />'
        '<add tagPrefix="lib" namespace="Vendor.Controls" assembly="Vendor" />'
        '</controls></pages></system.web>'
        '<connectionStrings><add name="db" connectionString="Password=SUPER_SECRET_PWD" />'
        '</connectionStrings></configuration>',
    )
    write(
        project / "Site.master",
        '<%@ Master Language="C#" CodeFile="Site.master.cs" %>'
        '<ui:Header ID="header" runat="server" />',
    )
    write(project / "Site.master.cs", "class Layout {}")
    write(
        project / "Home.aspx",
        '<%@ Page Language="C#" MasterPageFile="~/Site.master" CodeFile="Home.aspx.cs" %>'
        '<%-- <%@ Register TagPrefix="x" TagName="Old" Src="~/Old.ascx" %> --%>'
        '<adm:Menu runat="server" />',
    )
    write(project / "Home.aspx.cs", "class Home {}")
    write(
        project / "components" / "Header.ascx",
        '<%@ Control Language="C#" CodeFile="Header.ascx.cs" %>'
        '<link rel="stylesheet" href="../Styles/header.css" />'
        '<script src="https://cdn.example.com/lib.js"></script>',
    )
    write(project / "components" / "Header.ascx.cs", "class Header {}")
    write(project / "Styles" / "header.css", "body{}")
    # Subpasta com web.config minúsculo: registro só vale dentro de Admin/.
    write(
        project / "Admin" / "web.config",
        '<?xml version="1.0" encoding="utf-8"?>\n<configuration><system.web><pages><controls>'
        '<add tagPrefix="adm" tagName="Menu" src="Controls/AdminMenu.ascx" />'
        '</controls></pages></system.web></configuration>',
    )
    write(project / "Admin" / "Controls" / "AdminMenu.ascx", '<%@ Control Language="C#" %>')
    write(
        project / "Admin" / "Users.aspx",
        # Caixa diferente do arquivo real (comum em projetos Windows/IIS).
        '<%@ Page Language="C#" MasterPageFile="~/site.master" CodeBehind="Users.aspx.cs" %>'
        '<%@ Reference VirtualPath="~/components/Header.ascx" %>'
        '<adm:Menu runat="server" /><ui:Header runat="server" />'
        '<script src="~/Scripts/missing.js"></script>',
    )
    write(project / "Admin" / "Users.aspx.cs", "class Users {}")
    # Página salva em UTF-16 pelo Visual Studio.
    write(
        project / "Legacy.aspx",
        '<%@ Page Language="VB" MasterPageFile="~/Site.master" %>',
        encoding="utf-16",
    )
    return project


def build_python(base: Path) -> Path:
    project = base / "AcmeBilling"
    write(project / "pyproject.toml", "[project]\nname='acme-billing'\n")
    write(project / "requirements.txt", "requests==2.0\n")
    write(project / "acme_billing" / "__init__.py", "")
    write(project / "acme_billing" / "invoices.py", "def calc_internal_margin():\n    return 42\n")
    write(project / "acme_billing" / "secrets.py", "API_KEY='PY_SECRET_VALUE'\n")
    write(project / "tests" / "test_invoices.py", "def test_x():\n    pass\n")
    write(project / ".venv" / "lib" / "site.py", "venv")
    write(project / "myenv" / "pyvenv.cfg", "home = /usr/bin\n")
    write(project / "myenv" / "lib" / "hidden.py", "venv")
    write(project / "acme_billing" / "__pycache__" / "x.py", "cache")
    write(project / ".env", "DATABASE_URL=postgres://user:PY_DB_PASS@host/db")
    return project


def build_node(base: Path) -> Path:
    project = base / "ZetaStorefront"
    write(project / "package.json", '{"name": "zeta-storefront", "private": true}')
    write(project / "tsconfig.json", "{}")
    write(project / "src" / "index.ts", "export const checkoutFlow = 1;\n")
    write(project / "src" / "components" / "CartWidget.tsx", "export default 1;\n")
    write(project / "src" / "legacy.js", "module.exports = {};\n")
    write(project / "node_modules" / "left-pad" / "index.js", "module.exports = 1;")
    write(project / "dist" / "bundle.js", "bundle")
    write(project / ".env.local", "STRIPE_KEY=NODE_SECRET_VALUE")
    return project


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.out = self.base / "reports"
        self.webforms = build_webforms(self.base)
        self.python = build_python(self.base)
        self.node = build_node(self.base)

    def relations(self, project):
        data = scan(project, "private")
        return data, {(r["origem"], r["tipo"], r["destino"]): r["status"] for r in data["relacoes"]}


class WebFormsTests(Base):
    def test_master_and_global_register_are_linked(self):
        _, rel = self.relations(self.webforms)
        self.assertEqual(rel[("Home.aspx", "masterpage", "Site.master")], "localizado")
        self.assertEqual(rel[("Site.master", "uso_controle", "components/Header.ascx")], "localizado")
        self.assertIn(("components/Header.ascx", "codefile", "components/Header.ascx.cs"), rel)

    def test_relative_asset_is_contextual_and_external_is_ignored(self):
        data, rel = self.relations(self.webforms)
        css = [r for r in data["relacoes"] if r["origem"] == "components/Header.ascx" and r["tipo"] == "css"]
        self.assertEqual(len(css), 1)
        self.assertEqual(css[0]["status"], "contextual")
        self.assertFalse(any("cdn.example.com" in r["destino"] for r in data["relacoes"]))

    def test_nested_lowercase_web_config_applies_only_to_its_folder(self):
        _, rel = self.relations(self.webforms)
        self.assertEqual(
            rel[("Admin/Users.aspx", "uso_controle", "Admin/Controls/AdminMenu.ascx")], "localizado"
        )
        # A raiz herda só o Web.config da raiz.
        self.assertFalse(any(o == "Home.aspx" and t == "uso_controle" for o, t, _ in rel))
        # A subpasta também herda os registros da raiz.
        self.assertIn(("Admin/Users.aspx", "uso_controle", "components/Header.ascx"), rel)

    def test_case_insensitive_paths_like_windows(self):
        _, rel = self.relations(self.webforms)
        self.assertEqual(rel[("Admin/Users.aspx", "masterpage", "Site.master")], "localizado")
        self.assertEqual(rel[("Admin/Users.aspx", "codebehind", "Admin/Users.aspx.cs")], "localizado")

    def test_reference_directive_and_missing_file(self):
        _, rel = self.relations(self.webforms)
        self.assertEqual(rel[("Admin/Users.aspx", "referencia", "components/Header.ascx")], "localizado")
        self.assertEqual(rel[("Admin/Users.aspx", "javascript", "Scripts/missing.js")], "nao_encontrado")

    def test_commented_register_is_ignored(self):
        data, _ = self.relations(self.webforms)
        self.assertFalse(any("Old.ascx" in r["destino"] for r in data["relacoes"]))

    def test_utf16_page_is_read(self):
        _, rel = self.relations(self.webforms)
        self.assertIn(("Legacy.aspx", "masterpage", "Site.master"), rel)

    def test_web_config_with_doctype_is_refused(self):
        write(
            self.webforms / "Web.config",
            '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]>'
            '<configuration><controls><add tagPrefix="ui" tagName="Header" src="~/components/Header.ascx"/>'
            '</controls></configuration>',
        )
        _, rel = self.relations(self.webforms)
        self.assertNotIn(("Site.master", "uso_controle", "components/Header.ascx"), rel)

    def test_broken_web_config_does_not_crash(self):
        write(self.webforms / "Web.config", "<configuration><controls>")
        data = scan(self.webforms, "private")
        self.assertGreater(data["arquivos_indexados"], 0)

    def test_master_page_usage_counter(self):
        data = scan(self.webforms, "private")
        self.assertEqual(data["masterpages_utilizadas"]["Site.master"], 3)


class OtherStacksTests(Base):
    def test_python_project(self):
        data = scan(self.python, "private")
        self.assertIn("Python", data["tecnologias"])
        files = data["arquivos"]
        self.assertIn("acme_billing/invoices.py", files)
        self.assertIn("pyproject.toml", files)
        self.assertFalse(any(f.startswith((".venv/", "myenv/")) for f in files))
        self.assertFalse(any("__pycache__" in f for f in files))
        self.assertNotIn("acme_billing/secrets.py", files)
        self.assertGreaterEqual(data["arquivos_sensiveis_omitidos"], 2)
        self.assertEqual(data["relacoes"], [])

    def test_node_project(self):
        data = scan(self.node, "private")
        self.assertIn("Node.js (manifesto encontrado)", data["tecnologias"])
        self.assertIn("TypeScript", data["tecnologias"])
        self.assertIn("JavaScript", data["tecnologias"])
        files = data["arquivos"]
        self.assertIn("src/components/CartWidget.tsx", files)
        self.assertFalse(any(f.startswith(("node_modules/", "dist/")) for f in files))
        self.assertNotIn(".env.local", files)

    def test_tree_marks_folders(self):
        text = tree_text(["a/b.py", "c.py"])
        self.assertIn("a/", text)
        self.assertIn("b.py", text)

    def test_file_limit_stops_walk(self):
        with mock.patch.object(mapper, "MAX_FILES", 3):
            data = scan(self.node, "public")
        self.assertEqual(data["arquivos_indexados"], 3)
        self.assertTrue(data["limite_atingido"])

    @unittest.skipIf(os.name == "nt", "links simbólicos exigem privilégios no Windows")
    def test_symlinks_are_not_followed(self):
        outside = self.base / "Outside"
        write(outside / "leak.py", "x")
        os.symlink(outside, self.node / "linked")
        os.symlink(outside / "leak.py", self.node / "leak.py")
        data = scan(self.node, "private")
        self.assertFalse(any("leak" in f for f in data["arquivos"]))


class PrivacyAndSafetyTests(Base):
    SECRETS = (
        "DO_NOT_EXPORT", "SUPER_SECRET_PWD", "PY_SECRET_VALUE", "PY_DB_PASS",
        "NODE_SECRET_VALUE", "class Layout", "calc_internal_margin", "checkoutFlow",
    )

    def all_names(self, project):
        names = {project.name}
        for current, dirs, files in os.walk(project):
            names.update(dirs)
            names.update(Path(f).stem for f in files)
        return {n for n in names if len(n) > 3 and not n.startswith(".")}

    def test_public_reports_have_no_identifiers_or_content(self):
        generic = {"package", "pyproject", "requirements", "tsconfig", "tests", "Styles", "Scripts"}
        for project in (self.webforms, self.python, self.node):
            with self.subTest(project=project.name):
                folder = generate(project, "public", self.out, quiet=True)
                names, text = zip_text(folder)
                self.assertEqual(names, {"estrutura.json", "relatorio.md"})
                self.assertNotIn(project.name, str(folder))
                for identifier in self.all_names(project) - generic:
                    pattern = r"(?<![\w])" + re.escape(identifier) + r"(?![\w])"
                    self.assertIsNone(re.search(pattern, text, re.I), identifier)
                for secret in self.SECRETS:
                    self.assertNotIn(secret, text)
                data = json.loads((folder / "estrutura.json").read_text(encoding="utf-8"))
                for key in ("arquivos", "relacoes", "nome_projeto", "masterpages_utilizadas"):
                    self.assertNotIn(key, data)

    def test_private_report_never_copies_code_or_config(self):
        for project in (self.webforms, self.python, self.node):
            with self.subTest(project=project.name):
                folder = generate(project, "private", self.out, quiet=True)
                names, text = zip_text(folder)
                self.assertEqual(names, {"arvore.txt", "estrutura.json", "relatorio.md"})
                for secret in self.SECRETS:
                    self.assertNotIn(secret, text)
                self.assertNotIn("connectionString", text)

    def test_projects_are_not_modified(self):
        for project in (self.webforms, self.python, self.node):
            for mode in ("public", "private"):
                with self.subTest(project=project.name, mode=mode):
                    before = snapshot(project)
                    generate(project, mode, self.out, quiet=True)
                    self.assertEqual(before, snapshot(project))

    def test_no_network_is_used(self):
        def blocked(*args, **kwargs):
            raise AssertionError("tentativa de conexão de rede")

        with mock.patch.object(socket, "socket", blocked), \
                mock.patch.object(socket, "create_connection", blocked), \
                mock.patch.object(socket, "getaddrinfo", blocked):
            generate(self.webforms, "private", self.out, quiet=True)
            generate(self.node, "public", self.out, quiet=True)

    def test_source_imports_no_network_modules(self):
        tree = ast.parse((ROOT / "mapper.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"socket", "urllib", "http", "requests", "ftplib", "smtplib", "ssl", "subprocess"}
        self.assertEqual(imported & forbidden, set())

    def test_output_cannot_be_inside_project(self):
        with self.assertRaises(ValueError):
            generate(self.webforms, "public", self.webforms / "outputs", quiet=True)
        with self.assertRaises(ValueError):
            generate(self.webforms, "public", self.webforms, quiet=True)
        self.assertFalse((self.webforms / "outputs").exists())

    def test_output_folder_name_and_unique_runs(self):
        first = generate(self.node, "public", self.out, quiet=True)
        second = generate(self.node, "public", self.out, quiet=True)
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, self.out.resolve())
        self.assertTrue(first.name.startswith("mapa-publico-20"))

    def test_reference_cannot_escape_project_root(self):
        self.assertIsNone(normalize_reference("../../escape.cs", "Home.aspx"))
        self.assertIsNone(normalize_reference(r"C:\Windows\win.ini", "Home.aspx"))
        self.assertIsNone(normalize_reference(r"\\server\share\x.js", "Home.aspx"))
        self.assertIsNone(normalize_reference("file:///etc/passwd", "Home.aspx"))
        self.assertEqual(normalize_reference(r"..\Styles\a.css", "pages/A.aspx"), "Styles/a.css")

    def test_ignored_dirs_and_sensitive_files(self):
        data = scan(self.webforms, "private")
        names = data["arquivos"]
        self.assertFalse(any(x.startswith(".git/") for x in names))
        self.assertNotIn(".env", names)
        self.assertFalse(any(x.lower().endswith("web.config") for x in names))


class InterfaceTests(Base):
    def run_main(self, argv, tty=False):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.object(sys.stdin, "isatty", return_value=tty):
            code = mapper.main(argv)
        return code, out.getvalue(), err.getvalue()

    def run_wizard(self, answers, prefilled=None):
        out = io.StringIO()
        queue = list(answers)

        def fake_input(prompt=""):
            out.write(prompt)  # o input() real mostra o texto na tela
            return queue.pop(0)

        with contextlib.redirect_stdout(out), \
                mock.patch("builtins.input", side_effect=fake_input), \
                mock.patch.object(mapper, "choose_folder", return_value=""), \
                mock.patch.object(mapper.os, "name", "posix"):
            code = mapper.wizard(prefilled)
        return code, out.getvalue()

    def test_cli_public_default(self):
        code, out, _ = self.run_main([str(self.node), "--output", str(self.out)])
        self.assertEqual(code, 0)
        self.assertIn("Concluído", out)
        self.assertEqual(len(list(self.out.glob("mapa-publico-*"))), 1)

    def test_cli_missing_folder_has_friendly_error(self):
        code, _, err = self.run_main([str(self.base / "nao-existe"), "--output", str(self.out)])
        self.assertEqual(code, 1)
        self.assertIn("não foi encontrada", err)

    def test_cli_output_inside_project_has_friendly_error(self):
        code, _, err = self.run_main([str(self.node), "--output", str(self.node / "rel")])
        self.assertEqual(code, 1)
        self.assertIn("DENTRO do projeto", err)
        self.assertFalse((self.node / "rel").exists())

    def test_cli_without_terminal_shows_help(self):
        code, out, _ = self.run_main([], tty=False)
        self.assertEqual(code, 2)
        self.assertIn("--mode", out)

    def test_wizard_full_flow_private(self):
        answers = [
            "9",                         # opção inválida no menu
            "2",                         # ajuda
            "1",                         # mapear
            '"%s"' % self.webforms,      # caminho com aspas (Copiar como caminho)
            "x", "2",                    # modo inválido, depois privado
            str(self.webforms / "rel"),  # saída dentro do projeto: recusada
            str(self.out),               # saída válida
            "",                          # confirmar
            "n",                         # não mapear outro
        ]
        code, out = self.run_wizard(answers)
        self.assertEqual(code, 0)
        self.assertIn("Opção inválida", out)
        self.assertIn("dentro do projeto", out)
        self.assertEqual(len(list(self.out.glob("mapa-privado-*"))), 1)
        self.assertFalse((self.webforms / "rel").exists())

    def test_wizard_retries_missing_folder_and_can_cancel(self):
        answers = ["1", str(self.base / "nao-existe"), str(self.python), "", "", "n", "n"]
        code, out = self.run_wizard(answers)
        self.assertEqual(code, 0)
        self.assertIn("Pasta não encontrada", out)
        self.assertIn("Cancelado sem alterações", out)
        self.assertFalse(self.out.exists())

    def test_wizard_empty_enter_without_gui_asks_path(self):
        answers = ["1", "", "0"]
        code, out = self.run_wizard(answers)
        self.assertEqual(code, 0)
        self.assertIn("Nenhuma pasta selecionada", out)

    def test_wizard_prefilled_from_drag_and_drop(self):
        answers = ["1", str(self.out), "", "n"]
        code, out = self.run_wizard(answers, prefilled='"%s"' % self.node)
        self.assertEqual(code, 0)
        self.assertEqual(len(list(self.out.glob("mapa-publico-*"))), 1)

    def test_legacy_console_encoding_does_not_crash(self):
        """Consoles antigos/redirecionados do Windows (cp437/cp850) não exibem ✓ nem acentos."""
        import subprocess  # apenas nos testes; o mapper não usa subprocess

        env = dict(os.environ, PYTHONIOENCODING="cp437")
        result = subprocess.run(
            [sys.executable, str(ROOT / "mapper.py"), str(self.node), "--output", str(self.out)],
            capture_output=True, env=env, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bat_launcher_is_crlf_and_calls_wizard(self):
        data = (ROOT / "INICIAR_WINDOWS.bat").read_bytes()
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.bat text eol=crlf", attributes)
        text = data.decode("ascii")  # sem acentos: evita problemas de code page no cmd.exe
        self.assertIn("--assistente", text)
        self.assertIn("pause", text)
        if os.name == "nt" or b"\r\n" in data:
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))


if __name__ == "__main__":
    unittest.main()
