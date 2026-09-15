/** A cell address in a rectangular grid, zero-based. */
export interface CellPosition {
  readonly row: number;
  readonly col: number;
}

/** The number of rows and columns in a grid. */
export interface GridSize {
  readonly rows: number;
  readonly cols: number;
}

type Move = (position: CellPosition, size: GridSize) => CellPosition;

const MOVES: Readonly<Record<string, Move>> = {
  ArrowLeft: (position) => ({ row: position.row, col: position.col - 1 }),
  ArrowRight: (position) => ({ row: position.row, col: position.col + 1 }),
  ArrowUp: (position) => ({ row: position.row - 1, col: position.col }),
  ArrowDown: (position) => ({ row: position.row + 1, col: position.col }),
  Home: (position) => ({ row: position.row, col: 0 }),
  End: (position, size) => ({ row: position.row, col: size.cols - 1 }),
};

/** Clamp an index into 0..last. */
function clampIndex(value: number, last: number): number {
  return Math.min(Math.max(value, 0), Math.max(last, 0));
}

/** The cell a navigation key moves focus to, clamped at the edges; null for any other key. */
export function moveCell(
  position: CellPosition,
  key: string,
  size: GridSize,
): CellPosition | null {
  const move = MOVES[key];
  if (move === undefined) return null;
  const next = move(position, size);
  return {
    row: clampIndex(next.row, size.rows - 1),
    col: clampIndex(next.col, size.cols - 1),
  };
}
