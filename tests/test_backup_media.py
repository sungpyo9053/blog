import copy
import tempfile
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.audit_backup_media import audit_manifest, make_manifest


class BackupMediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        (self.source / '2026/09').mkdir(parents=True)
        (self.source / '2026/09/image.webp').write_bytes(b'fixture-image-not-a-real-photo')
        self.index = ['2026/09/image.webp']
        self.manifest = make_manifest(self.source, self.index)

    def test_database_references_without_uploads_fail(self):
        result = audit_manifest(self.root / 'empty-restore', self.manifest)
        self.assertFalse(result['passed'])
        self.assertEqual(result['failures'][0]['reason'], 'missing_file')

    def test_matching_restored_file_passes_without_claiming_whole_site_recovery(self):
        result = audit_manifest(self.source, self.manifest)
        self.assertTrue(result['passed'])
        self.assertFalse(result['whole_site_restore_verified'])

    def test_same_size_changed_bytes_fail(self):
        path = self.source / self.index[0]
        path.write_bytes(b'x' * path.stat().st_size)
        self.assertEqual(audit_manifest(self.source, self.manifest)['failures'][0]['reason'], 'content_mismatch')

    def test_unsafe_paths_rejected(self):
        for value in ('../private', '/etc/passwd', '2026/../secret', '2026\\secret', './2026/x', '2026//x', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                make_manifest(self.source, [value])

    def test_symlink_refused(self):
        (self.source / 'linked.webp').symlink_to(self.source / self.index[0])
        with self.assertRaises(ValueError):
            make_manifest(self.source, ['linked.webp'])

    def test_missing_source_cannot_become_successful_manifest(self):
        with self.assertRaises(ValueError):
            make_manifest(self.source, ['missing.webp'])

    def test_symlink_root_and_nonstring_reference_refused(self):
        link = self.root / 'linked-root'
        link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            make_manifest(link, self.index)
        with self.assertRaises(ValueError):
            make_manifest(self.source, [None])

    def test_empty_or_malformed_manifest_refused(self):
        for manifest in ({}, {'schema_version':1,'scope':'original_attachment_files','files':[]}, None):
            with self.assertRaises(ValueError):
                audit_manifest(self.source, manifest)

    def test_duplicate_references_collapse_to_one_file(self):
        result = make_manifest(self.source, self.index * 2)
        self.assertEqual(result['reference_count'], 2)
        self.assertEqual(len(result['files']), 1)

    def test_duplicate_manifest_records_refused(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['files'] *= 2
        manifest['reference_count'] = 2
        with self.assertRaises(ValueError):
            audit_manifest(self.source, manifest)

    def test_malformed_hash_and_boolean_size_refused(self):
        for key, value in (('sha256','not-a-hash'), ('bytes',True)):
            manifest = copy.deepcopy(self.manifest)
            manifest['files'][0][key] = value
            with self.assertRaises(ValueError):
                audit_manifest(self.source, manifest)

    def test_reader_cli_exit_codes_and_existing_evidence_preserved(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/audit_backup_media.py'
        index = self.root / 'references.json'
        index.write_text(json.dumps(self.index))
        manifest = self.root / 'manifest.json'
        def run(operation, uploads, source, output):
            return subprocess.run([sys.executable, str(script), operation,
                '--uploads', str(uploads), '--input', str(source), '--output', str(output)],
                capture_output=True, text=True)
        self.assertEqual(run('snapshot', self.source, index, manifest).returncode, 0)
        result = self.root / 'result.json'
        self.assertEqual(run('audit', self.root/'not-restored', manifest, result).returncode, 1)
        previous = result.read_bytes()
        self.assertNotEqual(run('audit', self.source, manifest, result).returncode, 0)
        self.assertEqual(result.read_bytes(), previous)
        self.assertEqual(run('audit', self.source, manifest, self.root/'after.json').returncode, 0)


if __name__ == '__main__':
    unittest.main()
