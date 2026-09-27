import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_bank import prepare_bank


class BankPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "packs").mkdir()

    def pack(self, entries=None):
        entries = entries or [("samples/f1/a.wav", b"recorded vowel a"),
                              ("samples/f1/u.wav", b"recorded vowel u")]
        path = self.root / "packs/f1.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries:
                    archive.writestr(name, data)
        data = path.read_bytes()
        manifest = {"version": 1, "packs": [{"file": "f1.zip",
                    "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
                    "files": len(entries), "unpacked_size": sum(len(value) for _, value in entries)}]}
        (self.root / "packs/manifest.json").write_text(json.dumps(manifest))
        return manifest

    def test_roundtrip_and_idempotence_preserve_existing_samples(self):
        self.pack()
        self.assertEqual(prepare_bank(self.root), {"packs": 1, "extracted": 2, "verified": 0})
        files = list((self.root / "samples/f1").glob("*.wav"))
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
        self.assertEqual(prepare_bank(self.root), {"packs": 1, "extracted": 0, "verified": 2})
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in files})
        self.assertEqual((self.root / "samples/f1/a.wav").read_bytes(), b"recorded vowel a")

    def test_wrong_archive_hash_rejected_before_extraction(self):
        manifest = self.pack()
        manifest["packs"][0]["sha256"] = "0" * 64
        (self.root / "packs/manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            prepare_bank(self.root)
        self.assertFalse((self.root / "samples").exists())

    def test_unsafe_archive_paths_rejected(self):
        for name in ("../escaped.wav", "/absolute.wav", "samples/f1/../../escaped.wav",
                     "samples/f2/wrong-singer.wav", "samples\\f1\\escaped.wav", "C:/absolute.wav"):
            with self.subTest(name=name):
                self.pack([(name, b"unsafe")])
                with self.assertRaisesRegex(ValueError, "Unsafe sample archive path"):
                    prepare_bank(self.root)
                self.assertFalse((self.root / "samples").exists())

    def test_existing_changed_file_is_preserved_and_missing_files_are_not_written(self):
        self.pack()
        destination = self.root / "samples/f1/u.wav"
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"my edited vowel")
        with self.assertRaisesRegex(ValueError, "preserving your file"):
            prepare_bank(self.root)
        self.assertEqual(destination.read_bytes(), b"my edited vowel")
        self.assertFalse((self.root / "samples/f1/a.wav").exists())

    def test_symlink_and_duplicate_archive_members_rejected(self):
        info = zipfile.ZipInfo("samples/f1/link.wav")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.pack([(info, b"../../outside")])
        with self.assertRaisesRegex(ValueError, "symlinks"):
            prepare_bank(self.root)
        for names in (("a.wav", "a.wav"), ("a.wav", "A.wav")):
            with self.subTest(names=names):
                self.pack([("samples/f1/" + name, b"vowel") for name in names])
                with self.assertRaisesRegex(ValueError, "Duplicate sample archive member"):
                    prepare_bank(self.root)
        self.assertFalse((self.root / "samples").exists())

    def test_declared_file_count_and_unpacked_size_rejected(self):
        for key in ("files", "unpacked_size"):
            with self.subTest(key=key):
                manifest = self.pack()
                manifest["packs"][0][key] += 1
                (self.root / "packs/manifest.json").write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, "file count or unpacked size mismatch"):
                    prepare_bank(self.root)
        self.assertFalse((self.root / "samples").exists())


if __name__ == "__main__":
    unittest.main()
