"""Manual tracking remains usable when a portable campaign has no rules path."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from sessiondesk.prepared_characters import update
from sessiondesk.prepared_rules import database
from tests.prepared_fixture import make_prepared, rules_library


class PreparedCharacterTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='sessiondesk-character-tracking-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.campaign=make_prepared(self.root/'campaign')
        self.characters=self.campaign/'characters'
        self.file=self.characters/'explorer/character.json'
        self.disconnected=self.root/'not-connected'
        self.addCleanup(database.cache_clear)

    def read(self):
        return json.loads(self.file.read_text(encoding='utf-8'))

    def save(self, value, reference=None):
        return update(self.characters,{'id':'explorer','field':'sheet','value':value},reference or self.disconnected)

    def test_offline_tracking_preserves_imported_rules_choices_and_display_name(self):
        original=self.read()
        original['sheet'].update(subclassKey='Keeper|Sentinel|PHB|Original',raceKey='Original folk|Original',
            subraceKey='Original lineage|Original|Original folk|Original',
            selectedFeatures=['Original option|Original'],selectedSpells=['Original spell|Original'])
        self.file.write_text(json.dumps(original),encoding='utf-8')
        self.save({'hpCurrent':17,'resources':'One charge remains.'})
        saved=self.read()
        self.assertEqual(saved['class'],original['class'])
        self.assertEqual(saved['threads'],original['threads'])
        expected=copy.deepcopy(original['sheet']);expected.update(hpCurrent=17,resources='One charge remains.')
        self.assertEqual(saved['sheet'],expected)

    def test_offline_removal_of_existing_options_does_not_require_source_data(self):
        original=self.read();original['sheet']['selectedSpells']=['Original one|Original','Original two|Original']
        self.file.write_text(json.dumps(original),encoding='utf-8')
        self.save({'selectedSpells':['Original two|Original']})
        self.assertEqual(self.read()['sheet']['selectedSpells'],['Original two|Original'])
        self.assertEqual(self.read()['class'],'Sentinel')

    def test_offline_tracking_rejects_new_unvalidated_rules_choices(self):
        before=self.file.read_bytes()
        for value in ({'classKey':'Other class|XPHB'}, {'raceKey':'Other folk|XPHB'},
                      {'selectedSpells':['New spell|XPHB']}, {'selectedFeatures':['New option|XPHB']}):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.save(value)
            self.assertEqual(self.file.read_bytes(),before)

    def test_connected_new_class_requires_valid_source_and_subclass_pair(self):
        reference=rules_library(self.root/'rules')
        data_path=reference/'data/class/class-sentinel.json'
        data=json.loads(data_path.read_text(encoding='utf-8'))
        data['class'].append({'name':'Other sentinel','source':'PHB','hd':{'faces':10},'classFeatures':[]})
        data['subclass']=[{'name':'Original keeper','shortName':'Keeper','className':'Sentinel','classSource':'PHB','source':'PHB','subclassFeatures':[]}]
        data_path.write_text(json.dumps(data),encoding='utf-8')
        self.save({'subclassKey':'Keeper|Sentinel|PHB|PHB'},reference)
        self.assertEqual(self.read()['class'],'Sentinel · Original keeper')
        before=self.file.read_bytes()
        with self.assertRaisesRegex(ValueError,'Subclass does not match'):
            self.save({'classKey':'Other sentinel|PHB'},reference)
        self.assertEqual(self.file.read_bytes(),before)
        self.save({'classKey':'Other sentinel|PHB','subclassKey':''},reference)
        self.assertEqual(self.read()['class'],'Other sentinel')

    def test_offline_tracking_still_validates_numbers_and_can_clear_class(self):
        before=self.file.read_bytes()
        with self.assertRaises(ValueError):self.save({'hpCurrent':-1})
        self.assertEqual(self.file.read_bytes(),before)
        self.save({'classKey':'','subclassKey':''})
        self.assertEqual(self.read()['class'],'Class not set')
