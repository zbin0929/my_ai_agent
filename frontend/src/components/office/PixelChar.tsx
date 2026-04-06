"use client";

import React from "react";
import type { AgentAnim } from "@/store/officeStore";

export type Gender = "male" | "female";
export type HairStyle = "short" | "medium" | "long";
export type SkinTone = "light" | "medium" | "dark";

export interface Appearance {
  gender: Gender;
  hairStyle: HairStyle;
  skinTone: SkinTone;
  hairColor: string;
}

interface PixelCharProps {
  x: number;
  y: number;
  color: string;
  anim: AgentAnim;
  frame: number;
  flip?: boolean;
  hat?: boolean;
  scale?: number;
  appearance?: Appearance;
  facing?: "up" | "down";
}

const PX = 3;

const SKIN_PALETTES: Record<SkinTone, Record<string, string>> = {
  light: { O: "#2a1518", H: "#8f6439", L: "#b18649", S: "#f0b899", s: "#fcd4b8", F: "#d9a088" },
  medium: { O: "#3a2018", H: "#7a5430", L: "#9a7440", S: "#d4976a", s: "#e8b088", F: "#b88060" },
  dark: { O: "#1a1010", H: "#4a3020", L: "#6a4830", S: "#a07050", s: "#b88868", F: "#8a6040" },
};

const HAIR_COLORS: Record<string, Record<string, string>> = {
  dark: { O: "#1a1010", H: "#2a1a10", L: "#3a2a18" },
  brown: { O: "#2a1518", H: "#8f6439", L: "#b18649" },
  blonde: { O: "#8a7a30", H: "#c4a840", L: "#dcc060" },
  red: { O: "#5a1818", H: "#a83820", L: "#c85030" },
};

const BODY_PAL: Record<string, string> = {
  E: "#000000",
  W: "#ffffff",
  g: "#4f4f4f",
  P: "#0f3052",
  p: "#1a4a7a",
  K: "#040605",
  N: "#493e38",
};

function getSkinPal(skin: SkinTone) {
  return SKIN_PALETTES[skin] || SKIN_PALETTES.light;
}

function getHairPal(hairColor: string) {
  return HAIR_COLORS[hairColor] || HAIR_COLORS.dark;
}

function col(token: string, shirt: string, skinPal: Record<string, string>, hairPal: Record<string, string>): string {
  if (token === "_" || token === " ") return "transparent";
  if (token === "C") return shirt;
  if (token === "D") {
    const r = parseInt(shirt.slice(1, 3), 16);
    const g2 = parseInt(shirt.slice(3, 5), 16);
    const b = parseInt(shirt.slice(5, 7), 16);
    return `#${Math.round(r * 0.7).toString(16).padStart(2, "0")}${Math.round(g2 * 0.7).toString(16).padStart(2, "0")}${Math.round(b * 0.7).toString(16).padStart(2, "0")}`;
  }
  if (skinPal[token]) return skinPal[token];
  if (hairPal[token]) return hairPal[token];
  return BODY_PAL[token] ?? "#ff00ff";
}

const HEAD_MALE_SHORT: string[] = [
  "________________",
  "________________",
  "____OOOOOOO_____",
  "___OHHHLOHHO____",
  "__OHHHHLHHHHHHO_",
  "_OLHHHHHOHHHHO__",
  "_OLHHHHHHHHHO___",
  "_OLHHHHHHHHHO___",
  "_OLHHHHHHHHHO___",
  "_OLHHHHHHHHHO___",
  "_OHHHLLLOHLHO___",
  "_OHHHHOOHOHHHO__",
  "_OHHOOSSPSSOO___",
  "__OOSSESSESOo___",
  "___NsWESSEWsN___",
  "___NsWgSSgWsN___",
  "____NFsSSsFN____",
];

const HEAD_FEMALE_MED: string[] = [
  "________________",
  "________________",
  "____OOOOOOO_____",
  "___OHHHLOHHO____",
  "__OHHHHLHHHHHHO_",
  "_OLHHHHHOHHHHO__",
  "_OLHHHHHHHHHO___",
  "_OLHHHHHHHHHO___",
  "_OLHHHHHHHHHO___",
  "_OLHHHHHHHHHO___",
  "_OHHHLLLOHLHO___",
  "_OHHHHOOHOHHHO__",
  "_OHHOOSSPSSOO___",
  "__OOSSESSESOo___",
  "___NsWESSEWsN___",
  "___NsWgSSgWsN___",
  "____NFsSSsFN____",
];

