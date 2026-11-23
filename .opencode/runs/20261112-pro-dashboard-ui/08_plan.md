# S8 PLAN — sequenced next steps

1. Rewrite src/api/web/templates/dashboard.html (pro UI, same path/contract). — DONE
2. Verify: compileall exit 0. — DONE
3. Verify: focused integration test test_full_buy_sell_pnl_flow passes. — DONE
4. Verify: flake8 (0 errors), mypy on config+logger (clean); black/isort only flag pre-existing untouched Python files. — DONE
5. S12 review (independent Task, edit:deny, spec+diff only) → 12_review.md.
6. S17 hostile judge (independent Task, edit:deny, spec+diff only) → 17_judge.md.
7. If PASS/PASS → write 16_verify.log + 18_learn.md; mark done citing 16_verify.log + 12_review.md:PASS + 17_judge.md:PASS.
8. Residual: uvicorn render check could not be run (classifier blocked starting the server previously); flagged for user to run manually: FASTAPI_API_KEY=dev-key python entrypoint.py, open /dashboard.
