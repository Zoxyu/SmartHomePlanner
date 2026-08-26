# AGENTS.md

## 1. 文件目的 / Purpose

本文件定义所有 AI Coding Agent 在本项目中的通用工作规则。

This file defines the general working rules for all AI coding agents working on this project.

无论使用什么 AI 厂商、Coding 软件、CLI、IDE 或 Agent，都应遵守本文件中的规则。

These rules apply regardless of the AI vendor, coding tool, CLI, IDE, or agent being used.

本项目使用统一的项目上下文文件：

This project uses a shared project context file:

`AI_CONTEXT.md`

`AI_CONTEXT.md` 是本项目在不同 AI Agent、Coding 工具、账号、Session 和设备之间共享的持久化项目状态。

`AI_CONTEXT.md` is the persistent project state shared across different AI agents, coding tools, accounts, sessions, and devices.

除非用户明确要求，否则不要创建厂商专用的项目上下文文件。

Do not create vendor-specific project context files unless explicitly requested by the user.

例如 / Examples:

- QODER_CONTEXT.md
- CODEX_CONTEXT.md
- CLAUDE_CONTEXT.md
- CURSOR_CONTEXT.md


---

## 2. 上下文恢复 / Context Recovery

开始一个非简单任务之前：

Before starting a non-trivial task:

1. 如果 `AI_CONTEXT.md` 存在，必须先读取。
   
   If `AI_CONTEXT.md` exists, read it first.

2. 检查当前 Git 分支以及工作区状态。
   
   Check the current Git branch and working tree status.

3. 阅读与当前任务直接相关的代码、配置、测试和文档。
   
   Inspect the code, configuration, tests, and documentation directly related to the current task.

4. 不要假设之前的 AI 对话历史仍然存在。
   
   Do not assume that previous AI conversation history is available.

5. 不要假设之前的 AI Agent 得出的结论一定正确。
   
   Do not assume that conclusions made by previous AI agents are necessarily correct.

6. 如果 `AI_CONTEXT.md` 与实际代码、配置、测试或 Git 状态发生冲突，应以实际项目状态为准。
   
   If `AI_CONTEXT.md` conflicts with the actual code, configuration, tests, or Git state, treat the actual project state as the source of truth.

如果 `AI_CONTEXT.md` 不存在：

If `AI_CONTEXT.md` does not exist:

- 先分析项目；
  
  Inspect the project first.

- 创建 `AI_CONTEXT.md`；
  
  Create `AI_CONTEXT.md`.

- 只记录对未来 Agent 有长期价值的信息。
  
  Record only information that is likely to be useful to future agents.

不要为了恢复丢失的聊天上下文，而进行没有必要的全项目分析。

Do not perform unnecessary project-wide analysis merely to reconstruct lost conversation history.


---

## 3. 任务执行 / Task Execution

修改代码之前：

Before modifying code:

1. 明确理解用户要求解决的问题。
   
   Clearly understand the problem the user wants to solve.

2. 找到与任务相关的模块、代码和依赖。
   
   Identify the relevant modules, code, and dependencies.

3. 在新增代码之前，先检查项目是否已经存在相关实现。
   
   Check whether a relevant implementation already exists before introducing new code.

4. 优先采用满足需求的最小、安全修改。
   
   Prefer the smallest safe change that satisfies the requirement.

5. 除非任务明确要求，否则不要改变现有行为。
   
   Preserve existing behavior unless the task explicitly requires changing it.

6. 不要进行与当前任务无关的重构。
   
   Do not perform unrelated refactoring.

7. 不要仅为了改善代码风格而修改无关文件。
   
   Do not modify unrelated files merely for stylistic improvements.

当需求存在歧义时：

When requirements are ambiguous:

- 明确指出歧义。
  
  Identify the ambiguity.

- 如果可以安全地做出合理假设，则说明假设并继续。
  
  If a safe and reasonable assumption can be made, state the assumption and proceed.