const FEMALE_HAIR_SIDE_L: string[] = [
  "________________",
  "________________",
  "________________",
  "________________",
  "________________",
  "LO______________",
  "LLO_____________",
  "LHHO____________",
  "LHHO____________",
  "LHHO____________",
  "LHHO____________",
  "LHHO____________",
  "LHO_____________",
  "LO______________",
  "HO______________",
  "HO______________",
  "________________",
];

const FEMALE_HAIR_SIDE_R: string[] = [
  "________________",
  "________________",
  "________________",
  "________________",
  "________________",
  "______________OL",
  "_____________OLL",
  "____________OHHO",
  "____________OHHO",
  "____________OHHO",
  "____________OHHO",
  "____________OHHO",
  "_____________OHL",
  "______________OL",
  "______________OH",
  "______________OH",
  "________________",
];

const ARMS_IDLE: string[] = [
  "___NCNNSSNNDN___",
  "__NCDDDWKKWDDN__",
  "__NDDDWKKWDDCN__",
  "__sWDDWKKWNSSN__",
  "__NSNDDWKKWSFN__",
];

const ARMS_TYPE: string[] = [
  "___NCNNSSNNDN___",
  "__NCDDDWKKWDDN__",
  "_NDDDWKKKKWDDNs_",
  "_NSSsDDWKKWNSsN_",
  "_NsSSNDKKKKNSSN_",
];

const ARMS_CELEBRATE: string[] = [
  "sNNNCNNSSNNCNNs_",
  "NsNCDDDWKKWDDsN_",
  "___NDDDWKKWDDD__",
  "__ssDDDWKKWNss__",
  "___NSNKKKKKNSN__",
];

const ARMS_SLEEP: string[] = [
  "___NCNNSSNNDN___",
  "__NCDDDWKKWDDN__",
  "__NDDDKKKKKDDNs_",
  "__NSDDKKKKKNSp__",
  "___SpNpppppNS___",
];

const LEGS_IDLE: string[] = [
  "__NFNpWKKWDNN___",
  "___NNpWWWWpN____",
];

const LEGS_WALK_A: string[] = [
  "__NFNpKppKDNN___",
  "___KppK___pKN___",
];

const LEGS_WALK_B: string[] = [
  "__NFNpKppKDNN___",
  "___NppK___KpK___",
];

const LEGS_TYPE: string[] = [
  "__NFNpWKKWDNN___",
  "___NpKK___KpN___",
];

const LEGS_CELEBRATE: string[] = [
  "__NpNpKKKKKpNN__",
  "_NKppK_____KppKN",
];

const SIT_IDLE_BODY: string[] = [
  "___NCNNSSNNDN___",
  "__NCDDDWKKWDDN__",
  "__NDDDWKKWDDCN__",
  "__sWDDWKKWNSSN__",
  "__NSNDDWKKWSFN__",
  "___NSNKKKKKNSN__",
  "____NCCCCCN_____",
  "___NCCCCCCCN____",
  "___NCCCCCCCN____",
];

const SIT_TYPE_BODY: string[] = [
  "___NCNNSSNNDN___",
  "__NCDDDWKKWDDN__",
  "_NDDDWKKKKWDDNs_",
  "_NSSsDDWKKWNSsN_",
  "_NsSSNDKKKKNSSN_",
  "___NSNKKKKKNSN__",
  "____NCCCCCN_____",
  "___NCCCCCCCN____",
  "___NCCCCCCCN____",
];

const SIT_SLEEP_BODY: string[] = [
  "___NCNNSSNNDN___",
  "__NCDDDWKKWDDN__",
  "__NDDDKKKKKDDNs_",
  "__NSDDKKKKKNSp__",
  "___SpNpppppNS___",
  "___NSNKKKKKNSN__",
  "____NCCCCCN_____",
  "___NCCCCCCCN____",
  "___NCCCCCCCN____",
];

function pixelRow(
  rowStr: string,
  rowIndex: number,
  bx: number,
  by: number,
  px: number,
  shirt: string,
  skinPal: Record<string, string>,
  hairPal: Record<string, string>,
  keyPrefix: string,
): React.ReactNode[] {
  const rects: React.ReactNode[] = [];
  for (let ci = 0; ci < rowStr.length; ci++) {
    const token = rowStr[ci];
    if (token === "_" || token === " ") continue;
    const fill = col(token, shirt, skinPal, hairPal);
    rects.push(
      <rect
        key={`${keyPrefix}${rowIndex}_${ci}`}
        x={bx + ci * px}
        y={by + rowIndex * px}
        width={px}
        height={px}
        fill={fill}
      />,
    );
  }
  return rects;
}

