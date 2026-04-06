/**
 * 精灵图加载器
 * 从 PNG 图片提取角色动画帧
 */

import type { SpriteData, CharacterSprites, Direction } from "./types";
import { Direction as Dir } from "./types";

const CHAR_WIDTH = 16;
const CHAR_HEIGHT = 32;
const FRAMES_PER_ROW = 7; // walk0, walk1, walk2, type0, type1, read0, read1

interface LoadedCharacterData {
  down: SpriteData[];
  up: SpriteData[];
  right: SpriteData[];
}

let loadedCharacters: LoadedCharacterData[] | null = null;
const spriteCache = new Map<string, CharacterSprites>();

/**
 * 从 PNG 图片提取像素数据
 */
async function extractSpritesFromImage(
  img: HTMLImageElement
): Promise<LoadedCharacterData> {
  const canvas = document.createElement("canvas");
  canvas.width = img.width;
  canvas.height = img.height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(img, 0, 0);

  const extractFrame = (
    startX: number,
    startY: number
  ): SpriteData => {
    const imageData = ctx.getImageData(startX, startY, CHAR_WIDTH, CHAR_HEIGHT);
    const data = imageData.data;
    const sprite: SpriteData = [];

    for (let y = 0; y < CHAR_HEIGHT; y++) {
      const row: string[] = [];
      for (let x = 0; x < CHAR_WIDTH; x++) {
        const idx = (y * CHAR_WIDTH + x) * 4;
        const r = data[idx];
        const g = data[idx + 1];
        const b = data[idx + 2];
        const a = data[idx + 3];

        if (a < 10) {
          row.push("");
        } else {
          const hex = `#${r.toString(16).padStart(2, "0")}${g
            .toString(16)
            .padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
          row.push(hex);
        }
      }
      sprite.push(row);
    }
    return sprite;
  };

  // 每个角色图片布局: 3行(down/up/right) x 7列(walk0,walk1,walk2,type0,type1,read0,read1)
  const down: SpriteData[] = [];
  const up: SpriteData[] = [];
  const right: SpriteData[] = [];

  for (let i = 0; i < FRAMES_PER_ROW; i++) {
    down.push(extractFrame(i * CHAR_WIDTH, 0));
    up.push(extractFrame(i * CHAR_WIDTH, CHAR_HEIGHT));
    right.push(extractFrame(i * CHAR_WIDTH, CHAR_HEIGHT * 2));
  }
  
  return { down, up, right };
}

/**
 * 水平翻转精灵图
 */
function flipSpriteHorizontal(sprite: SpriteData): SpriteData {
  return sprite.map((row) => [...row].reverse());
}

/**
 * 加载所有角色精灵图
 */
export async function loadCharacterSprites(): Promise<void> {
  if (loadedCharacters) return;
  const characters: LoadedCharacterData[] = [];
  const charCount = 6;

  for (let i = 0; i < charCount; i++) {
    try {
      const img = new Image();
      img.crossOrigin = "anonymous";
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = reject;
        img.src = `/office/characters/char_${i}.png`;
      });
      const data = await extractSpritesFromImage(img);
      characters.push(data);
    } catch (e) {
      // 创建空白占位符
      const empty: SpriteData = Array(CHAR_HEIGHT)
        .fill(null)
        .map(() => Array(CHAR_WIDTH).fill(""));
      characters.push({
        down: Array(7).fill(empty),
        up: Array(7).fill(empty),
        right: Array(7).fill(empty),
      });
    }
  }

  loadedCharacters = characters;
  spriteCache.clear();
}

/**
 * 获取角色精灵图集
 */
export function getCharacterSprites(paletteIndex: number): CharacterSprites {
  const cacheKey = `${paletteIndex}`;
  const cached = spriteCache.get(cacheKey);
  if (cached) return cached;

  if (!loadedCharacters) {
    // 返回空白占位符
    const empty: SpriteData = Array(CHAR_HEIGHT)
      .fill(null)
      .map(() => Array(CHAR_WIDTH).fill(""));
    const emptySet = [empty, empty, empty, empty];
    const emptyPair = [empty, empty];
    return {
      walk: {
        [Dir.DOWN]: emptySet,
        [Dir.UP]: emptySet,
        [Dir.RIGHT]: emptySet,
        [Dir.LEFT]: emptySet,
      },
      typing: {
        [Dir.DOWN]: emptyPair,
        [Dir.UP]: emptyPair,
        [Dir.RIGHT]: emptyPair,
        [Dir.LEFT]: emptyPair,
      },
      reading: {
        [Dir.DOWN]: emptyPair,
        [Dir.UP]: emptyPair,
        [Dir.RIGHT]: emptyPair,
        [Dir.LEFT]: emptyPair,
      },
      idle: {
        [Dir.DOWN]: [empty],
        [Dir.UP]: [empty],
        [Dir.RIGHT]: [empty],
        [Dir.LEFT]: [empty],
      },
    };
  }

  const char = loadedCharacters[paletteIndex % loadedCharacters.length];
  const d = char.down;
  const u = char.up;
  const rt = char.right;
  const flip = flipSpriteHorizontal;

  const sprites: CharacterSprites = {
    walk: {
      [Dir.DOWN]: [d[0], d[1], d[2], d[1]],
      [Dir.UP]: [u[0], u[1], u[2], u[1]],
      [Dir.RIGHT]: [rt[0], rt[1], rt[2], rt[1]],
      [Dir.LEFT]: [flip(rt[0]), flip(rt[1]), flip(rt[2]), flip(rt[1])],
    },
    typing: {
      [Dir.DOWN]: [d[3], d[4]],
      [Dir.UP]: [u[3], u[4]],
      [Dir.RIGHT]: [rt[3], rt[4]],
      [Dir.LEFT]: [flip(rt[3]), flip(rt[4])],
    },
    reading: {
      [Dir.DOWN]: [d[5], d[6]],
      [Dir.UP]: [u[5], u[6]],
      [Dir.RIGHT]: [rt[5], rt[6]],
      [Dir.LEFT]: [flip(rt[5]), flip(rt[6])],
    },
    idle: {
      [Dir.DOWN]: [d[0], d[0]], // 两帧相同，用于呼吸动画
      [Dir.UP]: [u[0], u[0]],
      [Dir.RIGHT]: [rt[0], rt[0]],
      [Dir.LEFT]: [flip(rt[0]), flip(rt[0])],
    },
  };

  spriteCache.set(cacheKey, sprites);
  return sprites;
}

/**
 * 获取已加载的角色数量
 */
export function getLoadedCharacterCount(): number {
  return loadedCharacters ? loadedCharacters.length : 6;
}
