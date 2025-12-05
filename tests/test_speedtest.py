#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2012 Matt Martz
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import unittest
import sys
import re
import time
from io import StringIO

# Import the module to test
import speedtest


class MockOpener:
    def __init__(self, response_data=b'', status=200):
        self.response_data = response_data
        self.status = status

    def open(self, request):
        class MockResponse:
            def __init__(self, data, code):
                self.data = data
                self.code = code
                self.headers = {'content-encoding': None}
            def read(self, size=None):
                return self.data if size is None else self.data[:size]
            def close(self):
                pass
        return MockResponse(self.response_data, self.status)


MOCK_CONFIG_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<settings>
    <client ip="1.2.3.4" lat="40.7128" lon="-74.0060" isp="Test ISP" />
    <server-config ignoreids="" threadcount="4" />
    <download testlength="10" initialtest="350" />
    <upload testlength="10" ratio="2" initialtest="0" mintestsize="32" />
</settings>'''

MOCK_SERVERS_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<settings>
    <servers>
        <server url="http://example.com/upload.php" lat="40.7128" lon="-74.0060" name="Test Server" country="US" sponsor="Test" id="1" />
    </servers>
</settings>'''


class TestSpeedtestUtils(unittest.TestCase):
    def test_distance_known_points(self):
        # New York to London (approximate)
        nyc = (40.7128, -74.0060)
        london = (51.5074, -0.1278)
        result = speedtest.distance(nyc, london)
        # Expected ~5585 km, allow 1% tolerance
        self.assertAlmostEqual(result, 5585, delta=55.85)

    def test_distance_same_point(self):
        point = (0, 0)
        result = speedtest.distance(point, point)
        self.assertEqual(result, 0)

    def test_distance_antipodal(self):
        point1 = (0, 0)
        point2 = (0, 180)
        result = speedtest.distance(point1, point2)
        # Should be approximately half Earth's circumference
        self.assertAlmostEqual(result, 20037, delta=200)

    def test_build_user_agent_format(self):
        ua = speedtest.build_user_agent()
        # Should contain Mozilla, platform, Python, and speedtest-cli
        self.assertIn('Mozilla/5.0', ua)
        self.assertIn('Python/', ua)
        self.assertIn('speedtest-cli', ua)
        # Should match general pattern
        pattern = r'Mozilla/5\.0 \(.*\) Python/.* speedtest-cli/.*'
        self.assertTrue(re.search(pattern, ua))

    def test_build_user_agent_no_empty(self):
        ua = speedtest.build_user_agent()
        self.assertGreater(len(ua), 50)  # Reasonable minimum length

    def test_build_request_basic(self):
        req = speedtest.build_request('http://example.com/test')
        self.assertEqual(req.get_full_url().split('?')[0], 'http://example.com/test')
        self.assertIn('Cache-control', req.headers)
        self.assertEqual(req.headers['Cache-control'], 'no-cache')

    def test_build_request_https_scheme(self):
        req = speedtest.build_request('://example.com/test', secure=True)
        self.assertTrue(req.get_full_url().startswith('https://'))

    def test_build_request_cache_busting(self):
        req1 = speedtest.build_request('http://example.com/test')
        time.sleep(0.001)  # Ensure different timestamp
        req2 = speedtest.build_request('http://example.com/test')
        # URLs should be different due to timestamp
        self.assertNotEqual(req1.get_full_url(), req2.get_full_url())

    def test_build_request_with_data(self):
        data = b'test data'
        req = speedtest.build_request('http://example.com/test', data=data)
        self.assertEqual(req.data, data)

    def test_parse_args_defaults(self):
        # Simulate no arguments
        old_argv = sys.argv
        sys.argv = ['speedtest-cli']
        try:
            args = speedtest.parse_args()
            self.assertTrue(args.download)
            self.assertTrue(args.upload)
            self.assertFalse(args.simple)
            self.assertEqual(args.timeout, 10)
        finally:
            sys.argv = old_argv

    def test_shell_no_download_no_upload_error(self):
        old_argv = sys.argv
        sys.argv = ['speedtest-cli', '--no-download', '--no-upload']
        try:
            with self.assertRaises(speedtest.SpeedtestCLIError):
                speedtest.shell()
        finally:
            sys.argv = old_argv

    def test_parse_args_version(self):
        old_argv = sys.argv
        sys.argv = ['speedtest-cli', '--version']
        try:
            args = speedtest.parse_args()
            self.assertTrue(args.version)
        finally:
            sys.argv = old_argv

    def test_validate_optional_args_json_available(self):
        # Mock args object
        class MockArgs:
            json = True
        args = MockArgs()
        # Should not raise if json is available
        if speedtest.json:
            speedtest.validate_optional_args(args)
        else:
            with self.assertRaises(SystemExit):
                speedtest.validate_optional_args(args)

    def test_validate_optional_args_secure_available(self):
        class MockArgs:
            secure = True
        args = MockArgs()
        if speedtest.HTTPSConnection:
            speedtest.validate_optional_args(args)
        else:
            with self.assertRaises(SystemExit):
                speedtest.validate_optional_args(args)

    def test_printer_normal_output(self):
        # Test that printer doesn't raise exceptions
        try:
            speedtest.printer('test message')
        except Exception as e:
            self.fail(f"printer raised an exception: {e}")

    def test_printer_debug_suppressed(self):
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            speedtest.printer('debug message', debug=True)
            output = sys.stdout.getvalue()
            self.assertEqual(output, '')  # Should be empty when DEBUG=False
        finally:
            sys.stdout = old_stdout

    def test_printer_quiet_suppressed(self):
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            speedtest.printer('quiet message', quiet=True)
            output = sys.stdout.getvalue()
            self.assertEqual(output, '')
        finally:
            sys.stdout = old_stdout


