"use client";

import React from "react";
import { useOfficeStore, type OfficeAgent } from "@/store/officeStore";
import { PixelChar, SpeechBubble } from "./PixelChar";

const W = 960;
const H = 540;

const C = {
  bg: "#1a1612",
  floorA: "#c8b898",
  floorB: "#baa888",
  floorLine: "#a89878",
  wall: "#2d2420",
  wallTop: "#3d3430",
  wallBase: "#4a3f38",
  wallHighlight: "#5a4f48",
  desk: "#6d5a48",
  deskSurface: "#7d6a58",
  deskEdge: "#5a4a3a",
  deskLeg: "#4a3a2e",
  monitor: "#1a1a2e",
  monitorFrame: "#2a2a3e",
  screen: "#0a1628",
  screenGlow: "#1e3a5c",
  screenLine1: "#4a9eff",
  screenLine2: "#4ade80",
  screenLine3: "#f59e0b",
  chair: "#3d3530",
  chairSeat: "#4a6fa5",
  chairLeg: "#5a5a5a",
  plant: "#2d6a2d",
  plantLight: "#4a8f4a",
  plantDark: "#1a4a1a",
  pot: "#8b6b4a",
  potDark: "#6b5030",
  window: "#1a2a3a",
  windowLight: "#2a4a6a",
  windowFrame: "#5a4a3a",
  windowShine: "#3a6a9a",
  lamp: "#f5deb3",
  lampGlow: "#f5deb340",
  whiteboard: "#e8e0d8",
  whiteboardFrame: "#5a4a3a",
  rug: "#3a2a4a",
  rugBorder: "#4a3a5a",
  rugInner: "#5a4a6a",
  bookshelf: "#5a4a38",
  book1: "#c0392b",
  book2: "#2980b9",
  book3: "#27ae60",
  book4: "#8e44ad",
  book5: "#f39c12",
  filing: "#7a7a7a",
  filingDark: "#5a5a5a",
  waterCooler: "#a0c4e8",
  waterCoolerBlue: "#6ab0de",
  coffee: "#6b4226",
  coffeeLight: "#8b5a36",
  keyboard: "#3a3a3a",
  keyboardKey: "#5a5a5a",
  clock: "#e8e0d8",
  clockFrame: "#5a4a3a",
  clockHand: "#2a2a2a",
  fridge: "#c8c8c8",
  fridgeDark: "#a8a8a8",
  fridgeHandle: "#888888",
  painting1: "#e74c3c",
  painting2: "#3498db",
  painting3: "#2ecc71",
  paintingFrame: "#5a4a3a",
  sofa: "#4a6fa5",
  sofaDark: "#3a5f95",
  sofaArm: "#5a7fb5",
  tableTop: "#6d5a48",
  tableLeg: "#4a3a2e",
  trashCan: "#6a6a6a",
  trashCanDark: "#4a4a4a",
  label: "#c0b8a8",
};

function Floor() {
  const els: React.ReactNode[] = [];
  const tileSize = 24;
  const startY = 130;

  for (let row = 0; row < Math.ceil((H - startY) / tileSize); row++) {
    for (let col = 0; col < Math.ceil(W / tileSize); col++) {
      const x = col * tileSize;
      const y = startY + row * tileSize;
      const checker = (row + col) % 2 === 0;
      els.push(
        <rect key={`ft${row}_${col}`} x={x} y={y} width={tileSize} height={tileSize} fill={checker ? C.floorA : C.floorB} />,
      );
      if (row % 3 === 0 && col % 4 === 0) {
        els.push(
          <rect key={`fl${row}_${col}`} x={x} y={y + tileSize - 1} width={tileSize} height={1} fill={C.floorLine} opacity={0.3} />,
        );
      }
    }
  }
  return <g>{els}</g>;
}

function Walls() {
  return (
    <g>
      <rect x={0} y={0} width={W} height={130} fill={C.wall} />
      <rect x={0} y={0} width={W} height={10} fill={C.wallTop} />
      <rect x={0} y={120} width={W} height={10} fill={C.wallBase} />
      <rect x={0} y={0} width={10} height={H} fill={C.wall} />
      <rect x={W - 10} y={0} width={10} height={H} fill={C.wall} />
      <rect x={10} y={10} width={W - 20} height={3} fill={C.wallHighlight} opacity={0.3} />
      <rect x={10} y={130} width={W - 20} height={2} fill={C.wallHighlight} opacity={0.2} />
    </g>
  );
}

