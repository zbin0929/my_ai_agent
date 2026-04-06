"use client";

import { useEffect, useRef } from "react";
import { useOfficeStore, getAgentColor } from "@/store/officeStore";
import { api } from "@/lib/api";
import { CanvasOffice } from "./CanvasOffice";
import { inferAppearance } from "./PixelChar";

export function OfficeView() {
  const tickFrame = useOfficeStore((s) => s.tickFrame);
  const spawnAgent = useOfficeStore((s) => s.spawnAgent);
  const initialized = useRef(false);

  useEffect(() => {
    const interval = setInterval(() => {
      tickFrame();
    }, 50);
    return () => clearInterval(interval);
  }, [tickFrame]);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const store = useOfficeStore.getState();
    if (Object.keys(store.agents).length > 0) return;

    api.agents
      .list()
      .then((data) => {
        const agents = data.agents || [];
        if (agents.length === 0) return;

        const currentStore = useOfficeStore.getState();
        if (Object.keys(currentStore.agents).length > 0) return;

        const manager = agents.find((a) => a.is_default);
        const workers = agents.filter((a) => !a.is_default);

        // 新的位置坐标 - 基于 Pixel Agents 风格布局
        // 布局: 21x22 瓦片, 每瓦片 16px, 缩放 2x
        // 坐标需要映射到 960x540 的旧坐标系统（officeStore 使用的）
        const TILE = 16;
        const ZOOM = 2;
        const LAYOUT_W = 21 * TILE * ZOOM; // 672
        const LAYOUT_H = 22 * TILE * ZOOM; // 704
        const OLD_W = 960;
        const OLD_H = 540;
        
        // 转换函数: 瓦片坐标 -> 旧坐标系统
        const tileToOld = (col: number, row: number) => ({
          x: (col * TILE * ZOOM / LAYOUT_W) * OLD_W,
          y: (row * TILE * ZOOM / LAYOUT_H) * OLD_H,
        });

        // 工位位置 (瓦片坐标)
        const DESK_POSITIONS = [
          { col: 4, row: 13, facing: "up" as const },   // 左上桌1
          { col: 8, row: 13, facing: "up" as const },   // 左上桌2
          { col: 4, row: 17, facing: "down" as const }, // 左下桌1
          { col: 8, row: 17, facing: "down" as const }, // 左下桌2
          { col: 18, row: 13, facing: "down" as const }, // 右侧站立
        ];
        
        // 项目主管坐在沙发上 (沙发前排 row 13，col 15)
        if (manager) {
          const app = inferAppearance(manager.name, 0);
          const pos = tileToOld(15, 13); // 沙发前排座位
          spawnAgent(manager.id, manager.name, "#f59e0b", pos.x, pos.y, true, app, "down");
        }

        // 员工分配到工位
        workers.forEach((worker, i) => {
          const deskPos = DESK_POSITIONS[i % DESK_POSITIONS.length];
          const pos = tileToOld(deskPos.col, deskPos.row);
          const color = getAgentColor(i);
          const app = inferAppearance(worker.name, i);
          spawnAgent(worker.id, worker.name, color, pos.x, pos.y, false, app, deskPos.facing);
        });
      })
      .catch(() => {});
  }, [spawnAgent]);

  return (
    <div
      className="w-full h-full flex items-center justify-center"
      style={{ background: "#1a1612" }}
    >
      <div className="w-full h-full max-w-[1100px] max-h-[660px] relative">
        <CanvasOffice />
      </div>
    </div>
  );
}
