/**
 * Canvas 渲染引擎
 * 负责绘制地板、家具、角色
 */

import type {
  Character,
  FurnitureInstance,
  SpriteData,
  TileType as TileTypeVal,
  Direction,
} from "./types";
import { TILE_SIZE, TileType, CharacterState, Direction as Dir } from "./types";
import { getCharacterSprites } from "./spriteLoader";

// 缓存渲染后的精灵图
const canvasCache = new Map<string, HTMLCanvasElement>();

/**
 * 将 SpriteData 渲染到 Canvas 并缓存
 * 注意：角色精灵图不应该缓存，因为需要动画
 */
function renderSpriteToCanvas(
  sprite: SpriteData,
  zoom: number,
  noCache: boolean = false
): HTMLCanvasElement {
  if (!noCache) {
    const key = JSON.stringify(sprite) + zoom;
    const cached = canvasCache.get(key);
    if (cached) return cached;
  }

  const h = sprite.length;
  const w = h > 0 ? sprite[0].length : 0;
  const canvas = document.createElement("canvas");
  canvas.width = w * zoom;
  canvas.height = h * zoom;
  const ctx = canvas.getContext("2d")!;

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const color = sprite[y][x];
      if (color && color !== "") {
        ctx.fillStyle = color;
        ctx.fillRect(x * zoom, y * zoom, zoom, zoom);
      }
    }
  }

  if (!noCache) {
    const key = JSON.stringify(sprite) + zoom;
    canvasCache.set(key, canvas);
  }
  return canvas;
}

// 地板颜色
const FLOOR_COLORS: Record<number, string> = {
  [TileType.FLOOR_1]: "#c8b898",
  [TileType.FLOOR_2]: "#baa888",
  [TileType.FLOOR_3]: "#a89878",
  [TileType.FLOOR_4]: "#d4c4a8",
  [TileType.FLOOR_5]: "#e0d0b8",
  [TileType.FLOOR_6]: "#b8a888",
  [TileType.FLOOR_7]: "#c0b090",
  [TileType.FLOOR_8]: "#d0c0a0",
  [TileType.FLOOR_9]: "#c8b890",
};

const WALL_COLOR = "#2d2420";
const VOID_COLOR = "#1a1612";

/**
 * 渲染瓦片网格
 */
export function renderTileGrid(
  ctx: CanvasRenderingContext2D,
  tileMap: TileTypeVal[][],
  offsetX: number,
  offsetY: number,
  zoom: number
): void {
  const s = TILE_SIZE * zoom;
  const rows = tileMap.length;
  const cols = rows > 0 ? tileMap[0].length : 0;

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const tile = tileMap[r][c];
      const x = offsetX + c * s;
      const y = offsetY + r * s;

      if (tile === TileType.VOID) {
        ctx.fillStyle = VOID_COLOR;
      } else if (tile === TileType.WALL) {
        ctx.fillStyle = WALL_COLOR;
      } else {
        ctx.fillStyle = FLOOR_COLORS[tile] || FLOOR_COLORS[TileType.FLOOR_1];
      }
      ctx.fillRect(x, y, s, s);

      // 添加网格线
      if (tile !== TileType.VOID && tile !== TileType.WALL) {
        ctx.strokeStyle = "rgba(0,0,0,0.1)";
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, s, s);
      }
    }
  }
}

interface ZDrawable {
  zY: number;
  draw: (ctx: CanvasRenderingContext2D) => void;
}

// 角色颜色调色板
const CHARACTER_COLORS = [
  "#4a9eff", // 蓝色
  "#4ade80", // 绿色
  "#f59e0b", // 橙色
  "#f472b6", // 粉色
  "#a78bfa", // 紫色
  "#fb923c", // 橘色
];

/**
 * 获取角色当前帧的精灵图
 */
