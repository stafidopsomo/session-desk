"""Offline readiness checks: no installed Codex, account or model needed."""
import json
from pathlib import Path
import queue
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.check_product_boundary import CLEAN_ROOT, inspect_boundary
from tools.probe_codex import ReadOnlyProbe, RpcError, account_summary, schema_summary


class ProbeTests(unittest.TestCase):
    def rpc(self, messages=()):
        # Bypass process creation; all protocol messages are original fakes.
        rpc = ReadOnlyProbe.__new__(ReadOnlyProbe)
        rpc.sequence, rpc.messages, rpc.send = 0, queue.Queue(), Mock()
        for message in messages:
            rpc.messages.put(message)
        return rpc

    def test_account_summary_drops_identity_and_secrets(self):
        summary = account_summary({'account': {
            'type': 'chatgpt', 'email': 'synthetic@example.invalid',
            'accessToken': 'SYNTHETIC_SECRET', 'accountId': 'SYNTHETIC_ID',
        }, 'refreshToken': 'SYNTHETIC_REFRESH'})
        self.assertEqual(summary, {'signedIn': True, 'authMode': 'chatgpt',
                                   'chatgptAccount': True})

    def test_unknown_auth_label_is_not_echoed(self):
        self.assertEqual(account_summary({'account': {'type': 'SYNTHETIC_SECRET'}})
                         ['authMode'], 'unknown')
        self.assertFalse(account_summary({'account': None})['signedIn'])

    def test_inference_and_auth_mutations_are_refused_before_transport(self):
        rpc = self.rpc()
        for method in ('thread/start', 'turn/start', 'account/login/start',
                       'account/logout', 'config/value/write'):
            with self.subTest(method=method), self.assertRaises(ValueError):
                rpc.request(method, {})
        rpc.send.assert_not_called()

    def test_notifications_are_ignored_and_server_requests_denied(self):
        rpc = self.rpc([
            {'method': 'synthetic/notice', 'params': {}},
            {'id': 80, 'method': 'synthetic/approval', 'params': {}},
            {'id': 1, 'result': {'synthetic': True}},
        ])
        self.assertEqual(rpc.request('account/read', {}), {'synthetic': True})
        denial = rpc.send.call_args_list[1].args[0]
        self.assertEqual(denial['id'], 80)
        self.assertEqual(denial['error']['code'], -32601)

    def test_raw_rpc_errors_are_not_exposed(self):
        rpc = self.rpc([{'id': 1, 'error': {
            'code': -32600, 'message': 'SYNTHETIC_PRIVATE_DATA'}}])
        with self.assertRaises(RpcError) as caught:
            rpc.request('command/exec', {})
        self.assertEqual(caught.exception.code, -32600)
        self.assertNotIn('SYNTHETIC_PRIVATE_DATA', str(caught.exception))

    def test_deadline_applies_even_when_notifications_keep_arriving(self):
        rpc = self.rpc([{'method': 'synthetic/notice'}])
        with patch('tools.probe_codex.time.monotonic', side_effect=[0, .5, 2]):
            with self.assertRaises(TimeoutError):
                rpc.request('account/read', {}, timeout=1)

    def test_closed_transport_fails_without_waiting(self):
        rpc = self.rpc([None])
        with self.assertRaisesRegex(RuntimeError, 'transport closed'):
            rpc.request('account/read', {})

    def test_schema_support_is_reported_without_claiming_live_capability(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            schemas = {
                'TurnStartParams': {'properties': {'outputSchema': {}}},
                'ThreadStartParams': {'properties': {'ephemeral': {}}},
                'TurnInterruptParams': {},
                'CommandExecParams': {'definitions': {'SandboxPolicy': {'oneOf': [
                    {'properties': {'type': {'enum': ['readOnly']}}}]}}},
            }
            for name, value in schemas.items():
                (root / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
            summary = schema_summary(root)
            self.assertTrue(summary['structuredOutputField'])
            self.assertTrue(summary['ephemeralThreadField'])
            self.assertTrue(summary['interruptRequestSchema'])
            self.assertFalse(summary['readRootRestrictionInStableCommandSchema'])
            schemas['CommandExecParams']['definitions']['SandboxPolicy']['oneOf'][0][
                'properties']['access'] = {}
            (root / 'CommandExecParams.json').write_text(
                json.dumps(schemas['CommandExecParams']), encoding='utf-8')
            self.assertTrue(schema_summary(root)['readRootRestrictionInStableCommandSchema'])


class BoundaryTests(unittest.TestCase):
    def test_original_text_in_clean_history_passes(self):
        self.assertEqual(inspect_boundary([CLEAN_ROOT], [
            ('README.md', '100644', b'Synthetic readiness content')]), [])

    def test_foreign_root_and_workspace_are_rejected(self):
        errors = inspect_boundary([CLEAN_ROOT, 'synthetic-foreign-root'], [
            ('workspaces/synthetic.json', '100644', b'{}')])
        self.assertEqual(len(errors), 2)

    def test_symlinks_binary_and_oversized_files_are_rejected(self):
        for mode, data in (('120000', b'target'), ('100644', b'\x00'),
                           ('100644', b'\xff'), ('100644', b'x' * 100_001)):
            with self.subTest(mode=mode, length=len(data)):
                self.assertTrue(inspect_boundary([CLEAN_ROOT], [('README.md', mode, data)]))


if __name__ == '__main__':
    unittest.main()
