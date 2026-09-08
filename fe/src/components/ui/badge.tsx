import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "success" | "warning" | "danger" | "info" | "outline";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
        variant === "default" && "border-border bg-secondary text-foreground",
        variant === "success" && "border-success/30 bg-success/15 text-success",
        variant === "warning" && "border-warning/30 bg-warning/15 text-warning",
        variant === "danger" && "border-destructive/30 bg-destructive/15 text-destructive",
        variant === "info" && "border-info/30 bg-info/15 text-info",
        variant === "outline" && "border-border text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
