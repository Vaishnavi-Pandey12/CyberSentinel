import type { Node, Edge } from '@xyflow/react';

export function getLayoutedElements<T extends Node>(
  nodes: T[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
): { nodes: T[]; edges: Edge[] } {
  const isHorizontal = direction === 'LR';
  
  const layoutedNodes = nodes.map((node, idx) => {
    if (node.position && (node.position.x !== 0 || node.position.y !== 0)) {
      return node;
    }
    const nodeType = String((node.data as any)?.type || node.type || '').toUpperCase();
    let level = 1;
    if (nodeType === 'VICTIM') level = 0;
    else if (nodeType === 'MULE') level = 1;
    else if (nodeType === 'DEVICE') level = 1;
    else if (nodeType === 'ATM') level = 2;

    const x = isHorizontal ? level * 250 : 150 + (idx % 3) * 180;
    const y = isHorizontal ? 100 + (idx * 100) : 50 + level * 160;

    return {
      ...node,
      position: { x, y }
    };
  });

  return { nodes: layoutedNodes, edges };
}
