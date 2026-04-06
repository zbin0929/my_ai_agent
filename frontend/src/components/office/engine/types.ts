/**
 * Office Canvas 渲染引擎类型定义
 * 参考 Pixel Agents 项目架构
 */

export const TILE_SIZE = 16;
export const DEFAULT_COLS = 20;
export const DEFAULT_ROWS = 12;

export const TileType = {
  WALL: 0,
  FLOOR_1: 1,
  FLOOR_2: 2,
  FLOOR_3: 3,
  FLOOR_4: 4,
  FLOOR_5: 5,
  FLOOR_6: 6,
  FLOOR_7: 7,
  FLOOR_8: 8,
  FLOOR_9: 9,
  VOID: 255,
} as const;
export type TileType = (typeof TileType)[keyof typeof TileType];

export const CharacterState = {
  IDLE: "idle",
  WALK: "walk",
  TYPE: "type",
  READ: "read",
} as const;
export type CharacterState = (typeof CharacterState)[keyof typeof CharacterState];

export const Direction = {
  DOWN: 0,
  LEFT: 1,
  RIGHT: 2,
  UP: 3,
} as const;
export type Direction = (typeof Direction)[keyof typeof Direction];

/** 2D array of hex color strings */
export type SpriteData = string[][];

export interface Character {
  id: string;
  name: string;
  state: CharacterState;
  dir: Direction;
  x: number;
  y: number;
  tileCol: number;
  tileRow: number;
  path: Array<{ col: number; row: number }>;
  moveProgress: number;
  palette: number;
  frame: number;
  frameTimer: number;
  isActive: boolean;
  speech?: string;
  speechTimer: number;
}

export interface Seat {
  uid: string;
  seatCol: number;
  seatRow: number;
  facingDir: Direction;
  assigned: boolean;
  agentId?: string;
}

export interface FurnitureInstance {
  uid: string;
  type: string;
  col: number;
  row: number;
  sprite: SpriteData;
  x: number;
  y: number;
  zY: number;
  mirrored?: boolean;
}

export interface OfficeLayout {
  cols: number;
  rows: number;
  tiles: TileType[];
  furniture: Array<{
    uid: string;
    type: string;
    col: number;
    row: number;
  }>;
}

export interface CharacterSprites {
  walk: Record<Direction, SpriteData[]>;
  typing: Record<Direction, SpriteData[]>;
  reading: Record<Direction, SpriteData[]>;
  idle: Record<Direction, SpriteData[]>;
}
