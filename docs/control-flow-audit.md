# Control-flow audit — 2026-09-15

## Scope

Scanned all 220 Python source modules using AST inspection, Ruff, and mypy with
unreachable-code warnings enabled. Traced suspicious paths through callers and
tests, and checked explicit AWS request arguments against the installed botocore
service models. Regression tests use mocks, temporary storage, and botocore
Stubber; they do not contact AWS.

The working tree already contained bulk and statistics changes. Those changes
were preserved. The only edit to the existing statistics collector changes is
the indentation of the Identity Store lookup return.

## Fixed behavior

| Area | Defect and correction |
| --- | --- |
| Statistics collection | The Identity Store lookup returned outside its matching branch, leaving the fallback unreachable and reading an uninitialized variable. Return immediately when the matching instance is found. |
| Restore client calls | Synchronous boto3 responses were awaited, producing `TypeError` after the API call had already executed. Run synchronous calls in a worker thread and support asynchronous clients as well. |
| Restore Identity Store cache | Only the first lookup returned the ID. Subsequent calls now return the cached ID. |
| Restore user creation | Optional names were sent as `None`, which botocore rejects. Omit absent optional fields and retain supplied name components. |
| Permission copying | User/group IDs were used as the AWS account target, `PrincipalId` was absent, and unsupported `AccountId` was supplied. Send the account as `TargetId` and the entity as `PrincipalId`. |
| Copy rollback requests | Deletion supplied unsupported `AccountId` and omitted `TargetType`. Use `TargetId` and `TargetType="AWS_ACCOUNT"`. |
| Copy rollback record parsing | Splitting on every colon broke permission-set ARNs. Decode the last two separators and validate the target; malformed records and incompatible operation types now raise errors before execution. |
| Rollback persistence | Saving a changed operation appended a duplicate while reads returned the old version. Replace previous records with the same operation ID. |
| Failed copy rollbacks | Failed operations were still marked rolled back. Persist completion only when every attempted action succeeds. |
| Copy rollback plans | One action per account used only the first permission set. Build actions from the exact recorded assignment combinations. |
| Rollback pagination | State checks and execution examined only the first assignment page and could incorrectly skip deletion. Share a lookup that follows every page until a match or the end. |
| Rollback log location | Configuration overrode an explicitly supplied storage directory. Explicit constructor arguments now take precedence. |
| Test collection | Statistics and cache tests had conflicting module names. Make statistics tests a package so ordinary pytest collection succeeds. |

Rollback execution also binds each action to its callback and finishes performance
tracking when an empty plan returns early.

## Validation

- Added 16 regression cases in `tests/unit/test_control_flow_regressions.py`.
  Confirmed the relevant cases failed before their fixes.
- Updated two existing assignment-copy tests that asserted invalid AWS arguments.
- 454 focused tests passed across rollback, permission cloning, restore, and the
  new regressions.
- The broader run passed 3,285 tests with seven skips and six warnings, excluding
  `tests/unit/statistics` and `tests/unit/backup_restore/test_encryption.py`.
  This run began before the final synchronous-restore regression was added; that
  final change is covered by the focused run above.
- `poetry run mypy src/`: passed for all 220 modules.
- Ruff passed for the edited source and test files. Black and isort passed for
  the edited files outside the pre-existing statistics collector changes.
- `git diff --check`: passed.
- Ordinary unit-test collection succeeded after the package fix (3,531 tests at
  that point in the audit, before the final restore regression was added).

The initial broad test run stopped after 2,133 passes, 14 failures, one fixture
error, and seven skips. Nine failures depended on encryption-key writes outside
the workspace; two exposed the storage-directory override fixed here; the
remaining failures/error involved existing statistics work. Repository-wide Ruff
also reports 26 existing test issues, largely unused imports in statistics tests.

Reproduce the focused validation with:

```sh
AWS_EC2_METADATA_DISABLED=true poetry run pytest \
  tests/unit/rollback tests/unit/permission_cloning \
  tests/unit/test_control_flow_regressions.py \
  tests/unit/backup_restore/test_restore_manager.py \
  tests/unit/backup_restore/test_restore_manager_cross_account.py -q
poetry run mypy src/
```

## Remaining implementation gaps

These require further implementation and are not resolved by the fixes above:

- Restore resource-existence lookups return `None`, and user/group/permission-set
  update helpers are no-ops in `backup_restore/restore_manager.py`. Consequently,
  conflict handling does not provide a complete restore implementation. The
  cross-account assignment helper is also a no-op.
- Assignment creation/deletion paths can treat an accepted asynchronous AWS
  request as completed without polling its final status. Request-schema tests
  do not establish eventual success in AWS.
- Statistics manager methods still contain `NotImplementedError` placeholders;
  several existing statistics tests have fixture/API mismatches or mock away
  the retry implementation they intend to exercise.

The passing checks establish the repaired paths' behavior. They do not establish
complete backup/restore feature coverage or a clean full test suite.
