import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class DeleteDocumentTest(unittest.TestCase):
    def test_runtime_status_reports_document_folder_and_pdf_count(self):
        workspace_tmp = Path("C:/tmp/portfolio-tests")
        workspace_tmp.mkdir(parents=True, exist_ok=True)

        with TemporaryDirectory(dir=workspace_tmp) as temp_dir:
            data_dir = Path(temp_dir)
            documentos = data_dir / "Documentos"
            documentos.mkdir(parents=True)
            (documentos / "arquivo.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
            excluded = documentos / "_Excluidos" / "20260527-120000"
            excluded.mkdir(parents=True)
            (excluded / "removido.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")

            previous = os.environ.get("PORTFOLIO_DATA_DIR")
            os.environ["PORTFOLIO_DATA_DIR"] = str(data_dir)
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                for module_name in ("servidor_admin", "app_runtime"):
                    sys.modules.pop(module_name, None)
                servidor_admin = importlib.import_module("servidor_admin")

                response = servidor_admin.app.test_client().get("/api/runtime-status")
            finally:
                if previous is None:
                    os.environ.pop("PORTFOLIO_DATA_DIR", None)
                else:
                    os.environ["PORTFOLIO_DATA_DIR"] = previous

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["pdf_count"], 1)
            self.assertEqual(Path(payload["documentos_dir"]), documentos)

    def test_edit_moves_loose_pdf_to_category_year_folder(self):
        workspace_tmp = Path("C:/tmp/portfolio-tests")
        workspace_tmp.mkdir(parents=True, exist_ok=True)

        with TemporaryDirectory(dir=workspace_tmp) as temp_dir:
            data_dir = Path(temp_dir)
            documentos = data_dir / "Documentos"
            loose_pdf = documentos / "arquivo solto.pdf"
            documentos.mkdir(parents=True)
            loose_pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")

            previous = os.environ.get("PORTFOLIO_DATA_DIR")
            os.environ["PORTFOLIO_DATA_DIR"] = str(data_dir)
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                for module_name in ("servidor_admin", "app_runtime"):
                    sys.modules.pop(module_name, None)
                servidor_admin = importlib.import_module("servidor_admin")

                response = servidor_admin.app.test_client().post(
                    "/api/editar",
                    json={
                        "arquivo": "arquivo solto.pdf",
                        "nome": "Documento Organizado",
                        "assunto": "Teste",
                        "numero": "10",
                        "data": "2026-05-27",
                        "categoria": "Comissão",
                    },
                )
            finally:
                if previous is None:
                    os.environ.pop("PORTFOLIO_DATA_DIR", None)
                else:
                    os.environ["PORTFOLIO_DATA_DIR"] = previous

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["novo_arquivo"], "Comissão/2026/Documento Organizado - Teste.pdf")
            self.assertFalse(loose_pdf.exists())
            self.assertTrue((documentos / payload["novo_arquivo"]).exists())

    def test_delete_moves_pdf_to_recovery_and_cleans_metadata(self):
        workspace_tmp = Path("C:/tmp/portfolio-tests")
        workspace_tmp.mkdir(parents=True, exist_ok=True)

        with TemporaryDirectory(dir=workspace_tmp) as temp_dir:
            data_dir = Path(temp_dir)
            documentos = data_dir / "Documentos"
            site = data_dir / "site"
            pdf = documentos / "Não Categorizado" / "arquivo.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
            site.mkdir()
            (site / "edicoes.json").write_text(json.dumps({
                "Não Categorizado/arquivo.pdf": {"nome": "Arquivo"}
            }), "utf-8")
            (site / "ocultos.json").write_text(json.dumps(["Não Categorizado/arquivo.pdf"]), "utf-8")

            previous = os.environ.get("PORTFOLIO_DATA_DIR")
            os.environ["PORTFOLIO_DATA_DIR"] = str(data_dir)
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                for module_name in ("servidor_admin", "app_runtime"):
                    sys.modules.pop(module_name, None)
                servidor_admin = importlib.import_module("servidor_admin")

                response = servidor_admin.app.test_client().post(
                    "/api/excluir",
                    json={"arquivo": "Não Categorizado/arquivo.pdf"},
                )
            finally:
                if previous is None:
                    os.environ.pop("PORTFOLIO_DATA_DIR", None)
                else:
                    os.environ["PORTFOLIO_DATA_DIR"] = previous

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIn("_Excluidos/", payload["arquivo_recuperacao"])
            self.assertFalse(pdf.exists())
            self.assertTrue((documentos / payload["arquivo_recuperacao"]).exists())
            self.assertEqual(json.loads((site / "edicoes.json").read_text("utf-8")), {})
            self.assertEqual(json.loads((site / "ocultos.json").read_text("utf-8")), [])


if __name__ == "__main__":
    unittest.main()
