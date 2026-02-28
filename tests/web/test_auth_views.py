"""Auth view tests have been split into focused modules.

See:
- test_auth_request.py — Request initiation endpoint tests
- test_auth_status.py — Status polling endpoint tests
- test_auth_complete.py — Login completion and replay prevention tests
- test_auth_ip_binding.py — IP binding and address parsing tests
- test_auth_helpers.py — Device info, UA parsing, token validation tests
- test_auth_integration.py — Full flow, background, concurrency tests
"""
