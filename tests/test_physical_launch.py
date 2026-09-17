import unittest
from scripts.publish_physical_launch import BATCH, CATEGORIES, validate_identity, Text


class LaunchTests(unittest.TestCase):
    def metadata(self, slot):
        result = {'run_id': BATCH, 'topic_id': slot, 'source_id': f'huntlab:{BATCH}:{slot}',
                  'category': CATEGORIES[slot], 'publish_mode': 'publish', 'content_type': 'foundation_concept'}
        if slot == 'basics':
            result['existing_post_id'] = 761
        return result

    def test_exact_four_slots(self):
        self.assertEqual(len(CATEGORIES), 4)
        for slot in CATEGORIES:
            validate_identity(slot, self.metadata(slot))

    def test_other_target_or_category_rejected(self):
        for field, value in [('existing_post_id', 999), ('category', 'Tech'), ('run_id', 'other'), ('publish_mode', 'draft')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_identity('tools', dict(self.metadata('tools'), **{field: value}))

    def test_basics_requires_existing_draft(self):
        data = self.metadata('basics')
        del data['existing_post_id']
        with self.assertRaises(ValueError):
            validate_identity('basics', data)

    def test_image_rewrite_preserves_body_text(self):
        self.assertEqual(Text('<p>Test <img src="local" alt="a"> body</p>').parts,
                         Text('<p>Test <img src="https://huntlab.app/image.png" alt="a"> body</p>').parts)
        self.assertNotEqual(Text('<pre> x</pre>').parts, Text('<pre>x</pre>').parts)