- 如果歧义可能导致完全不同的实现，应先向用户确认。
  
  If the ambiguity could materially change the implementation, ask the user before proceeding.


---

## 4. 代码安全 / Code Safety

在进行可能具有破坏性的修改之前：

Before making potentially destructive changes:

- 检查受影响的代码。
  
  Inspect the affected code.

- 理解相关依赖关系。
  
  Understand the relevant dependencies.

- 检查 Git 工作区状态。
  
  Check the Git working tree status.

- 避免覆盖用户已有的修改。
  
  Avoid overwriting existing user changes.

除非用户明确要求，否则绝对不要丢弃、重置或覆盖用户已有的修改。

Never discard, reset, or overwrite existing user changes unless explicitly requested.

除非获得明确授权，否则不要使用具有破坏性的 Git 命令。

Do not use destructive Git commands without explicit authorization.

例如 / Examples:

- `git reset --hard`
- `git checkout --`
- `git clean`
- force push


---

## 5. 验证 / Verification

完成代码修改后：

After making code changes:

1. 优先运行与当前修改最直接相关的测试。
   
   Run the smallest and most relevant tests first.

2. 在适当情况下运行相关的构建、Lint、类型检查或其他验证命令。
   
   Run relevant build, lint, type-check, or other validation commands when appropriate.

3. 确认实际实现确实满足用户要求。
   
   Verify that the implementation actually satisfies the user's requirements.

4. 明确说明已经执行了哪些测试，以及哪些测试没有执行。
   
   Clearly report which tests were run and which tests were not run.

没有实际执行的测试，不得声称测试已经通过。

Never claim that a test passed if it was not actually executed.


---

## 6. 项目上下文维护 / Project Context Maintenance

`AI_CONTEXT.md` 是本项目所有 AI Agent 共用的持久化项目记忆。

`AI_CONTEXT.md` is the shared persistent project memory for all AI agents.

当一次任务产生对未来 Agent 有长期价值的信息时，应更新 `AI_CONTEXT.md`。

Update `AI_CONTEXT.md` when a task produces information that is likely to be useful to future agents.

适合记录的信息包括：

Examples of information worth recording:

- 重要的架构决策 / Important architectural decisions
- 项目架构变化 / Architectural changes
- 新增的重要依赖 / Important new dependencies
- 构建或部署方式变化 / Changes to build or deployment procedures
- 重要业务规则 / Important business rules
- 已知限制 / Known limitations
- 尚未解决的重要技术问题 / Important unresolved technical issues
- 重要的已完成或进行中的工作 / Significant completed or ongoing work
- 项目当前开发方向的重大变化 / Significant changes in development direction

不要因为每一次代码修改都更新 `AI_CONTEXT.md`。

Do not update `AI_CONTEXT.md` after every minor code change.

不要把聊天记录复制到 `AI_CONTEXT.md`。

Do not copy conversation transcripts into `AI_CONTEXT.md`.

不要记录没有长期价值的临时推理过程。

Do not record temporary reasoning that has no long-term value.

保持 `AI_CONTEXT.md` 简洁、准确、当前有效。

Keep `AI_CONTEXT.md` concise, accurate, and current.

当已有信息过期时，应优先修改或删除旧信息，而不是无限追加历史记录。

When information becomes outdated, update or remove it instead of continuously appending historical information.


---

## 7. Session 独立性 / Session Independence

任何任务都应该能够在没有之前 AI 对话历史的情况下继续进行。

Every task should remain understandable and continuable without access to previous AI conversation history.

不要依赖类似以下信息：

Do not rely on statements such as:

- “如之前所讨论的……”
  / "As discussed earlier..."

- “我前面已经说过……”
  / "As I mentioned above..."

- “之前的 Agent 知道……”
  / "The previous agent knows..."

- “参考上一个 Session……”
  / "Refer to the previous session..."

如果某项重要信息未来仍然需要使用，应将其记录在适当的项目文件中。

If important information is needed for future work, record it in an appropriate project file.

