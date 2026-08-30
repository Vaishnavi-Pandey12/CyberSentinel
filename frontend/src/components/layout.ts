import type { Node, Edge } from '@xyflow/react';

export function getLayoutedElements<T extends Node>(
  nodes: T[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
): { nodes: T[]; edges: Edge[] } {
  const isHorizontal = direction === 'LR';

  // Group nodes by hierarchical tier
  const tierVictims: T[] = [];
  const tierMules: T[] = [];
  const tierATMs: T[] = [];
  const tierOthers: T[] = [];

  nodes.forEach((node) => {
    const rawType = String((node.data as any)?.type || node.type || '').toUpperCase();
    if (rawType.includes('VICTIM')) tierVictims.push(node);
    else if (rawType.includes('MULE') || rawType.includes('DEVICE')) tierMules.push(node);
    else if (rawType.includes('ATM')) tierATMs.push(node);
    else tierOthers.push(node);
  });

  const layoutedNodes: T[] = [];

  const arrangeTier = (tierNodes: T[], level: number) => {
    const total = tierNodes.length;
    const spacingX = 260; // horizontal gap between nodes
    const startX = Math.max(100, 400 - (total * spacingX) / 2);

    tierNodes.forEach((node, idx) => {
      const x = isHorizontal ? level * 300 + 100 : startX + idx * spacingX;
      const y = isHorizontal ? 120 + idx * 180 : level * 200 + 80;

      layoutedNodes.push({
        ...node,
        position: { x, y }
      });
    });
  };

  arrangeTier(tierVictims, 0);
  arrangeTier(tierMules, 1);
  arrangeTier(tierATMs, 2);
  arrangeTier(tierOthers, 1.5);

  return { nodes: layoutedNodes, edges };
}