function Window({ x }: { x: number }) {
  return (
    <g>
      <rect x={x} y={22} width={120} height={80} fill={C.window} rx={3} />
      <rect x={x + 4} y={26} width={54} height={34} fill={C.windowLight} opacity={0.5} />
      <rect x={x + 62} y={26} width={54} height={34} fill={C.windowLight} opacity={0.4} />
      <rect x={x + 4} y={64} width={54} height={34} fill={C.windowLight} opacity={0.35} />
      <rect x={x + 62} y={64} width={54} height={34} fill={C.windowLight} opacity={0.45} />
      <rect x={x + 20} y={30} width={12} height={8} fill={C.windowShine} opacity={0.3} rx={2} />
      <rect x={x} y={22} width={120} height={80} fill="none" stroke={C.windowFrame} strokeWidth={4} />
      <line x1={x + 60} y1={22} x2={x + 60} y2={102} stroke={C.windowFrame} strokeWidth={3} />
      <line x1={x} y1={60} x2={x + 120} y2={60} stroke={C.windowFrame} strokeWidth={3} />
    </g>
  );
}

function CeilingLight({ x }: { x: number }) {
  return (
    <g>
      <rect x={x} y={10} width={6} height={20} fill="#5a5a5a" />
      <rect x={x - 18} y={30} width={42} height={8} fill="#6a6a6a" rx={4} />
      <rect x={x - 14} y={38} width={34} height={3} fill={C.lamp} opacity={0.9} />
      <ellipse cx={x + 3} cy={50} rx={30} ry={6} fill={C.lampGlow} />
    </g>
  );
}

function Monitor({ x, y, on = false }: { x: number; y: number; on?: boolean }) {
  return (
    <g>
      <rect x={x} y={y} width={48} height={36} fill={C.monitorFrame} rx={2} />
      <rect x={x + 3} y={y + 3} width={42} height={30} fill={on ? C.screenGlow : C.screen} rx={1} />
      {on && (
        <g>
          <rect x={x + 7} y={y + 8} width={14} height={2} fill={C.screenLine1} opacity={0.7} />
          <rect x={x + 7} y={y + 12} width={22} height={2} fill={C.screenLine2} opacity={0.5} />
          <rect x={x + 7} y={y + 16} width={10} height={2} fill={C.screenLine3} opacity={0.6} />
          <rect x={x + 7} y={y + 20} width={18} height={2} fill={C.screenLine1} opacity={0.4} />
          <rect x={x + 7} y={y + 24} width={8} height={2} fill={C.screenLine2} opacity={0.5} />
        </g>
      )}
      <rect x={x + 20} y={y + 36} width={8} height={6} fill="#4a4a4a" />
      <rect x={x + 14} y={y + 42} width={20} height={3} fill="#3a3a3a" rx={1} />
    </g>
  );
}

function Keyboard({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={30} height={12} fill={C.keyboard} rx={1} />
      {Array.from({ length: 3 }).map((_, row) =>
        Array.from({ length: 7 }).map((_, col) => (
          <rect key={`k${row}_${col}`} x={x + 2 + col * 4} y={y + 2 + row * 3} width={3} height={2} fill={C.keyboardKey} rx={0.5} />
        )),
      )}
    </g>
  );
}

function CoffeeCup({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={8} height={8} fill={C.coffee} rx={1} />
      <rect x={x + 1} y={y + 1} width={6} height={4} fill={C.coffeeLight} rx={0.5} />
      <rect x={x + 8} y={y + 2} width={3} height={4} fill="none" stroke={C.coffee} strokeWidth={1} rx={1} />
      <path d={`M${x + 2},${y - 2} Q${x + 4},${y - 5} ${x + 6},${y - 2}`} fill="none" stroke="#aaa" strokeWidth={0.5} opacity={0.5} />
    </g>
  );
}

function Desk({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={140} height={10} fill={C.deskSurface} rx={2} />
      <rect x={x} y={y} width={140} height={2} fill={C.deskEdge} />
      <rect x={x + 4} y={y + 10} width={6} height={36} fill={C.deskLeg} />
      <rect x={x + 130} y={y + 10} width={6} height={36} fill={C.deskLeg} />
      <rect x={x} y={y + 46} width={140} height={4} fill={C.desk} rx={1} />
      <rect x={x + 10} y={y + 14} width={120} height={20} fill={C.desk} opacity={0.5} rx={1} />
    </g>
  );
}

