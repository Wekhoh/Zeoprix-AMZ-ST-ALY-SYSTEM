"use client";
/**
 * <ToastProvider> + useToast()
 * 轻量右上通知（default / success / warning / error）+ 自动消失
 */
import * as React from "react";
import { createPortal } from "react-dom";
import { clsx } from "clsx";
import {
	AlertTriangle,
	CheckCircle2,
	Info,
	X,
	XCircle,
	type LucideIcon,
} from "lucide-react";

export type ToastTone = "default" | "success" | "warning" | "error";

export interface ToastInput {
	title: string;
	description?: string;
	tone?: ToastTone;
	duration?: number;
}

interface Toast {
	id: string;
	title: string;
	description?: string;
	tone: ToastTone;
	duration: number;
}

interface ToastContextValue {
	push: (toast: ToastInput) => void;
	dismiss: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function useToast() {
	const ctx = React.useContext(ToastContext);
	if (!ctx) throw new Error("useToast 必须在 <ToastProvider> 内使用");
	return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
	const [toasts, setToasts] = React.useState<Toast[]>([]);
	const [mounted, setMounted] = React.useState(false);

	React.useEffect(() => {
		setMounted(true);
	}, []);

	const dismiss = React.useCallback((id: string) => {
		setToasts((prev) => prev.filter((t) => t.id !== id));
	}, []);

	const push = React.useCallback(
		(input: ToastInput) => {
			const id = Math.random().toString(36).slice(2);
			const toast: Toast = {
				id,
				title: input.title,
				description: input.description,
				tone: input.tone ?? "default",
				duration: input.duration ?? 4000,
			};
			setToasts((prev) => [...prev, toast]);
			window.setTimeout(() => dismiss(id), toast.duration);
		},
		[dismiss],
	);

	return (
		<ToastContext.Provider value={{ push, dismiss }}>
			{children}
			{mounted &&
				createPortal(
					<div
						className="fixed top-4 right-4 z-50 flex w-80 flex-col gap-2"
						role="region"
						aria-label="通知"
					>
						{toasts.map((t) => (
							<ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
						))}
					</div>,
					document.body,
				)}
		</ToastContext.Provider>
	);
}

const toneMap: Record<
	ToastTone,
	{ Icon: LucideIcon; border: string; iconClass: string }
> = {
	default: { Icon: Info, border: "border-border", iconClass: "text-fg-muted" },
	success: {
		Icon: CheckCircle2,
		border: "border-success/40",
		iconClass: "text-success-fg",
	},
	warning: {
		Icon: AlertTriangle,
		border: "border-warning/40",
		iconClass: "text-warning-fg",
	},
	error: {
		Icon: XCircle,
		border: "border-error/40",
		iconClass: "text-error-fg",
	},
};

function ToastItem({
	toast,
	onDismiss,
}: {
	toast: Toast;
	onDismiss: () => void;
}) {
	const { Icon, border, iconClass } = toneMap[toast.tone];
	return (
		<div
			role="status"
			className={clsx(
				"flex items-start gap-3 p-3",
				"rounded-md border bg-bg-elevated",
				border,
			)}
		>
			<Icon
				className={clsx("mt-0.5 h-5 w-5 shrink-0", iconClass)}
				aria-hidden="true"
			/>
			<div className="min-w-0 flex-1">
				<div className="text-sm font-medium text-fg leading-tight">
					{toast.title}
				</div>
				{toast.description && (
					<div className="mt-1 text-xs text-fg-muted leading-relaxed">
						{toast.description}
					</div>
				)}
			</div>
			<button
				type="button"
				onClick={onDismiss}
				aria-label="关闭"
				className="shrink-0 text-fg-subtle transition-colors hover:text-fg"
			>
				<X className="h-4 w-4" aria-hidden="true" />
			</button>
		</div>
	);
}
