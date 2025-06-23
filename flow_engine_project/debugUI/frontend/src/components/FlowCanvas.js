import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { useDebugStore } from '../store/debugStore';
import { ZoomIn, ZoomOut, RotateCcw, Maximize2 } from 'lucide-react';

const FlowCanvas = () => {
  const svgRef = useRef();
  const {
    debugInfo,
    executionResult,
    selectedSection,
    canvasData,
    selectedNode,
    setSelectedNode,
    setCanvasData
  } = useDebugStore();
  
  const [zoomLevel, setZoomLevel] = useState(1);

  useEffect(() => {
    if (debugInfo && executionResult) {
      renderFlowGraph();
    }
  }, [debugInfo, executionResult]);

  const renderFlowGraph = () => {
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous content

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Create main group for zoom/pan
    const mainGroup = svg.append("g").attr("class", "main-group");

    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 3])
      .on("zoom", (event) => {
        mainGroup.attr("transform", event.transform);
        setZoomLevel(event.transform.k);
      });

    svg.call(zoom);

    // Define arrow markers
    svg.append("defs").selectAll("marker")
      .data(["arrow", "arrow-active"])
      .enter().append("marker")
      .attr("id", d => d)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 15)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("class", d => d === "arrow-active" ? "fill-blue-600" : "fill-gray-400");

    // Process debug info to create nodes and edges
    const { nodes, edges } = processDebugInfo();

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30));

    // Create edges
    const link = mainGroup.append("g")
      .attr("class", "edges")
      .selectAll("line")
      .data(edges)
      .enter().append("line")
      .attr("class", d => `canvas-edge ${d.active ? 'active' : ''}`)
      .attr("stroke-width", d => d.active ? 3 : 1)
      .attr("marker-end", d => `url(#${d.active ? 'arrow-active' : 'arrow'})`);

    // Create edge labels for askWhen conditions
    const edgeLabels = mainGroup.append("g")
      .attr("class", "edge-labels")
      .selectAll("text")
      .data(edges.filter(d => d.askWhen))
      .enter().append("text")
      .attr("class", "text-xs fill-gray-600")
      .attr("text-anchor", "middle")
      .text(d => d.askWhen.length > 20 ? d.askWhen.substring(0, 20) + "..." : d.askWhen);

    // Create nodes
    const node = mainGroup.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(nodes)
      .enter().append("g")
      .attr("class", "node-group")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Add node shapes based on type
    node.each(function(d) {
      const group = d3.select(this);
      
      if (d.type === 'section') {
        // Rectangle for sections
        group.append("rect")
          .attr("class", `canvas-node section ${d.executed ? 'executed' : ''}`)
          .attr("width", 120)
          .attr("height", 60)
          .attr("x", -60)
          .attr("y", -30)
          .attr("rx", 5);
      } else if (d.type === 'question') {
        // Circle for questions
        group.append("circle")
          .attr("class", `canvas-node question ${d.executed ? 'executed' : ''}`)
          .attr("r", 25);
      } else if (d.type === 'action') {
        // Hexagon for actions
        const hexagon = d3.symbol().type(d3.symbolTriangle).size(800);
        group.append("path")
          .attr("class", `canvas-node action ${d.executed ? 'executed' : ''}`)
          .attr("d", hexagon);
      }
    });

    // Add node labels
    node.append("text")
      .attr("class", "text-sm font-medium fill-gray-800")
      .attr("text-anchor", "middle")
      .attr("dy", ".35em")
      .text(d => d.name.length > 15 ? d.name.substring(0, 15) + "..." : d.name);

    // Add step numbers for executed nodes
    node.filter(d => d.step)
      .append("circle")
      .attr("class", "fill-blue-600")
      .attr("r", 12)
      .attr("cx", 40)
      .attr("cy", -25);

    node.filter(d => d.step)
      .append("text")
      .attr("class", "text-xs font-bold fill-white")
      .attr("text-anchor", "middle")
      .attr("x", 40)
      .attr("y", -20)
      .text(d => d.step);

    // Add click handlers
    node.on("click", (event, d) => {
      setSelectedNode(d);
      event.stopPropagation();
    });

    // Update positions on simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      edgeLabels
        .attr("x", d => (d.source.x + d.target.x) / 2)
        .attr("y", d => (d.source.y + d.target.y) / 2);

      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Store canvas data for other components
    setCanvasData({ nodes, edges });
  };

  const processDebugInfo = () => {
    if (!debugInfo || !debugInfo.traversalPath) {
      return { nodes: [], edges: [] };
    }

    const nodes = [];
    const edges = [];
    const nodeMap = new Map();

    // Process traversal path to create nodes
    debugInfo.traversalPath.forEach((step, index) => {
      if (!nodeMap.has(step.nodeId)) {
        nodes.push({
          id: step.nodeId,
          name: step.nodeName || step.nodeId,
          type: step.nodeType.toLowerCase(),
          executed: true,
          step: index + 1,
          details: step.details,
          duration: step.duration
        });
        nodeMap.set(step.nodeId, true);
      }
    });

    // Process condition evaluations to create edges
    debugInfo.conditionEvaluations?.forEach(condition => {
      edges.push({
        source: condition.sourceNode,
        target: condition.targetNode,
        askWhen: condition.askWhen,
        result: condition.result,
        active: condition.result,
        variables: condition.variables
      });
    });

    return { nodes, edges };
  };

  const handleZoomIn = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().scaleBy, 1.5
    );
  };

  const handleZoomOut = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().scaleBy, 1 / 1.5
    );
  };

  const handleReset = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().transform,
      d3.zoomIdentity
    );
  };

  const handleFitToScreen = () => {
    if (!canvasData || canvasData.nodes.length === 0) return;
    
    const svg = d3.select(svgRef.current);
    const bounds = svg.node().getBBox();
    const fullWidth = svgRef.current.clientWidth;
    const fullHeight = svgRef.current.clientHeight;
    
    const width = bounds.width;
    const height = bounds.height;
    const midX = bounds.x + width / 2;
    const midY = bounds.y + height / 2;
    
    if (width === 0 || height === 0) return;
    
    const scale = Math.min(fullWidth / width, fullHeight / height) * 0.9;
    const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];
    
    svg.transition().call(
      d3.zoom().transform,
      d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
    );
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Canvas Header */}
      <div className="flex items-center justify-between p-4 bg-white border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Flow Visualization</h2>
          {selectedSection && (
            <p className="text-sm text-gray-500">
              Section: {selectedSection.sectionName}
            </p>
          )}
        </div>
        
        {/* Canvas Controls */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500">
            Zoom: {Math.round(zoomLevel * 100)}%
          </span>
          <div className="flex space-x-1">
            <button
              onClick={handleZoomIn}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={handleReset}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded"
              title="Reset View"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={handleFitToScreen}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded"
              title="Fit to Screen"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Canvas Area */}
      <div className="flex-1 relative">
        {!debugInfo ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 text-gray-400">
                <svg fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V8zm0 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1v-2z" clipRule="evenodd" />
                </svg>
              </div>
              <p className="text-gray-500">No flow execution to visualize</p>
              <p className="text-sm text-gray-400 mt-1">
                Run a flow execution to see the visualization
              </p>
            </div>
          </div>
        ) : (
          <svg
            ref={svgRef}
            className="w-full h-full cursor-move"
            onClick={() => setSelectedNode(null)}
          />
        )}
      </div>
    </div>
  );
};

export default FlowCanvas; 