一个 AI Session 的结束，不代表项目上下文的结束。

The end of an AI session does not mean the end of project context.


---

## 8. 多 Agent 协作 / Multi-Agent Collaboration

本项目可能由多个不同的 AI Coding Agent 共同开发。

This repository may be developed by multiple different AI coding agents.

例如 / Examples:

- Qoder
- Codex
- Claude Code
- Cursor
- 其他兼容的 AI Coding Agent / Other compatible AI coding agents

所有 Agent 共享相同的项目文件和 `AI_CONTEXT.md`。

All agents share the same project files and `AI_CONTEXT.md`.

不要为不同 AI 厂商创建互相独立的项目记忆。

Do not create separate competing project memories for different AI vendors.

开始工作之前：

Before starting work:

- 读取最新的 `AI_CONTEXT.md`；
  
  Read the latest `AI_CONTEXT.md`.

- 检查 Git 工作区状态；
  
  Check Git working tree status.

- 检查近期相关修改。
  
  Inspect recent relevant changes.

完成重要工作后：

After completing significant work:

- 在必要时更新 `AI_CONTEXT.md`；
  
  Update `AI_CONTEXT.md` when necessary.

- 确保项目处于其他 Agent 可以继续理解和工作的状态。
  
  Leave the project in a state that another agent can understand and continue.

必须假设：

Always assume:

> 当前 Agent 完成工作后，另一个完全不同的 Agent 可能会继续这个项目。
>
> Another completely different AI agent may continue this project after the current agent finishes.


---

## 9. Git 感知 / Git Awareness

Git 历史是理解项目上下文的重要信息来源。

Git history is an important source of project context.

在有帮助的情况下：

When useful:

- 查看最近的 Commit / Inspect recent commits
- 查看与当前任务相关的修改 / Inspect changes related to the current task
- 通过 Commit 信息理解项目开发历史 / Use commit messages to understand development history

除非用户明确要求，否则不要修改或重写 Git 历史。

Do not modify or rewrite Git history unless explicitly requested.

除非项目工作流程明确要求，否则不要擅自 Commit。

Do not create commits unless explicitly required by the project workflow or requested by the user.


---

## 10. 信息可靠性 / Information Quality

绝对不要编造项目事实。

Never invent project facts.

如果某项信息未知，应标记为：

If information is unknown, mark it as:

`UNKNOWN`

如果某项信息只是根据现有代码推测出来的，而不是已经确认的事实，应明确区分。

If information is inferred rather than confirmed, clearly distinguish the inference from confirmed facts.

优先使用以下信息作为事实依据：

Prefer the following sources as factual evidence:

- 实际源代码 / Actual source code
- 实际配置 / Actual configuration
- 测试结果 / Test results
- Git 历史 / Git history
- 项目文档 / Project documentation

不要用猜测代替事实。

Do not replace facts with assumptions.


---

## 11. 任务结束与交接 / Completion and Handoff

完成一个重要任务之前：

Before ending a significant task:

1. 验证实现结果。
   
   Verify the implementation.

2. 确认还有哪些工作没有完成。
   
   Identify unfinished work.

3. 确认是否存在已知问题或风险。
   
   Identify known issues or risks.

4. 如果项目状态发生重要变化，更新 `AI_CONTEXT.md`。
   
   Update `AI_CONTEXT.md` if the project state changed materially.

5. 用简洁的方式说明：
   
   Briefly report:

   - 完成了什么 / What was completed
   - 没有完成什么 / What remains incomplete
   - 是否存在需要后续 Agent 注意的问题 / Issues that future agents should be aware of

下一位 AI Agent 应当能够仅依靠：

The next AI agent should be able to continue using only:

- 项目代码 / Project source code
- `AI_CONTEXT.md`
- `AGENTS.md`
- 相关项目文档 / Relevant project documentation

而不需要依赖当前 Agent 的历史聊天记录。

without requiring access to the current agent's conversation history.