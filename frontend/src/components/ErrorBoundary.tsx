import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex items-center justify-center min-h-[200px] p-6">
          <div className="bg-one-surface border border-kpi-bad/30 rounded-xl p-6 max-w-md text-center">
            <p className="text-kpi-bad font-semibold text-sm mb-2">Hiba történt</p>
            <p className="text-one-grey text-xs mb-4">{this.state.error.message}</p>
            <button
              className="px-4 py-1.5 rounded-pill bg-one-turq text-[#04201f] text-xs font-semibold"
              onClick={() => this.setState({ error: null })}
            >
              Újrapróbálás
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
