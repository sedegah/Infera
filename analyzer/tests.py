import os
import tempfile
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from analyzer.services.code_parser import (
    UnsafeZipArchiveError,
    extract_zip_safely,
    generate_mermaid_erd,
)


class UploadCodeViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_upload_rejects_non_zip_files(self):
        payload = SimpleUploadedFile("not_code.txt", b"hello", content_type="text/plain")

        response = self.client.post(reverse("upload_code"), {"file": payload})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Only .zip files are supported")


class CodeParserTests(TestCase):
    def test_extract_zip_safely_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "evil.zip")
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("../escape.py", "print('x')")

            with self.assertRaises(UnsafeZipArchiveError):
                extract_zip_safely(zip_path, os.path.join(tmp_dir, "extract"))

    def test_generate_mermaid_erd_uses_ast_for_methods_attributes_and_functions(self):
        source = b"""
class Parent:
    pass

class Child(Parent):
    kind = 'x'

    def __init__(self):
        self.name = 'demo'

    async def run(self):
        self.status: str = 'ok'

def helper():
    return True
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            python_file = os.path.join(tmp_dir, "sample.py")
            with open(python_file, "wb") as handle:
                handle.write(source)

            diagram = generate_mermaid_erd(tmp_dir)

        self.assertIn("class Child", diagram)
        self.assertIn("name", diagram)
        self.assertIn("status", diagram)
        self.assertIn("__init__", diagram)
        self.assertIn("run", diagram)
        self.assertIn("Parent <|-- Child", diagram)
        self.assertIn("class root_module", diagram)
        self.assertIn("helper", diagram)