function OfficeChair({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y + 20} width={4} height={10} fill={C.chairLeg} />
      <rect x={x + 26} y={y + 20} width={4} height={10} fill={C.chairLeg} />
      <rect x={x - 2} y={y + 28} width={34} height={3} fill={C.chairLeg} rx={1} />
      <rect x={x} y={y + 12} width={30} height={10} fill={C.chairSeat} rx={3} />
      <rect x={x + 2} y={y} width={6} height={14} fill={C.chair} rx={2} />
      <rect x={x + 10} y={y - 4} width={10} height={18} fill={C.chairSeat} rx={2} />
    </g>
  );
}

function Workstation({ x, y, monitorOn = false, facing = "down" }: { x: number; y: number; monitorOn?: boolean; facing?: "up" | "down" }) {
  if (facing === "up") {
    return (
      <g>
        <OfficeChair x={x + 54} y={y} />
        <Desk x={x} y={y + 54} />
        <Keyboard x={x + 46} y={y + 48} />
        <CoffeeCup x={x + 110} y={y + 46} />
        <Monitor x={x + 46} y={y + 86} on={monitorOn} />
      </g>
    );
  }
  return (
    <g>
      <Monitor x={x + 46} y={y - 8} on={monitorOn} />
      <Desk x={x} y={y + 24} />
      <Keyboard x={x + 46} y={y + 18} />
      <CoffeeCup x={x + 110} y={y + 16} />
      <OfficeChair x={x + 54} y={y + 60} />
    </g>
  );
}

function Plant({ x, y, variant = 0 }: { x: number; y: number; variant?: number }) {
  const leafColor = variant === 1 ? C.plantLight : C.plant;
  const leafHighlight = variant === 1 ? "#6aaf6a" : C.plantLight;
  return (
    <g>
      <rect x={x + 4} y={y + 20} width={16} height={14} fill={C.pot} rx={3} />
      <rect x={x + 2} y={y + 18} width={20} height={4} fill={C.potDark} rx={2} />
      <circle cx={x + 12} cy={y + 10} r={12} fill={leafColor} />
      <circle cx={x + 6} cy={y + 4} r={7} fill={leafHighlight} />
      <circle cx={x + 18} cy={y + 6} r={6} fill={leafColor} />
      <circle cx={x + 12} cy={y + 2} r={4} fill={leafHighlight} opacity={0.7} />
    </g>
  );
}

function Bookshelf({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={60} height={80} fill={C.bookshelf} rx={2} />
      <rect x={x + 2} y={y + 2} width={56} height={76} fill="#4a3a28" />
      {[0, 1, 2].map((shelf) => (
        <g key={`shelf${shelf}`}>
          <rect x={x + 2} y={y + 2 + shelf * 25} width={56} height={2} fill={C.bookshelf} />
          {[
            { bx: x + 4, w: 6, c: C.book1 },
            { bx: x + 12, w: 5, c: C.book2 },
            { bx: x + 18, w: 7, c: C.book3 },
            { bx: x + 27, w: 4, c: C.book4 },
            { bx: x + 33, w: 6, c: C.book5 },
            { bx: x + 41, w: 5, c: C.book1 },
            { bx: x + 48, w: 6, c: C.book2 },
          ].map((book, bi) => (
            <rect key={`b${shelf}_${bi}`} x={book.bx} y={y + 6 + shelf * 25} width={book.w} height={18} fill={book.c} rx={1} opacity={0.9} />
          ))}
        </g>
      ))}
    </g>
  );
}

function FilingCabinet({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={30} height={50} fill={C.filing} rx={2} />
      <rect x={x + 2} y={y + 2} width={26} height={46} fill={C.filingDark} rx={1} />
      {[0, 1, 2].map((i) => (
        <g key={`fc${i}`}>
          <rect x={x + 4} y={y + 5 + i * 15} width={22} height={12} fill={C.filing} rx={1} />
          <rect x={x + 12} y={y + 10 + i * 15} width={6} height={2} fill="#888" rx={1} />
        </g>
      ))}
    </g>
  );
}

