import importlib
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class LoosePdfCatalogTest(unittest.TestCase):
    def test_catalogs_pdf_copied_directly_to_documentos(self):
        workspace_tmp = Path("C:/tmp/portfolio-tests")
        workspace_tmp.mkdir(parents=True, exist_ok=True)

        with TemporaryDirectory(dir=workspace_tmp) as temp_dir:
            data_dir = Path(temp_dir)
            documentos = data_dir / "Documentos"
            documentos.mkdir()
            (documentos / "Declaracao simples.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
            excluded = documentos / "_Excluidos" / "20260527-120000"
            excluded.mkdir(parents=True)
            (excluded / "Removido.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")

            previous = os.environ.get("PORTFOLIO_DATA_DIR")
            os.environ["PORTFOLIO_DATA_DIR"] = str(data_dir)
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                sys.modules.pop("gerar_dados", None)
                gerar_dados = importlib.import_module("gerar_dados")

                records = gerar_dados.catalog_folder(documentos)
            finally:
                if previous is None:
                    os.environ.pop("PORTFOLIO_DATA_DIR", None)
                else:
                    os.environ["PORTFOLIO_DATA_DIR"] = previous

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["arquivo"], "Declaracao simples.pdf")
            self.assertEqual(records[0]["categoria"], "Não Categorizado")
            self.assertEqual(records[0]["ano"], 0)


if __name__ == "__main__":
    unittest.main()
