/**
 * AgentMap — Frontier-style circle-packing map with D3 zoom/pan.
 * LOD Tiers:
 *   Zoomed out (k<1.5): Category circles with product icon + label + count
 *   Mid zoom (1.5<k<3): Colored square dots appear inside circles
 *   Zoomed in (k>3): Dots become agent icons with name labels
 */
import React, { useRef, useEffect, useState, useMemo, useCallback } from "react";
import {
  Text, Button, makeStyles, tokens,
  MessageBar, MessageBarBody, MessageBarTitle,
} from "@fluentui/react-components";
import {
  ArrowMaximizeRegular,
  ArrowMinimizeRegular,
  AddRegular,
  SubtractRegular,
  MyLocationRegular,
  Agents28Regular,
  SearchRegular,
} from "@fluentui/react-icons";
import * as d3 from "d3";
import { useMcpToolData, useMcpApp } from "../shared/McpAppProvider";
import { useFullscreen } from "../shared/useFullscreen";
import { useNotification } from "../shared/useNotification";
import { FallbackBanner } from "../shared/FallbackBanner";
import { AgentDetailPanel } from "../shared/AgentDetailPanel";
import { AssignOwnerPanel } from "../shared/AssignOwnerPanel";
import type { AgentMapData, Agent, AgentDetail, PublisherType } from "../../../src/types";

const GROUP_COLORS: Record<PublisherType, string> = {
  Microsoft: "#0078D4",
  CopilotStudio: "#D4760A",
  AgentBuilder: "#8B5CF6",
  ThirdParty: "#8764B8",
  AgentsToolkit: "#6B8E23",
  Others: "#E3008C",
};

const GROUP_LABELS: Record<PublisherType, string> = {
  Microsoft: "Microsoft",
  CopilotStudio: "Copilot Studio",
  AgentBuilder: "Agent Builder",
  ThirdParty: "Third party",
  AgentsToolkit: "Agents Toolkit",
  Others: "Others",
};

// Microsoft 4-color logo SVG (inline)
const MICROSOFT_ICON = `<svg viewBox="0 0 21 21" xmlns="http://www.w3.org/2000/svg"><rect x="1" y="1" width="9" height="9" fill="#F25022"/><rect x="11" y="1" width="9" height="9" fill="#7FBA00"/><rect x="1" y="11" width="9" height="9" fill="#00A4EF"/><rect x="11" y="11" width="9" height="9" fill="#FFB900"/></svg>`;

