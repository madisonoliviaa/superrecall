"""
Seed the knowledge base with realistic workflow issues.
Run once: python seed_data.py
"""

import requests

API = "http://localhost:8042"

ISSUES = [
    {
        "service": "Redis",
        "environment": "prod",
        "error_message": "Redis connection pool exhausted: max connections reached (128/128)",
        "root_cause": "Default max_connections was set to 128, insufficient for peak traffic. Connection leak in the session handler was not releasing connections on timeout.",
        "fix_applied": "Increased max_connections to 512 in redis.conf. Fixed connection leak in session handler by adding proper finally block to release connections. Deployed hotfix via SuperPlane rollback canvas.",
        "severity": "P1",
        "tags": ["redis", "connection-pool", "config", "memory"],
        "workflow_name": "prod-deploy-pipeline",
        "additional_notes": "Issue first appeared after traffic spike from Product Hunt launch. Monitor connection pool usage going forward.",
    },
    {
        "service": "PostgreSQL",
        "environment": "prod",
        "error_message": "ERROR: deadlock detected. Process 12847 waits for ShareLock on transaction 987654",
        "root_cause": "Two concurrent migration scripts both tried to ALTER TABLE on the users table. The scheduled migration ran while a manual migration was still in progress.",
        "fix_applied": "Killed the hung migration process. Added advisory lock to migration scripts to prevent concurrent runs. Added a pre-migration check to the deploy canvas that verifies no active migrations.",
        "severity": "P1",
        "tags": ["postgres", "migration", "deadlock", "database"],
        "workflow_name": "database-migration-canvas",
        "additional_notes": "Downtime was 12 minutes. Added Slack alert to migration canvas to notify before running.",
    },
    {
        "service": "GitHub Actions",
        "environment": "staging",
        "error_message": "CI pipeline timeout after 30 minutes. Tests hung on integration suite.",
        "root_cause": "Flaky test in auth module was waiting for external OAuth provider that was down. No timeout configured on the HTTP client in test setup.",
        "fix_applied": "Added 10-second timeout to all HTTP clients in test fixtures. Mocked external OAuth calls in integration tests. Added retry with circuit breaker pattern.",
        "severity": "P2",
        "tags": ["ci", "timeout", "flaky-tests", "github-actions"],
        "workflow_name": "ci-test-pipeline",
        "additional_notes": "This same OAuth provider has caused 3 test failures in the past month. Consider permanent mock.",
    },
    {
        "service": "DigitalOcean",
        "environment": "staging",
        "error_message": "Droplet creation failed: 422 Unprocessable Entity. Region nyc1 capacity exceeded.",
        "root_cause": "DigitalOcean NYC1 region hit capacity limits during a cloud provider incident. Preview environment canvas could not provision new droplets.",
        "fix_applied": "Added fallback region (sfo3) to the preview environment canvas. If primary region fails, automatically retry in fallback region. Added region health check as first step.",
        "severity": "P2",
        "tags": ["digitalocean", "capacity", "preview-env", "infrastructure"],
        "workflow_name": "preview-env-canvas",
        "additional_notes": "DO status page confirmed NYC1 capacity issues. Fallback region logic now handles this automatically.",
    },
    {
        "service": "API Gateway",
        "environment": "prod",
        "error_message": "502 Bad Gateway. Upstream connection refused on port 3000.",
        "root_cause": "Node.js application crashed due to unhandled promise rejection in the WebSocket handler. PM2 restart was slower than the health check interval, causing the load balancer to mark the instance as down.",
        "fix_applied": "Added global unhandled rejection handler. Increased PM2 restart delay tolerance. Extended health check interval from 5s to 15s with 3 retries before marking unhealthy.",
        "severity": "P1",
        "tags": ["api", "502", "node", "crash", "health-check"],
        "workflow_name": "prod-deploy-pipeline",
        "additional_notes": "Root cause was a race condition in WebSocket cleanup during client disconnect.",
    },
    {
        "service": "SSL/TLS",
        "environment": "prod",
        "error_message": "SSL certificate expired. ERR_CERT_DATE_INVALID on api.example.com",
        "root_cause": "Let's Encrypt auto-renewal cron job was disabled after a server migration. Certificate expired without warning because the monitoring alert was pointed at the old server.",
        "fix_applied": "Re-enabled certbot auto-renewal. Added certificate expiry monitoring to the ops canvas with 14-day and 7-day warning alerts. Moved to Render managed TLS.",
        "severity": "P1",
        "tags": ["ssl", "certificate", "letsencrypt", "monitoring"],
        "workflow_name": "infrastructure-health-canvas",
        "additional_notes": "30 minutes of downtime for HTTPS traffic. HTTP continued working but redirected to broken HTTPS.",
    },
    {
        "service": "Docker",
        "environment": "staging",
        "error_message": "Container killed: OOMKilled. Exit code 137. Memory limit 512MB exceeded.",
        "root_cause": "Memory leak in image processing library. Each uploaded image allocated ~50MB that was never freed due to missing cleanup in the sharp library usage.",
        "fix_applied": "Added explicit buffer cleanup after image processing. Increased container memory limit to 1GB as safety net. Added memory usage monitoring with alert at 80% threshold.",
        "severity": "P2",
        "tags": ["docker", "oom", "memory-leak", "image-processing"],
        "workflow_name": "staging-deploy-canvas",
        "additional_notes": "Leak was proportional to upload volume. Staging caught it before prod because of lower memory limits.",
    },
    {
        "service": "Stripe Webhook",
        "environment": "prod",
        "error_message": "Stripe webhook signature verification failed. HTTP 400 on /webhooks/stripe endpoint.",
        "root_cause": "Webhook signing secret was rotated in Stripe dashboard but the environment variable was not updated in the production deployment. Old secret was still cached.",
        "fix_applied": "Updated STRIPE_WEBHOOK_SECRET in production environment variables. Added secret rotation checklist to the deploy canvas. Canvas now verifies webhook connectivity after deploy.",
        "severity": "P2",
        "tags": ["stripe", "webhook", "secrets", "payments"],
        "workflow_name": "payment-pipeline-canvas",
        "additional_notes": "Payments continued processing but webhook events were lost for 2 hours. Had to replay events from Stripe dashboard.",
    },
    {
        "service": "DNS",
        "environment": "prod",
        "error_message": "DNS resolution failed for staging.example.com. NXDOMAIN response.",
        "root_cause": "DNS propagation delay after switching from Route53 to Cloudflare. TTL on old records was set to 86400 (24 hours) so some resolvers still had cached old records.",
        "fix_applied": "Lowered TTL to 300 seconds before migration. Waited 24h for old TTL to expire. Added DNS resolution check to deploy canvas that verifies domain resolves before proceeding.",
        "severity": "P2",
        "tags": ["dns", "propagation", "cloudflare", "migration"],
        "workflow_name": "infrastructure-migration-canvas",
        "additional_notes": "Affected approximately 15% of users for 6 hours. US-East resolvers were worst affected.",
    },
    {
        "service": "Render",
        "environment": "prod",
        "error_message": "Deploy failed: build exceeded 15-minute timeout. Node modules install hung.",
        "root_cause": "Package-lock.json had a circular dependency that caused npm to hang during resolution. The lock file was corrupted after a merge conflict was resolved incorrectly.",
        "fix_applied": "Deleted package-lock.json and regenerated it. Switched to bun for faster, more reliable installs. Added a pre-deploy canvas step that validates the lock file integrity.",
        "severity": "P2",
        "tags": ["render", "deploy", "npm", "dependencies", "build"],
        "workflow_name": "prod-deploy-pipeline",
        "additional_notes": "Build times dropped from 12min to 3min after switching to bun. Lock file validation catches corruption before deploy.",
    },
    {
        "service": "Convex",
        "environment": "dev",
        "error_message": "Convex function timeout: query exceeded 60-second limit. Stack overflow in recursive resolver.",
        "root_cause": "Recursive query in the feed resolver created infinite loop when a user followed themselves. No cycle detection in the social graph traversal.",
        "fix_applied": "Added cycle detection with a visited-set to the graph traversal. Added max-depth limit of 10. Added input validation to prevent self-follows at the mutation level.",
        "severity": "P3",
        "tags": ["convex", "timeout", "recursion", "query"],
        "workflow_name": "dev-test-canvas",
        "additional_notes": "Only affected dev environment. Added test case for self-follow scenario.",
    },
    {
        "service": "Slack Integration",
        "environment": "prod",
        "error_message": "Slack API rate limited: 429 Too Many Requests. Notification queue backing up.",
        "root_cause": "Deploy canvas was sending individual Slack messages for each step completion. During a busy deploy day with 20+ deploys, this exceeded Slack's rate limit of 1 message per second per channel.",
        "fix_applied": "Batched deploy notifications into a single summary message per deploy. Added rate limiting middleware to the Slack integration component. Canvas now collects all step results and posts once at completion.",
        "severity": "P3",
        "tags": ["slack", "rate-limit", "notifications", "integration"],
        "workflow_name": "prod-deploy-pipeline",
        "additional_notes": "Slack rate limits are per-workspace and per-channel. Batching reduced API calls by 85%.",
    },
]


def seed():
    """Seed the database with example workflow issues."""
    print(f"Seeding {len(ISSUES)} workflow issues...")

    for i, issue in enumerate(ISSUES, 1):
        try:
            resp = requests.post(f"{API}/api/issues", json=issue)
            resp.raise_for_status()
            data = resp.json()
            print(f"  [{i}/{len(ISSUES)}] {data['message']}")
        except Exception as e:
            print(f"  [{i}/{len(ISSUES)}] FAILED: {e}")

    print(f"\nDone! {len(ISSUES)} issues seeded.")
    print(f"Try: curl '{API}/api/search?q=database+connection+timeout'")


if __name__ == "__main__":
    seed()