class TestSpeedtestResults(unittest.TestCase):
    def test_init_defaults(self):
        results = speedtest.SpeedtestResults()
        self.assertEqual(results.download, 0)
        self.assertEqual(results.upload, 0)
        self.assertEqual(results.ping, 0)
        self.assertEqual(results.server, {})
        self.assertEqual(results.client, {})

    def test_init_with_params(self):
        results = speedtest.SpeedtestResults(
            download=100, upload=50, ping=20,
            server={'id': '1'}, client={'ip': '1.2.3.4'}
        )
        self.assertEqual(results.download, 100)
        self.assertEqual(results.upload, 50)
        self.assertEqual(results.ping, 20)
        self.assertEqual(results.server['id'], '1')
        self.assertEqual(results.client['ip'], '1.2.3.4')

    def test_dict(self):
        results = speedtest.SpeedtestResults(
            download=100, upload=50, ping=20,
            server={'id': '1'}, client={'ip': '1.2.3.4'}
        )
        data = results.dict()
        self.assertEqual(data['download'], 100)
        self.assertEqual(data['upload'], 50)
        self.assertEqual(data['ping'], 20)
        self.assertEqual(data['server']['id'], '1')
        self.assertEqual(data['client']['ip'], '1.2.3.4')

    def test_csv_header(self):
        header = speedtest.SpeedtestResults.csv_header()
        self.assertIn('Server ID', header)
        self.assertIn('Download', header)
        self.assertIn('Upload', header)

    def test_csv_header_delimiter(self):
        header = speedtest.SpeedtestResults.csv_header(delimiter=';')
        self.assertIn('Server ID', header)
        # Should use semicolon delimiter
        self.assertIn(';', header)

    def test_csv(self):
        results = speedtest.SpeedtestResults(
            download=1000000, upload=500000, ping=20,
            server={'id': '1', 'sponsor': 'Test', 'name': 'Server', 'd': 10},
            client={'ip': '1.2.3.4'}
        )
        csv_data = results.csv()
        self.assertIn('1', csv_data)
        self.assertIn('1000000', csv_data)  # Download in bit/s
        self.assertIn('500000', csv_data)  # Upload in bit/s

    def test_csv_custom_delimiter(self):
        results = speedtest.SpeedtestResults(
            download=1000000, upload=500000, ping=20,
            server={'id': '1', 'sponsor': 'Test', 'name': 'Server', 'd': 10},
            client={'ip': '1.2.3.4'}
        )
        csv_data = results.csv(delimiter=';')
        self.assertIn(';', csv_data)

    def test_json(self):
        results = speedtest.SpeedtestResults(download=100)
        json_data = results.json()
        self.assertIn('"download": 100', json_data)

    def test_json_pretty(self):
        results = speedtest.SpeedtestResults(download=100)
        pretty_json = results.json(pretty=True)
        self.assertIn('\n', pretty_json)
        self.assertIn('"download": 100', pretty_json)


class TestSpeedtest(unittest.TestCase):
    def test_init_defaults(self):
        try:
            st = speedtest.Speedtest()
            self.assertIsNotNone(st.config)
            self.assertEqual(st._source_address, None)
            self.assertEqual(st._timeout, 10)
            self.assertFalse(st._secure)
        except speedtest.ConfigRetrievalError:
            self.skipTest("Network unavailable for config retrieval")


    def test_best_property(self):
        try:
            st = speedtest.Speedtest()
            # Initially empty
            self.assertEqual(st._best, {})
            # Set _best and test property
            st._best = {'id': '1', 'latency': 10}
            self.assertEqual(st.best['id'], '1')
            self.assertEqual(st.best['latency'], 10)
        except speedtest.ConfigRetrievalError:
            self.skipTest("Network unavailable for config retrieval")

    def test_get_closest_servers(self):
        try:
            st = speedtest.Speedtest()
            # Mock servers data
            st.servers = {
                100: [{'id': '1', 'd': 100}],
                50: [{'id': '2', 'd': 50}],
                200: [{'id': '3', 'd': 200}]
            }
            closest = st.get_closest_servers(limit=2)
            self.assertEqual(len(closest), 2)
            self.assertEqual(closest[0]['id'], '2')  # Closest first
            self.assertEqual(closest[1]['id'], '1')  # Second closest
        except speedtest.ConfigRetrievalError:
            self.skipTest("Network unavailable for config retrieval")

    def test_get_closest_servers_limit(self):
        try:
            st = speedtest.Speedtest()
            st.servers = {
                10: [{'id': '1', 'd': 10}],
                20: [{'id': '2', 'd': 20}],
                30: [{'id': '3', 'd': 30}]
            }
            closest = st.get_closest_servers(limit=1)
            self.assertEqual(len(closest), 1)
            self.assertEqual(closest[0]['id'], '1')
        except speedtest.ConfigRetrievalError:
            self.skipTest("Network unavailable for config retrieval")


if __name__ == '__main__':
    unittest.main()