// Copilot Studio icon — full CopilotStudio_scalable.svg from workspace
const COPILOTSTUDIO_ICON = `<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M64.3242 4.77449C52.3121 0.77044 46.3052 -1.23042 42.1523 1.76277C38.0001 4.75619 38 11.0874 38 23.7491V33.9991L28.3242 30.7745C16.3121 26.7705 10.3052 24.7696 6.15234 27.7628C1.99998 30.7562 2 37.0874 2 49.7491V67.585C2 74.5417 1.9996 78.0209 3.88672 80.6397C5.7743 83.2586 9.07559 84.3596 15.6758 86.5596L20.002 87.9991L20 88.0011L33.8906 92.63C41.0527 95.0173 44.634 96.2117 48.2168 95.6612C51.7998 95.1105 54.8577 92.8959 60.9727 88.4678L79.5957 74.9835C84.6242 71.3421 87.5709 69.2032 89.3691 66.7569C89.551 66.5194 89.7213 66.2697 89.8789 66.005C90.0501 65.7303 90.212 65.4518 90.3594 65.1632C91.9996 61.9502 92 58.1948 92 50.6846V28.4151C92 21.4583 92.0007 17.9792 90.1133 15.3604C88.2257 12.7416 84.9244 11.6425 78.3242 9.44246L64.3242 4.77449Z" fill="url(#paint0_linear_4303_1230)"/><path d="M64.3242 4.77449C52.3121 0.77044 46.3052 -1.23042 42.1523 1.76277C38.0001 4.75619 38 11.0874 38 23.7491V33.9991L28.3242 30.7745C16.3121 26.7705 10.3052 24.7696 6.15234 27.7628C1.99998 30.7562 2 37.0874 2 49.7491V67.585C2 74.5417 1.9996 78.0209 3.88672 80.6397C5.7743 83.2586 9.07559 84.3596 15.6758 86.5596L20.002 87.9991L20 88.0011L33.8906 92.63C41.0527 95.0173 44.634 96.2117 48.2168 95.6612C51.7998 95.1105 54.8577 92.8959 60.9727 88.4678L79.5957 74.9835C84.6242 71.3421 87.5709 69.2032 89.3691 66.7569C89.551 66.5194 89.7213 66.2697 89.8789 66.005C90.0501 65.7303 90.212 65.4518 90.3594 65.1632C91.9996 61.9502 92 58.1948 92 50.6846V28.4151C92 21.4583 92.0007 17.9792 90.1133 15.3604C88.2257 12.7416 84.9244 11.6425 78.3242 9.44246L64.3242 4.77449Z" fill="url(#paint1_radial_4303_1230)"/><path d="M64.3242 4.77449C52.3121 0.77044 46.3052 -1.23042 42.1523 1.76277C38.0001 4.75619 38 11.0874 38 23.7491V33.9991L28.3242 30.7745C16.3121 26.7705 10.3052 24.7696 6.15234 27.7628C1.99998 30.7562 2 37.0874 2 49.7491V67.585C2 74.5417 1.9996 78.0209 3.88672 80.6397C5.7743 83.2586 9.07559 84.3596 15.6758 86.5596L20.002 87.9991L20 88.0011L33.8906 92.63C41.0527 95.0173 44.634 96.2117 48.2168 95.6612C51.7998 95.1105 54.8577 92.8959 60.9727 88.4678L79.5957 74.9835C84.6242 71.3421 87.5709 69.2032 89.3691 66.7569C89.551 66.5194 89.7213 66.2697 89.8789 66.005C90.0501 65.7303 90.212 65.4518 90.3594 65.1632C91.9996 61.9502 92 58.1948 92 50.6846V28.4151C92 21.4583 92.0007 17.9792 90.1133 15.3604C88.2257 12.7416 84.9244 11.6425 78.3242 9.44246L64.3242 4.77449Z" fill="url(#paint2_radial_4303_1230)"/><path d="M56 54.4151C56 47.4579 56 43.9793 54.1124 41.3604C52.2248 38.7415 48.9247 37.6415 42.3246 35.4414L28.3246 30.7748C16.312 26.7706 10.3058 24.7685 6.1529 27.7617C2 30.755 2 37.0861 2 49.7484V67.5847C2 74.5419 2 78.0206 3.88758 80.6394C5.77516 83.2583 9.07525 84.3583 15.6754 86.5584L29.6754 91.2251C41.688 95.2292 47.6942 97.2313 51.8471 94.2381C56 91.2448 56 84.9137 56 72.2514V54.4151Z" fill="url(#paint3_radial_4303_1230)"/><path d="M56 54.4151C56 47.4579 56 43.9793 54.1124 41.3604C52.2248 38.7415 48.9247 37.6415 42.3246 35.4414L28.3246 30.7748C16.312 26.7706 10.3058 24.7685 6.1529 27.7617C2 30.755 2 37.0861 2 49.7484V67.5847C2 74.5419 2 78.0206 3.88758 80.6394C5.77516 83.2583 9.07525 84.3583 15.6754 86.5584L29.6754 91.2251C41.688 95.2292 47.6942 97.2313 51.8471 94.2381C56 91.2448 56 84.9137 56 72.2514V54.4151Z" fill="url(#paint4_linear_4303_1230)"/><path d="M92 50.6846C92 58.1947 91.9996 61.9501 90.3594 65.1631C90.212 65.4517 90.0501 65.7302 89.8789 66.0049C89.7213 66.2696 89.551 66.5193 89.3691 66.7568C87.5709 69.2031 84.6242 71.3421 79.5957 74.9834L60.9727 88.4678C54.8577 92.8959 51.7998 95.1105 48.2168 95.6611C44.634 96.2116 41.0527 95.0172 33.8906 92.6299L25.2158 89.7393L20 88L20.002 87.999L16.7822 86.9277L15.2217 86.4072C8.92337 84.3067 5.73047 83.1977 3.88672 80.6396C1.99964 78.0208 2 74.5416 2 67.585V49.749C2 48.4323 2.00119 47.1841 2.00586 46.001L56 61.501L92 35.001V50.6846Z" fill="url(#paint5_radial_4303_1230)"/><path d="M38.0742 15.1036C31.3033 13.0668 27.2217 12.5497 24.1523 14.7618C21.0793 16.9767 20.281 21.0195 20.0732 28.1026C22.4635 28.8216 25.1889 29.7306 28.3232 30.7754L37.999 34V23.7491C37.999 20.4569 38.0012 17.5925 38.0742 15.1036Z" fill="url(#paint6_linear_4303_1230)"/><path d="M38.0742 15.1036C31.3033 13.0668 27.2217 12.5497 24.1523 14.7618C21.0793 16.9767 20.281 21.0195 20.0732 28.1026C22.4635 28.8216 25.1889 29.7306 28.3232 30.7754L37.999 34V23.7491C37.999 20.4569 38.0012 17.5925 38.0742 15.1036Z" fill="url(#paint7_linear_4303_1230)" fill-opacity="0.7"/><path d="M38.0742 15.1035C38.0012 17.5922 38 20.4561 38 23.748V41.585C38 48.5419 38.0002 52.0208 39.8877 54.6396C41.7753 57.2583 45.0758 58.3586 51.6758 60.5586L56 62C64.0027 64.6676 68.0041 66.0014 70.84 64.1408C71.0112 64.0284 71.1774 63.9086 71.3381 63.7817C74 61.6798 74 57.462 74 49.0263V41.415C74 34.4579 73.9999 30.9792 72.1123 28.3604C70.2247 25.7416 66.9243 24.6414 60.3242 22.4414L46.3242 17.7744C43.1901 16.7297 40.4644 15.8225 38.0742 15.1035Z" fill="url(#paint8_linear_4303_1230)"/><path d="M38.0742 15.1035C38.0012 17.5922 38 20.4561 38 23.748V41.585C38 48.5419 38.0002 52.0208 39.8877 54.6396C41.7753 57.2583 45.0758 58.3586 51.6758 60.5586L56 62C64.0027 64.6676 68.0041 66.0014 70.84 64.1408C71.0112 64.0284 71.1774 63.9086 71.3381 63.7817C74 61.6798 74 57.462 74 49.0263V41.415C74 34.4579 73.9999 30.9792 72.1123 28.3604C70.2247 25.7416 66.9243 24.6414 60.3242 22.4414L46.3242 17.7744C43.1901 16.7297 40.4644 15.8225 38.0742 15.1035Z" fill="url(#paint9_radial_4303_1230)"/><path d="M20.0742 28.1035C20.0012 30.5922 20 33.4561 20 36.748V54.585C20 61.5421 20.0001 65.0208 21.8877 67.6396C23.7753 70.2584 27.0757 71.3586 33.6758 73.5586L37.975 74.9917C46.0014 77.6671 50.0146 79.0049 52.855 77.1309C53.0159 77.0247 53.1724 76.9119 53.324 76.7928C56 74.6909 56 70.4606 56 62V54.415C56 47.4579 55.9999 43.9792 54.1123 41.3604C52.2247 38.7416 48.9243 37.6414 42.3242 35.4414L28.3242 30.7744C25.1901 29.7297 22.4644 28.8225 20.0742 28.1035Z" fill="url(#paint10_linear_4303_1230)"/><path d="M38 41.585C38 48.5422 38.0001 52.0208 39.8877 54.6397C41.7753 57.2585 45.0756 58.3585 51.6758 60.5586L56 62V54.415C56 47.4581 55.9998 43.9792 54.1123 41.3604C52.2247 38.7417 48.9242 37.6414 42.3242 35.4414L38 34V41.585Z" fill="url(#paint11_linear_4303_1230)"/><defs><linearGradient id="paint0_linear_4303_1230" x1="53.5" y1="77" x2="80.9999" y2="9.99998" gradientUnits="userSpaceOnUse"><stop stop-color="#2764E7"/><stop offset="0.307475" stop-color="#8B52F4"/><stop offset="0.544627" stop-color="#BB45EA"/><stop offset="0.803866" stop-color="#DB56C6"/><stop offset="1" stop-color="#F462AB"/></linearGradient><radialGradient id="paint1_radial_4303_1230" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(52.5 45) rotate(43.8065) scale(33.9485 21.4653)"><stop offset="0.549399" stop-color="#5B2AB5"/><stop offset="1" stop-color="#A931D8" stop-opacity="0"/></radialGradient><radialGradient id="paint2_radial_4303_1230" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(44 34) rotate(17.7004) scale(49.3356 24.5964)"><stop offset="0.527929" stop-color="#9529C2"/><stop offset="1" stop-color="#DD3CE2" stop-opacity="0"/></radialGradient><radialGradient id="paint3_radial_4303_1230" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(61.3922 89.3373) rotate(-124.89) scale(82.0935 82.0935)"><stop stop-color="#2764E7"/><stop offset="0.225228" stop-color="#0094F0"/><stop offset="0.443437" stop-color="#19B2CE"/><stop offset="0.6999" stop-color="#52D17C"/><stop offset="1" stop-color="#FFD638"/></radialGradient><linearGradient id="paint4_linear_4303_1230" x1="19.5444" y1="82.7096" x2="53.8452" y2="82.7096" gradientUnits="userSpaceOnUse"><stop stop-color="#16BBDA" stop-opacity="0"/><stop offset="0.535279" stop-color="#0094F0"/><stop offset="1" stop-color="#2764E7"/></linearGradient><radialGradient id="paint5_radial_4303_1230" cx="0" cy="0" r="1" gradientTransform="matrix(23 12.9998 8.90874 -13.0499 43 67.9995)" gradientUnits="userSpaceOnUse"><stop stop-color="#1B44B1"/><stop offset="1" stop-color="#367AF2" stop-opacity="0"/></radialGradient><linearGradient id="paint6_linear_4303_1230" x1="33.5" y1="32.5" x2="34" y2="13" gradientUnits="userSpaceOnUse"><stop stop-color="#FF9C70"/><stop offset="1" stop-color="#FFD394"/></linearGradient><linearGradient id="paint7_linear_4303_1230" x1="28.5" y1="24.5" x2="26.5" y2="33" gradientUnits="userSpaceOnUse"><stop stop-color="#FFB357" stop-opacity="0"/><stop offset="1" stop-color="#F24A9D"/></linearGradient><linearGradient id="paint8_linear_4303_1230" x1="58" y1="20" x2="58.5" y2="64.5" gradientUnits="userSpaceOnUse"><stop stop-color="#FFB357"/><stop offset="0.380259" stop-color="#FB6F7B"/><stop offset="0.659779" stop-color="#F24A9D"/><stop offset="1" stop-color="#DD3CE2"/></linearGradient><radialGradient id="paint9_radial_4303_1230" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(40 54) rotate(12.702) scale(24.0895 24.0895)"><stop offset="0.567938" stop-color="#D7257D"/><stop offset="1" stop-color="#F462AB" stop-opacity="0"/></radialGradient><linearGradient id="paint10_linear_4303_1230" x1="50.03" y1="77.3707" x2="20" y2="25.6869" gradientUnits="userSpaceOnUse"><stop stop-color="#0FAFFF"/><stop offset="0.54828" stop-color="#2BDABE"/><stop offset="0.765945" stop-color="#88E06C"/><stop offset="1" stop-color="#FFD638"/></linearGradient><linearGradient id="paint11_linear_4303_1230" x1="36" y1="44.5" x2="53" y2="50.5" gradientUnits="userSpaceOnUse"><stop stop-color="#76EB95"/><stop offset="1" stop-color="#3BD5FF" stop-opacity="0"/></linearGradient></defs></svg>`;

