Plan: Add idempotency keys to our payments API.

Clients may send an Idempotency-Key header on POST /charges. The server stores the
key-to-response mapping in Redis with a 24h TTL; on a duplicate key it returns the
cached response. Keys are optional. We will enable it for all clients at once next sprint.
