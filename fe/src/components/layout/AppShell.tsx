import type { ReactNode } from "react";
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BotMessageSquare,
  Clapperboard,
  GalleryVerticalEnd,
  LayoutDashboard,
  Menu,
  X,
} from "lucide-react";
import { api } from "@/api/client";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projects", icon: Clapperboard, end: false },
  { to: "/assets", label: "Assets", icon: GalleryVerticalEnd, end: false },
  { to: "/search-agent", label: "Multimodal RAG", icon: BotMessageSquare, end: false },
];

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const ready = useQuery({
    queryKey: ["ready"],
    queryFn: api.ready,
    refetchInterval: 15000,
    retry: false,
  });

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-5">
        <div className="text-base font-semibold tracking-tight">Production Agent</div>
        <div className="mt-0.5 text-xs text-muted-foreground">AI Creation Workflow</div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-3">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
                isActive && "bg-primary/15 text-foreground",
              )
            }
          >
            <item.icon className="h-4 w-4 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border p-4">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Environment
        </div>
        {ready.isError && (
          <div className="text-xs text-muted-foreground">Backend unavailable</div>
        )}
        {ready.data && (
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Backend</span>
              <Badge variant="success">Connected</Badge>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Generation</span>
              <Badge variant="outline">{ready.data.generation_provider}</Badge>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">LLM</span>
              <Badge variant="outline">{ready.data.llm_provider}</Badge>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Embedding</span>
              <Badge variant="outline">{ready.data.embedding_provider}</Badge>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="sticky top-0 hidden h-screen w-[232px] shrink-0 border-r border-border bg-sidebar lg:block">
        <SidebarBody />
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            className="absolute inset-0 bg-black/50"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
          />
          <aside className="relative z-50 h-full w-[232px] bg-sidebar shadow-xl">
            <div className="absolute right-2 top-2">
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close menu"
                onClick={() => setOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <SidebarBody onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-border px-4 py-3 lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Open menu"
            onClick={() => setOpen(true)}
          >
            <Menu className="h-4 w-4" />
          </Button>
          <span className="text-sm font-semibold">Production Agent</span>
        </div>
        <main className="mx-auto w-full max-w-shell flex-1 px-4 py-6 md:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
