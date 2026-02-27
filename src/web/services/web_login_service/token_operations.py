"""Token generation constants for web login service."""

import secrets

# 32 bytes = 256 bits of entropy.  secrets.token_urlsafe(32) produces a
# 43-char URL-safe base64 string.  256 bits makes brute-force guessing
# infeasible (~2^256 possible tokens).
TOKEN_BYTES = 32
# Derived from TOKEN_BYTES so token length validation stays in sync.
# secrets.token_urlsafe(32) produces exactly 43 chars; allow a small
# tolerance range for any future TOKEN_BYTES changes.
TOKEN_LENGTH = len(secrets.token_urlsafe(TOKEN_BYTES))
TOKEN_MIN_LENGTH = TOKEN_LENGTH - 3
TOKEN_MAX_LENGTH = TOKEN_LENGTH + 7
# 3 retries is sufficient because the 256-bit token space makes collisions
# astronomically unlikely (~1 in 2^128 for birthday paradox with 2^128
# existing tokens).  3 retries means we tolerate 3 back-to-back collisions,
# which should never happen in practice.
TOKEN_GENERATION_MAX_RETRIES = 3
