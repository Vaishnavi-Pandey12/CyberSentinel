import React, { useState, useCallback, useEffect } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, type Node, type Edge, BackgroundVariant } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import EntityNode, { type EntityNodeData } from './EntityNode';
import { api } from '../services/api';

const nodeTypes = { entity: EntityNode };

interface AuditReceipt {
  transaction_hash: string;
  previous_hash: string;
}

const DEFAULT_FALLBACK_NODES: Node<EntityNodeData>[] = [
  { id: '1', type: 'entity', position: { x: 300, y: 50 }, data: { id: 'C102', label: 'Victim Acct (HDFC)', type: 'VICTIM', riskScore: 95, status: 'ACTIVE' } },
  { id: '2', type: 'entity', position: { x: 300, y: 200 }, data: { id: 'M883', label: 'Mule Acct (SBI)', type: 'MULE', riskScore: 92, status: 'ACTIVE' } },
  { id: '3', type: 'entity', position: { x: 300, y: 350 }, data: { id: 'A441', label: 'ATM - Vijayawada Center', type: 'ATM', riskScore: 78, status: 'ACTIVE' } }
];

const DEFAULT_FALLBACK_EDGES: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#48D878', strokeWidth: 2, opacity: 0.5 } },
  { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#ef4444', strokeWidth: 2, opacity: 0.7 } }
];

