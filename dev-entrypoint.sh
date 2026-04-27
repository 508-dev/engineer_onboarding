#!/bin/bash
# Dev entrypoint: install engineer_onboarding then run the original command
set -e
cd /home/frappe/frappe-bench
./env/bin/pip install -e apps/engineer_onboarding -q
exec "$@"