// Agent icon for Tier 3 zoomed-in cards — actual Fluent Agents28Regular SVG paths
const AGENT_ICON = `<svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9.3 4.5a.75.75 0 0 0-.65.38L3.6 13.63a.75.75 0 0 0 0 .74l4.89 8.47a1.32 1.32 0 0 0 2.42-.32l4.73-17.44a2.82 2.82 0 0 1 5.17-.67l4.89 8.46c.4.7.4 1.56 0 2.26l-5.05 8.74c-.4.7-1.15 1.13-1.95 1.13h-3.95a.75.75 0 0 1 0-1.5h3.95c.27 0 .51-.14.65-.38l5.05-8.75a.75.75 0 0 0 0-.74L19.5 5.15a1.32 1.32 0 0 0-2.42.32l-4.73 17.44a2.82 2.82 0 0 1-5.17.67L2.3 15.13c-.4-.7-.4-1.56 0-2.26l5.05-8.74C7.75 3.42 8.5 3 9.3 3h3.95a.75.75 0 0 1 0 1.5H9.3Z" fill="#616161"/></svg>`;

// Agents Toolkit icon — Microsoft.png (embedded as base64 data URI)
const TOOLKIT_ICON = `<svg viewBox="0 0 21 21" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><image width="21" height="21" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABQAAAAUACAMAAAAvOg/FAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAATlBMVEXz8/Pz4Nrzu6vz6uft8OXL4KDl7NfzUyXz18/f6cmBvAbz7u3w8ezl7/PJ5fLs8fPz8ez16cn08OWg2PIFpvD/ugj336HX6vL07Nf///+mOo5nAAAAAWJLR0QZ7G61iAAAAAd0SU1FB+kIHQExAkYNKMAAABUUSURBVHja7dRLDoJQEADBJx8FFRRQ9P4n9QBsJhNCXFSdodOlAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwo1MFQXWusaaFoPPBA6wuENTlGuuvENQaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIAYIBYoBggBggGCAGCAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBjgVt1B0C3X2L2HoKYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/JNhhKBHrrHnBEHzwQNcXhA05hqb3hC0GiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBjgVt1B0C3X2L2HoKYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/JNhhKBHrrHnBEHzwQNcXhA05hqb3hC0GiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYIBggBggGiAGCAWKAYIAYIAZogBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAYIBogBggFigGCAGCAYIAYIBogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoBggBggGCAGCAaIAYIBYoBggBggBmiAGCAGaIAYIAZogBggBmiAGCAGaIAYIAZogBggBggGiAGCAWKAYIAYIBggBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAEaIAaIARogBogBGiAGiAGCAWKAYIAYIBggBggGiAFigAaIAWKABogBYoAGiAFigAaIAWKABogBYoAGiAFigAaIAWKAYIAYIBggBggGiAGCAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAYoAFigBigAWKAGKABYoAY4NZngaAh19i8QtC3AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwox8d+Eh2toR2IgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAyNS0wOC0yOVQwMTo0OTowMiswMDowMEE2gkoAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMjUtMDgtMjlUMDE6NDk6MDIrMDA6MDAwazr2AAAAAElFTkSuQmCC"/></svg>`;

