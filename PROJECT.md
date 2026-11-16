# AgentGuard — AI Agent Instructions & Governance Policy

## 🛡️ Mandatory Execution Routing

You are an autonomous AI coding/infrastructure agent operating within an environment governed by **AgentGuard**.

### Core Invariant
**You must NEVER execute raw infrastructure or database modification commands directly.**
All consequential operations must be routed through the `agentguard` CLI execution gateway.

### Supported Gateway Commands

| Target Tool | Direct Command (PROHIBITED) | AgentGuard Gateway (MANDATORY) |
|---|---|---|
| Terraform Plan | `terraform plan` | `agentguard terraform plan` |
| Terraform Apply | `terraform apply` | `agentguard terraform apply` |
| Terraform Destroy | `terraform destroy` | `agentguard terraform destroy` |
| High-risk Shell | `rm -rf <path>` | `agentguard exec -- rm -rf <path>` |
| General Shell | `<arbitrary command>` | `agentguard exec -- <command>` |

### Decision Outcomes

When you invoke `agentguard`, the gateway evaluates the action against deterministic safety policies and returns one of three outcomes:

1. **`ALLOW`**: The action is classified as safe and authorized for the current environment. AgentGuard executes the subprocess and returns stdout/stderr and exit code `0`.
2. **`BLOCK`**: The action violates a safety invariant (e.g. destructive actions in production). AgentGuard vetoes execution immediately with exit code `1`. The command is never executed. You must not attempt to circumvent this block.
3. **`REQUIRE_HUMAN_APPROVAL`**: The action modifies infrastructure or database state. The CLI will hold execution and display a spinner while waiting for a human reviewer to authorize it via the AgentGuard Web Dashboard. Do not cancel the process unless explicitly directed by the user.

### Configuration
The project configuration is defined in `.agentguard/config.yaml`. Do not edit the environment or project slug without explicit authorization.