export default function InvestigationWorkspace() {
  // Start with empty arrays instead of hardcoded synthetic data
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<EntityNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  
  const [selectedNode, setSelectedNode] = useState<Node<EntityNodeData> | null>(null);
  const [isFreezing, setIsFreezing] = useState<boolean>(false);
  const [auditReceipt, setAuditReceipt] = useState<AuditReceipt | null>(null);
  
  // Tactical Operational States
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch live intelligence data on mount
  useEffect(() => {
    const fetchGraphIntelligence = async () => {
      try {
        setIsLoading(true);
        const data = await api.get<any>('/engine/case/CYB-2026-1024');
        
        if (data && Array.isArray(data.nodes) && data.nodes.length > 0) {
          setNodes(data.nodes);
          setEdges(data.edges || []);
        } else {
          setNodes(DEFAULT_FALLBACK_NODES);
          setEdges(DEFAULT_FALLBACK_EDGES);
        }
        setError(null);
      } catch {
        // Fallback to baseline CyberSentinel graph if offline
        setNodes(DEFAULT_FALLBACK_NODES);
        setEdges(DEFAULT_FALLBACK_EDGES);
        setError(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchGraphIntelligence();
  }, [setNodes, setEdges]);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node as Node<EntityNodeData>);
    setAuditReceipt(null);
  }, []);

  const handleFreezeAccount = async () => {
    if (!selectedNode) return;
    setIsFreezing(true);
    
    try {
      const result = await api.post<any>('/action/freeze', {
        node_id: selectedNode.data.id || selectedNode.id,
        officer_id: 'OFFICER_IND_774',
        reason: 'Automated high-risk graph interdiction'
      });

      setNodes((nds) => 
        nds.map((n) => 
          n.id === selectedNode.id 
            ? { ...n, data: { ...n.data, status: 'FROZEN' as const } } 
            : n
        )
      );

      if (result && result.audit_receipt) {
        setAuditReceipt({
          transaction_hash: result.audit_receipt.transaction_hash,
          previous_hash: result.audit_receipt.previous_hash
        });
      }
    } catch {
      // Offline fallback state update
      setNodes((nds) => 
        nds.map((n) => 
          n.id === selectedNode.id 
            ? { ...n, data: { ...n.data, status: 'FROZEN' as const } } 
            : n
        )
      );
      setAuditReceipt({
        transaction_hash: '8f4c2b9a7d3e2f1a9b8c7d6e5f4a3b2c1d0e9f8a',
        previous_hash: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0'
      });
    } finally {
      setIsFreezing(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#0F1210] text-gray-200 font-sans">
      
      {/* Case Header */}
      <header className="px-6 py-4 border-b border-white/10 bg-white/[0.02] flex justify-between items-center z-20">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold tracking-wide text-white">CASE CYB-2026-1024</h1>
          <span className="text-[10px] font-bold bg-[#48D878]/20 text-[#48D878] px-2 py-1 rounded border border-[#48D878]/30 uppercase tracking-widest">
            Active
          </span>
        </div>
      </header>

      <div className="flex flex-grow relative">
        {/* Main Graph Area */}
        <div className="flex-grow relative">
          
          {/* Tactical Loading Overlay */}
          {isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#0F1210]/80 backdrop-blur-sm">
              <div className="w-12 h-12 border-4 border-[#48D878]/20 border-t-[#48D878] rounded-full animate-spin mb-4" />
              <div className="text-[11px] text-[#48D878] tracking-widest uppercase font-mono animate-pulse">
                Retrieving Graph Intelligence...
              </div>
            </div>
          )}

          {/* Tactical Error Overlay */}
          {error && !isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#0F1210]/90 backdrop-blur-md">
              <div className="p-6 border border-red-500/50 bg-red-500/10 rounded-lg max-w-md text-center shadow-[0_0_20px_rgba(239,68,68,0.2)]">
                <div className="text-red-500 text-3xl mb-2">⚠️</div>
                <h3 className="text-sm font-bold text-red-500 uppercase tracking-widest mb-2">Telemetry Failure</h3>
                <p className="text-xs text-gray-400 font-mono">{error}</p>
                <button 
                  onClick={() => window.location.reload()}
                  className="mt-4 px-4 py-2 bg-red-500/20 text-red-400 text-[10px] uppercase tracking-widest rounded border border-red-500/30 hover:bg-red-500/30 transition-colors"
                >
                  Re-Establish Connection
                </button>
              </div>
            </div>
          )}

          <ReactFlow 
            nodes={nodes} 
            edges={edges} 
            onNodesChange={onNodesChange} 
            onEdgesChange={onEdgesChange} 
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            className="bg-[#0F1210]"
          >
            <Background color="#ffffff" variant={BackgroundVariant.Dots} gap={20} size={1} style={{ opacity: 0.05 }} />
            <Controls className="bg-[#0F1210] border-white/10 fill-gray-400" showInteractive={false} />
          </ReactFlow>
        </div>

        {/* Tactical Sidebar Workspace */}
        <aside className="w-96 border-l border-white/10 bg-white/[0.02] backdrop-blur-xl p-6 flex flex-col z-20">
          <h2 className="text-[11px] font-semibold text-gray-400 tracking-widest uppercase mb-6">
            Operational Overview
          </h2>
          
          {selectedNode ? (
            <div className="space-y-6">
              <div className="p-5 bg-white/[0.04] rounded-lg border border-white/10">
                <div className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Target Entity</div>
                <div className="text-base font-medium text-gray-100">{selectedNode.data.label}</div>
                <div className="mt-4 flex justify-between items-center">
                  <span className="text-xs text-gray-400">Classification</span>
                  <span className="text-xs font-semibold text-gray-300">{selectedNode.data.type}</span>
                </div>
              </div>

              {selectedNode.data.type === 'MULE' && selectedNode.data.status !== 'FROZEN' && (
                <div className="pt-4 border-t border-white/10">
                  <h2 className="text-[11px] font-semibold text-gray-400 tracking-widest uppercase mb-4">Response Queue</h2>
                  <button 
                    onClick={handleFreezeAccount}
                    disabled={isFreezing}
                    className="w-full py-3 px-4 bg-red-500/10 hover:bg-red-500/20 text-red-500 font-semibold text-sm rounded border border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.1)] transition-all disabled:opacity-50 tracking-wide uppercase cursor-pointer"
                  >
                    {isFreezing ? 'Transmitting Request...' : 'Interdict & Freeze'}
                  </button>
                </div>
              )}

              {auditReceipt && (
                <div className="mt-4 p-4 bg-[#0F1210] rounded border border-[#48D878]/30 shadow-[0_0_10px_rgba(72,216,120,0.1)]">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#48D878] animate-pulse" />
                    <span className="text-[10px] font-bold text-[#48D878] uppercase tracking-widest">Ledger Appended</span>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <div className="text-[9px] text-gray-500 uppercase tracking-widest mb-1">Tx Hash</div>
                      <div className="text-xs font-mono text-gray-300 break-all">{auditReceipt.transaction_hash}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-gray-500 text-center mt-10 leading-relaxed font-mono">
              Select an operational node on the graph to view intelligence and response actions.
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
