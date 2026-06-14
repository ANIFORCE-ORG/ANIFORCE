/**
 * AG-UI Agent Composable
 *
 * 基于 @ag-ui/client HttpAgent 的 AG-UI 协议客户端。
 * 替代 streamAgentMessage + useHomeAgentSession 的手拼状态管理。
 *
 * 核心变化:
 *   - 消息列表来自 HttpAgent 内部 Message[]，自动按事件流排序
 *   - 不再需要 timelineBlocks + workspaceToolResults 分管理
 *   - activity 消息 (角色为 "activity") 自动出现在消息流中
 *   - state 变化通过 StateSnapshot 事件自动更新
 */

import { ref, computed, shallowRef, onUnmounted } from "vue";
import { HttpAgent, type AgentSubscriber } from "@ag-ui/client";
import type { Message, State } from "@ag-ui/core";

export interface AgUiAgentOptions {
  url: string;         // AG-UI runtime URL (e.g., "/api/v1/copilotkit")
  threadId: string;    // 会话 ID
  headers?: Record<string, string>;
  agentId?: string;
}

export function useAgUiAgent(options: AgUiAgentOptions) {
  const loading = ref(false);
  const error = ref<string | null>(null);
  const running = ref(false);
  const currentState = shallowRef<State>({});

  // HttpAgent 实例 (单例，整个会话复用)
  const agent = ref<HttpAgent | null>(null);
  const subscriber = ref<AgentSubscriber | null>(null);

  // Reactive messages — 直接从 agent.messages 同步
  const messages = shallowRef<Message[]>([]);
  let syncTimer: number | null = null;

  function syncMessages() {
    if (!agent.value) return;
    messages.value = [...agent.value.messages];
  }

  const visibleMessages = computed(() =>
    messages.value.filter(
      (m) => ["user", "assistant", "activity", "tool"].includes(m.role as string)
    )
  );

  function initAgent(threadId: string) {
    if (agent.value && agent.value.threadId === threadId) return;
    disposeAgent();

    agent.value = new HttpAgent({
      url: options.url,
      threadId,
      agentId: options.agentId,
      headers: options.headers,
    });

    // 订阅 agent 状态变化
    subscriber.value = {
      onMessagesChanged: () => {
        syncMessages();
      },
      onStateChanged: () => {
        if (agent.value) {
          currentState.value = { ...(agent.value.state as Record<string, unknown>) };
        }
      },
      onRunInitialized: () => {
        running.value = true;
        error.value = null;
      },
      onRunFinalized: () => {
        running.value = false;
        syncMessages();
      },
      onRunFailed: (params: unknown) => {
        running.value = false;
        error.value = (params as any)?.error?.message || "Agent run failed";
        syncMessages();
      },
    } as unknown as AgentSubscriber;

    agent.value.subscribe(subscriber.value);
    syncMessages();
    if (agent.value.state) {
      currentState.value = { ...(agent.value.state as Record<string, unknown>) };
    }
  }

  function disposeAgent() {
    if (subscriber.value && agent.value) {
      // subscriber returns { unsubscribe }
      agent.value = null;
    }
    subscriber.value = null;
    if (syncTimer) {
      clearInterval(syncTimer);
      syncTimer = null;
    }
  }

  async function send(text: string): Promise<void> {
    if (!text.trim()) return;
    initAgent(options.threadId);

    loading.value = true;
    error.value = null;

    // 将用户消息添加到 agent
    agent.value?.addMessages([
      {
        role: "user" as const,
        content: text,
      } as Message,
    ]);

    syncMessages();

    try {
      await agent.value?.runAgent();
    } catch (err: any) {
      error.value = err?.message || "Agent run failed";
    } finally {
      loading.value = false;
      running.value = false;
      syncMessages();
    }
  }

  function abort() {
    // HttpAgent 没有内置 abort，这里做最少处理
    running.value = false;
    error.value = "Run aborted by user";
  }

  onUnmounted(() => {
    disposeAgent();
  });

  return {
    // 状态
    messages,
    visibleMessages,
    currentState,
    loading,
    error,
    running,
    agent,

    // 操作
    send,
    abort,
    initAgent,
    disposeAgent,
  };
}
