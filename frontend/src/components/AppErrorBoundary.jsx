import React from "react";

export class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error(error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="panel" role="alert">
          <h1>Error inesperado</h1>
          <p>Recarga pagina o contacta a administracion.</p>
        </section>
      );
    }

    return this.props.children;
  }
}
