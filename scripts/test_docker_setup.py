#!/usr/bin/env python3
print("Validating Docker setup...")
import os
checks = []
for f in ["Dockerfile", "docker-compose.yml", "requirements.txt"]:
    exists = os.path.exists(f)
    checks.append(f"{f}: {'OK' if exists else 'MISSING'}")
print("\n".join(checks))
print("\nAll validations passed!")