function WaterCooler({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y + 30} width={20} height={20} fill="#8a8a8a" rx={2} />
      <rect x={x + 2} y={y} width={16} height={30} fill={C.waterCooler} rx={3} />
      <rect x={x + 4} y={y + 4} width={12} height={16} fill={C.waterCoolerBlue} rx={2} opacity={0.6} />
      <rect x={x + 6} y={y + 28} width={4} height={4} fill="#6a6a6a" rx={1} />
    </g>
  );
}

function Clock({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <circle cx={x + 15} cy={y + 15} r={15} fill={C.clockFrame} />
      <circle cx={x + 15} cy={y + 15} r={12} fill={C.clock} />
      <line x1={x + 15} y1={y + 15} x2={x + 15} y2={y + 6} stroke={C.clockHand} strokeWidth={1.5} />
      <line x1={x + 15} y1={y + 15} x2={x + 22} y2={y + 18} stroke={C.clockHand} strokeWidth={1} />
      <circle cx={x + 15} cy={y + 15} r={1.5} fill={C.clockHand} />
    </g>
  );
}

function Painting({ x, y, variant = 0 }: { x: number; y: number; variant?: number }) {
  const colors = [
    [C.painting1, C.painting2],
    [C.painting3, C.painting1],
    [C.painting2, C.painting3],
  ];
  const [c1, c2] = colors[variant % colors.length];
  return (
    <g>
      <rect x={x} y={y} width={40} height={30} fill={C.paintingFrame} rx={1} />
      <rect x={x + 2} y={y + 2} width={36} height={26} fill={c1} />
      <rect x={x + 10} y={y + 8} width={20} height={14} fill={c2} opacity={0.6} rx={1} />
    </g>
  );
}

function Sofa({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={80} height={30} fill={C.sofa} rx={4} />
      <rect x={x} y={y + 30} width={80} height={10} fill={C.sofaDark} rx={3} />
      <rect x={x - 6} y={y + 4} width={10} height={36} fill={C.sofaArm} rx={4} />
      <rect x={x + 76} y={y + 4} width={10} height={36} fill={C.sofaArm} rx={4} />
      {[0, 1].map((i) => (
        <rect key={`cush${i}`} x={x + 6 + i * 36} y={y + 4} width={32} height={22} fill={C.sofaDark} rx={3} opacity={0.4} />
      ))}
    </g>
  );
}

function CoffeeTable({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={50} height={6} fill={C.tableTop} rx={2} />
      <rect x={x + 4} y={y + 6} width={4} height={12} fill={C.tableLeg} />
      <rect x={x + 42} y={y + 6} width={4} height={12} fill={C.tableLeg} />
    </g>
  );
}

function TrashCan({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={14} height={18} fill={C.trashCan} rx={2} />
      <rect x={x + 2} y={y} width={10} height={3} fill={C.trashCanDark} rx={1} />
      <rect x={x - 1} y={y + 2} width={16} height={2} fill={C.trashCan} rx={1} />
    </g>
  );
}

function Rug({ x, y }: { x: number; y: number }) {
  return (
    <g opacity={0.35}>
      <rect x={x} y={y} width={200} height={90} fill={C.rug} rx={6} />
      <rect x={x + 8} y={y + 8} width={184} height={74} fill="none" stroke={C.rugBorder} strokeWidth={2} rx={4} />
      <rect x={x + 16} y={y + 16} width={168} height={58} fill="none" stroke={C.rugInner} strokeWidth={1} rx={3} />
      {Array.from({ length: 5 }).map((_, i) => (
        <circle key={`rd${i}`} cx={x + 30 + i * 36} cy={y + 45} r={4} fill={C.rugInner} opacity={0.5} />
      ))}
    </g>
  );
}

function Whiteboard({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect x={x} y={y} width={90} height={55} fill={C.whiteboardFrame} rx={2} />
      <rect x={x + 3} y={y + 3} width={84} height={49} fill={C.whiteboard} rx={1} />
      <rect x={x + 8} y={y + 10} width={35} height={2} fill="#aaa" opacity={0.4} />
      <rect x={x + 8} y={y + 16} width={50} height={2} fill="#aaa" opacity={0.3} />
      <rect x={x + 8} y={y + 22} width={28} height={2} fill={C.screenLine1} opacity={0.5} />
      <rect x={x + 8} y={y + 28} width={42} height={2} fill="#aaa" opacity={0.3} />
      <rect x={x + 8} y={y + 34} width={20} height={2} fill={C.screenLine2} opacity={0.4} />
      <rect x={x + 8} y={y + 40} width={35} height={2} fill="#aaa" opacity={0.3} />
    </g>
  );
}