function getCharacterSprite(ch: Character, zoom: number): HTMLCanvasElement {
  const sprites = getCharacterSprites(ch.palette);
  let spriteSet: SpriteData[];

  switch (ch.state) {
    case CharacterState.TYPE:
      spriteSet = sprites.typing[ch.dir];
      break;
    case CharacterState.READ:
      spriteSet = sprites.reading[ch.dir];
      break;
    case CharacterState.WALK:
      spriteSet = sprites.walk[ch.dir];
      break;
    default:
      spriteSet = sprites.idle[ch.dir];
  }

  const frameIndex = ch.frame % spriteSet.length;
  const sprite = spriteSet[frameIndex];
  
  // 检查精灵图是否为空（全透明）
  const pixelCount = sprite.reduce((acc, row) => acc + row.filter(p => p && p !== "").length, 0);
  
  if (pixelCount === 0) {
    // 使用简单的彩色像素人物作为后备
    return renderFallbackCharacter(ch.palette, ch.state, ch.frame, zoom);
  }
  
  // 使用精灵图渲染，不缓存以支持动画
  return renderSpriteToCanvas(sprite, zoom, true);
}

/**
 * 渲染后备角色（当精灵图未加载时）
 */
function renderFallbackCharacter(
  palette: number,
  state: CharacterState,
  frame: number,
  zoom: number
): HTMLCanvasElement {
  const w = 16;
  const h = 32;
  const canvas = document.createElement("canvas");
  canvas.width = w * zoom;
  canvas.height = h * zoom;
  const ctx = canvas.getContext("2d")!;
  
  const color = CHARACTER_COLORS[palette % CHARACTER_COLORS.length];
  const skinColor = "#f0b899";
  const hairColor = "#4a3020";
  
  // 打字动画：手臂位置变化
  const isTyping = state === CharacterState.TYPE;
  const armOffset = isTyping ? (frame % 2) : 0;
  
  // 头发
  ctx.fillStyle = hairColor;
  ctx.fillRect(5 * zoom, 2 * zoom, 6 * zoom, 4 * zoom);
  
  // 脸
  ctx.fillStyle = skinColor;
  ctx.fillRect(5 * zoom, 6 * zoom, 6 * zoom, 6 * zoom);
  
  // 眼睛
  ctx.fillStyle = "#000";
  ctx.fillRect(6 * zoom, 8 * zoom, zoom, zoom);
  ctx.fillRect(9 * zoom, 8 * zoom, zoom, zoom);
  
  // 身体
  ctx.fillStyle = color;
  ctx.fillRect(4 * zoom, 12 * zoom, 8 * zoom, 10 * zoom);
  
  // 手臂（打字时会移动）
  ctx.fillStyle = skinColor;
  if (isTyping) {
    // 打字动画：手臂交替上下
    ctx.fillRect(2 * zoom, (14 + armOffset) * zoom, 2 * zoom, 4 * zoom);
    ctx.fillRect(12 * zoom, (14 + (1 - armOffset)) * zoom, 2 * zoom, 4 * zoom);
  } else {
    ctx.fillRect(2 * zoom, 14 * zoom, 2 * zoom, 4 * zoom);
    ctx.fillRect(12 * zoom, 14 * zoom, 2 * zoom, 4 * zoom);
  }
  
  // 腿
  ctx.fillStyle = "#1a4a7a";
  if (state === CharacterState.WALK) {
    const legOffset = frame % 2;
    ctx.fillRect((5 + legOffset) * zoom, 22 * zoom, 3 * zoom, 8 * zoom);
    ctx.fillRect((8 - legOffset) * zoom, 22 * zoom, 3 * zoom, 8 * zoom);
  } else {
    ctx.fillRect(5 * zoom, 22 * zoom, 3 * zoom, 8 * zoom);
    ctx.fillRect(8 * zoom, 22 * zoom, 3 * zoom, 8 * zoom);
  }
  
  return canvas;
}

/**
 * 渲染场景（家具 + 角色，按 Y 排序）
 */
