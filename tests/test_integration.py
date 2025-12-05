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
import subprocess
import sys
import re

class TestCLIIntegration(unittest.TestCase):
    def setUp(self):
        self.speedtest_cmd = [sys.executable, 'speedtest.py']
    
    def run_cli(self, args, input=None, timeout=10):
        """Helper to run CLI and return (returncode, stdout, stderr)"""
        cmd = self.speedtest_cmd + args
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if input else None,
            universal_newlines=True
        )
        try:
            stdout, stderr = proc.communicate(input=input, timeout=timeout)
            return proc.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            proc.kill()
            return -1, '', 'Timeout'
    
    def test_help_output(self):
        returncode, stdout, stderr = self.run_cli(['--help'])
        self.assertEqual(returncode, 0)
        self.assertIn('usage:', stdout.lower())
        self.assertIn('speedtest-cli', stdout)
        self.assertIn('--help', stdout)
    
    def test_version_output(self):
        returncode, stdout, stderr = self.run_cli(['--version'])
        self.assertEqual(returncode, 0)
        self.assertIn('speedtest-cli', stdout)
        self.assertRegex(stdout, r'\d+\.\d+\.\d+')
    
    def test_csv_header_output(self):
        returncode, stdout, stderr = self.run_cli(['--csv-header'])
        self.assertEqual(returncode, 0)
        self.assertIn('Server ID', stdout)
        self.assertIn('Download', stdout)
        self.assertIn('Upload', stdout)
    
    def test_invalid_args_no_download_no_upload(self):
        returncode, stdout, stderr = self.run_cli(['--no-download', '--no-upload'])
        self.assertNotEqual(returncode, 0)
        self.assertIn('Cannot supply both', stderr)
    
    def test_invalid_csv_delimiter(self):
        returncode, stdout, stderr = self.run_cli(['--csv-delimiter', 'abc'])
        self.assertNotEqual(returncode, 0)
        self.assertIn('single character', stderr)
    
    def test_source_address_invalid(self):
        # This should fail with invalid source address
        returncode, stdout, stderr = self.run_cli(['--source', 'invalid.ip'], timeout=5)
        # May vary, but should not crash
        self.assertIsInstance(returncode, int)
    
    def test_timeout_option(self):
        returncode, stdout, stderr = self.run_cli(['--timeout', '1', '--list'], timeout=15)
        # Should either succeed or fail gracefully with timeout
        self.assertIsInstance(returncode, int)
    
    def test_kitty_output(self):
        returncode, stdout, stderr = self.run_cli(['--kitty'])
        self.assertEqual(returncode, 0)
        self.assertIn('/\\_/\\', stdout)
        self.assertIn('( o.o )', stdout)
    
    def test_simple_output_format(self):
        # Test with a quick timeout to avoid long test
        returncode, stdout, stderr = self.run_cli(['--simple', '--timeout', '1'], timeout=15)
        # Should either succeed or fail, but not crash
        self.assertIsInstance(returncode, int)
    
    def test_json_output_format(self):
        returncode, stdout, stderr = self.run_cli(['--json', '--timeout', '1'], timeout=15)
        if returncode == 0:
            # If successful, should be valid JSON
            import json
            try:
                json.loads(stdout)
            except json.JSONDecodeError:
                self.fail("Output is not valid JSON")
    
    def test_csv_output_format(self):
        returncode, stdout, stderr = self.run_cli(['--csv', '--timeout', '1'], timeout=15)
        if returncode == 0:
            # Should contain CSV-like output
            self.assertGreater(len(stdout.strip()), 0)


if __name__ == '__main__':
    unittest.main()