function isSitting(anim: AgentAnim): boolean {
  return anim === "idle" || anim === "type" || anim === "sleep";
}

export function PixelChar({
  x,
  y,
  color,
  anim,
  frame,
  flip = false,
  hat = false,
  scale = 1,
  appearance,
  facing = "down",
}: PixelCharProps) {
  const px = Math.round(PX * scale);
  const app = appearance || { gender: "male" as Gender, hairStyle: "short" as HairStyle, skinTone: "light" as SkinTone, hairColor: "dark" };
  const skinPal = getSkinPal(app.skinTone);
  const hairPal = getHairPal(app.hairColor);
  const isFemale = app.gender === "female";
  const sitting = isSitting(anim);

  const headRows = isFemale ? HEAD_FEMALE_MED : HEAD_MALE_SHORT;
  const charW = 16 * px;
  const standingH = 24 * px;
  const sittingH = 17 * px + 9 * px;

  const typeBounce = anim === "type" ? (Math.floor(frame / 6) % 2 === 0 ? -px : 0) : 0;
  const celebJump =
    anim === "celebrate"
      ? Math.round(Math.abs(Math.sin((frame / 30) * Math.PI * 4)) * px * 6)
      : 0;
  const sleepSway = anim === "sleep" ? Math.round(Math.sin(frame / 40) * px * 0.5) : 0;

  const totalH = sitting ? sittingH : standingH;
  const bx = x - charW / 2 + sleepSway;
  const by = y - totalH + typeBounce - celebJump;

  const walkPhase = Math.floor(frame / 8) % 2 === 0;

  const rects: React.ReactNode[] = [];

  if (hat) {
    rects.push(
      <rect key="hat-brim" x={bx + px} y={by + px * 2} width={14 * px} height={px * 2} fill={color} />,
      <rect key="hat-body" x={bx + 3 * px} y={by - px * 3} width={10 * px} height={px * 4} fill={color} />,
      <rect key="hat-star" x={bx + 7 * px} y={by - px * 2} width={2 * px} height={2 * px} fill="#f59e0b" />,
    );
  }

  headRows.forEach((row, ri) => {
    rects.push(...pixelRow(row, ri, bx, by, px, color, skinPal, hairPal, "h"));
  });

  if (isFemale && app.hairStyle !== "short") {
    FEMALE_HAIR_SIDE_L.forEach((row, ri) => {
      rects.push(...pixelRow(row, ri, bx, by, px, color, skinPal, hairPal, "hl"));
    });
    FEMALE_HAIR_SIDE_R.forEach((row, ri) => {
      rects.push(...pixelRow(row, ri, bx, by, px, color, skinPal, hairPal, "hr"));
    });
  }

  if (sitting) {
    const bodyRows =
      anim === "type" ? SIT_TYPE_BODY
      : anim === "sleep" ? SIT_SLEEP_BODY
      : SIT_IDLE_BODY;
    bodyRows.forEach((row, ri) => {
      rects.push(...pixelRow(row, 17 + ri, bx, by, px, color, skinPal, hairPal, "sb"));
    });
  } else {
    const armRows =
      anim === "celebrate" ? ARMS_CELEBRATE
      : anim === "sleep" ? ARMS_SLEEP
      : anim === "type" ? ARMS_TYPE
      : ARMS_IDLE;

    const legRows =
      anim === "walk"
        ? walkPhase ? LEGS_WALK_A : LEGS_WALK_B
        : anim === "celebrate" ? LEGS_CELEBRATE
        : anim === "type" ? LEGS_TYPE
        : LEGS_IDLE;

    armRows.forEach((row, ri) => {
      rects.push(...pixelRow(row, 17 + ri, bx, by, px, color, skinPal, hairPal, "a"));
    });
    legRows.forEach((row, ri) => {
      rects.push(...pixelRow(row, 22 + ri, bx, by, px, color, skinPal, hairPal, "g"));
    });
  }

  const zzzEl =
    anim === "sleep" ? (
      <text
        key="zzz"
        x={x + charW * 0.35}
        y={by - px}
        fontSize={px * 5}
        fill="#c0caf5"
        fontFamily="monospace"
        opacity={0.85}
      >
        Zzz
      </text>
    ) : null;

  const errorEl =
    anim === "error" && Math.floor(frame / 10) % 2 === 0 ? (
      <g key="err">
        <circle cx={x} cy={by - px * 5} r={px * 4} fill="#f7768e" opacity={0.9} />
        <text
          x={x - px}
          y={by - px * 2}
          fontSize={px * 6}
          fill="white"
          fontWeight="bold"
          fontFamily="monospace"
        >
          !
        </text>
      </g>
    ) : null;

  const starEls =
    anim === "celebrate"
      ? [[-5, -8], [5, -10], [0, -14], [-9, -5], [9, -6]].map(([dx, dy], i) => (
          <text
            key={`star${i}`}
            x={x + dx * px}
            y={by + dy * px}
            fontSize={px * 4}
            fill={["#f59e0b", "#4ade80", "#4a9eff", "#f472b6", "#a78bfa"][i]}
            fontFamily="monospace"
            opacity={0.7 + Math.sin((frame / 30) * Math.PI * 3 + i) * 0.3}
          >
            ★
          </text>
        ))
      : null;

  const flipTransform = flip ? `translate(${x * 2}, 0) scale(-1, 1)` : undefined;

  return (
    <g transform={flipTransform} style={{ imageRendering: "pixelated" }}>
      {rects}
      {zzzEl}
      {errorEl}
      {starEls}
    </g>
  );
}

