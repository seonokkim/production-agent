declare module "@dagrejs/dagre" {
  const dagre: {
    graphlib: {
      Graph: new () => unknown;
    };
    layout: (graph: unknown) => void;
  };
  export default dagre;
}
