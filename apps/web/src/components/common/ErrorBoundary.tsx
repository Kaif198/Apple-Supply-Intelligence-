"use client";

import * as React from "react";
import { ErrorState } from "@/components/common/States";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <ErrorState
            error={this.state.error}
            onRetry={() => this.setState({ error: null })}
          />
        )
      );
    }
    return this.props.children;
  }
}
