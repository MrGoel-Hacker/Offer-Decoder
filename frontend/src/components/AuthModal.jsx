import { X } from "lucide-react";
import { toast } from "sonner";
import { GoogleButton, useAuth } from "@/lib/auth";
import { errMsg } from "@/lib/api";

export const AuthModal = ({ open, onClose, onDone, title = "Sign in to continue", subtitle }) => {
  const { login } = useAuth();
  if (!open) return null;

  const handle = async (credential) => {
    try {
      const user = await login(credential);
      toast.success(`Signed in as ${user.name}.`);
      onDone ? onDone(user) : onClose();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4" onClick={onClose} data-testid="auth-modal">
      <div className="card w-full max-w-sm !p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="font-display text-lg font-bold text-[var(--text)]">{title}</h2>
            <p className="mt-1 text-sm text-[var(--text-dim)]">
              {subtitle || "One tap with Google. Your decoded result stays exactly as it is - it is only saved once you are in."}
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="text-[var(--text-dim)] hover:text-[var(--text)]" data-testid="auth-modal-close">
            <X size={18} />
          </button>
        </div>
        <div className="mt-5 flex justify-center">
          <GoogleButton onCredential={handle} />
        </div>
        <p className="mt-4 text-xs leading-relaxed text-[var(--text-dim)]">
          We store your name, email and Google ID so your saved reports belong to you. See our <a href="/privacy" className="underline">privacy page</a>.
        </p>
      </div>
    </div>
  );
};