// Others & Third Party icon — actual Fluent Agents28Color SVG
const AGENTS_COLOR_ICON = `<svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.31 24.6 14.36 3H18a6.5 6.5 0 0 0 .12 0c1.16 0 2.23.62 2.81 1.63l4.77 8.25c.4.7.4 1.55 0 2.24l-5.06 8.76c-.4.7-1.14 1.12-1.94 1.12H9.88c-.56 0-1.1-.14-1.57-.4Z" fill="url(#agc_a)"/><path d="M8.31 24.6 14.36 3H18a6.5 6.5 0 0 0 .12 0c1.16 0 2.23.62 2.81 1.63l4.77 8.25c.4.7.4 1.55 0 2.24l-5.06 8.76c-.4.7-1.14 1.12-1.94 1.12H9.88c-.56 0-1.1-.14-1.57-.4Z" fill="url(#agc_b)" fill-opacity=".5"/><path d="M16.02 5.2a2.5 2.5 0 0 1 2.3-2.2H9.3c-.8 0-1.54.43-1.95 1.13L2.3 12.88c-.4.7-.4 1.55 0 2.24l4.76 8.26c.1.16.2.31.33.45a2.5 2.5 0 0 0 4.59-1.02l4.04-17.6Z" fill="url(#agc_c)"/><path d="M16.02 5.2a2.5 2.5 0 0 1 2.3-2.2H9.3c-.8 0-1.54.43-1.95 1.13L2.3 12.88c-.4.7-.4 1.55 0 2.24l4.76 8.26c.1.16.2.31.33.45a2.5 2.5 0 0 0 4.59-1.02l4.04-17.6Z" fill="url(#agc_d)" fill-opacity=".4"/><defs><radialGradient id="agc_a" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="rotate(-87.78 24.2 7.07) scale(32.08 26.98)"><stop stop-color="#FFC470"/><stop offset=".25" stop-color="#FF835C"/><stop offset=".58" stop-color="#F24A9D"/><stop offset=".87" stop-color="#B339F0"/><stop offset="1" stop-color="#C354FF"/></radialGradient><radialGradient id="agc_b" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="matrix(-14.42 -13.52 13.65 -14.57 15.57 22.46)"><stop offset=".71" stop-color="#FFB357" stop-opacity="0"/><stop offset=".94" stop-color="#FFB357"/></radialGradient><radialGradient id="agc_c" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="rotate(-159.14 13.87 9.23) scale(30 26.54)"><stop offset=".22" stop-color="#4E46E2"/><stop offset=".58" stop-color="#625DF6"/><stop offset=".95" stop-color="#E37DFF"/></radialGradient><linearGradient id="agc_d" x1="6.96" y1="12.11" x2="14.03" y2="13.69" gradientUnits="userSpaceOnUse"><stop stop-color="#7563F7" stop-opacity="0"/><stop offset=".99" stop-color="#4916AE"/></linearGradient></defs></svg>`;

