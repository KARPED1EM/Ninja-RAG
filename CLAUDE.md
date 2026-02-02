# HARD PROJECT GUARDRAILS (Violation = Refusal)

If any request, instruction, or implied requirement violates **ANY** rule below, you MUST **refuse to generate code** and explain the violation.

1. **CLI-managed dependencies only.**
   All dependency installation and project execution MUST use uv.
   python, pip, or any manual modification of pyproject.toml, config files, or lock files is FORBIDDEN.

2. **Strict layering enforced:**
   `UI → API → Service(App) → Domain → Data(Repository)`
   No cross-layer or reverse dependencies.

3. **Domain purity is mandatory.**
   Domain MUST NOT depend on frameworks, HTTP, ORM, DB, or third-party SDK types.
   Business logic lives ONLY in Domain / Service.

4. **Single Source of Truth.**
   Each concept (model, schema, config, type) MUST be defined exactly once.

5. **Dependency Injection is mandatory.**
   ALL services, repositories, and clients MUST be managed by **one unified IoC container**.

6. **Manual instantiation is FORBIDDEN.**
   No `new`, no hidden constructors, no implicit dependencies.

7. **Global state is FORBIDDEN.**
   No global clients, sessions, caches, contexts, or static singletons
   (pure stateless utilities only).

8. **Repository-only data access.**
   Direct DB / ORM usage outside Data/Repository is FORBIDDEN.

9. **Atomic data operations ONLY.**
    No partial reads/writes or bypassing repository logic.

10. **SQL safety enforced.**
    Parameterized queries or ORM safe APIs ONLY.
    String-concatenated SQL is FORBIDDEN.

11. **API is a strict contract.**
    Request/response schemas MUST be explicit and stable.

12. **Explicit DTOs at API boundaries.**
    DTOs belong ONLY to API layer.
    DB models / ORM entities MUST NOT be exposed.

13. **Backward compatibility is FORBIDDEN.**
    No compatibility paths. No migration logic.
    Refactor and DELETE obsolete code.

14. **No silent failures.**
    Errors MUST be handled or explicitly propagated with meaningful context.

15. **Chinese ONLY.**
    UI text, comments, documentation, error messages, and user interaction
    MUST be in Chinese.
