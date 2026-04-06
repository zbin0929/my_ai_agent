"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import { useOfficeStore } from "@/store/officeStore";
import {
  loadCharacterSprites,
  renderTileGrid,
  renderScene,
  loadLayout,
  layoutToTileMap,
  loadFurnitureInstances,
  TILE_SIZE,
  CharacterState,
  Direction,
  type Character,
  type FurnitureInstance,
  type TileType as TileTypeVal,
  type LayoutData,
} from "./engine";

const ZOOM = 2;
const FRAME_INTERVAL = 1000 / 30; // 30 FPS

export function CanvasOffice() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);
  const frameCountRef = useRef<number>(0); // 本地帧计数器
  
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [tileMap, setTileMap] = useState<TileTypeVal[][] | null>(null);
  const [furniture, setFurniture] = useState<FurnitureInstance[]>([]);
  const [spritesLoaded, setSpritesLoaded] = useState(false);
  const [, forceUpdate] = useState(0); // 强制重渲染

  const { agents, tick, tickFrame } = useOfficeStore();

  // 加载布局和资源
  useEffect(() => {
    async function init() {
      try {
        // 加载角色精灵图
        await loadCharacterSprites();
        setSpritesLoaded(true);
        
        // 加载布局
        const layoutData = await loadLayout();
        setLayout(layoutData);
        setTileMap(layoutToTileMap(layoutData));
        
        // 加载家具
        const furnitureInstances = await loadFurnitureInstances(layoutData);
        setFurniture(furnitureInstances);
      } catch (e) {
        console.error("Failed to initialize office:", e);
      }
    }
    init();
  }, []);

  // 转换 agents 为 Character 格式
  const agentList = Object.values(agents);
  
  // 坐标转换: 旧坐标系(960x540) -> 新瓦片坐标系
  const OLD_W = 960;
  const OLD_H = 540;
  const LAYOUT_COLS = layout?.cols || 21;
  const LAYOUT_ROWS = layout?.rows || 22;
  
  const convertCoords = (oldX: number, oldY: number) => ({
    x: (oldX / OLD_W) * LAYOUT_COLS * TILE_SIZE,
    y: (oldY / OLD_H) * LAYOUT_ROWS * TILE_SIZE,
  });
  
  const characters: Character[] = agentList.length > 0
    ? agentList.map((agent, index) => {
        const coords = convertCoords(agent.x, agent.y);
        // 使用本地帧计数器驱动动画
        const frame = frameCountRef.current;
        const animFrame = agent.anim === "type" || agent.anim === "walk" 
          ? Math.floor(frame / 8) % 4  // 打字/走路动画 (较快)
          : Math.floor(frame / 20) % 2;  // 空闲呼吸动画 (较慢)
        return {
          id: agent.id,
          name: agent.name,
          state:
            agent.anim === "type"
              ? CharacterState.TYPE
              : agent.anim === "walk"
              ? CharacterState.WALK
              : CharacterState.IDLE,
          dir: agent.facing === "up" ? Direction.UP : Direction.DOWN,
          x: coords.x,
          y: coords.y,
          tileCol: Math.floor(coords.x / TILE_SIZE),
          tileRow: Math.floor(coords.y / TILE_SIZE),
          path: [],
          moveProgress: 0,
          palette: index % 6,
          frame: animFrame,
          frameTimer: 0,
          isActive: agent.anim === "type",
          speech: agent.speech ?? undefined,
          speechTimer: agent.speech ? 3 : 0,
        };
      })
    : [
        // 项目主管 - 坐在沙发上 (右侧休息区，沙发前排)
        {
          id: "manager",
          name: "项目主管",
          state: CharacterState.IDLE,
          dir: Direction.DOWN,
          x: 15 * TILE_SIZE,
          y: 14 * TILE_SIZE,
          tileCol: 15,
          tileRow: 14,
          path: [],
          moveProgress: 0,
          palette: 0,
          frame: Math.floor(frameCountRef.current / 8) % 4,
          frameTimer: 0,
          isActive: false,
          speech: undefined,
          speechTimer: 0,
        },
        // 员工1 - 左上角电脑桌
        {
          id: "worker1",
          name: "文字助手",
          state: CharacterState.TYPE,
          dir: Direction.UP,
          x: 4 * TILE_SIZE,
          y: 13 * TILE_SIZE,
          tileCol: 4,
          tileRow: 13,
          path: [],
          moveProgress: 0,
          palette: 1,
          frame: Math.floor(frameCountRef.current / 8) % 4,
          frameTimer: 0,
          isActive: true,
          speech: undefined,
          speechTimer: 0,
        },
        // 员工2 - 左上角第二个电脑桌
        {
          id: "worker2",
          name: "效率秘书",
          state: CharacterState.TYPE,
          dir: Direction.UP,
          x: 8 * TILE_SIZE,
          y: 13 * TILE_SIZE,
          tileCol: 8,
          tileRow: 13,
          path: [],
          moveProgress: 0,
          palette: 2,
          frame: Math.floor(frameCountRef.current / 8) % 4,
          frameTimer: 0,
          isActive: true,
          speech: undefined,
          speechTimer: 0,
        },
        // 员工3 - 左下角电脑桌
        {
          id: "worker3",
          name: "创意工坊",
          state: CharacterState.TYPE,
          dir: Direction.DOWN,
          x: 4 * TILE_SIZE,
          y: 17 * TILE_SIZE,
          tileCol: 4,
          tileRow: 17,
          path: [],
          moveProgress: 0,
          palette: 3,
          frame: Math.floor(frameCountRef.current / 8) % 4,
          frameTimer: 0,
          isActive: true,
          speech: undefined,
          speechTimer: 0,
        },
        // 员工4 - 左下角第二个电脑桌
        {
          id: "worker4",
          name: "研究分析师",
          state: CharacterState.TYPE,
          dir: Direction.DOWN,
          x: 8 * TILE_SIZE,
          y: 17 * TILE_SIZE,
          tileCol: 8,
          tileRow: 17,
          path: [],
          moveProgress: 0,
          palette: 4,
          frame: Math.floor(frameCountRef.current / 8) % 4,
          frameTimer: 0,
          isActive: true,
          speech: undefined,
          speechTimer: 0,
        },
        // 员工5 - 右侧休息区旁边站着
        {
          id: "worker5",
          name: "技术专家",
          state: CharacterState.IDLE,
          dir: Direction.LEFT,
          x: 18 * TILE_SIZE,
          y: 13 * TILE_SIZE,
          tileCol: 18,
          tileRow: 13,
          path: [],
          moveProgress: 0,
          palette: 5,
          frame: Math.floor(frameCountRef.current / 8) % 4,
          frameTimer: 0,
          isActive: false,
          speech: undefined,
          speechTimer: 0,
        },
      ];

  // 保存数据到 refs 以便在动画循环中访问
  const tileMapRef = useRef<TileTypeVal[][] | null>(null);
  const furnitureRef = useRef<FurnitureInstance[]>([]);
  const agentsRef = useRef(agents);
  
  useEffect(() => {
    tileMapRef.current = tileMap;
  }, [tileMap]);
  
  useEffect(() => {
    furnitureRef.current = furniture;
  }, [furniture]);
  
  useEffect(() => {
    agentsRef.current = agents;
  }, [agents]);

  // 动画循环 - 直接在循环中渲染，不依赖 React 状态
  useEffect(() => {
    if (!tileMap) return;

    const animate = (time: number) => {
      if (time - lastTimeRef.current >= FRAME_INTERVAL) {
        lastTimeRef.current = time;
        frameCountRef.current += 1;
        tickFrame();
        
        // 直接渲染
        const canvas = canvasRef.current;
        const currentTileMap = tileMapRef.current;
        if (!canvas || !currentTileMap) {
          animationRef.current = requestAnimationFrame(animate);
          return;
        }

        const ctx = canvas.getContext("2d");
        if (!ctx) {
          animationRef.current = requestAnimationFrame(animate);
          return;
        }

        // 构建角色数据
        const currentAgents = agentsRef.current;
        const agentList = Object.values(currentAgents);
        const frame = frameCountRef.current;
        
        const chars: Character[] = agentList.length > 0
          ? agentList.map((agent, index) => {
              const x = (agent.x / 960) * (layout?.cols || 21) * TILE_SIZE;
              const y = (agent.y / 540) * (layout?.rows || 22) * TILE_SIZE;
              // typing 有2帧，walk 有4帧
              const animFrame = agent.anim === "type" 
                ? Math.floor(frame / 15) % 2  // 打字动画 2帧，每15帧切换
                : agent.anim === "walk"
                ? Math.floor(frame / 8) % 4   // 走路动画 4帧
                : Math.floor(frame / 30) % 2; // 空闲动画 2帧
              return {
                id: agent.id,
                name: agent.name,
                state: agent.anim === "type" ? CharacterState.TYPE
                     : agent.anim === "walk" ? CharacterState.WALK
                     : CharacterState.IDLE,
                dir: agent.facing === "up" ? Direction.UP : Direction.DOWN,
                x, y,
                tileCol: Math.floor(x / TILE_SIZE),
                tileRow: Math.floor(y / TILE_SIZE),
                path: [],
                moveProgress: 0,
                palette: index % 6,
                frame: animFrame,
                frameTimer: 0,
                isActive: agent.anim === "type",
                speech: agent.speech ?? undefined,
                speechTimer: agent.speech ? 3 : 0,
              };
            })
          : [
              // 项目主管坐在沙发上 (沙发前排 row 14)
              { id: "m", name: "项目主管", state: CharacterState.IDLE, dir: Direction.DOWN,
                x: 15*TILE_SIZE, y: 15*TILE_SIZE, tileCol: 15, tileRow: 15, path: [],
                moveProgress: 0, palette: 0, frame: Math.floor(frame/30) % 2, frameTimer: 0,
                isActive: false, speech: undefined, speechTimer: 0 },
              // 效率秘书坐在沙发旁边
              { id: "w2", name: "效率秘书", state: CharacterState.IDLE, dir: Direction.DOWN,
                x: 17*TILE_SIZE, y: 15*TILE_SIZE, tileCol: 17, tileRow: 15, path: [],
                moveProgress: 0, palette: 2, frame: Math.floor(frame/30) % 2, frameTimer: 0,
                isActive: false, speech: undefined, speechTimer: 0 },
              // 文字助手在左上电脑桌 (面向上，对着电脑)
              { id: "w1", name: "文字助手", state: CharacterState.TYPE, dir: Direction.UP,
                x: 4*TILE_SIZE, y: 14*TILE_SIZE, tileCol: 4, tileRow: 14, path: [],
                moveProgress: 0, palette: 1, frame: Math.floor(frame/15) % 2, frameTimer: 0,
                isActive: true, speech: undefined, speechTimer: 0 },
              // 创意工坊在右上电脑桌
              { id: "w3", name: "创意工坊", state: CharacterState.TYPE, dir: Direction.UP,
                x: 8*TILE_SIZE, y: 14*TILE_SIZE, tileCol: 8, tileRow: 14, path: [],
                moveProgress: 0, palette: 3, frame: Math.floor(frame/15) % 2, frameTimer: 0,
                isActive: true, speech: undefined, speechTimer: 0 },
              // 研究分析师在左下电脑桌 (面向下)
              { id: "w4", name: "研究分析师", state: CharacterState.TYPE, dir: Direction.DOWN,
                x: 4*TILE_SIZE, y: 17*TILE_SIZE, tileCol: 4, tileRow: 17, path: [],
                moveProgress: 0, palette: 4, frame: Math.floor(frame/15) % 2, frameTimer: 0,
                isActive: true, speech: undefined, speechTimer: 0 },
              // 技术专家在右下电脑桌
              { id: "w5", name: "技术专家", state: CharacterState.TYPE, dir: Direction.DOWN,
                x: 8*TILE_SIZE, y: 17*TILE_SIZE, tileCol: 8, tileRow: 17, path: [],
                moveProgress: 0, palette: 5, frame: Math.floor(frame/15) % 2, frameTimer: 0,
                isActive: true, speech: undefined, speechTimer: 0 },
            ];

        // 清空画布
        ctx.fillStyle = "#1a1a2e";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // 渲染瓦片
        renderTileGrid(ctx, currentTileMap, 0, 0, ZOOM);

        // 渲染场景
        renderScene(ctx, furnitureRef.current, chars, 0, 0, ZOOM);
      }
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [tickFrame, tileMap, layout]);

  const canvasWidth = (layout?.cols || 21) * TILE_SIZE * ZOOM;
  const canvasHeight = (layout?.rows || 22) * TILE_SIZE * ZOOM;

  if (!layout || !tileMap) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-[#1a1a2e]">
        <div className="text-white">Loading office...</div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center bg-[#1a1a2e] overflow-hidden">
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        style={{
          imageRendering: "pixelated",
          maxWidth: "100%",
          maxHeight: "100%",
        }}
      />
    </div>
  );
}

export default CanvasOffice;