export function renderScene(
  ctx: CanvasRenderingContext2D,
  furniture: FurnitureInstance[],
  characters: Character[],
  offsetX: number,
  offsetY: number,
  zoom: number
): void {
  const drawables: ZDrawable[] = [];

  // 添加家具
  for (const f of furniture) {
    const cached = renderSpriteToCanvas(f.sprite, zoom);
    const fx = offsetX + f.x * zoom;
    const fy = offsetY + f.y * zoom;

    if (f.mirrored) {
      drawables.push({
        zY: f.zY,
        draw: (c) => {
          c.save();
          c.translate(fx + cached.width, fy);
          c.scale(-1, 1);
          c.drawImage(cached, 0, 0);
          c.restore();
        },
      });
    } else {
      drawables.push({
        zY: f.zY,
        draw: (c) => {
          c.drawImage(cached, fx, fy);
        },
      });
    }
  }

  // 添加角色
  for (const ch of characters) {
    const sprite = getCharacterSprite(ch, zoom);
    const cx = offsetX + ch.x * zoom - sprite.width / 2;
    const cy = offsetY + ch.y * zoom - sprite.height + TILE_SIZE * zoom / 2;

    drawables.push({
      zY: ch.y,
      draw: (c) => {
        c.drawImage(sprite, cx, cy);

        // 绘制名字标签
        if (ch.name) {
          c.font = `${10 * zoom}px "Press Start 2P", monospace`;
          c.textAlign = "center";
          c.fillStyle = "rgba(0,0,0,0.7)";
          const textY = cy - 4 * zoom;
          const textWidth = c.measureText(ch.name).width;
          c.fillRect(
            cx + sprite.width / 2 - textWidth / 2 - 2 * zoom,
            textY - 8 * zoom,
            textWidth + 4 * zoom,
            10 * zoom
          );
          c.fillStyle = "#fff";
          c.fillText(ch.name, cx + sprite.width / 2, textY);
        }

        // 绘制对话气泡
        if (ch.speech && ch.speechTimer > 0) {
          renderSpeechBubble(c, cx + sprite.width / 2, cy - 20 * zoom, ch.speech, zoom);
        }
      },
    });
  }

  // 按 Y 排序绘制
  drawables.sort((a, b) => a.zY - b.zY);
  for (const d of drawables) {
    d.draw(ctx);
  }
}

/**
 * 绘制对话气泡
 */
function renderSpeechBubble(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  text: string,
  zoom: number
): void {
  const fontSize = 8 * zoom;
  ctx.font = `${fontSize}px "Press Start 2P", monospace`;
  const maxWidth = 120 * zoom;
  const padding = 6 * zoom;
  const lineHeight = fontSize * 1.4;

  // 文本换行
  const words = text.split("");
  const lines: string[] = [];
  let currentLine = "";

  for (const char of words) {
    const testLine = currentLine + char;
    const metrics = ctx.measureText(testLine);
    if (metrics.width > maxWidth - padding * 2) {
      lines.push(currentLine);
      currentLine = char;
    } else {
      currentLine = testLine;
    }
  }
  if (currentLine) lines.push(currentLine);

  const bubbleWidth = Math.min(
    maxWidth,
    Math.max(...lines.map((l) => ctx.measureText(l).width)) + padding * 2
  );
  const bubbleHeight = lines.length * lineHeight + padding * 2;

  // 气泡背景
  const bx = x - bubbleWidth / 2;
  const by = y - bubbleHeight;

  ctx.fillStyle = "#fff";
  ctx.strokeStyle = "#333";
  ctx.lineWidth = zoom;

  // 圆角矩形
  const radius = 4 * zoom;
  ctx.beginPath();
  ctx.moveTo(bx + radius, by);
  ctx.lineTo(bx + bubbleWidth - radius, by);
  ctx.quadraticCurveTo(bx + bubbleWidth, by, bx + bubbleWidth, by + radius);
  ctx.lineTo(bx + bubbleWidth, by + bubbleHeight - radius);
  ctx.quadraticCurveTo(
    bx + bubbleWidth,
    by + bubbleHeight,
    bx + bubbleWidth - radius,
    by + bubbleHeight
  );
  // 尖角
  ctx.lineTo(x + 6 * zoom, by + bubbleHeight);
  ctx.lineTo(x, by + bubbleHeight + 6 * zoom);
  ctx.lineTo(x - 6 * zoom, by + bubbleHeight);
  ctx.lineTo(bx + radius, by + bubbleHeight);
  ctx.quadraticCurveTo(bx, by + bubbleHeight, bx, by + bubbleHeight - radius);
  ctx.lineTo(bx, by + radius);
  ctx.quadraticCurveTo(bx, by, bx + radius, by);
  ctx.closePath();

  ctx.fill();
  ctx.stroke();

  // 文本
  ctx.fillStyle = "#333";
  ctx.textAlign = "left";
  for (let i = 0; i < lines.length; i++) {
    ctx.fillText(lines[i], bx + padding, by + padding + (i + 1) * lineHeight - 4 * zoom);
  }
}

/**
 * 清除精灵缓存
 */
export function clearSpriteCache(): void {
  canvasCache.clear();
}
