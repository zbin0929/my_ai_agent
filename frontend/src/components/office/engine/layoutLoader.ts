/**
 * 布局加载器
 * 加载 Pixel Agents 风格的办公室布局
 */

import type { TileType as TileTypeVal, FurnitureInstance, SpriteData } from "./types";
import { TILE_SIZE, TileType } from "./types";

export interface LayoutData {
  cols: number;
  rows: number;
  tiles: TileTypeVal[];
  tileColors: Array<{ h: number; s: number; b: number; c: number } | null>;
  furniture: Array<{
    uid: string;
    type: string;
    col: number;
    row: number;
  }>;
}

// 家具精灵图缓存
const furnitureSpriteCache = new Map<string, SpriteData>();

/**
 * 加载布局 JSON
 */
export async function loadLayout(): Promise<LayoutData> {
  try {
    const response = await fetch("/office/default-layout-1.json");
    const data = await response.json();
    return {
      cols: data.cols,
      rows: data.rows,
      tiles: data.tiles,
      tileColors: data.tileColors || [],
      furniture: data.furniture || [],
    };
  } catch (e) {
    console.error("Failed to load layout:", e);
    // 返回默认布局
    return createDefaultLayout();
  }
}

/**
 * 创建默认布局
 */
function createDefaultLayout(): LayoutData {
  const cols = 20;
  const rows = 12;
  const tiles: TileTypeVal[] = [];
  
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (r < 2) {
        tiles.push(TileType.WALL);
      } else {
        tiles.push((r + c) % 2 === 0 ? TileType.FLOOR_1 : TileType.FLOOR_2);
      }
    }
  }
  
  return {
    cols,
    rows,
    tiles,
    tileColors: [],
    furniture: [],
  };
}

/**
 * 将布局转换为 2D 瓦片数组
 */
export function layoutToTileMap(layout: LayoutData): TileTypeVal[][] {
  const tileMap: TileTypeVal[][] = [];
  for (let r = 0; r < layout.rows; r++) {
    const row: TileTypeVal[] = [];
    for (let c = 0; c < layout.cols; c++) {
      const idx = r * layout.cols + c;
      row.push(layout.tiles[idx] as TileTypeVal);
    }
    tileMap.push(row);
  }
  return tileMap;
}

/**
 * 从 PNG 加载家具精灵图
 */
async function loadFurnitureSprite(type: string): Promise<SpriteData> {
  // 处理带方向的类型，如 "SOFA_SIDE:left"
  const [baseType, variant] = type.split(":");
  const isMirrored = variant === "left";
  
  const cached = furnitureSpriteCache.get(type);
  if (cached) return cached;
  
  // 解析文件夹名和文件名
  // 例如: "DESK_FRONT" -> folder: "DESK", file: "DESK_FRONT"
  // 例如: "PC_FRONT_OFF" -> folder: "PC", file: "PC_FRONT_OFF"
  // 例如: "SOFA_SIDE" -> folder: "SOFA", file: "SOFA_SIDE"
  let folderName = baseType;
  let filename = baseType;
  
  // 移除方向后缀来获取文件夹名
  const suffixes = ["_FRONT", "_BACK", "_SIDE", "_FRONT_OFF", "_SIDE_OFF"];
  for (const suffix of suffixes) {
    if (baseType.endsWith(suffix)) {
      folderName = baseType.slice(0, -suffix.length);
      break;
    }
  }
  
  // 特殊处理: SMALL_TABLE_FRONT -> SMALL_TABLE/SMALL_TABLE_FRONT
  // WOODEN_CHAIR_SIDE -> WOODEN_CHAIR/WOODEN_CHAIR_SIDE
  
  try {
    const img = new Image();
    img.crossOrigin = "anonymous";
    
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error(`Failed to load ${filename}`));
      img.src = `/office/furniture/${folderName}/${filename}.png`;
    });
    
    // 提取像素数据
    const canvas = document.createElement("canvas");
    canvas.width = img.width;
    canvas.height = img.height;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(img, 0, 0);
    
    const imageData = ctx.getImageData(0, 0, img.width, img.height);
    const data = imageData.data;
    const sprite: SpriteData = [];
    
    for (let y = 0; y < img.height; y++) {
      const row: string[] = [];
      for (let x = 0; x < img.width; x++) {
        const idx = (y * img.width + x) * 4;
        const r = data[idx];
        const g = data[idx + 1];
        const b = data[idx + 2];
        const a = data[idx + 3];
        
        if (a < 128) {
          row.push("");
        } else {
          row.push(`#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`);
        }
      }
      sprite.push(row);
    }
    
    // 如果需要镜像
    const finalSprite = isMirrored ? sprite.map(row => [...row].reverse()) : sprite;
    furnitureSpriteCache.set(type, finalSprite);
    return finalSprite;
  } catch (e) {
    // 返回占位符精灵图
    const placeholder = createPlaceholderSprite(32, 32);
    furnitureSpriteCache.set(type, placeholder);
    return placeholder;
  }
}

/**
 * 创建占位符精灵图
 */
function createPlaceholderSprite(w: number, h: number): SpriteData {
  const sprite: SpriteData = [];
  for (let y = 0; y < h; y++) {
    const row: string[] = [];
    for (let x = 0; x < w; x++) {
      if (x === 0 || x === w - 1 || y === 0 || y === h - 1) {
        row.push("#666666");
      } else {
        row.push("");
      }
    }
    sprite.push(row);
  }
  return sprite;
}

/**
 * 加载布局中的所有家具实例
 */
export async function loadFurnitureInstances(
  layout: LayoutData
): Promise<FurnitureInstance[]> {
  const instances: FurnitureInstance[] = [];
  
  for (const f of layout.furniture) {
    const sprite = await loadFurnitureSprite(f.type);
    const isMirrored = f.type.includes(":left");
    
    instances.push({
      uid: f.uid,
      type: f.type,
      col: f.col,
      row: f.row,
      sprite,
      x: f.col * TILE_SIZE,
      y: f.row * TILE_SIZE - (sprite.length - TILE_SIZE),
      zY: f.row * TILE_SIZE + TILE_SIZE,
      mirrored: isMirrored,
    });
  }
  
  return instances;
}