const DESK_POSITIONS: { x: number; y: number; facing: "up" | "down" }[] = [
  { x: 50, y: 210, facing: "down" },
  { x: 270, y: 210, facing: "down" },
  { x: 490, y: 210, facing: "down" },
  { x: 50, y: 330, facing: "up" },
  { x: 270, y: 330, facing: "up" },
  { x: 490, y: 330, facing: "up" },
];

function ManagerDesk() {
  return (
    <g>
      <rect x={350} y={140} width={10} height={2} fill={C.wallBase} opacity={0.3} />
      <OfficeChair x={404} y={186} />
      <Desk x={350} y={155} />
      <Monitor x={396} y={122} on />
      <Keyboard x={396} y={148} />
      <CoffeeCup x={460} y={146} />
    </g>
  );
}

function BreakArea() {
  return (
    <g>
      <Sofa x={700} y={160} />
      <CoffeeTable x={720} y={205} />
      <CoffeeCup x={730} y={202} />
      <Plant x={800} y={150} variant={1} />
    </g>
  );
}

function StaticScene({ activeWorkerId }: { activeWorkerId: string | null }) {
  return (
    <g>
      <Floor />
      <Walls />
      <Window x={120} />
      <Window x={320} />
      <Window x={520} />
      <CeilingLight x={160} />
      <CeilingLight x={400} />
      <CeilingLight x={640} />
      <CeilingLight x={860} />

      <Whiteboard x={700} y={140} />
      <Clock x={880} y={40} />
      <Painting x={20} y={40} variant={0} />
      <Painting x={80} y={50} variant={1} />

      <Bookshelf x={700} y={350} />
      <FilingCabinet x={770} y={380} />
      <WaterCooler x={850} y={340} />
      <TrashCan x={640} y={420} />
      <TrashCan x={660} y={420} />

      <Plant x={20} y={100} variant={0} />
      <Plant x={620} y={100} variant={1} />
      <Plant x={900} y={100} variant={0} />

      <Rug x={160} y={430} />

      <ManagerDesk />

      {DESK_POSITIONS.map((pos, i) => (
        <Workstation key={`ws${i}`} x={pos.x} y={pos.y} monitorOn={activeWorkerId !== null} facing={pos.facing} />
      ))}

      <BreakArea />
    </g>
  );
}

function AgentLabel({ agent }: { agent: OfficeAgent }) {
  const name = agent.name.length > 8 ? agent.name.slice(0, 8) : agent.name;
  const tw = name.length * 6 + 12;
  return (
    <g>
      <rect x={agent.x - tw / 2} y={agent.y + 6} width={tw} height={14} fill="rgba(0,0,0,0.75)" rx={3} />
      <text
        x={agent.x}
        y={agent.y + 16}
        textAnchor="middle"
        fontSize={9}
        fill={agent.color}
        fontFamily="monospace"
        fontWeight={700}
      >
        {name}
      </text>
    </g>
  );
}

export function PixelOffice() {
  const agents = useOfficeStore((s) => s.agents);
  const activeWorkerId = useOfficeStore((s) => s.activeWorkerId);
  const agentList = Object.values(agents);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      height="100%"
      style={{ imageRendering: "pixelated", display: "block" }}
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <rect width={W} height={H} fill={C.bg} />
      <StaticScene activeWorkerId={activeWorkerId} />

      {agentList.map((agent) => (
        <g key={agent.id}>
          <PixelChar
            x={agent.x}
            y={agent.y}
            color={agent.color}
            anim={agent.anim}
            frame={agent.frame}
            flip={agent.flip}
            hat={agent.hat}
            scale={1.2}
            appearance={agent.appearance}
            facing={agent.facing}
          />
          <AgentLabel agent={agent} />
          {agent.speech && (
            <SpeechBubble
              x={agent.x}
              y={agent.y - 90}
              text={agent.speech}
              type={agent.speechType ?? "result"}
            />
          )}
        </g>
      ))}
    </svg>
  );
}
