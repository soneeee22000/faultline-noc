import config from "../../../config/intended_config.json";
import { iconAt } from "../lib/icons";
import { round, svgCircle, svgLine, svgText } from "../lib/svg";
import {
  LOGICAL_EDGES,
  type LogicalEdge,
  NODE_LAYOUT,
  type NodeRoles,
  buildTopology,
} from "../viewmodel/topology";

/** Nodes and cables from `config/intended_config.json`, resolved at build time. */
export const TOPOLOGY = buildTopology(config);

const BEND_RATIO = 0.12;
const LABEL_OFFSET = 1.9;
const UPPER_HALF = 0.5;
const ICON_SCALE = 1.4;
const MIDPOINT_WEIGHT = 0.5;
const END_WEIGHT = 0.25;

/** How to draw a topology inside a given SVG box. */
export interface TopologyOptions {
  readonly width: number;
  readonly height: number;
  readonly padX: number;
  readonly padY: number;
  readonly nodeRadius: number;
  readonly showInterfaces: boolean;
  readonly roleOf: (node: string) => NodeRoles | null;
}

interface Point {
  readonly x: number;
  readonly y: number;
}

/** A node's position in the SVG box. */
function position(node: string, options: TopologyOptions): Point {
  const layout = NODE_LAYOUT[node];
  if (layout === undefined) throw new Error(`No layout for node ${node}`);
  return {
    x: options.padX + layout.x * (options.width - 2 * options.padX),
    y: options.padY + layout.y * (options.height - 2 * options.padY),
  };
}

/** Physical cables as straight hairlines. */
function cablesMarkup(options: TopologyOptions): string {
  return TOPOLOGY.cables
    .map(([a, b]) => {
      const from = position(a, options);
      const to = position(b, options);
      return svgLine(from.x, from.y, to.x, to.y, "svg-cable");
    })
    .join("");
}

/** A logical dependency as a curve bent off the straight line, with its interface label. */
function edgeMarkup(edge: LogicalEdge, options: TopologyOptions): string {
  const from = position(edge.from, options);
  const to = position(edge.to, options);
  const bend = Math.hypot(to.x - from.x, to.y - from.y) * BEND_RATIO;
  const angle = Math.atan2(to.y - from.y, to.x - from.x);
  const control = {
    x: (from.x + to.x) / 2 + Math.sin(angle) * bend,
    y: (from.y + to.y) / 2 - Math.cos(angle) * bend,
  };
  const path = `<path class="svg-dep" d="M${round(from.x)} ${round(from.y)} Q${round(control.x)} ${round(control.y)} ${round(to.x)} ${round(to.y)}"/>`;
  if (!options.showInterfaces) return path;
  const labelX =
    END_WEIGHT * from.x + MIDPOINT_WEIGHT * control.x + END_WEIGHT * to.x;
  const labelY =
    END_WEIGHT * from.y + MIDPOINT_WEIGHT * control.y + END_WEIGHT * to.y;
  return `${path}${svgText(labelX, labelY - options.nodeRadius / 2, edge.label, "svg-mono svg-mono--small svg-muted svg-halo surface-detail", "middle")}`;
}

/** The node circle class for its scenario role. */
function nodeClass(roles: NodeRoles | null): string {
  if (roles === null) return "svg-node";
  if (roles.root) return "svg-node svg-node--root";
  return roles.symptom
    ? "svg-node svg-node--symptom"
    : "svg-node svg-node--other";
}

/** One node: circle, name label, and glyphs for root cause and injection target. */
function nodeMarkup(node: string, options: TopologyOptions): string {
  const point = position(node, options);
  const roles = options.roleOf(node);
  const circle = svgCircle(
    point.x,
    point.y,
    options.nodeRadius,
    nodeClass(roles),
  );
  return `<g>${circle}${roleGlyphs(roles, point, options.nodeRadius)}${nodeLabel(node, point, options)}</g>`;
}

/** Glyphs for the root cause (inside the node) and the injection target (beside it). */
function roleGlyphs(
  roles: NodeRoles | null,
  point: Point,
  radius: number,
): string {
  const glyph = radius * ICON_SCALE;
  const root =
    roles?.root === true
      ? iconAt(
          "diamond",
          point.x - glyph / 2,
          point.y - glyph / 2,
          glyph,
          "svg-icon svg-icon--ground svg-icon--filled",
        )
      : "";
  const injection =
    roles?.injectionTarget === true
      ? iconAt(
          "message-square-warning",
          point.x - radius - glyph - 2,
          point.y - glyph / 2,
          glyph,
          "svg-icon svg-icon--trip",
        )
      : "";
  return `${root}${injection}`;
}

/** The node name: above nodes in the upper half so it clears the curves below them, else below. */
function nodeLabel(
  node: string,
  point: Point,
  options: TopologyOptions,
): string {
  const upper = (NODE_LAYOUT[node]?.y ?? 1) < UPPER_HALF;
  const offset = options.nodeRadius * LABEL_OFFSET;
  const y = upper ? point.y - offset : point.y + offset + options.nodeRadius;
  return svgText(
    point.x,
    y,
    node,
    "svg-mono svg-mono--small svg-halo",
    "middle",
  );
}

/** Cables, dependencies and nodes for a topology box. */
export function topologyMarkup(options: TopologyOptions): string {
  const edges = LOGICAL_EDGES.map((edge) => edgeMarkup(edge, options)).join("");
  const nodes = TOPOLOGY.nodes
    .map((node) => nodeMarkup(node, options))
    .join("");
  return `${cablesMarkup(options)}${edges}${nodes}`;
}