const BUBBLE_COLORS: Record<string, { bg: string; text: string }> = {
  task: { bg: "#1e3a5f", text: "#93c5fd" },
  result: { bg: "#1a332a", text: "#86efac" },
  thinking: { bg: "#3b2e5e", text: "#c4b5fd" },
  error: { bg: "#4a1c1c", text: "#fca5a5" },
};

interface SpeechBubbleProps {
  x: number;
  y: number;
  text: string;
  color?: string;
  textColor?: string;
  type?: "task" | "result" | "thinking" | "error";
}

export function SpeechBubble({
  x,
  y,
  text,
  type = "result",
}: SpeechBubbleProps) {
  const colors = BUBBLE_COLORS[type] ?? BUBBLE_COLORS.result;
  const maxW = 160;
  const pad = 8;
  const fontSize = 11;
  const truncated = text.length > 44 ? text.slice(0, 44) + "…" : text;
  const lines = truncated.length > 22 ? [truncated.slice(0, 22), truncated.slice(22)] : [truncated];
  const bH = lines.length * (fontSize + 4) + pad * 2;

  return (
    <g>
      <rect
        x={x - maxW / 2}
        y={y - bH - 10}
        width={maxW}
        height={bH}
        fill={colors.bg}
        rx={6}
        opacity={0.95}
        stroke={colors.text}
        strokeWidth={0.5}
      />
      <polygon points={`${x - 5},${y - 10} ${x + 5},${y - 10} ${x},${y - 2}`} fill={colors.bg} />
      {lines.map((line, i) => (
        <text
          key={i}
          x={x}
          y={y - bH - 10 + pad + fontSize + i * (fontSize + 4)}
          textAnchor="middle"
          fontSize={fontSize}
          fill={colors.text}
          fontFamily="monospace"
          fontWeight={600}
        >
          {line}
        </text>
      ))}
    </g>
  );
}

const FEMALE_KEYWORDS = ["秘书", "助手", "文字", "翻译", "创意", "设计", "文员", "客服"];
const HAIR_MAP: Record<string, { gender: Gender; hairStyle: HairStyle; hairColor: string }> = {
  "项目主管": { gender: "male", hairStyle: "short", hairColor: "dark" },
  "创意工坊": { gender: "female", hairStyle: "medium", hairColor: "red" },
  "研究分析师": { gender: "male", hairStyle: "short", hairColor: "dark" },
  "技术专家": { gender: "male", hairStyle: "short", hairColor: "brown" },
  "文字助手": { gender: "female", hairStyle: "medium", hairColor: "blonde" },
  "效率秘书": { gender: "female", hairStyle: "long", hairColor: "brown" },
};

const SKIN_VARIANTS: SkinTone[] = ["light", "medium", "dark"];

export function inferAppearance(agentName: string, agentIndex: number): Appearance {
  const mapped = HAIR_MAP[agentName];
  if (mapped) {
    return {
      gender: mapped.gender,
      hairStyle: mapped.hairStyle,
      skinTone: SKIN_VARIANTS[agentIndex % SKIN_VARIANTS.length],
      hairColor: mapped.hairColor,
    };
  }

  let gender: Gender = "male";
  for (const kw of FEMALE_KEYWORDS) {
    if (agentName.includes(kw)) {
      gender = "female";
      break;
    }
  }

  return {
    gender,
    hairStyle: gender === "female" ? "medium" : "short",
    skinTone: SKIN_VARIANTS[agentIndex % SKIN_VARIANTS.length],
    hairColor: gender === "female" ? "brown" : "dark",
  };
}
