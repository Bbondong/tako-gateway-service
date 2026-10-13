import unittest
from unittest.mock import Mock, patch

from flask import Flask
from src.routes import gateway_routes
from securite import securite


class FirebaseGatewayTests(unittest.TestCase):
    def setUp(self):
        securite.ip_requests.clear()
        securite.ip_bans.clear()
        self.app = Flask(__name__)
        self.app.register_blueprint(gateway_routes.gateway_bp)
        self.client = self.app.test_client()

    def test_forwards_firebase_token_unchanged_with_internal_key(self):
        payload = {'id_token': 'opaque--signature', 'nom': 'K', 'prenom': 'B'}
        upstream = Mock(status_code=200)
        upstream.json.return_value = {'access_token': 'internal-jwt'}
        upstream.raw.headers = {}
        with patch.dict(gateway_routes.SERVICE_URLS, client='https://auth.example'), \
                patch.object(gateway_routes, 'INTERNAL_API_KEY', 'server-only-test-key'), \
                patch.object(gateway_routes.requests, 'request', return_value=upstream) as proxy:
            response = self.client.post('/api/v1/auth/firebase-login', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(proxy.call_args.kwargs['url'],
                         'https://auth.example/api/v1/auth/firebase-login')
        self.assertIn(b'opaque--signature', proxy.call_args.kwargs['data'])
        self.assertEqual(proxy.call_args.kwargs['headers']['X-Internal-Key'],
                         'server-only-test-key')

    def test_names_and_other_routes_remain_filtered(self):
        with patch.object(gateway_routes.requests, 'request') as proxy:
            response = self.client.post('/api/v1/auth/firebase-login', json={
                'id_token': 'opaque--signature', 'nom': 'DROP TABLE user'})
            self.assertEqual(response.status_code, 400)
            proxy.assert_not_called()
        securite.ip_requests.clear()
        securite.ip_bans.clear()
        response = self.client.post('/api/v1/other', json={'id_token': 'opaque--signature'})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
