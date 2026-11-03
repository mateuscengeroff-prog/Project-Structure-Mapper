import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from mapper import generate, normalize_reference, scan


class MapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "DemoPortal"
        self.project.mkdir()
        (self.project / "components").mkdir()
        (self.project / "Styles").mkdir()
        (self.project / "Scripts").mkdir()
        (self.project / ".git").mkdir()
        (self.project / ".git" / "internal.cs").write_text("ignored", encoding="utf-8")
        (self.project / ".env").write_text("SECRET=DO_NOT_EXPORT", encoding="utf-8")
        (self.project / "Web.config").write_text(
            '<configuration><system.web><pages><controls>'
            '<add tagPrefix="ui" tagName="Header" src="~/components/Header.ascx" />'
            '</controls></pages></system.web></configuration>',
            encoding="utf-8",
        )
        (self.project / "Site.master").write_text(
            '<%@ Master Language="C#" CodeFile="Site.master.cs" %>'
            '<ui:Header ID="header" runat="server" />',
            encoding="utf-8",
        )
        (self.project / "Site.master.cs").write_text("class Layout {}", encoding="utf-8")
        (self.project / "Home.aspx").write_text(
            '<%@ Page Language="C#" MasterPageFile="~/Site.master" '
            'CodeFile="Home.aspx.cs" %>',
            encoding="utf-8",
        )
        (self.project / "Home.aspx.cs").write_text("class Home {}", encoding="utf-8")
        (self.project / "components" / "Header.ascx").write_text(
            '<%@ Control Language="C#" CodeFile="Header.ascx.cs" %>'
            '<link rel="stylesheet" href="../Styles/header.css" />',
            encoding="utf-8",
        )
        (self.project / "components" / "Header.ascx.cs").write_text(
            "class Header {}", encoding="utf-8"
        )
        (self.project / "Styles" / "header.css").write_text("body{}", encoding="utf-8")

    def test_master_and_global_register_are_linked(self):
        data = scan(self.project, "private")
        relations = {
            (r["origem"], r["tipo"], r["destino"])
            for r in data["relacoes"]
        }
        self.assertIn(
            ("Home.aspx", "masterpage", "Site.master"), relations
        )
        self.assertIn(
            ("Site.master", "uso_controle", "components/Header.ascx"), relations
        )
        self.assertIn(
            ("components/Header.ascx", "codefile", "components/Header.ascx.cs"),
            relations,
        )

    def test_relative_asset_is_contextual(self):
        data = scan(self.project, "private")
        css = [
            r for r in data["relacoes"]
            if r["origem"] == "components/Header.ascx" and r["tipo"] == "css"
        ]
        self.assertEqual(len(css), 1)
        self.assertEqual(css[0]["status"], "contextual")

    def test_public_report_has_no_identifiers(self):
        data = scan(self.project, "public")
        serialized = json.dumps(data)
        self.assertNotIn("DemoPortal", serialized)
        self.assertNotIn("Home.aspx", serialized)
        self.assertNotIn("Site.master", serialized)
        self.assertNotIn("DO_NOT_EXPORT", serialized)
        self.assertNotIn("relacoes", data)

    def test_private_report_never_copies_code_or_config(self):
        folder = generate(self.project, "private", self.base / "reports")
        with zipfile.ZipFile(folder / "mapa_do_projeto.zip") as archive:
            self.assertEqual(
                set(archive.namelist()),
                {"arvore.txt", "estrutura.json", "relatorio.md"},
            )
            combined = "\n".join(
                archive.read(name).decode("utf-8")
                for name in archive.namelist()
            )
        self.assertNotIn("SECRET=DO_NOT_EXPORT", combined)
        self.assertNotIn("class Layout", combined)

    def test_output_cannot_be_inside_project(self):
        with self.assertRaises(ValueError):
            generate(self.project, "public", self.project / "outputs")

    def test_reference_cannot_escape_project_root(self):
        self.assertIsNone(normalize_reference("../../escape.cs", "Home.aspx"))

    def test_ignored_dirs_and_sensitive_files(self):
        data = scan(self.project, "private")
        names = data["arquivos"]
        self.assertFalse(any(x.startswith(".git/") for x in names))
        self.assertNotIn(".env", names)
        self.assertNotIn("Web.config", names)


if __name__ == "__main__":
    unittest.main()