// Third Party icon — same Agents color icon
const THIRDPARTY_ICON = AGENTS_COLOR_ICON;

const CATEGORY_ICONS: Record<PublisherType, string> = {
  Microsoft: MICROSOFT_ICON,
  CopilotStudio: COPILOTSTUDIO_ICON,
  AgentBuilder: COPILOTSTUDIO_ICON,
  ThirdParty: THIRDPARTY_ICON,
  AgentsToolkit: MICROSOFT_ICON,
  Others: AGENTS_COLOR_ICON,
};

const useStyles = makeStyles({
  root: {
    fontFamily: tokens.fontFamilyBase,
    width: "100%",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 20px",
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  mapContainer: {
    position: "relative",
    flex: 1,
    overflow: "hidden",
  },
  zoomControls: {
    position: "absolute",
    top: "16px",
    right: "16px",
    display: "flex",
    gap: "4px",
    alignItems: "center",
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: "6px",
    padding: "4px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
    zIndex: 10,
  },
  zoomBtn: {
    minWidth: "32px",
    width: "32px",
    height: "32px",
    padding: "0",
  },
  legend: {
    display: "flex",
    gap: "16px",
    padding: "10px 20px",
    borderTop: `1px solid ${tokens.colorNeutralStroke1}`,
    flexWrap: "wrap",
    alignItems: "center",
  },
  legendItem: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    fontSize: "12px",
  },
  legendDot: {
    width: "12px",
    height: "12px",
    borderRadius: "50%",
    border: "2px solid",
  },
});

