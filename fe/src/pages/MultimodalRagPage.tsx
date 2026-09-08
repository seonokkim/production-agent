import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BotMessageSquare,
  Image as ImageIcon,
  Link2,
  Loader2,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Send,
  Trash2,
  Video,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/api/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { AgentCitation, AgentRun } from "@/types";

type ChatTurn = {
  id: string;
  role: "user" | "assistant";
  text: string;
  run?: AgentRun;
  stages?: Array<{ stage: string; message_en: string }>;
  streaming?: boolean;
};

const STAGE_ORDER = ["searching", "reading", "grounding_video", "answering"] as const;
const HISTORY_WIDTH_KEY = "rag.historyWidth";
const HISTORY_OPEN_KEY = "rag.historyOpen";
const MIN_HISTORY = 180;
const MAX_HISTORY = 420;
const DEFAULT_HISTORY = 260;

function loadWidth(): number {
  const n = Number(localStorage.getItem(HISTORY_WIDTH_KEY));
  if (Number.isFinite(n) && n >= MIN_HISTORY && n <= MAX_HISTORY) return n;
  return DEFAULT_HISTORY;
}

export function MultimodalRagPage() {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [mediaType, setMediaType] = useState<"any" | "image" | "video">("any");
  const [embeddingProvider, setEmbeddingProvider] = useState<
    "default" | "mock" | "marengo"
  >("default");
  const [projectId, setProjectId] = useState<number | "all">("all");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [activeRun, setActiveRun] = useState<AgentRun | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [attachSceneId, setAttachSceneId] = useState<number | "">("");
  const [liveStages, setLiveStages] = useState<
    Array<{ stage: string; message_en: string }>
  >([]);
  const [historyOpen, setHistoryOpen] = useState(
    () => localStorage.getItem(HISTORY_OPEN_KEY) !== "0",
  );
  const [historyWidth, setHistoryWidth] = useState(loadWidth);
  const dragging = useRef(false);

  const catalog = useQuery({ queryKey: ["agents"], queryFn: api.listAgents });
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.listProjects });
  const conversations = useQuery({
    queryKey: ["agent-conversations"],
    queryFn: api.listAgentConversations,
  });
  const agent = catalog.data?.[0];

  const scenes = useQuery({
    queryKey: ["rag-scenes", projectId, activeRun?.project_id],
    queryFn: async () => {
      const pid =
        typeof projectId === "number"
          ? projectId
          : activeRun?.project_id ?? projects.data?.[0]?.id;
      if (!pid) return [];
      return api.listScenes(pid);
    },
    enabled: Boolean(projects.data?.length),
  });

  useEffect(() => {
    localStorage.setItem(HISTORY_OPEN_KEY, historyOpen ? "1" : "0");
  }, [historyOpen]);

  useEffect(() => {
    localStorage.setItem(HISTORY_WIDTH_KEY, String(historyWidth));
  }, [historyWidth]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const next = Math.min(MAX_HISTORY, Math.max(MIN_HISTORY, e.clientX - 80));
      setHistoryWidth(next);
    };
    const onUp = () => {
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  const startNewChat = () => {
    setConversationId(null);
    setTurns([]);
    setActiveRun(null);
    setSelectedKeys(new Set());
    setLiveStages([]);
    setAttachSceneId("");
  };

  const loadConversation = useCallback(async (id: number) => {
    const detail = await api.getAgentConversation(id);
    setConversationId(detail.id);
    if (detail.project_id != null) setProjectId(detail.project_id);
    if (detail.media_type === "image" || detail.media_type === "video" || detail.media_type === "any") {
      setMediaType(detail.media_type);
    }
    const nextTurns: ChatTurn[] = detail.messages.map((m) => ({
      id: `m-${m.id}`,
      role: m.role === "user" ? "user" : "assistant",
      text: m.content,
      run: m.agent_run ?? undefined,
      stages: m.agent_run?.events.map((e) => ({
        stage: e.stage,
        message_en: e.message_en,
      })),
    }));
    setTurns(nextTurns);
    const lastRun = [...detail.messages]
      .reverse()
      .find((m) => m.agent_run)?.agent_run;
    setActiveRun(lastRun ?? null);
    setSelectedKeys(new Set(lastRun?.citations.map((c) => c.cite_key) ?? []));
    setLiveStages([]);
  }, []);

  const search = useMutation({
    mutationFn: async () => {
      const q = query.trim();
      const userTurn: ChatTurn = {
        id: `u-${Date.now()}`,
        role: "user",
        text: q,
      };
      const assistantId = `a-${Date.now()}`;
      setTurns((prev) => [
        ...prev,
        userTurn,
        {
          id: assistantId,
          role: "assistant",
          text: "",
          streaming: true,
          stages: [],
        },
      ]);
      setLiveStages([]);
      setActiveRun(null);
      setSelectedKeys(new Set());
      setQuery("");

      const run = await api.streamAgentRun(
        {
          query: q,
          media_type: mediaType,
          project_id: projectId === "all" ? null : projectId,
          conversation_id: conversationId,
          embedding_provider:
            embeddingProvider === "default" ? null : embeddingProvider,
        },
        {
          onStage: (stage) => {
            if (stage.conversation_id && !conversationId) {
              setConversationId(stage.conversation_id);
            }
            setLiveStages((prev) => {
              if (prev.some((p) => p.stage === stage.stage)) return prev;
              return [...prev, { stage: stage.stage, message_en: stage.message_en }];
            });
            setTurns((prev) =>
              prev.map((t) =>
                t.id === assistantId
                  ? {
                      ...t,
                      stages: [
                        ...(t.stages || []).filter((s) => s.stage !== stage.stage),
                        { stage: stage.stage, message_en: stage.message_en },
                      ],
                    }
                  : t,
              ),
            );
          },
        },
      );

      if (run.conversation_id) setConversationId(run.conversation_id);
      setActiveRun(run);
      setSelectedKeys(new Set(run.citations.map((c) => c.cite_key)));
      setTurns((prev) =>
        prev.map((t) =>
          t.id === assistantId
            ? {
                ...t,
                text: run.answer_text,
                run,
                streaming: false,
                stages: run.events.map((e) => ({
                  stage: e.stage,
                  message_en: e.message_en,
                })),
              }
            : t,
        ),
      );
      return run;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["agent-conversations"] });
    },
    onError: (err) => {
      toast.error((err as Error).message || "Agent run failed");
      setTurns((prev) =>
        prev.map((t) =>
          t.streaming
            ? {
                ...t,
                streaming: false,
                text: `Error: ${(err as Error).message}`,
              }
            : t,
        ),
      );
    },
  });

  const removeConversation = useMutation({
    mutationFn: (id: number) => api.deleteAgentConversation(id),
    onSuccess: (_data, id) => {
      if (conversationId === id) startNewChat();
      void qc.invalidateQueries({ queryKey: ["agent-conversations"] });
      toast.success("Conversation deleted");
    },
    onError: (err) => toast.error((err as Error).message),
  });

  const attach = useMutation({
    mutationFn: async () => {
      if (!activeRun || attachSceneId === "" || selectedKeys.size === 0) {
        throw new Error("Select citations and a scene first");
      }
      return api.attachAgentRun(activeRun.id, {
        scene_id: Number(attachSceneId),
        cite_keys: [...selectedKeys],
      });
    },
    onSuccess: (res) => {
      toast.success(`Attached ${res.cite_keys.length} cite(s) → scene #${res.scene_id}`);
    },
    onError: (err) => toast.error((err as Error).message),
  });

  const toggleCite = (key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="flex min-h-[70vh] flex-col gap-4">
      <PageHeader
        title={agent?.display_name_en ?? "Multimodal RAG"}
        description={
          agent?.description ??
          "Chat over approved stills and video. Cite → attach into a scene. Never self-approves."
        }
        badge={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">P2 · Agents SDK</Badge>
            <Badge variant="outline">{agent?.display_name_ko ?? "멀티모달 RAG"}</Badge>
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setHistoryOpen((v) => !v)}
          aria-label={historyOpen ? "Collapse history" : "Expand history"}
        >
          {historyOpen ? (
            <PanelLeftClose className="mr-1.5 h-4 w-4" />
          ) : (
            <PanelLeftOpen className="mr-1.5 h-4 w-4" />
          )}
          History
        </Button>
        <span className="text-muted-foreground">Scope</span>
        <select
          className="h-8 rounded-md border border-border bg-background px-2 text-sm"
          value={projectId === "all" ? "all" : String(projectId)}
          onChange={(e) =>
            setProjectId(e.target.value === "all" ? "all" : Number(e.target.value))
          }
        >
          <option value="all">All projects</option>
          {(projects.data || []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        {(["any", "image", "video"] as const).map((m) => (
          <button key={m} type="button" onClick={() => setMediaType(m)}>
            <Badge variant={mediaType === m ? "success" : "outline"}>
              {m === "any" ? "Any media" : m}
            </Badge>
          </button>
        ))}
        <span className="text-muted-foreground">Embed</span>
        {(
          [
            ["default", "Default"],
            ["mock", "Mock"],
            ["marengo", "TwelveLabs"],
          ] as const
        ).map(([value, label]) => (
          <button key={value} type="button" onClick={() => setEmbeddingProvider(value)}>
            <Badge variant={embeddingProvider === value ? "success" : "outline"}>
              {label}
            </Badge>
          </button>
        ))}
        <Badge variant="success">Approved only</Badge>
      </div>

      <div className="flex min-h-[420px] flex-1 overflow-hidden rounded-lg border border-border">
        {historyOpen && (
          <>
            <aside
              className="flex shrink-0 flex-col border-r border-border bg-sidebar/40"
              style={{ width: historyWidth }}
            >
              <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
                <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Conversations
                </span>
                <Button type="button" variant="ghost" size="sm" onClick={startNewChat}>
                  <MessageSquarePlus className="mr-1 h-3.5 w-3.5" />
                  New
                </Button>
              </div>
              <div className="flex-1 overflow-y-auto p-2">
                {!conversations.data?.length && (
                  <p className="px-2 py-6 text-center text-xs text-muted-foreground">
                    No chats yet. Send a message to start one.
                  </p>
                )}
                <ul className="space-y-1">
                  {(conversations.data || []).map((c) => {
                    const active = c.id === conversationId;
                    return (
                      <li key={c.id} className="group relative">
                        <button
                          type="button"
                          onClick={() => void loadConversation(c.id)}
                          className={cn(
                            "w-full rounded-md px-2.5 py-2 text-left transition-colors",
                            active
                              ? "bg-primary/15 text-foreground"
                              : "hover:bg-accent text-muted-foreground hover:text-foreground",
                          )}
                        >
                          <div className="truncate text-sm font-medium text-foreground">
                            {c.title || "New chat"}
                          </div>
                          <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                            {c.preview || `${c.message_count} messages`}
                          </div>
                        </button>
                        <button
                          type="button"
                          className="absolute right-1 top-1 hidden rounded p-1 text-muted-foreground hover:bg-destructive/20 hover:text-destructive group-hover:block"
                          aria-label="Delete conversation"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeConversation.mutate(c.id);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </aside>
            <div
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize history panel"
              className="w-1 shrink-0 cursor-col-resize bg-border/60 transition-colors hover:bg-primary/40"
              onMouseDown={() => {
                dragging.current = true;
                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
              }}
            />
          </>
        )}

        <Card className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-none border-0 shadow-none">
          <CardContent className="flex flex-1 flex-col gap-0 p-0">
            <div className="flex-1 space-y-4 overflow-y-auto p-4">
              {turns.length === 0 && (
                <div className="flex h-full min-h-[240px] flex-col items-center justify-center gap-2 text-center">
                  <BotMessageSquare className="h-9 w-9 text-muted-foreground" />
                  <p className="text-sm font-medium">Ask across approved image + video</p>
                  <p className="max-w-md text-xs text-muted-foreground">
                    Example: Find approved handheld night factory clips with warm practicals;
                    prefer 2–4s beats.
                  </p>
                </div>
              )}

              {turns.map((turn) => (
                <div
                  key={turn.id}
                  className={cn(
                    "flex",
                    turn.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  <div
                    className={cn(
                      "max-w-[90%] rounded-lg px-3 py-2 text-sm",
                      turn.role === "user"
                        ? "bg-primary/20 text-foreground"
                        : "border border-border bg-card",
                    )}
                  >
                    {turn.role === "assistant" &&
                      (turn.stages?.length || turn.streaming) && (
                        <div className="mb-2 flex flex-wrap gap-1.5">
                          {(turn.stages || []).map((s) => (
                            <Badge key={s.stage} variant="outline">
                              {s.stage}
                            </Badge>
                          ))}
                          {turn.streaming && (
                            <Badge variant="outline" className="gap-1">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              running
                            </Badge>
                          )}
                          {turn.run?.runtime && (
                            <Badge variant="outline">{turn.run.runtime}</Badge>
                          )}
                          {turn.run?.embedding_provider && (
                            <Badge variant="outline">
                              emb:{turn.run.embedding_provider}
                            </Badge>
                          )}
                        </div>
                      )}
                    {turn.text ? (
                      <pre className="whitespace-pre-wrap font-sans leading-relaxed">
                        {turn.text}
                      </pre>
                    ) : turn.streaming ? (
                      <p className="text-muted-foreground">
                        {liveStages.at(-1)?.message_en || "Starting agent…"}
                      </p>
                    ) : null}
                    {turn.role === "assistant" && turn.run && !turn.streaming && (
                      <button
                        type="button"
                        className="mt-2 text-xs text-primary underline-offset-2 hover:underline"
                        onClick={() => {
                          setActiveRun(turn.run!);
                          setSelectedKeys(
                            new Set(turn.run!.citations.map((c) => c.cite_key)),
                          );
                        }}
                      >
                        Show cites ({turn.run.citations.length})
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-border p-3">
              {(search.isPending || liveStages.length > 0) && (
                <div className="mb-2 flex flex-wrap gap-1.5">
                  {STAGE_ORDER.map((stage) => {
                    const hit = liveStages.find((s) => s.stage === stage);
                    const skip =
                      stage === "grounding_video" &&
                      activeRun &&
                      !activeRun.citations.some((c) => c.media_type === "video") &&
                      !search.isPending;
                    if (skip && !hit) return null;
                    return (
                      <Badge
                        key={stage}
                        variant={hit ? "success" : "outline"}
                        className={cn(!hit && search.isPending && "opacity-40")}
                      >
                        {stage}
                      </Badge>
                    );
                  })}
                </div>
              )}
              <div className="flex gap-2">
                <Textarea
                  id="multimodal-rag-query"
                  placeholder="Ask the multimodal retriever…"
                  rows={2}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      if (query.trim() && !search.isPending) search.mutate();
                    }
                  }}
                  className="min-h-[64px] resize-none"
                />
                <Button
                  type="button"
                  className="shrink-0 self-end"
                  disabled={!query.trim() || search.isPending}
                  onClick={() => search.mutate()}
                >
                  {search.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                History panel is collapsible & resizable · Enter to send · Attach only
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {activeRun && (
        <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-medium">Citations</h2>
              <span className="text-xs text-muted-foreground">
                {selectedKeys.size} selected · run #{activeRun.id}
                {activeRun.conversation_id
                  ? ` · chat #${activeRun.conversation_id}`
                  : ""}
              </span>
            </div>
            {!activeRun.citations.length ? (
              <Card className="border-dashed">
                <CardContent className="p-6 text-center text-sm text-muted-foreground">
                  No cites for this query. Approve + index more assets, then retry.
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {activeRun.citations.map((c) => (
                  <CitationCard
                    key={c.id}
                    citation={c}
                    selected={selectedKeys.has(c.cite_key)}
                    onToggle={() => toggleCite(c.cite_key)}
                  />
                ))}
              </div>
            )}
          </div>

          <Card>
            <CardContent className="space-y-3 p-4">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Link2 className="h-4 w-4" />
                Attach to scene
              </div>
              <p className="text-xs text-muted-foreground">
                Writes a RetrievalEvent for provenance. Does not generate or approve.
              </p>
              <label className="block text-xs text-muted-foreground" htmlFor="attach-scene">
                Scene
              </label>
              <select
                id="attach-scene"
                className="h-9 w-full rounded-md border border-border bg-background px-2 text-sm"
                value={attachSceneId === "" ? "" : String(attachSceneId)}
                onChange={(e) =>
                  setAttachSceneId(e.target.value ? Number(e.target.value) : "")
                }
              >
                <option value="">Select scene…</option>
                {(scenes.data || []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title} (#{s.id})
                  </option>
                ))}
              </select>
              <Button
                type="button"
                className="w-full"
                disabled={
                  attach.isPending ||
                  !activeRun.citations.length ||
                  selectedKeys.size === 0 ||
                  attachSceneId === ""
                }
                onClick={() => attach.mutate()}
              >
                {attach.isPending ? "Attaching…" : "Attach selected cites"}
              </Button>
              {attach.isSuccess && (
                <Link
                  to={`/scenes/${attach.data.scene_id}`}
                  className="block text-center text-xs text-primary underline-offset-2 hover:underline"
                >
                  Open scene #{attach.data.scene_id} →
                </Link>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function CitationCard({
  citation,
  selected,
  onToggle,
}: {
  citation: AgentCitation;
  selected: boolean;
  onToggle: () => void;
}) {
  const mediaUrl = citation.thumb_url || citation.poster_url;
  const isVideo = citation.media_type === "video";

  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "overflow-hidden rounded-lg border text-left transition-colors",
        selected ? "border-primary/60 bg-primary/5" : "border-border hover:border-white/14",
      )}
    >
      <div className="relative aspect-video bg-black/40">
        {mediaUrl ? (
          isVideo ? (
            <video src={mediaUrl} className="h-full w-full object-contain" muted />
          ) : (
            <img
              src={mediaUrl}
              alt={citation.cite_key}
              className="h-full w-full object-contain"
            />
          )
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            {isVideo ? <Video className="h-7 w-7" /> : <ImageIcon className="h-7 w-7" />}
          </div>
        )}
        <div className="absolute left-2 top-2 flex gap-1">
          <Badge variant="outline">{citation.media_type}</Badge>
          {selected && <Badge variant="success">selected</Badge>}
        </div>
      </div>
      <div className="space-y-1 p-3">
        <div className="text-sm font-medium">
          {citation.cite_key} · asset #{citation.asset_id}
        </div>
        <div className="text-xs text-muted-foreground">
          score {citation.score}
          {citation.t_start != null && citation.t_end != null
            ? ` · ${citation.t_start}s–${citation.t_end}s`
            : ""}
          {citation.segment_note ? ` · ${citation.segment_note}` : ""}
        </div>
      </div>
    </button>
  );
}