export function AgentMap() {
  const styles = useStyles();
  const { app } = useMcpApp();
  const data = useMcpToolData<AgentMapData>();
  const { isFullscreen, toggleFullscreen } = useFullscreen();
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown>>(undefined);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [selectedAgentDetail, setSelectedAgentDetail] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const agents = data?.agents ?? [];
  const groups = data?.groups ?? [];
  const dataSource = data?.dataSource ?? "mock";
  const detailMap = data?.detailMap ?? {};
  const assignableUsers = data?.assignableUsers ?? [];

  const handleBlock = useCallback(async (agentId: string) => {
    if (!app) return;
    try {
      await app.callServerTool({ name: "block_agent", arguments: { agentId, reason: "Blocked by admin via Agent 365" } });
      setSelectedAgent(prev => prev ? { ...prev, isBlocked: true } : null);
      showNotification(`Agent blocked successfully.`, "success");
    } catch (e) {
      showNotification(`Failed to block agent.`, "error");
    }
  }, [app]);

  const handleUnblock = useCallback(async (agentId: string) => {
    if (!app) return;
    try {
      await app.callServerTool({ name: "unblock_agent", arguments: { agentId } });
      setSelectedAgent(prev => prev ? { ...prev, isBlocked: false } : null);
      showNotification(`Agent unblocked successfully.`, "success");
    } catch (e) {
      showNotification(`Failed to unblock agent.`, "error");
    }
  }, [app]);

  // Assign owner state
  const [showPeoplePicker, setShowPeoplePicker] = useState(false);
  const { notification, showNotification } = useNotification();

  const handleDelete = useCallback(async (agentId: string) => {
    if (!app) return;
    try {
      await app.callServerTool({ name: "block_agent", arguments: { agentId, reason: "Deleted by admin" } });
      showNotification("Agent blocked. Note: full deletion is not available via the Graph API.", "success");
    } catch {
      showNotification("Failed to delete agent.", "error");
    }
  }, [app]);

  const handleAssignOwner = useCallback(async (userId: string) => {
    if (!app || !selectedAgent) return;
    try {
      await app.callServerTool({ name: "reassign_agent", arguments: { agentId: selectedAgent.id, newOwnerId: userId } });
      showNotification("Owner reassigned successfully.", "success");
      setShowPeoplePicker(false);
    } catch (e) {
      showNotification("Failed to reassign owner.", "error");
    }
  }, [app, selectedAgent]);

  // Build hierarchy for D3 circle-packing
  const hierarchy = useMemo(() => {
    const grouped = new Map<string, Agent[]>();
    for (const agent of agents) {
      const key = agent.publisherType;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key)!.push(agent);
    }

    const children = Array.from(grouped.entries()).map(([type, groupAgents]) => {
      // Pad small groups so they render at a minimum visible size
      const minSize = 8;
      const paddedAgents: Array<{ name: string; value: number; id: string; agent: Agent | null }> = groupAgents.map((a) => ({ name: a.displayName, value: 1, id: a.id, agent: a }));
      if (groupAgents.length < minSize) {
        for (let i = groupAgents.length; i < minSize; i++) {
          paddedAgents.push({ name: "", value: 1, id: `__pad_${type}_${i}`, agent: null });
        }
      }
      return { name: type, children: paddedAgents };
    });

    return d3.hierarchy({ name: "root", children })
      .sum((d) => (d as { value?: number }).value || 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0));
  }, [agents]);

  // Render SVG with D3
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || agents.length === 0) return;

    const width = svg.clientWidth || 900;
    const height = svg.clientHeight || 600;

    const d3Svg = d3.select(svg);
    d3Svg.selectAll("*").remove();

    // Defs: dot pattern + category icon images
    const defs = d3Svg.append("defs");

    // Dotted background pattern
    defs.append("pattern")
      .attr("id", "dotGrid")
      .attr("width", 24)
      .attr("height", 24)
      .attr("patternUnits", "userSpaceOnUse")
      .append("circle")
      .attr("cx", 12)
      .attr("cy", 12)
      .attr("r", 1.5)
      .attr("fill", "#d4d4d4");

    // Main group for zoom/pan
    const g = d3Svg.append("g").attr("class", "zoomable");

    // Background with dots
    g.append("rect")
      .attr("x", -5000)
      .attr("y", -5000)
      .attr("width", 10000)
      .attr("height", 10000)
      .attr("fill", "#fafafa");

    g.append("rect")
      .attr("x", -5000)
      .attr("y", -5000)
      .attr("width", 10000)
      .attr("height", 10000)
      .attr("fill", "url(#dotGrid)");

    // Circle-packing layout
    const pack = d3.pack<any>()
      .size([width * 0.85, height * 0.85])
      .padding(20);

    const root = pack(hierarchy);
    const offsetX = width * 0.075;
    const offsetY = height * 0.075;

    // Category nodes (depth 1)
    const categoryNodes = root.descendants().filter((d) => d.depth === 1);
    // All agent leaf nodes (exclude only padding)
    const allLeaves = root.leaves().filter((d) => !d.data.id?.startsWith("__pad_"));
    // Push dots that fall within center zone outward (don't remove them)
    const agentNodes = allLeaves.map((d) => {
      const parent = d.parent;
      if (!parent) return d;
      const dx = d.x - parent.x;
      const dy = d.y - parent.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const exclusionRadius = parent.r * 0.35;
      if (dist < exclusionRadius && dist > 0) {
        // Push outward to just beyond the exclusion zone
        // D3 typings declare x/y as readonly, but they are mutable post-layout
        const scale = (exclusionRadius + 8) / dist;
        (d as any).x = parent.x + dx * scale;
        (d as any).y = parent.y + dy * scale;
      } else if (dist === 0) {
        // Exactly at center — push in a random direction
        const angle = Math.random() * Math.PI * 2;
        (d as any).x = parent.x + Math.cos(angle) * (exclusionRadius + 8);
        (d as any).y = parent.y + Math.sin(angle) * (exclusionRadius + 8);
      }
      return d;
    });

    // --- CATEGORY CIRCLES ---
    const categoryG = g.selectAll("g.category")
      .data(categoryNodes)
      .join("g")
      .attr("class", "category")
      .attr("transform", (d) => `translate(${d.x + offsetX}, ${d.y + offsetY})`);

    // Circle with colored stroke and light fill
    categoryG.append("circle")
      .attr("r", (d) => d.r)
      .attr("fill", (d) => {
        const color = GROUP_COLORS[d.data.name as PublisherType] ?? "#888";
        return color + "12";
      })
      .attr("stroke", (d) => GROUP_COLORS[d.data.name as PublisherType] ?? "#888")
      .attr("stroke-width", 3)
      .attr("stroke-opacity", 0.8);

    // --- AGENT NODES (dots → icons based on zoom) --- rendered BEFORE center overlay
    const agentG = g.selectAll("g.agent")
      .data(agentNodes)
      .join("g")
      .attr("class", "agent")
      .attr("transform", (d) => `translate(${d.x + offsetX}, ${d.y + offsetY})`)
      .style("opacity", 0); // Hidden at initial zoom

    // Agent dot (colored square, matching Agent 365 style)
    agentG.append("rect")
      .attr("class", "agent-dot")
      .attr("x", -4)
      .attr("y", -4)
      .attr("width", 8)
      .attr("height", 8)
      .attr("rx", 2)
      .attr("fill", (d) => {
        const parent = d.parent;
        return GROUP_COLORS[parent?.data.name as PublisherType] ?? "#888";
      })
      .attr("opacity", 0.8)
      .style("cursor", "pointer");

    // Native tooltip showing agent name on hover
    agentG.append("title")
      .text((d) => d.data.name || "");

    // Click handler on agent nodes → open detail drawer
    agentG.on("click", async (event, d) => {
      event.stopPropagation();
      const agentData = agents.find(a => a.id === d.data.id || a.displayName === d.data.name);
      if (agentData) {
        setSelectedAgent(agentData);
        // Use preloaded detail if available
        const preloaded = detailMap[agentData.id];
        setSelectedAgentDetail(preloaded ?? null);
        setDetailLoading(false);
      }
    });

    // Hover behavior: fade others, highlight hovered agent
    agentG.on("mouseenter", function (event) {
      const self = this;
      g.selectAll("g.agent").style("opacity", function() {
        return this === self ? "1" : "0.25";
      });
    }).on("mouseleave", function () {
      // Restore all visible agents to full opacity (respecting current zoom tier)
      const currentK = d3.zoomTransform(svg).k;
      g.selectAll("g.agent").style("opacity", currentK >= 1.5 ? "1" : "0");
    });

    // Agent icon (foreignObject, hidden until zoomed in enough)
    agentG.append("foreignObject")
      .attr("class", "agent-icon-fo")
      .attr("x", -14)
      .attr("y", -14)
      .attr("width", 28)
      .attr("height", 28)
      .style("opacity", 0)
      .style("cursor", "pointer")
      .html(() => `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;border:1px solid #e0e0e0;border-radius:6px;background:white;box-shadow:0 1px 4px rgba(0,0,0,0.08)">${AGENT_ICON}</div>`);

    // Agent name label (hidden until very zoomed in) — truncated with native tooltip
    agentG.each(function (d) {
      const name = d.data.name ?? "";
      const truncated = name.length > 10 ? name.substring(0, 9) + "..." : name;
      const el = d3.select(this);

      const text = el.append("text")
        .attr("class", "agent-label")
        .attr("text-anchor", "middle")
        .attr("y", 22)
        .attr("font-size", 6)
        .attr("font-family", "Segoe UI, sans-serif")
        .attr("fill", "#444")
        .style("opacity", 0)
        .style("cursor", "pointer")
        .text(truncated);

      // Native SVG tooltip for full name on hover
      text.append("title").text(name);
    });

    // --- CATEGORY CENTER OVERLAY (rendered on top of dots) ---
    const overlayG = g.selectAll("g.cat-overlay")
      .data(categoryNodes)
      .join("g")
      .attr("class", "cat-overlay")
      .attr("transform", (d) => `translate(${d.x + offsetX}, ${d.y + offsetY})`)
      .style("pointer-events", "none");

    // Clear zone — no background, just pointer-events:none on the group keeps text readable
    // Dots are pushed outward by the repositioning logic above

    // Category icon — centered vertically accounting for label+count below
    overlayG.append("foreignObject")
      .attr("class", "cat-icon")
      .attr("x", (d) => -Math.min(24, d.r * 0.18))
      .attr("y", (d) => -Math.min(24, d.r * 0.18) - Math.min(14, d.r * 0.1))
      .attr("width", (d) => Math.min(48, d.r * 0.36))
      .attr("height", (d) => Math.min(48, d.r * 0.36))
      .html((d) => {
        const icon = CATEGORY_ICONS[d.data.name as PublisherType] ?? AGENTS_COLOR_ICON;
        return `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center">${icon}</div>`;
      });

    // Category label — just below center
    overlayG.append("text")
      .attr("class", "cat-label")
      .attr("text-anchor", "middle")
      .attr("y", (d) => Math.min(14, d.r * 0.1) + 4)
      .attr("font-size", (d) => Math.min(13, d.r * 0.1))
      .attr("font-family", "Segoe UI, sans-serif")
      .attr("font-weight", "600")
      .attr("fill", "#333")
      .text((d) => GROUP_LABELS[d.data.name as PublisherType] ?? d.data.name);

    // Category count — below label
    overlayG.append("text")
      .attr("class", "cat-count")
      .attr("text-anchor", "middle")
      .attr("y", (d) => Math.min(14, d.r * 0.1) + 4 + Math.min(20, d.r * 0.14))
      .attr("font-size", (d) => Math.min(20, d.r * 0.15))
      .attr("font-family", "Segoe UI, sans-serif")
      .attr("font-weight", "700")
      .attr("fill", "#444")
      .text((d) => d.children?.filter((c) => !(c.data as { id?: string }).id?.startsWith("__pad_")).length ?? 0);

    // --- ZOOM BEHAVIOR ---
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.4, 10])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
        const k = event.transform.k;
        setZoomLevel(k);

        // LOD Tier 1 (k < 1.5): Only category circles visible, no dots
        // LOD Tier 2 (1.5 <= k < 3.5): Dots appear as colored squares
        // LOD Tier 3 (k >= 3.5): Dots become agent icons with labels

        // Category elements: always visible but fade label at extreme zoom
        g.selectAll(".cat-icon").style("opacity", k < 4 ? 1 : 0.3);
        g.selectAll(".cat-label").style("opacity", k < 5 ? 1 : 0.2);
        g.selectAll(".cat-count").style("opacity", k < 5 ? 1 : 0.2);

        // Agent groups: appear at tier 2+
        g.selectAll("g.agent").style("opacity", k >= 1.5 ? 1 : 0);

        // Agent dots vs icons
        if (k >= 3.5) {
          // Tier 3: show icon, hide dot — cap icon size via inverse scale
          g.selectAll(".agent-dot").style("opacity", 0);
          g.selectAll(".agent-icon-fo").style("opacity", 1);
          g.selectAll(".agent-label").style("opacity", 1);
          // Cap icon at ~40px visual size (28 * maxScale)
          const maxVisualSize = 40;
          const naturalSize = 28 * k;
          if (naturalSize > maxVisualSize) {
            const scale = maxVisualSize / naturalSize;
            g.selectAll(".agent-icon-fo")
              .attr("transform", `scale(${1/k * (maxVisualSize/28)})`);
            g.selectAll(".agent-label")
              .attr("transform", `scale(${Math.min(1, 3.5/k)})`);
          } else {
            g.selectAll(".agent-icon-fo").attr("transform", null);
            g.selectAll(".agent-label").attr("transform", null);
          }
        } else {
          // Tier 2: show dot, hide icon
          g.selectAll(".agent-dot").style("opacity", 0.8);
          g.selectAll(".agent-icon-fo").style("opacity", 0);
          g.selectAll(".agent-label").style("opacity", 0);
        }
      });

    d3Svg.call(zoom);
    zoomRef.current = zoom;

  }, [hierarchy, agents]);

  // Zoom control handlers
  const handleZoomIn = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1.5);
  };
  const handleZoomOut = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 0.67);
  };
  const handleReset = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(500).call(zoomRef.current.transform, d3.zoomIdentity);
  };

  // --- INLINE VIEW (compact chat card per UX guidelines) ---
  if (!isFullscreen) {
    return (
      <div className={styles.root} style={{ padding: "24px" }}>
        <FallbackBanner dataSource={dataSource} />
        {/* Header with expand icon */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Agents28Regular style={{ fontSize: "28px", color: tokens.colorBrandForeground1 }} />
            <Text size={500} weight="bold">Agent Map</Text>
            <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>
              {agents.length} agents &middot; {groups.length} categories
            </Text>
          </div>
          <Button
            appearance="subtle"
            icon={<ArrowMaximizeRegular />}
            onClick={toggleFullscreen}
            title="Open in side-by-side"
          />
        </div>

        {/* Category breakdown in grid-styled container */}
        <div style={{
          border: "1px solid #E0E0E0", borderRadius: "8px", overflow: "hidden",
          backgroundColor: "#FFFFFF", boxShadow: "0 2px 8px rgba(0,0,0,0.12), 0 0 1px rgba(0,0,0,0.04)",
        }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid #E0E0E0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Text size={300} weight="semibold" style={{ color: tokens.colorNeutralForeground2 }}>Agent Categories</Text>
            <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>{agents.length} total</Text>
          </div>
          {groups.map((g, i) => (
            <div key={g.type} style={{
              display: "flex", alignItems: "center", gap: "10px",
              padding: "10px 16px",
              borderBottom: i < groups.length - 1 ? `1px solid ${tokens.colorNeutralStroke3}` : undefined,
            }}>
              <span
                style={{ width: "20px", height: "20px", flexShrink: 0, display: "inline-flex", alignItems: "center", justifyContent: "center" }}
                dangerouslySetInnerHTML={{ __html: CATEGORY_ICONS[g.type] }}
              />
              <Text size={300} style={{ flex: 1 }}>{GROUP_LABELS[g.type]}</Text>
              <Text size={300} weight="semibold" style={{ color: GROUP_COLORS[g.type] }}>{g.count}</Text>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // --- SIDE-BY-SIDE VIEW (full interactive map) ---
  return (
    <div className={styles.root} style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <FallbackBanner dataSource={dataSource} />
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Text size={500} weight="bold">Agent Map — Frontier</Text>
        </div>
        <Button
          appearance="subtle"
          icon={<ArrowMinimizeRegular />}
          onClick={toggleFullscreen}
          title="Exit side-by-side"
        />
      </div>

      {/* Map */}
      <div className={styles.mapContainer}>
        <svg
          ref={svgRef}
          role="img"
          aria-label="Circle-packing visualization of agents grouped by publisher type"
          style={{ width: "100%", height: "100%", display: "block", cursor: "grab", backgroundColor: "#fafafa" }}
        />

        {/* Zoom Controls */}
        <div className={styles.zoomControls}>
          <Button className={styles.zoomBtn} appearance="subtle" size="small" icon={<MyLocationRegular />} onClick={handleReset} title="Reset view" />
          <Button className={styles.zoomBtn} appearance="subtle" size="small" icon={<AddRegular />} onClick={handleZoomIn} title="Zoom in" />
          <Button className={styles.zoomBtn} appearance="subtle" size="small" icon={<SubtractRegular />} onClick={handleZoomOut} title="Zoom out" />
        </div>
      </div>

      {/* Legend */}
      <div className={styles.legend}>
        {groups.map((g) => (
          <span key={g.type} className={styles.legendItem}>
            <span className={styles.legendDot} style={{ borderColor: GROUP_COLORS[g.type], backgroundColor: GROUP_COLORS[g.type] + "30" }} />
            {GROUP_LABELS[g.type]} ({g.count})
          </span>
        ))}
        <Text size={200} style={{ color: tokens.colorNeutralForeground4, marginLeft: "auto" }}>
          Zoom: {Math.round(zoomLevel * 100)}% • {agents.length} agents total
        </Text>
      </div>

      {/* Agent Detail Panel */}
      {notification && (
        <div style={{ position: "fixed", top: "16px", right: "16px", zIndex: 2000, maxWidth: "400px" }}>
          <MessageBar intent={notification.intent}>
            <MessageBarBody>
              <MessageBarTitle>{notification.intent === "success" ? "Success" : "Error"}</MessageBarTitle>
              {notification.message}
            </MessageBarBody>
          </MessageBar>
        </div>
      )}
      {selectedAgent && (
        <>
          {showPeoplePicker ? (
            <>
              <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.3)", zIndex: 999 }}
                onClick={() => { setSelectedAgent(null); setShowPeoplePicker(false); }} />
              <div style={{ position: "fixed", top: 0, right: 0, width: "440px", height: "100%", overflow: "auto", zIndex: 1000, padding: "24px", backgroundColor: tokens.colorNeutralBackground1, boxShadow: "-4px 0 16px rgba(0,0,0,0.15)" }}>
                <AssignOwnerPanel
                  users={assignableUsers}
                  onAssign={handleAssignOwner}
                  onBack={() => setShowPeoplePicker(false)}
                  onClose={() => { setSelectedAgent(null); setShowPeoplePicker(false); }}
                  description="Select a user with a Microsoft 365 Copilot license to assign as the new owner."
                />
              </div>
            </>
          ) : (
            <AgentDetailPanel
              agent={selectedAgent}
              agentDetail={selectedAgentDetail}
              detailLoading={detailLoading}
              onClose={() => setSelectedAgent(null)}
              onBlock={handleBlock}
              onUnblock={handleUnblock}
              onAssignOwner={() => setShowPeoplePicker(true)}
              onDelete={handleDelete}
            />
          )}
        </>
      )}
    </div>
  );
}
